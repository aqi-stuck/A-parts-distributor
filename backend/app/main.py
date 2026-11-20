import logging
import sys
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request, Response
from app.routes import Route, ENDPOINTS, DISCOVERY
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import (
    ALLOWED_ORIGINS,
    ENGINE,
    ENGINE_TIMEOUT_MS,
    MODEL_VERSION,
    PAGE_SIZE_DEFAULTS,
    WINDOW_OPTIONS,
)
from app.models import FeedbackRequest as FeedbackRequestV0
from app.routes import DISCOVERY, SEARCH, FEEDBACK, REVIEW_QUEUE, EVENTS, HEALTH
from app.models import SearchRequest as SearchRequestV0
from app.models import SearchResponse as SearchResponseV0
from app.schemas.common import ErrorDetails, ErrorResponse, Paginated, Reason
from app.schemas.monitoring import MonitoringSummaryResponse
from app.schemas.public import (
    CatalogFacetsResponse,
    DependencyStatus,
    HealthResponseV1,
    PageSizeDefaults,
    PublicConfigResponse,
)
from app.schemas.review import FeedbackRequestV1, ReviewItem, ReviewItemDetail
from app.schemas.search import (
    SearchRequestV1,
    SearchResponseV1,
    build_search_response_v1,
)
from app.search import SearchService
import app.storage as storage

def _resolve_catalog_path(default_rel: str = "data/catalog.json") -> str:
    from pathlib import Path
    p = Path(default_rel)
    if p.is_file():
        return str(p)
    p_backend = Path(__file__).resolve().parent.parent / default_rel
    if p_backend.is_file():
        return str(p_backend)
    p_repo = Path(__file__).resolve().parents[2] / "backend" / default_rel
    if p_repo.is_file():
        return str(p_repo)
    return default_rel


service = SearchService(_resolve_catalog_path("data/catalog.json"))


def build_endpoint_map() -> None:
    """Generate ENDPOINTS list from FastAPI router definitions."""
    global ENDPOINTS
    ENDPOINTS.clear()
    for r in app.routes:
        if not getattr(r, "path", None) or not r.path.startswith("/"):
            continue
        methods = getattr(r, "methods", set())
        for m in methods:
            if m in {"GET", "POST", "PUT", "DELETE", "PATCH"}:
                response_model = getattr(r, "response_model", None)
                if response_model:
                    response_name = getattr(response_model, "__name__", str(response_model))
                else:
                    response_name = None
                ENDPOINTS.append({
                    "name": getattr(r, "name", ""),
                    "method": m,
                    "path": r.path,
                    "response_model": response_name,
                })


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.init_db()
    examples = storage.get_feedback_training_examples()
    if hasattr(service.engine, "reload_feedback"):
        service.engine.reload_feedback(examples)
    # Pre-cache facets
    storage.get_catalog_facets("data/catalog.json")
    build_endpoint_map()
    yield


app = FastAPI(title="Parts Search API", lifespan=lifespan)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = req_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response


app.add_middleware(RequestIDMiddleware)

# CORS middleware with origins from configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    is_v1 = request.url.path.startswith("/v1")
    formatted_errors = [
        {
            "loc": [str(x) for x in err.get("loc", [])],
            "msg": str(err.get("msg", "")),
            "type": str(err.get("type", "")),
        }
        for err in exc.errors()
    ]
    if is_v1:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error=ErrorDetails(
                    code="validation_error",
                    message="Validation error: invalid request payload",
                    details={"errors": formatted_errors, "request_id": req_id},
                )
            ).model_dump(),
            headers={"X-Request-ID": req_id},
        )
    return JSONResponse(
        status_code=422,
        content={"detail": formatted_errors},
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    req_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    is_v1 = request.url.path.startswith("/v1")
    code = "not_found" if exc.status_code == 404 else ("validation_error" if exc.status_code == 400 else "http_error")
    if is_v1 or isinstance(exc.detail, dict):
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                error=ErrorDetails(
                    code=code,
                    message=str(exc.detail),
                    details={"request_id": req_id},
                )
            ).model_dump(),
            headers={"X-Request-ID": req_id},
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": str(exc.detail)},
        headers={"X-Request-ID": req_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    req_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    logging.exception("Unhandled error for request %s: %s", req_id, exc)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetails(
                code="internal_error",
                message="An internal server error occurred",
                details={"request_id": req_id},
            )
        ).model_dump(),
        headers={"X-Request-ID": req_id},
    )


