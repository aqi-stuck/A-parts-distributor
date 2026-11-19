
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.baseline import PartsBaseline


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.csv"
GOLD = ROOT / "data" / "gold_queries_tagged.csv"
OUTPUT = ROOT / "results" / "baseline_v1.json"


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def score_rows(baseline: PartsBaseline, rows: list[dict[str, str]]) -> dict[str, Any]:
    top1 = 0
    top5 = 0
    failures: list[dict[str, str]] = []
    for row in rows:
        results = baseline.search(row["query"], limit=5)
        ranked_skus = [result["sku"] for result in results]
        is_top1 = ranked_skus[0] == row["target_sku"]
        is_top5 = row["target_sku"] in ranked_skus
        top1 += is_top1
        top5 += is_top5
        if not is_top5:
            failures.append(
                {
                    "gold_id": row["gold_id"],
                    "query": row["query"],
                    "expected_sku": row["target_sku"],
                    "predicted_sku": ranked_skus[0],
                }
            )
    count = len(rows)
    return {
        "queries": count,
        "top_1_accuracy": round(top1 / count, 4) if count else 0,
        "top_5_accuracy": round(top5 / count, 4) if count else 0,
        "top_1_correct": top1,
        "top_5_correct": top5,
        "top_5_failures": failures,
    }


def main() -> None:
    rows = load_rows(GOLD)
    baseline = PartsBaseline.from_csv(CATALOG)
    slices: dict[str, list[dict[str, str]]] = defaultdict(list)
    slices["overall"] = rows
    for row in rows:
        slices[f"transformation:{row['transformation']}"].append(row)
        slices[f"primary_tag:{row['primary_tag']}"].append(row)

    metrics = {name: score_rows(baseline, group) for name, group in slices.items()}
    result = {
        "benchmark": "gold_queries_tagged.csv",
        "catalog": "catalog.csv",
        "model": "BM25 + TF-IDF + RapidFuzz",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "metrics": metrics,
    }
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    overall = metrics["overall"]
    print(
        f"top1={overall['top_1_accuracy']:.2%} "
        f"top5={overall['top_5_accuracy']:.2%} "
        f"queries={overall['queries']}"
    )
    print(f"Saved {OUTPUT}")


if __name__ == "__main__":
    main()
