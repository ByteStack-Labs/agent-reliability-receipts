# Fixture: tool-eval

A tool evaluation scored three ways, built to be diagnosed. This is a teaching fixture,
not a real product, and it is labeled as one on purpose. Nothing here is hidden or dressed
up as a genuine experiment.

## What it is

`scorer.py` is the system under test: a naive tool-eval scorer that grades a tool's answer
by exact string match against a stored ground truth, the way a naive tool evaluation does.
It is fragile in one real way. It marks a correct value wrong when the format differs
(`$11,614.72` vs `11614.72`), and it marks a wrong value right when the answer happens to
match a stored ground truth that is itself wrong. `data/runs.jsonl` is a committed
eight-task calculator run transcript; `results/naive_metrics.json` is what the naive scorer
reports on it.

## Reproduce every number

```
cd fixtures/tool-eval
python3 generate.py
```

Standard library only. No model, no GPU, no network. The transcript is fixed, so the
numbers regenerate identically every run. The script writes the run data to `data/` and
the naive metric to `results/`.

## What the numbers show

The naive scorer reports 0.750. Re-derive each answer from the raw operands, the real
ground truth, and you also get 0.750, but on a different set of failing tasks. The naive
scorer marks a correct answer wrong (a dollar sign and a comma) and marks a wrong answer
right (it matches a transposed ground truth). Normalizing format alone lifts the number to
0.875 by recovering the false negative, but it still cannot see the silent error, because
that failure is not about format, it is about truth. The full re-derivation, and the proof
that it fails closed, is in `receipts/tool-eval/`.
