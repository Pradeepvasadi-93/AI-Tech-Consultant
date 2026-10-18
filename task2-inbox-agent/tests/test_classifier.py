
from app.schemas import EmailRequest, EmailCategory, RiskLevel
from app.email.classifier import classify_email


def test_refund_requires_human_review():
    email = EmailRequest(
        sender="customer@example.com",
        subject="Refund request",
        body="Please refund my payment.",
    )

    result = classify_email(email)

    assert result.category == EmailCategory.REFUND_CANCELLATION
    assert result.risk_level == RiskLevel.HIGH
    assert result.requires_human_review is True


def test_security_incident_is_critical():
    email = EmailRequest(
        sender="customer@example.com",
        subject="Security breach",
        body="We suspect a data breach. Please investigate.",
    )

    result = classify_email(email)

    assert result.risk_level == RiskLevel.CRITICAL
    assert result.requires_human_review is True
