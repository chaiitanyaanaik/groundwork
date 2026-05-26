from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

from reality_check.api.schemas import RealityCheckResponse
from reality_check.engine.calibration_bundle import role_label
from reality_check.engine.distortions import humanize_calibration_short
from reality_check.engine.loader import load_philosophy_questions, questions_by_id
from reality_check.engine.retrieval import RetrievalBundle

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

BOTTLENECK_PLAYBOOK_SUFFIX: dict[str, str] = {
    "move_fast": "speed and quality",
    "high_experimentation": "experiment throughput and learning",
    "empower_teams": "autonomy and alignment",
    "ai_first": "AI adoption and governance",
    "founder_mode": "founder leverage and team throughput",
    "ai_native_pms": "builder PM capacity and coordination",
    "design_led": "cohesion and ship velocity",
    "minimal_process": "lightweight decisions and clarity",
    "product_led_growth": "product loops and GTM pull",
    "influence_without_politics": "decision speed and buy-in",
    "high_performance_culture": "standards and psychological safety",
    "lean_constraints": "leverage and headcount discipline",
    "bottom_up_ai": "grassroots adoption and scale",
    "evals_first_ai": "AI quality and ship velocity",
    "platform_org": "platform leverage and GM autonomy",
}


def _lc(fragment: str) -> str:
    s = fragment.strip().rstrip(".")
    if not s:
        return s
    return s[0].lower() + s[1:] if len(s) > 1 else s.lower()


def _is_short_fragment(text: str, min_words: int = 8) -> bool:
    return len(text.split()) < min_words


@lru_cache(maxsize=1)
def load_role_playbooks() -> dict:
    path = _DATA_DIR / "role_playbooks.json"
    with open(path) as f:
        return json.load(f)


def _want_phrase(bundle: RetrievalBundle) -> str:
    if bundle.aspiration:
        label = (bundle.aspiration.get("label") or "").strip()
        if label:
            if label.lower().startswith("you "):
                return label if label.endswith(".") else f"{label}."
            return f"You want to {label[0].lower()}{label[1:]}." if len(label) > 1 else f"You want {label.lower()}."
        raw = bundle.aspiration.get("user_facing_hook") or bundle.aspiration.get("emotional_subtitle", "")
    else:
        raw = bundle.philosophy.get("user_facing_hook", "")
    if not raw:
        label = bundle.philosophy.get("label", "this change")
        return f"You want {label.lower()}."
    text = raw.strip()
    if text.lower().startswith("you "):
        return text if text.endswith(".") else f"{text}."
    text = re.sub(r"^We want", "You want", text, flags=re.IGNORECASE)
    text = re.sub(r"^we want", "you want", text)
    return text if text.endswith(".") else f"{text}."


def split_calibration_labels(bundle: RetrievalBundle) -> tuple[list[str], list[str]]:
    """Universal org answers vs philosophy-specific calibration labels."""
    cal = bundle.org_summary.get("calibration") or {}
    pq = load_philosophy_questions()
    universal_ids = set(pq.get("universal_question_ids", []))
    for cond in pq.get("conditional_questions", []):
        universal_ids.add(cond["question_id"])
    phil_id = bundle.philosophy.get("id")
    specific_qid = pq.get("philosophy_question_ids", {}).get(phil_id)

    qmap = questions_by_id()
    universal: list[str] = []
    specific: list[str] = []
    for qid, option_id in cal.items():
        q = qmap.get(qid)
        if not q:
            continue
        opt = next((o for o in q["options"] if o["id"] == option_id), None)
        if not opt:
            continue
        label = opt["label"].strip()
        if qid == specific_qid:
            specific.append(label)
        elif qid in universal_ids:
            universal.append(label)
    return universal, specific


