"""Generate labeled distribution-shift queries from validation queries."""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "splits" / "validation.csv"
OUTPUT = ROOT / "shifted_queries.csv"


def load_rows() -> list[dict[str, str]]:
    with INPUT.open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def main() -> None:
    rows = load_rows()[:100]
    output: list[dict[str, str]] = []
    transformations = {
        "new_category": lambda query: f"hydraulic pump {query}",
        "new_supplier_style": lambda query: f"omnisupply-x {query}",
        "other_language": lambda query: f"perno acero {query}",
        "heavy_abbreviation": lambda query: query.replace("stainless steel", "ss").replace(
            "black oxide", "bo"
        ).replace("bearing", "brg").replace("connector", "conn").replace("washer", "wshr"),
    }
    for row in rows:
        for shift_type, transform in transformations.items():
            output.append(
                {
                    "query_id": row["query_id"],
                    "query": transform(row["query"]),
                    "shift_type": shift_type,
                    "is_shifted": "true",
                }
            )
    with OUTPUT.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=output[0].keys())
        writer.writeheader()
        writer.writerows(output)
    print(f"Wrote {len(output)} shifted queries to {OUTPUT}")


if __name__ == "__main__":
    main()
