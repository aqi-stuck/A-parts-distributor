# Distribution-shift detection

The detector uses four query features:

- Embedding distance from the nearest catalog document
- Unseen-token rate against the catalog vocabulary
- Query length
- Unknown-category rate, with category proportions tracked per window

The per-query OOD threshold is the 95th percentile of scores from the
validation reference window. Window drift uses KS statistics for numeric
features and PSI for category proportions. The current alert thresholds are
`KS >= 0.2` or `PSI >= 0.2`.

Generate simulated shifts and evaluate them with:

```powershell
.\.venv\Scripts\python.exe data\generate_shifts.py
.\.venv\Scripts\python.exe -m src.evaluate_drift
```

The report is saved to `results/drift_v1.json`. The simulated benchmark is
intentionally diagnostic, not a production threshold claim: its per-query
detector achieved 75.61% precision and 15.50% recall overall, while the
window detector raised an alert with a maximum KS statistic of 0.584487.
