"""Review queue and feedback models for v1 API."""

from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator

from app.schemas.common import ItemStatus
from app.schemas.search import Result


class ReviewItem(BaseModel):
    id: str
    query: str
    created_at: str
    status: ItemStatus
    priority: int
    candidates: list[Result] = Field(default_factory=list)
    audit_count: int = 0


class AuditEntry(BaseModel):
    timestamp: str
    action: str
    reviewer: str
    model_version: str
    output_sku: Optional[str] = None


class ReviewItemDetail(ReviewItem):
    audit: list[AuditEntry] = Field(default_factory=list)


class FeedbackRequestV1(BaseModel):
    item_id: str
    action: Literal["approve", "correct", "reject"]
    corrected_sku: Optional[str] = None
    reviewer: str

    @model_validator(mode="after")
    def check_corrected_sku(self):
        if self.action == "correct":
            if not self.corrected_sku or not self.corrected_sku.strip():
                raise ValueError("corrected_sku is required when action is 'correct'")
        return self