# ==========================================
# Legacy Routes (v0) - Backward Compatible
# ==========================================


@app.get(HEALTH)
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponseV0)
def search_legacy(req: SearchRequestV0):
    """Search parts and log the query; legacy route."""
    result = service.search(req.query)
    results = result.get("results", [])
    top_sku = results[0]["sku"] if results else None
    try:
        storage.log_query(req.query, result["route"], top_sku, result["latency_ms"], MODEL_VERSION, results)
    except Exception:
        storage.record_log_failure()
        logging.exception("query log failed")
        print(f"query log failed: query={req.query[:80]!r}", file=sys.stderr)
    return result


@app.post("/feedback")
def feedback_legacy(req: FeedbackRequestV0):
    """Save human feedback for a query; legacy route."""
    try:
        storage.save_feedback(req.query, req.sku, req.decision, req.reviewer, req.query_id)
        if req.decision in {"approve", "correct"} and req.sku:
            if hasattr(service.engine, "record_feedback"):
                service.engine.record_feedback(req.query, req.sku)
    except Exception:
        storage.record_log_failure()
        logging.exception("feedback save failed")
        print(f"feedback save failed: query={req.query[:80]!r}", file=sys.stderr)
        return {"saved": False, "reason": "feedback_store_unavailable"}
    return {"saved": True}


@app.get("/review-queue")
def review_queue_legacy():
    """Get recent queries needing human review; legacy route."""
    try:
        return storage.review_queue()
    except Exception:
        logging.exception("review queue unavailable")
        print("review queue unavailable", file=sys.stderr)
        return []


@app.get("/metrics")
def metrics():
    """Get basic usage metrics; legacy and v1 compatible."""
    return storage.metrics()


# ==========================================
# V1 API Routes

# -------------------------------------------------
# Discovery endpoint (GET /v1) – returns generated endpoint map
# -------------------------------------------------
from fastapi.responses import StreamingResponse
import json
import asyncio
from datetime import datetime, timezone
from collections import deque
from prometheus_client import Counter, Gauge

# Metrics for event streaming
event_publish_failures_total = Counter("event_publish_failures_total", "Count of failures when publishing SSE events")
# Gauge for current subscriber count
event_subscriber_current = Gauge("event_subscriber_current", "Current number of active SSE subscribers")

# In‑memory ring buffer for the last 200 events (id, type, payload dict)
_EVENT_BUFFER = deque(maxlen=200)
_event_id_seq = 0
_current_subscribers = 0
_MAX_SUBSCRIBERS = 50

def _next_event_id() -> int:
    global _event_id_seq
    _event_id_seq += 1
    return _event_id_seq

def publish_event(event_type: str, payload: dict):
    """Publish an event to the ring buffer. Non‑blocking – errors are counted.
    """
    try:
        eid = _next_event_id()
        _EVENT_BUFFER.append({"id": eid, "type": event_type, "payload": payload})
    except Exception:
        event_publish_failures_total.inc()

@app.get(Route.DISCOVERY)
async def discovery(request: Request):
    req_id = getattr(request.state, "request_id", uuid4().hex)
    endpoint_list = []
    for ep in ENDPOINTS:
        endpoint_list.append({
            "name": ep["name"],
            "method": ep["method"],
            "path": ep["path"],
            "response_model": ep["response_model"],
        })
    doc = {
        "schema_version": "1.0",
        "request_id": req_id,
        "base_path": "/v1",
        "endpoints": endpoint_list,
        "events_stream": {"path": Route.EVENTS, "transport": "sse"},
    }
    return JSONResponse(content=doc)

