from pathlib import Path

import pytest

from src.baseline import PartsBaseline, tokenize


CATALOG = Path(__file__).parents[1] / "data" / "catalog.csv"


def test_tokenize_preserves_part_identifiers() -> None:
    assert tokenize("M8 1/4-20 x 40 mm") == ["m8", "1/4-20", "x", "40", "mm"]


def test_baseline_returns_expected_sku() -> None:
    baseline = PartsBaseline.from_csv(CATALOG)
    results = baseline.search("zinc steel bolt m6 20 mm", limit=5)

    assert results
    assert results[0]["sku"] == "BOL-M6-020-0001"
    assert results[0]["evidence"]["matched_tokens"]


def test_baseline_rejects_invalid_input() -> None:
    baseline = PartsBaseline.from_csv(CATALOG)

    with pytest.raises(ValueError):
        baseline.search("   ")
    with pytest.raises(ValueError):
        baseline.search("bolt", limit=0)
