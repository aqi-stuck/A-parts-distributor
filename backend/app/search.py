import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Any

from app.config import ENGINE, ENGINE_TIMEOUT_MS, DRIFT_THRESHOLD
from app.routing import decide_route
from app.fallback import keyword_fallback
import app.storage as storage
import app.drift_state as drift_state

# The retrieval engine pulls in numpy/scipy/sklearn native extensions. On hosts
# where an application-control policy blocks those DLLs, importing them at module
# scope made the whole API fail to boot. Degrade to the F8 manual catalog search
# instead: the service still answers every request, just without the model.
ENGINE_IMPORT_ERROR: str | None = None
try:
    if ENGINE == "model":
        from ml.model_engine import Engine
    else:
        from ml.baseline_engine import Engine
except Exception as _engine_exc:  # noqa: BLE001 - any import failure must degrade
    Engine = None  # type: ignore[assignment]
    ENGINE_IMPORT_ERROR = f"{type(_engine_exc).__name__}: {_engine_exc}"
    logging.warning(
        "Search engine unavailable (%s); serving manual catalog fallback only",
        ENGINE_IMPORT_ERROR,
    )

_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="parts-engine")
_DRIFT_WINDOW_SIZE = 100


def _safe_fallback(catalog: list[dict], query: str) -> list[dict]:
    """Keyword fallback that never raises; empty list on failure."""
    try:
        return keyword_fallback(catalog, query)
    except Exception:
        logging.exception("keyword fallback failed")
        return []


_DRIFT_TRACKER: drift_state.DriftTracker | None = None
_REFERENCE_FEATURES: list[dict[str, Any]] = []
_RETRIEVER: "Any | None" = None
_DRIFT_INIT_ATTEMPTED = False


def _reference_catalog_paths():
    """Repository catalog.csv first, then the backend-bundled catalog.json (Docker)."""
    from pathlib import Path

    # __file__ = backend/app/search.py
    backend_dir = Path(__file__).resolve().parents[1]
    repo_root = backend_dir.parent
    return repo_root / "data" / "catalog.csv", backend_dir / "data" / "catalog.json"


def _get_retriever():
    """Load the reference retriever from the repository catalog with a Docker fallback."""
    global _RETRIEVER
    if _RETRIEVER is not None:
        return _RETRIEVER
    try:
        from ml.improved_retrieval import HybridPartsRetriever

        catalog_csv, catalog_json = _reference_catalog_paths()
        if catalog_csv.is_file():
            _RETRIEVER = HybridPartsRetriever.from_csv(str(catalog_csv))
        elif catalog_json.is_file():
            # Docker images ship only backend/data/catalog.json.
            with open(catalog_json, "r", encoding="utf-8") as f:
                _RETRIEVER = HybridPartsRetriever(json.load(f))
        else:
            logging.warning(
                "No reference catalog found (looked for %s and %s)",
                catalog_csv,
                catalog_json,
            )
    except Exception:
        logging.warning("Reference retriever initialization failed", exc_info=True)
        _RETRIEVER = None
    return _RETRIEVER


def reset_drift_tracker() -> None:
    """Drop the active tracker and retriever so drift state can be rebuilt."""
    global _DRIFT_TRACKER, _REFERENCE_FEATURES, _RETRIEVER, _DRIFT_INIT_ATTEMPTED
    _DRIFT_TRACKER = None
    _REFERENCE_FEATURES = []
    _RETRIEVER = None
    _DRIFT_INIT_ATTEMPTED = False


def _initialize_drift_tracker() -> None:
    global _DRIFT_TRACKER, _REFERENCE_FEATURES, _DRIFT_INIT_ATTEMPTED
    if _DRIFT_TRACKER is not None or _DRIFT_INIT_ATTEMPTED:
        return
    _DRIFT_INIT_ATTEMPTED = True
    try:
        from ml.improved_retrieval import normalize_query
        from ml.baseline_model import tokenize
        from sklearn.metrics.pairwise import cosine_similarity

        retriever = _get_retriever()
        if retriever is None:
            logging.warning("Drift tracker disabled: reference catalog unavailable")
            return

        known_tokens = set(retriever.vectorizer.vocabulary_)
        known_categories = {row.get("category", "unknown").lower() for row in retriever.catalog if row.get("category")}

        def extract_features(query: str) -> dict[str, Any]:
            normalized = normalize_query(query)
            tokens = tokenize(normalized)
            unseen_rate = (
                sum(token not in known_tokens for token in tokens) / len(tokens)
                if tokens else 1.0
            )
            query_vector = retriever.vectorizer.transform([normalized])
            query_embedding = retriever.embedding_model.transform(query_vector)
            similarities = cosine_similarity(
                query_embedding, retriever.document_matrix
            ).ravel()
            category = next(
                (value for value in known_categories if value in normalized),
                "unknown",
            )
            return {
                "embedding_distance": float(1.0 - similarities.max(initial=0.0)),
                "unseen_token_rate": float(unseen_rate),
                "query_length": len(tokens),
                "category": category,
                "unknown_category": float(category == "unknown"),
            }

        ref_queries = [
            "zinc steel bolt m6 20 mm",
            "m8 zinc hex bolt 25 mm",
            "steel washer m6",
            "brass screw m4 10 mm",
            "stainless bolt m10 30 mm",
        ]
        _REFERENCE_FEATURES = [extract_features(q) for q in ref_queries]
        _DRIFT_TRACKER = drift_state.DriftTracker(_REFERENCE_FEATURES, threshold=DRIFT_THRESHOLD)
    except Exception as e:
        logging.warning("Drift tracker initialization failed: %s", e)


