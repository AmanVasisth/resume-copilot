import os
import json
from typing import Any

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
    except Exception:
        return None

def evaluate_with_llm(question, answer, candidate):
    prompt = f"""Evaluate this interview answer.

Candidate profile:
{candidate.model_dump_json(indent=2)}

Question:
{question.model_dump_json(indent=2)}

Answer:
{answer}

Return JSON with exactly:
{{
  "score": 0,
  "technical_correctness": 0,
  "depth": 0,
  "reasoning": 0,
  "specificity": 0,
  "communication": 0,
  "strengths": ["..."],
  "weaknesses": ["..."],
  "follow_up_question": "...",
  "next_focus": "..."
}}
Scores are 0-100. The follow-up must react specifically to the candidate's answer."""
    if _provider() == "openrouter":
        return _openrouter(prompt)
    return None
