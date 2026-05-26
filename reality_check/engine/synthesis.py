from __future__ import annotations

import asyncio
import json

from reality_check.api.schemas import (
    RealityCheckResponse,
    SourceCitation,
)
from reality_check.config import settings
from reality_check.engine.calibration_bundle import role_label
from reality_check.engine.distortions import humanize_calibration, humanize_calibration_short
from reality_check.engine.loader import load_philosophy_questions
from reality_check.engine.prompts import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from reality_check.engine.response_enrichment import enrich_response
from reality_check.engine.response_validation import validate_response_data
from reality_check.engine.relevance import object_matches_philosophy, text_matches_philosophy
from reality_check.engine.retrieval import RetrievalBundle


def _simulation_style(philosophy_id: str | None) -> str:
    styles = load_philosophy_questions().get("simulation_styles", {})
    if philosophy_id and philosophy_id in styles:
        return styles[philosophy_id]
    return "Emphasize how the org drifts under revenue and priority pressure."


def _format_meta_patterns(bundle: RetrievalBundle) -> str:
    lines = []
    for item in bundle.meta_patterns:
        meta = item["meta"]
        lines.append(f"- {meta['pattern_name']}: {meta.get('core_tension', meta.get('description', ''))}")
        norm = item.get("normalized") or {}
        for fm in (norm.get("failure_modes") or [])[:3]:
            lines.append(f"  failure: {fm}")
    return "\n".join(lines) or "(none)"


def _format_objects(bundle: RetrievalBundle) -> str:
    lines = []
    for obj in bundle.intelligence_objects[: settings.retrieval_object_limit]:
        lines.append(
            f"- [{obj.get('intelligence_id')}] {obj.get('pattern_name')} ({obj.get('source_guest')})\n"
            f"  belief: {(obj.get('core_belief') or '')[:120]}\n"
            f"  hidden: {'; '.join((obj.get('hidden_assumptions') or [])[:1])}\n"
            f"  quote: {(obj.get('source_quote_or_context') or '')[:120]}"
        )
    return "\n".join(lines) or "(none)"


def _user_facing_label(bundle: RetrievalBundle) -> str:
    if bundle.aspiration:
        return bundle.aspiration.get("label", bundle.philosophy.get("label", ""))
    return bundle.philosophy.get("label", "")


def _user_facing_hook(bundle: RetrievalBundle) -> str:
    if bundle.aspiration:
        return bundle.aspiration.get("emotional_subtitle", bundle.philosophy.get("user_facing_hook", ""))
    return bundle.philosophy.get("user_facing_hook", "")


def build_user_prompt(bundle: RetrievalBundle) -> str:
    cal = bundle.org_summary.get("calibration") or {}
    pid = bundle.philosophy.get("id")
    return USER_PROMPT_TEMPLATE.format(
        philosophy_label=_user_facing_label(bundle),
        philosophy_hook=_user_facing_hook(bundle),
        simulation_style=_simulation_style(pid if pid != "custom" else None),
        confidence=bundle.confidence,
        confidence_reason=bundle.confidence_reason,
        calibration_lines="\n".join(
            f"- {l}" for l in humanize_calibration_short(cal) or humanize_calibration(cal)
        ),
        stage=bundle.org_summary.get("stage") or "unknown",
        size=bundle.org_summary.get("size") or "unknown",
        model=bundle.org_summary.get("model") or "unknown",
        user_role=role_label(bundle.org_summary.get("user_role")),
        distortions="\n".join(
            f"- {d.get('label', d.get('id'))}" for d in bundle.distortion_profiles
        )
        or "(none detected)",
        meta_patterns=_format_meta_patterns(bundle),
        objects=_format_objects(bundle),
        contradicting="\n".join(
            f"- {p.get('label')}" for p in bundle.contradicting_philosophies
        )
        or "(none)",
    )


