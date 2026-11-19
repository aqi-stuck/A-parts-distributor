
import csv
import json
from pathlib import Path
from typing import Any

from src.baseline import PartsBaseline
from src.improved_retrieval import HybridPartsRetriever


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.csv"
GOLD = ROOT / "data" / "gold_queries_tagged.csv"
SUMMARY = ROOT / "results" / "summary.md"
ERRORS = ROOT / "results" / "error_analysis_v1.json"


def load(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def top1_accuracy(rows: list[dict[str, str]], predictions: list[str]) -> float:
    correct = sum(row["target_sku"] == prediction for row, prediction in zip(rows, predictions))
    return round(correct / len(rows), 4)


def failure_cause(row: dict[str, str]) -> str:
    return {
        "missing_attribute": "incomplete query leaves similar catalog records unresolved",
        "unit_or_fraction": "unit or thread-fraction normalization remains ambiguous",
        "typo": "typo correction still maps to a competing catalog description",
        "abbreviation": "abbreviation expansion leaves a close competing candidate",
        "word_order": "word-order variation changes lexical similarity",
        "noise": "irrelevant query text affects candidate ranking",
    }.get(row["transformation"], "retrieval/reranking error requiring inspection")


def evaluate() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    catalog = load(CATALOG)
    gold = load(GOLD)
    catalog_by_sku = {row["sku"]: row for row in catalog}
    baseline = PartsBaseline(catalog)
    improved = HybridPartsRetriever(catalog)
    baseline_predictions = [baseline.search(row["query"], limit=1)[0]["sku"] for row in gold]
    improved_results = [improved.search(row["query"], limit=1)[0] for row in gold]
    improved_predictions = [result["sku"] for result in improved_results]
    errors = []
    for row, baseline_sku, result in zip(gold, baseline_predictions, improved_results):
        if result["sku"] == row["target_sku"]:
            continue
        expected = catalog_by_sku[row["target_sku"]]
        predicted = catalog_by_sku[result["sku"]]
        errors.append(
            {
                "gold_id": row["gold_id"],
                "query": row["query"],
                "expected_sku": row["target_sku"],
                "predicted_sku": result["sku"],
                "baseline_sku": baseline_sku,
                "confidence": result["confidence"],
                "transformation": row["transformation"],
                "primary_tag": row["primary_tag"],
                "cause": failure_cause(row),
                "expected_description": expected["description"],
                "predicted_description": predicted["description"],
            }
        )
    errors.sort(key=lambda item: (-item["confidence"], item["gold_id"]))
    headline = {
        "queries": len(gold),
        "baseline_top_1_accuracy": top1_accuracy(gold, baseline_predictions),
        "improved_top_1_accuracy": top1_accuracy(gold, improved_predictions),
        "absolute_improvement": round(
            top1_accuracy(gold, improved_predictions)
            - top1_accuracy(gold, baseline_predictions),
            4,
        ),
        "baseline_correct": sum(row["target_sku"] == sku for row, sku in zip(gold, baseline_predictions)),
        "improved_correct": sum(row["target_sku"] == sku for row, sku in zip(gold, improved_predictions)),
    }
    return headline, errors[:20]


def write_outputs(headline: dict[str, Any], errors: list[dict[str, Any]]) -> None:
    ERRORS.write_text(
        json.dumps(
            {
                "headline_metrics": headline,
                "worst_failures_definition": "20 incorrect improved predictions with highest confidence",
                "failures": errors,
                "remaining_gaps": [
                    "Ambiguous or missing-attribute queries remain the dominant failure slice.",
                    "The frozen gold set does not support a small-brand comparison.",
                    "High-confidence wrong answers require further calibration or stricter review routing.",
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    SUMMARY.write_text(
        "# Retrieval evaluation summary\n\n"
        "Evaluated on the frozen `data/gold_queries_tagged.csv` benchmark (400 queries).\n\n"
        "## G12 headline result\n\n"
        "| System | Top-1 accuracy | Correct |\n"
        "| --- | ---: | ---: |\n"
        f"| Baseline (BM25 + TF-IDF + fuzzy) | {headline['baseline_top_1_accuracy']:.2%} | {headline['baseline_correct']} |\n"
        f"| Improved hybrid retriever | {headline['improved_top_1_accuracy']:.2%} | {headline['improved_correct']} |\n\n"
        f"The improved system gains **{headline['absolute_improvement']:.2%}** absolute Top-1 accuracy "
        "on the frozen benchmark. This is an evaluation-only comparison; the gold set was not used for tuning.\n\n"
        "## G13 error analysis\n\n"
        "The accompanying JSON lists the 20 incorrect improved predictions with the highest confidence. "
        "The most important unresolved pattern is incomplete or ambiguous input: the system can be confident "
        "when several catalog records share the visible attributes. These cases should remain reviewable rather "
        "than being treated as definitive answers.\n\n"
        "See `results/error_analysis_v1.json` for each query, expected and predicted SKU, confidence, and cause.\n",
        encoding="utf-8",
    )


def main() -> None:
    headline, errors = evaluate()
    SUMMARY.parent.mkdir(exist_ok=True)
    write_outputs(headline, errors)
    print(json.dumps({"headline": headline, "worst_failures": len(errors)}, indent=2))


if __name__ == "__main__":
    main()
