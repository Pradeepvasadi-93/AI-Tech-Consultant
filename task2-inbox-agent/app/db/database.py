
import json
import os
import sqlite3
import uuid

from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def get_database_path() -> Path:
    configured_path = os.getenv(
        "DATABASE_PATH",
        "data/inbox_agent.db",
    )

    path = Path(configured_path)

    # Relative paths are resolved from the Task 2 working directory.
    if not path.is_absolute():
        path = Path.cwd() / path

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(get_database_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS emails (
                email_id TEXT PRIMARY KEY,
                sender TEXT NOT NULL,
                subject TEXT NOT NULL,
                body TEXT NOT NULL,
                conversation_context TEXT DEFAULT '',

                category TEXT,
                risk_level TEXT,
                urgency TEXT,
                classification_json TEXT,

                draft_json TEXT,
                original_draft_json TEXT,
                knowledge_json TEXT,
                sources_json TEXT,

                requires_human_review INTEGER NOT NULL DEFAULT 1,
                review_status TEXT NOT NULL DEFAULT 'pending',

                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reviews (
                review_id TEXT PRIMARY KEY,
                email_id TEXT NOT NULL,
                decision TEXT NOT NULL,
                edited_reply TEXT,
                reviewer TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,

                FOREIGN KEY (email_id)
                    REFERENCES emails(email_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS feedback (
                feedback_id TEXT PRIMARY KEY,
                email_id TEXT NOT NULL,
                category_correct INTEGER,
                draft_useful INTEGER,
                comments TEXT,
                created_at TEXT NOT NULL,

                FOREIGN KEY (email_id)
                    REFERENCES emails(email_id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS sent_emails (
                send_id TEXT PRIMARY KEY,
                email_id TEXT NOT NULL UNIQUE,
                idempotency_key TEXT NOT NULL UNIQUE,
                final_reply TEXT NOT NULL,
                unchanged_from_original INTEGER NOT NULL,
                send_mode TEXT NOT NULL DEFAULT 'simulated',
                sent_at TEXT NOT NULL,
                FOREIGN KEY (email_id) REFERENCES emails(email_id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS category_autonomy (
                category TEXT PRIMARY KEY,
                consecutive_unchanged INTEGER NOT NULL DEFAULT 0,
                eligible_for_trial INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_sent_emails_sent_at
                ON sent_emails(sent_at);

            CREATE INDEX IF NOT EXISTS idx_emails_review_status
                ON emails(review_status);

            CREATE INDEX IF NOT EXISTS idx_emails_category
                ON emails(category);

            CREATE INDEX IF NOT EXISTS idx_reviews_email_id
                ON reviews(email_id);

            CREATE INDEX IF NOT EXISTS idx_feedback_email_id
                ON feedback(email_id);
            """
        )

        columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(emails)").fetchall()
        }
        if "original_draft_json" not in columns:
            connection.execute(
                "ALTER TABLE emails ADD COLUMN original_draft_json TEXT"
            )
        connection.execute(
            """
            UPDATE emails
            SET original_draft_json = draft_json
            WHERE original_draft_json IS NULL
            """
        )


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def save_processed_email(result: Any) -> str:
    """
    Persist an EmailDraftResponse and return its email ID.

    The response is expected to expose email, classification, draft,
    knowledge_result, sources, and review fields.
    """
    email_id = getattr(result, "email_id", None) or str(uuid.uuid4())

    email = result.email
    classification = result.classification

    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO emails (
                email_id,
                sender,
                subject,
                body,
                conversation_context,
                category,
                risk_level,
                urgency,
                classification_json,
                draft_json,
                original_draft_json,
                knowledge_json,
                sources_json,
                requires_human_review,
                review_status,
                created_at,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email_id) DO UPDATE SET
                category = excluded.category,
                risk_level = excluded.risk_level,
                urgency = excluded.urgency,
                classification_json = excluded.classification_json,
                draft_json = excluded.draft_json,
                knowledge_json = excluded.knowledge_json,
                sources_json = excluded.sources_json,
                requires_human_review = excluded.requires_human_review,
                review_status = excluded.review_status,
                updated_at = excluded.updated_at
            """,
            (
                email_id,
                email.sender,
                email.subject,
                email.body,
                email.conversation_context or "",
                str(getattr(classification.category, "value", classification.category)),
                str(getattr(classification.risk_level, "value", classification.risk_level)),
                str(getattr(classification.urgency, "value", classification.urgency)),
                _json_text(classification.model_dump(mode="json")),
                _json_text(result.draft.model_dump(mode="json")),
                _json_text(result.draft.model_dump(mode="json")),
                _json_text(result.knowledge_result),
                _json_text(result.sources),
                int(result.requires_human_review),
                result.review_status,
                now,
                now,
            ),
        )

    return email_id


def list_emails(limit: int = 50) -> list[dict[str, Any]]:
    """Return the most recently updated email records."""
    limit = max(1, min(limit, 200))

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT
                email_id, sender, subject, category,
                risk_level, urgency, requires_human_review,
                review_status, created_at, updated_at
            FROM emails
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [dict(row) for row in rows]


def get_email(email_id: str) -> dict[str, Any] | None:
    """Return one complete stored email record."""
    with get_connection() as connection:
        row = connection.execute(
            "SELECT * FROM emails WHERE email_id = ?",
            (email_id,),
        ).fetchone()

    if row is None:
        return None

    record = dict(row)

    for field in (
        "classification_json",
        "draft_json",
        "original_draft_json",
        "knowledge_json",
        "sources_json",
    ):
        raw_value = record.pop(field)
        record[field.removesuffix("_json")] = (
            json.loads(raw_value) if raw_value else None
        )

    record["requires_human_review"] = bool(
        record["requires_human_review"]
    )

    return record



def record_review(
    email_id: str,
    decision: str,
    edited_reply: str | None = None,
    reviewer: str | None = None,
    notes: str | None = None,
) -> str:
    """Save a review decision and preserve edits to the draft."""

    allowed_decisions = {
        "approved", "edited", "rejected", "escalated"
    }

    if decision not in allowed_decisions:
        raise ValueError("Invalid review decision.")

    if decision == "edited" and not (
        edited_reply and edited_reply.strip()
    ):
        raise ValueError(
            "edited_reply is required when decision is 'edited'."
        )

    review_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        row = connection.execute(
            """
            SELECT category, draft_json
            FROM emails
            WHERE email_id = ?
            """,
            (email_id,),
        ).fetchone()

        if row is None:
            raise ValueError(f"Email not found: {email_id}")

        if decision == "edited":
            draft = json.loads(row["draft_json"] or "{}")
            draft["suggested_reply"] = edited_reply.strip()

            connection.execute(
                """
                UPDATE emails
                SET draft_json = ?,
                    review_status = ?,
                    updated_at = ?
                WHERE email_id = ?
                """,
                (
                    _json_text(draft),
                    decision,
                    now,
                    email_id,
                ),
            )
        else:
            connection.execute(
                """
                UPDATE emails
                SET review_status = ?, updated_at = ?
                WHERE email_id = ?
                """,
                (decision, now, email_id),
            )

        connection.execute(
            """
            INSERT INTO reviews (
                review_id, email_id, decision, edited_reply,
                reviewer, notes, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                review_id,
                email_id,
                decision,
                edited_reply.strip()
                if edited_reply and edited_reply.strip()
                else None,
                reviewer,
                notes,
                now,
            ),
        )

        if decision in {"edited", "rejected"} and row["category"]:
            connection.execute(
                """
                INSERT INTO category_autonomy (
                    category, consecutive_unchanged, eligible_for_trial, updated_at
                )
                VALUES (?, 0, 0, ?)
                ON CONFLICT(category) DO UPDATE SET
                    consecutive_unchanged = 0,
                    eligible_for_trial = 0,
                    updated_at = excluded.updated_at
                """,
                (row["category"], now),
            )

    return review_id


def record_feedback(
    email_id: str,
    category_correct: bool | None = None,
    draft_useful: bool | None = None,
    comments: str | None = None,
) -> str:
    """Store feedback for later evaluation and improvement."""
    feedback_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:
        exists = connection.execute(
            "SELECT 1 FROM emails WHERE email_id = ?",
            (email_id,),
        ).fetchone()

        if exists is None:
            raise ValueError(f"Email not found: {email_id}")

        connection.execute(
            """
            INSERT INTO feedback (
                feedback_id, email_id, category_correct,
                draft_useful, comments, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id,
                email_id,
                None if category_correct is None else int(category_correct),
                None if draft_useful is None else int(draft_useful),
                comments,
                now,
            ),
        )

    return feedback_id



def send_simulated_email(
    email_id: str,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Record a simulated send; no real email is sent."""
    now = datetime.now(timezone.utc).isoformat()
    key = idempotency_key or email_id

    with get_connection() as connection:
        email = connection.execute(
            "SELECT * FROM emails WHERE email_id = ?", (email_id,)
        ).fetchone()
        if email is None:
            raise ValueError(f"Email not found: {email_id}")

        existing = connection.execute(
            "SELECT * FROM sent_emails WHERE email_id = ?", (email_id,)
        ).fetchone()
        if existing is not None:
            return {
                "send_id": existing["send_id"],
                "email_id": email_id,
                "send_mode": existing["send_mode"],
                "sent_at": existing["sent_at"],
                "duplicate": True,
                "unchanged_from_original": bool(existing["unchanged_from_original"]),
                "message": "This email was already recorded as sent.",
            }

        if email["review_status"] not in {"approved", "edited"}:
            raise ValueError(
                "A draft must be approved or edited by a reviewer before it can be sent."
            )

        current = json.loads(email["draft_json"] or "{}")
        original = json.loads(
            email["original_draft_json"] or email["draft_json"] or "{}"
        )
        final_reply = str(current.get("suggested_reply", "")).strip()
        original_reply = str(original.get("suggested_reply", "")).strip()
        if not final_reply:
            raise ValueError("The final reply is empty.")

        normalize = lambda value: " ".join(value.split())
        unchanged = normalize(final_reply) == normalize(original_reply)
        category = email["category"] or "other"
        previous = connection.execute(
            "SELECT consecutive_unchanged FROM category_autonomy WHERE category = ?",
            (category,),
        ).fetchone()
        streak = (
            (previous["consecutive_unchanged"] + 1 if previous else 1)
            if unchanged else 0
        )
        eligible = streak >= 20
        send_id = str(uuid.uuid4())

        connection.execute(
            """
            INSERT INTO sent_emails (
                send_id, email_id, idempotency_key, final_reply,
                unchanged_from_original, send_mode, sent_at
            ) VALUES (?, ?, ?, ?, ?, 'simulated', ?)
            """,
            (send_id, email_id, key, final_reply, int(unchanged), now),
        )
        connection.execute(
            """
            INSERT INTO category_autonomy (
                category, consecutive_unchanged, eligible_for_trial, updated_at
            ) VALUES (?, ?, ?, ?)
            ON CONFLICT(category) DO UPDATE SET
                consecutive_unchanged = excluded.consecutive_unchanged,
                eligible_for_trial = excluded.eligible_for_trial,
                updated_at = excluded.updated_at
            """,
            (category, streak, int(eligible), now),
        )
        connection.execute(
            "UPDATE emails SET review_status = 'sent', updated_at = ? WHERE email_id = ?",
            (now, email_id),
        )

    return {
        "send_id": send_id,
        "email_id": email_id,
        "send_mode": "simulated",
        "sent_at": now,
        "duplicate": False,
        "unchanged_from_original": unchanged,
        "category": category,
        "consecutive_unchanged": streak,
        "eligible_for_trial": eligible,
        "message": "Simulated send recorded. No real email was sent.",
    }


def list_sent_emails(limit: int = 50) -> list[dict[str, Any]]:
    """List recent simulated-send audit records."""
    limit = max(1, min(limit, 200))
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT send_id, email_id, final_reply, unchanged_from_original,
                   send_mode, sent_at
            FROM sent_emails ORDER BY sent_at DESC LIMIT ?
            """,
            (limit,),
        ).fetchall()
    result = [dict(row) for row in rows]
    for row in result:
        row["unchanged_from_original"] = bool(row["unchanged_from_original"])
    return result


def get_autonomy_status() -> dict[str, Any]:
    """Return category streaks; automatic sending is never enabled here."""
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT category, consecutive_unchanged, eligible_for_trial, updated_at
            FROM category_autonomy ORDER BY category
            """
        ).fetchall()
    statuses = []
    for row in rows:
        item = dict(row)
        item["eligible_for_trial"] = bool(item["eligible_for_trial"])
        statuses.append(item)
    return {
        "autonomy_status": statuses,
        "automatic_sending_enabled": False,
    }
