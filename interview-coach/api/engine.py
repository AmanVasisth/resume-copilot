import re
from .models import CandidateProfile, Question, AnswerEvaluation

SKILLS = {
    "SQL": r"\bsql\b|mysql|postgres|oracle|sql server|window function|cte|join",
    "Python": r"\bpython\b|pandas|numpy|scikit-learn",
    "Power BI": r"power\s*bi|dax|power query",
    "Qlik Sense": r"qlik\s*sense|qlikview|qvd|set analysis",
    "Databricks": r"databricks|spark|delta lake",
    "Snowflake": r"snowflake|warehouse|micro-partition",
    "Azure": r"\bazure\b|data factory|fabric|synapse",
    "Tableau": r"tableau",
    "Machine Learning": r"machine learning|xgboost|regression|classification",
    "GenAI": r"generative ai|genai|llm|langchain|langgraph|rag",
}

def seniority(role: str, years: float) -> str:
    role = role.lower()
    if years >= 7 or any(x in role for x in ("lead", "principal", "architect")):
        return "senior"
    if years >= 3 or "senior" in role:
        return "professional"
    return "foundational"

def extract_skills(text: str) -> list[str]:
    low = text.lower()
    return [skill for skill, pattern in SKILLS.items() if re.search(pattern, low)]

def extract_claims(resume: str) -> list[str]:
    pattern = r"(?:improved|reduced|increased|saved|optimized|delivered|automated|built|implemented|led)[^.]{10,180}"
    return [x.strip() for x in re.findall(pattern, resume, re.I)[:8]]

def build_profile(req) -> CandidateProfile:
    resume_skills = extract_skills(req.resume_text)
    jd_skills = extract_skills(req.job_description)
    skills = list(dict.fromkeys(resume_skills + jd_skills))
    claims = extract_claims(req.resume_text)
    projects = []
    for line in req.resume_text.splitlines():
        if any(k in line.lower() for k in ("project", "client", "dashboard", "platform", "migration")) and len(line.strip()) > 15:
            projects.append(line.strip()[:180])
    return CandidateProfile(
        target_role=req.target_role,
        years_experience=req.years_experience,
        skills=skills,
        projects=projects[:8],
        claims=claims,
        required_skills=jd_skills,
    )

def make_questions(profile: CandidateProfile, count: int, mode: str) -> list[Question]:
    questions = []
    diff = seniority(profile.target_role, profile.years_experience)

    for i, skill in enumerate(profile.skills):
        if len(questions) >= max(3, count - 3):
            break
        source = "job_description" if skill in profile.required_skills else "resume"
        questions.append(Question(
            id=f"tech-{i+1}",
            category="technical",
            skill=skill,
            difficulty=diff,
            source=source,
            question=f"Explain how you have used {skill} in a real project. What problem were you solving, what approach did you choose, and what trade-offs did you make?",
            rationale=f"Tests {skill} at {diff} depth instead of checking keyword familiarity.",
        ))

    for i, claim in enumerate(profile.claims[:2]):
        if len(questions) >= count - 2:
            break
        questions.append(Question(
            id=f"proof-{i+1}",
            category="project",
            skill="Resume Proof",
            difficulty=diff,
            source="resume",
            question=f'You claim: "{claim}". Prove it. What exactly did you personally do, how did you measure the result, and what would you do differently now?',
            rationale="Checks ownership, evidence and depth behind a resume claim.",
        ))

    if mode != "technical" and len(questions) < count:
        questions.append(Question(
            id="behavior-1",
            category="behavioral",
            skill="Ownership",
            difficulty=diff,
            source="role_map",
            question="Tell me about a difficult stakeholder or project situation you personally owned. What did you do and what measurable outcome followed?",
            rationale="Tests ownership and business impact.",
        ))

    if len(questions) < count:
        questions.append(Question(
            id="comm-1",
            category="communication",
            skill="Executive Communication",
            difficulty=diff,
            source="role_map",
            question="Explain one complex technical decision from your recent work to a non-technical business leader in under two minutes.",
            rationale="Tests clarity, structure and business translation.",
        ))

    return questions[:count]

def evaluate_answer(question: Question, answer: str, candidate: CandidateProfile) -> AnswerEvaluation:
    text = answer.strip()
    words = re.findall(r"\b\w+\b", text)
    lower = text.lower()

    specificity = min(100, 35 + min(40, len(words)//2) + (20 if any(x in lower for x in ("example", "metric", "result", "impact")) else 0))
    reasoning = min(100, 40 + (20 if any(x in lower for x in ("because", "therefore", "trade-off", "alternative")) else 0) + (20 if len(words) > 80 else 0))
    technical = min(100, 35 + (25 if any(k.lower() in lower for k in candidate.skills) else 0) + (20 if len(words) > 60 else 0))
    depth = min(100, 35 + (25 if any(x in lower for x in ("architecture", "performance", "scale", "failure", "monitor", "security")) else 0) + (20 if len(words) > 100 else 0))
    communication = max(35, min(100, 85 - (lower.count("basically") + lower.count("actually")) * 6 - (10 if len(words) > 220 else 0)))

    score = round((technical + depth + reasoning + specificity + communication) / 5)
    weaknesses = []

    if len(words) < 45:
        weaknesses.append("Answer is too short; add context, decisions and outcome.")
    if technical < 60 and question.category == "technical":
        weaknesses.append("Technical explanation needs more concrete implementation detail.")
    if specificity < 65:
        weaknesses.append("Use a specific example, metric or measurable result.")
    if reasoning < 65:
        weaknesses.append("Explain why you chose the approach and the trade-offs.")

    strengths = []
    if specificity >= 75:
        strengths.append("Good use of concrete evidence or examples.")
    if reasoning >= 75:
        strengths.append("Shows reasoning rather than only listing concepts.")
    if communication >= 75:
        strengths.append("Generally clear and concise.")

    follow = "Give me a concrete example and explain the decision, trade-off, and measurable outcome." if weaknesses else None

    return AnswerEvaluation(
        score=score,
        technical_correctness=technical,
        depth=depth,
        reasoning=reasoning,
        specificity=specificity,
        communication=communication,
        strengths=strengths or ["Answer addresses the question."],
        weaknesses=weaknesses or ["No major weakness detected in this first-pass evaluation."],
        follow_up_question=follow,
        next_focus=question.skill if weaknesses else "increase_depth",
    )
