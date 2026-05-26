#!/usr/bin/env python3
"""
Stricter semantic deduplication for Reality Check intelligence objects.

Signals (union-find):
  A) Exact normalized pattern_name
  B) core_belief SequenceMatcher >= BELIEF_MERGE (0.85)
  C) Operational fingerprint Jaccard >= JACCARD_MERGE (0.62) AND belief >= 0.70
  D) pattern_name SequenceMatcher >= 0.90 AND same category

Conservative: cross-guest merges only when B or (C with belief >= 0.82).
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).parent
INPUT = ROOT / "reality-check-intelligence.json"
OUTPUT = ROOT / "reality-check-intelligence.json"
REPORT = ROOT / "semantic-dedupe-report.md"
COMPACT = ROOT / "reality-check-intelligence.compact.json"

BELIEF_MERGE = 0.85
JACCARD_MERGE = 0.62
JACCARD_BELIEF_FLOOR = 0.70
CROSS_GUEST_BELIEF = 0.82
RELATED_JACCARD = 0.48  # link only, no merge


def norm_name(s: str) -> str:
    return re.sub(r"[^\w\s]", "", (s or "").lower()).strip()


def norm_text(s: str) -> str:
    s = re.sub(r"[^\w\s]", " ", (s or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def tokens(s: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{4,}", (s or "").lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def fingerprint(obj: dict) -> set[str]:
    parts: list[str] = []
    for k in (
        "pattern_name",
        "core_belief",
        "operational_pattern",
        "organizational_archetype",
        "source_quote_or_context",
        "category",
    ):
        parts.append(str(obj.get(k, "")))
    for k in (
        "hidden_assumptions",
        "pressure_scenarios",
        "failure_modes",
        "contradictions",
        "behavioral_signals",
        "emotional_political_dynamics",
        "operational_adaptations",
        "ai_era_implications",
    ):
        v = obj.get(k, [])
        if isinstance(v, list):
            parts.extend(str(x) for x in v)
    return tokens(" ".join(parts))


def richness(obj: dict) -> int:
    n = 0
    for v in obj.values():
        if isinstance(v, str):
            n += len(v)
        elif isinstance(v, list):
            n += sum(len(str(x)) for x in v)
    return n


class UnionFind:
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, x: int) -> int:
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[rb] = ra


def merge_list_fields(canonical: dict, other: dict) -> None:
    """Union list fields from duplicate into canonical (deduped strings)."""
    list_fields = (
        "hidden_assumptions",
        "pressure_scenarios",
        "failure_modes",
        "contradictions",
        "behavioral_signals",
        "emotional_political_dynamics",
        "operational_adaptations",
        "ai_era_implications",
    )
    for k in list_fields:
        seen = {norm_text(x) for x in canonical.get(k, [])}
        merged = list(canonical.get(k, []))
        for item in other.get(k, []):
            if norm_text(item) not in seen:
                merged.append(item)
                seen.add(norm_text(item))
        canonical[k] = merged


def main() -> None:
    bundle = json.loads(INPUT.read_text())
    items: list[dict] = bundle["intelligence"]
    n = len(items)

    for i, obj in enumerate(items):
        obj["intelligence_id"] = f"rc_{i:04d}"

    uf = UnionFind(n)
    merge_reasons: list[tuple[str, int, int, float, str]] = []

    fps = [fingerprint(o) for o in items]
    beliefs = [norm_text(o.get("core_belief", "")) for o in items]
    names = [norm_name(o.get("pattern_name", "")) for o in items]
    categories = [norm_text(o.get("category", "")) for o in items]

    def record(reason: str, i: int, j: int, score: float) -> None:
        uf.union(i, j)
        merge_reasons.append((reason, i, j, score, items[i]["pattern_name"]))

    # A: exact pattern name
    by_name: dict[str, list[int]] = defaultdict(list)
    for i, name in enumerate(names):
        if name:
            by_name[name].append(i)
    for indices in by_name.values():
        for a in range(1, len(indices)):
            record("exact_pattern_name", indices[0], indices[a], 1.0)

    # B, C, D: pairwise (n=462 manageable)
    for i in range(n):
        for j in range(i + 1, n):
            if uf.find(i) == uf.find(j):
                continue

            b_sim = SequenceMatcher(None, beliefs[i], beliefs[j]).ratio() if beliefs[i] and beliefs[j] else 0
            j_sim = jaccard(fps[i], fps[j])
            n_sim = SequenceMatcher(None, names[i], names[j]).ratio() if names[i] and names[j] else 0
            same_guest = items[i]["source_guest"] == items[j]["source_guest"]
            same_cat = categories[i] == categories[j] and categories[i] != ""

            if b_sim >= BELIEF_MERGE:
                if same_guest or b_sim >= CROSS_GUEST_BELIEF:
                    record("core_belief", i, j, b_sim)
                    continue

            if j_sim >= JACCARD_MERGE and b_sim >= JACCARD_BELIEF_FLOOR:
                if same_guest or b_sim >= CROSS_GUEST_BELIEF:
                    record("fingerprint_jaccard", i, j, j_sim)
                    continue

            if n_sim >= 0.90 and same_cat and (same_guest or b_sim >= 0.75):
                record("pattern_name_category", i, j, n_sim)

    # Cluster
    clusters: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        clusters[uf.find(i)].append(i)

    # Related links (no merge)
    related: dict[str, list[str]] = defaultdict(list)
    for i in range(n):
        for j in range(i + 1, n):
            if uf.find(i) == uf.find(j):
                continue
            j_sim = jaccard(fps[i], fps[j])
            if j_sim >= RELATED_JACCARD:
                b_sim = SequenceMatcher(None, beliefs[i], beliefs[j]).ratio()
                if 0.45 <= j_sim < JACCARD_MERGE or (j_sim >= JACCARD_MERGE and b_sim < JACCARD_BELIEF_FLOOR):
                    related[items[i]["intelligence_id"]].append(items[j]["intelligence_id"])
                    related[items[j]["intelligence_id"]].append(items[i]["intelligence_id"])

    deduped: list[dict] = []
    merge_log: list[dict] = []

    for _root, members in sorted(clusters.items(), key=lambda x: -len(x[1])):
        members_sorted = sorted(members, key=lambda i: -richness(items[i]))
        canonical = dict(items[members_sorted[0]])
        merged_sources = []

        for idx in members_sorted[1:]:
            dup = items[idx]
            merged_sources.append({
                "intelligence_id": dup["intelligence_id"],
                "pattern_name": dup["pattern_name"],
                "source_guest": dup["source_guest"],
                "source_episode": dup["source_episode"],
            })
            merge_list_fields(canonical, dup)
            # Prefer longer quote if canonical is short
            if len(str(dup.get("source_quote_or_context", ""))) > len(
                str(canonical.get("source_quote_or_context", ""))
            ):
                canonical["source_quote_or_context"] = dup["source_quote_or_context"]

        if merged_sources:
            canonical["semantic_cluster_id"] = canonical["intelligence_id"]
            canonical["merged_sources"] = merged_sources
            canonical["dedupe_merged_count"] = len(merged_sources)
            merge_log.append({
                "canonical_id": canonical["intelligence_id"],
                "pattern_name": canonical["pattern_name"],
                "source_guest": canonical["source_guest"],
                "merged_count": len(merged_sources),
                "merged": merged_sources,
            })
        else:
            canonical.pop("semantic_cluster_id", None)
            canonical.pop("merged_sources", None)
            canonical.pop("dedupe_merged_count", None)

        rel_ids = set()
        for mid in members:
            rel_ids.update(related.get(items[mid]["intelligence_id"], []))
        # Remove self-cluster and merged-away ids
        cluster_ids = {items[m]["intelligence_id"] for m in members}
        rel_ids -= cluster_ids
        if rel_ids:
            canonical["related_intelligence_ids"] = sorted(rel_ids)

        deduped.append(canonical)

    deduped.sort(key=lambda o: (o["source_guest"].lower(), o["pattern_name"].lower()))

    # Re-assign sequential ids after dedupe
    id_map = {}
    for i, obj in enumerate(deduped):
        old_id = obj["intelligence_id"]
        new_id = f"rc_{i:04d}"
        id_map[old_id] = new_id
        obj["intelligence_id"] = new_id

    def remap_ids(obj: dict) -> None:
        if "merged_sources" in obj:
            for m in obj["merged_sources"]:
                m["canonical_id"] = obj["intelligence_id"]
        if "related_intelligence_ids" in obj:
            obj["related_intelligence_ids"] = sorted(
                id_map.get(rid, rid) for rid in obj["related_intelligence_ids"]
            )

    for obj in deduped:
        remap_ids(obj)

    removed = n - len(deduped)
    stats = bundle.get("merge_stats", {})
    bundle["semantic_dedupe"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rules": {
            "exact_pattern_name": True,
            "belief_merge_threshold": BELIEF_MERGE,
            "jaccard_merge_threshold": JACCARD_MERGE,
            "cross_guest_belief_floor": CROSS_GUEST_BELIEF,
            "related_link_jaccard_floor": RELATED_JACCARD,
        },
        "before_count": n,
        "after_count": len(deduped),
        "removed_count": removed,
        "clusters_merged": len(merge_log),
        "merge_log": merge_log,
        "pairwise_merge_events": len(merge_reasons),
    }
    bundle["merge_stats"]["semantic_dedupe_removed"] = removed
    bundle["merge_stats"]["deduplicated_objects"] = len(deduped)
    bundle["intelligence"] = deduped
    bundle["generated_at"] = datetime.now(timezone.utc).isoformat()

    OUTPUT.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n")
    COMPACT.write_text(json.dumps(deduped, ensure_ascii=False) + "\n")

    lines = [
        "# Semantic dedupe report",
        "",
        f"Generated: {bundle['semantic_dedupe']['generated_at']}",
        "",
        "## Summary",
        "",
        f"- **Before:** {n} objects",
        f"- **After:** {len(deduped)} objects",
        f"- **Removed:** {removed} near-duplicates merged into canonical records",
        f"- **Merge clusters:** {len(merge_log)}",
        "",
        "## Rules applied",
        "",
        f"1. Exact normalized `pattern_name` → merge",
        f"2. `core_belief` similarity ≥ {BELIEF_MERGE} (cross-guest requires ≥ {CROSS_GUEST_BELIEF})",
        f"3. Fingerprint Jaccard ≥ {JACCARD_MERGE} with belief ≥ {JACCARD_BELIEF_FLOOR}",
        f"4. `pattern_name` similarity ≥ 0.90 within same category",
        f"5. Related-only link (no merge) when Jaccard ≥ {RELATED_JACCARD} but below merge thresholds",
        "",
        "Canonical records retain the richest object; list fields are unioned; "
        "`merged_sources` lists absorbed duplicates.",
        "",
        "## Merge clusters",
        "",
    ]
    if not merge_log:
        lines.append("_No clusters merged at current thresholds._")
    else:
        for entry in merge_log:
            lines.append(f"### {entry['pattern_name']} ({entry['source_guest']})")
            lines.append("")
            lines.append(f"- **Canonical ID:** `{entry['canonical_id']}`")
            lines.append(f"- **Merged:** {entry['merged_count']} object(s)")
            lines.append("")
            for m in entry["merged"]:
                lines.append(
                    f"- `{m['intelligence_id']}` — {m['pattern_name']} ({m['source_guest']})"
                )
            lines.append("")

    lines.extend([
        "",
        "## Notes",
        "",
        "The starter-pack corpus was already sparse on lexical duplicates (batches used distinct `pattern_name` labels). "
        "Most merges are newsletter cross-author duplicates and cross-episode thematic overlap "
        "(e.g. societal adoption constraints in consumer AI).",
        "",
        "Re-run: `python3 semantic_dedupe.py`",
        "",
    ])
    REPORT.write_text("\n".join(lines) + "\n")

    print(f"Semantic dedupe: {n} → {len(deduped)} (removed {removed})")
    print(f"Merge clusters: {len(merge_log)}")
    print(f"Wrote {OUTPUT}, {COMPACT}, {REPORT}")


if __name__ == "__main__":
    main()
