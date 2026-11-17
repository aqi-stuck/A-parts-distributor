"""Contract tests for all /v1 endpoints, error shapes, cursor pagination, and fallback."""

import uuid
from fastapi.testclient import TestClient
import pytest

from app.main import app, service
from app.schemas.common import ErrorResponse, ItemStatus, Paginated, Route
from app.schemas.monitoring import MonitoringSummaryResponse
from app.schemas.public import CatalogFacetsResponse, HealthResponseV1, PublicConfigResponse
from app.schemas.review import ReviewItem, ReviewItemDetail
from app.schemas.search import SearchResponseV1
import app.storage as storage


def test_v1_search_valid_query():
    with TestClient(app) as client:
        r = client.post("/v1/search", json={"query": "hex bolt zinc"})
    assert r.status_code == 200
    assert "X-Request-ID" in r.headers

    data = r.json()
    model = SearchResponseV1.model_validate(data)
    assert model.request_id == r.headers["X-Request-ID"]
    assert model.route in (Route.auto, Route.review)
    assert model.reason.code in (
        "high_margin",
        "low_margin",
        "attribute_mismatch",
        "ood_query",
        "dependency_unavailable",
        "empty_query",
        "not_found",
    )
    assert isinstance(model.results, list)
    for res in model.results:
        assert isinstance(res.sku, str)
        assert 0.0 <= res.score <= 1.0
        assert 0.0 <= res.confidence.value <= 1.0
        assert isinstance(res.evidence, list)
        for ev in res.evidence:
            assert ev.match.value in ("exact", "partial", "mismatch", "missing")


def test_v1_search_empty_and_whitespace_returns_400():
    with TestClient(app) as client:
        # 1. empty string
        r1 = client.post("/v1/search", json={"query": ""})
        assert r1.status_code == 400
        err1 = ErrorResponse.model_validate(r1.json())
        assert err1.error.code == "validation_error"

        # 2. whitespace only
        r2 = client.post("/v1/search", json={"query": "   \n\t  "})
        assert r2.status_code == 400
        err2 = ErrorResponse.model_validate(r2.json())
        assert err2.error.code == "validation_error"

        # 3. missing field
        r3 = client.post("/v1/search", json={})
        assert r3.status_code == 400
        err3 = ErrorResponse.model_validate(r3.json())
        assert err3.error.code == "validation_error"


def test_v1_search_not_found_returns_empty_results_review():
    with TestClient(app) as client:
        r = client.post("/v1/search", json={"query": "zzqxv qqwpl non-existent part 9999"})
    assert r.status_code == 200
    model = SearchResponseV1.model_validate(r.json())
    assert model.route == Route.review
    assert isinstance(model.results, list)


def test_v1_search_fallback_returns_same_shape_on_failure():
    orig_search = service.engine.search
    try:
        service.engine.search = lambda q: (_ for _ in ()).throw(RuntimeError("retrieval engine down"))
        with TestClient(app) as client:
            r = client.post("/v1/search", json={"query": "steel bolt"})
        assert r.status_code == 200
        model = SearchResponseV1.model_validate(r.json())
        assert model.route == Route.review
        assert model.reason.code == "dependency_unavailable"
        assert isinstance(model.results, list)
    finally:
        service.engine.search = orig_search


def test_v1_review_queue_endpoint_and_pagination():
    # Insert multiple review records to test cursor pagination
    test_queries = [f"test-review-query-{uuid.uuid4().hex[:6]}" for _ in range(5)]
    with TestClient(app) as client:
        for q in test_queries:
            storage.log_query(
                query=q,
                route="review",
                top_sku="TEST-SKU",
                latency_ms=15.0,
                model_version="hybrid-retriever-v1",
                output=[{"sku": "TEST-SKU", "description": "test", "score": 0.4, "confidence": 0.4, "evidence": []}],
            )

        # Page 1: limit 2
        r1 = client.get("/v1/review-queue?limit=2")
        assert r1.status_code == 200
        p1 = Paginated[ReviewItem].model_validate(r1.json())
        assert len(p1.items) == 2
        assert p1.next_cursor is not None
        assert p1.total_estimate is not None and p1.total_estimate >= 5

        # Page 2: with cursor
        r2 = client.get(f"/v1/review-queue?limit=2&cursor={p1.next_cursor}")
        assert r2.status_code == 200
        p2 = Paginated[ReviewItem].model_validate(r2.json())
        assert len(p2.items) == 2

        # Ensure no overlap between page 1 and page 2
        ids_p1 = {it.id for it in p1.items}
        ids_p2 = {it.id for it in p2.items}
        assert ids_p1.isdisjoint(ids_p2)

        # Insert item during pagination to verify cursor stability
        storage.log_query(
            query="inserted-between-pages",
            route="review",
            top_sku="TEST-SKU-NEW",
            latency_ms=10.0,
            model_version="hybrid-retriever-v1",
            output=[],
        )

        # Page 3
        r3 = client.get(f"/v1/review-queue?limit=2&cursor={p2.next_cursor}")
        assert r3.status_code == 200
        p3 = Paginated[ReviewItem].model_validate(r3.json())
        ids_p3 = {it.id for it in p3.items}
        assert ids_p1.isdisjoint(ids_p3)
        assert ids_p2.isdisjoint(ids_p3)