def _source_citations(objects: list[dict], limit: int) -> list[SourceCitation]:
    out = []
    for obj in objects[:limit]:
        if not obj.get("intelligence_id"):
            continue
        out.append(
            SourceCitation(
                intelligence_id=obj.get("intelligence_id", ""),
                pattern_name=obj.get("pattern_name", ""),
                source_guest=obj.get("source_guest", ""),
                source_episode=obj.get("source_episode"),
                quote=(obj.get("source_quote_or_context") or "")[:300],
            )
        )
    return out


def _split_sources(sources: list[SourceCitation]) -> tuple[list[SourceCitation], list[SourceCitation]]:
    if len(sources) <= 2:
        return sources, []
    return sources[:2], sources[2:]


def _unique(items: list[str], limit: int) -> list[str]:
    return [item for item in dict.fromkeys(items) if item][:limit]


def _split_failure_line(text: str) -> list[str]:
    return [p.strip() for p in text.replace(";", ".").split(".") if p.strip()]


def _primary_object(bundle: RetrievalBundle) -> dict | None:
    objs = bundle.intelligence_objects
    return objs[0] if objs else None


def _fields_from_object(obj: dict) -> dict[str, list[str]]:
    failures: list[str] = []
    for fm in obj.get("failure_modes") or []:
        failures.extend(_split_failure_line(str(fm)))
    pressures: list[str] = []
    for ps in obj.get("pressure_scenarios") or []:
        pressures.extend(_split_failure_line(str(ps)))
    adaptations: list[str] = []
    for a in obj.get("operational_adaptations") or []:
        adaptations.extend(_split_failure_line(str(a)))
    hidden = list(obj.get("hidden_assumptions") or [])
    return {
        "failures": failures,
        "pressures": pressures,
        "adaptations": adaptations,
        "hidden": hidden,
    }


def _bottleneck_block(bundle: RetrievalBundle, primary: dict | None, collapse: str) -> dict[str, str]:
    phil = bundle.philosophy
    pid = phil.get("id")
    style = _simulation_style(pid if pid != "custom" else None)

    if primary:
        fields = _fields_from_object(primary)
        bottleneck = fields["failures"][0] if fields["failures"] else collapse
        pressures = fields["pressures"]
        adaptations = fields["adaptations"]
        next_step = (
            pressures[0]
            if pressures
            else f"Teams respond with a familiar workaround that protects this week's delivery — common under {phil.get('label', 'this philosophy').lower()}."
        )
        effect = (
            fields["failures"][1]
            if len(fields["failures"]) > 1
            else (
                adaptations[0]
                if adaptations
                else f"The workaround undermines the intent of {phil.get('label', 'the philosophy').lower()} while feeling responsible in the moment."
            )
        )
        return {
            "bottleneck": bottleneck,
            "what_teams_usually_do_next": next_step,
            "unintended_effect": effect,
        }

    return {
        "bottleneck": collapse or phil.get("operational_truth", "Operational drift under pressure."),
        "what_teams_usually_do_next": style,
        "unintended_effect": (
            f"The org keeps the language of {phil.get('label', 'the philosophy').lower()} "
            "but behavior drifts toward what already felt safe under pressure."
        ),
    }


