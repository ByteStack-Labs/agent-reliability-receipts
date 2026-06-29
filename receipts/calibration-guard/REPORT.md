# calibration-guard receipt: calibration is a property of a distribution

The same classifier, read on two committed batches: an evaluation batch and a production
batch drawn from a shifted input distribution. Reproduce every number from this directory
with `python3 verify.py` (standard library only, no model, no GPU). The batches regenerate
with `python3 generate.py` from `fixtures/calibration-guard/`.

## What the naive read reports

Summarize each split the way a dashboard does, accuracy and mean confidence:

| split      | accuracy | mean confidence |
| ---------- | -------- | --------------- |
| eval       | 0.772    | 0.7687          |
| production | 0.584    | 0.8297          |

Accuracy falls by nineteen points and mean confidence *rises* by six. Confidence moves the
wrong way as correctness collapses. The naive read shows the drop but cannot say why, or
which predictions to stop trusting.

## Calibration inverts under shift, it does not just degrade

Bin each split by confidence and compare confidence to accuracy:

| measure                                   | eval     | production |
| ----------------------------------------- | -------- | ---------- |
| expected calibration error (ECE)          | 0.0245   | 0.2572     |
| confidence(correct) − confidence(wrong)   | +0.0839  | −0.0408    |
| high-confidence (≥0.9) error rate         | 0.0444   | 0.5507     |

On eval the model is well calibrated and confidence separates right from wrong: it is more
confident on the answers it gets right. On production the gap is ten times larger and the
separation **inverts** to negative, the wrong answers come back more confident than the
right ones. The high-confidence error rate runs from about one in twenty-three to more than
one in two. This is not a model that got noisier; it is a model whose confidence now points
the wrong way, and no single accuracy number, on either split alone, shows it.

## One signal fails under shift, an independent second holds

A natural response is to abstain on low confidence. Tune that threshold on eval and it works
there, then stops working exactly when it is needed:

| rule, scored on errors                                   | eval  | production |
| -------------------------------------------------------- | ----- | ---------- |
| abstain if confidence < 0.80 (tuned on eval)             | 0.772 | 0.284      |
| flag if confidence − verifier_score ≥ 0.25 (independent) | —     | 0.644      |

The eval-tuned confidence rule recovers 77% of eval errors but only 28% of production
errors: because the model stays confident under shift, a rule built on its own confidence
silently stops protecting. An independent verifier disagreeing with that confidence by at
least 0.25 recovers 64% of production errors, and fires zero times on the eval batch (its
largest eval disagreement is 0.07, well under the threshold). It is not a perfect detector,
of the 197 production cases it flags, 134 are genuinely wrong (precision 0.68), and it
misses 74 low-confidence errors where the verifier was also low and so did not disagree. But
it more than doubles the protection the stale confidence rule provides under shift, using a
signal the model does not control.

## The receipt

`verify.py` re-derives the naive read, the per-split ECE and confidence separation, the
high-confidence error rates, and both detector rules from the two committed batches in
`fixtures/calibration-guard/data/`, importing the fixture's own naive read for the headline
numbers and never reading `results/` back. The figures here are not asserted; they are what
the script prints, or it exits non-zero. The receipt fails closed: erase the disagreement on
a single shifted record and the committed counts stop reproducing.

## The judge layer, kept separate

This fixture is synthetic and openly so. The verifier is constructed to respond to what the
shift perturbs, which is why it separates the shifted slice cleanly; a real secondary check
is noisier, and the precision and recall above would move. What transfers is not the exact
figures but the method: calibration must be measured on the production distribution, not
assumed from the eval one, and the protective signal must be one the model does not control.
Any qualitative account of *why* a given model decouples under a given shift is a hypothesis
that belongs alongside this, labeled, and never mixed into the numbers.

## The open question

The shift here is a single fixed pocket at one mixing fraction. How the inversion and the
detector behave as the shifted fraction varies, and under gradual rather than abrupt shift,
is untested; sweeping that fraction is the measurement that would close it.

---

Built by ByteStack Labs. Every number reproduces from runnable code, or it does not ship.
