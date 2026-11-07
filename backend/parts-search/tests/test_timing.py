from fastapi.testclient import TestClient
from app.main import app

def test_timing_ms_present_and_valid():
    """Search response includes valid timing_ms."""
    with TestClient(app) as client:
        r = client.post("/search", json={"query": "hex bolt"})
        assert r.status_code == 200
        data = r.json()
        assert "timing_ms" in data
        timing = data["timing_ms"]
        assert set(timing.keys()) >= {"engine", "routing", "total"}
        for k in ("engine", "routing", "total"):
            v = timing[k]
            assert isinstance(v, (int, float))
            assert v >= 0
        assert timing["total"] >= timing["engine"]
        # latency_ms should equal total
        assert data["latency_ms"] == timing["total"]
