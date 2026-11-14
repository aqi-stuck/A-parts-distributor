import pytest
from app.config import VERSION, LOW_CONFIDENCE, TOO_CLOSE
from app.routing import decide_route


def test_config_loads():
    """Config loads and version is correct."""
    assert VERSION == "1.1"
    assert isinstance(LOW_CONFIDENCE, float)
    assert isinstance(TOO_CLOSE, float)


def test_decide_route_empty():
    """decide_route returns review for empty results."""
    route, reason = decide_route([])
    assert route == "review"
    assert reason == "no matches"
