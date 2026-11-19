
import csv
import json
from pathlib import Path

import numpy as np
from sklearn.isotonic import IsotonicRegression

from src.improved_retrieval import HybridPartsRetriever


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.csv"
VALIDATION = ROOT / "data" / "splits" / "validation.csv"
OUTPUT = ROOT / "results" / "confidence_calibration.json"


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def main() -> None:
    retriever = HybridPartsRetriever(rows(CATALOG))
    validation = rows(VALIDATION)
    raw_scores: list[float] = []
    labels: list[int] = []
    for row in validation:
        result = retriever.search(row["query"], limit=1)[0]
        raw_scores.append(result["confidence"])
        labels.append(int(result["sku"] == row["target_sku"]))

    calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds="clip")
    calibrator.fit(raw_scores, labels)
    retriever.calibrator = calibrator
    calibrated = np.asarray(calibrator.predict(raw_scores))
    report = {
        "method": "isotonic_regression",
        "validation_queries": len(validation),
        "raw_brier": round(float(np.mean((np.asarray(raw_scores) - labels) ** 2)), 6),
        "calibrated_brier": round(float(np.mean((calibrated - labels) ** 2)), 6),
        "raw_confidence_range": [round(min(raw_scores), 6), round(max(raw_scores), 6)],
        "calibrated_confidence_range": [
            round(float(calibrated.min()), 6),
            round(float(calibrated.max()), 6),
        ],
    }
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
