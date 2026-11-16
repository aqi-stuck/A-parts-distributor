# API contract

The API is served by the backend on port `8000`. JSON responses use the
following contract. Unknown response fields may be added without breaking
clients; the fields below are stable for the current `v1` contract.

## `POST /search`

Request:

```json
{"query": "zinc hex bolt m8"}
```

`query` is required, must be a non-empty string, and is limited to 500
characters. An invalid request returns HTTP `422`.

Response (`200`):

```json
{
  "route": "auto",
  "reason": null,
  "results": [
    {
      "sku": "BLT-0042",
      "description": "M8 zinc hex bolt ...",
      "score": 0.93,
      "confidence": 0.95,
      "evidence": ["matched attribute: material = zinc"]
    }
  ],
  "latency_ms": 18.4,
  "timing_ms": {"engine": 17.9, "routing": 0.1, "total": 18.4},
  "engine": "model"
}
```

`route` is either `auto` or `review`. A review response includes a
human-readable `reason` such as `no matches`, `low confidence`, `top
candidates too close`, or `system error`. `results` contains at most five
catalog candidates. Every returned SKU must exist in the catalog.

## `POST /feedback`

Request:

```json
{
  "query": "zinc hex bolt m8",
  "sku": "BLT-0042",
  "decision": "approve",
  "reviewer": "warehouse-user",
  "query_id": 17
}
```

`decision` is one of `approve`, `correct`, or `reject`. `reviewer`, `sku`, and
`query_id` are optional. A successful request returns `{"saved": true}`.

## `GET /review-queue`

Returns an array of unresolved review items. Each item contains its query,
timestamp, latency, and the same catalog-grounded candidate shape used by
`/search`.

## `GET /metrics`

Returns aggregate metrics including:

- `total_queries`: total number of queries processed
- `review_count`: number of queries routed to human review
- `avg_latency_ms`: average query latency in milliseconds
- `db_status`: `ok` or `unavailable` depending on database health
- `log_write_failures_total`: count of audit log write failures

Drift detection metrics (available after a window of 100 queries):

- `drift_window_score`: latest window-level PSI value
- `drift_alert_active`: `0` or `1`, `1` when PSI or KS exceeds threshold
- `drift_window_size`: number of queries in the last completed window (100)
- `drift_last_window_end`: ISO-8601 timestamp of the last completed window
- `drift_status`: `warming_up` before first window completes, `ok` after
- `ood_score_mean`: mean OOD score over the current window's queries
- `ood_score_p95`: 95th percentile OOD score over the current window
- `ood_flag_rate`: fraction of queries flagged OOD in the current window

Legacy fields (for backward compatibility):

- `drift_score`: alias for `drift_window_score`
- `drift_alert`: boolean alias for `drift_alert_active > 0`

Before the first drift window completes, `drift_window_score` and related
fields are `null` and `drift_status` is `warming_up`.

## `GET /health`

Returns `{"status": "ok"}` when the API process is running.