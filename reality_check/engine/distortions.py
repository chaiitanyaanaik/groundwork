from __future__ import annotations

from reality_check.engine.loader import load_calibration, questions_by_id


def collect_calibration_tags(calibration: dict[str, str]) -> set[str]:
    """Map question answers to internal search tags."""
    cal_data = load_calibration()
    option_tags = cal_data.get("option_tags", {})
    tags: set[str] = set()
    for option_id in calibration.values():
        tags.add(option_id)
        tags.update(option_tags.get(option_id, []))
    return tags


def resolve_distortion_profiles(calibration: dict[str, str]) -> list[dict]:
    """Return matched distortion profiles for org reality mapping."""
    cal_data = load_calibration()
    selected = set(calibration.values())
    profiles = []
    for profile in cal_data.get("distortion_profiles", []):
        required = set(profile.get("required_tags", []))
        boost = set(profile.get("boost_tags", []))
        if required and not required.issubset(selected):
            continue
        score = len(required) * 2 + len(boost & selected)
        if score <= 0:
            continue
        profiles.append({**profile, "match_score": score})
    profiles.sort(key=lambda p: -p["match_score"])
    return profiles[:3]


def humanize_calibration(calibration: dict[str, str]) -> list[str]:
    """User-facing labels for calibration answers (for LLM context)."""
    questions = questions_by_id()
    lines = []
    for qid, option_id in calibration.items():
        q = questions.get(qid)
        if not q:
            continue
        opt = next((o for o in q["options"] if o["id"] == option_id), None)
        if opt:
            lines.append(f"{q['prompt']}: {opt['label']}")
    return lines


def humanize_calibration_short(calibration: dict[str, str]) -> list[str]:
    """Short option labels only — for user-facing copy (no question prompts)."""
    questions = questions_by_id()
    lines: list[str] = []
    for qid, option_id in calibration.items():
        q = questions.get(qid)
        if not q:
            continue
        opt = next((o for o in q["options"] if o["id"] == option_id), None)
        if opt:
            lines.append(opt["label"])
    return lines
