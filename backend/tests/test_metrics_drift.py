from fastapi.testclient import TestClient

from app.main import app


def test_metrics_includes_drift_score_key():
    """/metrics must always expose drift score fields."""
    with TestClient(app) as client:
        r = client.get("/metrics")

    assert r.status_code == 200
    data = r.json()
    assert "drift_window_score" in data
    assert "drift_alert_active" in data
    assert "drift_window_size" in data
    assert "drift_last_window_end" in data
    assert "drift_status" in data
    assert "ood_score_mean" in data
    assert "ood_score_p95" in data
    assert "ood_flag_rate" in data
    # Initially warming_up with null score
    assert data["drift_window_score"] is None
    assert data["drift_status"] == "warming_up"


def test_metrics_drift_field_types():
    """All drift fields have correct types."""
    with TestClient(app) as client:
        r = client.get("/metrics")

    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["drift_window_score"], (float, type(None)))
    assert isinstance(data["drift_alert_active"], int)
    assert isinstance(data["drift_window_size"], int)
    assert isinstance(data["drift_last_window_end"], (str, type(None)))
    assert data["drift_status"] in ("warming_up", "ok")
    assert isinstance(data["ood_score_mean"], (float, type(None)))
    assert isinstance(data["ood_score_p95"], (float, type(None)))
    assert isinstance(data["ood_flag_rate"], (float, type(None)))
