from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from reality_check.api.main import app
from reality_check.engine.loader import aspiration_by_id, load_philosophies, resolve_philosophy_id
from reality_check.engine.relevance import object_matches_philosophy, text_matches_philosophy
from reality_check.engine.retrieval import retrieve
from reality_check.engine.synthesis import _fallback_response

client = TestClient(app)

ORG_DESIGN = {
    "stage": "scaleup",
    "size": "medium",
    "model": "b2b",
    "calibration": {
        "roadmap_override": "exec_override",
        "priority_chaos": "chaos_monthly",
        "revenue_pressure": "recentralize",
        "bottleneck": "design_gate",
        "design_led_gate_role": "design_bypassed",
    },
}

# Cross-philosophy bleed phrases we must not surface on design-led / cohesion runs.
DESIGN_FORBIDDEN = [
    "rubber-stamping ai strategy",
    "experimentation theater",
    "founder mode",
    "plg",
    "platform org",
    "barrel throughput",
]

AI_FORBIDDEN_ON_DESIGN = DESIGN_FORBIDDEN


def _all_section_text(data: dict) -> str:
    parts = [
        data.get("transformation_name", ""),
        data.get("what_youre_trying_to_change", {}).get("goal", ""),
        data.get("what_youre_trying_to_change", {}).get("operational_meaning", ""),
        data.get("environment_readiness", {}).get("readiness_summary", ""),
        data.get("first_bottleneck", {}).get("bottleneck", ""),
        data.get("first_bottleneck", {}).get("what_teams_usually_do_next", ""),
        data.get("first_bottleneck", {}).get("unintended_effect", ""),
        data.get("core_organizational_insight", ""),
    ]
    for key in ("supporting_conditions", "resisting_conditions"):
        parts.extend(data.get("environment_readiness", {}).get(key, []))
    parts.extend(data.get("likely_resistance", {}).get("patterns", []))
    for key in ("start_with", "avoid", "introduce_later"):
        parts.extend(data.get("how_to_drive_change", {}).get(key, []))
    for key in ("positive_signals", "warning_signs"):
        parts.extend(data.get("what_to_measure", {}).get(key, []))
    parts.extend(data.get("when_to_course_correct", {}).get("course_correct_if", []))
    parts.append(data.get("when_to_course_correct", {}).get("typical_adaptation", ""))
    parts.extend(data.get("where_this_works_best", {}).get("conditions", []))
    for s in data.get("sources", []):
        parts.append(s.get("pattern_name", ""))
    return " ".join(parts).lower()


@pytest.fixture(autouse=True)
def skip_llm(monkeypatch):
    monkeypatch.setenv("REALITY_CHECK_SKIP_LLM", "1")
    from reality_check.config import settings

    settings.reality_check_skip_llm = True


def test_retrieval_objects_match_philosophy_keywords():
    asp = aspiration_by_id()["product_cohesion"]
    pid = resolve_philosophy_id(aspiration_id="product_cohesion")
    bundle = retrieve(pid, ORG_DESIGN, aspiration=asp)
    phil = bundle.philosophy
    assert bundle.intelligence_objects, "expected at least one philosophy-scoped object"
    for obj in bundle.intelligence_objects:
        assert object_matches_philosophy(obj, phil)
    names = " ".join(o.get("pattern_name", "") for o in bundle.intelligence_objects).lower()
    assert "rubber-stamping" not in names


def test_product_cohesion_fallback_bottleneck_is_design_relevant():
    asp = aspiration_by_id()["product_cohesion"]
    pid = resolve_philosophy_id(aspiration_id="product_cohesion")
    bundle = retrieve(pid, ORG_DESIGN, aspiration=asp)
    out = _fallback_response(bundle).model_dump()
    bottleneck = out["first_bottleneck"]["bottleneck"].lower()
    assert text_matches_philosophy(bottleneck, bundle.philosophy) or any(
        k in bottleneck for k in ("design", "cohesion", "gate", "ship", "taste")
    )
    assert "rubber-stamping" not in bottleneck


def test_stress_test_sections_relevant_for_each_philosophy():
    philosophies = load_philosophies()["philosophies"]
    for phil in philosophies:
        org = {
            "stage": "scaleup",
            "size": "medium",
            "model": "b2b",
            "calibration": {
                "roadmap_override": "exec_override",
                "priority_chaos": "chaos_monthly",
                "revenue_pressure": "recentralize",
                "bottleneck": "design_gate",
            },
        }
        r = client.post(
            "/api/stress-test",
            json={"philosophy_id": phil["id"], "org_profile": org},
        )
        assert r.status_code == 200, phil["id"]
        data = r.json()
        assert data["philosophy_label"]
        blob = _all_section_text(data)
        assert text_matches_philosophy(blob, phil) or any(
            k.lower() in blob for k in phil.get("keywords", [])[:3]
        ), phil["id"]


def test_design_led_api_excludes_ai_newsletter_bleed():
    r = client.post(
        "/api/stress-test",
        json={"aspiration_id": "product_cohesion", "org_profile": ORG_DESIGN},
    )
    assert r.status_code == 200
    blob = _all_section_text(r.json())
    for phrase in AI_FORBIDDEN_ON_DESIGN:
        assert phrase not in blob, f"found forbidden phrase: {phrase}"
