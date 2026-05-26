from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator


ConfidenceLevel = Literal["high", "partial", "low", "none"]

UserRole = Literal["founder_ceo", "pm_product_lead", "eng_design_leader", "other_leader"]


class OrgProfile(BaseModel):
    stage: Literal["startup", "scaleup", "enterprise"] | None = None
    size: Literal["small", "medium", "large"] | None = None
    model: Literal["b2b", "b2c", "platform"] | None = None
    user_role: UserRole | None = None
    calibration: dict[str, str] = Field(default_factory=dict)

    @field_validator("calibration")
    @classmethod
    def validate_calibration(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 30:
            raise ValueError("Too many calibration answers")
        for key, answer in value.items():
            if len(key) > 80:
                raise ValueError("Calibration key too long")
            if len(str(answer)) > 200:
                raise ValueError("Calibration answer too long")
        return value


class StressTestRequest(BaseModel):
    philosophy_id: str | None = None
    aspiration_id: str | None = None
    custom_philosophy: str | None = Field(default=None, max_length=500)
    org_profile: OrgProfile


class SourceCitation(BaseModel):
    intelligence_id: str
    pattern_name: str
    source_guest: str
    source_episode: str | None = None
    quote: str | None = None


class WhatYoureTryingToChangeBlock(BaseModel):
    goal: str
    operational_meaning: str


class EnvironmentReadinessBlock(BaseModel):
    supporting_conditions: list[str] = Field(default_factory=list)
    resisting_conditions: list[str] = Field(default_factory=list)
    readiness_summary: str


class FirstBottleneckBlock(BaseModel):
    bottleneck: str
    what_teams_usually_do_next: str
    unintended_effect: str


class ResistanceBlock(BaseModel):
    patterns: list[str] = Field(default_factory=list)


class DriveChangeBlock(BaseModel):
    start_with: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    introduce_later: list[str] = Field(default_factory=list)


class MeasurementBlock(BaseModel):
    positive_signals: list[str] = Field(default_factory=list)
    warning_signs: list[str] = Field(default_factory=list)


class CourseCorrectionBlock(BaseModel):
    course_correct_if: list[str] = Field(default_factory=list)
    typical_adaptation: str


class WorksBestWhenBlock(BaseModel):
    conditions: list[str] = Field(default_factory=list)


class YourVersionBlock(BaseModel):
    title: str = ""
    keep: list[str] = Field(default_factory=list)
    modify: list[str] = Field(default_factory=list)
    add: list[str] = Field(default_factory=list)
    watch_for: list[str] = Field(default_factory=list)


class RealityCheckResponse(BaseModel):
    confidence: ConfidenceLevel
    confidence_reason: str
    headline: str = ""
    transformation_name: str
    philosophy_label: str
    what_youre_trying_to_change: WhatYoureTryingToChangeBlock
    environment_readiness: EnvironmentReadinessBlock
    first_bottleneck: FirstBottleneckBlock
    likely_resistance: ResistanceBlock
    how_to_drive_change: DriveChangeBlock
    what_to_measure: MeasurementBlock
    when_to_course_correct: CourseCorrectionBlock
    where_this_works_best: WorksBestWhenBlock
    your_version: YourVersionBlock = Field(default_factory=YourVersionBlock)
    core_organizational_insight: str
    synthesis_path: str | None = None
    sources: list[SourceCitation] = Field(default_factory=list)
    sources_more: list[SourceCitation] = Field(default_factory=list)
    gap_notice: str | None = None
    contradicting_philosophies: list[str] = Field(default_factory=list)


class PreviewResponse(BaseModel):
    confidence: ConfidenceLevel
    confidence_reason: str
    philosophy: dict
    distortion_profiles: list[dict]
    meta_patterns: list[str]
    intelligence_ids: list[str]
    contradicting_philosophies: list[str]


FeedbackRating = Literal["up", "down"]


class FeedbackRequest(BaseModel):
    rating: FeedbackRating
    comment: str | None = Field(default=None, max_length=2000)
    aspiration_id: str | None = None
    result_summary: dict | None = None