def build_headline(bundle: RetrievalBundle) -> str:
    want = _want_phrase(bundle).rstrip(".")
    universal, specific = split_calibration_labels(bundle)
    profiles = bundle.distortion_profiles
    collapse = ""
    if profiles:
        collapse = (profiles[0].get("collapse_pattern") or profiles[0].get("label") or "").strip()
    collapse_low = _lc(collapse) if collapse else ""

    if specific and universal:
        spec = specific[0]
        context = universal[0]
        if len(universal) > 1:
            context = f"{context}, {universal[1]}"
        if collapse_low:
            return f"{want}, but {spec} — and with {context}, you often see {collapse_low}."
        return f"{want}, but {spec} — and your org also runs with {context}."

    if specific:
        if collapse_low:
            return f"{want}, but {specific[0]} — under pressure you often see {collapse_low}."
        return f"{want}, but {specific[0]} will shape how this plays out under pressure."

    pressure_parts = universal[:3]
    if collapse_low and pressure_parts:
        joined = ", ".join(pressure_parts[:2])
        if len(pressure_parts) > 2:
            joined += f", and {pressure_parts[2]}"
        return f"{want}, but with {joined} — and under pressure you often see {collapse_low}."

    if pressure_parts:
        joined = " and ".join(pressure_parts[:2])
        return f"{want}, but your answers ({joined}) will shape how that plays out day to day."

    return f"{want}, but operational pressure may contradict the aspiration before new habits stick."


def _format_playbook_line(template: str, cal_short: list[str], phil_l: str) -> str:
    ctx = {
        "phil": phil_l,
        "c0": cal_short[0] if cal_short else "your top constraint",
        "c1": cal_short[1] if len(cal_short) > 1 else "priorities shift under pressure",
        "c2": cal_short[2] if len(cal_short) > 2 else cal_short[-1] if cal_short else "pressure rises",
    }
    return template.format(**ctx)


def role_start_with(bundle: RetrievalBundle, cal_short: list[str]) -> list[str]:
    role = bundle.org_summary.get("user_role") or "other_leader"
    pid = bundle.philosophy.get("id", "custom")
    phil = (
        bundle.aspiration.get("label", bundle.philosophy.get("label", "this change"))
        if bundle.aspiration
        else bundle.philosophy.get("label", "this change")
    )
    phil_l = phil.lower()

    playbooks = load_role_playbooks()
    role_map = playbooks.get(pid, {})
    templates = role_map.get(role) or role_map.get("pm_product_lead") or role_map.get("other_leader")
    if templates:
        return [_format_playbook_line(t, cal_short, phil_l) for t in templates[:3]]

    return [
        f"Name what {phil_l} changes for the next 30 days given {cal_short[0] if cal_short else 'your constraints'}.",
        "Define one lightweight decision rule for what must hold under pressure.",
        "Assign a single owner for review and escalation instead of creating a committee.",
    ]


def enrich_bottleneck_block(
    block: dict[str, str],
    bundle: RetrievalBundle,
    collapse: str,
) -> dict[str, str]:
    b = (block.get("bottleneck") or "").strip()
    n = (block.get("what_teams_usually_do_next") or "").strip()
    e = (block.get("unintended_effect") or "").strip()
    phil = (bundle.philosophy.get("label") or "this change").lower()
    pid = bundle.philosophy.get("id", "")
    _, specific = split_calibration_labels(bundle)
    context = specific[0] if specific else (humanize_calibration_short(bundle.org_summary.get("calibration") or {}) or ["under pressure"])[0]
    playbook = BOTTLENECK_PLAYBOOK_SUFFIX.get(pid, "the change you want")

    if n.lower().startswith("emphasize "):
        n = re.sub(r"^emphasize\s+", "", n, flags=re.IGNORECASE).strip()

    if not (_is_short_fragment(b) or _is_short_fragment(n) or _is_short_fragment(e)):
        if n.lower().startswith("teams often respond with emphasize"):
            n = n.replace("emphasize ", "", 1)
        return block

    failure = _lc(b) if b else _lc(collapse) or "operational drift"
    response = _lc(n) if n else "familiar workarounds that protect this week's delivery"
    effect = _lc(e) if e else "the original intent erodes while everyone feels responsible"

    return {
        "bottleneck": (
            f"While pursuing {phil}, teams operating with {context} often hit {failure} "
            f"before there is a shared playbook for {playbook}."
        ),
        "what_teams_usually_do_next": (
            f"Teams often respond by {response}, which feels like responsible progress in the moment."
        ),
        "unintended_effect": (
            f"That frequently undermines {phil}: {effect}, without anyone explicitly choosing it."
        ),
    }


