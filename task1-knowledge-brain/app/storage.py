"""Small SQLite store for human escalations and ingestion job status."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone

from app.config import settings

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _db_path() -> Path:
    path = Path(settings.ESCALATION_DB_PATH)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _connect():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def _connection():
    conn = _connect()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def _now():
    return datetime.now(timezone.utc).isoformat()


def initialize_storage():
    with _connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS escalations (
                id TEXT PRIMARY KEY,
                question TEXT NOT NULL,
                reason TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open',
                expert_answer TEXT,
                answer_sources_json TEXT,
                created_at TEXT NOT NULL,
                resolved_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS approved_knowledge (
                id TEXT PRIMARY KEY,
                escalation_id TEXT NOT NULL,
                version INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                UNIQUE(escalation_id, version)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_jobs (
                id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                result_json TEXT,
                error TEXT
            )
        """)


def create_escalation(question: str, reason: str, evidence: list | None = None) -> dict:
    initialize_storage()
    item = {
        "id": str(uuid4()),
        "question": question,
        "reason": reason,
        "evidence": evidence or [],
        "status": "open",
        "created_at": _now(),
    }
    with _connection() as conn:
        conn.execute(
            """INSERT INTO escalations
            (id, question, reason, evidence_json, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (item["id"], item["question"], item["reason"],
             json.dumps(item["evidence"]), item["status"], item["created_at"]),
        )
    return item


def get_escalation(escalation_id: str) -> dict | None:
    initialize_storage()
    with _connection() as conn:
        row = conn.execute("SELECT * FROM escalations WHERE id=?", (escalation_id,)).fetchone()
    if not row:
        return None
    result = dict(row)
    result["evidence"] = json.loads(result.pop("evidence_json"))
    result["answer_sources"] = json.loads(result.pop("answer_sources_json") or "[]")
    return result


def list_escalations(status: str | None = None, limit: int = 100) -> list[dict]:
    initialize_storage()
    with _connection() as conn:
        if status:
            rows = conn.execute(
                "SELECT id FROM escalations WHERE status=? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id FROM escalations ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
    return [item for row in rows if (item := get_escalation(row["id"])) is not None]


def resolve_escalation(escalation_id: str, answer: str, sources: list[str]) -> dict | None:
    """Resolve an open escalation and create a separate versioned knowledge record."""
    initialize_storage()
    now = _now()
    with _connection() as conn:
        current = conn.execute(
            "SELECT * FROM escalations WHERE id=? AND status='open'", (escalation_id,)
        ).fetchone()
        if not current:
            return None
        row = conn.execute(
            "SELECT COALESCE(MAX(version), 0) AS latest FROM approved_knowledge WHERE escalation_id=?",
            (escalation_id,),
        ).fetchone()
        version = int(row["latest"]) + 1
        knowledge_id = str(uuid4())
        cursor = conn.execute(
            """UPDATE escalations SET status='resolved', expert_answer=?,
            answer_sources_json=?, resolved_at=? WHERE id=? AND status='open'""",
            (answer, json.dumps(sources), now, escalation_id),
        )
        if cursor.rowcount == 0:
            return None
        conn.execute(
            """INSERT INTO approved_knowledge
            (id, escalation_id, version, question, answer, sources_json, created_at, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)""",
            (knowledge_id, escalation_id, version, current["question"], answer,
             json.dumps(sources), now),
        )
    return get_escalation(escalation_id)




def next_knowledge_version(escalation_id: str) -> int:
    initialize_storage()
    with _connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(version), 0) AS latest FROM approved_knowledge WHERE escalation_id=?",
            (escalation_id,),
        ).fetchone()
    return int(row["latest"]) + 1

def list_approved_knowledge(limit: int = 100) -> list[dict]:
    initialize_storage()
    with _connection() as conn:
        rows = conn.execute(
            """SELECT id, escalation_id, version, question, answer, sources_json,
            created_at, active FROM approved_knowledge ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    results = []
    for row in rows:
        item = dict(row)
        item["sources"] = json.loads(item.pop("sources_json"))
        item["active"] = bool(item["active"])
        results.append(item)
    return results


def create_ingestion_job() -> str:
    initialize_storage()
    job_id = str(uuid4())
    with _connection() as conn:
        conn.execute(
            "INSERT INTO ingestion_jobs (id,status,started_at) VALUES (?,?,?)",
            (job_id, "running", _now()),
        )
    return job_id


def finish_ingestion_job(job_id: str, result: dict | None = None, error: str | None = None):
    initialize_storage()
    with _connection() as conn:
        conn.execute(
            """UPDATE ingestion_jobs SET status=?, finished_at=?, result_json=?, error=?
            WHERE id=?""",
            ("failed" if error else "completed", _now(),
             json.dumps(result) if result is not None else None, error, job_id),
        )


def get_ingestion_job(job_id: str | None = None) -> dict | None:
    initialize_storage()
    with _connection() as conn:
        if job_id:
            row = conn.execute("SELECT * FROM ingestion_jobs WHERE id=?", (job_id,)).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM ingestion_jobs ORDER BY started_at DESC LIMIT 1"
            ).fetchone()
    if not row:
        return None
    item = dict(row)
    item["result"] = json.loads(item.pop("result_json") or "null")
    return item
