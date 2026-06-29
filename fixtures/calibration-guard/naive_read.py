"""The system under test for the calibration-guard fixture: the naive reliability read.

This is the thing being diagnosed, not a helper. It summarizes a batch of predictions the
way a dashboard does, overall accuracy and mean confidence, and reports nothing about
whether that confidence is earned, or whether it still holds when the input distribution
moves. Read per split, it makes a model that has come apart under shift look healthy.
Standard library only.
"""


def naive_summary(records):
    """Overall accuracy and mean confidence. The 'looks healthy' numbers."""
    n = len(records)
    acc = sum(1 for r in records if r["predicted"] == r["actual"]) / n
    conf = sum(r["confidence"] for r in records) / n
    return {"accuracy": round(acc, 4), "mean_confidence": round(conf, 4)}
