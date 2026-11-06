import logging
import time
from ml.engine import Engine
from app.routing import decide_route


class SearchService:
    """Provides search with engine and routing, measuring latency."""

    def __init__(self, catalog_path: str):
        self.engine = Engine(catalog_path)

    def search(self, query: str) -> dict:
        """Run search, decide route, and return results with latency."""
        start = time.perf_counter()
        try:
            results = self.engine.search(query)[:5]
            route, reason = decide_route(results)
        except Exception:
            logging.exception("search failed")
            results = []
            route = "review"
            reason = "system error"
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        return {
            "route": route,
            "reason": reason,
            "results": results,
            "latency_ms": latency_ms
        }
