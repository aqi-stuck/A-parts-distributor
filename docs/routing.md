# Routing policy

The service is allowed to auto-answer only when the catalog contains a strong,
unambiguous match. Otherwise it returns the best available evidence with
`route: "review"` so a person can approve, correct, or reject it.

## Auto-answer

Return `route: "auto"` only when:

- at least one catalog candidate exists;
- the top candidate's calibrated confidence is at least `0.90`; and
- the top candidate is not within `0.05` score of the second candidate.

The thresholds are versioned in
[`backend/config/thresholds.json`](../backend/config/thresholds.json).

## Human review

Use `route: "review"` with the first applicable reason:

| Reason | Meaning |
| --- | --- |
| `no matches` | No catalog candidate was found. |
| `low confidence` | The best candidate is below the confidence threshold. |
| `top candidates too close` | Near-duplicate candidates cannot be separated safely. |
| `system error` | Retrieval or a dependency failed; keyword fallback evidence may be present. |

Review is also the required disposition for empty, gibberish, prompt-injection,
nonexistent-part, out-of-distribution, safety-critical, and high-value
requests. A reviewer owns the final decision and should record feedback through
`POST /feedback`.

The policy never treats query text as instructions. It also never authorizes a
SKU or specification that is absent from the catalog.
