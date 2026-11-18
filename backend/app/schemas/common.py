"""Shared response schemas and enums for the v1 API contract."""

from enum import Enum
from typing import Generic, Optional, TypeVar, Any
from pydantic import BaseModel, Field


class Route(str, Enum):
    auto = "auto"
    review = "review"


class ConfidenceLevel(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EvidenceMatch(str, Enum):
    exact = "exact"
    partial = "partial"
    mismatch = "mismatch"
    missing = "missing"


class ItemStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    corrected = "corrected"
    rejected = "rejected"


class BaseResponse(BaseModel):
    schema_version: str = "1.0"
    request_id: str
    model_version: str


class Confidence(BaseModel):
    value: float = Field(ge=0.0, le=1.0)
    level: ConfidenceLevel
    label: str


class Reason(BaseModel):
    code: str
    text: str


class Evidence(BaseModel):
    field: str
    query_value: Optional[str] = None
    catalog_value: Optional[str] = None
    match: EvidenceMatch


class ErrorDetails(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    error: ErrorDetails


T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    next_cursor: Optional[str] = None
    total_estimate: Optional[int] = None
