"""Verification script for the tool-eval receipt.

Standard library only. No model, no GPU, no network. Re-derives every number in REPORT.md
from the committed run transcript in fixtures/tool-eval/data/runs.jsonl, scores it three
ways, and shows that a single naive accuracy hides two opposite errors. Run from this
directory:

    python3 verify.py

  naive     : exact string match vs the stored ground truth (the naive scorer under test)
  normalized: numeric value match (strip $, commas, whitespace, then compare the numbers)
  recompute : the agent's value vs the answer recomputed from the raw operands, i.e. the
              real ground truth rather than the stored one

Every printed figure is recomputed here from data/runs.jsonl; nothing is read back from
results/. If a number cannot be reproduced, the script exits non-zero.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def find_fixture(start):
    """Walk up to the repo root and locate the committed fixture. Rename-proof:
    independent of where the receipt is placed, as long as it lives in the same repo
    as fixtures/tool-eval/."""
    rel = os.path.join("fixtures", "tool-eval", "data", "runs.jsonl")
    d = start
    while True:
        if os.path.isfile(os.path.join(d, rel)):
            return os.path.join(d, "fixtures", "tool-eval")
        parent = os.path.dirname(d)
        if parent == d:
            print("verify: could not locate fixtures/tool-eval", file=sys.stderr)
            sys.exit(2)
        d = parent


FIX = find_fixture(HERE)
sys.path.insert(0, FIX)
from scorer import naive_score  # noqa: E402  # type: ignore  (the system under test)


def to_value(s):
    """Parse a money/number string to a float. '$11,614.72' -> 11614.72."""
    return round(float(re.sub(r"[^0-9.\-]", "", str(s))), 2)


def recompute(r):
    """The real ground truth: recomputed from the raw operands, not the stored string."""
    if r["op"] == "add":
        return round(r["a"] + r["b"], 2)
    if r["op"] == "mul":
        return round(r["a"] * r["b"], 2)
    raise ValueError("unknown op: " + r["op"])


def load():
    with open(os.path.join(FIX, "data", "runs.jsonl")) as f:
        return [json.loads(line) for line in f]


def banner(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def check(label, got, want):
    ok = got == want
    print(f"  [{'OK ' if ok else 'XX '}] {label}: {got!r}" + ("" if ok else f"  (expected {want!r})"))
    return ok


def main():
    ok = True
    runs = load()
    n = len(runs)

    # ---- 1. Three scorers, one transcript --------------------------------
    banner("1. THREE SCORERS, SAME RUNS  (re-derived from raw, not read from results/)")
    naive = norm = truth = 0
    rows = []
    for r in runs:
        mv, gv, cv = to_value(r["model_answer"]), to_value(r["ground_truth"]), recompute(r)
        nv = naive_score(r["model_answer"], r["ground_truth"])
        nm, tv = int(mv == gv), int(mv == cv)
        naive += nv; norm += nm; truth += tv
        rows.append((r["id"], r["model_answer"], r["ground_truth"], cv, nv, nm, tv))
    naive_acc, norm_acc, truth_acc = round(naive / n, 4), round(norm / n, 4), round(truth / n, 4)
    print(f"  {'task':5}{'model':>12}{'stored':>11}{'recomputed':>12}   naive norm truth")
    for x in rows:
        print(f"  {x[0]:5}{x[1]:>12}{x[2]:>11}{x[3]:>12.2f}      {x[4]:>3}  {x[5]:>3}  {x[6]:>3}")
    print(f"  naive exact-match : {naive_acc:.3f}")
    print(f"  normalized value  : {norm_acc:.3f}")
    print(f"  recompute (truth) : {truth_acc:.3f}")
    ok &= check("naive exact-match accuracy", naive_acc, 0.75)
    ok &= check("normalized value accuracy", norm_acc, 0.875)
    ok &= check("recompute (true) accuracy", truth_acc, 0.75)

    # ---- 2. Same headline, opposite errors -------------------------------
    banner("2. SAME HEADLINE, OPPOSITE ERRORS  (which tasks each scorer fails)")
    naive_wrong = sorted(r["id"] for r in runs if not naive_score(r["model_answer"], r["ground_truth"]))
    truth_wrong = sorted(r["id"] for r in runs if to_value(r["model_answer"]) != recompute(r))
    format_only = sorted(r["id"] for r in runs
                         if not naive_score(r["model_answer"], r["ground_truth"])
                         and to_value(r["model_answer"]) == recompute(r))
    silent_wrong = sorted(r["id"] for r in runs
                          if naive_score(r["model_answer"], r["ground_truth"])
                          and to_value(r["model_answer"]) != recompute(r))
    true_errors = sorted(r["id"] for r in runs
                         if not naive_score(r["model_answer"], r["ground_truth"])
                         and to_value(r["model_answer"]) != recompute(r))
    print(f"  naive flags wrong     : {naive_wrong}")
    print(f"  recompute flags wrong : {truth_wrong}")
    print(f"  format-only mismatch (correct value, naive marks wrong) : {format_only}")
    print(f"  silent wrong (naive marks right, value is wrong)        : {silent_wrong}")
    print(f"  true errors (wrong by both)                             : {true_errors}")
    print("  Naive and recompute both report 0.750, but disagree on which failed:")
    print("  naive flags t1, which is correct, and clears t7, which is wrong.")
    ok &= check("format-only mismatches", format_only, ["t1"])
    ok &= check("silent-wrong set", silent_wrong, ["t7"])
    ok &= check("true errors", true_errors, ["t8"])
    ok &= check("naive and recompute disagree on the failure set", naive_wrong != truth_wrong, True)

    # ---- 3. Verdict ------------------------------------------------------
    banner("VERDICT")
    if ok:
        print("  All checks reproduced. A single naive accuracy (0.750) concealed both a")
        print("  format false-negative (t1, a correct value marked wrong) and a silent error")
        print("  (t7, a wrong value marked right against a wrong stored ground truth). The")
        print("  value-correct number is 0.875; the true number by recompute is 0.750, on a")
        print("  different failure set than the naive scorer reports.")
    else:
        print("  ONE OR MORE CHECKS FAILED -- see XX lines above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
