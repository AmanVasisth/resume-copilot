from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .models import InterviewRequest, InterviewPlan, EvaluateAnswerRequest, AnswerEvaluation, NextQuestionRequest, NextQuestionResponse, Question
from .engine import build_profile, make_questions, evaluate_answer
from .llm import evaluate_with_llm
from .adaptive import InterviewState, select_next_question, readiness_report

app = FastAPI(title="CareerCoach AI Interview Engine", version="0.4.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status":"ok","service":"careercoach-interview-engine","version":"0.4.2"}

@app.post("/v1/interview/plan", response_model=InterviewPlan)
def create_plan(req: InterviewRequest):
    profile=build_profile(req)
    return InterviewPlan(profile=profile, questions=make_questions(profile, req.question_count, req.mode))

@app.post("/v1/interview/evaluate", response_model=AnswerEvaluation)
def evaluate(req: EvaluateAnswerRequest):
    llm_result=evaluate_with_llm(req.question, req.answer, req.candidate)
    result = (
        AnswerEvaluation.model_validate(llm_result)
        if llm_result
        else evaluate_answer(req.question, req.answer, req.candidate)
    )
    # An adaptive probe is intentionally one level deep. Do not generate
    # another copy of the same generic follow-up after the probe is answered.
    if req.question.id.startswith("followup-"):
        result.follow_up_question = None
    return result

@app.post("/v1/interview/next", response_model=NextQuestionResponse)
def next_question(req: NextQuestionRequest):
    state=InterviewState(asked=req.asked_questions, evaluations=req.evaluations)
    if req.last_question.id not in {q.id for q in state.asked}:
        state.record(req.last_question, req.last_evaluation)
    if (
        req.last_evaluation.score < 65
        and req.last_evaluation.follow_up_question
        and not req.last_question.id.startswith("followup-")
    ):
        follow_up = Question(
            id=f"followup-{len(req.asked_questions) + 1}",
            category=req.last_question.category,
            skill=req.last_question.skill,
            difficulty=req.last_question.difficulty,
            question=req.last_evaluation.follow_up_question,
            rationale="Adaptive probe generated from the candidate's previous answer.",
            source="adaptive",
        )
        return NextQuestionResponse(
            question=follow_up,
            interview_complete=False,
            readiness=readiness_report(req.candidate, state),
        )

    q=select_next_question(req.candidate, req.available_questions, state, req.last_question, req.last_evaluation)
    return NextQuestionResponse(question=q, interview_complete=q is None, readiness=readiness_report(req.candidate, state))
