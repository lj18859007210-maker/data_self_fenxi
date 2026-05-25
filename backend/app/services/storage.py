"""SQLite-based persistent storage for sessions and analysis results."""

import sqlite3
import json
from datetime import datetime
from typing import Any
from app.config import DB_PATH
from app.models.session import Session, SessionState, FieldInfo


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER DEFAULT 0,
            row_count INTEGER DEFAULT 0,
            column_count INTEGER DEFAULT 0,
            fields TEXT DEFAULT '[]',
            state TEXT DEFAULT 'uploaded',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS analysis_results (
            session_id TEXT PRIMARY KEY,
            results TEXT DEFAULT '{}',
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
        CREATE TABLE IF NOT EXISTS analysis_progress (
            session_id TEXT PRIMARY KEY,
            progress REAL DEFAULT 0.0,
            error TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        );
    """)
    conn.commit()
    conn.close()


def save_session(session: Session):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            session.id, session.filename, session.file_path,
            session.file_size, session.row_count, session.column_count,
            json.dumps([f.model_dump() for f in session.fields], default=str),
            session.state.value,
            session.created_at.isoformat(),
        )
    )
    conn.commit()
    conn.close()


def get_session(session_id: str):
    conn = get_conn()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    if not row:
        return None
    fields_data = json.loads(row["fields"])
    fields = [FieldInfo(**f) for f in fields_data] if fields_data else []
    return Session(
        id=row["id"], filename=row["filename"], file_path=row["file_path"],
        file_size=row["file_size"], row_count=row["row_count"],
        column_count=row["column_count"], fields=fields,
        state=SessionState(row["state"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def list_sessions(limit: int = 50):
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, filename, file_size, row_count, column_count, state, created_at "
        "FROM sessions ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_session(session_id: str):
    conn = get_conn()
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.execute("DELETE FROM analysis_results WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM analysis_progress WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()


def save_results(session_id: str, results: dict):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO analysis_results VALUES (?, ?, datetime('now'))",
        (session_id, json.dumps(results, default=str)),
    )
    conn.commit()
    conn.close()


def get_results(session_id: str) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT results FROM analysis_results WHERE session_id = ?", (session_id,)).fetchone()
    conn.close()
    return json.loads(row["results"]) if row else {}


def save_progress(session_id: str, progress: float, error: str | None = None):
    conn = get_conn()
    conn.execute(
        "INSERT OR REPLACE INTO analysis_progress VALUES (?, ?, ?)",
        (session_id, progress, error),
    )
    conn.commit()
    conn.close()


def get_progress_data(session_id: str) -> dict:
    conn = get_conn()
    row = conn.execute("SELECT progress, error FROM analysis_progress WHERE session_id = ?", (session_id,)).fetchone()
    conn.close()
    return {"progress": row["progress"] if row else 0.0, "error": row["error"] if row else None}