def build_your_version(bundle: RetrievalBundle, data: dict) -> dict:
    phil = data.get("philosophy_label") or bundle.philosophy.get("label", "this change")
    org = bundle.org_summary
    stage = org.get("stage") or "your"
    size = org.get("size") or ""
    model = org.get("model") or ""
    org_bits = " ".join(x for x in (stage, size, model) if x).strip() or "your org"

    readiness = data.get("environment_readiness") or {}
    works = data.get("where_this_works_best") or {}
    drive = data.get("how_to_drive_change") or {}
    measure = data.get("what_to_measure") or {}
    resistance = data.get("likely_resistance") or {}
    correction = data.get("when_to_course_correct") or {}

    keep = _unique(
        list(readiness.get("supporting_conditions") or [])[:2]
        + list(works.get("conditions") or [])[:2],
        4,
    )
    modify = _unique(list(drive.get("introduce_later") or [])[:3], 3)
    typical = (correction.get("typical_adaptation") or "").strip()
    if typical and typical not in modify:
        modify = [typical, *modify][:3]

    add = list(drive.get("start_with") or [])[:3]
    watch_for = _unique(
        list(measure.get("warning_signs") or [])[:3]
        + list(resistance.get("patterns") or [])[:2],
        5,
    )

    if not keep:
        keep = [f"The core intent behind {phil.lower()} still matters in {org_bits}."]
    if not modify:
        modify = [f"Constrain {phil.lower()} when executive pressure spikes — do not apply it uniformly."]
    if not add:
        add = [f"Name one behavior that must change in the next 30 days for {phil.lower()}."]
    if not watch_for:
        watch_for = [f"Workarounds that preserve this week but erode {phil.lower()} over a quarter."]

    return {
        "title": f"Your version of {phil} in a {org_bits} org",
        "keep": keep,
        "modify": modify,
        "add": add,
        "watch_for": watch_for,
    }


def _unique(items: list[str], limit: int) -> list[str]:
    return [item for item in dict.fromkeys(items) if item][:limit]


def _dedupe_across_sections(data: dict) -> None:
    later = {x.strip().lower() for x in (data.get("how_to_drive_change") or {}).get("introduce_later", [])}
    measure = data.setdefault("what_to_measure", {})
    if isinstance(measure, dict):
        pos = measure.get("positive_signals") or []
        measure["positive_signals"] = [x for x in pos if x.strip().lower() not in later]

    seen: set[str] = set()
    for key in ("introduce_later", "positive_signals", "warning_signs"):
        container = data.get("how_to_drive_change") if key == "introduce_later" else measure
        if key != "introduce_later":
            container = measure
        if not isinstance(container, dict):
            continue
        field = "introduce_later" if key == "introduce_later" else key
        items = container.get(field) or []
        deduped = []
        for item in items:
            norm = item.strip().lower()
            if norm in seen:
                continue
            seen.add(norm)
            deduped.append(item)
        container[field] = deduped


def _ensure_insight(insight: str, phil_truth: str, bundle: RetrievalBundle) -> str:
    insight = (insight or "").strip()
    truth = (phil_truth or "").strip()
    operational = ""
    if bundle.aspiration:
        operational = (bundle.aspiration.get("operational_truth") or "").strip()
    if not operational:
        operational = truth

    if insight and insight not in {truth, operational}:
        return insight

    profiles = bundle.distortion_profiles
    collapse = profiles[0].get("collapse_pattern") if profiles else ""
    phil = bundle.philosophy.get("label", "this philosophy")
    role = role_label(bundle.org_summary.get("user_role"))
    _, specific = split_calibration_labels(bundle)
    spec_clause = f" when {specific[0].lower()}" if specific else ""
    if collapse:
        return (
            f"For a {role}, {phil.lower()} fails in execution when {_lc(collapse)}{spec_clause} — "
            "not because the aspiration is wrong."
        )
    return (
        f"Pressure changes behavior faster than {phil.lower()} can reshape systems — "
        "the gap is operational, not intent."
    )


