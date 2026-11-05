"""Assign evaluation slices to the frozen gold queries."""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "gold_queries.csv"
OUTPUT = ROOT / "gold_queries_tagged.csv"
RARE_CATEGORIES = {"bearing", "seal", "bracket", "connector"}


def tags_for(row: dict[str, str]) -> tuple[str, str]:
    transformation = row["transformation"]
    tags = ["in_distribution"]
    words = set(row["query"].split())

    if transformation in {"typo", "abbreviation"}:
        tags.append("adversarial")
    if transformation == "missing_attribute":
        tags.append("ambiguous")
    if words.intersection(RARE_CATEGORIES):
        tags.append("rare")
    if transformation in {"unit_or_fraction", "noise"}:
        tags.append("easy")

    primary = next(
        (tag for tag in ("adversarial", "ambiguous", "rare", "easy") if tag in tags),
        "easy",
    )
    return primary, "|".join(tags)


def main() -> None:
    with INPUT.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    for row in rows:
        row["primary_tag"], row["tags"] = tags_for(row)
        row["ood"] = "false"

    fieldnames = [
        "gold_id",
        "query_id",
        "query",
        "target_sku",
        "transformation",
        "primary_tag",
        "tags",
        "ood",
    ]
    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} tagged gold queries to {OUTPUT}")


if __name__ == "__main__":
    main()
