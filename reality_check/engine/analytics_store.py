from __future__ import annotations

import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import psycopg2
import psycopg2.extras


def _conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def append_event(event: str, properties: dict[str, Any] | None = None) -> None:
    try:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO analytics_events (event, properties) VALUES (%s, %s)",
                (event, json.dumps(properties or {})),
            )
    except Exception:
        pass


def compute_summary() -> dict[str, Any]:
    try:
        with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT event, properties, ts FROM analytics_events ORDER BY ts")
            events = list(cur)
    except Exception:
        events = []

    total = len(events)
    by_event: dict[str, int] = defaultdict(int)
    aspiration_selected: dict[str, int] = defaultdict(int)
    aspiration_completed: dict[str, int] = defaultdict(int)
    confidence_dist: dict[str, int] = defaultdict(int)
    daily_counts: dict[str, int] = defaultdict(int)

    for e in events:
        name = e["event"]
        by_event[name] += 1
        props = e["properties"] or {}

        if name == "aspiration_selected":
            aid = props.get("aspiration_id") or props.get("label") or "unknown"
            aspiration_selected[aid] += 1

        if name == "stress_test_completed":
            aid = props.get("aspiration_id") or "unknown"
            aspiration_completed[aid] += 1
            conf = props.get("confidence") or "unknown"
            confidence_dist[conf] += 1

        ts = e["ts"]
        if ts:
            day = ts.strftime("%Y-%m-%d") if hasattr(ts, "strftime") else str(ts)[:10]
            daily_counts[day] += 1

    submitted = by_event.get("stress_test_submitted", 0)
    completed = by_event.get("stress_test_completed", 0)
    completion_rate = round(completed / submitted * 100, 1) if submitted > 0 else 0
    sorted_daily = dict(sorted(daily_counts.items())[-14:])

    # Feedback
    try:
        with _conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT rating, comment, aspiration_id, result_summary, created_at "
                "FROM feedback ORDER BY created_at"
            )
            feedback_rows = list(cur)
    except Exception:
        feedback_rows = []

    thumbs_up = sum(1 for r in feedback_rows if r["rating"] == "up")
    thumbs_down = sum(1 for r in feedback_rows if r["rating"] == "down")
    total_feedback = len(feedback_rows)
    satisfaction_pct = round(thumbs_up / total_feedback * 100, 1) if total_feedback > 0 else None

    feedback_by_aspiration: dict[str, dict[str, int]] = defaultdict(lambda: {"up": 0, "down": 0})
    for r in feedback_rows:
        aid = r["aspiration_id"] or "unknown"
        rating = r["rating"]
        if rating in ("up", "down"):
            feedback_by_aspiration[aid][rating] += 1

    recent_comments = [
        {
            "rating": r["rating"],
            "comment": r["comment"],
            "aspiration_id": r["aspiration_id"],
            "transformation_name": (r["result_summary"] or {}).get("transformation_name"),
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
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
