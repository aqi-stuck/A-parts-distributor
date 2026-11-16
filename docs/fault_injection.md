# Fault injection (checklist G9)

The API must never answer a fault with a raw `500`, a stack trace, or a hang past
the timeout budget. Every injected fault below ends in a documented response:
either a **validation error (`422`)** with a clear message, or a **`200`** with
`route: "review"` and a `reason` a human can act on.

Run the suite from `backend/parts-search`:

```bash
python -m pytest -v tests/fault          # fault suite only (CI step "Fault-injection suite (G9)")
python -m pytest -v tests/fault -s       # also prints the p99 numbers
python -m pytest -v                      # whole backend suite
```

Faults are injected with `monkeypatch`/mocks — no real outages, no sleeps.

## Documented policy

| Input / fault class | Documented behaviour |
| --- | --- |
| Empty, whitespace-only, missing or `null` query | `null`/missing/empty → `422` with a FastAPI validation `detail` (per `docs/contract.md`); whitespace-only is syntactically valid → `200`, `route: "review"`. |
| Oversized input | 500 chars accepted, 501+ and 100k chars → `422` with a validation message. |
| Gibberish (random bytes, random unicode) | `200`, `route: "review"`, no ungrounded SKU. |
| Special characters, SQL fragments, prompt injection | `200`; query is treated as data. Every returned SKU must exist in `data/catalog.json`; instruction text never authorises a SKU. |
| Retrieval index / embedding model / reranker unavailable | F8 keyword fallback runs; `200`, `route: "review"`, `reason: "system error"`, results catalog-grounded. |
| Engine and fallback both unavailable | `200`, `route: "review"`, `reason: "system error"`, `results: []`. |
| Slow model (hangs past the budget) | `200`, `route: "review"`, `reason: "engine timeout"`, response inside `engine_timeout_ms`. |
| Audit/log write failure | Request still succeeds (`200`); failure written to **stderr**, counted in `log_write_failures_total`, exposed in `/metrics`. |
| Feedback store unavailable | `200`, `{"saved": false, "reason": "feedback_store_unavailable"}`. |
| Review-queue store unavailable | `200`, `[]`. |
| `/metrics` with audit store down | `200`, `db_status: "unavailable"`, counts fall back to 0. |

`engine_timeout_ms` lives in `config/thresholds.json` (H7), default `2000` ms, and
is read into `app.config.ENGINE_TIMEOUT_MS`. The engine call runs on a shared
4-worker `ThreadPoolExecutor`; the caller waits at most the budget.

## Results