def enrich_response(
    bundle: RetrievalBundle,
    response: RealityCheckResponse,
    *,
    synthesis_path: str | None = None,
) -> RealityCheckResponse:
    data = response.model_dump()
    cal_short = humanize_calibration_short(bundle.org_summary.get("calibration") or {})
    phil_truth = bundle.philosophy.get("operational_truth", "")

    universal, specific = split_calibration_labels(bundle)
    headline = (data.get("headline") or "").strip()
    if specific or not headline or " but " not in headline.lower():
        data["headline"] = build_headline(bundle)
    elif specific and specific[0].lower() not in headline.lower():
        data["headline"] = build_headline(bundle)

    collapse = ""
    if bundle.distortion_profiles:
        collapse = bundle.distortion_profiles[0].get("collapse_pattern") or ""

    bottleneck = data.get("first_bottleneck") or {}
    if isinstance(bottleneck, dict):
        data["first_bottleneck"] = enrich_bottleneck_block(bottleneck, bundle, collapse)

    readiness = data.setdefault("environment_readiness", {})
    if isinstance(readiness, dict):
        hook = data.get("what_youre_trying_to_change", {}).get("goal", "")
        org = bundle.org_summary
        stage, size, model = org.get("stage"), org.get("size"), org.get("model")
        role = role_label(org.get("user_role"))
        phil = data.get("philosophy_label", "this change")
        supporting = [
            f"Clear intent: {hook}" if hook else f"Explicit pursuit of {phil.lower()}.",
        ]
        if stage and size and model:
            supporting.append(
                f"Org context ({stage}, {size}, {model}) is known enough to tailor the operating model."
            )
        supporting.append(
            f"As {role}, you can influence how {phil.lower()} shows up in weekly decisions."
        )
        resisting = list(readiness.get("resisting_conditions") or [])
        cleaned_resist: list[str] = []
        for line in resisting:
            if line.startswith("Your answers point to"):
                cleaned_resist.append(line)
            elif line.count(":") >= 2 and "Friction:" not in line:
                cleaned_resist.append(f"Friction: {cal_short[0]}." if cal_short else line)
            else:
                cleaned_resist.append(line)
        for label in specific[:2]:
            entry = f"Philosophy friction: {label}."
            if entry not in cleaned_resist:
                cleaned_resist.append(entry)
        for label in universal[1:3]:
            entry = f"Friction: {label}."
            if entry not in cleaned_resist:
                cleaned_resist.append(entry)
        readiness["supporting_conditions"] = supporting[:3]
        readiness["resisting_conditions"] = cleaned_resist[:5]

        summary_parts = specific + universal[:2]
        parts_text = ", ".join(summary_parts) if summary_parts else "your calibration answers"
        readiness["readiness_summary"] = (
            f"The environment is not simply ready or unready. Intent is real, but {parts_text} "
            f"will shape how {phil.lower()} behaves when stakes rise."
        )

    drive = data.setdefault("how_to_drive_change", {})
    if isinstance(drive, dict):
        generic_markers = (
            "using your calibration answer:",
            "Who usually overrides",
        )
        move_fast_leak = ("blast-radius tiers", "eng-led preview")
        start = drive.get("start_with") or []
        pid = bundle.philosophy.get("id", "")
        playbooks = load_role_playbooks()
        wrong_template = pid != "move_fast" and any(
            any(leak in s.lower() for leak in move_fast_leak) for s in start
        )
        if pid in playbooks and (
            not start
            or any(any(m in s for m in generic_markers) for s in start)
            or wrong_template
        ):
            drive["start_with"] = role_start_with(bundle, cal_short)

    data["core_organizational_insight"] = _ensure_insight(
        data.get("core_organizational_insight", ""),
        phil_truth,
        bundle,
    )

    if not data.get("contradicting_philosophies"):
        data["contradicting_philosophies"] = [
            p.get("label", "") for p in bundle.contradicting_philosophies
        ]

    _dedupe_across_sections(data)
    data["your_version"] = build_your_version(bundle, data)
    if synthesis_path:
        data["synthesis_path"] = synthesis_path
    return RealityCheckResponse.model_validate(data)
