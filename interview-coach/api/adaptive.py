from dataclasses import dataclass, field
from .models import Question, AnswerEvaluation, CandidateProfile

@dataclass
class InterviewState:
    asked: list[Question] = field(default_factory=list)
    evaluations: list[AnswerEvaluation] = field(default_factory=list)
    skill_scores: dict[str, list[int]] = field(default_factory=dict)

    def record(self, question: Question, evaluation: AnswerEvaluation):
        self.asked.append(question)
        self.evaluations.append(evaluation)
        self.skill_scores.setdefault(question.skill, []).append(evaluation.score)

    def average(self, skill: str) -> int:
        values = self.skill_scores.get(skill, [])
        return round(sum(values)/len(values)) if values else 0

    def overall(self) -> int:
        if not self.evaluations:
            return 0
        return round(sum(x.score for x in self.evaluations)/len(self.evaluations))

def select_next_question(
    candidate: CandidateProfile,
    available: list[Question],
    state: InterviewState,
    last: Question,
    last_eval: AnswerEvaluation,
) -> Question | None:
    unused=[q for q in available if q.id not in {x.id for x in state.asked}]
    if not unused:
        return None

    # Weak answer: probe the same skill before moving on.
    if last_eval.score < 65:
        same=[q for q in unused if q.skill == last.skill]
        if same:
            return same[0]

    # Strong answer: move toward another required skill.
    required=[q for q in unused if q.skill in candidate.required_skills]
    if required:
        return required[0]

    return unused[0]

def readiness_report(candidate: CandidateProfile, state: InterviewState) -> dict:
    skills={}
    for skill in state.skill_scores:
        skills[skill]=state.average(skill)

    overall=state.overall()
    weak=sorted(skills.items(), key=lambda x:x[1])[:3]
    strong=sorted(skills.items(), key=lambda x:x[1], reverse=True)[:3]

    return {
        "overall_readiness": overall,
        "skill_scores": skills,
        "top_strengths":[x[0] for x in strong if x[1] >= 70][:3],
        "priority_gaps":[x[0] for x in weak if x[1] < 70][:3],
        "recommendation": (
            "Ready for targeted interview practice." if overall >= 80 else
            "Practice priority gaps before interviewing." if overall >= 60 else
            "Build fundamentals and repeat the interview loop."
        ),
    }