def test_v1_review_queue_item_detail_and_404():
    # Seed a review item
    q_str = f"detail-test-{uuid.uuid4().hex[:6]}"
    storage.log_query(
        query=q_str,
        route="review",
        top_sku="DETAIL-SKU",
        latency_ms=12.0,
        model_version="hybrid-retriever-v1",
        output=[{"sku": "DETAIL-SKU", "description": "detail desc", "score": 0.5, "confidence": 0.5, "evidence": ["exact match"]}],
    )
    with TestClient(app) as client:
        # Get latest queue item to find id
        rq = client.get("/v1/review-queue?limit=1")
        item_id = rq.json()["items"][0]["id"]

        # Detail endpoint
        r = client.get(f"/v1/review-queue/{item_id}")
        assert r.status_code == 200
        detail = ReviewItemDetail.model_validate(r.json())
        assert detail.id == item_id
        assert isinstance(detail.audit, list)
        assert len(detail.audit) >= 1
        assert detail.audit[0].action == "initial_search"

        # Missing item returns 404 ErrorResponse
        r_miss = client.get("/v1/review-queue/999999999")
        assert r_miss.status_code == 404
        err = ErrorResponse.model_validate(r_miss.json())
        assert err.error.code == "not_found"


def test_v1_feedback_flow():
    # Seed item
    q_str = f"feedback-test-{uuid.uuid4().hex[:6]}"
    storage.log_query(
        query=q_str,
        route="review",
        top_sku="FB-SKU",
        latency_ms=10.0,
        model_version="hybrid-retriever-v1",
        output=[{"sku": "FB-SKU", "description": "desc", "score": 0.5, "confidence": 0.5, "evidence": []}],
    )
    with TestClient(app) as client:
        rq = client.get("/v1/review-queue?limit=1")
        item_id = rq.json()["items"][0]["id"]

        # Approve feedback
        r_app = client.post(
            "/v1/feedback",
            json={"item_id": item_id, "action": "approve", "reviewer": "qa-reviewer"},
        )
        assert r_app.status_code == 200
        updated = ReviewItem.model_validate(r_app.json())
        assert updated.status == ItemStatus.approved
        assert updated.audit_count >= 2

        # Correct feedback without corrected_sku fails validation 400
        r_bad = client.post(
            "/v1/feedback",
            json={"item_id": item_id, "action": "correct", "reviewer": "qa-reviewer"},
        )
        assert r_bad.status_code == 400
        err = ErrorResponse.model_validate(r_bad.json())
        assert err.error.code == "validation_error"

        # Correct feedback with corrected_sku succeeds
        r_cor = client.post(
            "/v1/feedback",
            json={"item_id": item_id, "action": "correct", "corrected_sku": "CORRECTED-123", "reviewer": "qa-reviewer"},
        )
        assert r_cor.status_code == 200
        updated_cor = ReviewItem.model_validate(r_cor.json())
        assert updated_cor.status == ItemStatus.corrected


def test_v1_monitoring_summary_and_windows():
    with TestClient(app) as client:
        for w in ("15m", "1h", "24h"):
            r = client.get(f"/v1/monitoring/summary?window={w}")
            assert r.status_code == 200
            model = MonitoringSummaryResponse.model_validate(r.json())
            assert model.window == w
            assert model.drift.status in ("ok", "alert", "warming_up")
            assert 0.0 <= model.escalation.rate <= 1.0

        # Invalid window returns 400
        r_inv = client.get("/v1/monitoring/summary?window=7d")
        assert r_inv.status_code == 400
        err = ErrorResponse.model_validate(r_inv.json())
        assert err.error.code == "validation_error"


def test_v1_catalog_facets():
    with TestClient(app) as client:
        r = client.get("/v1/catalog/facets")
    assert r.status_code == 200
    model = CatalogFacetsResponse.model_validate(r.json())
    assert isinstance(model.categories, list)
    assert isinstance(model.brands, list)
    assert isinstance(model.materials, list)
    assert len(model.categories) > 0


def test_v1_config_public():
    with TestClient(app) as client:
        r = client.get("/v1/config/public")
    assert r.status_code == 200
    model = PublicConfigResponse.model_validate(r.json())
    assert "high" in model.confidence_thresholds
    assert "medium" in model.confidence_thresholds
    assert "low" in model.confidence_thresholds
    assert model.page_size_defaults.default_limit == 20
    assert model.page_size_defaults.max_limit == 100


def test_v1_health():
    with TestClient(app) as client:
        r = client.get("/v1/health")
    assert r.status_code == 200
    model = HealthResponseV1.model_validate(r.json())
    assert model.status in ("ok", "degraded")
    assert model.dependencies.index in ("ok", "down")
    assert model.dependencies.model in ("ok", "down")


def test_null_safety_no_null_lists_across_endpoints():
    with TestClient(app) as client:
        res = client.post("/v1/search", json={"query": "zzqxv qqwpl"}).json()
        assert res.get("results") is not None
        assert isinstance(res.get("results"), list)

        q = client.get("/v1/review-queue").json()
        assert q.get("items") is not None
        assert isinstance(q.get("items"), list)

        facets = client.get("/v1/catalog/facets").json()
        assert facets.get("categories") is not None
        assert facets.get("brands") is not None
        assert facets.get("materials") is not None
