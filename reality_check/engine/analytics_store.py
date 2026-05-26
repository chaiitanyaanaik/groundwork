from __future__ import annotations

import json
import os
import threading
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOCK = threading.Lock()
_ANALYTICS_FILE = Path(os.getenv("ANALYTICS_FILE", "analytics.jsonl"))
_FEEDBACK_FILE = Path(__file__).resolve().parents[1] / "data" / "feedback.jsonl"


def _analytics_path() -> Path:
    return _ANALYTICS_FILE


def append_event(event: str, properties: dict[str, Any] | None = None) -> None:
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "properties": properties or {},
    }
    line = json.dumps(record, ensure_ascii=False)
    with _LOCK:
        with open(_analytics_path(), "a", encoding="utf-8") as f:
            f.write(line + "\n")


def _read_events() -> list[dict]:
    path = _analytics_path()
    if not path.exists():
        return []
    events = []
    with _LOCK:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    return events


def _read_feedback() -> list[dict]:
    if not _FEEDBACK_FILE.exists():
        return []
    rows = []
    with open(_FEEDBACK_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return rows


def compute_summary() -> dict[str, Any]:
    events = _read_events()
    total = len(events)

    by_event: dict[str, int] = defaultdict(int)
    aspiration_selected: dict[str, int] = defaultdict(int)
    aspiration_completed: dict[str, int] = defaultdict(int)
    confidence_dist: dict[str, int] = defaultdict(int)
    daily_counts: dict[str, int] = defaultdict(int)

    for e in events:
        name = e.get("event", "unknown")
        by_event[name] += 1
        props = e.get("properties", {})

        if name == "aspiration_selected":
            aid = props.get("aspiration_id") or props.get("label") or "unknown"
            aspiration_selected[aid] += 1

        if name == "stress_test_completed":
            aid = props.get("aspiration_id") or "unknown"
            aspiration_completed[aid] += 1
            conf = props.get("confidence") or "unknown"
            confidence_dist[conf] += 1

        ts = e.get("ts", "")
        if ts:
            day = ts[:10]
            daily_counts[day] += 1

    submitted = by_event.get("stress_test_submitted", 0)
    completed = by_event.get("stress_test_completed", 0)
    completion_rate = round(completed / submitted * 100, 1) if submitted > 0 else 0

    sorted_daily = dict(sorted(daily_counts.items())[-14:])

    # Feedback
    feedback_rows = _read_feedback()
    thumbs_up = sum(1 for r in feedback_rows if r.get("rating") == "up")
    thumbs_down = sum(1 for r in feedback_rows if r.get("rating") == "down")
    total_feedback = len(feedback_rows)
    satisfaction_pct = round(thumbs_up / total_feedback * 100, 1) if total_feedback > 0 else None

    feedback_by_aspiration: dict[str, dict[str, int]] = defaultdict(lambda: {"up": 0, "down": 0})
    for r in feedback_rows:
        aid = r.get("aspiration_id") or "unknown"
        rating = r.get("rating")
        if rating in ("up", "down"):
            feedback_by_aspiration[aid][rating] += 1

    recent_comments = [
        {
            "rating": r.get("rating"),
            "comment": r.get("comment"),
            "aspiration_id": r.get("aspiration_id"),
            "transformation_name": (r.get("result_summary") or {}).get("transformation_name"),
            "created_at": r.get("created_at"),
        }
        for r in reversed(feedback_rows)
        if r.get("comment")
    ][:10]

    return {
        "total_events": total,
        "by_event": dict(sorted(by_event.items(), key=lambda x: -x[1])),
        "top_aspirations_selected": dict(
            sorted(aspiration_selected.items(), key=lambda x: -x[1])[:10]
        ),
        "top_aspirations_completed": dict(
            sorted(aspiration_completed.items(), key=lambda x: -x[1])[:10]
        ),
        "confidence_distribution": dict(confidence_dist),
        "completion_rate_pct": completion_rate,
        "stress_tests_submitted": submitted,
        "stress_tests_completed": completed,
        "daily_events_last_14d": sorted_daily,
        "feedback": {
            "total": total_feedback,
            "thumbs_up": thumbs_up,
            "thumbs_down": thumbs_down,
            "satisfaction_pct": satisfaction_pct,
            "by_aspiration": {k: dict(v) for k, v in feedback_by_aspiration.items()},
            "recent_comments": recent_comments,
        },
    }
