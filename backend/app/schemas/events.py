from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class SearchCompletedPayload(BaseModel):
    query: str
    result_ids: List[int]
    timestamp: datetime

class ReviewCreatedPayload(BaseModel):
    query: str
    reason: str
    timestamp: datetime

class FeedbackRecordedPayload(BaseModel):
    query: str
    sku: str
    decision: str
    reviewer: Optional[str] = None
    timestamp: datetime

class DriftUpdatedPayload(BaseModel):
    drift_score: float
    timestamp: datetime

class HealthChangedPayload(BaseModel):
    status: str
    timestamp: datetime
