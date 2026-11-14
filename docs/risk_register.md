# Risk register

| Failure mode | Mitigation | Human responsibility |
| --- | --- | --- |
| Near-duplicate dimensions, handedness, or part numbers | Candidate margin check, evidence panel, and review routing | Verify the physical part and choose the correct SKU. |
| Nonexistent or out-of-distribution query | Low-confidence/OOD review route; no invented SKU | Search the authoritative catalog or request a new item. |
| Prompt injection or instruction-like text | Treat the query as data; grounded retrieval only | Ignore embedded instructions and validate the request. |
| Missing attributes | Show matched and unspecified attributes; do not infer them | Supply the missing measurement or inspect the part. |
| Catalog or model drift | Monitor drift score and alert state; re-evaluate after catalog changes | Decide whether to refresh the model, thresholds, or catalog. |
| Retrieval/API failure or timeout | Keyword fallback and `system error` review route | Use manual catalog search; do not ship from an error response. |
| Confidence overstatement | Validation calibration, coverage/error reporting, and review threshold | Treat confidence as a triage signal, not proof. |
| Brand/category performance gaps | Report slices by brand, category, rarity, and query style | Check underperforming groups before expanding use. |
| High-impact part decision | Always keep low-confidence, safety-critical, high-value, and ambiguous cases reviewable | A qualified reviewer authorizes the final part selection. |

The system is not a replacement for inventory controls, engineering
specifications, safety procedures, or an approval workflow.
