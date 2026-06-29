"""Verification script for the calibration-guard receipt.

Standard library only. No model, no GPU, no network. Re-derives every number in REPORT.md
from the committed prediction batch in fixtures/calibration-guard/data/predictions.jsonl,
and shows that a healthy-looking accuracy and a high mean confidence hide a model that is
most confident exactly where it is least correct. Exits non-zero if any committed figure
fails to reproduce. Run from this directory:

    python3 verify.py

  naive read   : overall accuracy and mean confidence (what a dashboard shows)
  reliability  : per-confidence-bin accuracy vs confidence, and the gap between them
  ECE          : expected calibration error, the size of that gap averaged over the batch
  high-conf err: the predictions made at >= 0.9 confidence that are wrong

Every figure is recomputed here from the raw predictions; nothing is read back from
results/. If a number cannot be reproduced, the script exits non-zero.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_fixture(start):
    rel = os.path.join("fixtures", "calibration-guard", "data", "predictions.jsonl")
    d = start
    while True:
        if os.path.isfile(os.path.join(d, rel)):
            return os.path.join(d, "fixtures", "calibration-guard")
        parent = os.path.dirname(d)
        if parent == d:
            print("verify: could not locate fixtures/calibration-guard", file=sys.stderr)
            sys.exit(2)
        d = parent


FIX = find_fixture(HERE)
sys.path.insert(0, FIX)
from naive_read import naive_summary  # noqa: E402  # the system under test


def load():
    with open(os.path.join(FIX, "data", "predictions.jsonl")) as f:
        return [json.loads(line) for line in f]


def is_correct(r):
    return r["predicted"] == r["actual"]


def reliability(records, n_bins=10):
    """Per-bin (confidence, accuracy, gap, count). Equal-width bins over [0, 1)."""
    bins = {}
    for r in records:
        b = min(int(r["confidence"] * n_bins), n_bins - 1)
        bins.setdefault(b, []).append(r)
    table = []
    for b in sorted(bins):
        g = bins[b]; cnt = len(g)
        conf = sum(x["confidence"] for x in g) / cnt
        acc = sum(1 for x in g if is_correct(x)) / cnt
        table.append({"bin": b, "lo": b / n_bins, "hi": (b + 1) / n_bins,
                      "count": cnt, "conf": conf, "acc": acc, "gap": conf - acc})
    return table


def ece(records, n_bins=10):
    n = len(records)
    return sum(row["count"] / n * abs(row["gap"]) for row in reliability(records, n_bins))


def banner(t):
    print("\n" + "=" * 70); print(t); print("=" * 70)


def check(label, got, want):
    ok = got == want
    print(f"  [{'OK ' if ok else 'XX '}] {label}: {got!r}" + ("" if ok else f"  (expected {want!r})"))
    return ok


def main():
    ok = True
    recs = load()
    n = len(recs)

    # ---- 1. The naive read (looks healthy) -------------------------------
    banner("1. THE NAIVE READ  (what a dashboard shows)")
    summ = naive_summary(recs)
    print(f"  predictions        : {n}")
    print(f"  overall accuracy   : {summ['accuracy']:.4f}")
    print(f"  mean confidence    : {summ['mean_confidence']:.4f}")
    print("  Read on its own, healthy-looking accuracy beside high confidence. Ship it.")
    ok &= check("count", n, 500)
    ok &= check("overall accuracy", round(summ["accuracy"], 4), 0.686)
    ok &= check("mean confidence", round(summ["mean_confidence"], 4), 0.8251)

    # ---- 2. Reliability and ECE (where confidence is earned) -------------
    banner("2. RELIABILITY BY CONFIDENCE BIN  (is the confidence earned?)")
    table = reliability(recs)
    print(f"  {'bin':12}{'count':>7}{'avg_conf':>10}{'accuracy':>10}{'gap (conf-acc)':>16}")
    for row in table:
        print(f"  [{row['lo']:.1f},{row['hi']:.1f})    {row['count']:>5}   {row['conf']:>8.4f}  {row['acc']:>8.4f}   {row['gap']:>+12.4f}")
    e = ece(recs)
    print(f"  expected calibration error (ECE): {e:.4f}")
    top = [r for r in table if r["bin"] == 9][0]
    mids = [r for r in table if r["bin"] in (6, 7, 8)]
    print("  Calibrated through the mid bins, then the top bin claims ~0.94 and delivers ~0.55.")
    ok &= check("ECE", round(e, 4), 0.1614)
    ok &= check("top-bin [0.9,1.0) accuracy", round(top["acc"], 4), 0.5508)
    ok &= check("top-bin [0.9,1.0) confidence", round(top["conf"], 4), 0.9426)
    ok &= check("top-bin overconfidence gap > 0.30", round(top["gap"], 4) > 0.30, True)
    ok &= check("mid bins calibrated (all |gap| < 0.10)", all(abs(r["gap"]) < 0.10 for r in mids), True)

    # ---- 3. The slice that ships: high-confidence errors -----------------
    banner("3. HIGH-CONFIDENCE ERRORS  (most confident, least correct)")
    hi = [r for r in recs if r["confidence"] >= 0.9]
    hi_wrong = [r for r in hi if not is_correct(r)]
    rate = len(hi_wrong) / len(hi)
    print(f"  predictions at >= 0.90 confidence : {len(hi)}  ({len(hi)/n:.1%} of the batch)")
    print(f"  of those, wrong                   : {len(hi_wrong)}")
    print(f"  error rate inside the >=0.90 bin  : {rate:.4f}  (accuracy {1-rate:.4f})")
    print(f"  high-confidence errors as a share of ALL predictions: {len(hi_wrong)/n:.4f}")
    print("  These are the predictions an operator trusts most. They are wrong most.")
    ok &= check("high-confidence count (>=0.9)", len(hi), 187)
    ok &= check("high-confidence wrong", len(hi_wrong), 84)
    ok &= check("high-confidence error rate", round(rate, 4), 0.4492)

    # ---- 4. Verdict ------------------------------------------------------
    banner("VERDICT")
    if ok:
        print("  All checks reproduced. Overall accuracy 0.686 beside mean confidence 0.825")
        print("  reads as healthy, but ECE is 0.161: the model is well calibrated up to 0.9 and")
        print("  badly overconfident above it, claiming ~0.94 where it is right ~0.55. 84")
        print("  predictions made at >= 0.90 confidence are wrong. A single accuracy number")
        print("  never shows it; the calibration breaks exactly where trust is highest.")
    else:
        print("  ONE OR MORE CHECKS FAILED -- see XX lines above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
