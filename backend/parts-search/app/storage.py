import base64
import json
import logging
import os
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

# numpy is only needed for drift statistics; a blocked native DLL must not stop
# the API from importing, so it is optional here.
try:
    import numpy as np
except Exception:  # noqa: BLE001
    np = None  # type: ignore[assignment]

from app.config import (
    CONFIDENCE_THRESHOLDS,
    DRIFT_THRESHOLD,
    PAGE_SIZE_DEFAULTS,
    TOO_CLOSE,
    WINDOW_OPTIONS,
)
from app.schemas.common import ItemStatus
from app.schemas.review import AuditEntry, ReviewItem, ReviewItemDetail
from app.schemas.search import build_result_item

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


def _compute_priority(candidates: list[dict]) -> int:
    """Calculate review priority (0-100, higher means urgent)."""
    if not candidates:
        return 100
    top_conf = float(candidates[0].get("confidence", candidates[0].get("score", 0.0)))
    return int(max(1, min(100, round((1.0 - top_conf) * 100))))


def _build_review_item_from_row(row: sqlite3.Row, feedback_rows: list[sqlite3.Row]) -> ReviewItem:
    """Construct a typed ReviewItem from a query_log row and matching feedback rows."""
    raw_candidates = json.loads(row["output_json"] or "[]")
    candidates = [build_result_item(c) for c in raw_candidates]
    priority = _compute_priority(raw_candidates)

    if feedback_rows:
        latest = feedback_rows[-1]
        decision = (latest["decision"] or "").lower()
        if decision == "approve":
            status = ItemStatus.approved
        elif decision == "correct":
            status = ItemStatus.corrected
        elif decision == "reject":
            status = ItemStatus.rejected
        else:
            status = ItemStatus.pending
    else:
        status = ItemStatus.pending

    audit_count = len(feedback_rows) + 1  # 1 for initial search event

    return ReviewItem(
        id=str(row["id"]),
        query=str(row["query"]),
        created_at=str(row["created_at"]),
        status=status,
        priority=priority,
        candidates=candidates,
        audit_count=audit_count,
    )


def get_review_queue_v1(
    cursor: Optional[str] = None,
    limit: int = 20,
) -> tuple[list[ReviewItem], Optional[str], Optional[int]]:
    """Cursor-paginated review queue ordered by priority desc, created_at asc."""
    limit = max(1, min(limit, 100))

    cursor_priority: Optional[int] = None
    cursor_created_at: Optional[str] = None
    cursor_id: Optional[int] = None

    if cursor:
        try:
            raw_json = base64.urlsafe_b64decode(cursor.encode()).decode()
            payload = json.loads(raw_json)
            cursor_priority = int(payload["priority"])
            cursor_created_at = str(payload.get("created_at", ""))
            cursor_id = int(payload["id"])
        except Exception:
            cursor_priority = None
            cursor_created_at = None
            cursor_id = None

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT COUNT(*) FROM query_log WHERE route = 'review'")
        total_estimate = cur.fetchone()[0]

        # Fetch review rows and their feedback
        cur = conn.execute("""
            SELECT q.id, q.query, q.top_sku, q.latency_ms, q.created_at,
                   q.model_version, q.output_json
            FROM query_log AS q
            WHERE q.route = 'review'
            ORDER BY q.id ASC
        """)
        all_q_rows = cur.fetchall()

        # Fetch all feedback grouped by query_id
        cur = conn.execute("SELECT id, query_id, decision, reviewer, created_at, sku FROM feedback ORDER BY id ASC")
        all_f = cur.fetchall()
        feedback_by_qid: dict[int, list[sqlite3.Row]] = {}
        for f in all_f:
            qid = f["query_id"]
            if qid is not None:
                feedback_by_qid.setdefault(qid, []).append(f)

    # Convert all into ReviewItems
    items: list[ReviewItem] = []
    for q_row in all_q_rows:
        f_list = feedback_by_qid.get(q_row["id"], [])
        items.append(_build_review_item_from_row(q_row, f_list))

    # Sort on backend by priority desc, then created_at asc, id asc
    items.sort(key=lambda item: (-item.priority, item.created_at, int(item.id)))

    # Apply cursor filter if present
    if cursor_priority is not None and cursor_id is not None:
        filtered = []
        for it in items:
            it_id = int(it.id)
            # Item is strictly after cursor in sort order (-priority, created_at, id)
            if it.priority < cursor_priority:
                filtered.append(it)
            elif it.priority == cursor_priority:
                if it.created_at > cursor_created_at:
                    filtered.append(it)
                elif it.created_at == cursor_created_at and it_id > cursor_id:
                    filtered.append(it)
        items = filtered

    # Paginate limit + 1
    page_items = items[:limit]
    has_more = len(items) > limit

    next_cursor = None
    if has_more and page_items:
        last = page_items[-1]
        cur_payload = {
            "priority": last.priority,
            "created_at": last.created_at,
            "id": int(last.id),
        }
        next_cursor = base64.urlsafe_b64encode(json.dumps(cur_payload).encode()).decode()

    return page_items, next_cursor, total_estimate