def _fallback_response(bundle: RetrievalBundle) -> RealityCheckResponse:
    phil = _user_facing_label(bundle) or "this philosophy"
    hook = _user_facing_hook(bundle) or f"We want {phil.lower()}."
    org = bundle.org_summary
    cal = org.get("calibration") or {}
    cal_lines = humanize_calibration_short(cal)
    role = role_label(org.get("user_role"))
    stage = org.get("stage") or "unknown-stage"
    size = org.get("size") or "unknown-size"
    model = org.get("model") or "unknown-model"
    distortion = (
        bundle.distortion_profiles[0]["label"]
        if bundle.distortion_profiles
        else "operational pressure may contradict the aspiration"
    )
    collapse = (
        bundle.distortion_profiles[0].get("collapse_pattern")
        if bundle.distortion_profiles
        else "Operational drift under pressure"
    )

    primary = _primary_object(bundle)
    primary_fields = _fields_from_object(primary) if primary else {
        "failures": [],
        "pressures": [],
        "adaptations": [],
        "hidden": [],
    }

    hidden, adaptations, failures, pressures = [], [], [], []
    for obj in bundle.intelligence_objects[:5]:
        hidden.extend(obj.get("hidden_assumptions") or [])
        for fm in obj.get("failure_modes") or []:
            failures.extend(_split_failure_line(str(fm)))
        for ps in obj.get("pressure_scenarios") or []:
            pressures.extend(_split_failure_line(str(ps)))
        for a in obj.get("operational_adaptations") or []:
            adaptations.extend(_split_failure_line(str(a)))

    all_sources = _source_citations(bundle.intelligence_objects, 5)
    featured, more = _split_sources(all_sources)

    gap = None
    if bundle.confidence in ("low", "none"):
        gap = (
            "Corpus coverage is limited for this exact situation. "
            "The following is grounded in adjacent patterns - not a proven playbook."
        )

    phil_truth = bundle.philosophy.get("operational_truth", "")
    pressures_u = _unique(pressures or primary_fields["pressures"], 5)
    failures_u = _unique(failures or primary_fields["failures"], 5)
    hidden_u = _unique(hidden or primary_fields["hidden"], 3)
    adaptations_u = _unique(adaptations or primary_fields["adaptations"], 3)
    distortion_labels = _unique(
        [d.get("label", "") for d in bundle.distortion_profiles],
        3,
    )
    first_answer = cal_lines[0] if cal_lines else "mixed operating pressure"
    second_answer = cal_lines[1] if len(cal_lines) > 1 else first_answer

    response = RealityCheckResponse(
        confidence=bundle.confidence,  # type: ignore[arg-type]
        confidence_reason=bundle.confidence_reason,
        transformation_name=phil,
        philosophy_label=phil,
        what_youre_trying_to_change={
            "goal": hook,
            "operational_meaning": phil_truth
            or (
                f"For a {role} in a {size} {stage} {model} org, pursuing {phil.lower()} changes "
                "how teams trade off speed, ownership, and quality when pressure rises."
            ),
        },
        environment_readiness={
            "supporting_conditions": [
                f"Clear intent: {hook}",
                f"Org context ({stage}, {size}, {model}) is known enough to tailor the operating model.",
                f"As {role}, you can influence how {phil.lower()} shows up in weekly decisions.",
            ],
            "resisting_conditions": [
                f"Your answers point to {distortion.lower()}.",
                f"Friction: {first_answer}.",
                *[f"Friction: {label}." for label in cal_lines[1:3]],
                *distortion_labels[1:2],
            ],
            "readiness_summary": (
                f"The environment is not simply ready or unready. Intent is real, but "
                f"{', '.join(cal_lines[:3]).lower() if cal_lines else 'operating pressure'} "
                f"will shape how {phil.lower()} behaves when stakes rise."
            ),
        },
        first_bottleneck=_bottleneck_block(bundle, primary, collapse),
        likely_resistance={
            "patterns": pressures_u
            or [
                f"Teams support {phil.lower()} in calm periods, then revert when {distortion.lower()}.",
                f"Pressure exposes gaps in {phil.lower()} before new habits have stuck.",
            ],
        },
        how_to_drive_change={
            "start_with": [],
            "avoid": [
                "Do not turn the philosophy into a broad governance program before teams trust the behavior.",
                "Do not add checkpoints for every edge case; start with the pressure points your answers surfaced.",
                "Do not measure adoption by enthusiasm or stated agreement.",
            ],
            "introduce_later": adaptations_u
            or [
                "Add stronger coordination rituals once teams are voluntarily following the lightweight version.",
                "Create clearer standards after the first repeated bottleneck is visible.",
            ],
        },
        what_to_measure={
            "positive_signals": [
                f"Teams ship with the agreed {phil.lower()} bar without extra exec escalation.",
                "Review exceptions decrease week over week while throughput holds.",
                f"Partners can name what must hold for {phil.lower()} under pressure.",
            ],
            "warning_signs": failures_u[:4]
            or [
                f"Workarounds bypass the intent of {phil.lower()}.",
                f"{distortion} shows up in weekly decisions.",
            ],
        },
        when_to_course_correct={
            "course_correct_if": [
                "The transformation starts creating the opposite effect.",
                "Coordination overhead increases faster than velocity or quality improves.",
                "Teams stop voluntarily following the new system.",
                f"The behavior implied by {second_answer.lower()} becomes the default under pressure.",
            ],
            "typical_adaptation": (
                "You may need lighter-weight coordination and clearer pressure rules, not stricter governance."
            ),
        },
        where_this_works_best={
            "conditions": adaptations_u[:3]
            or [
                f"Leadership reinforces {phil.lower()} when stakes rise, not only in calm periods.",
                "Teams have clear ownership at interfaces between functions.",
            ],
        },
        core_organizational_insight="",
        sources=featured,
        sources_more=more,
        gap_notice=gap,
        contradicting_philosophies=[p.get("label", "") for p in bundle.contradicting_philosophies],
    )
    return enrich_response(bundle, response, synthesis_path="fallback")


