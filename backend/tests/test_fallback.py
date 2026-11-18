import json
import pytest
from app.search import SearchService


def test_engine_failure_uses_fallback():
    """When engine fails, fallback returns results from catalog."""
    service = SearchService("data/catalog.json")
    # Monkeypatch engine.search to raise
    def raise_error(query):
        raise RuntimeError("engine down")
    service.engine.search = raise_error

    result = service.search("hex bolt zinc")
    assert result["route"] == "review"
    assert result["reason"] == "system error"
    results = result["results"]
    assert isinstance(results, list)
    # Load catalog to verify SKUs
    with open("data/catalog.json", "r", encoding="utf-8") as f:
        catalog = json.load(f)
    catalog_skus = {p["sku"] for p in catalog}
    for item in results:
        assert item["sku"] in catalog_skus


def test_fallback_no_matches():
    """Fallback returns empty list when query matches nothing."""
    service = SearchService("data/catalog.json")
    def raise_error(query):
        raise RuntimeError("engine down")
    service.engine.search = raise_error

    result = service.search("zzqxv qqwpl")
    assert result["route"] == "review"
    assert result["reason"] == "system error"
    assert result["results"] == []
