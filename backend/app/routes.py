# Route path constants and enumeration for the Parts Search API.
# All route strings are defined here to avoid hard‑coded values throughout the codebase.

from enum import Enum

# API version prefix
API_V1_PREFIX = "/v1"

# v1 endpoints
SEARCH = f"{API_V1_PREFIX}/search"
FEEDBACK = f"{API_V1_PREFIX}/feedback"
REVIEW_QUEUE = f"{API_V1_PREFIX}/review-queue"
REVIEW_QUEUE_ITEM = f"{API_V1_PREFIX}/review-queue/{{id}}"
MONITORING_SUMMARY = f"{API_V1_PREFIX}/monitoring/summary"
CATALOG_FACETS = f"{API_V1_PREFIX}/catalog/facets"
PUBLIC_CONFIG = f"{API_V1_PREFIX}/config/public"
HEALTH_V1 = f"{API_V1_PREFIX}/health"
EVENTS = f"{API_V1_PREFIX}/events"
DISCOVERY = f"{API_V1_PREFIX}"

# Legacy (v0) endpoints – kept for backward compatibility
HEALTH = "/health"

class Route(str, Enum):
    """Enum exposing routes as strings for type‑safe usage.
    The values reference the constants defined above so that any change
    propagates automatically.
    """
    HEALTH = HEALTH
    SEARCH = SEARCH
    FEEDBACK = FEEDBACK
    REVIEW_QUEUE = REVIEW_QUEUE
    REVIEW_QUEUE_ITEM = REVIEW_QUEUE_ITEM
    MONITORING_SUMMARY = MONITORING_SUMMARY
    CATALOG_FACETS = CATALOG_FACETS
    PUBLIC_CONFIG = PUBLIC_CONFIG
    HEALTH_V1 = HEALTH_V1
    EVENTS = EVENTS
    DISCOVERY = DISCOVERY

# Endpoint metadata used by the discovery document.
# Each entry is a dict with name, method, path, and response_model.
ENDPOINTS = [
    {
        "name": "search",
        "method": "POST",
        "path": SEARCH,
        "response_model": "SearchResponse",
    },
    {
        "name": "review_queue_list",
        "method": "GET",
        "path": REVIEW_QUEUE,
        "response_model": "Paginated[ReviewItem]",
    },
    {
        "name": "review_queue_detail",
        "method": "GET",
        "path": REVIEW_QUEUE_ITEM,
        "response_model": "ReviewItemDetail",
    },
    {
        "name": "feedback",
        "method": "POST",
        "path": FEEDBACK,
        "response_model": "FeedbackResponse",
    },
    {
        "name": "monitoring_summary",
        "method": "GET",
        "path": MONITORING_SUMMARY,
        "response_model": "MonitoringSummaryResponse",
    },
    {
        "name": "catalog_facets",
        "method": "GET",
        "path": CATALOG_FACETS,
        "response_model": "CatalogFacetsResponse",
    },
    {
        "name": "public_config",
        "method": "GET",
        "path": PUBLIC_CONFIG,
        "response_model": "PublicConfigResponse",
    },
    {
        "name": "health",
        "method": "GET",
        "path": HEALTH_V1,
        "response_model": "HealthResponseV1",
    },
    {
        "name": "events_stream",
        "method": "GET",
        "path": EVENTS,
        "response_model": "ServerSentEvents",
    },
]