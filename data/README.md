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

The gold set is frozen with a SHA-256 manifest. Verify it before evaluation:

```powershell
.\.venv\Scripts\python.exe data\freeze_gold_set.py
```

If verification fails, do not overwrite the manifest. Investigate the change
and create a new explicitly versioned gold set instead.

`tag_gold_queries.py` adds evaluation slices to every gold query. Gold queries
are all in-distribution because their target SKUs exist in the catalog.
Adversarial, ambiguous, rare, and easy tags are recorded as slices; OOD
queries belong in a separate future set rather than being mislabeled here.

```powershell
.\.venv\Scripts\python.exe data\tag_gold_queries.py
```
