
import csv
import json
from pathlib import Path

from src.improved_retrieval import HybridPartsRetriever


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.csv"
GOLD = ROOT / "data" / "gold_queries_tagged.csv"
OUTPUT = ROOT / "results" / "coverage_accuracy_v1.json"
THRESHOLDS = (0.0, 0.2, 0.4, 0.6, 0.8, 0.9)


def load(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def main() -> None:
    retriever = HybridPartsRetriever.from_csv(CATALOG)
    rows = load(GOLD)
    scored = [
        {
            "confidence": result["confidence"],
            "correct": result["sku"] == row["target_sku"],
        }
        for row in rows
        for result in [retriever.search(row["query"], limit=1)[0]]
    ]
    curve = []
    for threshold in THRESHOLDS:
        accepted = [item for item in scored if item["confidence"] >= threshold]
        curve.append(
            {
                "threshold": threshold,
                "auto_answered": len(accepted),
                "reviewed": len(scored) - len(accepted),
                "coverage": round(len(accepted) / len(scored), 4),
                "accuracy": round(
                    sum(item["correct"] for item in accepted) / len(accepted), 4
                )
                if accepted
                else 0.0,
            }
        )
    report = {
        "benchmark": "gold_queries_tagged.csv",
        "queries": len(scored),
        "policy": "auto-answer when confidence >= threshold; otherwise review",
        "curve": curve,
    }
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
