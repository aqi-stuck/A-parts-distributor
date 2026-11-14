import json
import sqlite3
import threading
import time

import pytest
from fastapi.testclient import TestClient

import app.fallback as fallback_module
import app.search as search_module
import app.storage as storage
from app.main import app, service

CATALOG_SKUS = {part["sku"] for part in json.load(open("data/catalog.json", encoding="utf-8"))}


# 1. An empty query is rejected by request validation.
def test_empty_query_422():
    with TestClient(app) as client:
        r = client.post("/search", json={"query": ""})
        assert r.status_code == 422


# 2. A whitespace-only query is accepted but routed to human review.
def test_whitespace_only_review():
    with TestClient(app) as client:
        r = client.post("/search", json={"query": "   "})
        assert r.status_code == 200
        assert r.json()["route"] == "review"


# 3. Gibberish never matches a part and is routed to review.
def test_gibberish_review():
    with TestClient(app) as client:
        r = client.post("/search", json={"query": "qqqq zzzz"})
        assert r.status_code == 200
        assert r.json()["route"] == "review"


# 4. The 500-character limit is inclusive; 501 characters is rejected.
def test_length_limits():
    with TestClient(app) as client:
        r200 = client.post("/search", json={"query": "a" * 500})
        assert r200.status_code == 200
        r422 = client.post("/search", json={"query": "a" * 501})
        assert r422.status_code == 422


# 5. Injection-ish and special-character input is treated as data, never crashes.
def test_special_chars_safe():
    queries = [
        "<script>alert(1)</script> bolt",
        "' OR 1=1 --",
        "bolt\x00nut",
        "bolt 漢字 ü",
        "!!@@##$$%%^^&&**",
        "bolt\n\tnut",
    ]
    with TestClient(app) as client:
        for query in queries:
            r = client.post("/search", json={"query": query})
            assert r.status_code == 200, query
            data = r.json()
            assert data["route"] in ("auto", "review"), query
            for item in data["results"]:
                assert item["sku"] in CATALOG_SKUS, query


# 6. SQL text is stored as a value by parameterized SQL; the table survives.
def test_sql_text_stored_safely():
    query = "'); DROP TABLE query_log;--"
    with TestClient(app) as client:
        r = client.post("/search", json={"query": query})
        assert r.status_code == 200
    with sqlite3.connect(storage.DB_PATH) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "query_log" in tables
        stored = conn.execute("SELECT COUNT(*) FROM query_log WHERE query = ?", (query,)).fetchone()[0]
        assert stored >= 1


# 7. A failing engine falls back to keyword search and routes to review.
def test_engine_down_system_error(monkeypatch):
    def boom(query):
        raise RuntimeError("engine down")

    monkeypatch.setattr(service.engine, "search", boom)
    with TestClient(app) as client:
        r = client.post("/search", json={"query": "hex bolt zinc"})
        assert r.status_code == 200
        data = r.json()
        assert data["route"] == "review"
        assert data["reason"] == "system error"
        for item in data["results"]:
            assert item["sku"] in CATALOG_SKUS


# 8. When the engine and the keyword fallback both fail, the API still answers 200.
def test_engine_and_fallback_down(monkeypatch):
    def boom(query):
        raise RuntimeError("dependency down")

    monkeypatch.setattr(service.engine, "search", boom)
    monkeypatch.setattr(fallback_module, "keyword_fallback", boom)
    monkeypatch.setattr(search_module, "keyword_fallback", boom)
    with TestClient(app) as client:
        r = client.post("/search", json={"query": "hex bolt zinc"})
        assert r.status_code == 200
        data = r.json()
        assert data["route"] == "review"
        assert data["reason"] == "system error"
        assert data["results"] == []


# 9. A hanging engine is cut off by the timeout and answered from the fallback.
def test_engine_slow_timeout(monkeypatch):
    event = threading.Event()

    def slow(query):
        event.wait(5)
        return []

    monkeypatch.setattr(service.engine, "search", slow)
    monkeypatch.setattr(search_module, "ENGINE_TIMEOUT_MS", 300)
    try:
        with TestClient(app) as client:
            started = time.perf_counter()
            r = client.post("/search", json={"query": "hex bolt zinc"})
            wall = time.perf_counter() - started
        assert r.status_code == 200
        data = r.json()
        assert data["route"] == "review"
        assert data["reason"] == "engine timeout"
        assert wall < 2.0
        print(f"timeout wall time: {wall:.3f}s")
    finally:
        event.set()


# 10. A logging failure must never hide a successful search response.
def test_logging_down_still_200(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("logging down")

    monkeypatch.setattr(storage, "log_query", boom)
    with TestClient(app) as client:
        r = client.post("/search", json={"query": "hex bolt"})
        assert r.status_code == 200
        assert r.json()["route"] in ("auto", "review")


# 11. Metrics stay readable after a fault has been handled.
def test_metrics_still_works_after_fault(monkeypatch):
    def boom(query):
        raise RuntimeError("engine down")

    monkeypatch.setattr(service.engine, "search", boom)
    with TestClient(app) as client:
        client.post("/search", json={"query": "hex bolt"})
        r = client.get("/metrics")
        assert r.status_code == 200
        assert "total_queries" in r.json()
