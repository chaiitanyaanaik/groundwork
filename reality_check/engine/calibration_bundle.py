from __future__ import annotations

from reality_check.engine.loader import (
    load_calibration,
    load_philosophy_questions,
    philosophy_by_id,
    questions_by_id,
)


def get_calibration_for_philosophy(philosophy_id: str) -> dict:
    """Merge universal, philosophy-specific, and conditional calibration questions."""
    if philosophy_id not in philosophy_by_id():
        raise ValueError(f"Unknown philosophy_id: {philosophy_id}")

    pq = load_philosophy_questions()
    q_by_id = questions_by_id()

    ordered_ids: list[str] = list(pq["universal_question_ids"])
    phil_qid = pq["philosophy_question_ids"].get(philosophy_id)
    if phil_qid:
        ordered_ids.append(phil_qid)

    for cond in pq.get("conditional_questions", []):
        if philosophy_id in cond.get("applies_to_philosophy_ids", []):
            qid = cond["question_id"]
            if qid not in ordered_ids:
                ordered_ids.append(qid)

    questions = []
    for qid in ordered_ids:
        if qid not in q_by_id:
            raise ValueError(f"Calibration question not found: {qid}")
        questions.append(q_by_id[qid])

    return {
        "philosophy_id": philosophy_id,
        "questions": questions,
        "question_count": len(questions),
        "role_options": pq.get("role_options", []),
    }


def role_label(user_role: str | None) -> str:
    if not user_role:
        return "leader (role not specified)"
    for opt in load_philosophy_questions().get("role_options", []):
        if opt["id"] == user_role:
            return opt["label"]
    return user_role
