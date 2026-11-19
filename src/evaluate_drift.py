
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.drift_detection import DriftDetector
from src.improved_retrieval import HybridPartsRetriever


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.csv"
REFERENCE = ROOT / "data" / "splits" / "validation.csv"
SHIFTS = ROOT / "data" / "shifted_queries.csv"
OUTPUT = ROOT / "results" / "drift_v1.json"


def load(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def classification_metrics(rows: list[dict[str, Any]]) -> dict[str, float]:
    tp = sum(row["predicted"] and row["actual"] for row in rows)
    fp = sum(row["predicted"] and not row["actual"] for row in rows)
    fn = sum(not row["predicted"] and row["actual"] for row in rows)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
    }


def main() -> None:
    reference = load(REFERENCE)
    shifts = load(SHIFTS)
    detector = DriftDetector(
        HybridPartsRetriever.from_csv(CATALOG),
        [row["query"] for row in reference],
    )
    evaluated = [
        {
            "predicted": detector.score_query(row["query"])["is_ood"],
            "actual": False,
        }
        for row in reference
    ] + [
        {
            "predicted": detector.score_query(row["query"])["is_ood"],
            "actual": row["is_shifted"] == "true",
        }
        for row in shifts
    ]
    by_shift: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in evaluated[: len(reference)]:
        by_shift["in_distribution"].append(result)
    for row, result in zip(shifts, evaluated[len(reference) :]):
        by_shift[row["shift_type"]].append(result)
    report = {
        "reference_queries": len(reference),
        "shifted_queries": len(shifts),
        "threshold": round(detector.threshold, 6),
        "overall": classification_metrics(evaluated),
        "by_shift_type": {
            shift: classification_metrics(rows) for shift, rows in by_shift.items()
        },
        "window_drift": detector.window_drift([row["query"] for row in shifts]),
        "features": [
            "embedding_distance",
            "unseen_token_rate",
            "query_length",
            "unknown_category",
        ],
    }
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