| # | Input or fault | Expected behaviour | Actual behaviour | Pass/Fail | Test |
| --- | --- | --- | --- | --- | --- |
| 1 | Missing / empty / `null` query | `422` + `detail` | `422` + `detail` | PASS | `tests/fault/test_inputs.py::test_missing_empty_or_null_query_is_validation_error` (3 params) |
| 2 | Whitespace-only `"   \t \n "` | `200`, `review`, reason set | `200`, `review`, `no matches` | PASS | `test_whitespace_only_goes_to_review` |
| 3 | Random bytes (5 samples) | `200`, `review`, grounded | `200`, `review`, grounded | PASS | `test_gibberish_random_bytes` |
| 4 | Random unicode (5 samples) | `200`, `review`, grounded | `200`, `review`, grounded | PASS | `test_gibberish_random_unicode` |
| 5 | 100 000 characters | `422`, validation message | `422` ("String should have at most 500 characters") | PASS | `test_huge_input_rejected` |
| 6 | 500 vs 501 characters | `200` / `422` | `200` / `422` | PASS | `test_length_boundary` |
| 7 | Emoji, RTL, zero-width, NUL byte, control chars, HTML, SQL, SQL UNION, prompt injection (EN + ZH) — 10 params | `200`, grounded, no `SKU X` | `200`, grounded, no `SKU X` | PASS | `test_special_characters_and_injection_are_safe` |
| 8 | `'); DROP TABLE query_log;--` stored | Table intact, row stored | Table intact, row stored (parameterized SQL) | PASS | `test_sql_fragment_does_not_destroy_audit_table` |
| 9 | 200-request burst of bad input, then a good query | Later requests healthy | Final query `200` with `timing_ms`, grounded | PASS | `test_200_query_burst_stays_healthy` |
| 10 | Retrieval index unavailable | F8 fallback, `review`/`system error` | `200`, `review`, `system error`, grounded | PASS | `test_dependencies.py::test_index_unavailable_falls_back` |
| 11 | Embedding model raises | `200`, `review`, `system error` | Same | PASS | `test_embedding_model_failure_falls_back` |
| 12 | Reranker raises | `200`, `review`, `system error` | Same | PASS | `test_reranker_failure_falls_back` |
| 13 | Engine unavailable | `200`, `review`, `system error`, fallback candidates | Same | PASS | `test_engine_unavailable_falls_back` |
| 14 | Engine + keyword fallback down | `200`, `review`, `system error`, `[]` | Same | PASS | `test_engine_and_fallback_unavailable` |
| 15 | LLM explanation service down | Fault injectable only if D9 exists | **Skipped** — D9 (LLM explanations) is not implemented in this build, so there is no LLM dependency to break | SKIP | `test_llm_explanation_service_down` |
| 16 | Slow model blocks 5 s (budget 300 ms) | `200`, `review`, `engine timeout`, < 2 s | `200`, `review`, `engine timeout`, ~0.33 s | PASS | `test_slow_engine_respects_timeout_budget` |
| 17 | Audit store unopenable, `/search` | `200`, stderr, counter++ | `200`, stderr `query log failed`, `log_write_failures_total >= 1`, `db_status: unavailable` | PASS | `test_audit_store_unavailable_search_still_200` |
| 18 | `log_query` raises, `/search` | `200`, stderr, counter == 1 | `200`, stderr, `log_write_failures_total == 1` | PASS | `test_log_write_failure_is_counted` |
| 19 | Feedback store unavailable | `200`, `saved: false` | `200`, `{"saved": false, "reason": "feedback_store_unavailable"}` | PASS | `test_feedback_store_unavailable` |
| 20 | Review-queue store unavailable | `200`, `[]` | `200`, `[]` | PASS | `test_review_queue_store_unavailable` |
| 21 | `/metrics` with store down | `200`, `db_status: unavailable` | `200`, `db_status: unavailable`, `total_queries: 0` | PASS | `test_metrics_survives_store_outage` |

**Zero `500` responses across all cases.** Every fault test asserts `status_code`
explicitly; `test_200_query_burst_stays_healthy` allows only `200`/`422` over 200
requests.

## p99 latency under fault conditions (D11 `timing_ms.total`)

30 samples per fault mode, p99 computed as the nearest-rank 99th percentile of
`timing_ms.total` from the response body. Budget: `engine_timeout_ms = 2000` ms.

| Fault mode | p99 `timing_ms.total` | Budget | Within budget | Test |
| --- | --- | --- | --- | --- |
| Retrieval engine raising on every call | **17.18 ms** | 2000 ms | yes | `test_latency_p99.py::test_p99_dependency_error_within_budget` |
| Engine hanging past a shortened 300 ms budget | **324.69 ms** | 2000 ms (test shortens to 300 ms) | yes (≈ budget + pool overhead) | `test_p99_timeout_within_budget` |
| `log_query` raising on every call | **41.20 ms** | 2000 ms | yes | `test_p99_log_write_failure_within_budget` |

The hang case is bounded by construction: the response returns as soon as
`future.result(timeout=...)` expires, so p99 tracks the configured budget, not
the model's actual runtime.

## Known limitations

- **A timed-out worker thread keeps running** until the model returns. The pool is
  capped at 4 workers, so repeated timeouts can temporarily exhaust it and queue
  later calls (slow, not failing). Accepted for the hackathon.
- **No circuit breaker.** A persistently broken engine is retried (then fell back)
  on every request, paying the failed-call cost each time.
- **`log_write_failures_total` is per process**, not persisted; it resets on
  restart and is not shared across uvicorn workers.
- **The stderr fallback is not durable**: it satisfies "do not drop the response
  and keep the failure visible", but a real audit guarantee needs an out-of-process
  sink (file/syslog/collector).
- **`/feedback` returns `200` with `saved: false`** when the store is down rather
  than a `5xx`: the reviewer UI can retry, and no raw error reaches the browser.
