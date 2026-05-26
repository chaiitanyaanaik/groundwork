from __future__ import annotations

import json
import sys
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CORPUS_ROOT = ROOT.parent

# Import META_PATTERNS from existing compress script at repo root
if str(CORPUS_ROOT) not in sys.path:
    sys.path.insert(0, str(CORPUS_ROOT))
from compress_patterns import META_PATTERNS  # noqa: E402


@lru_cache(maxsize=1)
def load_philosophies() -> dict:
    with open(DATA_DIR / "philosophies.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_aspirations() -> dict:
    with open(DATA_DIR / "aspirations.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_calibration() -> dict:
    with open(DATA_DIR / "calibration.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_philosophy_questions() -> dict:
    with open(DATA_DIR / "philosophy_questions.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def questions_by_id() -> dict[str, dict]:
    return {q["id"]: q for q in load_calibration()["questions"]}


@lru_cache(maxsize=1)
def load_intelligence_objects() -> list[dict]:
    path = CORPUS_ROOT / "reality-check-intelligence.json"
    with open(path) as f:
        data = json.load(f)
    return data["intelligence"]


@lru_cache(maxsize=1)
def load_normalized_patterns() -> list[dict]:
    path = CORPUS_ROOT / "normalized-intelligence.json"
    with open(path) as f:
        data = json.load(f)
    return data["patterns"]


@lru_cache(maxsize=1)
def intelligence_by_id() -> dict[str, dict]:
    return {obj["intelligence_id"]: obj for obj in load_intelligence_objects()}


@lru_cache(maxsize=1)
def meta_pattern_by_id() -> dict[str, dict]:
    return {m["id"]: m for m in META_PATTERNS}


@lru_cache(maxsize=1)
def normalized_pattern_by_meta_id() -> dict[str, dict]:
    """Map compress_patterns meta id → normalized-intelligence.json pattern blob."""
    name_to_meta = {m["pattern_name"]: m["id"] for m in META_PATTERNS}
    out: dict[str, dict] = {}
    for pat in load_normalized_patterns():
        meta_id = name_to_meta.get(pat["pattern_name"])
        if meta_id:
            out[meta_id] = pat
    return out


@lru_cache(maxsize=1)
def philosophy_by_id() -> dict[str, dict]:
    return {p["id"]: p for p in load_philosophies()["philosophies"]}


@lru_cache(maxsize=1)
def aspiration_by_id() -> dict[str, dict]:
    return {a["id"]: a for a in load_aspirations()["aspirations"]}


def resolve_philosophy_id(
    *,
    philosophy_id: str | None = None,
    aspiration_id: str | None = None,
) -> str:
    """Map user-facing aspiration to internal philosophy registry."""
    if aspiration_id:
        aspiration = aspiration_by_id().get(aspiration_id)
        if not aspiration:
            raise ValueError(f"Unknown aspiration_id: {aspiration_id}")
        philosophy_id = aspiration["philosophy_id"]
    if not philosophy_id:
        raise ValueError("philosophy_id or aspiration_id is required")
    if philosophy_id not in philosophy_by_id():
        raise ValueError(f"Unknown philosophy_id: {philosophy_id}")
    return philosophy_id


def corpus_stats() -> dict:
    return {
        "intelligence_objects": len(load_intelligence_objects()),
        "meta_patterns": len(META_PATTERNS),
        "normalized_patterns": len(load_normalized_patterns()),
        "philosophies": len(load_philosophies()["philosophies"]),
        "aspirations": len(load_aspirations()["aspirations"]),
    }
