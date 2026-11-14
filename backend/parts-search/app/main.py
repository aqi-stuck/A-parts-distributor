import logging
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
    """Search parts and log the query."""
    result = service.search(req.query)
    results = result.get("results", [])
    top_sku = results[0]["sku"] if results else None
    try:
        storage.log_query(req.query, result["route"], top_sku, result["latency_ms"], MODEL_VERSION, results)
    except Exception:
        # A logging/DB failure must never hide a valid search result.
        logging.exception("query log failed")
    return result


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    """Save human feedback for a query."""
    storage.save_feedback(req.query, req.sku, req.decision, req.reviewer, req.query_id)
    return {"saved": True}


@app.get("/review-queue")
def review_queue():
    """Get recent queries needing human review."""
    return storage.review_queue()


@app.get("/metrics")
def metrics():
    """Get basic usage metrics."""
    return storage.metrics()
