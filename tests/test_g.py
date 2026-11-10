import json
from pathlib import Path

from src.evaluate_g import OUTPUT


def test_g1_to_g4_report_passes_grounding_and_not_found_checks() -> None:
    report = json.loads(OUTPUT.read_text(encoding="utf-8"))
    assert report["g3_grounding"]["hallucinated_sku_rate"] == 0.0
    assert report["g3_grounding"]["catalog_grounded_explanations"]
    assert report["g4_nonexistent_parts"]["all_returned_not_found"]
    assert report["g2_hard_case_results"]["ood_queries"] == 400
