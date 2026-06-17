# Fixture: invoice-extraction

A deliberately format-fragile extraction system, built to be diagnosed. This
is a teaching fixture, not a real product, and it is labeled as one on purpose.
Nothing here is hidden or dressed up as a genuine experiment.

## What it is

`extractor.py` reads eleven fields from an invoice by line position. It assumes
the fields always arrive one per line in a fixed order. On consistently
formatted input it is perfect. When the order or line structure shifts, it
silently assigns values to the wrong fields and still returns clean, well-formed
output. It has learned layout, not meaning.

## Reproduce every number

```
cd fixtures/invoice-extraction
python3 generate.py
```

Standard library only. No model, no GPU, no network. `random.seed(42)` is fixed,
so the numbers regenerate identically every run. The script writes synthetic
data to `data/` and metrics to `results/`.

## What the numbers show

Evaluation (the format the extractor expects) scores 100% exact match.
Production (the same eleven fields, shifted formatting) drops to about 86%
exact match at roughly 95% mean field accuracy: well-formed output, no errors
raised, a silent failure on the records that matter.

The honest part is the per-slice breakdown in `results/production_metrics.json`.
`shift_type` is persisted on every production record, so the failure can be
attributed to its cause: order-preserving shifts (delimiter, whitespace) survive
at 1.0, while shifts that move fields (reorder, mixed, compact, verbose) collapse
to 0.0. The root cause is positional dependence, and the saved artifacts prove it
rather than asserting it.

## Design notes

This fixture bakes in three habits that a real diagnostic pipeline should keep:
accuracy is measured against ground truth and never relabeled as "confidence"
(no confidence signal is claimed, because none is measured); `shift_type` is
saved so per-slice analysis is possible from the artifacts alone; and the run is
seeded so every number is reproducible.
