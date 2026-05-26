from __future__ import annotations

import asyncio

import pytest

from reality_check.config import settings
from reality_check.engine.retrieval import retrieve
from reality_check.engine.synthesis import synthesize
from tests.test_api import FIXTURE_ORG_EMPOWER


def test_synthesize_timeout_returns_fallback(monkeypatch):
    monkeypatch.setattr(settings, "reality_check_skip_llm", False)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_timeout_seconds", 0.01)

    async def slow(*_args, **_kwargs):
        await asyncio.sleep(1)
        raise AssertionError("should not complete")

    monkeypatch.setattr("reality_check.engine.synthesis._call_openai", slow)

    bundle = retrieve("empower_teams", FIXTURE_ORG_EMPOWER)
    result = asyncio.run(synthesize(bundle))
    assert result.transformation_name
    assert result.gap_notice and "longer than expected" in result.gap_notice
