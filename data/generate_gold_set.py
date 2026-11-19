
import csv
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
QUERIES = ROOT / "messy_queries.csv"
CATALOG = ROOT / "catalog.csv"
OUTPUT = ROOT / "gold_queries.csv"
GOLD_SIZE = 400


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def build_gold_set() -> list[dict[str, str]]:
    queries = load_rows(QUERIES)
    catalog_skus = {row["sku"] for row in load_rows(CATALOG)}
    by_transformation: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in queries:
        if row["target_sku"] not in catalog_skus:
            raise ValueError(f"Unknown target SKU: {row['target_sku']}")
        by_transformation[row["transformation"]].append(row)

    transformations = sorted(by_transformation)
    per_group, remainder = divmod(GOLD_SIZE, len(transformations))
    selected: list[dict[str, str]] = []
    for index, transformation in enumerate(transformations):
        amount = per_group + (index < remainder)
        selected.extend(by_transformation[transformation][:amount])

    selected.sort(key=lambda row: int(row["query_id"]))
    for gold_id, row in enumerate(selected, start=1):
        row["gold_id"] = f"G{gold_id:04d}"
    return selected


def main() -> None:
    rows = build_gold_set()
    fieldnames = ["gold_id", "query_id", "query", "target_sku", "transformation"]
    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} frozen gold queries to {OUTPUT}")


if __name__ == "__main__":
    main()
