from __future__ import annotations

import json
import os

import psycopg2


def _conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def append_feedback(record: dict) -> None:
    result_summary = record.get("result_summary")
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO feedback (rating, comment, aspiration_id, result_summary)
            VALUES (%s, %s, %s, %s)
            """,
            (
                record.get("rating"),
                record.get("comment"),
                record.get("aspiration_id"),
                json.dumps(result_summary) if result_summary else None,
            ),
        )
