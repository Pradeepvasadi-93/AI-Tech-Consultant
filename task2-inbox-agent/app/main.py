import os
from fastapi import FastAPI, HTTPException
from app.schemas import (
    EmailRequest,
    ClassificationResponse,
    EmailDraftResponse,
    ReviewRequest,
    FeedbackRequest,
)
from app.email.classifier import classify_email
from app.knowledge_client.client import (
    Task1KnowledgeClient,
    KnowledgeBrainError,
)
from app.drafting.service import generate_draft
from app.db.database import (
    init_db,
    save_processed_email,
    list_emails,
    get_email,
    record_review,
    record_feedback,
    send_simulated_email,
)


app = FastAPI(
    title="Inbox Agent API",
    description="AI-assisted customer email classification and drafting",
    version="0.1.0",
)

init_db()

@app.get("/")
def root():
    return {
        "message": "Inbox Agent API is running",
        "status": "healthy",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post(
    "/emails/classify",
    response_model=ClassificationResponse,
)
def classify_incoming_email(email: EmailRequest):
    return classify_email(email)


@app.post("/emails/process", response_model=EmailDraftResponse)
def process_incoming_email(email: EmailRequest):
    # 1. Classify the email.
    classification = classify_email(email)

    category = getattr(
        classification.category, "value", classification.category
    )
    risk_level = getattr(
        classification.risk_level, "value", classification.risk_level
    )

    # 2. Retrieve product evidence from Task 1.
    question = (
        f"Email subject: {email.subject}\n\n"
        f"Customer message:\n{email.body}"
    )

    if email.conversation_context:
        question += (
            f"\n\nPrevious conversation:\n"
            f"{email.conversation_context}"
        )

    client = Task1KnowledgeClient()

    try:
        knowledge_result = client.query(question=question, top_k=5)
    except KnowledgeBrainError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "message": "Knowledge Brain retrieval failed. "
                "No draft was generated.",
                "reason": str(exc),
            },
        ) from exc

    # 3. Generate a draft using the retrieved response.
    try:
        draft = generate_draft(
            email=email,
            knowledge_result=knowledge_result,
            category=str(category),
            risk_level=str(risk_level),
        )
    except Exception as exc:
        # Don't return a fabricated fallback draft.
        raise HTTPException(
            status_code=502,
            detail=f"Draft generation failed: {str(exc)}",
        ) from exc

    # 4. Preserve sources returned by Task 1.
    sources = knowledge_result.get("sources", [])
    if not isinstance(sources, list):
        sources = []

    # 5. Apply review rules in the backend.
    status = str(knowledge_result.get("status", "")).lower()
    task1_needs_human = (
        bool(knowledge_result.get("needs_human", False))
        or status in {
            "needs_human",
            "insufficient_evidence",
            "escalated",
        }
    )

    approval_setting = os.getenv(
        "REQUIRE_HUMAN_APPROVAL", "true"
    ).lower() in {"true", "1", "yes"}

    requires_review = (
        approval_setting
        or classification.requires_human_review
        or task1_needs_human
    )

    response = EmailDraftResponse(
        email=email,
        classification=classification,
        draft=draft,
        knowledge_result=knowledge_result,
        sources=sources,
        requires_human_review=requires_review,
        review_status="pending" if requires_review else "ready",
    )
    save_processed_email(response)
    return response

@app.get("/emails")
def get_inbox(limit: int = 50):
    return {"emails": list_emails(limit=limit)}


@app.get("/emails/{email_id}")
def get_email_details(email_id: str):
    result = get_email(email_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Email not found",
        )

    return result


@app.post("/emails/{email_id}/review")
def review_email(email_id: str, request: ReviewRequest):
    # An edit must include the replacement reply.
    if request.decision == "edited" and not (
        request.edited_reply and request.edited_reply.strip()
    ):
        raise HTTPException(
            status_code=422,
            detail="edited_reply is required for an edited decision.",
        )

    try:
        review_id = record_review(
            email_id=email_id,
            decision=request.decision,
            edited_reply=request.edited_reply,
            reviewer=request.reviewer,
            notes=request.notes,
        )
    except ValueError as exc:
        if "Email not found" in str(exc):
            raise HTTPException(
                status_code=404,
                detail="Email not found.",
            ) from exc
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc

    return {
        "review_id": review_id,
        "email_id": email_id,
        "decision": request.decision,
        "message": "Review decision saved.",
    }


@app.post("/emails/{email_id}/feedback")
def submit_email_feedback(
    email_id: str,
    request: FeedbackRequest,
):
    try:
        feedback_id = record_feedback(
            email_id=email_id,
            category_correct=request.category_correct,
            draft_useful=request.draft_useful,
            comments=request.comments,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail="Email not found.",
        ) from exc

    return {
        "feedback_id": feedback_id,
        "email_id": email_id,
        "message": "Feedback saved.",
    }


@app.post("/emails/{email_id}/send")
def simulate_send(email_id: str):
    try:
        return send_simulated_email(email_id)
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "Email not found" in message else 422
        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from exc


@app.get("/sent-emails")
def get_sent_emails():
    from app.db.database import get_connection

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT send_id, email_id, final_reply,
                   unchanged_from_original, send_mode, sent_at
            FROM sent_emails
            ORDER BY sent_at DESC
            """
        ).fetchall()

    return {"sent_emails": [dict(row) for row in rows]}


@app.get("/autonomy/status")
def get_autonomy_status():
    from app.db.database import get_connection

    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT category, consecutive_unchanged,
                   eligible_for_trial, updated_at
            FROM category_autonomy
            ORDER BY category
            """
        ).fetchall()

    return {
        "autonomy_status": [
            {
                **dict(row),
                "eligible_for_trial": bool(row["eligible_for_trial"]),
            }
            for row in rows
        ],
        "automatic_sending_enabled": False,
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8001, reload=False)