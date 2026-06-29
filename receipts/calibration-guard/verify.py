"""Verification script for the calibration-guard receipt.

Standard library only. No model, no GPU, no network. Re-derives every number in REPORT.md
from the two committed batches in fixtures/calibration-guard/data/ (eval.jsonl and
production.jsonl), and shows that calibration is a property of a distribution: a model that
is well calibrated on its evaluation set comes apart on a shifted production set, and a
confidence threshold tuned on eval stops protecting, while an independent second signal
still flags the failures. Exits non-zero if any committed figure fails to reproduce. Run
from this directory:

    python3 verify.py

  naive read   : per-split accuracy and mean confidence (what a dashboard shows)
  inversion    : ECE and confidence-separation on eval vs production
  detector     : an independent verifier disagreeing with confidence, vs a stale
                 confidence threshold, scored on production errors

Every figure is recomputed here from the raw predictions; nothing is read back from
results/. If a number cannot be reproduced, the script exits non-zero.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DISAGREE_TH = 0.25     # confidence - verifier_score at or above this = the two signals disagree
ABSTAIN_TH = 0.80      # the eval-tuned rule: abstain when stated confidence < this


def find_fixture(start):
    rel = os.path.join("fixtures", "calibration-guard", "data", "eval.jsonl")
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


def load(split):
    with open(os.path.join(FIX, "data", f"{split}.jsonl")) as f:
        return [json.loads(line) for line in f]


def correct(r):
    return r["predicted"] == r["actual"]


def reliability(records, n_bins=10):
    bins = {}
    for r in records:
        b = min(int(r["confidence"] * n_bins), n_bins - 1)
        bins.setdefault(b, []).append(r)
    out = []
    for b in sorted(bins):
        g = bins[b]; cnt = len(g)
        conf = sum(x["confidence"] for x in g) / cnt
        acc = sum(1 for x in g if correct(x)) / cnt
        out.append({"bin": b, "count": cnt, "conf": conf, "acc": acc, "gap": conf - acc})
    return out


def ece(records, n_bins=10):
    n = len(records)
    return sum(row["count"] / n * abs(row["gap"]) for row in reliability(records, n_bins))


def conf_separation(records):
    """Mean confidence on correct predictions minus mean confidence on wrong ones.
    Positive means confidence tells right from wrong; negative means it is inverted."""
    cr = [r["confidence"] for r in records if correct(r)]
    wr = [r["confidence"] for r in records if not correct(r)]
    return sum(cr) / len(cr) - sum(wr) / len(wr)


def hi_conf(records, thr=0.9):
    hi = [r for r in records if r["confidence"] >= thr]
    wrong = [r for r in hi if not correct(r)]
    return len(hi), len(wrong)


def abstain_recall(records, thr):
    """Share of this split's errors that a 'confidence < thr' rule would catch."""
    err = [r for r in records if not correct(r)]
    return sum(1 for r in err if r["confidence"] < thr) / len(err)


def banner(t):
    print("\n" + "=" * 70); print(t); print("=" * 70)


def check(label, got, want):
    ok = got == want
    print(f"  [{'OK ' if ok else 'XX '}] {label}: {got!r}" + ("" if ok else f"  (expected {want!r})"))
    return ok


