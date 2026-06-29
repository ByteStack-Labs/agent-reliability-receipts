"""Build the calibration-guard fixture: two committed batches of predictions from the same
classifier, an evaluation batch and a production batch drawn from a shifted input
distribution, each scored by the naive reliability read. Standard library only.

Honest by construction:
  - Each prediction carries two signals: the model's own stated `confidence`, and an
    independent `verifier_score` from a cheap secondary check. Only `confidence` is the
    model talking about itself. The verifier is a separate signal and is kept separate,
    never averaged into the confidence.
  - Every production record persists `shift`, so the per-slice decoupling is
    reconstructable from the committed artifacts alone.
  - random.seed is fixed, so every number regenerates identically.

The flaw, stated plainly. On the evaluation distribution the model is well calibrated:
stated confidence tracks how often it is actually right, and the verifier agrees. The
production batch draws a large minority of its inputs from a shifted pocket the model
cannot perceive. There it stays just as confident while its accuracy collapses. Its own
confidence does not move, so a confidence threshold tuned on eval stops protecting
anything. The verifier, grounded in something the shift perturbs, drops on exactly those
cases, so the disagreement between the two signals still flags them. A single confidence
signal that decouples under shift, versus a two-signal disagreement rule that survives it,
is the whole demonstration. The naive read, high accuracy beside high confidence, cannot
see any of it.
"""
import json, os, random
from naive_read import naive_summary

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data"); RES = os.path.join(HERE, "results")
os.makedirs(DATA, exist_ok=True); os.makedirs(RES, exist_ok=True)

random.seed(42)
N = 500                 # predictions per split
SHIFT_FRACTION = 0.40   # share of production inputs drawn from the shifted pocket


def clamp(x, lo=0.01, hi=0.99):
    return max(lo, min(hi, x))


def calibrated_record(i, prefix):
    """Well behaved: stated confidence tracks the true correctness probability, and the
    verifier agrees with it. This is what calibrated looks like."""
    p = random.uniform(0.55, 0.98)                        # true prob this one is right
    conf = clamp(round(p + random.uniform(-0.03, 0.03), 2), 0.50, 0.99)
    verifier = clamp(round(p + random.uniform(-0.05, 0.05), 2))
    correct = random.random() < p
    actual = random.randint(0, 1)
    predicted = actual if correct else 1 - actual
    return {"id": f"{prefix}{i:03d}", "confidence": conf,
            "verifier_score": verifier, "predicted": predicted, "actual": actual}


def shifted_record(i, prefix):
    """The pocket the model cannot see: very confident, usually wrong. The verifier,
    grounded in what the shift perturbs, drops and so disagrees with the confidence."""
    conf = clamp(round(random.uniform(0.88, 0.99), 2), 0.50, 0.99)
    p = 0.30                                              # confident, but usually wrong
    verifier = clamp(round(random.uniform(0.20, 0.50), 2))
    correct = random.random() < p
    actual = random.randint(0, 1)
    predicted = actual if correct else 1 - actual
    return {"id": f"{prefix}{i:03d}", "confidence": conf,
            "verifier_score": verifier, "predicted": predicted, "actual": actual}


def build(split):
    prefix = "e" if split == "eval" else "p"
    recs = []
    for i in range(N):
        if split == "production" and random.random() < SHIFT_FRACTION:
            r = shifted_record(i, prefix); r["shift"] = True
        else:
            r = calibrated_record(i, prefix)
            if split == "production":
                r["shift"] = False
        recs.append(r)
    return recs


out = {}
for split in ("eval", "production"):
    recs = build(split)
    with open(os.path.join(DATA, f"{split}.jsonl"), "w") as f:
        for r in recs:
            f.write(json.dumps(r) + "\n")
    metrics = naive_summary(recs)
    metrics["split"] = split
    if split == "production":
        metrics["shifted_fraction"] = round(sum(r["shift"] for r in recs) / N, 4)
    with open(os.path.join(RES, f"{split}_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    out[split] = metrics

print(json.dumps(out, indent=2))
