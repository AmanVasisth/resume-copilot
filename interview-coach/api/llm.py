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
    model = os.getenv("LLM_MODEL", "openai/gpt-4o-mini")
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
        r.raise_for_status()
        return json.loads(r.json()["choices"][0]["message"]["content"])
    except Exception as exc:
        logger.warning("LLM evaluation unavailable (%s); using fallback evaluator.", type(exc).__name__)
        return None

def evaluate_with_llm(question, answer, candidate):
    prompt = f"""You are grading a real professional interview answer. Be evidence-based, strict, and fair.
Do not give points for length, confidence, grammar alone, or repeating words from the question.
First determine whether the answer actually addresses the question. If it is vague, irrelevant, or merely says they did the project without specifics, the total score MUST be 0-15 and technical correctness/depth/reasoning/specificity must each be 0-10. A fluent but unrelated answer is not a strong answer.
Do not assume facts the candidate did not state. Do not invent missing details or metrics. Distinguish an incorrect claim from missing evidence.
Use this rubric:
- relevance to the exact question: 25%
- technical/role correctness: 25%
- personal ownership and specificity: 15%
- reasoning, design decisions and trade-offs: 15%
- validation and evidence of outcome: 10%
- communication clarity and structure: 10%
For project questions, check the business problem, personal contribution, design decision, trade-off, validation and actual result. Missing a requested dimension must lower the score.
For a short or vague answer, provide a low score and a helpful follow-up question that asks for the most important missing evidence. Praise only what is genuinely present. If an answer states no real experience, reward honesty but do not rate it as demonstrated technical competence.
Return integers 0-100 for component scores and overall score. Overall score must reflect the rubric, not an average inflated by communication.

Candidate profile:
{candidate.model_dump_json(indent=2)}

Question:
{question.model_dump_json(indent=2)}

Candidate answer:
{answer}

Return JSON with exactly these keys:
{{
  "score": 0,
  "technical_correctness": 0,
  "depth": 0,
  "reasoning": 0,
  "specificity": 0,
  "communication": 0,
  "strengths": ["only evidence-backed strengths"],
  "weaknesses": ["specific missing or incorrect elements"],
  "follow_up_question": "one targeted follow-up or empty string",
  "next_focus": "the most important competency to improve"
}}
The follow-up must be based on this answer, not a generic template."""
    if _provider() == "openrouter":
        return _openrouter(prompt)
    return None
