"""The system under test for the calibration-guard fixture: the naive reliability read.

This is the thing being diagnosed, not a helper. It summarizes a batch of confident
predictions the way a dashboard does: overall accuracy and mean confidence. That summary
is exactly why miscalibration ships, high accuracy next to high confidence looks healthy,
and says nothing about whether the confidence is earned where it matters. Standard library
only.
"""


def naive_summary(records):
    """Overall accuracy and mean confidence. The 'looks healthy' numbers."""
    n = len(records)
    acc = sum(1 for r in records if r["predicted"] == r["actual"]) / n
    conf = sum(r["confidence"] for r in records) / n
    return {"accuracy": round(acc, 4), "mean_confidence": round(conf, 4)}