def _as_string_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if ";" in text:
            return [part.strip() for part in text.split(";") if part.strip()]
        return [text]
    return []


def _llm_payload_recognized(data: dict) -> bool:
    markers = (
        "transformation_name",
        "philosophy_label",
        "headline",
        "what_youre_trying_to_change",
        "environment_readiness",
        "first_bottleneck",
    )
    return any(key in data for key in markers)


def _merge_with_fallback_scaffold(data: dict, bundle: RetrievalBundle) -> dict:
    """Fill missing/invalid LLM fields from corpus fallback so validation succeeds."""
    scaffold = _fallback_response(bundle).model_dump()
    if not _llm_payload_recognized(data):
        merged = {**scaffold, **{k: v for k, v in data.items() if v is not None}}
        merged["confidence"] = bundle.confidence
        merged["confidence_reason"] = bundle.confidence_reason
        return merged

    for key, scaffold_val in scaffold.items():
        if key in ("gap_notice", "synthesis_path", "sources_more"):
            continue
        val = data.get(key)
        if val is None or val == "" or val == {} or val == []:
            data[key] = scaffold_val
        elif isinstance(scaffold_val, dict) and isinstance(val, dict):
            for sub_key, sub_val in scaffold_val.items():
                if not val.get(sub_key):
                    val[sub_key] = sub_val
    data.setdefault("confidence", bundle.confidence)
    data.setdefault("confidence_reason", bundle.confidence_reason)
    return data


