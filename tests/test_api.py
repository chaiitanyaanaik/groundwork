from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from reality_check.api.main import app
from reality_check.engine.calibration_bundle import get_calibration_for_philosophy
from reality_check.engine.retrieval import retrieve

client = TestClient(app)

FIXTURE_ORG_AI_NATIVE = {
    "stage": "scaleup",
    "size": "medium",
    "model": "b2b",
    "user_role": "pm_product_lead",
    "calibration": {
        "roadmap_override": "exec_override",
        "priority_chaos": "chaos_monthly",
        "revenue_pressure": "recentralize",
        "bottleneck": "design_gate",
        "ai_native_pm_time_split": "pm_mostly_coordinate",
        "ai_reality": "ai_mandate",
    },
}

FIXTURE_ORG_EMPOWER = {
    "stage": "scaleup",
    "size": "medium",
    "model": "b2b",
    "calibration": {
        "roadmap_override": "exec_override",
        "priority_chaos": "chaos_monthly",
        "revenue_pressure": "recentralize",
        "bottleneck": "design_gate",
        "empower_autonomy_reality": "own_until_pressure",
    },
}

FIXTURE_ORG_MOVE_FAST_PM = {
    "stage": "scaleup",
    "size": "medium",
    "model": "b2b",
    "user_role": "pm_product_lead",
    "calibration": {
        "roadmap_override": "exec_override",
        "priority_chaos": "chaos_monthly",
        "revenue_pressure": "recentralize",
        "bottleneck": "design_gate",
        "move_fast_quality_bar": "review_lightweight",
        "ai_reality": "ai_mandate",
    },
}

FIXTURE_ORG_DESIGN = {
    "calibration": {
        "roadmap_override": "exec_override",
        "priority_chaos": "chaos_monthly",
        "revenue_pressure": "recentralize",
        "bottleneck": "design_gate",
        "design_led_gate_role": "design_bypassed",
    },
}


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["intelligence_objects"] == 458
    assert "llm_configured" in data


def test_philosophies_list():
    r = client.get("/api/philosophies")
    assert r.status_code == 200
    ids = {p["id"] for p in r.json()["philosophies"]}
    assert len(ids) == 15
    assert "ai_native_pms" in ids
    assert "empower_teams" in ids


def test_aspirations_list():
    r = client.get("/api/aspirations")
    assert r.status_code == 200
    data = r.json()
    assert len(data["aspirations"]) == 15
    assert "reflection_layers" in data["aspirations"][0]
    assert "theme" in data["aspirations"][0]
    first = data["aspirations"][0]
    assert "label" in first
    assert "emotional_subtitle" in first
    assert "operational_truth" in first
    assert "philosophy_id" not in first


def test_calibration_questions_by_aspiration():
    r = client.get(
        "/api/calibration/questions",
        params={"aspiration_id": "team_ownership"},
    )
    assert r.status_code == 200
    assert r.json()["question_count"] >= 4


def test_calibration_questions_requires_philosophy():
    r = client.get("/api/calibration/questions")
    assert r.status_code == 400


def test_calibration_questions_ai_native_has_six():
    r = client.get("/api/calibration/questions", params={"philosophy_id": "ai_native_pms"})
    assert r.status_code == 200
    data = r.json()
    assert data["question_count"] == 6
    qids = {q["id"] for q in data["questions"]}
    assert "ai_native_pm_time_split" in qids
    assert "ai_reality" in qids
    assert len(data["role_options"]) == 4


def test_calibration_questions_design_led_has_five_no_ai():
    r = client.get("/api/calibration/questions", params={"philosophy_id": "design_led"})
    assert r.status_code == 200
    data = r.json()
    assert data["question_count"] == 5
    qids = {q["id"] for q in data["questions"]}
    assert "design_led_gate_role" in qids
    assert "ai_reality" not in qids


def test_calibration_questions_empower_specific():
    bundle = get_calibration_for_philosophy("empower_teams")
    qids = [q["id"] for q in bundle["questions"]]
    assert qids[-1] == "empower_autonomy_reality" or "empower_autonomy_reality" in qids


def test_retrieval_ai_native_pms():
    bundle = retrieve("ai_native_pms", FIXTURE_ORG_AI_NATIVE)
    assert bundle.confidence in ("high", "partial", "low")
    assert len(bundle.meta_patterns) >= 1
    assert len(bundle.intelligence_objects) >= 1
    assert bundle.org_summary.get("user_role") == "pm_product_lead"


