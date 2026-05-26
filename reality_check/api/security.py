from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request

from reality_check.config import settings

_RATE_BUCKETS: dict[str, deque[float]] = defaultdict(deque)
_RATE_LOCK = Lock()


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def check_rate_limit(request: Request, bucket: str, limit_per_minute: int) -> None:
    if not settings.rate_limit_enabled or limit_per_minute <= 0:
        return

    key = f"{bucket}:{client_ip(request)}"
    now = time.monotonic()
    window = 60.0

    with _RATE_LOCK:
        hits = _RATE_BUCKETS[key]
        while hits and now - hits[0] > window:
            hits.popleft()
        if len(hits) >= limit_per_minute:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please wait a minute and try again.",
            )
        hits.append(now)


def verify_stress_test_api_key(request: Request) -> None:
    expected = settings.stress_test_api_key.strip()
    if not expected:
        return
    provided = request.headers.get("X-Reality-Check-Key", "").strip()
    if provided != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def require_feedback_enabled() -> None:
    if not settings.feedback_enabled:
        raise HTTPException(status_code=503, detail="Feedback is disabled")