def _coerce_flat_llm_fields(data: dict) -> None:
    """GPT sometimes returns prose strings where the schema expects nested objects."""
    if isinstance(data.get("what_youre_trying_to_change"), str):
        text = data["what_youre_trying_to_change"]
        data["what_youre_trying_to_change"] = {"goal": text, "operational_meaning": text}

    readiness = data.get("environment_readiness")
    if isinstance(readiness, str):
        data["environment_readiness"] = {
            "supporting_conditions": [],
            "resisting_conditions": [],
            "readiness_summary": readiness,
        }
    elif isinstance(readiness, dict):
        for field in ("supporting_conditions", "resisting_conditions"):
            if field in readiness:
                readiness[field] = _as_string_list(readiness[field])

    if isinstance(data.get("first_bottleneck"), str):
        text = data["first_bottleneck"]
        data["first_bottleneck"] = {
            "bottleneck": text,
            "what_teams_usually_do_next": "Teams add reviews or workarounds to protect near-term delivery.",
            "unintended_effect": "The workaround slows the transformation while feeling responsible.",
        }

    resistance = data.get("likely_resistance")
    if isinstance(resistance, str):
        data["likely_resistance"] = {"patterns": _as_string_list(resistance)}
    elif isinstance(resistance, dict) and isinstance(resistance.get("patterns"), str):
        resistance["patterns"] = _as_string_list(resistance["patterns"])

    drive = data.get("how_to_drive_change")
    if isinstance(drive, str):
        data["how_to_drive_change"] = {
            "start_with": _as_string_list(drive),
            "avoid": [],
            "introduce_later": [],
        }
    elif isinstance(drive, dict):
        for field in ("start_with", "avoid", "introduce_later"):
            if field in drive:
                drive[field] = _as_string_list(drive[field])

    measure = data.get("what_to_measure")
    if isinstance(measure, str):
        data["what_to_measure"] = {"positive_signals": [measure], "warning_signs": []}
    elif isinstance(measure, dict):
        for field in ("positive_signals", "warning_signs"):
            if field in measure:
                measure[field] = _as_string_list(measure[field])

    correction = data.get("when_to_course_correct")
    if isinstance(correction, str):
        data["when_to_course_correct"] = {
            "course_correct_if": _as_string_list(correction),
            "typical_adaptation": correction,
        }
    elif isinstance(correction, dict) and isinstance(correction.get("course_correct_if"), str):
        correction["course_correct_if"] = _as_string_list(correction["course_correct_if"])

    works = data.get("where_this_works_best")
    if isinstance(works, str):
        data["where_this_works_best"] = {"conditions": _as_string_list(works)}
    elif isinstance(works, dict) and isinstance(works.get("conditions"), str):
        works["conditions"] = _as_string_list(works["conditions"])

    yv = data.get("your_version")
    if isinstance(yv, str):
        data["your_version"] = {"title": "", "keep": [], "modify": [], "add": _as_string_list(yv), "watch_for": []}
    elif isinstance(yv, dict):
        for field in ("keep", "modify", "add", "watch_for"):
            if field in yv:
                yv[field] = _as_string_list(yv[field])


def _coerce_response_shape(data: dict) -> dict:
    """Map legacy LLM shapes and fill required fields before validation."""
    ps = data.get("pressure_simulation") or data.get("simulation") or {}
    nuance = data.get("nuance") or {}
    diag = data.get("diagnosis") or {}
    adapt = data.get("adaptation") or {}

    _coerce_flat_llm_fields(data)

    if not data.get("headline"):
        data["headline"] = diag.get("mismatch_summary") or ""

    if "what_youre_trying_to_change" not in data:
        data["what_youre_trying_to_change"] = {
            "goal": data.get("headline") or data.get("transformation_name") or "Change the operating model.",
            "operational_meaning": (
                nuance.get("tradeoff")
                or diag.get("mismatch_summary")
                or "Change how teams make decisions and handle pressure day to day."
            ),
        }

    readiness = data.setdefault("environment_readiness", {})
    if isinstance(readiness, dict):
        readiness.setdefault("supporting_conditions", list(adapt.get("keep") or [])[:3])
        readiness.setdefault(
            "resisting_conditions",
            list(diag.get("organizational_distortions") or [])[:3],
        )
        readiness.setdefault(
            "readiness_summary",
            nuance.get("hidden_illusion")
            or "The environment has useful support and hidden friction; readiness is not binary.",
        )

    bottleneck = data.setdefault("first_bottleneck", {})
    if isinstance(bottleneck, dict):
        collapses = list(ps.get("where_this_collapses") or [])
        bottleneck.setdefault(
            "bottleneck",
            collapses[0] if collapses else diag.get("collapse_pattern") or "Pressure exposes unclear ownership.",
        )
        bottleneck.setdefault(
            "what_teams_usually_do_next",
            "Teams add reviews, escalations, or workarounds to protect delivery.",
        )
        bottleneck.setdefault(
            "unintended_effect",
            "Coordination overhead rises and the transformation starts feeling slower than the old system.",
        )

    resistance = data.setdefault("likely_resistance", {})
    if isinstance(resistance, dict):
        resistance.setdefault(
            "patterns",
            list(ps.get("under_stress_behaviors") or [])[:5]
            or ["Teams agree with the philosophy but revert under pressure."],
        )

    drive = data.setdefault("how_to_drive_change", {})
    if isinstance(drive, dict):
        drive.setdefault("start_with", list(adapt.get("steps") or [])[:3])
        drive.setdefault("avoid", ["Do not add heavy governance before the first bottleneck is clear."])
        drive.setdefault("introduce_later", list(adapt.get("modify") or adapt.get("add") or [])[:3])

    measure = data.setdefault("what_to_measure", {})
    if isinstance(measure, dict):
        measure.setdefault(
            "positive_signals",
            ["Teams follow the intended behavior without escalation."],
        )
        measure.setdefault(
            "warning_signs",
            list(ps.get("early_warning_signs") or [])[:4]
            or ["Exception requests rise.", "Teams bypass the system under pressure."],
        )

    correction = data.setdefault("when_to_course_correct", {})
    if isinstance(correction, dict):
        correction.setdefault(
            "course_correct_if",
            list(ps.get("where_this_collapses") or [])[:4]
            or ["The transformation starts creating the opposite effect."],
        )
        correction.setdefault(
            "typical_adaptation",
            "Use lighter coordination and clearer pressure rules before adding stricter process.",
        )

    works = data.setdefault("where_this_works_best", {})
    if isinstance(works, dict):
        works.setdefault(
            "conditions",
            [nuance.get("works_well_when") or "Teams have clear ownership and stable priorities."],
        )

    data.setdefault("core_organizational_insight", data.get("closing_insight") or data.get("headline", "Pressure changes behavior faster than systems adapt."))
    data.setdefault("transformation_name", data.get("philosophy_label") or "Transformation")
    data.setdefault("sources_more", data.get("sources_more") or [])

    yv = data.get("your_version") or {}
    adapt = data.get("adaptation") or {}
    if not yv or not yv.get("keep"):
        data["your_version"] = {
            "title": data.get("your_version", {}).get("title", ""),
            "keep": list(adapt.get("keep") or [])[:3],
            "modify": list(adapt.get("modify") or [])[:3],
            "add": list(adapt.get("add") or adapt.get("steps") or [])[:3],
            "watch_for": list(adapt.get("watch_for") or [])[:4],
        }

    return data


