# calibration-guard receipt: confident exactly where it is wrong

A batch of 500 confident predictions, read two ways from the same committed data. Reproduce
every number from this directory with `python3 verify.py` (standard library only, no model,
no GPU). The fixture regenerates with `python3 generate.py` from `fixtures/calibration-guard/`.

## What the naive read reports

Summarize the batch the way a dashboard does, overall accuracy and mean confidence, and you
get **0.686 accuracy at 0.825 mean confidence**. Read on its own, that is a healthy-looking
accuracy sitting beside high confidence. Nothing in those two numbers asks whether the
confidence is earned.

## Where the confidence is earned, and where it is not

Bin the predictions by stated confidence and compare each bin's confidence to its actual
accuracy:

| confidence bin | count | avg confidence | accuracy | gap (conf − acc) |
| -------------- | ----- | -------------- | -------- | ---------------- |
| [0.6, 0.7)     | 96    | 0.6485         | 0.6354   | +0.0131          |
| [0.7, 0.8)     | 96    | 0.7456         | 0.7396   | +0.0060          |
| [0.8, 0.9)     | 121   | 0.8464         | 0.8926   | −0.0461          |
| [0.9, 1.0)     | 187   | 0.9426         | 0.5508   | **+0.3918**      |

The model is well calibrated through the mid bins, the gap between what it claims and what
it delivers is within a few points. Then the top bin breaks: it states about 0.94 confidence
and is right about 0.55 of the time. Expected calibration error across the batch is **0.161**.
The calibration holds right up until the confidence is highest, then fails.

## The slice that ships

The predictions an operator trusts most are the high-confidence ones, and that is exactly the
broken slice. Of the **187** predictions made at 0.90 confidence or higher, **84 are wrong**,
an error rate of **0.449** inside the bin the model is surest about. Those 84 are 16.8% of the
entire batch: confident, well-formed, and wrong, the failures least likely to be double-checked.

## The receipt

`verify.py` re-derives the naive read, the full reliability table, the ECE, and the
high-confidence-error slice from `fixtures/calibration-guard/data/predictions.jsonl`,
importing the fixture's own naive read for the headline numbers, and never reading `results/`
back. The figures here are not asserted; they are what the script prints, or the script exits
non-zero. A tampered batch fails closed: flip one high-confidence error to correct and the
committed numbers stop reproducing.

## The judge layer, kept separate

A model's or reviewer's qualitative take on why the top bin is overconfident, training
imbalance, a shifted input distribution, a temperature that wants tuning, is useful and
belongs alongside this, but it is a hypothesis, not a measurement. It stays labeled and is
never mixed into the numbers above.

---

Built by ByteStack Labs. Every number reproduces from runnable code, or it does not ship.
