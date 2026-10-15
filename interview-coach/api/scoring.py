from typing import Any

from .models import AnswerEvaluation

WEIGHTS = {
    "relevance": 0.20,
    "technical_correctness": 0.20,
    "ownership": 0.15,
    "reasoning": 0.15,
    "validation": 0.10,
    "depth": 0.10,
    "specificity": 0.05,
    "communication": 0.05,
}

SCORE_FIELDS = tuple(WEIGHTS)


def _as_score(value: Any) -> int:
    """Convert a model-provided dimension to a safe 0-100 integer."""
    if isinstance(value, bool):
        return 0
    try:
        score = round(float(value))
    except (TypeError, ValueError):
        return 0
    return max(0, min(100, score))


def _as_text_list(value: Any) -> list[str]:
    """Providers sometimes return a single string where the schema expects a list."""
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        # Split common newline/bullet-separated output without splitting every sentence.
        lines = [line.strip(" -•\\t") for line in text.splitlines() if line.strip(" -•\\t")]
        return lines or [text]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if item is not None and str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def apply_rubric_result(payload: dict, provider: str) -> AnswerEvaluation:
    """Normalize inconsistent LLM JSON, validate it, and calculate the canonical score.

    Missing score dimensions are conservatively set to zero rather than guessed.
    The provider's overall score is ignored; the weighted rubric is the single source
    of truth across Gemini and OpenRouter.
    """
    clean = dict(payload)
    clean.pop("_evaluation_provider", None)

    for field in SCORE_FIELDS:
        clean[field] = _as_score(clean.get(field, 0))

    clean["strengths"] = _as_text_list(clean.get("strengths"))
    clean["weaknesses"] = _as_text_list(clean.get("weaknesses"))
    if not isinstance(clean.get("follow_up_question"), str):
        clean["follow_up_question"] = ""
    if not isinstance(clean.get("next_focus"), str) or not clean["next_focus"].strip():
        clean["next_focus"] = "specificity"

    clean.update({
        "evaluation_provider": provider if provider in {"gemini", "openrouter"} else "heuristic",
        "evaluation_method": "llm_rubric",
        "confidence": "medium",
    })
    result = AnswerEvaluation.model_validate(clean)
    weighted = sum(getattr(result, name) * weight for name, weight in WEIGHTS.items())
    result.score = round(weighted)
    return result
