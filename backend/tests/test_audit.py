import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_audit_trail_model_version_and_output():
    """Search logs model version and output_json."""
    with TestClient(app) as client:
        r = client.post("/search", json={"query": "hex bolt"})
        assert r.status_code == 200
        conn = sqlite3.connect("data/app.db")
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT model_version, output_json FROM query_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["model_version"] == "hybrid-retriever-v1"
        assert row["output_json"]
        assert len(row["output_json"]) > 2


def test_feedback_reviewer_saved():
    """Feedback reviewer is persisted."""
    with TestClient(app) as client:
        r = client.post("/feedback", json={"query": "hex bolt", "sku": "BLT-0042", "decision": "approve", "reviewer": "tester"})
        assert r.status_code == 200
        conn = sqlite3.connect("data/app.db")
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT reviewer FROM feedback ORDER BY id DESC LIMIT 1"
        ).fetchone()
        conn.close()
        assert row is not None
        assert row["reviewer"] == "tester"
