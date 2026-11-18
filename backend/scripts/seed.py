import sys
import os
import json
from app.storage import init_db, log_query, save_feedback, metrics
from app.search import SearchService
from app.config import MODEL_VERSION

def validate_catalog(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"Failed to read catalog: {e}")
        sys.exit(1)
    if not isinstance(data, list):
        print("Catalog is not a list")
        sys.exit(1)
    required = {"sku", "description", "brand", "size", "material", "category"}
    seen = set()
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            print(f"Item {i} is not an object")
            sys.exit(1)
        missing = required - item.keys()
        if missing:
            print(f"Item {i} missing keys {missing}")
            sys.exit(1)
        sku = item.get("sku")
        if sku in seen:
            print(f"Duplicate SKU {sku}")
            sys.exit(1)
        seen.add(sku)
    return data

def main():
    catalog_path = "data/catalog.json"
    catalog = validate_catalog(catalog_path)
    db_path = "data/app.db"
    if os.path.exists(db_path):
        os.remove(db_path)
    init_db()
    print(f"Loaded {len(catalog)} parts")
    service = SearchService("data/catalog.json")
    queries = [
        "hex bolt zinc",
        "steel nut 1/2",
        "washer 3/8",
        "zzqxv qqwpl",
        "M8x30 flange bolt",
        "screw",
        "pipe fitting",
        "flange bolt",
        "hex nut",
        "carriage bolt",
        "stainless screw",
        "galvanized washer",
        "brass fitting",
        "copper pipe",
        "nylon washer",
        "steel bolt",
        "aluminum bracket",
        "rubber gasket",
        "plastic cap",
        "zinc plated"
    ]
    for q in queries:
        result = service.search(q)
        route = result.get("route")
        latency = result.get("latency_ms", 0.0)
        results = result.get("results", [])
        top_sku = results[0]["sku"] if results else None
        output = results
        log_query(q, route, top_sku, float(latency), MODEL_VERSION, output)
    # demo feedback
    skus = [item["sku"] for item in catalog][:3]
    decisions = ["approve", "reject", "approve"]
    feedback_queries = ["hex bolt zinc", "steel nut 1/2", "washer 3/8"]
    for q, sku, dec in zip(feedback_queries, skus, decisions):
        save_feedback(q, sku, dec, reviewer="seed")
    m = metrics()
    print(m)

if __name__ == "__main__":
    main()
