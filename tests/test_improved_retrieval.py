from pathlib import Path

from src.baseline import PartsBaseline
from src.improved_retrieval import AttributeExtractor, HybridPartsRetriever, normalize_query


CATALOG = Path(__file__).parents[1] / "data" / "catalog.csv"


def test_normalization_handles_abbreviations_and_fraction_variants() -> None:
    assert normalize_query("ZINC SS bolt 1/420 40 millimeters") == (
        "zinc stainless steel bolt 1/4-20 40 mm"
    )


def test_attribute_extraction_reads_search_constraints() -> None:
    attributes = AttributeExtractor().extract("zinc stainless steel bolt M8 x 40 mm")
    assert attributes.values["material"] == "stainless steel"
    assert attributes.values["thread"] == "m8"
    assert attributes.values["length_mm"] == "40"


def test_hybrid_retriever_returns_evidence_and_sku() -> None:
    retriever = HybridPartsRetriever(PartsBaseline.from_csv(CATALOG).catalog)
    results = retriever.search("zinc steel bolt m6 20 mm")
    assert results
    assert results[0]["sku"] == "BOL-M6-020-0001"
    assert results[0]["evidence"]["attribute_agreement"] > 0
