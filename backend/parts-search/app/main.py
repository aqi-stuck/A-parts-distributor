import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import SearchRequest, SearchResponse, FeedbackRequest
from app.search import SearchService
from app.config import MODEL_VERSION
import app.storage as storage

service = SearchService("data/catalog.json")


@asynccontextmanager
async def lifespan(app: FastAPI):
    storage.init_db()
    yield


app = FastAPI(title="Parts Search API", lifespan=lifespan)

# CORS for hackathon, allow all origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    """Search parts and log the query; a logging fault never fails the request."""
    result = service.search(req.query)
    results = result.get("results", [])
    top_sku = results[0]["sku"] if results else None
    try:
        storage.log_query(req.query, result["route"], top_sku, result["latency_ms"], MODEL_VERSION, results)
    except Exception:
        # A logging/DB failure must never hide a valid search result. Count it
        # for /metrics and write it to stderr as the fallback audit channel.
        storage.record_log_failure()
        logging.exception("query log failed")
        print(f"query log failed: query={req.query[:80]!r}", file=sys.stderr)
    return result


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    """Save human feedback for a query; an unavailable store is reported, not raised."""
    try:
        storage.save_feedback(req.query, req.sku, req.decision, req.reviewer, req.query_id)
    except Exception:
        storage.record_log_failure()
        logging.exception("feedback save failed")
        print(f"feedback save failed: query={req.query[:80]!r}", file=sys.stderr)
        return {"saved": False, "reason": "feedback_store_unavailable"}
    return {"saved": True}


@app.get("/review-queue")
def review_queue():
    """Get recent queries needing human review; empty list if the store is down."""
    try:
        return storage.review_queue()
    except Exception:
        logging.exception("review queue unavailable")
        print("review queue unavailable", file=sys.stderr)
        return []


@app.get("/metrics")
def metrics():
    """Get basic usage metrics; never raises when the audit store is down."""
    return storage.metrics()
