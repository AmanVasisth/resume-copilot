import os
import json
import logging
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
# Load the API-local .env reliably, regardless of the directory used to start uvicorn.
load_dotenv(Path(__file__).with_name(".env"))

SYSTEM = """You are CareerCoach AI, an expert interviewer for professional data, BI, software and AI roles.
Evaluate answers like a demanding but fair senior interviewer. Do not reward keyword stuffing.
Prioritize correctness, ownership, reasoning, trade-offs, evidence, scale, failure handling and business impact.
Return ONLY valid JSON matching the requested schema."""

def _provider():
    return os.getenv("LLM_PROVIDER", "none").lower()

def _openrouter(prompt: str) -> dict[str, Any] | None:
    key = os.getenv("OPENROUTER_API_KEY")
    # OpenRouter uses a separate model setting so it can act as a fallback
    # even when LLM_MODEL is configured for Gemini.
    model = os.getenv("OPENROUTER_MODEL", "openrouter/free")
    if not key:
        return None
    try:
        import requests
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": model, "messages":[{"role":"system","content":SYSTEM},{"role":"user","content":prompt}],
                  "response_format":{"type":"json_object"}, "temperature":0.2},
            timeout=45,
        )
        if not r.ok:
            # Log status and provider's safe error message, never the API key.
            try:
                detail = r.json().get("error", {}).get("message", "No error message returned")
            except Exception:
                detail = "No error message returned"
            logger.warning("OpenRouter API HTTP %s: %s", r.status_code, detail[:500])
            return None
        try:
            body = r.json()
            content = body["choices"][0]["message"]["content"]
            if not isinstance(content, str):
                logger.warning("OpenRouter returned non-text message content.")
                return None
            return json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            logger.warning("OpenRouter response format invalid (%s).", type(exc).__name__)
            return None
    except Exception as exc:
        logger.warning("OpenRouter request failed (%s).", type(exc).__name__)
        return None

def _gemini(prompt: str) -> dict[str, Any] | None:
    key = os.getenv("GEMINI_API_KEY")
    model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    if not key:
        logger.warning("GEMINI_API_KEY is not configured; using fallback evaluator.")
        return None
    try:
        import requests
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        r = requests.post(
            url,
            headers={"x-goog-api-key": key, "Content-Type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": SYSTEM}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
            },
            timeout=45,
        )
        if not r.ok:
            # Log Google's safe error message (never log the API key).
            try:
                detail = r.json().get("error", {}).get("message", "No error message returned")
            except Exception:
                detail = "No error message returned"
            logger.warning("Gemini API HTTP %s: %s", r.status_code, detail)
            return None
        payload = r.json()
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(text)
    except Exception as exc:
        logger.warning("Gemini evaluation unavailable (%s); using fallback evaluator.", type(exc).__name__)
        return None

def evaluate_with_llm(question, answer, candidate):
    prompt = f"""You are grading a professional interview answer. Be evidence-based, calibrated, and consistent across providers.
Do not reward length, confidence, grammar alone, or keyword stuffing. Never invent facts or metrics. Treat hypothetical wording ("I would test", "I would measure") as a proposed plan, NOT completed validation or an achieved result.
Score each dimension independently from 0 to 100:
- relevance: 0=unrelated, 25=topic only, 50=partially answers, 75=answers most asks, 100=fully addresses the exact question.
- technical_correctness: 0=wrong/unrelated, 25=generic, 50=some correct specifics, 75=technically solid, 100=precise and defensible.
- ownership: 0=no contribution, 25=generic "worked on it", 50=some tasks, 75=clear individual ownership, 100=clear decisions and accountable implementation.
- reasoning: 0=no reasoning, 25=names a choice only, 50=some rationale, 75=compares alternatives and trade-offs, 100=strong evidence-backed reasoning.
- validation: 0=none, 25=only says tested/would test, 50=method without results, 75=real test evidence, 100=quantified and reproducible evidence.
- depth: 0=none, 25=surface-level, 50=useful implementation details, 75=deep implementation/failure handling, 100=senior-level detail and sound limits.
- specificity: 0=none, 25=generic, 50=some specifics, 75=concrete and attributable, 100=highly specific and verifiable.
- communication: clarity and structure only; do not let this inflate a technically weak answer.
Calculate overall score using this exact weighted formula, rounded to nearest integer:
overall = 0.20*relevance + 0.20*technical_correctness + 0.15*ownership + 0.15*reasoning + 0.10*validation + 0.10*depth + 0.05*specificity + 0.05*communication.
The "score" must equal that formula within 1 point. Do not choose the overall score by intuition.
Calibration checks:
- Irrelevant or very vague answers with no usable evidence: 0-15 overall.
- Some relevant technical details but mostly generic, hypothetical validation, no actual result: usually 25-50, depending on correctness and relevance. Do not automatically assign 5-15 just because metrics are missing.
- Clear implementation, sound reasoning and actual validation, but limited metrics: usually 50-70.
- Strong, specific, technically sound answer with clear personal ownership, trade-offs, completed validation and evidence: usually 70-90.
- 90+ requires exceptional, detailed, defensible evidence; polished generic answers do not qualify.
For project questions, assess business problem, personal contribution, design decision, trade-off, completed validation and actual outcome. Missing one dimension lowers that dimension; do not treat one missing metric as proof the entire answer is worthless.
A correct technical term is a positive signal but not proof of hands-on experience. Use candidate profile only as context; resume skills do not prove this answer's claims. Praise only evidence-backed strengths. If no genuine strength exists, return an empty strengths array.
Return integers 0-100 for every score and exactly these keys:
{{
  "score": 0,
  "relevance": 0,
  "technical_correctness": 0,
  "ownership": 0,
  "reasoning": 0,
  "validation": 0,
  "depth": 0,
  "specificity": 0,
  "communication": 0,
  "strengths": ["only evidence-backed strengths"],
  "weaknesses": ["specific missing or incorrect elements"],
  "follow_up_question": "one targeted follow-up or empty string",
  "next_focus": "the most important competency to improve"
}}
The follow-up must be based on this answer, not a generic template.

Candidate profile:
{candidate.model_dump_json(indent=2)}

Question:
{question.model_dump_json(indent=2)}

Candidate answer:
{answer}
"""
    provider = _provider()
    if provider == "openrouter":
        result = _openrouter(prompt)
        if result is not None:
            result["_evaluation_provider"] = "openrouter"
        return result
    if provider == "gemini":
        result = _gemini(prompt)
        if result is not None:
            result["_evaluation_provider"] = "gemini"
            return result
        # Optional cross-provider failover when Gemini is unavailable.
        if os.getenv("OPENROUTER_API_KEY"):
            logger.warning("Gemini unavailable; trying OpenRouter fallback.")
            result = _openrouter(prompt)
            if result is not None:
                result["_evaluation_provider"] = "openrouter"
            return result
        return None
    return None
