
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from src.improved_retrieval import HybridPartsRetriever


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "catalog.csv"
GOLD = ROOT / "data" / "gold_queries_tagged.csv"
OUTPUT = ROOT / "results" / "g5_g11_v1.json"
AUTO_THRESHOLD = 0.9
NOISE_WORDS = ("please", "urgent", "warehouse", "replacement", "item")


def load(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def accuracy(rows: list[dict[str, Any]]) -> float:
    return round(
        sum(row["correct"] for row in rows) / len(rows), 4
    ) if rows else 0.0


def grouped(rows: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row[field]].append(row)
    return {
        key: {"queries": len(items), "top_1_accuracy": accuracy(items)}
        for key, items in sorted(groups.items())
    }


def score_queries(
    retriever: HybridPartsRetriever, rows: list[dict[str, str]], queries: list[str] | None = None
) -> list[dict[str, Any]]:
    values = queries or [row["query"] for row in rows]
    return [
        {
            **row,
            "confidence": result["confidence"],
            "correct": result["sku"] == row["target_sku"],
        }
        for row, query in zip(rows, values)
        for result in [retriever.search(query, limit=1)[0]]
    ]


def add_catalog_slices(rows: list[dict[str, Any]], catalog: list[dict[str, str]]) -> None:
    by_sku = {row["sku"]: row for row in catalog}
    category_counts = Counter(row["category"] for row in catalog)
    median_count = sorted(category_counts.values())[len(category_counts) // 2]
    for row in rows:
        catalog_row = by_sku[row["target_sku"]]
        row["brand_tier_proxy"] = (
            "large_proxy"
            if catalog_row["brand"] in {"ForgePro", "Northstar"}
            else "small_proxy"
        )
        row["category_frequency"] = (
            "common" if category_counts[catalog_row["category"]] >= median_count else "rare"
        )
        row["category"] = catalog_row["category"]
        row["query_style"] = {
            "abbreviation": "abbreviation_heavy",
            "typo": "typo_heavy",
            "missing_attribute": "terse",
            "noise": "verbose",
        }.get(row["transformation"], row["transformation"])


def calibration(rows: list[dict[str, Any]], bins: int = 10) -> dict[str, Any]:
    buckets = []
    for index in range(bins):
        lower = index / bins
        upper = (index + 1) / bins
        members = [
            row for row in rows
            if lower <= row["confidence"] < upper
            or index == bins - 1 and row["confidence"] == upper
        ]
        if members:
            mean_confidence = sum(row["confidence"] for row in members) / len(members)
            mean_accuracy = sum(row["correct"] for row in members) / len(members)
            buckets.append(
                {
                    "lower": lower,
                    "upper": upper,
                    "queries": len(members),
                    "mean_confidence": round(mean_confidence, 4),
                    "accuracy": round(mean_accuracy, 4),
                }
            )
    ece = sum(
        bucket["queries"] / len(rows)
        * abs(bucket["mean_confidence"] - bucket["accuracy"])
        for bucket in buckets
    )
    return {
        "reliability_diagram": buckets,
        "bins": buckets,
        "expected_calibration_error": round(ece, 4),
    }


def escalation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    auto = [row for row in rows if row["confidence"] >= AUTO_THRESHOLD]
    review = [row for row in rows if row["confidence"] < AUTO_THRESHOLD]
    by_group = {}
    for group, members in sorted(
        ((key, list(items)) for key, items in grouped_rows(rows, "primary_tag").items()),
    ):
        auto_members = [row for row in members if row["confidence"] >= AUTO_THRESHOLD]
        by_group[group] = {
            "queries": len(members),
            "escalation_rate": round(1 - len(auto_members) / len(members), 4),
            "error_rate": round(1 - accuracy(members), 4),
            "auto_error_rate": round(1 - accuracy(auto_members), 4) if auto_members else 0.0,
        }
    return {
        "threshold": AUTO_THRESHOLD,
        "auto_answered": len(auto),
        "reviewed": len(review),
        "coverage": round(len(auto) / len(rows), 4),
        "auto_error_rate": round(1 - accuracy(auto), 4) if auto else 0.0,
        "review_error_rate": round(1 - accuracy(review), 4) if review else 0.0,
        "by_primary_tag": by_group,
    }


def grouped_rows(
    rows: list[dict[str, Any]], field: str
) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[row[field]].append(row)
    return groups


def robustness(retriever: HybridPartsRetriever, rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    curve = []
    for level in range(len(NOISE_WORDS) + 1):
        queries = [
            f"{row['query']} {' '.join(NOISE_WORDS[:level])}".strip()
            for row in rows
        ]
        scored = score_queries(retriever, rows, queries)
        curve.append({"noise_words": level, "accuracy": accuracy(scored)})
    return curve


def main() -> None:
    catalog = load(CATALOG)
    gold = load(GOLD)
    retriever = HybridPartsRetriever.from_csv(CATALOG)
    scored = score_queries(retriever, gold)
    add_catalog_slices(scored, catalog)
    report = {
        "g5_bias": {
            "brand_tier_definition": "large_proxy=ForgePro/Northstar; small_proxy=other synthetic brands",
            "coverage_note": "The frozen gold set contains only large_proxy targets; small_proxy is not estimable from this benchmark.",
            "by_brand_tier_proxy": grouped(scored, "brand_tier_proxy"),
            "by_category_frequency": grouped(scored, "category_frequency"),
            "by_category": grouped(scored, "category"),
        },
        "g6_query_style": {
            "by_transformation": grouped(scored, "transformation"),
            "by_query_style": grouped(scored, "query_style"),
        },
        "g7_escalation_and_error": escalation(scored),
        "g10_calibration": calibration(scored),
        "g11_robustness": {"accuracy_by_noise_level": robustness(retriever, gold)},
    }
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
