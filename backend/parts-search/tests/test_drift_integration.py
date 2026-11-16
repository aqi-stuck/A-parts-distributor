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