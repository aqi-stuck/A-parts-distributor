#!/usr/bin/env python3
"""Convenience script to export OpenAPI schema from repository root."""

import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
backend_dir = repo_root / "backend" / "parts-search"

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from scripts.export_openapi import export_openapi

if __name__ == "__main__":
    export_openapi(repo_root / "docs" / "openapi.json")
