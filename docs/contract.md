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

Returns `total_queries`, `review_count`, and `avg_latency_ms`. When drift
measurements are available, it may also include `drift_score` and
`drift_alert`.

## `GET /health`

Returns `{"status": "ok"}` when the API process is running.
