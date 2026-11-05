"""Create deterministic train, validation, and test splits without leakage."""

import csv
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parent
QUERIES = ROOT / "messy_queries.csv"
GOLD = ROOT / "gold_queries.csv"
SPLIT_DIR = ROOT / "splits"
SEED = 20261105


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def write_rows(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    all_queries = load_rows(QUERIES)
    gold_ids = {row["query_id"] for row in load_rows(GOLD)}
    candidates = [row for row in all_queries if row["query_id"] not in gold_ids]
    random.Random(SEED).shuffle(candidates)

    train_end = round(len(candidates) * 0.70)
    validation_end = train_end + round(len(candidates) * 0.15)
    splits = {
        "train": candidates[:train_end],
        "validation": candidates[train_end:validation_end],
        "test": candidates[validation_end:],
    }

    SPLIT_DIR.mkdir(exist_ok=True)
    for name, rows in splits.items():
        write_rows(SPLIT_DIR / f"{name}.csv", rows)
    print("Created " + ", ".join(f"{name}={len(rows)}" for name, rows in splits.items()))


if __name__ == "__main__":
    main()
