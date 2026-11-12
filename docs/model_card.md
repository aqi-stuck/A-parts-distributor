# Parts distributor retrieval model card

## Intended use

This system retrieves catalog SKUs from messy warehouse part descriptions. It
assists warehouse staff, returns catalog-grounded evidence, and routes
uncertain matches to human review.

## Data and evaluation

The catalog is a deterministic synthetic dataset of 3,000 parts. Evaluation
uses the frozen 400-query gold set in `data/gold_queries_tagged.csv`, kept
separate from training and validation data.

## Results

On the frozen benchmark, the improved hybrid retriever achieves 85.25% Top-1
accuracy versus 78.75% for the BM25/TF-IDF/fuzzy baseline. It returns only
catalog SKUs, and nonexistent-part checks returned `not_found`.

## Known limitations and bias findings

- Missing-attribute/ambiguous queries are weakest at 38.81% Top-1 accuracy.
- Category accuracy ranges from 78.72% for seals to 89.80% for brackets.
- Common and rare category accuracy is similar (85.19% and 85.71%), but the
  gold set contains only the proxy large-brand group, so small-brand fairness
  is not estimable yet.
- At the 0.9 confidence threshold, auto-answer coverage is 75.5% with a 4.3%
  observed error rate. Calibration ECE is 0.1196.
- The benchmark and catalog are synthetic; results do not establish production
  performance on real supplier language or safety-critical parts.

## Human responsibility

Reviewers remain responsible for ambiguous, low-confidence, out-of-distribution,
or high-impact part decisions. The model must not invent SKUs or specifications.
