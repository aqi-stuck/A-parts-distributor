"""Configure test environment for drift detection tests."""

import sys
from pathlib import Path

# tests/conftest.py -> [0]=tests, [1]=backend, [2]=repo root
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))