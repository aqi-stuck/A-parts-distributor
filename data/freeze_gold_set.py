
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
GOLD_SET = ROOT / "gold_queries.csv"
MANIFEST = ROOT / "gold_queries.sha256"


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest() -> None:
    manifest = {
        "file": GOLD_SET.name,
        "sha256": checksum(GOLD_SET),
        "status": "frozen",
        "rule": "Do not tune retrieval behavior against this file.",
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Frozen {GOLD_SET.name}: {manifest['sha256']}")


def verify_manifest() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    actual = checksum(GOLD_SET)
    if actual != manifest["sha256"]:
        raise SystemExit(
            f"Gold set changed: expected {manifest['sha256']}, got {actual}"
        )
    print(f"Verified frozen gold set: {actual}")


if __name__ == "__main__":
    if not GOLD_SET.exists():
        raise SystemExit(f"Missing gold set: {GOLD_SET}")
    if MANIFEST.exists():
        verify_manifest()
    else:
        write_manifest()
