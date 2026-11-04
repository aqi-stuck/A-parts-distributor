"""Generate deterministic messy search queries linked to catalog SKUs."""

import csv
import random
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "catalog.csv"
OUTPUT = ROOT / "messy_queries.csv"

ABBREVIATIONS = {
    "aluminum": "alu",
    "bearing": "brg",
    "bracket": "brkt",
    "connector": "conn",
    "diameter": "dia",
    "stainless steel": "ss",
    "washer": "wshr",
}
NOISE = ("please", "need", "replacement", "warehouse", "part", "item")


def typo(word: str, rng: random.Random) -> str:
    if len(word) < 4:
        return word
    position = rng.randrange(len(word))
    return word[:position] + word[position + 1 :]


def fraction_variant(value: str) -> str:
    if value == "25":
        return "1 inch"
    if value == "50":
        return "2 inch"
    return f"{value}mm"


def make_query(row: dict[str, str], rng: random.Random) -> tuple[str, str]:
    fields = [
        row["finish"],
        row["material"],
        row["category"],
        row["thread"],
        f"{row['length_mm']} mm",
    ]
    transformations: list[str] = []
    choice = rng.choice(
        ("typo", "abbreviation", "units", "word_order", "missing", "noise")
    )

    if choice == "typo":
        index = rng.randrange(len(fields))
        fields[index] = typo(fields[index], rng)
        transformations.append("typo")
    elif choice == "abbreviation":
        for index, field in enumerate(fields):
            fields[index] = ABBREVIATIONS.get(field, field)
        fields[3] = fields[3].replace("-", "")
        transformations.append("abbreviation")
    elif choice == "units":
        fields[-1] = fraction_variant(row["length_mm"])
        transformations.append("unit_or_fraction")
    elif choice == "word_order":
        rng.shuffle(fields)
        transformations.append("word_order")
    elif choice == "missing":
        fields.pop(rng.randrange(len(fields)))
        transformations.append("missing_attribute")
    else:
        fields.insert(rng.randrange(len(fields) + 1), rng.choice(NOISE))
        transformations.append("noise")

    query = " ".join(fields)
    query = re.sub(r"\s+", " ", query).strip().lower()
    return query, "|".join(transformations)


def load_catalog() -> list[dict[str, str]]:
    with CATALOG.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def build_queries(count: int = 3000, seed: int = 20261105) -> list[dict[str, str]]:
    catalog = load_catalog()
    rng = random.Random(seed)
    queries: list[dict[str, str]] = []
    for query_id in range(1, count + 1):
        row = catalog[(query_id - 1) % len(catalog)]
        query, transformation = make_query(row, rng)
        queries.append(
            {
                "query_id": str(query_id),
                "query": query,
                "target_sku": row["sku"],
                "transformation": transformation,
            }
        )
    return queries


def main() -> None:
    queries = build_queries()
    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=queries[0].keys())
        writer.writeheader()
        writer.writerows(queries)
    print(f"Wrote {len(queries)} queries to {OUTPUT}")


if __name__ == "__main__":
    main()
