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

    required_keys = ["version", "low_confidence", "too_close_margin", "model_version"]
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise KeyError(f"Threshold config missing keys: {', '.join(missing)}")

    return data

_config = _load_config()

VERSION = _config["version"]
LOW_CONFIDENCE = float(_config["low_confidence"])
TOO_CLOSE = float(_config["too_close_margin"])
MODEL_VERSION = _config["model_version"]
