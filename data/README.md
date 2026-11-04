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
