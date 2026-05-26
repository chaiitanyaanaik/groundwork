from __future__ import annotations

import json

from evals.judge.rubric import DIMENSIONS

SYSTEM_PROMPT = """You are an expert evaluator for "GroundWork", a product that stress-tests
startup/product philosophies against a user's organizational reality.

You judge OUTPUT QUALITY for product learning — not whether you agree with the philosophy.

Scoring anchors (1–5):
1 = Missing or wrong; unusable
2 = Weak; major gap
3 = Adequate; noticeable issues
4 = Strong; minor gaps only
5 = Excellent; would trust forwarding to a busy PM

Rules:
- Base scores only on the provided system output and scenario context.
- Cite brief evidence from the output (paraphrase or short quote).
- Be strict on calibration_use: pasted question prompts like "Who usually overrides the roadmap?" score ≤2.
- Be strict on philosophy_grounding: Move-fast ship-bar advice on experimentation scenarios scores ≤2.
- pass_recommendation = true only if overall_score >= 4.0 AND no dimension below 3.
- Return valid JSON only, matching the schema exactly.
"""

USER_PROMPT_TEMPLATE = """## Scenario
id: {scenario_id}
description: {description}
user_role: {user_role}
stage / size / model: {stage} / {size} / {model}

## What the user selected
{selection_block}

## Calibration answers (human labels)
{calibration_block}

## System metadata
synthesis_path: {synthesis_path}
confidence: {confidence} ({confidence_reason})
gap_notice: {gap_notice}

## System output to judge
{output_block}

## Rubric dimensions
{rubric_block}

Return JSON:
{{
  "scenario_id": "{scenario_id}",
  "overall_score": <float 1-5>,
  "pass_recommendation": <bool>,
  "dimensions": [
    {{"dimension": "<id>", "score": <1-5>, "evidence": "...", "improvement": "..."}},
    ...
  ],
  "summary": "<2-3 sentences>",
  "critical_issues": ["<issue>", ...]
}}
"""


def _format_rubric() -> str:
    lines = []
    for d in DIMENSIONS:
        lines.append(f"- **{d['id']}** ({d['name']}): {d['question']}")
    return "\n".join(lines)


def build_output_block(response: dict) -> str:
    """Condensed view for the judge — full enough to score, not the entire corpus."""
    yv = response.get("your_version") or {}
    bn = response.get("first_bottleneck") or {}
    drive = response.get("how_to_drive_change") or {}
    readiness = response.get("environment_readiness") or {}
    sources = response.get("sources") or []

    parts = [
        f"HEADLINE: {response.get('headline', '')}",
        f"TRANSFORMATION: {response.get('transformation_name', '')}",
        "",
        "WHAT YOU'RE TRYING TO CHANGE:",
        f"  goal: {response.get('what_youre_trying_to_change', {}).get('goal', '')}",
        f"  meaning: {response.get('what_youre_trying_to_change', {}).get('operational_meaning', '')}",
        "",
        "READINESS:",
        f"  supporting: {readiness.get('supporting_conditions', [])}",
        f"  resisting: {readiness.get('resisting_conditions', [])}",
        f"  summary: {readiness.get('readiness_summary', '')}",
        "",
        "BOTTLENECK:",
        f"  {bn.get('bottleneck', '')}",
        f"  next: {bn.get('what_teams_usually_do_next', '')}",
        f"  effect: {bn.get('unintended_effect', '')}",
        "",
        "YOUR VERSION:",
        f"  title: {yv.get('title', '')}",
        f"  keep: {yv.get('keep', [])}",
        f"  modify: {yv.get('modify', [])}",
        f"  add: {yv.get('add', [])}",
        f"  watch_for: {yv.get('watch_for', [])}",
        "",
        "START WITH:",
        *(f"  - {x}" for x in drive.get("start_with", [])),
        "",
        "SOURCES:",
        *(
            f"  - {s.get('pattern_name', '')} ({s.get('source_guest', '')})"
            for s in sources[:3]
        ),
        "",
        f"INSIGHT: {response.get('core_organizational_insight', '')}",
    ]
    return "\n".join(parts)


def build_judge_user_prompt(
    scenario: dict,
    response: dict,
    synthesis_path: str,
) -> str:
    org = scenario.get("org_profile") or {}
    cal = org.get("calibration") or {}

    if scenario.get("aspiration_id"):
        selection = f"aspiration_id: {scenario['aspiration_id']}"
    elif scenario.get("philosophy_id"):
        selection = f"philosophy_id: {scenario['philosophy_id']}"
    else:
        selection = "custom (see description)"

    cal_lines = []
    for qid, opt in cal.items():
        cal_lines.append(f"- {qid}: {opt}")
    calibration_block = "\n".join(cal_lines) if cal_lines else "(none)"

    return USER_PROMPT_TEMPLATE.format(
        scenario_id=scenario["id"],
        description=scenario.get("description", ""),
        user_role=org.get("user_role", "unspecified"),
        stage=org.get("stage", "?"),
        size=org.get("size", "?"),
        model=org.get("model", "?"),
        selection_block=selection,
        calibration_block=calibration_block,
        synthesis_path=synthesis_path,
        confidence=response.get("confidence", ""),
        confidence_reason=response.get("confidence_reason", ""),
        gap_notice=response.get("gap_notice") or "(none)",
        output_block=build_output_block(response),
        rubric_block=_format_rubric(),
    )
