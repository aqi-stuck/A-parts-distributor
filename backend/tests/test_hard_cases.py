import json
import pytest
from fastapi.testclient import TestClient
from app.main import app

def load_cases():
    with open("tests/hard_cases.json", "r", encoding="utf-8") as f:
        return json.load(f)

def load_catalog_skus():
    with open("data/catalog.json", "r", encoding="utf-8") as f:
        catalog = json.load(f)
    return {p["sku"] for p in catalog}

def test_hard_cases():
    cases = load_cases()
    catalog_skus = load_catalog_skus()
    passed = 0
    total = len(cases)
    with TestClient(app) as client:
        for case in cases:
            cid = case["id"]
            query = case["query"]
            expect_status = case.get("expect_status", 200)
            expect_route = case.get("expect_route")
            try:
                r = client.post("/search", json={"query": query})
                status = r.status_code
                if status != expect_status:
                    print(f"[FAIL] {cid} status {status} != expected {expect_status}")
                    continue
                if expect_status != 200:
                    # validation error expected, no further checks
                    passed += 1
                    continue
                data = r.json()
                route = data.get("route")
                if expect_route and route != expect_route:
                    print(f"[FAIL] {cid} route {route} != expected {expect_route}")
                    continue
                results = data.get("results", [])
                # hallucination check
                hallucinated = False
                for item in results:
                    sku = item.get("sku")
                    if sku not in catalog_skus:
                        hallucinated = True
                        print(f"[FAIL] {cid} hallucinated SKU {sku}")
                        break
                    if sku == "ADMIN-000":
                        hallucinated = True
                        print(f"[FAIL] {cid} ADMIN-000 appeared")
                        break
                if hallucinated:
                    continue
                passed += 1
            except Exception as e:
                print(f"[FAIL] {cid} exception {e}")
                continue
    accuracy = passed / total if total else 0
    print(f"hard-case accuracy: {passed}/{total}")
    assert accuracy == 1.0, f"hard-case accuracy {passed}/{total} != 1.0"
