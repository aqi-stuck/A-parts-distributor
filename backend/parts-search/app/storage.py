DB_PATH = "data/app.db"

import json
import sqlite3
import os
from datetime import datetime, timezone


def init_db():
    """Create data folder and tables if they do not exist, add missing columns."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_log (
                id INTEGER PRIMARY KEY,
                query TEXT,
                route TEXT,
                top_sku TEXT,
                latency_ms REAL,
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY,
                query TEXT,
                sku TEXT,
                decision TEXT,
                created_at TEXT
            )
        """)
        # Ensure query_log has model_version and output_json
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(query_log)").fetchall()}
        if "model_version" not in existing_cols:
            conn.execute("ALTER TABLE query_log ADD COLUMN model_version TEXT")
        if "output_json" not in existing_cols:
            conn.execute("ALTER TABLE query_log ADD COLUMN output_json TEXT")
        # Ensure feedback has reviewer
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(feedback)").fetchall()}
        if "reviewer" not in existing_cols:
            conn.execute("ALTER TABLE feedback ADD COLUMN reviewer TEXT")


def log_query(query, route, top_sku, latency_ms, model_version, output):
    """Insert a query log row with current UTC timestamp."""
    created_at = datetime.now(timezone.utc).isoformat()
    output_json = json.dumps(output)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO query_log (query, route, top_sku, latency_ms, created_at, model_version, output_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (query, route, top_sku, latency_ms, created_at, model_version, output_json)
        )


def save_feedback(query, sku, decision, reviewer=None):
    """Insert a feedback row with current UTC timestamp."""
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO feedback (query, sku, decision, created_at, reviewer) VALUES (?, ?, ?, ?, ?)",
            (query, sku, decision, created_at, reviewer)
        )


def review_queue(limit=50):
    """Return recent review queries ordered newest first."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT query, top_sku, latency_ms, created_at FROM query_log WHERE route = ? ORDER BY created_at DESC LIMIT ?",
            ("review", limit)
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]


def metrics():
    """Return total queries, review count and average latency."""
    with sqlite3.connect(DB_PATH) as conn:
        total = conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0]
        review = conn.execute("SELECT COUNT(*) FROM query_log WHERE route = 'review'").fetchone()[0]
        avg_row = conn.execute("SELECT AVG(latency_ms) FROM query_log").fetchone()[0]
        avg = round(avg_row, 2) if avg_row is not None else 0.0
    return {"total_queries": total, "review_count": review, "avg_latency_ms": avg}
