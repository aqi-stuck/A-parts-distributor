"""Drift detection state tracking for the /metrics endpoint."""

import threading
from collections import deque, Counter
from datetime import datetime, timezone
from typing import Any

import numpy as np
from scipy.stats import ks_2samp


_WINDOW_SIZE = 100
_drift_lock = threading.RLock()
_current_window: deque = deque(maxlen=_WINDOW_SIZE)
_ood_scores: deque = deque(maxlen=_WINDOW_SIZE)
_ood_flagged: int = 0
_window_end: datetime | None = None
_psi_score: float | None = None
_ks_score: float | None = None
_alert_active: bool = False


class DriftTracker:
    """Window-based drift detection using KS statistic and PSI."""

    def __init__(self, reference_features: list[dict[str, Any]], threshold: float = 0.2):
        self.reference_features = reference_features
        self.threshold = threshold
        self._lock = threading.RLock()
        self._window: deque = deque(maxlen=_WINDOW_SIZE)
        self._ood_scores: deque = deque(maxlen=_WINDOW_SIZE)
        self._ood_flagged = 0
        self._window_end_dt: datetime | None = None
        self._psi: float | None = None
        self._ks: float = 0.0
        self._alert: bool = False

    def reset_window(self) -> None:
        with self._lock:
            self._window.clear()
            self._ood_scores.clear()
            self._ood_flagged = 0

    def add_query(self, ood_score: float, is_ood: bool, features: dict[str, Any]) -> bool:
        """Add a query to the window. Returns True if window should close."""
        with self._lock:
            self._window.append(features)
            self._ood_scores.append(ood_score)
            if is_ood:
                self._ood_flagged += 1
            if len(self._window) >= _WINDOW_SIZE:
                return True
            return False

    def close_window(self) -> dict[str, Any]:
        """Compute drift metrics for the completed window."""
        with self._lock:
            if not self._window:
                result = {
                    "window_size": 0,
                    "psi_score": None,
                    "ks_score": 0.0,
                    "alert_active": False,
                    "window_end": None,
                    "ood_scores": [],
                    "ood_flagged": 0,
                }
            else:
                current = [self._extract_features(f) for f in self._window]
                psi = self._compute_psi(self.reference_features, current)
                ks = self._compute_ks(self.reference_features, current)

                self._psi = psi
                self._ks = max(ks.values()) if ks else 0.0
                self._alert = self._threshold_exceeded(psi, ks)
                self._window_end_dt = datetime.now(timezone.utc)

                result = {
                    "window_size": len(self._window),
                    "psi_score": psi,
                    "ks_score": self._ks,
                    "alert_active": self._alert,
                    "window_end": self._window_end_dt,
                    "ood_scores": list(self._ood_scores),
                    "ood_flagged": self._ood_flagged,
                }

            self._window.clear()
            self._ood_scores.clear()
            self._ood_flagged = 0
            return result

    @staticmethod
    def _extract_features(f: dict[str, Any]) -> dict[str, Any]:
        return {
            "embedding_distance": f.get("embedding_distance", 0.0),
            "unseen_token_rate": f.get("unseen_token_rate", 0.0),
            "query_length": f.get("query_length", 0),
            "category": f.get("category", "unknown"),
        }

    def _compute_ks(self, ref: list[dict], curr: list[dict]) -> dict[str, float]:
        fields = ("embedding_distance", "unseen_token_rate", "query_length")
        return {
            field: float(ks_2samp(
                [item[field] for item in ref],
                [item[field] for item in curr],
            ).statistic)
            for field in fields
        }

    def _compute_psi(self, ref: list[dict], curr: list[dict]) -> float:
        ref_cats = Counter(item.get("category", "unknown") for item in ref)
        curr_cats = Counter(item.get("category", "unknown") for item in curr)
        all_cats = set(ref_cats) | set(curr_cats)
        ref_n = len(ref)
        curr_n = len(curr)
        psi = 0.0
        for cat in all_cats:
            ref_prop = max(ref_cats.get(cat, 0) / ref_n, 1e-6)
            curr_prop = max(curr_cats.get(cat, 0) / curr_n, 1e-6)
            psi += (curr_prop - ref_prop) * np.log(curr_prop / ref_prop)
        return float(psi)

    def _threshold_exceeded(self, psi: float, ks: dict[str, float]) -> bool:
        return psi > self.threshold + 1e-12 or max(ks.values()) > self.threshold + 1e-12


def reset_drift_state() -> None:
    """Reset drift state (test helper)."""
    global _current_window, _ood_scores, _ood_flagged, _window_end, _psi_score, _ks_score, _alert_active
    with _drift_lock:
        _current_window.clear()
        _ood_scores.clear()
        _ood_flagged = 0
        _window_end = None
        _psi_score = None
        _ks_score = None
        _alert_active = False
    try:
        from app import search
        if search._DRIFT_TRACKER is not None:
            search._DRIFT_TRACKER.reset_window()
    except Exception:
        pass