def test_retrieval_distortion_changes_results():
    org_a = {
        **FIXTURE_ORG_EMPOWER,
        "calibration": {**FIXTURE_ORG_EMPOWER["calibration"], "revenue_pressure": "recentralize"},
    }
    org_b = {
        **FIXTURE_ORG_EMPOWER,
        "calibration": {**FIXTURE_ORG_EMPOWER["calibration"], "revenue_pressure": "double_down"},
    }
    a = retrieve("empower_teams", org_a)
    b = retrieve("empower_teams", org_b)
    assert a.distortion_profiles != b.distortion_profiles or a.intelligence_objects[0] != b.intelligence_objects[0]


def test_stress_test_preview():
    r = client.post(
        "/api/stress-test/preview",
        json={"philosophy_id": "ai_native_pms", "org_profile": FIXTURE_ORG_AI_NATIVE},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["philosophy"]["id"] == "ai_native_pms"
    assert len(data["meta_patterns"]) >= 1


def test_stress_test_output_quality_move_fast_pm(monkeypatch):
    monkeypatch.setenv("REALITY_CHECK_SKIP_LLM", "1")
    from reality_check.config import settings

    settings.reality_check_skip_llm = True
    r = client.post(
        "/api/stress-test",
        json={"philosophy_id": "move_fast", "org_profile": FIXTURE_ORG_MOVE_FAST_PM},
    )
    assert r.status_code == 200
    assert r.headers.get("X-Synthesis-Path") == "fallback"
    data = r.json()
    assert data["headline"]
    assert " but " in data["headline"].lower()
    assert "Who usually overrides" not in data["headline"]
    bottleneck = data["first_bottleneck"]["bottleneck"]
    assert len(bottleneck.split()) >= 8
    assert data["first_bottleneck"]["what_teams_usually_do_next"]
    assert len(data["first_bottleneck"]["what_teams_usually_do_next"].split()) >= 8
    start = data["how_to_drive_change"]["start_with"]
    assert any("ship" in s.lower() or "preview" in s.lower() for s in start)
    assert not any("experiment log" in s.lower() for s in start)
    later = {x.lower() for x in data["how_to_drive_change"]["introduce_later"]}
    for signal in data["what_to_measure"]["positive_signals"]:
        assert signal.lower() not in later
    assert data["core_organizational_insight"] != data["what_youre_trying_to_change"]["operational_meaning"]
    assert len(data["contradicting_philosophies"]) >= 1
    supporting = data["environment_readiness"]["supporting_conditions"]
    assert not any("Ungoverned shipping" in s for s in supporting)


def test_all_philosophies_have_retrieval_and_sources(monkeypatch):
    monkeypatch.setenv("REALITY_CHECK_SKIP_LLM", "1")
    from reality_check.config import settings
    from reality_check.engine.loader import load_philosophy_questions, questions_by_id

    settings.reality_check_skip_llm = True
    pq = load_philosophy_questions()
    qmap = questions_by_id()
    spec_defaults = {
        "move_fast": "review_lightweight",
        "empower_teams": "own_until_pressure",
        "ai_first": "ai_top_down",
        "founder_mode": "barrel_few",
        "high_experimentation": "kill_no_insight",
        "ai_native_pms": "pm_mostly_coordinate",
        "design_led": "design_bypassed",
        "minimal_process": "process_creep",
        "product_led_growth": "plg_sales_led",
        "influence_without_politics": "influence_theater",
        "high_performance_culture": "perf_blame",
        "lean_constraints": "lean_shadow_hire",
        "bottom_up_ai": "bottom_up_pockets",
        "evals_first_ai": "evals_after_ship",
        "platform_org": "platform_silos",
    }
    base_cal = {
        "roadmap_override": "exec_override",
        "priority_chaos": "chaos_monthly",
        "revenue_pressure": "recentralize",
        "bottleneck": "design_gate",
        "ai_reality": "ai_mandate",
    }
    for pid in spec_defaults:
        cal = dict(base_cal)
        spec_q = pq["philosophy_question_ids"][pid]
        cal[spec_q] = spec_defaults[pid]
        org = {"stage": "scaleup", "size": "medium", "model": "b2b", "user_role": "pm_product_lead", "calibration": cal}
        r = client.post("/api/stress-test", json={"philosophy_id": pid, "org_profile": org})
        assert r.status_code == 200, pid
        data = r.json()
        assert data["headline"] and " but " in data["headline"].lower(), pid
        assert len(data["sources"]) >= 1, pid
        assert "blast-radius" not in " ".join(data["how_to_drive_change"]["start_with"]).lower() or pid == "move_fast", pid


def test_high_experimentation_headline_mentions_learning(monkeypatch):
    monkeypatch.setenv("REALITY_CHECK_SKIP_LLM", "1")
    from reality_check.config import settings

    settings.reality_check_skip_llm = True
    org = {
        **FIXTURE_ORG_MOVE_FAST_PM,
        "calibration": {
            **FIXTURE_ORG_MOVE_FAST_PM["calibration"],
            "experiment_kill_pattern": "kill_no_insight",
        },
    }
    org["calibration"].pop("move_fast_quality_bar", None)
    r = client.post(
        "/api/stress-test",
        json={"philosophy_id": "high_experimentation", "org_profile": org},
    )
    data = r.json()
    assert "insight" in data["headline"].lower() or "propagat" in data["headline"].lower()
    start = " ".join(data["how_to_drive_change"]["start_with"]).lower()
    assert "experiment" in start
    assert "blast-radius" not in start


def test_stress_test_includes_your_version(monkeypatch):
    monkeypatch.setenv("REALITY_CHECK_SKIP_LLM", "1")
    from reality_check.config import settings

    settings.reality_check_skip_llm = True
    r = client.post(
        "/api/stress-test",
        json={"philosophy_id": "move_fast", "org_profile": FIXTURE_ORG_MOVE_FAST_PM},
    )
    data = r.json()
    yv = data["your_version"]
    assert yv["title"]
    assert "Your version" in yv["title"]
    assert len(yv["keep"]) >= 1
    assert len(yv["modify"]) >= 1
    assert len(yv["add"]) >= 1
    assert len(yv["watch_for"]) >= 1
    assert data.get("synthesis_path") == "fallback"


def test_normalize_llm_sources_accepts_string_ids():
    from reality_check.engine.retrieval import retrieve
    from reality_check.engine.synthesis import _normalize_response

    bundle = retrieve("move_fast", FIXTURE_ORG_MOVE_FAST_PM)
    iid = bundle.intelligence_objects[0]["intelligence_id"]
    data = {
        "philosophy_label": "Move fast",
        "transformation_name": "Move fast",
        "sources": [iid, {"intelligence_id": iid}],
        "sources_more": [],
    }
    out = _normalize_response(data, bundle)
    assert len(out["sources"]) >= 1
    assert out["sources"][0]["intelligence_id"] == iid


def test_llm_output_validation_uses_fallback(monkeypatch):
    import asyncio

    from reality_check.api.schemas import RealityCheckResponse
    from reality_check.config import settings
    from reality_check.engine.retrieval import retrieve
    from reality_check.engine.synthesis import synthesize_with_meta

    monkeypatch.setattr(settings, "reality_check_skip_llm", False)
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    card_truth = "Fast orgs often discover that coordination slows down after shipping speeds increase."

    async def bad_llm(bundle):
        return RealityCheckResponse(
            confidence="high",
            confidence_reason="test",
            headline="Move fast only",
            transformation_name="Move fast",
            philosophy_label="Move fast",
            what_youre_trying_to_change={"goal": "x", "operational_meaning": "y"},
            environment_readiness={
                "supporting_conditions": [],
                "resisting_conditions": [],
                "readiness_summary": "r",
            },
            first_bottleneck={
                "bottleneck": "short",
                "what_teams_usually_do_next": "short",
                "unintended_effect": "short",
            },
            likely_resistance={"patterns": []},
            how_to_drive_change={"start_with": [], "avoid": [], "introduce_later": []},
            what_to_measure={"positive_signals": [], "warning_signs": []},
            when_to_course_correct={"course_correct_if": [], "typical_adaptation": ""},
            where_this_works_best={"conditions": []},
            core_organizational_insight=card_truth,
            sources=[],
        )

    monkeypatch.setattr("reality_check.engine.synthesis._call_openai", bad_llm)

    bundle = retrieve("move_fast", FIXTURE_ORG_MOVE_FAST_PM)
    result, path = asyncio.run(synthesize_with_meta(bundle))
    assert path == "fallback_validated"
    assert result.gap_notice and "quality checks" in result.gap_notice
    assert result.headline and " but " in result.headline.lower()
    assert len(result.sources) >= 1


def test_stress_test_fallback_no_llm(monkeypatch):
    monkeypatch.setenv("REALITY_CHECK_SKIP_LLM", "1")
    from reality_check.config import settings

    settings.reality_check_skip_llm = True
    r = client.post(
        "/api/stress-test",
        json={"philosophy_id": "empower_teams", "org_profile": FIXTURE_ORG_EMPOWER},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["transformation_name"] == "Empower teams"
    assert data["what_youre_trying_to_change"]["goal"]
    assert data["environment_readiness"]["readiness_summary"]
    assert len(data["environment_readiness"]["resisting_conditions"]) >= 1
    assert data["first_bottleneck"]["bottleneck"]
    assert len(data["likely_resistance"]["patterns"]) >= 1
    assert len(data["how_to_drive_change"]["start_with"]) >= 1
    assert len(data["what_to_measure"]["warning_signs"]) >= 1
    assert data["when_to_course_correct"]["typical_adaptation"]
    assert len(data["where_this_works_best"]["conditions"]) >= 1
    assert data["core_organizational_insight"]
    assert len(data["sources"]) <= 2


def test_stress_test_requires_philosophy():
    r = client.post("/api/stress-test", json={"org_profile": FIXTURE_ORG_EMPOWER})
    assert r.status_code == 400


def test_stress_test_preview_by_aspiration(monkeypatch):
    monkeypatch.setenv("REALITY_CHECK_SKIP_LLM", "1")
    r = client.post(
        "/api/stress-test/preview",
        json={"aspiration_id": "team_ownership", "org_profile": FIXTURE_ORG_EMPOWER},
    )
    assert r.status_code == 200
    assert r.json()["philosophy"]["id"] == "empower_teams"


@pytest.mark.parametrize(
    "aspiration_id,philosophy_id,specific_question",
    [
        ("cross_functional_alignment", "influence_without_politics", "influence_decision_path"),
        ("scale_innovation", "platform_org", "platform_silo_reality"),
        ("reduce_roadmap_chaos", "founder_mode", "founder_barrel_count"),
        ("execution_speed_no_burnout", "lean_constraints", "lean_headcount_stance"),
        ("team_ownership", "empower_teams", "empower_autonomy_reality"),
    ],
)
def test_aspiration_philosophy_question_mapping(aspiration_id, philosophy_id, specific_question):
    from reality_check.engine.loader import aspiration_by_id, resolve_philosophy_id

    assert aspiration_by_id()[aspiration_id]["philosophy_id"] == philosophy_id
    resolved = resolve_philosophy_id(aspiration_id=aspiration_id)
    assert resolved == philosophy_id
    r = client.get("/api/calibration/questions", params={"aspiration_id": aspiration_id})
    assert r.status_code == 200
    qids = {q["id"] for q in r.json()["questions"]}
    assert specific_question in qids


def test_submit_feedback(tmp_path, monkeypatch):
    from reality_check.engine import feedback_store

    feedback_file = tmp_path / "feedback.jsonl"
    monkeypatch.setattr(feedback_store, "FEEDBACK_PATH", feedback_file)

    r = client.post(
        "/api/feedback",
        json={
            "rating": "up",
            "comment": "Clear and actionable",
            "aspiration_id": "cross_functional_alignment",
            "result_summary": {
                "confidence": "partial",
                "transformation_name": "Test",
                "synthesis_path": "llm",
            },
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    lines = feedback_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    row = __import__("json").loads(lines[0])
    assert row["rating"] == "up"
    assert row["comment"] == "Clear and actionable"
    assert row["aspiration_id"] == "cross_functional_alignment"
    assert row["result_summary"] == {
        "confidence": "partial",
        "transformation_name": "Test",
        "synthesis_path": "llm",
    }
    assert "org_profile" not in row
    assert "created_at" in row


def test_submit_feedback_requires_rating():
    r = client.post("/api/feedback", json={"comment": "missing rating"})
    assert r.status_code == 422


def test_stress_test_uses_aspiration_label(monkeypatch):
    monkeypatch.setenv("REALITY_CHECK_SKIP_LLM", "1")
    from reality_check.config import settings

    settings.reality_check_skip_llm = True
    r = client.post(
        "/api/stress-test",
        json={
            "aspiration_id": "cross_functional_alignment",
            "org_profile": FIXTURE_ORG_EMPOWER,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["philosophy_label"] == "Improve cross-functional alignment"
    assert data["transformation_name"] == "Improve cross-functional alignment"
    assert "Platform org" not in data["what_youre_trying_to_change"]["goal"]
