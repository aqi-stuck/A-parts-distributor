"""Test that all committed frontend fixtures validate against active Pydantic models."""

import json
from pathlib import Path
import pytest

from app.schemas.common import Paginated
from app.schemas.monitoring import MonitoringSummaryResponse
from app.schemas.review import ReviewItem
from app.schemas.search import SearchResponseV1


EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "docs" / "examples"


def test_fixture_directory_exists():
    assert EXAMPLES_DIR.is_dir(), f"Expected examples directory at {EXAMPLES_DIR}"


def test_search_auto_fixture():
    path = EXAMPLES_DIR / "search_auto.json"
    assert path.is_file()
    model = SearchResponseV1.model_validate_json(path.read_text(encoding="utf-8"))
    assert model.route.value == "auto"
    assert model.reason.code == "high_margin"
    assert len(model.results) > 0
    assert model.results[0].confidence.level.value == "high"


def test_search_review_fixture():
    path = EXAMPLES_DIR / "search_review.json"
    assert path.is_file()
    model = SearchResponseV1.model_validate_json(path.read_text(encoding="utf-8"))
    assert model.route.value == "review"
    assert model.reason.code == "low_margin"
    assert any(any(ev.match.value == "mismatch" for ev in r.evidence) for r in model.results)


def test_search_fallback_fixture():
    path = EXAMPLES_DIR / "search_fallback.json"
    assert path.is_file()
    model = SearchResponseV1.model_validate_json(path.read_text(encoding="utf-8"))
    assert model.route.value == "review"
    assert model.reason.code == "dependency_unavailable"
    assert len(model.results) > 0


def test_search_not_found_fixture():
    path = EXAMPLES_DIR / "search_not_found.json"
    assert path.is_file()
    model = SearchResponseV1.model_validate_json(path.read_text(encoding="utf-8"))
    assert model.route.value == "review"
    assert model.reason.code == "not_found"
    assert model.results == []


def test_review_queue_fixture():
    path = EXAMPLES_DIR / "review_queue.json"
    assert path.is_file()
    model = Paginated[ReviewItem].model_validate_json(path.read_text(encoding="utf-8"))
    assert len(model.items) == 3
    assert model.next_cursor is not None
    assert model.total_estimate == 42
    for item in model.items:
        assert isinstance(item.id, str)
        assert item.status.value in ("pending", "approved", "corrected", "rejected")
        assert item.priority >= 0


def test_monitoring_summary_fixture():
    path = EXAMPLES_DIR / "monitoring_summary.json"
    assert path.is_file()
    model = MonitoringSummaryResponse.model_validate_json(path.read_text(encoding="utf-8"))
    assert model.drift.alert_active is True
    assert model.drift.status == "alert"
    assert model.escalation.rate > 0.0
    assert model.latency_ms.p50 is not None
    assert model.ood.mean_score is not None


def test_monitoring_summary_ok_fixture():
    path = EXAMPLES_DIR / "monitoring_summary_ok.json"
    assert path.is_file()
    model = MonitoringSummaryResponse.model_validate_json(path.read_text(encoding="utf-8"))
    assert model.drift.alert_active is False
    assert model.drift.status == "ok"
    assert model.escalation.rate >= 0.0
