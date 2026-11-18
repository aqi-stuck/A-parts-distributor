#!/usr/bin/env python3
"""Generate contract JSON fixtures for the frontend using real Pydantic models."""

import base64
import json
import sys
from pathlib import Path

# Setup sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.schemas.common import (
    Confidence,
    ConfidenceLevel,
    Evidence,
    EvidenceMatch,
    ItemStatus,
    Paginated,
    Reason,
    Route,
)
from app.schemas.monitoring import (
    DriftSummary,
    EscalationSummary,
    LatencySummary,
    MonitoringSummaryResponse,
    OodSummary,
)
from app.schemas.review import ReviewItem
from app.schemas.search import Result, SearchResponseV1, SearchTiming


def generate_all_fixtures(output_dir: Path | None = None) -> None:
    if output_dir is None:
        repo_root = backend_dir.parent.parent
        output_dir = repo_root / "docs" / "examples"

    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. search_auto.json
    search_auto = SearchResponseV1(
        schema_version="1.0",
        request_id="req-auto-8a1f29b0",
        model_version="hybrid-retriever-v1",
        query="zinc hex bolt m8 x 30",
        route=Route.auto,
        reason=Reason(
            code="high_margin",
            text="Clear top match with distinct confidence margin.",
        ),
        timing_ms=SearchTiming(normalize=1, retrieve=14, rerank=2, total=17),
        results=[
            Result(
                sku="BOL-M8-030-0042",
                description="zinc steel hex bolt M8 x 30 mm",
                score=0.96,
                confidence=Confidence(
                    value=0.96,
                    level=ConfidenceLevel.high,
                    label="High confidence",
                ),
                evidence=[
                    Evidence(
                        field="thread",
                        query_value="M8",
                        catalog_value="M8",
                        match=EvidenceMatch.exact,
                    ),
                    Evidence(
                        field="finish",
                        query_value="zinc",
                        catalog_value="zinc",
                        match=EvidenceMatch.exact,
                    ),
                    Evidence(
                        field="length_mm",
                        query_value="30",
                        catalog_value="30",
                        match=EvidenceMatch.exact,
                    ),
                ],
            ),
            Result(
                sku="BOL-M8-035-0043",
                description="zinc steel hex bolt M8 x 35 mm",
                score=0.74,
                confidence=Confidence(
                    value=0.74,
                    level=ConfidenceLevel.medium,
                    label="Medium confidence",
                ),
                evidence=[
                    Evidence(
                        field="thread",
                        query_value="M8",
                        catalog_value="M8",
                        match=EvidenceMatch.exact,
                    ),
                    Evidence(
                        field="length_mm",
                        query_value="30",
                        catalog_value="35",
                        match=EvidenceMatch.mismatch,
                    ),
                ],
            ),
        ],
    )

    # 2. search_review.json
    search_review = SearchResponseV1(
        schema_version="1.0",
        request_id="req-review-5c3b9912",
        model_version="hybrid-retriever-v1",
        query="brass hex bolt 10mm",
        route=Route.review,
        reason=Reason(
            code="low_margin",
            text="Top candidates are too close in score; human verification needed.",
        ),
        timing_ms=SearchTiming(normalize=1, retrieve=21, rerank=3, total=25),
        results=[
            Result(
                sku="BOL-M10-025-1089",
                description="zinc steel hex bolt M10 x 25 mm",
                score=0.68,
                confidence=Confidence(
                    value=0.68,
                    level=ConfidenceLevel.low,
                    label="Low confidence",
                ),
                evidence=[
                    Evidence(
                        field="thread",
                        query_value="10mm",
                        catalog_value="M10",
                        match=EvidenceMatch.exact,
                    ),
                    Evidence(
                        field="material",
                        query_value="brass",
                        catalog_value="steel",
                        match=EvidenceMatch.mismatch,
                    ),
                ],
            ),
            Result(
                sku="SCR-M10-020-0541",
                description="brass machine screw M10 x 20 mm",
                score=0.66,
                confidence=Confidence(
                    value=0.66,
                    level=ConfidenceLevel.low,
                    label="Low confidence",
                ),
                evidence=[
                    Evidence(
                        field="material",
                        query_value="brass",
                        catalog_value="brass",
                        match=EvidenceMatch.exact,
                    ),
                    Evidence(
                        field="category",
                        query_value="bolt",
                        catalog_value="screw",
                        match=EvidenceMatch.mismatch,
                    ),
                ],
            ),
        ],
    )

    # 3. search_fallback.json
    search_fallback = SearchResponseV1(
        schema_version="1.0",
        request_id="req-fallback-44a108e1",
        model_version="hybrid-retriever-v1",
        query="stainless washer m12",
        route=Route.review,
        reason=Reason(
            code="dependency_unavailable",
            text="Search dependency is currently unavailable; falling back to catalog keyword search.",
        ),
        timing_ms=SearchTiming(normalize=1, retrieve=10, rerank=0, total=11),
        results=[
            Result(
                sku="WSH-M12-001-0988",
                description="stainless steel washer M12",
                score=0.55,
                confidence=Confidence(
                    value=0.55,
                    level=ConfidenceLevel.low,
                    label="Low confidence",
                ),
                evidence=[
                    Evidence(
                        field="description",
                        query_value="stainless washer m12",
                        catalog_value="stainless steel washer M12",
                        match=EvidenceMatch.partial,
                    )
                ],
            )
        ],
    )

    # 4. search_not_found.json
    search_not_found = SearchResponseV1(
        schema_version="1.0",
        request_id="req-notfound-09a8823f",
        model_version="hybrid-retriever-v1",
        query="zzqxv qqwpl non-existent widget 999",
        route=Route.review,
        reason=Reason(
            code="not_found",
            text="No matching parts found in catalog.",
        ),
        timing_ms=SearchTiming(normalize=1, retrieve=9, rerank=0, total=10),
        results=[],
    )

    # 5. review_queue.json
    cursor_payload = {"priority": 68, "created_at": "2026-11-17T12:00:00Z", "id": 104}
    encoded_cursor = base64.urlsafe_b64encode(json.dumps(cursor_payload).encode()).decode()

    review_queue = Paginated[ReviewItem](
        items=[
            ReviewItem(
                id="102",
                query="hydraulic perno acero",
                created_at="2026-11-17T11:45:00Z",
                status=ItemStatus.pending,
                priority=85,
                candidates=[
                    Result(
                        sku="BOL-M12-050-0112",
                        description="high tensile steel bolt M12 x 50 mm",
                        score=0.45,
                        confidence=Confidence(
                            value=0.45,
                            level=ConfidenceLevel.low,
                            label="Low confidence",
                        ),
                        evidence=[
                            Evidence(
                                field="material",
                                query_value="acero",
                                catalog_value="steel",
                                match=EvidenceMatch.partial,
                            )
                        ],
                    )
                ],
                audit_count=1,
            ),
            ReviewItem(
                id="103",
                query="brass hex bolt 10mm",
                created_at="2026-11-17T11:50:00Z",
                status=ItemStatus.pending,
                priority=72,
                candidates=[
                    Result(
                        sku="BOL-M10-025-1089",
                        description="zinc steel hex bolt M10 x 25 mm",
                        score=0.68,
                        confidence=Confidence(
                            value=0.68,
                            level=ConfidenceLevel.low,
                            label="Low confidence",
                        ),
                        evidence=[
                            Evidence(
                                field="material",
                                query_value="brass",
                                catalog_value="steel",
                                match=EvidenceMatch.mismatch,
                            )
                        ],
                    )
                ],
                audit_count=1,
            ),
            ReviewItem(
                id="104",
                query="m6 nylon locknut zinc",
                created_at="2026-11-17T12:00:00Z",
                status=ItemStatus.pending,
                priority=68,
                candidates=[
                    Result(
                        sku="NUT-M6-001-0321",
                        description="zinc steel nylon lock nut M6",
                        score=0.72,
                        confidence=Confidence(
                            value=0.72,
                            level=ConfidenceLevel.medium,
                            label="Medium confidence",
                        ),
                        evidence=[
                            Evidence(
                                field="thread",
                                query_value="M6",
                                catalog_value="M6",
                                match=EvidenceMatch.exact,
                            )
                        ],
                    )
                ],
                audit_count=1,
            ),
        ],
        next_cursor=encoded_cursor,
        total_estimate=42,
    )

    # 6. monitoring_summary.json (drift alert on)
    monitoring_summary = MonitoringSummaryResponse(
        schema_version="1.0",
        request_id="req-mon-alert-7721",
        window="1h",
        generated_at="2026-11-17T13:00:00Z",
        drift=DriftSummary(
            score=0.584487,
            alert_active=True,
            method="psi",
            status="alert",
        ),
        escalation=EscalationSummary(
            rate=0.28,
            review_count=28,
            total_count=100,
        ),
        latency_ms=LatencySummary(
            p50=22,
            p95=85,
            p99=140,
        ),
        ood=OodSummary(
            flag_rate=0.22,
            mean_score=0.3125,
        ),
    )

    # 7. monitoring_summary_ok.json (drift alert off)
    monitoring_summary_ok = MonitoringSummaryResponse(
        schema_version="1.0",
        request_id="req-mon-ok-9012",
        window="1h",
        generated_at="2026-11-17T13:00:00Z",
        drift=DriftSummary(
            score=0.082154,
            alert_active=False,
            method="psi",
            status="ok",
        ),
        escalation=EscalationSummary(
            rate=0.06,
            review_count=6,
            total_count=100,
        ),
        latency_ms=LatencySummary(
            p50=18,
            p95=42,
            p99=75,
        ),
        ood=OodSummary(
            flag_rate=0.03,
            mean_score=0.1245,
        ),
    )

    fixtures = {
        "search_auto.json": search_auto.model_dump(),
        "search_review.json": search_review.model_dump(),
        "search_fallback.json": search_fallback.model_dump(),
        "search_not_found.json": search_not_found.model_dump(),
        "review_queue.json": review_queue.model_dump(),
        "monitoring_summary.json": monitoring_summary.model_dump(),
        "monitoring_summary_ok.json": monitoring_summary_ok.model_dump(),
    }

    for filename, data in fixtures.items():
        file_path = output_dir / filename
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        print(f"Generated fixture: {file_path}")


if __name__ == "__main__":
    generate_all_fixtures()
