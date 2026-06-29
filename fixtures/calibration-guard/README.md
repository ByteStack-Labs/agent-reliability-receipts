# Fixture: calibration-guard

Two batches of predictions from the same classifier, built to be diagnosed: an evaluation
batch and a production batch drawn from a shifted input distribution. This is a teaching
fixture, not a real model, and it is labeled as one on purpose.

## What it is

`naive_read.py` is the system under test: the naive reliability read that summarizes a
batch as overall accuracy plus mean confidence, the way a dashboard does. Read per split,
it makes a model that has come apart under shift still look healthy. `data/eval.jsonl` and
`data/production.jsonl` are the two committed batches; each prediction carries two signals,
the model's own stated `confidence` and an independent `verifier_score` from a cheap
secondary check. The two are kept separate and never averaged. Every production record also
records whether it came from the shifted pocket. `results/` holds the naive summary of each
split.

## Reproduce every number

```
cd fixtures/calibration-guard
python3 generate.py
```

Standard library only. No model, no GPU, no network. The random parts are seeded, so both
batches regenerate identically every run. The script writes `eval.jsonl` and
`production.jsonl` to `data/` and a naive summary per split to `results/`.

## What the numbers show

On the evaluation batch the model is well calibrated: ECE 0.0245, and stated confidence is
higher on the answers it gets right than on the ones it gets wrong. On the production
batch, where 40% of inputs come from a pocket the model cannot perceive, accuracy falls to
0.584 while mean confidence rises to 0.830, ECE jumps to 0.2572, and the confidence
separation inverts: wrong answers come back more confident than right ones. A confidence
threshold tuned on eval then catches only 28% of production errors, down from 77%. The
independent verifier, disagreeing with confidence by at least 0.25, still catches 64% and
never fires on the eval batch. The full re-derivation, and the proof that it fails closed,
is in `receipts/calibration-guard/`.
