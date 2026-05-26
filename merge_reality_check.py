#!/usr/bin/env python3
"""Merge operational intelligence batches into reality-check-intelligence.json."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent

# One file per batch; exclude duplicate pretty/compact twins of patterns
SOURCE_FILES = [
    "operational-intelligence-patterns.compact.json",
    "operational-intelligence-batch2.json",
    "operational-intelligence-batch4.json",
    "operational-intelligence-batch5.json",
    "operational-intelligence-extract.json",
    "operational-intelligence-newsletters.json",
]

REQUIRED_FIELDS = [
    "pattern_name",
    "source_episode",
    "source_guest",
    "source_quote_or_context",
    "category",
    "core_belief",
    "operational_pattern",
    "organizational_archetype",
    "hidden_assumptions",
    "pressure_scenarios",
    "failure_modes",
    "contradictions",
    "behavioral_signals",
    "emotional_political_dynamics",
    "operational_adaptations",
    "ai_era_implications",
]

# Guest alias → canonical name from index.json
GUEST_ALIASES: dict[str, str] = {
    "sherwin wu v2": "Sherwin Wu",
    "sherwin wu": "Sherwin Wu",
    "codex": "Alexander Embiricos",
    "alexander embiricos": "Alexander Embiricos",
    "elena verna 4.0": "Elena Verna",
    "elena verna": "Elena Verna",
    "nikhyl singhal": "Nikhyl Singhal",
    "dr. fei fei li": "Dr. Fei-Fei Li",
    "dr fei-fei li": "Dr. Fei-Fei Li",
    "dr. fei-fei li": "Dr. Fei-Fei Li",
    "jason m lekin": "Jason Lemkin",
    "jason lemkin": "Jason Lemkin",
    "aishwarya naresh reganti + kiriti badam": "Aishwarya Naresh Reganti & Kiriti Badam",
    "aishwarya naresh reganti, kiriti badam": "Aishwarya Naresh Reganti & Kiriti Badam",
    "kiriti badam, aishwarya naresh reganti": "Aishwarya Naresh Reganti & Kiriti Badam",
    "aishwarya naresh reganti": "Aishwarya Naresh Reganti",
    "kiriti badam": "Kiriti Badam",
    "hamel husain & shreya shankar": "Hamel Husain & Shreya Shankar",
    "jeanne grosser": "Jeanne DeWitt Grosser",
    "jeanne dewitt grosser": "Jeanne DeWitt Grosser",
    "dhanji r. prasanna": "Dhanji R. Prasanna",
    "lenny rachitsky": "Lenny Rachitsky (Newsletter)",
    "aman khan": "Aman Khan (Newsletter)",
    "jorge mazal": "Jorge Mazal (Newsletter)",
    "tal raviv": "Tal Raviv (Newsletter)",
    "colin matthews": "Colin Matthews (Newsletter)",
    "amir klein": "Amir Klein (Newsletter)",
    "molly graham (via mark zuckerberg)": "Molly Graham",
    "molly graham (cheryl sandberg)": "Molly Graham",
}


def norm_guest(guest: str) -> str:
    g = (guest or "").strip()
    key = re.sub(r"\s+", " ", g.lower())
    return GUEST_ALIASES.get(key, g)


def norm_text(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^\w\s]", "", s)
    return re.sub(r"\s+", " ", s)


def dedupe_key(obj: dict) -> str:
    return "|".join([
        norm_text(obj.get("pattern_name", "")),
        norm_text(norm_guest(obj.get("source_guest", ""))),
    ])


def richness_score(obj: dict) -> int:
    """Prefer longer, more complete objects when deduping."""
    score = 0
    for k in REQUIRED_FIELDS:
        v = obj.get(k)
        if isinstance(v, str):
            score += len(v)
        elif isinstance(v, list):
            score += sum(len(str(x)) for x in v)
    return score


LIST_FIELDS = (
    "hidden_assumptions",
    "pressure_scenarios",
    "failure_modes",
    "contradictions",
    "behavioral_signals",
    "emotional_political_dynamics",
    "operational_adaptations",
    "ai_era_implications",
)


def to_list(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x is not None and str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


def normalize_object(obj: dict, source_file: str) -> dict:
    out: dict = {}
    for k in REQUIRED_FIELDS:
        out[k] = obj.get(k, "" if k not in LIST_FIELDS else [])
    out["source_guest"] = norm_guest(str(out.get("source_guest", "")))
    out["_provenance"] = source_file
    for k in LIST_FIELDS:
        out[k] = to_list(obj.get(k))
    # String fields default
    for k in ("pattern_name", "source_episode", "source_quote_or_context", "category",
              "core_belief", "operational_pattern", "organizational_archetype"):
        if not out.get(k):
            out[k] = str(obj.get(k, "") or "Unknown")
    return out


def load_all() -> tuple[list[dict], list[str], int]:
    merged: dict[str, dict] = {}
    sources_loaded: list[str] = []
    raw_count = 0

    for fname in SOURCE_FILES:
        path = ROOT / fname
        if not path.exists():
            print(f"WARN: missing {fname}")
            continue
        data = json.loads(path.read_text())
        if not isinstance(data, list):
            raise ValueError(f"{fname} is not a JSON array")
        sources_loaded.append(fname)
        for obj in data:
            raw_count += 1
            if not obj.get("pattern_name"):
                raise ValueError(f"{fname}: object missing pattern_name")
            normalized = normalize_object(obj, fname)
            key = dedupe_key(normalized)
            existing = merged.get(key)
            if existing is None or richness_score(normalized) > richness_score(existing):
                merged[key] = normalized

    items = list(merged.values())
    # Stable sort: guest, then pattern name
    items.sort(key=lambda o: (o["source_guest"].lower(), o["pattern_name"].lower()))
    return items, sources_loaded, raw_count


def build_coverage(items: list[dict], index: dict) -> dict:
    by_guest = Counter(o["source_guest"] for o in items)

    podcast_guests = {p["guest"]: p for p in index.get("podcasts", [])}
    newsletter_titles = {n["title"]: n for n in index.get("newsletters", [])}

    # Map intelligence guests to podcast index guests (fuzzy last name)
    def name_key(name: str) -> str:
        return re.sub(r"[-\s]+", " ", (name or "").lower()).strip()

    podcast_by_key = {name_key(g): g for g in podcast_guests}

    def match_podcast(canonical: str) -> str | None:
        if "(Newsletter)" in canonical:
            return None
        if canonical in podcast_guests:
            return canonical
        hit = podcast_by_key.get(name_key(canonical))
        if hit:
            return hit
        c_low = canonical.lower()
        for pg in podcast_guests:
            if pg.lower() in c_low or c_low in pg.lower():
                return pg
            cl = c_low.split()[-1] if c_low.split() else ""
            pl = pg.lower().split()[-1] if pg.split() else ""
            if cl and cl == pl and len(cl) > 3:
                return pg
        return None

    podcast_coverage: dict[str, dict] = {}
    podcast_counts: dict[str, int] = defaultdict(int)
    for g, c in by_guest.items():
        matched = match_podcast(g)
        if matched:
            podcast_counts[matched] += c

    for guest, meta in podcast_guests.items():
        podcast_coverage[guest] = {
            "objects": podcast_counts.get(guest, 0),
            "filename": meta["filename"],
            "date": meta.get("date"),
            "title": meta["title"],
        }

    uncovered_podcasts = [g for g, v in podcast_coverage.items() if v["objects"] == 0]

    newsletter_objects = sum(c for g, c in by_guest.items() if "(Newsletter)" in g)
    newsletter_authors = {g: c for g, c in by_guest.items() if "(Newsletter)" in g}

    return {
        "podcasts_total": len(podcast_guests),
        "podcasts_with_intelligence": len(podcast_guests) - len(uncovered_podcasts),
        "podcasts_uncovered": uncovered_podcasts,
        "podcast_by_guest": dict(sorted(podcast_counts.items(), key=lambda x: -x[1])),
        "newsletters_in_corpus": len(newsletter_titles),
        "newsletter_objects": newsletter_objects,
        "newsletter_by_author": dict(sorted(newsletter_authors.items(), key=lambda x: -x[1])),
        "top_guests_by_objects": dict(by_guest.most_common(15)),
    }


def main():
    items, sources, raw_count = load_all()
    index = json.loads((ROOT / "index.json").read_text())
    coverage = build_coverage(items, index)

    # Strip internal provenance for output (keep in separate manifest optional)
    intelligence = []
    for o in items:
        row = {k: o[k] for k in REQUIRED_FIELDS}
        intelligence.append(row)

    out = {
        "schema_version": "1.0",
        "product": "Reality Check",
        "description": "Operational intelligence layer for stress-testing startup/product advice against execution reality.",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "corpus": {
            "name": "Lenny's Podcast & Newsletter starter pack",
            "podcasts": len(index.get("podcasts", [])),
            "newsletters": len(index.get("newsletters", [])),
        },
        "merge_stats": {
            "source_files": sources,
            "raw_objects": raw_count,
            "deduplicated_objects": len(intelligence),
            "duplicates_removed": raw_count - len(intelligence),
        },
        "coverage": coverage,
        "intelligence": intelligence,
    }

    out_path = ROOT / "reality-check-intelligence.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")

    # Compact version for tooling
    compact_path = ROOT / "reality-check-intelligence.compact.json"
    compact_path.write_text(json.dumps(intelligence, ensure_ascii=False) + "\n")

    # Human-readable coverage report
    report_lines = [
        "# Reality Check — Corpus Coverage Report",
        "",
        f"Generated: {out['generated_at']}",
        "",
        "## Merge summary",
        "",
        f"- **Raw objects ingested:** {raw_count}",
        f"- **After deduplication:** {len(intelligence)}",
        f"- **Duplicates removed:** {raw_count - len(intelligence)}",
        "",
        "**Source files:**",
    ]
    for s in sources:
        report_lines.append(f"- `{s}`")
    report_lines.extend([
        "",
        "## Podcast coverage",
        "",
        f"- **Episodes in index:** {coverage['podcasts_total']}",
        f"- **Episodes with ≥1 intelligence object:** {coverage['podcasts_with_intelligence']}",
        "",
    ])
    if coverage["podcasts_uncovered"]:
        report_lines.append("**Uncovered episodes (0 objects after guest matching):**")
        for g in coverage["podcasts_uncovered"]:
            report_lines.append(f"- {g}")
        report_lines.append("")
    report_lines.append("| Guest | Objects |")
    report_lines.append("|-------|---------|")
    for guest, count in sorted(coverage["podcast_by_guest"].items(), key=lambda x: -x[1]):
        report_lines.append(f"| {guest} | {count} |")
    report_lines.extend([
        "",
        "## Newsletter coverage",
        "",
        f"- **Newsletter objects:** {coverage['newsletter_objects']}",
        "",
    ])
    for author, count in coverage["newsletter_by_author"].items():
        report_lines.append(f"- {author}: {count}")
    report_lines.extend([
        "",
        "## Output files",
        "",
        "- `reality-check-intelligence.json` — full bundle with metadata + coverage",
        "- `reality-check-intelligence.compact.json` — intelligence array only",
        "",
    ])
    (ROOT / "reality-check-coverage.md").write_text("\n".join(report_lines) + "\n")

    print(f"Wrote {out_path} ({len(intelligence)} objects)")
    print(f"Wrote {compact_path}")
    print(f"Wrote reality-check-coverage.md")
    print("Tip: run `python3 semantic_dedupe.py` for stricter semantic dedupe.")
    print(f"Raw: {raw_count} → Deduped: {len(intelligence)} (removed {raw_count - len(intelligence)})")
    print(f"Podcasts covered: {coverage['podcasts_with_intelligence']}/{coverage['podcasts_total']}")
    if coverage["podcasts_uncovered"]:
        print("Uncovered:", ", ".join(coverage["podcasts_uncovered"]))


if __name__ == "__main__":
    main()
