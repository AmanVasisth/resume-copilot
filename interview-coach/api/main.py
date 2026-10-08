from fastapi import FastAPI
from .models import InterviewRequest, InterviewPlan, EvaluateAnswerRequest, AnswerEvaluation
from .engine import build_profile, make_questions, evaluate_answer
from .llm import evaluate_with_llm

app = FastAPI(title="CareerCoach AI Interview Engine", version="0.3.0")

@app.get("/health")
def health():
    return {"status":"ok","service":"careercoach-interview-engine","version":"0.3.0"}

@app.post("/v1/interview/plan", response_model=InterviewPlan)
def create_plan(req: InterviewRequest):
    profile=build_profile(req)
    return InterviewPlan(profile=profile, questions=make_questions(profile, req.question_count, req.mode))

@app.post("/v1/interview/evaluate", response_model=AnswerEvaluation)
def evaluate(req: EvaluateAnswerRequest):
    llm_result=evaluate_with_llm(req.question, req.answer, req.candidate)
    if llm_result:
        return AnswerEvaluation.model_validate(llm_result)
    return evaluate_answer(req.question, req.answer, req.candidate)
