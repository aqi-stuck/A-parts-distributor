import json

from src.evaluate_g12_g13 import ERRORS, SUMMARY


def test_g12_and_g13_reports_are_complete() -> None:
    report = json.loads(ERRORS.read_text(encoding="utf-8"))
    metrics = report["headline_metrics"]
    assert metrics["improved_top_1_accuracy"] > metrics["baseline_top_1_accuracy"]
    assert len(report["failures"]) == 20
    assert all(item["confidence"] >= 0 for item in report["failures"])
    assert "G12 headline result" in SUMMARY.read_text(encoding="utf-8")
