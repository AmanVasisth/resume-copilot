import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(__file__).resolve().parent / "careercoach.db"

def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with _connect() as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_key TEXT NOT NULL,
            target_role TEXT NOT NULL,
            years_experience REAL NOT NULL DEFAULT 0,
            mode TEXT NOT NULL,
            overall_score INTEGER,
            status TEXT NOT NULL DEFAULT 'in_progress',
            created_at TEXT NOT NULL,
            completed_at TEXT,
            plan_json TEXT
        )""")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            question_id TEXT NOT NULL,
            question TEXT NOT NULL,
            skill TEXT NOT NULL,
            category TEXT NOT NULL,
            answer TEXT NOT NULL,
            score INTEGER NOT NULL,
            evaluation_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
        cols = {row["name"] for row in conn.execute("PRAGMA table_info(sessions)").fetchall()}
        if "plan_json" not in cols:
            conn.execute("ALTER TABLE sessions ADD COLUMN plan_json TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_candidate_date ON sessions(candidate_key, created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_answers_session ON answers(session_id, id)")
        conn.execute("""CREATE UNIQUE INDEX IF NOT EXISTS idx_answers_session_question ON answers(session_id, question_id)""")
        conn.commit()

def create_session(candidate_key: str, target_role: str, years_experience: float, mode: str, plan: dict | None = None) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "INSERT INTO sessions(candidate_key,target_role,years_experience,mode,created_at,plan_json) VALUES(?,?,?,?,?,?)",
            (candidate_key, target_role, years_experience, mode, now, json.dumps(plan) if plan else None),
        )
        conn.commit()
        return get_session(int(cur.lastrowid), candidate_key)


def save_answer(
    session_id: int,
    candidate_key: str,
    question: dict,
    answer: str,
    evaluation: dict,
) -> dict:
    now = datetime.now(timezone.utc).isoformat()

    with _connect() as conn:
        owner = conn.execute(
            "SELECT id FROM sessions WHERE id=? AND candidate_key=?",
            (session_id, candidate_key),
        ).fetchone()

        if not owner:
            raise ValueError(
                "Interview session not found for this candidate."
            )

        existing = conn.execute(
            """
            SELECT id FROM answers
            WHERE session_id=? AND question_id=?
            ORDER BY id DESC LIMIT 1
            """,
            (session_id, question["id"]),
        ).fetchone()

        values = (
            question["question"],
            question["skill"],
            question["category"],
            answer,
            int(evaluation["score"]),
            json.dumps(evaluation),
        )

        if existing:
            conn.execute(
                """
                UPDATE answers
                SET question=?, skill=?, category=?, answer=?,
                    score=?, evaluation_json=?, created_at=?
                WHERE id=?
                """,
                (*values, now, existing["id"]),
            )
        else:
            conn.execute(
                """
                INSERT INTO answers(
                    session_id, question_id, question, skill,
                    category, answer, score, evaluation_json, created_at
                ) VALUES(?,?,?,?,?,?,?,?,?)
                """,
                (session_id, question["id"], *values, now),
            )

        conn.commit()

        return {
            "saved": True,
            "session_id": session_id,
            "question_id": question["id"],
        }

def complete_session(session_id: int, candidate_key: str, overall_score: int) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        cur = conn.execute(
            "UPDATE sessions SET status='completed', overall_score=?, completed_at=? WHERE id=? AND candidate_key=?",
            (overall_score, now, session_id, candidate_key),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise ValueError("Interview session not found for this candidate.")
        return get_session(session_id, candidate_key)

def get_session(session_id: int, candidate_key: str) -> dict:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id=? AND candidate_key=?", (session_id, candidate_key)).fetchone()
        if not row:
            raise ValueError("Interview session not found for this candidate.")
        session = dict(row)
        session["plan"] = json.loads(session.pop("plan_json")) if session.get("plan_json") else None
        rows = conn.execute("SELECT * FROM answers WHERE session_id=? ORDER BY id", (session_id,)).fetchall()
        session["answers"] = []
        for item in rows:
            a = dict(item)
            a["evaluation"] = json.loads(a.pop("evaluation_json"))
            session["answers"].append(a)
        return session

def list_sessions(candidate_key: str, limit: int = 25) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT s.*, COUNT(a.id) AS answers_count FROM sessions s LEFT JOIN answers a ON a.session_id=s.id WHERE s.candidate_key=? GROUP BY s.id ORDER BY s.created_at DESC LIMIT ?",
            (candidate_key, min(max(limit, 1), 100)),
        ).fetchall()
        return [dict(row) for row in rows]

def progress_summary(candidate_key: str) -> dict:
    with _connect() as conn:
        sessions = conn.execute(
            "SELECT id,target_role,overall_score,status,created_at,completed_at FROM sessions WHERE candidate_key=? ORDER BY created_at",
            (candidate_key,),
        ).fetchall()
        answers = conn.execute(
            """SELECT a.skill,a.score,a.evaluation_json,a.created_at,s.id AS session_id,s.target_role
            FROM answers a JOIN sessions s ON s.id=a.session_id
            WHERE s.candidate_key=? ORDER BY a.created_at""",
            (candidate_key,),
        ).fetchall()
    skill_data = {}
    for row in answers:
        skill = (row["skill"] or "General").strip()
        bucket = skill_data.setdefault(skill, {"scores": [], "sessions": set()})
        bucket["scores"].append(int(row["score"]))
        bucket["sessions"].add(int(row["session_id"]))
    skills = []
    for skill, bucket in skill_data.items():
        scores = bucket["scores"]
        skills.append({
            "skill": skill,
            "average_score": round(sum(scores) / len(scores)),
            "answers_count": len(scores),
            "sessions_count": len(bucket["sessions"]),
            "latest_score": scores[-1],
            "trend": "improving" if len(scores) >= 2 and scores[-1] > scores[0] else ("declining" if len(scores) >= 2 and scores[-1] < scores[0] else "steady"),
        })
    skills.sort(key=lambda x: (x["average_score"], x["skill"]))
    completed = [dict(s) for s in sessions if s["status"] == "completed" and s["overall_score"] is not None]
    weak = [x["skill"] for x in skills if x["average_score"] < 65][:5]
    return {
        "total_sessions": len(sessions),
        "completed_sessions": len(completed),
        "answers_count": len(answers),
        "average_completed_score": round(sum(s["overall_score"] for s in completed) / len(completed)) if completed else None,
        "sessions": [dict(s) for s in sessions],
        "skills": skills,
        "priority_gaps": weak,
    }


def detailed_recommendations(candidate_key: str) -> dict:
    summary = progress_summary(candidate_key)
    with _connect() as conn:
        rows = conn.execute(
            """SELECT a.skill,a.score,a.question,a.answer,a.evaluation_json,a.created_at
            FROM answers a JOIN sessions s ON s.id=a.session_id
            WHERE s.candidate_key=? ORDER BY a.created_at DESC LIMIT 200""",
            (candidate_key,),
        ).fetchall()
    by_skill = {}
    for row in rows:
        skill = (row["skill"] or "General").strip()
        item = by_skill.setdefault(skill, {"scores": [], "weaknesses": [], "examples": []})
        item["scores"].append(int(row["score"]))
        evaluation = json.loads(row["evaluation_json"])
        for weakness in (evaluation.get("weaknesses") or []):
            if weakness not in item["weaknesses"]:
                item["weaknesses"].append(weakness)
        if len(item["examples"]) < 2:
            item["examples"].append({"question": row["question"], "answer_excerpt": (row["answer"] or "")[:260], "score": int(row["score"])})
    topics = []
    for skill in summary.get("skills", []):
        skill_name = skill["skill"]
        detail = by_skill.get(skill_name, {})
        weaknesses = detail.get("weaknesses", [])[:4]
        topics.append({
            "skill": skill_name,
            "score": skill["average_score"],
            "latest_score": skill["latest_score"],
            "trend": skill["trend"],
            "weaknesses": weaknesses or (["Score below target"] if skill["average_score"] < 70 else ["Add more real-world detail and validation evidence"]),
            "examples": detail.get("examples", []),
            "practice": _practice_for_skill(skill_name, weaknesses, skill["average_score"]),
        })
    topics.sort(key=lambda t: (t["score"], t["skill"]))
    return {"topics": topics[:8], "message": "Built from saved answers and feedback. Use this as practice guidance, not a formal assessment."}


def _practice_for_skill(skill: str, weaknesses: list[str], score: int) -> str:
    text = " ".join(weaknesses).lower()
    if any(word in text for word in ["short", "context", "specific example", "measurable", "outcome", "trade-off", "tradeoff"]):
        return f"Describe one {skill} project using the problem, your personal contribution, a design decision, a trade-off, validation, and a measurable result."
    if any(word in text for word in ["depth", "technical", "correct", "reasoning", "explain"]):
        return f"Explain how you used {skill} in production, why you chose the approach, alternatives you considered, failure handling, and how you tested it."
    if score < 65:
        return f"Review core {skill} concepts, then solve one scenario end-to-end and explain assumptions, implementation steps, edge cases, and validation."
    return f"Give a specific {skill} example, justify your decisions, discuss one trade-off, and quantify the result where possible."
