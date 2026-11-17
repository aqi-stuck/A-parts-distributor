#!/usr/bin/env python3
"""Export the FastAPI OpenAPI JSON schema to docs/openapi.json."""

import json
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.main import app


def export_openapi(output_path: Path | None = None) -> Path:
    if output_path is None:
        # Resolve docs/openapi.json in repo root
        repo_root = backend_dir.parent.parent
        output_path = repo_root / "docs" / "openapi.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    schema = app.openapi()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
        f.write("\n")

    print(f"Exported OpenAPI schema to {output_path}")
    return output_path


if __name__ == "__main__":
    export_openapi()
