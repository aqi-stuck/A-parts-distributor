"""Search request and response schemas for v1 API."""

import re
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.common import (
    BaseResponse,
    Confidence,
    ConfidenceLevel,
    Evidence,
    EvidenceMatch,
    Reason,
    Route,
)
from app.config import get_confidence_level_and_label, map_reason_code_and_text


class SearchRequestV1(BaseModel):
    query: str = Field(..., max_length=500, description="Messy part query description")


class SearchTiming(BaseModel):
    normalize: int = 0
    retrieve: int = 0
    rerank: int = 0
    total: int = 0


class Result(BaseModel):
    sku: str
    description: str
    score: float = Field(ge=0.0, le=1.0)
    confidence: Confidence
    evidence: list[Evidence] = Field(default_factory=list)


class SearchResponseV1(BaseResponse):
    query: str
    route: Route
    reason: Reason
    timing_ms: SearchTiming
    results: list[Result] = Field(default_factory=list)


def parse_evidence_item(text: str) -> Evidence:
    """Convert raw candidate evidence string into a structured Evidence object."""
    lower = text.lower()
    if "mismatch" in lower:
        match_type = EvidenceMatch.mismatch
    elif "missing" in lower:
        match_type = EvidenceMatch.missing
    elif "exact" in lower or "match" in lower:
        match_type = EvidenceMatch.exact
    else:
        match_type = EvidenceMatch.partial

    # Look for patterns like "matched attribute: material = zinc"
    attr_match = re.search(r"attribute:\s*([a-zA-Z0-9_]+)\s*=\s*(.+)", text, re.IGNORECASE)
    if attr_match:
        field = attr_match.group(1).strip()
        val = attr_match.group(2).strip()
        return Evidence(
            field=field,
            query_value=val,
            catalog_value=val,
            match=match_type,
        )

    # Look for "sku match" or similar
    if "sku" in lower:
        return Evidence(
            field="sku",
            query_value=text,
            catalog_value=text,
            match=EvidenceMatch.exact if "exact" in lower else EvidenceMatch.partial,
        )

    return Evidence(
        field="description",
        query_value=text,
        catalog_value=text,
        match=match_type,
    )


def build_result_item(raw: dict) -> Result:
    """Build a typed Result model from an internal raw candidate dict."""
    score_val = max(0.0, min(1.0, float(raw.get("score", 0.0))))
    conf_val = max(0.0, min(1.0, float(raw.get("confidence", score_val))))
    level_str, label_str = get_confidence_level_and_label(conf_val)

    confidence = Confidence(
        value=round(conf_val, 4),
        level=ConfidenceLevel(level_str),
        label=label_str,
    )

    raw_evidence = raw.get("evidence", []) or []
    evidence_list = [parse_evidence_item(ev) for ev in raw_evidence]

    return Result(
        sku=str(raw.get("sku", "")),
        description=str(raw.get("description", "")),
        score=round(score_val, 4),
        confidence=confidence,
        evidence=evidence_list,
    )


def build_search_response_v1(
    query: str,
    raw_response: dict,
    request_id: str,
    model_version: str,
) -> SearchResponseV1:
    """Convert an internal search service output into SearchResponseV1."""
    route_str = str(raw_response.get("route", "review"))
    raw_reason = raw_response.get("reason")
    code, text = map_reason_code_and_text(route_str, raw_reason)

    raw_timing = raw_response.get("timing_ms", {}) or {}
    total_ms = int(round(raw_response.get("latency_ms", raw_timing.get("total", 0.0))))
    engine_ms = int(round(raw_timing.get("engine", 0.0)))
    routing_ms = int(round(raw_timing.get("routing", 0.0)))

    # Allocate stage timings (normalize, retrieve, rerank, total)
    normalize_ms = 1 if total_ms > 0 else 0
    retrieve_ms = max(0, engine_ms - normalize_ms)
    rerank_ms = max(0, routing_ms)

    timing = SearchTiming(
        normalize=normalize_ms,
        retrieve=retrieve_ms,
        rerank=rerank_ms,
        total=total_ms,
    )

    results_raw = raw_response.get("results", []) or []
    results = [build_result_item(r) for r in results_raw]

    # Special case: if results are empty, route must be review with reason code not_found
    if not results:
        route_str = "review"
        code, text = map_reason_code_and_text("review", "no matches")

    return SearchResponseV1(
        schema_version="1.0",
        request_id=request_id,
        model_version=model_version,
        query=query,
        route=Route(route_str),
        reason=Reason(code=code, text=text),
        timing_ms=timing,
        results=results,
    )
