import json
from pathlib import Path

from src.evaluate_coverage import OUTPUT


def test_coverage_report_has_monotonic_review_tradeoff() -> None:
    report = json.loads(OUTPUT.read_text(encoding="utf-8"))
    curve = report["curve"]
    assert report["queries"] == 400
    assert curve[0]["coverage"] == 1.0
    assert all(
        left["coverage"] >= right["coverage"]
        for left, right in zip(curve, curve[1:])
    )
    assert all(0 <= point["accuracy"] <= 1 for point in curve)
