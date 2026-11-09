from pathlib import Path

from src.drift_detection import DriftDetector
from src.improved_retrieval import HybridPartsRetriever


CATALOG = Path(__file__).parents[1] / "data" / "catalog.csv"


def detector() -> DriftDetector:
    retriever = HybridPartsRetriever.from_csv(CATALOG)
    return DriftDetector(retriever, ["zinc steel bolt m6 20 mm"] * 10)


def test_ood_score_contains_required_features() -> None:
    result = detector().score_query("hydraulic pump perno acero")
    assert {"embedding_distance", "unseen_token_rate", "query_length", "category"} <= set(
        result["features"]
    )
    assert result["is_ood"]


def test_window_drift_alerts_on_new_category() -> None:
    result = detector().window_drift(["hydraulic pump perno acero"] * 10)
    assert result["alert"]
