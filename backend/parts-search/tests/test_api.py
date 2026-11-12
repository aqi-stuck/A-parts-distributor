import json
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    """Health endpoint returns ok."""
    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


def test_search_shape():
    """Search returns expected shape and valid scores."""
    with TestClient(app) as client:
        r = client.post("/search", json={"query": "hex bolt 1/2 zinc"})
        assert r.status_code == 200
        data = r.json()
        assert set(data.keys()) >= {"route", "reason", "results", "latency_ms"}
        assert data["route"] in ("auto", "review")
        results = data["results"]
        assert isinstance(results, list)
        assert len(results) <= 5
        for item in results:
            assert set(item.keys()) >= {"sku", "description", "score", "confidence", "evidence"}
            assert isinstance(item["score"], (int, float))
            assert 0 <= item["score"] <= 1
            assert isinstance(item["confidence"], (int, float))
            assert 0 <= item["confidence"] <= 1


def test_empty_query_rejected():
    """Empty query is rejected by validation."""
    with TestClient(app) as client:
        r = client.post("/search", json={"query": ""})
        assert r.status_code == 422


def test_long_query_rejected():
    """Query longer than 500 chars is rejected."""
    with TestClient(app) as client:
        long_q = "a" * 501
        r = client.post("/search", json={"query": long_q})
        assert r.status_code == 422


def test_gibberish_goes_to_review():
    """Gibberish query should be routed to review."""
    with TestClient(app) as client:
        r = client.post("/search", json={"query": "zzqxv qqwpl"})
        assert r.status_code == 200
        assert r.json()["route"] == "review"


def test_results_come_from_catalog():
    """All returned SKUs must exist in catalog."""
    with TestClient(app) as client:
        r = client.post("/search", json={"query": "hex bolt"})
        assert r.status_code == 200
        results = r.json()["results"]
        with open("data/catalog.json", "r", encoding="utf-8") as f:
            catalog = json.load(f)
        catalog_skus = {p["sku"] for p in catalog}
        for item in results:
            assert item["sku"] in catalog_skus


def test_feedback_saved():
    """Feedback endpoint saves decision."""
    with TestClient(app) as client:
        r = client.post("/feedback", json={"query": "hex bolt", "sku": "BLT-0042", "decision": "approve"})
        assert r.status_code == 200
        assert r.json() == {"saved": True}


def test_feedback_bad_decision_rejected():
    """Invalid decision is rejected by validation."""
    with TestClient(app) as client:
        r = client.post("/feedback", json={"query": "hex bolt", "sku": "BLT-0042", "decision": "maybe"})
        assert r.status_code == 422


def test_review_queue_is_list():
    """Review queue returns a list."""
    with TestClient(app) as client:
        r = client.get("/review-queue")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


def test_metrics_shape():
    """Metrics endpoint returns required keys."""
    with TestClient(app) as client:
        r = client.get("/metrics")
        assert r.status_code == 200
        data = r.json()
        assert "total_queries" in data
        assert "review_count" in data
        assert "avg_latency_ms" in data
