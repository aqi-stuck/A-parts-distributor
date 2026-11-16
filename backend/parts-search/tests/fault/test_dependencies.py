"""Dependency fault injection for /search (mock/monkeypatch, no real outages).

Documented behaviour (see docs/fault_injection.md):
  * any retrieval-stage failure -> route=review, reason="system error",
    results from the F8 keyword fallback (catalog-grounded), HTTP 200;
  * slow engine -> route=review, reason="engine timeout" within the configured
    engine_timeout_ms budget;
  * audit/log write failure -> HTTP 200, stderr fallback, counter incremented
    and exposed in /metrics as log_write_failures_total.
"""

import threading
import time

import pytest

import app.search as search_module
import app.storage as storage
from app.main import service
from tests.fault.conftest import CATALOG_SKUS


def _close_store(monkeypatch, tmp_path):
    """Point the audit store at an unopenable path (missing parent directory)."""
    monkeypatch.setattr(storage, "DB_PATH", str(tmp_path / "missing_dir" / "app.db"))


# Retrieval index unavailable: the BM25/lexical index raises.
def test_index_unavailable_falls_back(client, monkeypatch):
    def boom(*args, **kwargs):
        raise OSError("index file missing")

    monkeypatch.setattr(service.engine.retriever.baseline, "search", boom)
    r = client.post("/search", json={"query": "hex bolt zinc"})
    assert r.status_code == 200
    data = r.json()
    assert data["route"] == "review"
    assert data["reason"] == "system error"
    for item in data["results"]:
        assert item["sku"] in CATALOG_SKUS


# Embedding model raises during query projection.
def test_embedding_model_failure_falls_back(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("embedding service error")

    monkeypatch.setattr(service.engine.retriever.embedding_model, "transform", boom)
    r = client.post("/search", json={"query": "stainless washer m10"})
    assert r.status_code == 200
    data = r.json()
    assert data["route"] == "review"
    assert data["reason"] == "system error"
    for item in data["results"]:
        assert item["sku"] in CATALOG_SKUS


# Reranker raises (reranking is inline in the retriever's attribute scoring stage).
def test_reranker_failure_falls_back(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("reranker unavailable")

    monkeypatch.setattr(service.engine.retriever, "_attribute_score", boom)
    r = client.post("/search", json={"query": "zinc bolt m6"})
    assert r.status_code == 200
    data = r.json()
    assert data["route"] == "review"
    assert data["reason"] == "system error"
    for item in data["results"]:
        assert item["sku"] in CATALOG_SKUS


# Retrieval engine entirely unavailable (dependency down).
def test_engine_unavailable_falls_back(client, monkeypatch):
    def boom(query):
        raise RuntimeError("engine down")

    monkeypatch.setattr(service.engine, "search", boom)
    r = client.post("/search", json={"query": "hex bolt zinc"})
    assert r.status_code == 200
    data = r.json()
    assert data["route"] == "review"
    assert data["reason"] == "system error"
    assert data["results"], "keyword fallback should still return candidates"


# Engine and keyword fallback both unavailable: 200 with an empty result list.
def test_engine_and_fallback_unavailable(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("dependency down")

    monkeypatch.setattr(service.engine, "search", boom)
    monkeypatch.setattr(search_module, "keyword_fallback", boom)
    r = client.post("/search", json={"query": "hex bolt zinc"})
    assert r.status_code == 200
    data = r.json()
    assert data["route"] == "review"
    assert data["reason"] == "system error"
    assert data["results"] == []


# D9 (LLM explanations) is not implemented, so there is no explanation service
# to take down; the engine-stage test covers the same call path.
def test_llm_explanation_service_down():
    pytest.skip("D9 LLM explanations are not implemented in this build; no LLM dependency to fault")


# Slow model: the engine blocks longer than the configured timeout budget.
def test_slow_engine_respects_timeout_budget(client, monkeypatch):
    event = threading.Event()

    def slow(query):
        event.wait(5)
        return []

    monkeypatch.setattr(service.engine, "search", slow)
    monkeypatch.setattr(search_module, "ENGINE_TIMEOUT_MS", 300)
    try:
        started = time.perf_counter()
        r = client.post("/search", json={"query": "hex bolt zinc"})
        elapsed_ms = (time.perf_counter() - started) * 1000
    finally:
        event.set()

    assert r.status_code == 200
    data = r.json()
    assert data["route"] == "review"
    assert data["reason"] == "engine timeout"
    assert elapsed_ms < 2000, f"elapsed {elapsed_ms:.1f}ms exceeded the 2000ms budget"
    for item in data["results"]:
        assert item["sku"] in CATALOG_SKUS


# Audit store unavailable: /search still succeeds and the failure is counted.
def test_audit_store_unavailable_search_still_200(client, monkeypatch, tmp_path, capfd):
    _close_store(monkeypatch, tmp_path)
    r = client.post("/search", json={"query": "hex bolt zinc"})
    assert r.status_code == 200
    assert r.json()["route"] in ("auto", "review")

    metrics = client.get("/metrics")
    assert metrics.status_code == 200
    body = metrics.json()
    assert body["db_status"] == "unavailable"
    assert body["log_write_failures_total"] >= 1
    assert "query log failed" in capfd.readouterr().err


# Logging/audit write failure: request succeeds, stderr + counter record it.
def test_log_write_failure_is_counted(client, monkeypatch, capfd):
    def boom(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(storage, "log_query", boom)
    r = client.post("/search", json={"query": "hex bolt zinc"})
    assert r.status_code == 200
    assert r.json()["route"] in ("auto", "review")

    captured = capfd.readouterr()
    assert "query log failed" in captured.err

    metrics = client.get("/metrics").json()
    assert metrics["log_write_failures_total"] == 1


# Feedback store unavailable: reported in the body, not raised as a 500.
def test_feedback_store_unavailable(client, monkeypatch, tmp_path):
    _close_store(monkeypatch, tmp_path)
    r = client.post("/feedback", json={"query": "hex bolt", "sku": "BLT-0042", "decision": "approve"})
    assert r.status_code == 200
    assert r.json() == {"saved": False, "reason": "feedback_store_unavailable"}


# Review queue store unavailable: empty list instead of an error.
def test_review_queue_store_unavailable(client, monkeypatch, tmp_path):
    _close_store(monkeypatch, tmp_path)
    r = client.get("/review-queue")
    assert r.status_code == 200
    assert r.json() == []


# /metrics stays readable with the audit store down.
def test_metrics_survives_store_outage(client, monkeypatch, tmp_path):
    _close_store(monkeypatch, tmp_path)
    r = client.get("/metrics")
    assert r.status_code == 200
    body = r.json()
    assert body["db_status"] == "unavailable"
    assert body["total_queries"] == 0
