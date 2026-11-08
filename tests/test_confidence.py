from pathlib import Path

from sklearn.isotonic import IsotonicRegression

from src.improved_retrieval import HybridPartsRetriever


CATALOG = Path(__file__).parents[1] / "data" / "catalog.csv"


def test_confidence_contains_margin_and_catalog_grounding() -> None:
    retriever = HybridPartsRetriever.from_csv(CATALOG)
    result = retriever.search("zinc steel bolt m6 20 mm", limit=1)[0]
    assert 0 <= result["confidence"] <= 1
    assert result["evidence"]["score_margin"] >= 0
    assert result["evidence"]["catalog_verified"] is True


def test_calibrated_confidence_is_bounded() -> None:
    calibrator = IsotonicRegression(y_min=0, y_max=1, out_of_bounds="clip")
    calibrator.fit([0.1, 0.5, 0.9], [0, 1, 1])
    assert 0 <= calibrator.predict([0.7])[0] <= 1
