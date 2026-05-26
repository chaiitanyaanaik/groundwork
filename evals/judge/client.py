from __future__ import annotations

import json

from openai import OpenAI

from evals.judge.prompts import SYSTEM_PROMPT, build_judge_user_prompt
from evals.judge.schema import JudgeVerdict
from reality_check.config import settings


def run_judge(
    scenario: dict,
    response: dict,
    synthesis_path: str,
    *,
    model: str | None = None,
    temperature: float = 0.2,
) -> JudgeVerdict:
    """Call OpenAI to score one stress-test output."""
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required for judge evals")

    client = OpenAI(api_key=settings.openai_api_key, timeout=60.0)
    user_prompt = build_judge_user_prompt(scenario, response, synthesis_path)
    judge_model = model or settings.openai_model

    completion = client.chat.completions.create(
        model=judge_model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    raw = completion.choices[0].message.content
    if not raw:
        raise ValueError("empty judge response")
    data = json.loads(raw)
    return JudgeVerdict.model_validate(data)
