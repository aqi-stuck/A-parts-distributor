import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
DB_DIR = Path("/tmp/parts-search")
DB_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("PARTS_DB_PATH", str(DB_DIR / "app.db"))
sys.path.insert(0, str(BACKEND))

from app.main import app as backend_app


class ApiPrefixMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] in ("http", "websocket"):
            path = scope.get("path", "")
            root_path = scope.get("root_path", "")
            if path.startswith("/api/"):
                scope = dict(scope)
                scope["path"] = path[len("/api"):]
                scope["raw_path"] = scope["path"].encode("utf-8")
                scope["root_path"] = f"{root_path}/api".rstrip("/")
        await self.app(scope, receive, send)


app = ApiPrefixMiddleware(backend_app)