def get_review_item_detail_v1(item_id: str) -> Optional[ReviewItemDetail]:
    """Fetch a single review item with full audit trail."""
    try:
        qid = int(item_id)
    except ValueError:
        return None

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        q_row = conn.execute("SELECT * FROM query_log WHERE id = ?", (qid,)).fetchone()
        if not q_row:
            return None
        f_rows = conn.execute("SELECT * FROM feedback WHERE query_id = ? ORDER BY id ASC", (qid,)).fetchall()

    item = _build_review_item_from_row(q_row, f_rows)

    # Build audit entries
    audit: list[AuditEntry] = []
    # 1. Initial search event
    audit.append(
        AuditEntry(
            timestamp=str(q_row["created_at"]),
            action="initial_search",
            reviewer="system",
            model_version=str(q_row["model_version"] or "hybrid-retriever-v1"),
            output_sku=q_row["top_sku"],
        )
    )
    # 2. Subsequent feedback events
    for f in f_rows:
        audit.append(
            AuditEntry(
                timestamp=str(f["created_at"]),
                action=str(f["decision"]),
                reviewer=str(f["reviewer"] or "reviewer"),
                model_version=str(q_row["model_version"] or "hybrid-retriever-v1"),
                output_sku=f["sku"],
            )
        )

    return ReviewItemDetail(
        id=item.id,
        query=item.query,
        created_at=item.created_at,
        status=item.status,
        priority=item.priority,
        candidates=item.candidates,
        audit_count=len(audit),
        audit=audit,
    )


def save_feedback_v1(
    item_id: str,
    action: str,
    corrected_sku: Optional[str],
    reviewer: str,
) -> Optional[ReviewItem]:
    """Record human feedback and return the updated ReviewItem."""
    try:
        qid = int(item_id)
    except ValueError:
        return None

    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        q_row = conn.execute("SELECT * FROM query_log WHERE id = ?", (qid,)).fetchone()
        if not q_row:
            return None

        if action == "correct":
            sku = corrected_sku
        elif action == "approve":
            sku = q_row["top_sku"]
            if not sku:
                candidates = json.loads(q_row["output_json"] or "[]")
                sku = candidates[0].get("sku") if candidates else None
        else:
            sku = None

        created_at = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO feedback (query, sku, decision, created_at, reviewer, query_id) VALUES (?, ?, ?, ?, ?, ?)",
            (q_row["query"], sku, action, created_at, reviewer, qid),
        )
        f_rows = conn.execute("SELECT * FROM feedback WHERE query_id = ? ORDER BY id ASC", (qid,)).fetchall()

    return _build_review_item_from_row(q_row, f_rows)


def _percentile_nearest_rank(data: list[float], p: float) -> Optional[float]:
    if not data:
        return None
    sorted_data = sorted(data)
    n = len(sorted_data)
    rank = int(np.ceil((p / 100.0) * n))
    rank = max(1, min(rank, n))
    return sorted_data[rank - 1]


