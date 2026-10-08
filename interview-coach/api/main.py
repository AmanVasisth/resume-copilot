from __future__ import annotations
import re
from typing import Literal
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="CareerCoach AI Interview Engine", version="0.1.0")

class InterviewRequest(BaseModel):
    resume_text: str = ""
    job_description: str = ""
    target_role: str
    years_experience: float = Field(default=0, ge=0)
    mode: Literal["mixed","technical","behavioral","pressure"] = "mixed"

class Question(BaseModel):
    category: Literal["technical","project","behavioral","communication"]
    skill: str
    difficulty: Literal["foundational","professional","senior"]
    question: str
    source: Literal["resume","job_description","role_map"]

class InterviewBlueprint(BaseModel):
    target_role: str
    seniority: str
    detected_skills: list[str]
    questions: list[Question]

SKILL_PATTERNS = {
    "SQL": r"\bsql\b|mysql|postgres|oracle|sql server",
    "Python": r"\bpython\b|pandas|numpy",
    "Power BI": r"power\s*bi|dax",
    "Qlik Sense": r"qlik\s*sense|qlikview",
    "Databricks": r"databricks|spark",
    "Snowflake": r"snowflake",
    "Azure": r"\bazure\b|data factory|fabric",
    "AWS": r"\baws\b|s3|redshift",
    "Tableau": r"tableau",
    "Machine Learning": r"machine learning|xgboost|scikit-learn|sklearn",
    "GenAI": r"generative ai|genai|llm|langchain|langgraph|rag",
}

def seniority_for(role: str, years: float) -> str:
    text = role.lower()
    if years >= 7 or any(x in text for x in ("lead","principal","architect")):
        return "senior"
    if years >= 3 or "senior" in text:
        return "professional"
    return "foundational"

def detect_skills(text: str) -> list[str]:
    lower = text.lower()
    return [skill for skill, pattern in SKILL_PATTERNS.items() if re.search(pattern, lower)]

def build_questions(skills: list[str], seniority: str, request: InterviewRequest) -> list[Question]:
    questions = []
    for skill in skills[:8]:
        source = "job_description" if re.search(SKILL_PATTERNS[skill], request.job_description.lower()) else "resume"
        questions.append(Question(
            category="technical", skill=skill, difficulty=seniority, source=source,
            question=f"Explain how you have used {skill} in a real project. What problem did it solve, what design did you choose, and what trade-offs did you make?"
        ))
    for achievement in re.findall(r"(?:improved|reduced|increased|saved|optimized|delivered)[^.]{10,120}", request.resume_text, re.I)[:2]:
        questions.append(Question(
            category="project", skill="Resume Proof", difficulty=seniority, source="resume",
            question=f'You claim: "{achievement.strip()}". Walk me through exactly how you measured that result, what your personal contribution was, and what evidence supports the claim.'
        ))
    questions.extend([
        Question(category="behavioral", skill="Ownership", difficulty=seniority, source="role_map",
                  question="Tell me about a difficult stakeholder or project situation you personally owned. What did you do, and what was the measurable outcome?"),
        Question(category="communication", skill="Executive Communication", difficulty=seniority, source="role_map",
                  question="Explain one complex technical decision from your recent work as if you were speaking to a non-technical business leader.")
    ])
    return questions[:12]

@app.get("/health")
def health():
    return {"status":"ok","service":"careercoach-interview-engine"}

@app.post("/v1/interview/blueprint", response_model=InterviewBlueprint)
def create_blueprint(request: InterviewRequest):
    combined = f"{request.resume_text}\n{request.job_description}"
    skills = detect_skills(combined)
    seniority = seniority_for(request.target_role, request.years_experience)
    return InterviewBlueprint(target_role=request.target_role, seniority=seniority, detected_skills=skills,
                              questions=build_questions(skills, seniority, request))