def _source_dict_from_object(obj: dict) -> dict:
    return {
        "intelligence_id": obj.get("intelligence_id", ""),
        "pattern_name": obj.get("pattern_name", ""),
        "source_guest": obj.get("source_guest", ""),
        "source_episode": obj.get("source_episode"),
        "quote": (obj.get("source_quote_or_context") or "")[:300],
    }


def _coerce_llm_sources(raw: list | None, bundle: RetrievalBundle) -> list[dict]:
    """Normalize LLM source shapes (dicts, bare ids, or invalid entries)."""
    by_id = {
        o.get("intelligence_id"): o
        for o in bundle.intelligence_objects
        if o.get("intelligence_id")
    }
    out: list[dict] = []
    for item in raw or []:
        if isinstance(item, dict):
            iid = item.get("intelligence_id")
            if iid and iid in by_id:
                merged = {**_source_dict_from_object(by_id[iid]), **item}
                out.append(merged)
            elif item.get("pattern_name") or item.get("source_guest"):
                out.append(item)
            continue
        if isinstance(item, str):
            key = item.strip()
            if key in by_id:
                out.append(_source_dict_from_object(by_id[key]))
    return out


def _normalize_response(data: dict, bundle: RetrievalBundle) -> dict:
    data["philosophy_label"] = _user_facing_label(bundle) or data.get("philosophy_label", "")
    data["transformation_name"] = data.get("transformation_name") or data["philosophy_label"]
    data["confidence"] = bundle.confidence
    data["confidence_reason"] = bundle.confidence_reason

    allowed_ids = {o.get("intelligence_id") for o in bundle.intelligence_objects}
    data["sources"] = _coerce_llm_sources(data.get("sources"), bundle)
    if allowed_ids:
        data["sources"] = [
            s
            for s in data["sources"]
            if not s.get("intelligence_id") or s.get("intelligence_id") in allowed_ids
        ]
    if not data.get("sources") and bundle.intelligence_objects:
        data["sources"] = [
            _source_dict_from_object(o) for o in bundle.intelligence_objects[:2]
        ]

    if not data.get("contradicting_philosophies"):
        data["contradicting_philosophies"] = [
            p.get("label", "") for p in bundle.contradicting_philosophies
        ]

    citations = []
    for s in data.get("sources") or []:
        citations.append(SourceCitation.model_validate(s))
    featured, more = _split_sources(citations)
    data["sources"] = [s.model_dump() for s in featured]

    more_raw = _coerce_llm_sources(data.get("sources_more"), bundle)
    for s in more_raw:
        if isinstance(s, dict):
            try:
                more.append(SourceCitation.model_validate(s))
            except Exception:
                continue
    data["sources_more"] = [s.model_dump() if hasattr(s, "model_dump") else s for s in more]
    return data


