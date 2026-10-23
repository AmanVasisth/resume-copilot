import os, json, re
from io import BytesIO
from pathlib import Path
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from fastapi.middleware.cors import CORSMiddleware
from .models import InterviewRequest, InterviewPlan, EvaluateAnswerRequest, AnswerEvaluation, NextQuestionRequest, NextQuestionResponse, Question
from .engine import build_profile, make_questions, evaluate_answer
from .llm import evaluate_with_llm, rewrite_resume_bullet
from .scoring import apply_rubric_result
from .adaptive import InterviewState, select_next_question, readiness_report
from .resume_parser import extract_resume_text
from . import database

app = FastAPI(title="CareerCoach AI Interview Engine", version="0.4.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    database.init_db()

@app.get("/health")
def health():
    return {"status":"ok","service":"careercoach-interview-engine","version":"0.4.3"}

@app.post("/v1/resume/extract")
async def extract_resume(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text = extract_resume_text(file.filename or "", content)
        if not text:
            raise ValueError("No readable text found in the uploaded resume.")
        return {"filename": file.filename, "text": text}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

def _clean_extracted_resume_text(text: str) -> str:
    """Normalize common PDF text-extraction splits without changing resume claims."""
    text = text.replace("\\u00a0", " ").replace("\\r", "")
    fixes = {
        "g mail.com": "gmail.com", "G mail.com": "gmail.com",
        "Microsof t": "Microsoft", "Develop ed": "Developed", "develop ed": "developed",
        "cont rolled": "controlled", "app lication": "application", "reason ing": "reasoning",
        "docume nt": "document", "Document Inte lligence": "Document Intelligence",
        "groundn ess": "groundedness", "groundedn ess": "groundedness", "gro undedness": "groundedness",
        "deploy ment": "deployment", "integratio n": "integration", "sou rce": "source",
        "ve ctor": "vector", "DevO ps": "DevOps", "wit h": "with", "Po wer BI": "Power BI",
        "tool -enabled": "tool-enabled", "human -in-the- loop": "human-in-the-loop",
        "human -in-the-": "human-in-the-", "Hands -on": "Hands-on", "source -aware": "source-aware",
        "natural -language": "natural-language", "Azure -oriented": "Azure-oriented",
        "multi -agent": "multi-agent", "tool -calling": "tool-calling",
        "prompt -injection": "prompt-injection", "sensitive -information": "sensitive-information",
        "production -oriented": "production-oriented", "Gurgaon , India": "Gurgaon, India",
        "+91 -7015042204": "+91 7015042204",
        "linkedin.com/in/aman -sharma -0b113a136": "linkedin.com/in/aman-sharma-0b113a136",
    }
    for broken, fixed in fixes.items():
        text = text.replace(broken, fixed)
    text = re.sub(r"(?i)g\\s+mail\\.com", "gmail.com", text)
    text = re.sub(r"(?i)microsof\\s+t", "Microsoft", text)
    text = re.sub(r"(?i)vector/hybrid\\s+r\\s*etrieval", "vector/hybrid retrieval", text)
    text = re.sub(r"(?i)human\\s*-?in-the-\\s*loop", "human-in-the-loop", text)
    text = re.sub(r"\\[X\\]\\s*%\\s*improvement\\s+in\\s+\\[metric\\]", "", text, flags=re.I)
    text = re.sub(r"[ \\t]+([,.;:])", r"\\1", text)
    text = re.sub(r" {2,}", " ", text)
    # Preserve paragraph/section boundaries; only merge obvious word-wrap continuations.
    lines = [line.strip() for line in text.split("\\n")]
    out = []
    headings = re.compile(r"^(PROFESSIONAL SUMMARY|PROFILE SUMMARY|SUMMARY|AI & TECHNICAL SKILLS|TECHNICAL SKILLS|SKILLS|PROFESSIONAL EXPERIENCE|WORK EXPERIENCE|EXPERIENCE|KEY AI PROJECTS|PROJECTS|AI ENGINEERING FOCUS|EDUCATION|CERTIFICATIONS|AWARDS|ACHIEVEMENTS)$", re.I)
    starts_new = re.compile(r"^(?:[-•▪●]\\s+|\\d+[.)]\\s+|Qlik Sense Developer|Senior Consultant|Consultant|Power BI Developer|GenAI|AI Engineer|Data Analyst)\\b", re.I)
    for line in lines:
        if not line:
            continue
        if out and not headings.match(line) and not starts_new.match(line):
            prev = out[-1]
            if prev.endswith(("-", "/")):
                out[-1] = prev + line
                continue
            if len(prev) < 95 and not prev.endswith((",", "|", ".", "!", ":", ";")) and not headings.match(prev):
                out[-1] = prev + " " + line
                continue
        out.append(line)
    return "\\n".join(out).strip()


def _build_resume_docx(resume_text: str):
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Inches(0.35)
    section.bottom_margin = Inches(0.35)
    section.left_margin = Inches(0.48)
    section.right_margin = Inches(0.48)
    normal = doc.styles["Normal"]
    normal.font.name = "Arial"
    normal.font.size = Pt(8.25)
    normal.font.color.rgb = RGBColor(38, 48, 65)
    normal.paragraph_format.space_after = Pt(1)
    normal.paragraph_format.line_spacing = 1.0
    headings = {"professional summary", "profile summary", "summary", "experience", "professional experience", "work experience", "projects", "key projects", "key ai projects", "ai & technical skills", "technical skills", "skills", "core competencies", "education", "certifications", "awards", "achievements", "key result areas", "ai engineering focus"}
    skill_categories = ("Agentic AI", "LLMs", "RAG & Retrieval", "AI Evaluation & Guardrails", "Azure AI", "Python & Backend", "Cloud / DevOps", "Data & Analytics")
    raw_lines = [line.strip() for line in resume_text.splitlines() if line.strip()]
    if not raw_lines:
        raise ValueError("No readable resume text found.")
    title = doc.add_paragraph()
    title.alignment = 1
    title.paragraph_format.space_after = Pt(1)
    run = title.add_run(raw_lines[0])
    run.bold = True
    run.font.name = "Arial"
    run.font.size = Pt(17)
    run.font.color.rgb = RGBColor(37, 49, 78)
    idx = 1
    if idx < len(raw_lines) and ("@" in raw_lines[idx] or "linkedin.com" in raw_lines[idx].lower() or re.search(r"\\+?\\d[\\d ()-]{7,}", raw_lines[idx])):
        contact = doc.add_paragraph()
        contact.alignment = 1
        contact.paragraph_format.space_after = Pt(3)
        cr = contact.add_run(raw_lines[idx])
        cr.font.size = Pt(7.5)
        cr.font.color.rgb = RGBColor(90, 99, 115)
        idx += 1
    current_section = ""
    for line in raw_lines[idx:]:
        clean_line = re.sub(r"^[-•▪●]\s*", "", line).strip()
        if clean_line.lower() in headings:
            current_section = clean_line.lower()
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after = Pt(1)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(clean_line.upper())
            r.bold = True
            r.font.name = "Arial"
            r.font.size = Pt(9.25)
            r.font.color.rgb = RGBColor(79, 70, 229)
            continue
        matched_skill = next((label for label in skill_categories if clean_line.startswith(label + " ")), None)
        if matched_skill:
            value = clean_line[len(matched_skill):].strip(" :-|")
            table = doc.add_table(rows=1, cols=2)
            table.autofit = False
            table.columns[0].width = Inches(1.48)
            table.columns[1].width = Inches(5.65)
            left, right = table.rows[0].cells
            left.width, right.width = Inches(1.48), Inches(5.65)
            left.text, right.text = matched_skill, value
            for run in left.paragraphs[0].runs:
                run.bold = True
                run.font.size = Pt(7.75)
                run.font.color.rgb = RGBColor(37, 49, 78)
            for cell in (left, right):
                for p in cell.paragraphs:
                    p.paragraph_format.space_after = Pt(0)
                    for run in p.runs:
                        run.font.name = "Arial"
                        run.font.size = Pt(7.75)
            continue
        is_role = bool(re.match(r"^(Qlik Sense Developer|Senior Consultant|Consultant|Power BI Developer|GenAI|AI Engineer|Data Analyst).{0,180}\|", clean_line, re.I))
        is_project = bool(re.match(r"^(?:\d+[.)]\s+)?(?:ANZ|Control Tower|SOFAC|Shipping|Vessel|Conversational|RAG|Agentic|AI[- ]powered)", clean_line, re.I))
        is_bullet = bool(re.match(r"^[-•▪●]\s*", line))
        p = doc.add_paragraph()
        p.paragraph_format.keep_together = True
        p.paragraph_format.space_after = Pt(1)
        if is_role or is_project:
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.keep_with_next = True
            r = p.add_run(clean_line)
            r.bold = True
            r.font.color.rgb = RGBColor(37, 49, 78)
        elif is_bullet or current_section in {"experience", "professional experience", "work experience", "projects", "key projects", "key ai projects", "ai engineering focus"}:
            p.paragraph_format.left_indent = Inches(0.16)
            p.paragraph_format.first_line_indent = Inches(-0.12)
            p.add_run("• " + re.sub(r"^[-•▪●]\s*", "", clean_line))
        else:
            p.add_run(clean_line)
    return doc

@app.post("/v1/resume/export")
async def export_revised_resume(file: UploadFile = File(...), approved_bullets: str = ""):
    """Export approved resume edits as an editable, consistently styled DOCX."""
    try:
        content = await file.read()
        ext = Path(file.filename or "").suffix.lower()
        replacements = json.loads(approved_bullets or "[]")
        if not isinstance(replacements, list):
            raise ValueError("Approved bullet changes must be a list.")

        if ext == ".docx":
            doc = Document(BytesIO(content))
            for item in replacements:
                original = str(item.get("original", "")).strip()
                replacement = str(item.get("replacement", "")).strip()
                if not original or not replacement:
                    continue
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip() == original:
                        if paragraph.runs:
                            paragraph.runs[0].text = replacement
                            for run in paragraph.runs[1:]:
                                run.text = ""
                        else:
                            paragraph.add_run(replacement)
                        break
        else:
            resume_text = extract_resume_text(file.filename or "", content)
            if not resume_text.strip():
                raise ValueError("No readable text found in the uploaded resume.")
            for item in replacements:
                original = str(item.get("original", "")).strip()
                replacement = str(item.get("replacement", "")).strip()
                if original and replacement:
                    resume_text = resume_text.replace(original, replacement, 1)
            resume_text = _clean_extracted_resume_text(resume_text)
            doc = _build_resume_docx(resume_text)

        stream = BytesIO()
        doc.save(stream)
        stream.seek(0)
        return StreamingResponse(
            stream,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": 'attachment; filename="careercoach-revised-resume.docx"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not export revised resume: {exc}")

@app.post("/v1/resume/rewrite-bullet")
def rewrite_bullet(payload: dict):
    original = str(payload.get("original", "")).strip()
    draft = str(payload.get("draft", "")).strip()
    job_description = str(payload.get("job_description", "")).strip()
    if not original:
        raise HTTPException(status_code=400, detail="A resume bullet is required.")
    if len(original) > 3000 or len(draft) > 3000 or len(job_description) > 12000:
        raise HTTPException(status_code=413, detail="Please shorten the bullet or job description and try again.")
    result = rewrite_resume_bullet(original, draft, job_description)
    if not result:
        raise HTTPException(status_code=503, detail="AI rewriting is temporarily unavailable. Check the configured AI provider and retry.")
    return result

@app.post("/v1/interview/plan", response_model=InterviewPlan)
def create_plan(req: InterviewRequest):
    profile = build_profile(req)
    memory_topics = []
    if req.candidate_key:
        try:
            memory_topics = database.detailed_recommendations(req.candidate_key).get("topics", [])
        except Exception:
            memory_topics = []
    questions = make_questions(profile, req.question_count, req.mode, memory_topics=memory_topics)
    return InterviewPlan(profile=profile, questions=questions)

@app.post("/v1/sessions")
def start_session(payload: dict):
    key = str(payload.get("candidate_key", "")).strip()
    role = str(payload.get("target_role", "")).strip()
    if not key or not role:
        raise HTTPException(status_code=400, detail="candidate_key and target_role are required.")
    try:
        return database.create_session(key, role, float(payload.get("years_experience", 0)), str(payload.get("mode", "mixed")), payload.get("plan"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.get("/v1/sessions")
def sessions(candidate_key: str, limit: int = 25):
    return {"sessions": database.list_sessions(candidate_key, limit)}

@app.get("/v1/progress")
def progress(candidate_key: str):
    return database.progress_summary(candidate_key)

@app.get("/v1/recommendations")
def recommendations(candidate_key: str):
    return database.detailed_recommendations(candidate_key)

@app.get("/v1/sessions/{session_id}")
def session_detail(session_id: int, candidate_key: str):
    try:
        return database.get_session(session_id, candidate_key)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@app.post("/v1/sessions/{session_id}/answers")
def save_session_answer(session_id: int, payload: dict):
    try:
        return database.save_answer(
            session_id, str(payload.get("candidate_key", "")),
            payload["question"], str(payload.get("answer", "")), payload["evaluation"]
        )
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/v1/sessions/{session_id}/complete")
def complete_session(session_id: int, payload: dict):
    try:
        return database.complete_session(session_id, str(payload.get("candidate_key", "")), int(payload["overall_score"]))
    except (ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc))

@app.post("/v1/interview/evaluate", response_model=AnswerEvaluation)
def evaluate(req: EvaluateAnswerRequest):
    normalized = " ".join(req.answer.lower().split())
    short_or_nonanswer = len(req.answer.strip().split()) < 3 or normalized in {"no", "nope", "n/a", "na", "idk", "dont know", "not sure", "skip", "pass", "nothing"}
    if short_or_nonanswer:
        result = evaluate_answer(req.question, req.answer, req.candidate)
    else:
        llm_result = evaluate_with_llm(req.question, req.answer, req.candidate)
        if not llm_result:
            raise HTTPException(
                status_code=503,
                detail="AI evaluation is temporarily unavailable. Your answer has not been scored; please retry shortly.",
            )
        try:
            provider_used = llm_result.get(
                "_evaluation_provider",
                "openrouter" if os.getenv("LLM_PROVIDER") == "openrouter" else "gemini",
            )
            result = apply_rubric_result(llm_result, provider_used)
        except Exception:
            raise HTTPException(
                status_code=503,
                detail="AI evaluation returned an invalid response. Your answer has not been scored; please retry.",
            )
    # Adaptive probing is only needed for a weak answer, and only one level deep.
    if req.question.id.startswith("followup-") or result.score >= 65:
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
