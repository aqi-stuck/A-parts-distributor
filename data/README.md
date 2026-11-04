# Dataset

`catalog.csv` is a deterministic synthetic catalog for checklist item A4.
It contains 3,000 parts across fasteners, bearings, seals, brackets, and
connectors, with structured attributes suitable for retrieval and hard-case
evaluation.

The catalog is generated locally by:

```powershell
.\.venv\Scripts\python.exe data\generate_catalog.py
```

It has no external data license or personal data dependency. The generator is
the source of truth; do not hand-edit `catalog.csv`.

`generate_queries.py` creates deterministic messy queries linked to catalog
SKUs. It covers typos, abbreviations, unit and fraction variants, word-order
changes, missing attributes, and noise:

```powershell
.\.venv\Scripts\python.exe data\generate_queries.py
```

`generate_gold_set.py` creates the frozen 400-query evaluation set from the
generated labeled queries. It balances all six transformation types and
verifies every target SKU exists in `catalog.csv`:

```powershell
.\.venv\Scripts\python.exe data\generate_gold_set.py
```

Do not tune retrieval behavior against `gold_queries.csv`; use it only for
final evaluation.
