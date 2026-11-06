DB_PATH = "data/app.db"

import sqlite3
import os
from datetime import datetime, timezone


def init_db():
    """Create data folder and tables if they do not exist."""
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


def log_query(query, route, top_sku, latency_ms):
    """Insert a query log row with current UTC timestamp."""
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO query_log (query, route, top_sku, latency_ms, created_at) VALUES (?, ?, ?, ?, ?)",
            (query, route, top_sku, latency_ms, created_at)
        )


def save_feedback(query, sku, decision):
    """Insert a feedback row with current UTC timestamp."""
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO feedback (query, sku, decision, created_at) VALUES (?, ?, ?, ?)",
            (query, sku, decision, created_at)
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
