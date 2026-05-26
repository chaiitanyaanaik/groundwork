from __future__ import annotations

from reality_check.engine.retrieval import RetrievalBundle


def validate_response_data(data: dict, bundle: RetrievalBundle) -> list[str]:
    """Return issue codes; empty list means output passes quality gates."""
    issues: list[str] = []
    blob = str(data)

    headline = (data.get("headline") or "").strip()
    if not headline or " but " not in headline.lower():
        issues.append("headline_missing_but")

    if "Who usually overrides" in blob or "using your calibration answer" in blob:
        issues.append("calibration_debug_leak")

    bn = data.get("first_bottleneck") or {}
    if isinstance(bn, dict):
        for field in ("bottleneck", "what_teams_usually_do_next", "unintended_effect"):
            text = (bn.get(field) or "").strip()
            if len(text.split()) < 8:
                issues.append(f"bottleneck_{field}_short")

    truth = (bundle.philosophy.get("operational_truth") or "").strip()
    aspiration_truth = ""
    if bundle.aspiration:
        aspiration_truth = (bundle.aspiration.get("operational_truth") or "").strip()
    insight = (data.get("core_organizational_insight") or "").strip()
    if insight and insight in {truth, aspiration_truth}:
        issues.append("insight_equals_card")

    allowed_ids = {o.get("intelligence_id") for o in bundle.intelligence_objects if o.get("intelligence_id")}
    sources = data.get("sources") or []
    if allowed_ids and not sources:
        issues.append("missing_sources")
    for source in sources:
        if not isinstance(source, dict):
            continue
        sid = source.get("intelligence_id")
        if sid and allowed_ids and sid not in allowed_ids:
            issues.append("invalid_source_id")
            break

    drive = data.get("how_to_drive_change") or {}
    start = drive.get("start_with") or [] if isinstance(drive, dict) else []
    pid = bundle.philosophy.get("id", "")
    if pid and pid != "move_fast" and start:
        joined = " ".join(start).lower()
        if "blast-radius tiers" in joined and "eng-led preview" in joined:
            issues.append("wrong_philosophy_playbook")

    return issues
