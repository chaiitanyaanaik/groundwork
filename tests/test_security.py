from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from reality_check.config import settings


@pytest.fixture
def prod_client(monkeypatch):
    from reality_check.api.main import app

    monkeypatch.setenv("REALITY_CHECK_ENV", "production")
    monkeypatch.setenv("REALITY_CHECK_ENABLE_DOCS", "0")
    monkeypatch.setattr(settings, "reality_check_env", "production")
    monkeypatch.setattr(settings, "reality_check_enable_docs", False)
    monkeypatch.setattr(settings, "reality_check_expose_health_details", False)
    return TestClient(app)


def test_production_hides_api_docs(prod_client, monkeypatch):
    monkeypatch.setattr(settings, "reality_check_enable_docs", False)
    assert prod_client.get("/docs").status_code == 404
    assert prod_client.get("/openapi.json").status_code == 404


def test_production_health_hides_llm_flag(prod_client):
    r = prod_client.get("/api/health")
    assert r.status_code == 200
    assert "llm_configured" not in r.json()


def test_custom_philosophy_max_length():
    from reality_check.api.main import app

    client = TestClient(app)
    r = client.post(
        "/api/stress-test/preview",
        json={
            "custom_philosophy": "x" * 501,
            "org_profile": {"calibration": {}},
        },
    )
    assert r.status_code == 422


def test_stress_test_requires_api_key_when_configured(monkeypatch):
    from reality_check.api.main import app

    monkeypatch.setattr(settings, "reality_check_stress_test_api_key", "secret-key")
    client = TestClient(app)
    body = {
        "aspiration_id": "cross_functional_alignment",
        "org_profile": {
            "stage": "scaleup",
            "calibration": {
                "roadmap_override": "exec_override",
                "priority_chaos": "chaos_monthly",
                "revenue_pressure": "recentralize",
                "bottleneck": "design_gate",
            },
        },
    }
    denied = client.post("/api/stress-test/preview", json=body)
    assert denied.status_code == 401

    allowed = client.post(
        "/api/stress-test/preview",
        json=body,
        headers={"X-Reality-Check-Key": "secret-key"},
    )
    assert allowed.status_code == 200


def test_rate_limit_stress_test(monkeypatch):
    from reality_check.api import security
    from reality_check.api.main import app

    monkeypatch.setattr(settings, "reality_check_env", "production")
    monkeypatch.setattr(settings, "reality_check_rate_limit_enabled", True)
    monkeypatch.setattr(settings, "reality_check_rate_limit_preview", 2)
    security._RATE_BUCKETS.clear()

    client = TestClient(app)
    body = {
        "aspiration_id": "cross_functional_alignment",
        "org_profile": {
            "calibration": {
                "roadmap_override": "exec_override",
                "priority_chaos": "chaos_monthly",
                "revenue_pressure": "recentralize",
                "bottleneck": "design_gate",
            },
        },
    }
    assert client.post("/api/stress-test/preview", json=body).status_code == 200
    assert client.post("/api/stress-test/preview", json=body).status_code == 200
    assert client.post("/api/stress-test/preview", json=body).status_code == 429