def get_monitoring_summary_v1(window: str = "1h", request_id: str = "") -> dict:
    """Precompute monitoring aggregates for window (15m, 1h, 24h)."""
    now = datetime.now(timezone.utc)
    if window == "15m":
        delta = timedelta(minutes=15)
    elif window == "24h":
        delta = timedelta(hours=24)
    else:
        window = "1h"
        delta = timedelta(hours=1)

    cutoff_iso = (now - delta).isoformat()

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT route, latency_ms FROM query_log WHERE created_at >= ?",
            (cutoff_iso,),
        ).fetchall()

    total_count = len(rows)
    review_count = sum(1 for r in rows if r[0] == "review")
    rate = round(review_count / total_count, 4) if total_count > 0 else 0.0

    latencies = [float(r[1]) for r in rows if r[1] is not None]
    if latencies:
        p50 = int(round(_percentile_nearest_rank(latencies, 50) or 0))
        p95 = int(round(_percentile_nearest_rank(latencies, 95) or 0))
        p99 = int(round(_percentile_nearest_rank(latencies, 99) or 0))
    else:
        p50, p95, p99 = None, None, None

    # Derive drift & OOD from existing /metrics synchronization
    m = metrics()
    drift_score = m.get("drift_window_score")
    alert_active = bool(m.get("drift_alert_active", 0))
    raw_status = m.get("drift_status", "warming_up")

    if alert_active:
        drift_status = "alert"
    elif raw_status == "warming_up" or total_count == 0:
        drift_status = "warming_up"
    else:
        drift_status = "ok"

    method = "psi" if drift_score is not None else None
    ood_flag_rate = float(m.get("ood_flag_rate") or 0.0)
    ood_mean_score = m.get("ood_score_mean")

    return {
        "schema_version": "1.0",
        "request_id": request_id,
        "model_version": "hybrid-retriever-v1",
        "window": window,
        "generated_at": now.isoformat(),
        "drift": {
            "score": drift_score,
            "alert_active": alert_active,
            "method": method,
            "status": drift_status,
        },
        "escalation": {
            "rate": rate,
            "review_count": review_count,
            "total_count": total_count,
        },
        "latency_ms": {
            "p50": p50,
            "p95": p95,
            "p99": p99,
        },
        "ood": {
            "flag_rate": ood_flag_rate,
            "mean_score": ood_mean_score,
        },
    }


_FACETS_CACHE: Optional[dict[str, list[dict]]] = None


def get_catalog_facets(catalog_path: str = "data/catalog.json") -> dict:
    """Compute and cache catalog facets (categories, brands, materials)."""
    global _FACETS_CACHE
    if _FACETS_CACHE is not None:
        return _FACETS_CACHE

    p = Path(catalog_path)
    if not p.is_file():
        p = Path(__file__).resolve().parent.parent / "data" / "catalog.json"
    if not p.is_file():
        p = Path(__file__).resolve().parents[3] / "data" / "catalog.json"
    if not p.is_file():
        return {"categories": [], "brands": [], "materials": []}

    with open(p, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    cat_counter = Counter(str(item.get("category", "")).strip() for item in catalog if item.get("category"))
    brand_counter = Counter(str(item.get("brand", "")).strip() for item in catalog if item.get("brand"))
    mat_counter = Counter(str(item.get("material", "")).strip() for item in catalog if item.get("material"))

    _FACETS_CACHE = {
        "categories": [{"value": k, "count": v} for k, v in cat_counter.most_common()],
        "brands": [{"value": k, "count": v} for k, v in brand_counter.most_common()],
        "materials": [{"value": k, "count": v} for k, v in mat_counter.most_common()],
    }
    return _FACETS_CACHE


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
            if np is not None and ood_scores:
                scores_arr = np.asarray(ood_scores)
                mean_score = float(np.mean(scores_arr)) if len(scores_arr) > 0 else None
                p95_score = float(np.percentile(scores_arr, 95)) if len(scores_arr) > 0 else None
            else:
                mean_score = None
                p95_score = None
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

        if np is None:
            # The statistics stack could not be imported in this process.
            drift_metrics["drift_status"] = "unavailable"

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
