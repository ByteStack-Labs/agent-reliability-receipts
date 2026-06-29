# Fixture: calibration-guard

A batch of confident classifier predictions, built to be diagnosed. This is a teaching
fixture, not a real model, and it is labeled as one on purpose.

## What it is

`naive_read.py` is the system under test: the naive reliability read that summarizes a
batch of predictions as overall accuracy plus mean confidence, the way a dashboard does.
That summary is what lets miscalibration ship, healthy accuracy next to high confidence
looks fine. `data/predictions.jsonl` is a committed batch of 500 binary-classifier
predictions, each with a stated confidence; `results/naive_metrics.json` is what the naive
read reports on it. The batch is built with one real flaw: most predictions are roughly
calibrated, but a concentrated pocket is highly confident and usually wrong.

## Reproduce every number

```
cd fixtures/calibration-guard
python3 generate.py
```

Standard library only. No model, no GPU, no network. The random parts are seeded, so the
batch regenerates identically every run. The script writes the predictions to `data/` and
the naive summary to `results/`.

## What the numbers show

The naive read is 0.686 accuracy at 0.825 mean confidence, unremarkable. Bin the
predictions by confidence and the picture changes: the model is well calibrated from 0.6
to 0.9, then in its top bin, where it places 187 of 500 predictions, it states ~0.94
confidence and is right ~0.55 of the time. Expected calibration error is 0.161, and 84
predictions made at 0.90 confidence or higher are wrong. The model is most confident
exactly where it is least correct. The full re-derivation, and the proof that it fails
closed, is in `receipts/calibration-guard/`.
