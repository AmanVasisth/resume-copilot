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
    pattern = r"(?:improved|reduced|increased|saved|optimized|delivered|automated|built|implemented|led)[^.]{10,220}"
    return [x.strip(" -•") for x in re.findall(pattern, resume, re.I)[:10]]

def extract_projects(resume: str) -> list[str]:
    projects=[]
    for line in resume.splitlines():
        clean=line.strip(" -•\t")
        low=clean.lower()
        if len(clean) > 25 and any(k in low for k in ("project", "client", "dashboard", "platform", "migration", "solution", "application")):
            projects.append(clean[:220])
    return list(dict.fromkeys(projects))[:10]

def build_skill_evidence(text: str, skills: list[str]) -> dict[str, list[str]]:
    lines=[x.strip(" -•\t") for x in text.splitlines() if len(x.strip()) > 20]
    evidence={}
    for skill in skills:
        pattern=re.compile(SKILLS[skill], re.I)
        hits=[line[:220] for line in lines if pattern.search(line)]
        evidence[skill]=list(dict.fromkeys(hits))[:3]
    return evidence

def build_profile(req) -> CandidateProfile:
    resume_skills = extract_skills(req.resume_text)
    jd_skills = extract_skills(req.job_description)
    skills = list(dict.fromkeys(resume_skills + jd_skills))
    claims = extract_claims(req.resume_text)
    projects = extract_projects(req.resume_text)
    return CandidateProfile(
        target_role=req.target_role,
        years_experience=req.years_experience,
        skills=skills,
        projects=projects,
        claims=claims,
        required_skills=jd_skills,
        skill_evidence=build_skill_evidence(req.resume_text, resume_skills),
    )

def make_questions(profile: CandidateProfile, count: int, mode: str) -> list[Question]:
    questions=[]
    diff=seniority(profile.target_role, profile.years_experience)

    def add(q):
        if len(questions) < count and q.question not in {x.question for x in questions}:
            questions.append(q)

    # First cover JD priorities. If the resume contains evidence, challenge ownership;
    # if it doesn't, test whether the candidate can genuinely perform the requirement.
    for i, skill in enumerate(profile.required_skills):
        evidence=profile.skill_evidence.get(skill, [])
        if evidence:
            snippet=evidence[0]
            add(Question(
                id=f"jd-proof-{i+1}",
                category="technical",
                skill=skill,
                difficulty=diff,
                source="job_description",
                question=f"You list {skill} experience in your resume, including: "{snippet}". Walk me through what you personally built, the design decision you made, the hardest issue you faced, and how you validated the result.",
                rationale=f"JD requirement + resume evidence: tests real hands-on depth in {skill}.",
            ))
        else:
            add(Question(
                id=f"jd-gap-{i+1}",
                category="technical",
                skill=skill,
                difficulty=diff,
                source="job_description",
                question=f"This role requires {skill}, but your resume gives limited direct evidence. Describe the closest real problem you solved with {skill}, what you implemented yourself, and where your knowledge is still developing.",
                rationale=f"Tests credibility against a required JD skill without assuming unsupported experience.",
            ))

    # Then challenge measurable resume claims.
    for i, claim in enumerate(profile.claims[:3]):
        add(Question(
            id=f"proof-{i+1}",
            category="project",
            skill="Resume Proof",
            difficulty=diff,
            source="resume",
            question=f'Your resume says: "{claim}". What was the baseline, what did you personally change, how did you measure the result, and what trade-off did you accept?',
            rationale="Checks ownership, evidence, measurement and decision quality behind a resume claim.",
        ))

    # Project deep dive gives the interviewer a concrete story to follow.
    for i, project in enumerate(profile.projects[:2]):
        add(Question(
            id=f"project-{i+1}",
            category="project",
            skill="Project Deep Dive",
            difficulty=diff,
            source="resume",
            question=f'In this project context from your resume — "{project}" — what was the business problem, what architecture or workflow did you own, and what changed because of your work?',
            rationale="Tests project ownership and business impact using candidate-provided evidence.",
        ))

    if mode != "technical":
        add(Question(
            id="behavior-1",
            category="behavioral",
            skill="Ownership",
            difficulty=diff,
            source="role_map",
            question="Tell me about a difficult stakeholder or project situation you personally owned. What options did you consider, what did you decide, and what measurable outcome followed?",
            rationale="Tests ownership, stakeholder judgment and business impact.",
        ))

    add(Question(
        id="comm-1",
        category="communication",
        skill="Executive Communication",
        difficulty=diff,
        source="role_map",
        question="Explain one complex technical decision from your recent work to a non-technical business leader in under two minutes. Focus on the business problem, decision, risk and outcome.",
        rationale="Tests clarity, structure and business translation.",
    ))

    # Add uncovered resume skills only after JD coverage and proof questions.
    for i, skill in enumerate(profile.skills):
        if skill in profile.required_skills:
            continue
        evidence=profile.skill_evidence.get(skill, [])
        add(Question(
            id=f"resume-tech-{i+1}",
            category="technical",
            skill=skill,
            difficulty=diff,
            source="resume",
            question=f"Your resume shows {skill}. Pick one real implementation and explain the architecture, your personal contribution, the main failure or bottleneck, and how you improved it.",
            rationale=f"Tests hands-on resume evidence for {skill}.",
        ))

    return questions[:count]

