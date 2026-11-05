# Models for parts search API

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Incoming search query from warehouse staff."""
    query: str = Field(min_length=1, max_length=500)


class Candidate(BaseModel):
    """A candidate part returned by the search."""
    sku: str
    description: str
    score: float = Field(ge=0, le=1)
    evidence: List[str]


class SearchResponse(BaseModel):
    """Response with ranked candidates or escalation routing."""
    route: Literal["auto", "review"]
    reason: Optional[str] = None
    results: List[Candidate]
    latency_ms: float


class FeedbackRequest(BaseModel):
    """Human reviewer feedback on a search result."""
    query: str
    sku: str
    decision: Literal["approve", "reject"]
