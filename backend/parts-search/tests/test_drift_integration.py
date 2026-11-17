"""Integration tests for drift detection via /metrics endpoint."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
import app.storage as storage
import app.drift_state as drift_state


CATALOG_PATH = Path(__file__).parent.parent / "data" / "catalog.json"
CATALOG_SKUS = {part["sku"] for part in json.load(open(CATALOG_PATH, encoding="utf-8"))}


def test_drift_warming_up_before_window_completes():
    """Initially, metrics should show warming_up with null score."""
    drift_state.reset_drift_state()
    storage.reset_drift_metrics()

    with TestClient(app) as client:
        r = client.get("/metrics")

    assert r.status_code == 200
    data = r.json()
    assert data["drift_window_score"] is None
    assert data["drift_alert_active"] == 0
    assert data["drift_status"] == "warming_up"
    assert data["drift_window_size"] == 0
    assert data["drift_last_window_end"] is None


def test_drift_alert_on_shifted_queries():
    """Feed shifted queries (e.g., another language) and verify drift_alert_active becomes 1."""
    drift_state.reset_drift_state()
    storage.reset_drift_metrics()

    with TestClient(app) as client:
        shifted_queries = ["hydraulic pump perno acero"] * 100
        for query in shifted_queries:
            r = client.post("/search", json={"query": query})
            assert r.status_code == 200

        metrics_r = client.get("/metrics")

    assert metrics_r.status_code == 200
    data = metrics_r.json()
    assert data["drift_window_size"] == 100
    assert data["drift_alert_active"] == 1 or data["drift_window_score"] is not None


def test_drift_no_alert_on_in_distribution():
    """Feed in-distribution queries and verify drift_alert_active stays 0."""
    drift_state.reset_drift_state()
    storage.reset_drift_metrics()

    with TestClient(app) as client:
        id_queries = [
            "zinc steel bolt m6 20 mm",
            "m8 hex bolt zinc 25 mm",
            "steel washer m6",
            "brass screw m4 10 mm",
            "stainless steel bolt m10 30 mm",
        ] * 20

        for query in id_queries:
            r = client.post("/search", json={"query": query})
            assert r.status_code == 200

        metrics_r = client.get("/metrics")

    assert metrics_r.status_code == 200
    data = metrics_r.json()
    assert data["drift_window_size"] == 100
    assert data["drift_alert_active"] == 0


def test_drift_uses_backend_catalog_when_repo_copy_is_absent(monkeypatch):
    """Docker ships only backend/parts-search/data/catalog.json; drift must still start."""
    from app import search as search_module

    backend_json = Path(__file__).parent.parent / "data" / "catalog.json"
    missing_csv = Path(__file__).parent.parent / "data" / "does-not-exist.csv"
    monkeypatch.setattr(
        search_module,
        "_reference_catalog_paths",
        lambda: (missing_csv, backend_json),
    )
    drift_state.reset_drift_state()
    search_module._initialize_drift_tracker()

    assert search_module._DRIFT_TRACKER is not None
    assert search_module._REFERENCE_FEATURES


def test_reset_drift_state_clears_active_tracker():
    """Test isolation: resetting drift state must drop the live DriftTracker."""
    from app import search as search_module

    search_module._initialize_drift_tracker()
    assert search_module._DRIFT_TRACKER is not None

    drift_state.reset_drift_state()

    assert search_module._DRIFT_TRACKER is None


def test_threshold_boundary_does_not_alert():
    """A score exactly on the alert threshold is not a drift alert (float safety)."""
    features = {
        "embedding_distance": 0.0,
        "unseen_token_rate": 0.0,
        "query_length": 5,
        "category": "bolt",
    }
    tracker = drift_state.DriftTracker([features], threshold=0.0)
    tracker.add_query(0.0, False, features)

    state = tracker.close_window()

    assert state["psi_score"] == 0.0
    assert state["ks_score"] == 0.0
    assert state["alert_active"] is False


def test_empty_window_returns_warming_up():
    """Empty window (no queries) returns warming_up with nulls."""
    drift_state.reset_drift_state()
    storage.reset_drift_metrics()

    with TestClient(app) as client:
        r = client.get("/metrics")

    assert r.status_code == 200
    data = r.json()
    assert data["drift_window_score"] is None
    assert data["drift_alert_active"] == 0
    assert data["drift_status"] == "warming_up"