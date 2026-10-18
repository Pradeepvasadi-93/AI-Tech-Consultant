from types import SimpleNamespace

import pytest

from app.db import database


def ns(**kwargs):
    return SimpleNamespace(**kwargs)


def fake_email_result(email_id="test-email-001"):
    email = ns(
        sender="customer@example.com",
        subject="Where can I find support documentation?",
        body="Please share the support documentation website.",
        conversation_context="",
    )
    category = ns(value="how_to")
    risk = ns(value="low")
    urgency = ns(value="normal")
    classification = ns(
        category=category,
        risk_level=risk,
        urgency=urgency,
        model_dump=lambda mode="json": {
            "category": "how_to",
            "risk_level": "low",
            "urgency": "normal",
            "requires_human_review": False,
            "reasons": [],
            "summary": "test",
        },
    )
    draft = ns(
        summary="Support docs request",
        suggested_reply="You can browse https://support.brilliantdirectories.com",
        next_action="Review the draft",
        uncertainty_note="",
        model_dump=lambda mode="json": {
            "summary": "Support docs request",
            "suggested_reply": "You can browse https://support.brilliantdirectories.com",
            "next_action": "Review the draft",
            "uncertainty_note": "",
        },
    )
    return ns(
        email_id=email_id,
        email=email,
        classification=classification,
        draft=draft,
        knowledge_result={
            "status": "answered",
            "needs_human": False,
            "answer": "The support documentation is available at https://support.brilliantdirectories.com",
        },
        sources=[],
        requires_human_review=True,
        review_status="pending",
    )


@pytest.fixture
def isolated_database(tmp_path, monkeypatch):
    db_path = tmp_path / "test_inbox.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    database.init_db()
    return db_path


def test_pending_email_cannot_be_sent(isolated_database):
    email_id = database.save_processed_email(fake_email_result())
    with pytest.raises(ValueError, match="approved or edited"):
        database.send_simulated_email(email_id)


def test_approved_email_can_be_simulated_and_duplicate_is_idempotent(isolated_database):
    email_id = database.save_processed_email(fake_email_result())
    database.record_review(email_id, "approved", reviewer="pytest")
    first = database.send_simulated_email(email_id)
    second = database.send_simulated_email(email_id)

    assert first["send_mode"] == "simulated"
    assert first["duplicate"] is False
    assert second["duplicate"] is True
    assert database.get_autonomy_status()["automatic_sending_enabled"] is False
    assert len(database.list_sent_emails()) == 1


def test_rejected_email_cannot_be_sent(isolated_database):
    email_id = database.save_processed_email(fake_email_result())
    database.record_review(email_id, "rejected", reviewer="pytest")
    with pytest.raises(ValueError, match="approved or edited"):
        database.send_simulated_email(email_id)


def test_edited_reply_is_not_counted_as_unchanged(isolated_database):
    email_id = database.save_processed_email(fake_email_result())
    database.record_review(
        email_id,
        "edited",
        edited_reply="This is the reviewed replacement reply.",
        reviewer="pytest",
    )
    result = database.send_simulated_email(email_id)
    assert result["unchanged_from_original"] is False
    assert result["consecutive_unchanged"] == 0
    assert database.get_autonomy_status()["automatic_sending_enabled"] is False
