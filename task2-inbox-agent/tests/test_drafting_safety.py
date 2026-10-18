import importlib.util
import sys
from types import ModuleType

# Safety helper tests do not invoke Groq. Permit importing service.py in a
# minimal test environment where the optional provider package is absent.
if importlib.util.find_spec("langchain_groq") is None:
    groq_stub = ModuleType("langchain_groq")
    groq_stub.ChatGroq = object
    sys.modules.setdefault("langchain_groq", groq_stub)

from app.schemas import EmailRequest
from app.drafting.service import (
    _knowledge_needs_review,
    _safe_fallback_draft,
)


def make_email(subject, body):
    return EmailRequest(
        sender="test@example.com",
        subject=subject,
        body=body,
        conversation_context="",
    )


def test_needs_human_status_forces_fallback():
    result = {
        "status": "needs_human",
        "needs_human": True,
        "answer": "The documentation does not contain the requested setup steps.",
    }
    assert _knowledge_needs_review(result) is True


def test_empty_or_missing_knowledge_forces_fallback():
    assert _knowledge_needs_review({}) is True
    assert _knowledge_needs_review({"status": "answered", "answer": ""}) is True


def test_supported_answer_can_use_normal_drafting_path():
    result = {
        "status": "answered",
        "needs_human": False,
        "answer": "Browse the support documentation at https://support.brilliantdirectories.com",
    }
    assert _knowledge_needs_review(result) is False


def test_security_fallback_does_not_invent_investigation():
    email = make_email(
        "Urgent: possible account takeover",
        "We suspect someone has taken over our account. Please investigate immediately.",
    )
    result = {
        "status": "answered",
        "needs_human": False,
        "answer": "Open a ticket and ask support to investigate.",
    }
    draft = _safe_fallback_draft(
        email=email,
        knowledge_result=result,
        category="other",
        risk_level="critical",
        knowledge_review=False,
    )
    reply = draft.suggested_reply.lower()
    assert "do not send passwords" in reply
    assert "investigation has started" not in reply
    assert "we have investigated" not in reply
    assert "verification codes" in reply


def test_missing_evidence_fallback_avoids_promises():
    email = make_email(
        "Quantum integration",
        "Please confirm whether quantum-computer integration is supported.",
    )
    draft = _safe_fallback_draft(
        email=email,
        knowledge_result={"status": "needs_human", "needs_human": True, "answer": ""},
        category="project_request",
        risk_level="high",
        knowledge_review=True,
    )
    reply = draft.suggested_reply.lower()
    assert "does not provide enough verified information" in reply
    assert "i've escalated" not in reply
    assert "i will get back to you" not in reply
    assert "authorized human must review" in draft.uncertainty_note.lower()