def evaluate_answer(question: Question, answer: str, candidate: CandidateProfile) -> AnswerEvaluation:
    text=answer.strip()
    words=re.findall(r"\b\w+\b",text)
    lower=text.lower()

    specificity=min(100,30+min(45,len(words)//2)+(20 if any(x in lower for x in ("example","metric","result","impact","baseline","measured")) else 0))
    reasoning=min(100,35+(20 if any(x in lower for x in ("because","therefore","trade-off","alternative","chose","decision")) else 0)+(20 if len(words)>80 else 0))
    technical=min(100,35+(25 if any(k.lower() in lower for k in candidate.skills) else 0)+(20 if len(words)>60 else 0))
    depth=min(100,35+(25 if any(x in lower for x in ("architecture","performance","scale","failure","monitor","security","testing","validation")) else 0)+(20 if len(words)>100 else 0))
    communication=max(35,min(100,85-(lower.count("basically")+lower.count("actually"))*6-(10 if len(words)>220 else 0)))
    score=round((technical+depth+reasoning+specificity+communication)/5)

    weaknesses=[]
    if len(words)<45: weaknesses.append("Answer is too short; add context, decisions and outcome.")
    if question.category=="technical" and technical<60: weaknesses.append("Technical explanation needs more concrete implementation detail.")
    if specificity<65: weaknesses.append("Use a specific example, metric or measurable result.")
    if reasoning<65: weaknesses.append("Explain why you chose the approach and the trade-offs.")
    if question.category in ("project","technical") and depth<65: weaknesses.append("Go deeper into architecture, failure handling, validation or scale.")

    strengths=[]
    if specificity>=75: strengths.append("Good use of concrete evidence or examples.")
    if reasoning>=75: strengths.append("Shows reasoning rather than only listing concepts.")
    if depth>=75: strengths.append("Demonstrates meaningful technical depth.")
    if communication>=75: strengths.append("Generally clear and concise.")

    follow=None
    if weaknesses and not question.id.startswith("followup-"):
        if specificity<65:
            follow="Give me one concrete example and quantify the outcome. What was the baseline, what changed, and how did you measure the improvement?"
        elif reasoning<65:
            follow="Why did you choose that approach over the main alternative? Explain the trade-off and what would have changed your decision."
        elif depth<65:
            follow="Take that implementation one level deeper: what was the architecture, what failed or became a bottleneck, and how did you validate the fix?"
        else:
            follow="What did you personally own, and how can you prove the result was caused by your contribution?"
    return AnswerEvaluation(
        score=score,technical_correctness=technical,depth=depth,reasoning=reasoning,
        specificity=specificity,communication=communication,
        strengths=strengths or ["Answer addresses the question."],
        weaknesses=weaknesses or ["No major weakness detected in this first-pass evaluation."],
        follow_up_question=follow,
        next_focus=question.skill if weaknesses else "increase_depth",
    )
