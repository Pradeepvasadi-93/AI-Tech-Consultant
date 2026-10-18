import uuid
from typing import Any, Literal
from enum import Enum
from pydantic import BaseModel, Field


class EmailCategory(str, Enum):
    HOW_TO = "how_to"
    TROUBLESHOOTING = "troubleshooting"
    PROJECT_REQUEST = "project_request"
    REFUND_CANCELLATION = "refund_cancellation"
    COMPLAINT = "complaint"
    QUOTE_REQUEST = "quote_request"
    FOLLOW_UP = "follow_up"
    OTHER = "other"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class UrgencyLevel(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class EmailRequest(BaseModel):
    sender: str = Field(min_length=3, max_length=254)
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=20000)
    conversation_context: str | None = Field(
        default=None,
        max_length=20000,
    )


class ClassificationResponse(BaseModel):
    category: EmailCategory
    risk_level: RiskLevel
    urgency: UrgencyLevel
    requires_human_review: bool
    reasons: list[str]
    summary: str

class DraftContent(BaseModel):
    """Fields Claude must generate for a draft."""

    summary: str = Field(
        description="A short summary of the customer's request."
    )
    suggested_reply: str = Field(
        description="The proposed email reply to the customer."
    )
    next_action: str = Field(
        description="The recommended internal next step."
    )
    uncertainty_note: str = Field(
        description=(
            "State missing information or uncertainty. "
            "Use an empty string when none needs mentioning."
        )
    )


class EmailDraftResponse(BaseModel):
    """Complete result returned by the Inbox Agent."""
    email_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailRequest
    classification: ClassificationResponse
    draft: DraftContent
    knowledge_result: dict[str, Any]
    sources: list[dict[str, Any]] = Field(default_factory=list)
    requires_human_review: bool = True
    review_status: str = "pending"

class ReviewRequest(BaseModel):
    decision: Literal["approved", "edited", "rejected", "escalated"]
    edited_reply: str | None = Field(default=None, max_length=20000)
    reviewer: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)

class FeedbackRequest(BaseModel):
    category_correct: bool | None = None
    draft_useful: bool | None = None
    comments: str | None = Field(default=None, max_length=2000)