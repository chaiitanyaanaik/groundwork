from __future__ import annotations

from pydantic import BaseModel, Field


class DimensionScore(BaseModel):
    dimension: str
    score: int = Field(ge=1, le=5)
    evidence: str = Field(description="Quote or paraphrase from the output that supports the score")
    improvement: str = Field(description="One concrete change if score < 5")


class JudgeVerdict(BaseModel):
    scenario_id: str
    overall_score: float = Field(ge=1.0, le=5.0)
    pass_recommendation: bool
    dimensions: list[DimensionScore]
    summary: str
    critical_issues: list[str] = Field(default_factory=list)


class ScenarioResult(BaseModel):
    scenario_id: str
    scenario_description: str
    synthesis_path: str
    latency_seconds: float
    headline: str
    gap_notice: str | None = None
    verdict: JudgeVerdict
    output_snapshot: dict = Field(default_factory=dict)
