from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

FEEDBACK_PATH = Path(__file__).resolve().parents[1] / "data" / "feedback.jsonl"


def append_feedback(record: dict) -> None:
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    row = {
        **record,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with FEEDBACK_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
