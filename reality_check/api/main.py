from __future__ import annotations

from pathlib import Path

import pydantic
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from reality_check.api.schemas import FeedbackRequest, PreviewResponse, StressTestRequest
from reality_check.api.security import (
    check_rate_limit,
    require_feedback_enabled,
    verify_stress_test_api_key,
)
from reality_check.engine.feedback_store import append_feedback
from reality_check.engine.analytics_store import append_event, compute_summary
from reality_check.engine.calibration_bundle import get_calibration_for_philosophy
from reality_check.engine.loader import (
    aspiration_by_id,
    corpus_stats,
    load_aspirations,
    load_philosophies,
    philosophy_by_id,
    resolve_philosophy_id,
)
from reality_check.engine.retrieval import retrieve
from reality_check.config import settings
from reality_check.engine.synthesis import synthesize_with_meta


def create_app() -> FastAPI:
    docs_url = "/docs" if settings.api_docs_enabled else None
    redoc_url = "/redoc" if settings.api_docs_enabled else None
    openapi_url = "/openapi.json" if settings.api_docs_enabled else None

    application = FastAPI(
        title="Reality Check",
        description="Stress-test startup/product philosophies against operational reality.",
        version="0.1.0",
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )

    origins = settings.cors_origins
    if origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "OPTIONS"],
            allow_headers=["Content-Type", "X-Reality-Check-Key"],
        )

    @application.middleware("http")
    async def security_and_docs_gate(request: Request, call_next):
        path = request.url.path
        if not settings.api_docs_enabled and path in ("/docs", "/redoc", "/openapi.json"):
            return JSONResponse(status_code=404, content={"detail": "Not found"})
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if path == "/" or path.endswith((".html", ".js", ".css")):
            response.headers["Cache-Control"] = "no-store, max-age=0"
        return response

    return application


app = create_app()


def _stress_test_guards(request: Request) -> None:
    verify_stress_test_api_key(request)
    check_rate_limit(request, "stress_test", settings.rate_limit_stress_test)


def _preview_guards(request: Request) -> None:
    verify_stress_test_api_key(request)
    check_rate_limit(request, "stress_preview", settings.rate_limit_preview)


def _feedback_guards(request: Request) -> None:
    require_feedback_enabled()
    check_rate_limit(request, "feedback", settings.rate_limit_feedback)


def _feedback_record(body: FeedbackRequest) -> dict:
    comment = (body.comment or "").strip() or None
    slim_summary = None
    if body.result_summary:
        slim_summary = {
            "confidence": body.result_summary.get("confidence"),
            "transformation_name": body.result_summary.get("transformation_name"),
            "synthesis_path": body.result_summary.get("synthesis_path"),
        }
    return {
        "rating": body.rating,
        "comment": comment,
        "aspiration_id": body.aspiration_id,
        "result_summary": slim_summary,
    }


class AnalyticsEventRequest(pydantic.BaseModel):
    event: str
    properties: dict = {}


@app.post("/api/analytics/event", status_code=204)
async def track_event(body: AnalyticsEventRequest, request: Request):
    check_rate_limit(request, "analytics_event", 120)
    try:
        append_event(body.event, body.properties)
    except Exception:
        pass


@app.get("/api/analytics/summary")
def analytics_summary():
    return compute_summary()


@app.get("/api/health")
def health():
    stats = corpus_stats()
    payload: dict = {"status": "ok", **stats}
    if settings.expose_health_details:
        payload["llm_configured"] = bool(
            settings.openai_api_key and not settings.reality_check_skip_llm
        )
    return payload


@app.get("/api/philosophies")
def list_philosophies():
    data = load_philosophies()
    return {
        "philosophies": [
            {
                "id": p["id"],
                "label": p["label"],
                "tagline": p["tagline"],
                "emotional_subtitle": p.get("emotional_subtitle", p["tagline"]),
                "operational_truth": p.get("operational_truth", ""),
                "user_facing_hook": p["user_facing_hook"],
            }
            for p in data["philosophies"]
        ]
    }


@app.get("/api/philosophies/{philosophy_id}")
def get_philosophy(philosophy_id: str):
    by_id = philosophy_by_id()
    if philosophy_id not in by_id:
        raise HTTPException(status_code=404, detail="Philosophy not found")
    p = by_id[philosophy_id]
    return p


def _public_aspiration(a: dict) -> dict:
    return {
        "id": a["id"],
        "label": a["label"],
        "emotional_subtitle": a["emotional_subtitle"],
        "operational_truth": a["operational_truth"],
        "theme": a.get("theme", "default"),
        "reflection_layers": a.get("reflection_layers", []),
    }


