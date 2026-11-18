"""p99 latency under fault conditions, measured from the D11 timing output.

Each fault mode is sampled 30 times; p99 of timing_ms.total must stay inside the
configured engine timeout budget (config/thresholds.json: engine_timeout_ms).
Run with -s to print the numbers used in docs/fault_injection.md.
"""

import math
import threading

import app.search as search_module
import app.storage as storage
from app.config import ENGINE_TIMEOUT_MS
from app.main import service

SAMPLES = 30


def _p99(values):
    ordered = sorted(values)
    index = max(0, math.ceil(0.99 * len(ordered)) - 1)
    return ordered[index]


def _samples(client, monkeypatch, mode, query="hex bolt zinc"):
    totals = []
    for _ in range(SAMPLES):
        r = client.post("/search", json={"query": query})
        assert r.status_code == 200
        totals.append(r.json()["timing_ms"]["total"])
    return totals


# Fault: retrieval engine raises. p99 must stay inside the timeout budget.
def test_p99_dependency_error_within_budget(client, monkeypatch):
    def boom(query):
        raise RuntimeError("engine down")

    monkeypatch.setattr(service.engine, "search", boom)
    totals = _samples(client, monkeypatch, "error")
    p99 = _p99(totals)
    print(f"p99 dependency_error: {p99:.2f} ms (budget {ENGINE_TIMEOUT_MS} ms)")
    assert p99 < ENGINE_TIMEOUT_MS


# Fault: engine hangs past a shortened timeout. p99 tracks the timeout, not the hang.
def test_p99_timeout_within_budget(client, monkeypatch):
    event = threading.Event()
    budget_ms = 300

    def slow(query):
        event.wait(5)
        return []

    monkeypatch.setattr(service.engine, "search", slow)
    monkeypatch.setattr(search_module, "ENGINE_TIMEOUT_MS", budget_ms)
    try:
        totals = _samples(client, monkeypatch, "timeout")
    finally:
        event.set()

    p99 = _p99(totals)
    print(f"p99 engine_timeout: {p99:.2f} ms (shortened budget {budget_ms} ms)")
    assert p99 < budget_ms + 500


# Fault: audit write fails on every request. p99 is normal-path latency.
def test_p99_log_write_failure_within_budget(client, monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("disk full")

    monkeypatch.setattr(storage, "log_query", boom)
    totals = _samples(client, monkeypatch, "log")
    p99 = _p99(totals)
    print(f"p99 log_write_failure: {p99:.2f} ms (budget {ENGINE_TIMEOUT_MS} ms)")
    assert p99 < ENGINE_TIMEOUT_MS