def main():
    ok = True
    E = load("eval"); P = load("production")

    # ---- 1. The naive read, per split (looks healthy either way) ---------
    banner("1. THE NAIVE READ, PER SPLIT  (what a dashboard shows)")
    se = naive_summary(E); sp = naive_summary(P)
    print(f"  eval        : accuracy {se['accuracy']:.4f}   mean confidence {se['mean_confidence']:.4f}")
    print(f"  production  : accuracy {sp['accuracy']:.4f}   mean confidence {sp['mean_confidence']:.4f}")
    print("  Accuracy slips and confidence RISES. Confidence moves the wrong way; the naive")
    print("  read cannot say why, or which predictions to stop trusting.")
    ok &= check("eval count", len(E), 500)
    ok &= check("production count", len(P), 500)
    ok &= check("eval accuracy", round(se["accuracy"], 4), 0.772)
    ok &= check("eval mean confidence", round(se["mean_confidence"], 4), 0.7687)
    ok &= check("production accuracy", round(sp["accuracy"], 4), 0.584)
    ok &= check("production mean confidence", round(sp["mean_confidence"], 4), 0.8297)

    # ---- 2. Calibration inverts under shift ------------------------------
    banner("2. CALIBRATION INVERTS UNDER SHIFT  (not just degrades)")
    ece_e, ece_p = ece(E), ece(P)
    sep_e, sep_p = conf_separation(E), conf_separation(P)
    he_n, he_w = hi_conf(E); hp_n, hp_w = hi_conf(P)
    print(f"  expected calibration error : eval {ece_e:.4f}   production {ece_p:.4f}   ({ece_p/ece_e:.1f}x)")
    print(f"  confidence(correct) - confidence(wrong): eval {sep_e:+.4f}   production {sep_p:+.4f}")
    print(f"    on eval, confidence is higher on right answers; on production the sign flips,")
    print(f"    wrong answers come back MORE confident than right ones.")
    print(f"  high-confidence (>=0.9) error rate: eval {he_w/he_n:.4f} ({he_w}/{he_n})   "
          f"production {hp_w/hp_n:.4f} ({hp_w}/{hp_n})")
    ok &= check("eval ECE", round(ece_e, 4), 0.0245)
    ok &= check("production ECE", round(ece_p, 4), 0.2572)
    ok &= check("production ECE is >10x eval ECE", ece_p > 10 * ece_e, True)
    ok &= check("eval confidence separation", round(sep_e, 4), 0.0839)
    ok &= check("production confidence separation", round(sep_p, 4), -0.0408)
    ok &= check("separation inverts sign (eval>0, prod<0)", sep_e > 0 and sep_p < 0, True)
    ok &= check("eval high-conf error rate", round(he_w / he_n, 4), 0.0444)
    ok &= check("production high-conf error rate", round(hp_w / hp_n, 4), 0.5507)

    # ---- 3. One signal fails, two signals hold ---------------------------
    banner("3. THE DETECTOR  (one signal fails under shift, an independent second holds)")
    # 3a. the eval-tuned confidence rule collapses under shift
    ar_e, ar_p = abstain_recall(E, ABSTAIN_TH), abstain_recall(P, ABSTAIN_TH)
    print(f"  eval-tuned rule  (abstain if confidence < {ABSTAIN_TH}):")
    print(f"    catches {ar_e:.4f} of eval errors, but only {ar_p:.4f} of production errors.")
    print(f"    Tuned on eval, it silently stops protecting once the distribution moves.")
    # 3b. the independent disagreement rule, scored on production errors
    flagged = [r for r in P if r["confidence"] - r["verifier_score"] >= DISAGREE_TH]
    fl_wrong = [r for r in flagged if not correct(r)]
    prod_err = [r for r in P if not correct(r)]
    prec = len(fl_wrong) / len(flagged)
    rec = len(fl_wrong) / len(prod_err)
    eval_fp = sum(1 for r in E if r["confidence"] - r["verifier_score"] >= DISAGREE_TH)
    eval_max = max(r["confidence"] - r["verifier_score"] for r in E)
    print(f"  independent rule (flag if confidence - verifier_score >= {DISAGREE_TH}):")
    print(f"    flags {len(flagged)} production cases; {len(fl_wrong)} are wrong "
          f"(precision {prec:.4f}), catching {rec:.4f} of all production errors.")
    print(f"    fires on the eval batch {eval_fp} times (max eval disagreement {eval_max:.4f}).")
    print(f"  Under shift the stale confidence rule recovers {ar_p:.4f} of errors; the")
    print(f"  independent signal recovers {rec:.4f}, with no false alarms in-distribution.")
    ok &= check("eval-tuned rule recall on eval errors", round(ar_e, 4), 0.7719)
    ok &= check("eval-tuned rule recall on production errors", round(ar_p, 4), 0.2837)
    ok &= check("disagreement rule flagged count", len(flagged), 197)
    ok &= check("disagreement rule precision vs error", round(prec, 4), 0.6802)
    ok &= check("disagreement rule recall vs production errors", round(rec, 4), 0.6442)
    ok &= check("disagreement rule false positives on eval", eval_fp, 0)
    ok &= check("independent rule beats stale rule under shift", rec > ar_p, True)

    # ---- 4. Verdict ------------------------------------------------------
    banner("VERDICT")
    if ok:
        print("  All checks reproduced. The same classifier is well calibrated on eval")
        print("  (ECE 0.0245) and badly miscalibrated on a shifted production batch")
        print("  (ECE 0.2572), where confidence inverts: wrong answers come back more")
        print("  confident than right ones, and the >=0.9 error rate runs 0.044 -> 0.551.")
        print("  A confidence threshold tuned on eval recovers only 0.28 of production")
        print("  errors; an independent verifier disagreeing with confidence recovers 0.64,")
        print("  and never fires in-distribution. Calibration is a property of a")
        print("  distribution, so it must be measured on both, and protected with a signal")
        print("  the model does not control.")
    else:
        print("  ONE OR MORE CHECKS FAILED -- see XX lines above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
