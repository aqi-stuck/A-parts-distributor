
from csv import DictWriter
from itertools import product
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "catalog.csv"

BRANDS = ("ForgePro", "Northstar", "Apex", "Mekanix", "RivetWorks")
MATERIALS = ("steel", "stainless steel", "aluminum", "brass")
FINISHES = ("zinc", "black oxide", "plain", "nickel")


def build_rows(limit: int = 3000) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    combinations = product(
        BRANDS,
        MATERIALS,
        FINISHES,
        ("bolt", "nut", "washer", "screw", "bearing", "seal", "bracket", "connector"),
        ("M6", "M8", "M10", "M12", "1/4-20", "3/8-16"),
        (20, 25, 30, 40, 50, 60),
    )
    for index, (brand, material, finish, category, thread, length) in enumerate(
        combinations, start=1
    ):
        if (index - 1) % 7 != 0:
            continue
        if len(rows) >= limit:
            break
        sku = f"{category[:3].upper()}-{thread.replace('/', '').replace('-', '')}-{length:03d}-{index:04d}"
        description = f"{finish} {material} {category} {thread} x {length} mm"
        rows.append(
            {
                "sku": sku,
                "description": description,
                "brand": brand,
                "category": category,
                "material": material,
                "thread": thread,
                "diameter_mm": thread.split("-")[0].removeprefix("M")
                if thread.startswith("M")
                else "",
                "length_mm": str(length),
                "finish": finish,
                "compatible_model": f"IND-{(index % 12) + 1:02d}",
            }
        )
    return rows


def main() -> None:
    rows = build_rows()
    with OUTPUT.open("w", newline="", encoding="utf-8") as file:
        writer = DictWriter(file, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows to {OUTPUT}")


if __name__ == "__main__":
    main()
