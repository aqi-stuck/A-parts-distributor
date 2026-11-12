from typing import List, Literal, Optional
from pydantic import BaseModel, Field

# What the website sends to /search
class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)

# One matching part in the results
class Candidate(BaseModel):
    sku: str
    description: str
    score: float
    confidence: float = 0.0
    evidence: List[str]

# What /search sends back
class SearchResponse(BaseModel):
    route: Literal["auto", "review"]
    reason: Optional[str] = None
    results: List[Candidate]
    latency_ms: float
    timing_ms: Optional[dict] = None

# What the website sends to /feedback
class FeedbackRequest(BaseModel):
    query: str
    sku: Optional[str] = None
    decision: Literal["approve", "correct", "reject"]
    reviewer: Optional[str] = None
    query_id: Optional[int] = None