def _extract_ood_score(query: str) -> tuple[float, bool, dict[str, Any]]:
    """Extract OOD score and features for a query using the same logic as DriftDetector."""
    try:
        from ml.improved_retrieval import normalize_query
        from ml.baseline_model import tokenize
        from sklearn.metrics.pairwise import cosine_similarity

        retriever = _get_retriever()
        if not retriever:
            return 0.0, False, {}

        normalized = normalize_query(query)
        tokens = tokenize(normalized)

        known_tokens = set(retriever.vectorizer.vocabulary_)
        known_categories = {row.get("category", "unknown").lower() for row in retriever.catalog if row.get("category")}

        unseen_rate = (
            sum(token not in known_tokens for token in tokens) / len(tokens)
            if tokens else 1.0
        )

        query_vector = retriever.vectorizer.transform([normalized])
        query_embedding = retriever.embedding_model.transform(query_vector)
        similarities = cosine_similarity(
            query_embedding, retriever.document_matrix
        ).ravel()

        category = next(
            (value for value in known_categories if value in normalized),
            "unknown",
        )

        feat = {
            "embedding_distance": float(1.0 - similarities.max(initial=0.0)),
            "unseen_token_rate": float(unseen_rate),
            "query_length": len(tokens),
            "category": category,
            "unknown_category": float(category == "unknown"),
        }

        length_signal = min(float(len(tokens)) / 20.0, 1.0)
        score = float(
            0.45 * feat["embedding_distance"]
            + 0.30 * feat["unseen_token_rate"]
            + 0.15 * length_signal
            + 0.10 * feat["unknown_category"]
        )

        threshold = 0.22
        is_ood = score > threshold

        return round(score, 6), is_ood, feat
    except Exception as e:
        logging.debug("OOD score extraction failed: %s", e)
        return 0.0, False, {}


class SearchService:
    """Provides search with engine and routing, measuring latency."""

    def __init__(self, catalog_path: str):
        self.engine = Engine(catalog_path) if Engine is not None else None
        with open(catalog_path, 'r', encoding='utf-8') as f:
            self.catalog = json.load(f)
        if self.engine is not None:
            _initialize_drift_tracker()

    def search(self, query: str) -> dict:
        """Run search, decide route, and return results with latency."""
        start = time.perf_counter()
        engine_ms = 0.0
        routing_ms = 0.0
        if self.engine is None:
            # Startup-time dependency failure: answer from the catalog directly.
            results = _safe_fallback(self.catalog, query)
            route = "review"
            reason = "system error"
        else:
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

        if _DRIFT_TRACKER is None:
            # Rebuild after a reset so completed windows keep reaching /metrics.
            _initialize_drift_tracker()

        if _DRIFT_TRACKER is not None:
            ood_score, is_ood, features = _extract_ood_score(query)
            if _DRIFT_TRACKER.add_query(ood_score, is_ood, features):
                state = _DRIFT_TRACKER.close_window()
                storage.update_drift_metrics(
                    window_size=state.get("window_size", 0),
                    psi_score=state.get("psi_score"),
                    ks_score=state.get("ks_score", 0.0),
                    alert_active=state.get("alert_active", False),
                    window_end=state.get("window_end"),
                    ood_scores=state.get("ood_scores", []),
                    ood_flagged=state.get("ood_flagged", 0),
                )

        return {
            "route": route,
            "reason": reason,
            "results": results,
            "latency_ms": latency_ms,
            "timing_ms": {"engine": engine_ms, "routing": routing_ms, "total": total_ms},
            "engine": ENGINE
        }