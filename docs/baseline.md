# Retrieval baseline

## Version and scope

Baseline version: `v1`, evaluated against the frozen 400-query gold set on
2026-11-06. It combines BM25 keyword scores, word/phrase TF-IDF similarity,
and RapidFuzz description similarity with weights `0.45 / 0.35 / 0.20`.

## Results

Results are stored in [`results/baseline_v1.json`](../results/baseline_v1.json).

| Metric | Result |
|---|---:|
| Queries | 400 |
| Top-1 accuracy | 78.75% |
| Top-5 accuracy | 95.25% |

The JSON report also includes transformation and difficulty slices plus the
queries missed by Top-5 retrieval.

## Known failure modes

- Abbreviations and fraction variants can collapse distinct SKUs into similar
  lexical representations.
- Missing attributes make near-duplicate parts difficult to distinguish.
- The baseline has no explicit attribute extraction or agreement check.
- It has no confidence calibration or out-of-distribution detection.

The baseline is a measurement anchor, not the final production retriever.
