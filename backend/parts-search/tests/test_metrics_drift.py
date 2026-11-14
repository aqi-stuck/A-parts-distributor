from fastapi.testclient import TestClient

from app.main import app


def test_metrics_includes_drift_score_key():
    """/metrics must always expose a drift_score field."""
    with TestClient(app) as client:
        r = client.get("/metrics")

    assert r.status_code == 200
    data = r.json()
    assert "drift_score" in data
    assert "drift_status" in data
    # No drift implementation exists yet, so the score is explicitly unavailable.
    if data["drift_score"] is None:
        assert data["drift_status"] == "not_computed"
