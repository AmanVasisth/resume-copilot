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

def apply_rubric_result(payload: dict, provider: str) -> AnswerEvaluation:
    """Validate provider output and calculate the one canonical weighted score."""
    clean = dict(payload)
    clean.pop("_evaluation_provider", None)
    result = AnswerEvaluation.model_validate({
        **clean,
        "evaluation_provider": provider if provider in {"gemini", "openrouter"} else "heuristic",
        "evaluation_method": "llm_rubric",
        "confidence": "medium",
    })
    weighted = sum(getattr(result, name) * weight for name, weight in WEIGHTS.items())
    result.score = round(weighted)
    return result
