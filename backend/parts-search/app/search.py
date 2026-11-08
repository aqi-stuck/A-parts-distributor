import json
import logging
import time
from app.config import ENGINE
from app.routing import decide_route
from app.fallback import keyword_fallback

if ENGINE == "model":
    from ml.model_engine import Engine
else:
    from ml.baseline_engine import Engine


class SearchService:
    """Provides search with engine and routing, measuring latency."""

    def __init__(self, catalog_path: str):
        self.engine = Engine(catalog_path)
        with open(catalog_path, 'r', encoding='utf-8') as f:
            self.catalog = json.load(f)

    def search(self, query: str) -> dict:
        """Run search, decide route, and return results with latency."""
        start = time.perf_counter()
        engine_ms = 0.0
        routing_ms = 0.0
        try:
            engine_start = time.perf_counter()
            results_raw = self.engine.search(query)
            engine_end = time.perf_counter()
            engine_ms = round((engine_end - engine_start) * 1000, 2)
            results = results_raw[:5]
            routing_start = time.perf_counter()
            route, reason = decide_route(results)
            routing_end = time.perf_counter()
            routing_ms = round((routing_end - routing_start) * 1000, 2)
        except Exception:
            logging.exception("search failed")
            try:
                results = keyword_fallback(self.catalog, query, limit=5)
            except Exception:
                results = []
            route = "review"
            reason = "system error"
            engine_ms = 0.0
            routing_ms = 0.0
        total_ms = round((time.perf_counter() - start) * 1000, 2)
        latency_ms = total_ms
        return {
            "route": route,
            "reason": reason,
            "results": results,
            "latency_ms": latency_ms,
            "timing_ms": {"engine": engine_ms, "routing": routing_ms, "total": total_ms}
        }
