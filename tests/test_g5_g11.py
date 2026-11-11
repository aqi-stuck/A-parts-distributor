import json
from pathlib import Path

from src.evaluate_g5_g11 import OUTPUT


def test_g5_to_g11_report_has_required_sections() -> None:
    report = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert {"g5_bias", "g6_query_style", "g7_escalation_and_error", "g10_calibration", "g11_robustness"} <= set(report)
    assert 0 <= report["g10_calibration"]["expected_calibration_error"] <= 1
    assert len(report["g11_robustness"]["accuracy_by_noise_level"]) == 6
    assert report["g7_escalation_and_error"]["auto_answered"] + report["g7_escalation_and_error"]["reviewed"] == 400