# -------------------------------------------------
# Server‑Sent Events endpoint
# -------------------------------------------------
@app.get(Route.EVENTS)
async def events_stream(request: Request, types: Optional[str] = None):
    global _current_subscribers
    if _current_subscribers >= _MAX_SUBSCRIBERS:
        raise HTTPException(
            status_code=503,
            detail={"code": "too_many_streams", "message": "Maximum number of event streams reached"},
        )
    _current_subscribers += 1
    client_last_id = request.headers.get("Last-Event-ID")
    allowed_types = set(types.split(",")) if types else None

    async def event_generator():
        # Replay missed events if Last-Event-ID supplied
        if client_last_id and client_last_id.isdigit():
            last_id = int(client_last_id)
            # Find events with id > last_id
            missed = [e for e in list(_EVENT_BUFFER) if e["id"] > last_id]
            if missed:
                for ev in missed:
                    if allowed_types and ev["type"] not in allowed_types:
                        continue
                    yield f"id: {ev['id']}\n"
                    yield f"event: {ev['type']}\n"
                    data = json.dumps({
                        "schema_version": "1.0",
                        "request_id": request.state.request_id,
                        "emitted_at": datetime.utcnow().isoformat() + "Z",
                        "payload": ev["payload"],
                    })
                    yield f"data: {data}\n\n"
            else:
                # Buffer does not contain requested id → ask client to resync
                yield "event: resync\n"
                yield "data: {}\n\n"
        # Live feed loop
        keepalive_interval = 15.0
        while True:
            # Check client disconnect
            if await request.is_disconnected():
                break
            # Emit any new events that arrive after this point
            # We'll poll the buffer periodically for new entries
            current_len = len(_EVENT_BUFFER)
            start_index = current_len
            while True:
                await asyncio.sleep(0.5)
                if await request.is_disconnected():
                    break
                if len(_EVENT_BUFFER) > start_index:
                    new_events = list(_EVENT_BUFFER)[start_index:]
                    start_index = len(_EVENT_BUFFER)
                    for ev in new_events:
                        if allowed_types and ev["type"] not in allowed_types:
                            continue
                        yield f"id: {ev['id']}\n"
                        yield f"event: {ev['type']}\n"
                        data = json.dumps({
                            "schema_version": "1.0",
                            "request_id": request.state.request_id,
                            "emitted_at": datetime.utcnow().isoformat() + "Z",
                            "payload": ev["payload"],
                        })
                        yield f"data: {data}\n\n"
                # Keep‑alive comment
                now = datetime.utcnow().timestamp()
                if now % keepalive_interval < 0.6:
                    yield ": keepalive\n\n"
        # End of stream – decrement subscriber count
        # (will also be handled in finally block below)

    try:
        return StreamingResponse(event_generator(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
    finally:
        _current_subscribers = max(0, _current_subscribers - 1)

# -------------------------------------------------
# Hook publishing into existing actions (example: feedback)
# -------------------------------------------------
from app.schemas.events import FeedbackRecordedPayload

@app.post(Route.FEEDBACK, response_model=ReviewItem)
def feedback_v1(req: FeedbackRequestV1):
    updated = storage.save_feedback_v1(
        item_id=req.item_id,
        action=req.action,
        corrected_sku=req.corrected_sku,
        reviewer=req.reviewer,
    )
    if not updated:
        raise HTTPException(status_code=404, detail=f"Review item {req.item_id} not found")
    if req.action in {"approve", "correct"}:
        feedback_sku = req.corrected_sku or (
            updated.candidates[0].sku if updated.candidates else None
        )
        if feedback_sku and hasattr(service.engine, "record_feedback"):
            service.engine.record_feedback(updated.query, feedback_sku)
    # Publish event after successful feedback
    payload = FeedbackRecordedPayload(
        query=updated.query,
        sku=req.corrected_sku or (updated.candidates[0].sku if updated.candidates else ""),
        decision=req.action,
        reviewer=req.reviewer,
        timestamp=datetime.now(timezone.utc),
    ).model_dump(mode="json")
    publish_event("feedback.recorded", payload)
    return updated

# -------------------------------------------------
# Ensure other endpoints also publish when appropriate (search, review creation, drift updates, health changes)
# For brevity, only feedback is wired here – similar calls can be added where needed.

# ==========================================


@app.post(Route.SEARCH, response_model=SearchResponseV1)
def search_v1(req: SearchRequestV1, request: Request):
    """Search parts with typed, display-ready response models and reason codes."""
    req_id = getattr(request.state, "request_id", uuid.uuid4().hex)

    # Empty or whitespace-only queries return 400 validation_error per contract
    trimmed = req.query.strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="Query string cannot be empty or whitespace only")

    raw_result = service.search(req.query)
    results = raw_result.get("results", [])
    top_sku = results[0]["sku"] if results else None

    # Resilient audit logging
    try:
        storage.log_query(req.query, raw_result["route"], top_sku, raw_result["latency_ms"], MODEL_VERSION, results)
    except Exception:
        storage.record_log_failure()
        logging.exception("query log failed in /v1/search")
        print(f"query log failed: query={req.query[:80]!r}", file=sys.stderr)

    response = build_search_response_v1(
        query=req.query,
        raw_response=raw_result,
        request_id=req_id,
        model_version=MODEL_VERSION,
    )
    return response


@app.get("/v1/review-queue", response_model=Paginated[ReviewItem])
def review_queue_v1(
    cursor: Optional[str] = Query(None, description="Opaque base64 pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
):
    """Paginated review queue with cursor keyed on (priority, created_at, id)."""
    items, next_cursor, total = storage.get_review_queue_v1(cursor=cursor, limit=limit)
    return Paginated[ReviewItem](
        items=items,
        next_cursor=next_cursor,
        total_estimate=total,
    )


@app.get("/v1/review-queue/{id}", response_model=ReviewItemDetail)
def review_item_detail_v1(id: str):
    """Fetch a single review item with complete audit trail history."""
    item = storage.get_review_item_detail_v1(id)
    if not item:
        raise HTTPException(status_code=404, detail=f"Review item {id} not found")
    return item


@app.get("/v1/monitoring/summary", response_model=MonitoringSummaryResponse)
def monitoring_summary_v1(
    request: Request,
    window: str = Query("1h", description="Time window aggregation: 15m, 1h, or 24h"),
):
    """Precomputed monitoring summary containing drift, escalation, latency, and OOD metrics."""
    if window not in WINDOW_OPTIONS:
        raise HTTPException(status_code=400, detail=f"Invalid window '{window}'. Allowed: {', '.join(WINDOW_OPTIONS)}")
    req_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    data = storage.get_monitoring_summary_v1(window=window, request_id=req_id)
    return MonitoringSummaryResponse(**data)


@app.get("/v1/catalog/facets", response_model=CatalogFacetsResponse)
def catalog_facets_v1():
    """Cached catalog facet distributions for categories, brands, and materials."""
    data = storage.get_catalog_facets("data/catalog.json")
    return CatalogFacetsResponse(**data)


@app.get("/v1/config/public", response_model=PublicConfigResponse)
def public_config_v1():
    """Public thresholds and configuration parameters required by frontend."""
    from app.config import (
        CONFIDENCE_THRESHOLDS,
        DRIFT_THRESHOLD,
        PAGE_SIZE_DEFAULTS,
        TOO_CLOSE,
        WINDOW_OPTIONS,
    )
    return PublicConfigResponse(
        confidence_thresholds=CONFIDENCE_THRESHOLDS,
        too_close_margin=TOO_CLOSE,
        drift_threshold=DRIFT_THRESHOLD,
        window_options=WINDOW_OPTIONS,
        page_size_defaults=PageSizeDefaults(**PAGE_SIZE_DEFAULTS),
    )


@app.get("/v1/health", response_model=HealthResponseV1)
def health_v1(request: Request):
    """Detailed health check including dependency status."""
    req_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    has_catalog = service.catalog is not None and len(service.catalog) > 0
    has_engine = service.engine is not None

    index_status = "ok" if has_catalog else "down"
    model_status = "ok" if has_engine else "down"
    overall = "ok" if (index_status == "ok" and model_status == "ok") else "degraded"

    return HealthResponseV1(
        schema_version="1.0",
        request_id=req_id,
        model_version=MODEL_VERSION,
        status=overall,
        dependencies=DependencyStatus(index=index_status, model=model_status),
    )
