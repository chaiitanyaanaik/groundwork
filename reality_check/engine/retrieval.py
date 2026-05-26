from __future__ import annotations

import re
from dataclasses import dataclass, field

from reality_check.config import settings
from reality_check.engine.distortions import collect_calibration_tags, resolve_distortion_profiles
from reality_check.engine.relevance import gather_linked_objects, object_philosophy_relevance
from reality_check.engine.loader import (
    intelligence_by_id,
    meta_pattern_by_id,
    normalized_pattern_by_meta_id,
    philosophy_by_id,
)
from compress_patterns import META_PATTERNS, norm_text, obj_blob, kw_in_blob


@dataclass
class RetrievalBundle:
    philosophy: dict
    org_summary: dict
    distortion_profiles: list[dict]
    meta_patterns: list[dict]
    intelligence_objects: list[dict]
    contradicting_philosophies: list[dict]
    confidence: str
    confidence_reason: str
    retrieval_scores: dict = field(default_factory=dict)
    aspiration: dict | None = None


def _score_object_against_tags(obj: dict, tags: set[str]) -> float:
    blob = obj_blob(obj)
    score = 0.0
    for tag in tags:
        if len(tag) < 4:
            continue
        if kw_in_blob(tag, blob):
            score += 2.0
    return score


def _resolve_philosophy(philosophy_id: str | None, custom_philosophy: str | None) -> dict:
    by_id = philosophy_by_id()
    if philosophy_id and philosophy_id in by_id:
        return by_id[philosophy_id]
    if custom_philosophy:
        return {
            "id": "custom",
            "label": custom_philosophy[:120],
            "tagline": "Custom philosophy",
            "user_facing_hook": custom_philosophy,
            "keywords": re.findall(r"[a-zA-Z]{4,}", custom_philosophy.lower()),
            "meta_pattern_ids": [],
            "contradicting_philosophy_ids": [],
        }
    raise ValueError("philosophy_id or custom_philosophy required")


def _rank_meta_patterns(philosophy: dict, tags: set[str], distortions: list[dict]) -> list[dict]:
    linked = set(philosophy.get("meta_pattern_ids", []))
    norm_by_meta = normalized_pattern_by_meta_id()
    meta_by_id = meta_pattern_by_id()
    scored: list[tuple[float, str, dict]] = []

    for meta in META_PATTERNS:
        mid = meta["id"]
        score = 0.0
        if mid in linked:
            score += 10.0
        for kw in philosophy.get("keywords", []):
            if kw_in_blob(kw, norm_text(meta.get("pattern_name", "") + " " + meta.get("description", ""))):
                score += 3.0
        for tag in tags:
            if kw_in_blob(tag, norm_text(" ".join(meta.get("keywords", [])))):
                score += 1.5
        for d in distortions:
            cp = d.get("collapse_pattern", "")
            if cp and kw_in_blob(norm_text(cp), norm_text(meta["pattern_name"])):
                score += 5.0
        if score > 0:
            enriched = {
                "meta_id": mid,
                "meta": meta,
                "normalized": norm_by_meta.get(mid),
                "score": score,
            }
            scored.append((score, mid, enriched))

    scored.sort(key=lambda x: -x[0])
    seen = set()
    out = []
    for _, mid, item in scored:
        if mid in seen:
            continue
        seen.add(mid)
        out.append(item)
        if len(out) >= 4:
            break
    return out


def _gather_objects(
    meta_items: list[dict],
    tags: set[str],
    philosophy: dict,
    limit: int | None = None,
) -> list[dict]:
    """Philosophy-scoped retrieval only — no full-corpus bleed from shared calibration tags."""
    limit = limit or settings.retrieval_object_limit
    return gather_linked_objects(meta_items, philosophy, tags, limit)


def compute_confidence(
    philosophy: dict,
    meta_items: list[dict],
    objects: list[dict],
    tags: set[str],
    distortions: list[dict],
) -> tuple[str, str]:
    linked_ids = set(philosophy.get("meta_pattern_ids", []))
    linked_hits = sum(1 for m in meta_items if m["meta_id"] in linked_ids)
    object_count = len(objects)

    if object_count == 0:
        return "none", "No corpus objects matched this philosophy and org profile"

    if philosophy.get("id") == "custom" and linked_hits == 0:
        return "low", "Custom philosophy with weak corpus overlap"

    strong_objects = sum(
        1 for o in objects if object_philosophy_relevance(o, philosophy) >= 4.0
    )
    tag_object_hits = sum(1 for o in objects if _score_object_against_tags(o, tags) >= 2)

    if object_count < 2:
        return (
            "partial",
            f"Limited corpus grounding ({object_count} pattern) — treat as directional",
        )

    if linked_hits >= 1 and strong_objects >= 2 and (tag_object_hits >= 1 or distortions):
        return (
            "high",
            f"Strong match — {object_count} grounded patterns for this philosophy and org",
        )

    if strong_objects >= 1 or linked_hits >= 1:
        return (
            "partial",
            f"Partial match — {object_count} patterns; some may be keyword-adjacent",
        )

    return (
        "low",
        f"Weak match — {object_count} adjacent patterns only; verify before acting",
    )


def retrieve(
    philosophy_id: str | None,
    org_profile: dict,
    custom_philosophy: str | None = None,
    aspiration: dict | None = None,
) -> RetrievalBundle:
    philosophy = _resolve_philosophy(philosophy_id, custom_philosophy)
    calibration = org_profile.get("calibration") or {}
    tags = collect_calibration_tags(calibration)
    distortions = resolve_distortion_profiles(calibration)

    meta_items = _rank_meta_patterns(philosophy, tags, distortions)
    if not meta_items and philosophy.get("meta_pattern_ids"):
        meta_by_id = meta_pattern_by_id()
        norm_by_meta = normalized_pattern_by_meta_id()
        for mid in philosophy["meta_pattern_ids"]:
            if mid in meta_by_id:
                meta_items.append(
                    {
                        "meta_id": mid,
                        "meta": meta_by_id[mid],
                        "normalized": norm_by_meta.get(mid),
                        "score": 10.0,
                    }
                )

    objects = _gather_objects(meta_items, tags, philosophy)

    contra_ids = philosophy.get("contradicting_philosophy_ids", [])
    by_id = philosophy_by_id()
    contradicting = [by_id[cid] for cid in contra_ids if cid in by_id]

    confidence, reason = compute_confidence(philosophy, meta_items, objects, tags, distortions)

    return RetrievalBundle(
        philosophy=philosophy,
        org_summary={
            "stage": org_profile.get("stage"),
            "size": org_profile.get("size"),
            "model": org_profile.get("model"),
            "user_role": org_profile.get("user_role"),
            "calibration": calibration,
        },
        distortion_profiles=distortions,
        meta_patterns=meta_items,
        intelligence_objects=objects,
        contradicting_philosophies=contradicting,
        confidence=confidence,
        confidence_reason=reason,
        retrieval_scores={
            "meta_pattern_count": len(meta_items),
            "object_count": len(objects),
            "distortion_count": len(distortions),
        },
        aspiration=aspiration,
    )
