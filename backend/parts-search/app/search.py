import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError

from app.config import ENGINE, ENGINE_TIMEOUT_MS
from app.routing import decide_route
from app.fallback import keyword_fallback

if ENGINE == "model":
    from ml.model_engine import Engine
else:
    from ml.baseline_engine import Engine

# One shared pool so a timed-out call never spawns unlimited threads.
_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="parts-engine")


def _safe_fallback(catalog: list[dict], query: str) -> list[dict]:
    """Keyword fallback that never raises; empty list on failure."""
    try:
        return keyword_fallback(catalog, query)
    except Exception:
        logging.exception("keyword fallback failed")
        return []


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
            future = _EXECUTOR.submit(self.engine.search, query)
            try:
                results_raw = future.result(timeout=ENGINE_TIMEOUT_MS / 1000.0)
            except FuturesTimeoutError:
                logging.warning("engine timed out after %s ms", ENGINE_TIMEOUT_MS)
                engine_ms = round((time.perf_counter() - engine_start) * 1000, 2)
                results = _safe_fallback(self.catalog, query)
                route = "review"
                reason = "engine timeout"
            else:
                engine_ms = round((time.perf_counter() - engine_start) * 1000, 2)
                results = results_raw[:5]
                routing_start = time.perf_counter()
                route, reason = decide_route(results)
                routing_end = time.perf_counter()
                routing_ms = round((routing_end - routing_start) * 1000, 2)
        except Exception:
            logging.exception("search failed")
            results = _safe_fallback(self.catalog, query)
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
            "timing_ms": {"engine": engine_ms, "routing": routing_ms, "total": total_ms},
            "engine": ENGINE
        }
