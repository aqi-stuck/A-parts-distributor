import json
import logging
import os
import sqlite3
from datetime import datetime, timezone
from typing import Any

import numpy as np

DB_PATH = os.environ.get("PARTS_DB_PATH", "data/app.db")
_WINDOW_SIZE = int(os.environ.get("DRIFT_WINDOW_SIZE", "100"))

_LOG_WRITE_FAILURES = 0


def record_log_failure() -> int:
    """Count one failed audit/log write and return the running total."""
    global _LOG_WRITE_FAILURES
    _LOG_WRITE_FAILURES += 1
    return _LOG_WRITE_FAILURES


def log_write_failures_total() -> int:
    """Return how many audit writes have failed since process start."""
    return _LOG_WRITE_FAILURES


def reset_log_write_failures() -> None:
    """Reset the counter (test helper)."""
    global _LOG_WRITE_FAILURES
    _LOG_WRITE_FAILURES = 0


def init_db():
    """Create data folder and tables if they do not exist, add missing columns."""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
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
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(query_log)").fetchall()}
        if "model_version" not in existing_cols:
            conn.execute("ALTER TABLE query_log ADD COLUMN model_version TEXT")
        if "output_json" not in existing_cols:
            conn.execute("ALTER TABLE query_log ADD COLUMN output_json TEXT")
        existing_cols = {row[1] for row in conn.execute("PRAGMA table_info(feedback)").fetchall()}
        if "reviewer" not in existing_cols:
            conn.execute("ALTER TABLE feedback ADD COLUMN reviewer TEXT")
        if "query_id" not in existing_cols:
            conn.execute("ALTER TABLE feedback ADD COLUMN query_id INTEGER")


def log_query(query, route, top_sku, latency_ms, model_version, output):
    """Insert a query log row with current UTC timestamp."""
    created_at = datetime.now(timezone.utc).isoformat()
    output_json = json.dumps(output)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO query_log (query, route, top_sku, latency_ms, created_at, model_version, output_json) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (query, route, top_sku, latency_ms, created_at, model_version, output_json)
        )


def save_feedback(query, sku, decision, reviewer=None, query_id=None):
    """Insert a feedback row with current UTC timestamp."""
    created_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO feedback (query, sku, decision, created_at, reviewer, query_id) VALUES (?, ?, ?, ?, ?, ?)",
            (query, sku, decision, created_at, reviewer, query_id)
        )


def review_queue(limit=50):
    """Return recent review queries ordered newest first."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            """
            SELECT q.id, q.query, q.top_sku, q.latency_ms, q.created_at,
                   q.output_json
            FROM query_log AS q
            WHERE q.route = ?
              AND NOT EXISTS (
                  SELECT 1 FROM feedback AS f WHERE f.query_id = q.id
              )
            ORDER BY q.created_at DESC
            LIMIT ?
            """,
            ("review", limit)
        )
        rows = cur.fetchall()
        items = []
        for row in rows:
            item = dict(row)
            item["results"] = json.loads(item.pop("output_json") or "[]")
            items.append(item)
        return items


_drifting: dict[str, Any] = {}
_drift_lock = __import__("threading").RLock()


def update_drift_metrics(
    window_size: int,
    psi_score: float | None,
    ks_score: float,
    alert_active: bool,
    window_end: datetime | None,
    ood_scores: list[float],
    ood_flagged: int,
) -> None:
    """Update the in-memory drift state. Must be called from the search service."""
    with _drift_lock:
        _drifting["window_size"] = window_size
        _drifting["psi_score"] = psi_score
        _drifting["ks_score"] = ks_score
        _drifting["alert_active"] = alert_active
        _drifting["window_end"] = window_end
        _drifting["ood_scores"] = list(ood_scores) if ood_scores else []
        _drifting["ood_flagged"] = ood_flagged


def metrics():
    """Return usage metrics; degrade gracefully when the audit store is down."""
    payload = {
        "total_queries": 0,
        "review_count": 0,
        "avg_latency_ms": 0.0,
        "db_status": "ok",
    }
    try:
        with sqlite3.connect(DB_PATH) as conn:
            total = conn.execute("SELECT COUNT(*) FROM query_log").fetchone()[0]
            review = conn.execute("SELECT COUNT(*) FROM query_log WHERE route = 'review'").fetchone()[0]
            avg_row = conn.execute("SELECT AVG(latency_ms) FROM query_log").fetchone()[0]
    except sqlite3.Error:
        logging.exception("metrics: audit store unavailable")
        payload["db_status"] = "unavailable"
    else:
        payload["total_queries"] = total
        payload["review_count"] = review
        payload["avg_latency_ms"] = round(avg_row, 2) if avg_row is not None else 0.0

    with _drift_lock:
        drift_data = dict(_drifting)
        ood_scores = drift_data.get("ood_scores", [])
        ood_flagged = drift_data.get("ood_flagged", 0)

        if not drift_data.get("window_end"):
            drift_metrics = {
                "drift_window_score": None,
                "drift_alert_active": 0,
                "drift_window_size": 0,
                "drift_last_window_end": None,
                "drift_status": "warming_up",
                "ood_score_mean": None,
                "ood_score_p95": None,
                "ood_flag_rate": None,
                "drift_score": None,
                "drift_alert": False,
            }
        else:
            scores_arr = np.asarray(ood_scores) if ood_scores else np.array([])
            mean_score = float(np.mean(scores_arr)) if len(scores_arr) > 0 else None
            p95_score = float(np.percentile(scores_arr, 95)) if len(scores_arr) > 0 else None
            total_ood = len(ood_scores)
            flag_rate = float(ood_flagged / total_ood) if total_ood > 0 else None
            psi = drift_data.get("psi_score")
            alert_active = drift_data.get("alert_active", False)

            drift_metrics = {
                "drift_window_score": psi,
                "drift_alert_active": 1 if alert_active else 0,
                "drift_window_size": drift_data.get("window_size", 0),
                "drift_last_window_end": drift_data["window_end"].isoformat() if drift_data.get("window_end") else None,
                "drift_status": "ok",
                "ood_score_mean": round(mean_score, 6) if mean_score is not None else None,
                "ood_score_p95": round(p95_score, 6) if p95_score is not None else None,
                "ood_flag_rate": round(flag_rate, 6) if flag_rate is not None else None,
                "drift_score": psi,
                "drift_alert": alert_active,
            }

    payload.update({
        "log_write_failures_total": log_write_failures_total(),
    })
    payload.update(drift_metrics)
    return payload


def reset_drift_metrics():
    """Reset drift state (test helper)."""
    global _drifting
    with _drift_lock:
        _drifting = {}