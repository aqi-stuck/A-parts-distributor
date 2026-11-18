"""Shared fixtures for the fault-injection suite."""

import json

import pytest
from fastapi.testclient import TestClient

import app.storage as storage
from app.main import app

with open("data/catalog.json", encoding="utf-8") as _f:
    CATALOG = json.load(_f)
CATALOG_SKUS = {part["sku"] for part in CATALOG}


@pytest.fixture(autouse=True)
def reset_failure_counter():
    """Each test starts from a clean log-write failure counter."""
    storage.reset_log_write_failures()
    yield
    storage.reset_log_write_failures()


@pytest.fixture
def client():
    """TestClient with lifespan (init_db) running."""
    with TestClient(app) as test_client:
        yield test_client
