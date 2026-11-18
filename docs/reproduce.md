# Reproduce evaluation

Commands below assume the repository root and Python 3.12. Create the
environment and install dependencies first:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip install -r backend/requirements.txt
```

## Dataset and frozen benchmark

The catalog and generated queries are deterministic. Regenerate development
data, then verify the frozen gold-set manifest:

```bash
python data/generate_catalog.py
python data/generate_queries.py
python data/generate_gold_set.py
python data/tag_gold_queries.py
python data/split_queries.py
python data/freeze_gold_set.py
```

Do not tune against `data/gold_queries.csv`; it is reserved for final
evaluation.

## Evaluation reports

Run the repository's evaluation scripts from the root:

```bash
python -m src.evaluate_baseline
python -m src.evaluate_g12_g13
python -m src.evaluate_coverage
python -m src.evaluate_drift
```

The generated reports belong in `results/`. Existing benchmark summaries are
described in `docs/baseline.md`, `docs/model_card.md`, and
`results/summary.md`.

## Tests and application checks

```bash
cd backend
python -m pytest -q
cd ../..
cd frontend
npm ci
npm run build
```

For a local end-to-end run, use `docker compose up --build` from the root and
check `/health`, `/docs`, the search page, the review queue, and the monitoring
panel. The backend load-test script records p50/p95/p99 latency in
`backend/results/latency.json`.
