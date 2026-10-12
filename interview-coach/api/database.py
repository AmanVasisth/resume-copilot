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

def save_answer(session_id: int, candidate_key: str, question: dict, answer: str, evaluation: dict) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        owner = conn.execute("SELECT id FROM sessions WHERE id=? AND candidate_key=?", (session_id, candidate_key)).fetchone()
        if not owner:
            raise ValueError("Interview session not found for this candidate.")
        conn.execute(
            """INSERT INTO answers(session_id,question_id,question,skill,category,answer,score,evaluation_json,created_at)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (session_id, question["id"], question["question"], question["skill"], question["category"], answer, int(evaluation["score"]), json.dumps(evaluation), now),
        )
        conn.commit()
        return {"saved": True, "session_id": session_id}

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
