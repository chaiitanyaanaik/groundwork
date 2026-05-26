"""Rubric dimensions for LLM-as-judge evals.

Each dimension is scored 1–5. See evals/README.md for anchor descriptions.
"""

DIMENSIONS: list[dict[str, str]] = [
    {
        "id": "mismatch_clarity",
        "name": "Mismatch clarity",
        "question": "Does the headline clearly express 'you want X, but Y happens in this org' using human language?",
    },
    {
        "id": "calibration_use",
        "name": "Calibration use",
        "question": "Does the output reflect at least two specific calibration answers (not pasted question text)?",
    },
    {
        "id": "actionability",
        "name": "Actionability",
        "question": "Could a PM or leader name at least one concrete action for the next 30 days?",
    },
    {
        "id": "philosophy_grounding",
        "name": "Philosophy grounding",
        "question": "Is advice specific to the selected philosophy/aspiration (not generic velocity/AI platitudes)?",
    },
    {
        "id": "tone",
        "name": "Tone",
        "question": "Does it read as a stress-test of advice (empathetic, direct) rather than an organizational audit or consultant deck?",
    },
    {
        "id": "evidence_hygiene",
        "name": "Evidence hygiene",
        "question": "Are sources present and plausible, with no obvious debug/corpus artifacts in user-facing copy?",
    },
]

PASS_OVERALL_MIN = 3.8
PASS_DIMENSION_MIN = 3
