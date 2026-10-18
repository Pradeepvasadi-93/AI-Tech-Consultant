from app.schemas import (
    EmailRequest,
    EmailCategory,
    RiskLevel,
    UrgencyLevel,
    ClassificationResponse,
)


def _contains_any(text: str, phrases: tuple[str, ...] | list[str]) -> bool:
    """Return True when any configured phrase appears in normalized text."""
    return any(phrase in text for phrase in phrases)


def classify_email(email: EmailRequest) -> ClassificationResponse:
    """
    Classify an incoming email using ordered, explainable keyword rules.

    This is a rule-based baseline, not an ML model. More specific intents
    are checked before general how-to and troubleshooting language.
    """
    subject = email.subject or ""
    body = email.body or ""
    context = email.conversation_context or ""
    text = f"{subject}\n{body}".lower()
    full_text = f"{subject}\n{body}\n{context}".lower()

    reasons: list[str] = []

    # Category rules: specific and sensitive intents take precedence.
    refund_phrases = (
        "refund", "chargeback", "money back", "give my money back",
        "cancel my subscription", "cancel my plan", "cancel the subscription",
        "cancel my account", "cancel this subscription", "cancellation",
        "reverse the charge", "reimburse", "return my payment",
    )
    complaint_phrases = (
        "complaint", "unacceptable", "very disappointed",
        "terrible service", "poor service", "bad service",
        "unhappy with", "not happy with", "dissatisfied",
        "frustrated with your support", "disappointed with support",
        "support has been poor", "support team has not",
        "this is unacceptable", "formal complaint",
        "broke our website", "website was broken after",
        "website is still broken after",
    )
    quote_phrases = (
        "quote", "quotation", "pricing", "how much",
        "cost estimate", "price for", "estimate the cost",
        "estimated cost", "provide an estimate", "get an estimate",
        "what would it cost", "how much would it cost",
        "budget for", "price estimate", "cost of redesign",
        "cost to redesign", "quote for", "share an estimate"
    )
    project_phrases = (
        "add a feature", "new feature", "custom development",
        "build a feature", "customization", "customisation",
        "build a customer dashboard", "customer dashboard",
        "dashboard for us", "develop a dashboard",
        "create a dashboard", "build a dashboard",
        "online booking", "booking system", "booking functionality",
        "calendar integration", "integrate with", "integration with",
        "connect to our", "connect our", "external integration",
        "new functionality", "develop a feature", "implement a feature",
        "build us a", "develop a new", "create a new",
        "can you build", "could you build", "can you develop",
        "could you develop", "would like to build",
        "would like to add", "we need a new",
    )
    troubleshooting_phrases = (
        "not working", "doesn't work", "does not work", "isn't working",
        "is not working", "error", "failed", "failure", "broken",
        "unable to", "can't access", "cannot access", "keeps failing",
        "keeps crashing", "crashes when", "stopped working",
        "not loading", "won't load", "will not load",
        "payment integration", "payment gateway", "checkout is failing",
        "checkout fails", "payments are failing", "payment failed",
        "integration is giving", "integration gives", "integration fails",
        "server error", "internal server error", "500 error",
        "technical issue", "technical problem", "bug", "issue with",
        "problem with", "something went wrong", "timed out",
        "timeout", "unable to complete",
    )
    how_to_phrases = (
        "how do i", "how can i", "steps to", "where can i",
        "how to", "please show me how", "instructions for",
        "guide me through", "walk me through", "where do i",
        "how do we", "how can we", "need instructions",
        "update the contact information", "change the contact information",
        "update contact details", "change contact details",
        "edit contact information", "update my website settings",
        "configure the settings", "configure general settings",
        "change the website settings", "change my website settings",
        "update the site name", "change the site name",
    )
    follow_up_phrases = (
        "following up", "follow up", "any update", "just checking",
        "previous email", "did you receive", "status of my",
        "status of the", "current status", "check the status",
        "checking on the status", "update on my request",
        "update on this request", "update on my ticket",
        "support ticket", "ticket status", "have you had a chance",
        "wanted to follow up", "following up on",
        "regarding my previous", "regarding our previous",
        "still waiting for a response", "any progress on",
    )

    if _contains_any(text, refund_phrases):
        category = EmailCategory.REFUND_CANCELLATION
        reasons.append("Financial or cancellation request detected.")

    elif _contains_any(text, complaint_phrases):
        category = EmailCategory.COMPLAINT
        reasons.append("Customer dissatisfaction or complaint detected.")

    # A request for a price/estimate should take precedence over a general
    # project phrase such as "website redesign".
    elif _contains_any(text, quote_phrases):
        category = EmailCategory.QUOTE_REQUEST
        reasons.append("Pricing or quotation request detected.")

    elif _contains_any(text, project_phrases):
        category = EmailCategory.PROJECT_REQUEST
        reasons.append("Potential project, integration, or scope change detected.")

    # Technical failure is more specific than general help wording.
    elif _contains_any(text, troubleshooting_phrases):
        category = EmailCategory.TROUBLESHOOTING
        reasons.append("Technical problem or failure detected.")

    elif _contains_any(text, follow_up_phrases):
        category = EmailCategory.FOLLOW_UP
        reasons.append("Follow-up or request-status message detected.")

    elif _contains_any(text, how_to_phrases):
        category = EmailCategory.HOW_TO
        reasons.append("How-to or configuration question detected.")

    else:
        category = EmailCategory.OTHER
        reasons.append("No configured category pattern matched.")

    # Urgency is assessed independently of the category.
    critical_words = (
        "security breach", "data breach", "site is down",
        "production is down", "entire site is down",
        "all users are locked out", "account takeover",
    )
    high_words = (
        "urgent", "asap", "immediately", "today",
        "deadline", "cannot access", "can't access",
        "business is blocked", "production issue",
    )

    if _contains_any(full_text, critical_words):
        urgency = UrgencyLevel.CRITICAL
        reasons.append("Potential critical outage or security incident.")
    elif _contains_any(full_text, high_words):
        urgency = UrgencyLevel.HIGH
        reasons.append("Urgency indicators detected.")
    else:
        urgency = UrgencyLevel.NORMAL

    # Risk assessment remains separate from category detection.
    critical_risk_words = (
        "security breach", "data breach", "account takeover",
        "stolen credentials", "exposed customer data",
        "unauthorized access", "unauthorised access",
    )
    high_risk_words = (
        "refund", "chargeback", "legal action", "lawyer",
        "lawsuit", "contract", "guarantee",
        "promise a delivery date", "regulatory complaint",
    )

    if _contains_any(full_text, critical_risk_words):
        risk_level = RiskLevel.CRITICAL
        reasons.append("Sensitive security or data risk detected.")
    elif (
        category in {
            EmailCategory.REFUND_CANCELLATION,
            EmailCategory.COMPLAINT,
            EmailCategory.QUOTE_REQUEST,
            EmailCategory.PROJECT_REQUEST,
        }
        or _contains_any(full_text, high_risk_words)
    ):
        risk_level = RiskLevel.HIGH
        reasons.append("Financial, commercial, or reputational risk detected.")
    elif category == EmailCategory.TROUBLESHOOTING:
        risk_level = RiskLevel.MEDIUM
        reasons.append("Technical response should be checked against evidence.")
    else:
        risk_level = RiskLevel.LOW

    # Always require review for high/critical risk and critical urgency.
    requires_human_review = risk_level in {
        RiskLevel.HIGH,
        RiskLevel.CRITICAL,
    } or urgency == UrgencyLevel.CRITICAL

    summary = (
        f"Email classified as {category.value}; "
        f"risk={risk_level.value}; urgency={urgency.value}."
    )

    return ClassificationResponse(
        category=category,
        risk_level=risk_level,
        urgency=urgency,
        requires_human_review=requires_human_review,
        reasons=reasons,
        summary=summary,
    )
