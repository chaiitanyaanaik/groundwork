from __future__ import annotations

from compress_patterns import kw_in_blob, norm_text, obj_blob
from reality_check.engine.loader import (
    intelligence_by_id,
    meta_pattern_by_id,
    normalized_pattern_by_meta_id,
)


def _keyword_hits(blob: str, keywords: list[str]) -> int:
    blob_l = blob.lower()
    hits = 0
    for kw in keywords:
        k = kw.lower().strip()
        if len(k) < 3:
            continue
        if k in blob_l:
            hits += 1
    return hits


def _score_object_against_tags(obj: dict, tags: set[str]) -> float:
    blob = obj_blob(obj)
    score = 0.0
    for tag in tags:
        if len(tag) < 4:
            continue
        if kw_in_blob(tag, blob):
            score += 2.0
    return score


def philosophy_linked_meta_ids(philosophy: dict) -> set[str]:
    return set(philosophy.get("meta_pattern_ids") or [])


def object_text_blob(obj: dict) -> str:
    return norm_text(
        f"{obj.get('pattern_name', '')} {obj.get('core_belief', '')} "
        f"{obj.get('operational_pattern', '')} {' '.join(obj.get('hidden_assumptions') or [])}"
    )


def object_philosophy_relevance(obj: dict, philosophy: dict) -> float:
    """Higher = more aligned with this philosophy's vocabulary."""
    blob = object_text_blob(obj)
    score = float(_keyword_hits(blob, philosophy.get("keywords", []))) * 4.0

    linked = philosophy_linked_meta_ids(philosophy)
    iid = obj.get("intelligence_id", "")
    norm_by_meta = normalized_pattern_by_meta_id()
    for mid in linked:
        norm = norm_by_meta.get(mid) or {}
        for ref in norm.get("supporting_objects", []):
            if ref.get("intelligence_id") == iid:
                score += 3.0
                break

    return score


def object_matches_philosophy(obj: dict, philosophy: dict, *, min_keyword_hits: int = 1) -> bool:
    """Require philosophy vocabulary in the object itself — linked-list membership is not enough."""
    blob = object_text_blob(obj)
    kw_hits = _keyword_hits(blob, philosophy.get("keywords", []))
    if philosophy.get("id") == "custom":
        custom_kws = philosophy.get("keywords", [])
        return kw_hits >= 1 or _keyword_hits(blob, custom_kws) >= 1
    return kw_hits >= min_keyword_hits


def filter_objects_for_philosophy(
    objects: list[dict],
    philosophy: dict,
    *,
    limit: int | None = None,
) -> list[dict]:
    scored: list[tuple[float, dict]] = []
    for obj in objects:
        if object_matches_philosophy(obj, philosophy):
            scored.append((object_philosophy_relevance(obj, philosophy), obj))
    scored.sort(key=lambda x: -x[0])
    out = [obj for _, obj in scored]
    if limit:
        return out[:limit]
    return out


def _score_and_add(
    scored: list[tuple[float, dict]],
    seen: set[str],
    obj: dict,
    philosophy: dict,
    tags: set[str],
    base_score: float = 0.0,
) -> None:
    iid = obj.get("intelligence_id")
    if not iid or iid in seen:
        return
    if not object_matches_philosophy(obj, philosophy):
        return
    seen.add(iid)
    score = (
        object_philosophy_relevance(obj, philosophy)
        + base_score
        + _score_object_against_tags(obj, tags) * 0.5
    )
    scored.append((score, obj))


def _objects_from_normalized_refs(
    linked_ids: set[str],
    meta_items: list[dict],
    philosophy: dict,
    tags: set[str],
    scored: list[tuple[float, dict]],
    seen: set[str],
) -> None:
    norm_by_meta = normalized_pattern_by_meta_id()
    meta_by_id = meta_pattern_by_id()
    by_id = intelligence_by_id()
    score_by_mid = {m.get("meta_id"): m.get("score", 0) for m in meta_items}

    for mid in linked_ids:
        norm = norm_by_meta.get(mid) or {}
        for ref in norm.get("supporting_objects", [])[:8]:
            obj = by_id.get(ref.get("intelligence_id", ""))
            if obj:
                _score_and_add(scored, seen, obj, philosophy, tags, score_by_mid.get(mid, 0) * 0.1)


def _objects_from_meta_keywords(
    linked_ids: set[str],
    philosophy: dict,
    tags: set[str],
    scored: list[tuple[float, dict]],
    seen: set[str],
) -> None:
    """When normalized patterns lack refs, match corpus objects to meta + philosophy keywords."""
    meta_by_id = meta_pattern_by_id()
    by_id = intelligence_by_id()
    keyword_set: list[str] = list(philosophy.get("keywords", []))
    for mid in linked_ids:
        meta = meta_by_id.get(mid) or {}
        keyword_set.extend(meta.get("keywords", []))

    for obj in by_id.values():
        blob = object_text_blob(obj)
        if not any(kw_in_blob(kw, blob) for kw in keyword_set if len(kw) >= 3):
            continue
        _score_and_add(scored, seen, obj, philosophy, tags, base_score=2.0)


def search_objects_for_philosophy(
    philosophy: dict,
    tags: set[str],
    limit: int,
) -> list[dict]:
    """Corpus-wide fallback scoped to philosophy vocabulary."""
    scored: list[tuple[float, dict]] = []
    for obj in intelligence_by_id().values():
        if not object_matches_philosophy(obj, philosophy):
            continue
        score = object_philosophy_relevance(obj, philosophy) + _score_object_against_tags(obj, tags)
        if score > 0:
            scored.append((score, obj))
    scored.sort(key=lambda x: -x[0])
    return [obj for _, obj in scored[:limit]]


def gather_linked_objects(
    meta_items: list[dict],
    philosophy: dict,
    tags: set[str],
    limit: int,
) -> list[dict]:
    """Objects from linked meta-patterns; fall back to keyword search when refs are missing."""
    linked_ids = philosophy_linked_meta_ids(philosophy)
    scored: list[tuple[float, dict]] = []
    seen: set[str] = set()

    _objects_from_normalized_refs(linked_ids, meta_items, philosophy, tags, scored, seen)
    if len(scored) < limit:
        _objects_from_meta_keywords(linked_ids, philosophy, tags, scored, seen)

    scored.sort(key=lambda x: -x[0])
    out = [obj for _, obj in scored[:limit]]
    if len(out) < limit:
        for obj in search_objects_for_philosophy(philosophy, tags, limit):
            iid = obj.get("intelligence_id")
            if iid and iid not in seen:
                out.append(obj)
                seen.add(iid)
            if len(out) >= limit:
                break
    return out[:limit]


def text_matches_philosophy(text: str, philosophy: dict) -> bool:
    if not text.strip():
        return True
    return _keyword_hits(norm_text(text), philosophy.get("keywords", [])) >= 1
