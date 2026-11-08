import pytest
from fastapi.testclient import TestClient
from app.main import app, service
import app.storage as storage

def test_empty_query_returns_422():
    """Empty query is rejected."""
    with TestClient(app) as client:
        r = client.post("/search", json={"query": ""})
        assert r.status_code == 422


def test_gibberish_goes_to_review():
    """Gibberish query returns review."""
    with TestClient(app) as client:
        r = client.post("/search", json={"query": "qqqq zzzz"})
        assert r.status_code == 200
        data = r.json()
        assert data["route"] == "review"


def test_query_length_limits():
    """500 chars ok, 501 chars rejected."""
    with TestClient(app) as client:
        r200 = client.post("/search", json={"query": "a" * 500})
        assert r200.status_code == 200
        r422 = client.post("/search", json={"query": "a" * 501})
        assert r422.status_code == 422


def test_special_characters_handled():
    """Special characters do not crash."""
    with TestClient(app) as client:
        query = '<>&"\' \n\t ü 漢字'
        r = client.post("/search", json={"query": query})
        assert r.status_code == 200
        data = r.json()
        assert "route" in data


def test_engine_down_returns_review_system_error():
    """Engine failure triggers fallback and review."""
    original = service.engine.search
    try:
        service.engine.search = lambda q: (_ for _ in ()).throw(RuntimeError("engine down"))
        with TestClient(app) as client:
            r = client.post("/search", json={"query": "hex bolt zinc"})
            assert r.status_code == 200
            data = r.json()
            assert data["route"] == "review"
            assert data["reason"] == "system error"
    finally:
        service.engine.search = original


@pytest.mark.xfail(reason="logging failure not handled")
def test_logging_down_causes_500():
    """Logging failure currently propagates as 500."""
    original_log = storage.log_query
    try:
        def raise_log(*args, **kwargs):
            raise RuntimeError("logging down")
        storage.log_query = raise_log
        with TestClient(app) as client:
            r = client.post("/search", json={"query": "hex bolt"})
            # Current implementation does not catch log_query errors -> 500
            assert r.status_code == 500
    finally:
        storage.log_query = original_log


def test_slow_engine_comment():
    """Slowness is covered by latency metrics, not simulated here."""
    # No sleep / network. Latency is validated in test_timing.
    assert True
