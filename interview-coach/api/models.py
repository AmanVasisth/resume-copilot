from typing import Literal
from pydantic import BaseModel, Field

Category = Literal["technical","project","behavioral","communication"]
Difficulty = Literal["foundational","professional","senior"]

class CandidateProfile(BaseModel):
    target_role: str
    years_experience: float = Field(ge=0)
    skills: list[str] = []
    projects: list[str] = []
    claims: list[str] = []
    required_skills: list[str] = []

class InterviewRequest(BaseModel):
    resume_text: str = ""
    job_description: str = ""
    target_role: str
    years_experience: float = Field(default=0, ge=0)
    mode: Literal["mixed","technical","behavioral","pressure"] = "mixed"
    question_count: int = Field(default=10, ge=5, le=20)

class Question(BaseModel):
    id: str
    category: Category
    skill: str
    difficulty: Difficulty
    question: str
    rationale: str
    source: Literal["resume","job_description","role_map","memory"]

class InterviewPlan(BaseModel):
    profile: CandidateProfile
    questions: list[Question]

class EvaluateAnswerRequest(BaseModel):
    question: Question
    answer: str
    candidate: CandidateProfile

class AnswerEvaluation(BaseModel):
    score: int = Field(ge=0, le=100)
    technical_correctness: int = Field(ge=0, le=100)
    depth: int = Field(ge=0, le=100)
    reasoning: int = Field(ge=0, le=100)
    specificity: int = Field(ge=0, le=100)
    communication: int = Field(ge=0, le=100)
    strengths: list[str]
    weaknesses: list[str]
    follow_up_question: str | None = None
    next_focus: str

class NextQuestionRequest(BaseModel):
    candidate: CandidateProfile
    available_questions: list[Question]
    asked_questions: list[Question] = []
    evaluations: list[AnswerEvaluation] = []
    last_question: Question
    last_evaluation: AnswerEvaluation

class NextQuestionResponse(BaseModel):
    question: Question | None
    interview_complete: bool
    readiness: dict
