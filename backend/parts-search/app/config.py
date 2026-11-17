import json
import os
from pathlib import Path

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "thresholds.json"


def _load_config():
    if not _CONFIG_PATH.is_file():
        raise FileNotFoundError(f"Threshold config not found at {_CONFIG_PATH}")
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Threshold config is not valid JSON: {e}") from e

    required_keys = ["version", "low_confidence", "too_close_margin", "model_version", "engine"]
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise KeyError(f"Threshold config missing keys: {', '.join(missing)}")

    return data


_config = _load_config()

VERSION = _config["version"]
LOW_CONFIDENCE = float(_config["low_confidence"])
TOO_CLOSE = float(_config["too_close_margin"])
MODEL_VERSION = _config["model_version"]
ENGINE = _config.get("engine", "baseline")
ENGINE_TIMEOUT_MS = int(_config.get("engine_timeout_ms", 2000))
DRIFT_THRESHOLD = float(_config.get("drift_threshold", 0.2))

CONFIDENCE_THRESHOLDS = _config.get(
    "confidence_thresholds",
    {"high": 0.9, "medium": 0.7, "low": 0.0},
)

CONFIDENCE_LABELS = _config.get(
    "confidence_labels",
    {
        "high": "High confidence",
        "medium": "Medium confidence",
        "low": "Low confidence",
    },
)

REASONS = _config.get(
    "reasons",
    {
        "high_margin": "Clear top match with distinct confidence margin.",
        "low_margin": "Top candidates are too close in score; human verification needed.",
        "attribute_mismatch": "Extracted query attributes do not match candidate specifications.",
        "ood_query": "Query appears out-of-distribution or unusual.",
        "dependency_unavailable": "Search dependency is currently unavailable; falling back to catalog keyword search.",
        "empty_query": "Query was empty or whitespace only.",
        "not_found": "No matching parts found in catalog.",
    },
)

WINDOW_OPTIONS = _config.get("window_options", ["15m", "1h", "24h"])
PAGE_SIZE_DEFAULTS = _config.get("page_size_defaults", {"default_limit": 20, "max_limit": 100})
ALLOWED_ORIGINS = _config.get(
    "allowed_origins",
    [
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
    ],
)


def get_confidence_level_and_label(value: float) -> tuple[str, str]:
    """Map a confidence float (0-1) to an enum level and display label."""
    high_cutoff = float(CONFIDENCE_THRESHOLDS.get("high", 0.9))
    med_cutoff = float(CONFIDENCE_THRESHOLDS.get("medium", 0.7))
    if value >= high_cutoff:
        return "high", CONFIDENCE_LABELS.get("high", "High confidence")
    if value >= med_cutoff:
        return "medium", CONFIDENCE_LABELS.get("medium", "Medium confidence")
    return "low", CONFIDENCE_LABELS.get("low", "Low confidence")


def map_reason_code_and_text(route: str, raw_reason: str | None) -> tuple[str, str]:
    """Map existing internal routing reasons to standard reason code and text."""
    if route == "auto":
        code = "high_margin"
    elif not raw_reason or raw_reason == "no matches":
        code = "not_found"
    elif raw_reason in ("system error", "engine timeout"):
        code = "dependency_unavailable"
    elif raw_reason in ("low confidence", "top candidates too close"):
        code = "low_margin"
    elif "attribute" in raw_reason.lower():
        code = "attribute_mismatch"
    elif "ood" in raw_reason.lower() or "shift" in raw_reason.lower():
        code = "ood_query"
    elif "empty" in raw_reason.lower():
        code = "empty_query"
    else:
        code = "low_margin"

    text = REASONS.get(code, raw_reason or "Review required")
    return code, text
