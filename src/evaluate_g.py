"""Run G1-G4 evaluation checks for retrieval quality and grounding."""

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from src.baseline import PartsBaseline
from src.drift_detection import DriftDetector
from src.improved_retrieval import HybridPartsRetriever


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.csv"
GOLD = ROOT / "data" / "gold_queries_tagged.csv"
SHIFTED = ROOT / "data" / "shifted_queries.csv"
OUTPUT = ROOT / "results" / "g1_g4_v1.json"
NONEXISTENT = (
    "titanium rocket engine gasket z99 999 mm",
    "nonexistent quantum bearing q99 9999 mm",
    "left hand flux capacitor connector x404",
)


def load(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def metrics(rows: list[dict[str, str]], predictions: list[list[str]]) -> dict[str, Any]:
    pairs = zip(rows, predictions)
    top1 = sum(top1_match(row["target_sku"], result) for row, result in pairs)
    pairs = zip(rows, predictions)
    top5 = sum(row["target_sku"] in result for row, result in pairs)
    return {
        "queries": len(rows),
        "top_1_accuracy": round(top1 / len(rows), 4),
        "top_5_accuracy": round(top5 / len(rows), 4),
    }


def top1_match(target_sku: str, predictions: list[str]) -> int:
    return int(predictions[:1] == [target_sku])


def grouped_metrics(
    rows: list[dict[str, str]], predictions: list[list[str]], field: str
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        groups[row[field]].append(index)
    return {
        group: metrics(
            [rows[index] for index in indices],
            [predictions[index] for index in indices],
        )
        for group, indices in groups.items()
    }


def predictions(
    baseline: PartsBaseline,
    improved: HybridPartsRetriever,
    gold: list[dict[str, str]],
) -> tuple[list[list[str]], list[list[dict[str, Any]]]]:
    baseline_predictions = [
        [result["sku"] for result in baseline.search(row["query"])] for row in gold
    ]
    improved_results = [improved.search(row["query"]) for row in gold]
    improved_predictions = [
        [result["sku"] for result in results] for results in improved_results
    ]
    return baseline_predictions, improved_results


def grounded_explanations(
    catalog: list[dict[str, str]],
    improved: HybridPartsRetriever,
    results: list[list[dict[str, Any]]],
    gold: list[dict[str, str]],
) -> bool:
    catalog_by_sku = {row["sku"]: row for row in catalog}
    returned_skus_valid = returned_skus_are_grounded(results, catalog_by_sku)
    explanations = [
        improved.search(row["query"], limit=1, include_explanation=True)[0]
        for row in gold
    ]
    explanations_valid = explanations_are_grounded(explanations, catalog_by_sku)
    return returned_skus_valid and explanations_valid


def returned_skus_are_grounded(
    results: list[list[dict[str, Any]]], catalog_by_sku: dict[str, dict[str, str]]
) -> bool:
    return all(
        result["sku"] in catalog_by_sku for group in results for result in group
    )


def explanations_are_grounded(
    explanations: list[dict[str, Any]], catalog_by_sku: dict[str, dict[str, str]]
) -> bool:
    return all(
        explanation_contains_catalog_fields(result, catalog_by_sku)
        for result in explanations
    )


def explanation_contains_catalog_fields(
    result: dict[str, Any], catalog_by_sku: dict[str, dict[str, str]]
) -> bool:
    catalog_row = catalog_by_sku[result["sku"]]
    return all(
        value in result["explanation"]
        for value in (result["sku"], catalog_row["description"], catalog_row["brand"])
    )


def ood_detection_rate(improved: HybridPartsRetriever, shifted: list[dict[str, str]]) -> float:
    validation = load(ROOT / "data" / "splits" / "validation.csv")
    detector = DriftDetector(improved, [row["query"] for row in validation])
    detected = [detector.score_query(row["query"])["is_ood"] for row in shifted]
    return round(sum(detected) / len(detected), 4)


def build_report(
    catalog: list[dict[str, str]],
    gold: list[dict[str, str]],
    baseline_predictions: list[list[str]],
    improved_results: list[list[dict[str, Any]]],
    improved: HybridPartsRetriever,
    shifted: list[dict[str, str]],
) -> dict[str, Any]:
    improved_predictions = [
        [result["sku"] for result in results] for results in improved_results
    ]
    grounded = grounded_explanations(catalog, improved, improved_results, gold)
    not_found = [
        improved.search_or_not_found(query, min_confidence=0.9)
        for query in NONEXISTENT
    ]
    return {
        "g1_accuracy_per_slice": accuracy_report(gold, baseline_predictions, improved_predictions),
        "g2_hard_case_results": hard_case_report(gold, improved_predictions, improved, shifted),
        "g3_grounding": grounding_report(catalog, grounded),
        "g4_nonexistent_parts": not_found_report(not_found),
    }


def accuracy_report(
    gold: list[dict[str, str]],
    baseline_predictions: list[list[str]],
    improved_predictions: list[list[str]],
) -> dict[str, Any]:
    return {
        "baseline_by_transformation": grouped_metrics(gold, baseline_predictions, "transformation"),
        "improved_by_transformation": grouped_metrics(gold, improved_predictions, "transformation"),
        "baseline_by_primary_tag": grouped_metrics(gold, baseline_predictions, "primary_tag"),
        "improved_by_primary_tag": grouped_metrics(gold, improved_predictions, "primary_tag"),
    }


def hard_case_report(
    gold: list[dict[str, str]],
    predictions: list[list[str]],
    improved: HybridPartsRetriever,
    shifted: list[dict[str, str]],
) -> dict[str, Any]:
    return {
        "improved_by_primary_tag": grouped_metrics(gold, predictions, "primary_tag"),
        "ood_shift_detection_rate": ood_detection_rate(improved, shifted),
        "ood_queries": len(shifted),
    }


def grounding_report(catalog: list[dict[str, str]], grounded: bool) -> dict[str, Any]:
    return {
        "catalog_skus": len(catalog),
        "all_returned_skus_in_catalog": grounded,
        "hallucinated_sku_rate": float(not grounded),
        "catalog_grounded_explanations": grounded,
    }


def not_found_report(responses: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "queries": len(responses),
        "not_found_count": sum(item["status"] == "not_found" for item in responses),
        "all_returned_not_found": all(item["status"] == "not_found" for item in responses),
        "responses": responses,
    }


def main() -> None:
    catalog = load(CATALOG)
    gold = load(GOLD)
    shifted = load(SHIFTED)
    baseline = PartsBaseline(catalog)
    improved = HybridPartsRetriever(catalog)
    baseline_predictions, improved_results = predictions(baseline, improved, gold)
    report = build_report(
        catalog,
        gold,
        baseline_predictions,
        improved_results,
        improved,
        shifted,
    )
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
