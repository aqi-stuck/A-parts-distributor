"""Monitoring summary schemas for v1 API."""

from typing import Literal, Optional
from pydantic import BaseModel, Field

from app.schemas.common import BaseResponse


class DriftSummary(BaseModel):
    score: Optional[float] = None
    alert_active: bool = False
    method: Optional[Literal["psi", "ks"]] = None
    status: Literal["ok", "alert", "warming_up"] = "warming_up"


class EscalationSummary(BaseModel):
    rate: float = Field(ge=0.0, le=1.0, default=0.0)
    review_count: int = 0
    total_count: int = 0


class LatencySummary(BaseModel):
    p50: Optional[int] = None
    p95: Optional[int] = None
    p99: Optional[int] = None


class OodSummary(BaseModel):
    flag_rate: float = Field(ge=0.0, le=1.0, default=0.0)
    mean_score: Optional[float] = None


class MonitoringSummaryResponse(BaseResponse):
    window: Literal["15m", "1h", "24h"] = "1h"
    generated_at: str
    drift: DriftSummary
    escalation: EscalationSummary
    latency_ms: LatencySummary
    ood: OodSummary