def get_drift_threshold() -> float:
    try:
        from app.config import DRIFT_THRESHOLD
        return DRIFT_THRESHOLD
    except Exception:
        return 0.2


def add_query_to_window(ood_score: float, is_ood: bool, features: dict[str, Any]) -> bool:
    """Add a query to the drift window. Returns True if window should close."""
    global _ood_flagged
    with _drift_lock:
        _current_window.append(features)
        _ood_scores.append(ood_score)
        if is_ood:
            _ood_flagged += 1
        if len(_current_window) >= _WINDOW_SIZE:
            return True
        return False


def compute_window_drift(reference_features: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute PSI and KS statistics for the current window."""
    with _drift_lock:
        if len(_current_window) == 0:
            return {
                "psi_score": None,
                "ks_score": None,
                "alert_active": False,
                "window_size": 0,
                "window_end": None,
                "ood_scores": [],
                "ood_flagged": 0,
            }

        threshold = get_drift_threshold()
        current = list(_current_window)
        psi = _compute_psi(reference_features, current)
        ks = _compute_ks(reference_features, current)
        max_ks = max(ks.values()) if ks else 0.0
        alert = psi > threshold + 1e-12 or max_ks > threshold + 1e-12
        _window_end = datetime.now(timezone.utc)
        _psi_score = psi
        _ks_score = max_ks
        _alert_active = alert
        window_size = len(_current_window)
        scores = list(_ood_scores)
        flagged = _ood_flagged
        _current_window.clear()
        _ood_scores.clear()
        _ood_flagged = 0
        return {
            "psi_score": psi,
            "ks_score": max_ks,
            "alert_active": alert,
            "window_size": window_size,
            "window_end": _window_end,
            "ood_scores": scores,
            "ood_flagged": flagged,
        }


def _compute_psi(ref: list[dict], curr: list[dict]) -> float:
    ref_cats = Counter(item.get("category", "unknown") for item in ref)
    curr_cats = Counter(item.get("category", "unknown") for item in curr)
    all_cats = set(ref_cats) | set(curr_cats)
    ref_n = len(ref)
    curr_n = len(curr)
    psi = 0.0
    for cat in all_cats:
        ref_prop = max(ref_cats.get(cat, 0) / ref_n, 1e-6)
        curr_prop = max(curr_cats.get(cat, 0) / curr_n, 1e-6)
        psi += (curr_prop - ref_prop) * np.log(curr_prop / ref_prop)
    return float(psi)


def _compute_ks(ref: list[dict], curr: list[dict]) -> dict[str, float]:
    fields = ("embedding_distance", "unseen_token_rate", "query_length")
    return {
        field: float(ks_2samp(
            [item[field] for item in ref],
            [item[field] for item in curr],
        ).statistic)
        for field in fields
    }


def update_metrics_from_drift(
    window_size: int,
    psi_score: float | None,
    ks_score: float,
    alert_active: bool,
    window_end: datetime | None,
    ood_scores: list[float],
    ood_flagged: int,
) -> None:
    """Update the global drift metrics state."""
    global _window_end, _psi_score, _ks_score, _alert_active
    with _drift_lock:
        _window_end = window_end
        _psi_score = psi_score
        _ks_score = ks_score
        _alert_active = alert_active


def get_metrics_state() -> dict[str, Any]:
    """Get the current drift metrics state for the /metrics endpoint."""
    with _drift_lock:
        if _window_end is None:
            return {
                "drift_window_score": None,
                "drift_alert_active": 0,
                "drift_window_size": 0,
                "drift_last_window_end": None,
                "drift_status": "warming_up",
                "ood_score_mean": None,
                "ood_score_p95": None,
                "ood_flag_rate": None,
            }

        scores_arr = np.asarray(_ood_scores) if _ood_scores else np.array([])
        mean_score = float(np.mean(scores_arr)) if len(scores_arr) > 0 else None
        p95_score = float(np.percentile(scores_arr, 95)) if len(scores_arr) > 0 else None
        total_ood = len(_ood_scores)
        flag_rate = float(_ood_flagged / total_ood) if total_ood > 0 else None

        return {
            "drift_window_score": _psi_score,
            "drift_alert_active": 1 if _alert_active else 0,
            "drift_window_size": _WINDOW_SIZE if _window_end else 0,
            "drift_last_window_end": _window_end.isoformat() if _window_end else None,
            "drift_status": "ok",
            "ood_score_mean": round(mean_score, 6) if mean_score is not None else None,
            "ood_score_p95": round(p95_score, 6) if p95_score is not None else None,
            "ood_flag_rate": round(flag_rate, 6) if flag_rate is not None else None,
        }