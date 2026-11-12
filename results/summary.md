# Retrieval evaluation summary

Evaluated on the frozen `data/gold_queries_tagged.csv` benchmark (400 queries).

## G12 headline result

| System | Top-1 accuracy | Correct |
| --- | ---: | ---: |
| Baseline (BM25 + TF-IDF + fuzzy) | 78.75% | 315 |
| Improved hybrid retriever | 85.25% | 341 |

The improved system gains **6.50%** absolute Top-1 accuracy on the frozen benchmark. This is an evaluation-only comparison; the gold set was not used for tuning.

## G13 error analysis

The accompanying JSON lists the 20 incorrect improved predictions with the highest confidence. The most important unresolved pattern is incomplete or ambiguous input: the system can be confident when several catalog records share the visible attributes. These cases should remain reviewable rather than being treated as definitive answers.

See `results/error_analysis_v1.json` for each query, expected and predicted SKU, confidence, and cause.