async def _call_openai(bundle: RetrievalBundle) -> RealityCheckResponse:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
    )
    user_prompt = build_user_prompt(bundle)

    kwargs: dict = {
        "model": settings.openai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.4,
        "max_tokens": settings.openai_max_tokens,
    }
    if settings.openai_use_json_schema:
        kwargs["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "reality_check_response",
                "schema": RealityCheckResponse.model_json_schema(),
                "strict": False,
            },
        }
    else:
        kwargs["response_format"] = {"type": "json_object"}

    response = await client.chat.completions.create(**kwargs)
    raw = response.choices[0].message.content
    if not raw:
        raise ValueError("empty LLM response")
    payload = json.loads(raw)
    if not _llm_payload_recognized(payload):
        return _fallback_response(bundle).model_copy(update={"synthesis_path": "llm_scaffold"})

    data = _normalize_response(_coerce_response_shape(payload), bundle)
    try:
        parsed = RealityCheckResponse.model_validate(data)
    except Exception:
        data = _merge_with_fallback_scaffold(data, bundle)
        parsed = RealityCheckResponse.model_validate(data)
    return enrich_response(bundle, parsed, synthesis_path="llm")


def _validated_fallback(
    bundle: RetrievalBundle,
    path: str,
    gap_prefix: str | None = None,
) -> RealityCheckResponse:
    out = _fallback_response(bundle)
    if gap_prefix:
        existing = (out.gap_notice or "").strip()
        out.gap_notice = f"{gap_prefix} {existing}".strip() if existing else gap_prefix
    return out.model_copy(update={"synthesis_path": path})


async def synthesize_with_meta(bundle: RetrievalBundle) -> tuple[RealityCheckResponse, str]:
    if settings.reality_check_skip_llm or not settings.openai_api_key:
        out = _fallback_response(bundle)
        return out.model_copy(update={"synthesis_path": "fallback"}), "fallback"

    try:
        out = await asyncio.wait_for(
            _call_openai(bundle),
            timeout=settings.openai_timeout_seconds,
        )
        issues = validate_response_data(out.model_dump(), bundle)
        if issues:
            return _validated_fallback(
                bundle,
                "fallback_validated",
                "Generated narrative did not pass quality checks — showing corpus-grounded guidance.",
            ), "fallback_validated"
        return out.model_copy(update={"synthesis_path": "llm"}), "llm"
    except asyncio.TimeoutError:
        return _validated_fallback(
            bundle,
            "fallback_timeout",
            "OpenAI took longer than expected — showing a corpus-based preview.",
        ), "fallback_timeout"
    except json.JSONDecodeError:
        return _validated_fallback(
            bundle,
            "fallback_error",
            "OpenAI returned invalid JSON — showing corpus-based guidance grounded in your answers.",
        ), "fallback_error"
    except Exception as exc:
        detail = type(exc).__name__
        if settings.openai_model:
            detail = f"{detail} ({settings.openai_model})"
        return _validated_fallback(
            bundle,
            "fallback_error",
            (
                "OpenAI could not be reached — showing corpus-based guidance grounded in your answers. "
                f"({detail})"
            ),
        ), "fallback_error"


async def synthesize(bundle: RetrievalBundle) -> RealityCheckResponse:
    result, _ = await synthesize_with_meta(bundle)
    return result