@app.get("/api/aspirations")
def list_aspirations():
    return {
        "aspirations": [_public_aspiration(a) for a in load_aspirations()["aspirations"]]
    }


@app.get("/api/aspirations/{aspiration_id}")
def get_aspiration(aspiration_id: str):
    if aspiration_id not in aspiration_by_id():
        raise HTTPException(status_code=404, detail="Aspiration not found")
    return _public_aspiration(aspiration_by_id()[aspiration_id])


def _philosophy_id_from_request(
    philosophy_id: str | None,
    aspiration_id: str | None,
    custom_philosophy: str | None,
) -> str | None:
    if custom_philosophy:
        return None
    try:
        return resolve_philosophy_id(
            philosophy_id=philosophy_id,
            aspiration_id=aspiration_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/calibration/questions")
def calibration_questions(
    philosophy_id: str | None = None,
    aspiration_id: str | None = None,
):
    if not philosophy_id and not aspiration_id:
        raise HTTPException(
            status_code=400,
            detail="philosophy_id or aspiration_id query parameter is required",
        )
    try:
        resolved = resolve_philosophy_id(
            philosophy_id=philosophy_id,
            aspiration_id=aspiration_id,
        )
        bundle = get_calibration_for_philosophy(resolved)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return {
        "philosophy_id": bundle["philosophy_id"],
        "question_count": bundle["question_count"],
        "role_options": bundle["role_options"],
        "questions": [
            {
                "id": q["id"],
                "prompt": q["prompt"],
                "framing": q.get("framing", ""),
                "options": q["options"],
            }
            for q in bundle["questions"]
        ],
    }


@app.post("/api/stress-test/preview", dependencies=[Depends(_preview_guards)])
def stress_test_preview(body: StressTestRequest):
    if not body.philosophy_id and not body.aspiration_id and not body.custom_philosophy:
        raise HTTPException(
            status_code=400,
            detail="philosophy_id, aspiration_id, or custom_philosophy required",
        )
    pid = _philosophy_id_from_request(
        body.philosophy_id, body.aspiration_id, body.custom_philosophy
    )
    aspiration = aspiration_by_id().get(body.aspiration_id) if body.aspiration_id else None
    try:
        bundle = retrieve(
            pid,
            body.org_profile.model_dump(),
            body.custom_philosophy,
            aspiration=aspiration,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    return PreviewResponse(
        confidence=bundle.confidence,  # type: ignore[arg-type]
        confidence_reason=bundle.confidence_reason,
        philosophy={
            "id": bundle.philosophy.get("id"),
            "label": bundle.philosophy.get("label"),
        },
        distortion_profiles=bundle.distortion_profiles,
        meta_patterns=[m["meta"]["pattern_name"] for m in bundle.meta_patterns],
        intelligence_ids=[o.get("intelligence_id", "") for o in bundle.intelligence_objects],
        contradicting_philosophies=[p.get("label", "") for p in bundle.contradicting_philosophies],
    )


@app.post("/api/feedback", dependencies=[Depends(_feedback_guards)])
def submit_feedback(body: FeedbackRequest):
    record = _feedback_record(body)
    try:
        append_feedback(record)
    except OSError as e:
        raise HTTPException(status_code=500, detail="Could not save feedback") from e
    return {"status": "ok"}


@app.post("/api/stress-test", dependencies=[Depends(_stress_test_guards)])
async def stress_test(body: StressTestRequest):
    if not body.philosophy_id and not body.aspiration_id and not body.custom_philosophy:
        raise HTTPException(
            status_code=400,
            detail="philosophy_id, aspiration_id, or custom_philosophy required",
        )
    pid = _philosophy_id_from_request(
        body.philosophy_id, body.aspiration_id, body.custom_philosophy
    )
    aspiration = aspiration_by_id().get(body.aspiration_id) if body.aspiration_id else None
    try:
        bundle = retrieve(
            pid,
            body.org_profile.model_dump(),
            body.custom_philosophy,
            aspiration=aspiration,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    result, synthesis_path = await synthesize_with_meta(bundle)
    return JSONResponse(
        content=result.model_dump(),
        headers={"X-Synthesis-Path": synthesis_path},
    )


# Optional static frontend when frontend/ exists (Replit phase)
_frontend = Path(__file__).resolve().parents[2] / "frontend"
if _frontend.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend), html=True), name="frontend")
