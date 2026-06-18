"""Verification script for the invoice-extraction production autopsy.

Standard library only. No model, no GPU, no network. Reproduces every number in
REPORT.md from the committed fixture artifacts, and runs the ablations that
isolate the root cause.

Run from anywhere:

    python3 receipts/invoice-extraction/verify.py

It does two things:
  1. VERIFY: re-scores the committed eval/production data with the fixture's own
     extractor and confirms the headline gap, the per-slice breakdown, and the
     per-field error attribution.
  2. ABLATE: constructs minimal inputs that hold everything constant except field
     position, proving the extractor reads layout (line position) rather than the
     label beside each value.

Every printed figure is recomputed here from the raw text + ground truth in
data/*.jsonl; nothing is read back from results/*.json. If a number cannot be
reproduced, it is not reported.
"""

import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(REPO, "fixtures", "invoice-extraction")
sys.path.insert(0, FIX)

from extractor import FIELDS, extract  # noqa: E402, # type: ignore

# The fixture builds eval-format text exactly this way (mirrors generate.fmt_eval
# / fmt_prod's verbose branch). Re-declared here so the ablations are self-
# contained and do not depend on private helpers in generate.py.
LABELS = {
    "invoice_id": "Invoice",
    "vendor": "Vendor",
    "client": "Client",
    "date": "Date",
    "item": "Item",
    "quantity": "Quantity",
    "unit_price": "Unit Price",
    "total": "Total",
    "currency": "Currency",
    "payment_terms": "Terms",
    "po_number": "PO",
}


def load(split):
    path = os.path.join(FIX, "data", f"{split}.jsonl")
    with open(path) as f:
        return [json.loads(line) for line in f]


def score(pred, truth):
    correct = sum(1 for f in FIELDS if pred[f] == truth[f])
    return correct / len(FIELDS), int(correct == len(FIELDS))


def eval_format(truth):
    return "\n".join(f"{LABELS[f]}: {truth[f]}" for f in FIELDS)


def banner(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def check(label, got, want):
    ok = got == want
    flag = "OK " if ok else "XX "
    print(f"  [{flag}] {label}: {got!r}" + ("" if ok else f"  (expected {want!r})"))
    return ok


def main():
    ok = True

    # ---- 1. Headline gap: eval vs production ------------------------------
    banner("1. HEADLINE GAP  (re-scored from raw text, not read from results/)")
    agg = {}
    for split in ("eval", "production"):
        recs = load(split)
        ems, fas = [], []
        for r in recs:
            pred = extract(r["text"])
            fa, em = score(pred, r["truth"])
            fas.append(fa)
            ems.append(em)
        em_rate = round(sum(ems) / len(ems), 4)
        fa_mean = round(sum(fas) / len(fas), 4)
        agg[split] = (em_rate, fa_mean, len(recs))
        print(
            f"  {split:11s} n={len(recs)}  exact_match={em_rate}  mean_field_accuracy={fa_mean}"
        )
    ok &= check("eval exact_match", agg["eval"][0], 1.0)
    ok &= check("eval mean_field_accuracy", agg["eval"][1], 1.0)
    ok &= check("production exact_match", agg["production"][0], 0.8625)
    ok &= check("production mean_field_accuracy", agg["production"][1], 0.9464)
    drop = round(agg["eval"][0] - agg["production"][0], 4)
    print(f"  --> aggregate exact-match drop: {drop} ({drop*100:.2f} points)")

    # ---- 2. The slice that hides in the aggregate ------------------------
    banner("2. PER-SLICE BREAKDOWN  (which shift_type drives the drop)")
    prod = load("production")
    by_em = defaultdict(list)
    counts = defaultdict(int)
    for r in prod:
        pred = extract(r["text"])
        _, em = score(pred, r["truth"])
        by_em[r["shift_type"]].append(em)
        counts[r["shift_type"]] += 1
    order_preserving = {"delimiter", "whitespace"}
    field_moving = {"reorder", "mixed", "compact", "verbose"}
    print(f"  {'shift_type':12s} {'n':>4s} {'exact_match':>12s} {'class':>16s}")
    moving_n = 0
    for s in sorted(by_em):
        rate = round(sum(by_em[s]) / len(by_em[s]), 3)
        cls = "order-preserving" if s in order_preserving else "FIELD-MOVING"
        if s in field_moving:
            moving_n += counts[s]
        print(f"  {s:12s} {counts[s]:>4d} {rate:>12.3f} {cls:>16s}")
        want = 1.0 if s in order_preserving else 0.0
        ok &= check(f"{s} exact_match", rate, want)
    print(
        f"  --> field-moving records: {moving_n}/400 = {moving_n/400:.4f} "
        f"== production error rate {1-agg['production'][0]:.4f}"
    )
    ok &= check(
        "field-moving fraction == error rate",
        round(moving_n / 400, 4),
        round(1 - agg["production"][0], 4),
    )

    # ---- 3. Silent failure: no signal separates right from wrong ---------
    banner("3. SILENT FAILURE  (how much wrong output carries no detectable signal)")
    wrong, silent, detectable = 0, 0, 0
    silent_by, detectable_by = defaultdict(int), defaultdict(int)
    for r in prod:
        pred = extract(r["text"])
        _, em = score(pred, r["truth"])
        if not em:
            wrong += 1
            # "silent" = all 11 fields populated, non-empty, no error raised:
            # indistinguishable from a correct record. "detectable" = at least
            # one empty field, which a downstream null-check would flag.
            if all(pred[f].strip() for f in FIELDS):
                silent += 1
                silent_by[r["shift_type"]] += 1
            else:
                detectable += 1
                detectable_by[r["shift_type"]] += 1
    print(f"  wrong records: {wrong}")
    print(
        f"  SILENT (well-formed, no signal): {silent}  by shift: {dict(sorted(silent_by.items()))}"
    )
    print(
        f"  detectable (empty field present): {detectable}  by shift: {dict(sorted(detectable_by.items()))}"
    )
    print(f"  --> silent error rate = {silent}/400 = {silent/400:.4f} of all traffic")
    print("  The silent share emits NO confidence signal and is structurally")
    print("  identical to a correct record. The only self-flagging failures are")
    print("  the compact ones, caught by accident (empty fields), not by design.")
    ok &= check("silent (well-formed-but-wrong) count", silent, 49)
    ok &= check("detectable (empty-field) count", detectable, 6)
    ok &= check(
        "detectable failures are exactly the compact slice",
        dict(detectable_by),
        {"compact": 6},
    )

    # ---- 4. ABLATION A: single adjacent swap, all else held constant -----
    banner(
        "4. ABLATION A  (hold content + delimiter + line-count constant; move 2 fields)"
    )
    truth = load("eval")[0]["truth"]
    base_text = eval_format(truth)
    base_pred = extract(base_text)
    _, base_em = score(base_pred, truth)
    print(f"  eval-format record: exact_match={base_em} (control passes)")
    # swap the adjacent semantic pair vendor<->client; identical otherwise
    swapped = list(FIELDS)
    i, j = swapped.index("vendor"), swapped.index("client")
    swapped[i], swapped[j] = swapped[j], swapped[i]
    swap_text = "\n".join(f"{LABELS[f]}: {truth[f]}" for f in swapped)
    swap_pred = extract(swap_text)
    sfa, sem = score(swap_pred, truth)
    changed = [f for f in FIELDS if swap_pred[f] != truth[f]]
    print(
        f"  one adjacent swap (vendor<->client): exact_match={sem} field_accuracy={sfa:.4f}"
    )
    print(f"  fields now wrong: {changed}")
    print(
        f"  extractor put '{swap_pred['vendor']}' in vendor (truth '{truth['vendor']}'),"
    )
    print(
        f"               '{swap_pred['client']}' in client (truth '{truth['client']}')"
    )
    ok &= check("control eval-format passes", base_em, 1)
    ok &= check(
        "single swap breaks exactly the 2 moved fields",
        sorted(changed),
        sorted(["vendor", "client"]),
    )
    ok &= check(
        "the two values are transposed (read by position, not label)",
        (swap_pred["vendor"], swap_pred["client"]),
        (truth["client"], truth["vendor"]),
    )

    # ---- 5. ABLATION B: one decorative leading line => off-by-one cascade -
    banner("5. ABLATION B  (one extra leading line; labels untouched, order untouched)")
    verbose_text = "=== INVOICE ===\n" + base_text
    vpred = extract(verbose_text)
    vfa, vem = score(vpred, truth)
    vwrong = [f for f in FIELDS if vpred[f] != truth[f]]
    print(f"  prepend one decorative line: exact_match={vem} field_accuracy={vfa:.4f}")
    print(
        f"  fields wrong: {len(vwrong)}/{len(FIELDS)} (a single line shifts every position)"
    )
    print(f"  invoice_id now reads the banner: {vpred['invoice_id']!r}")
    ok &= check("a single leading line corrupts every field", len(vwrong), len(FIELDS))
    ok &= check(
        "first field absorbs the decorative banner",
        vpred["invoice_id"],
        "=== INVOICE ===",
    )

    # ---- 6. Verdict ------------------------------------------------------
    banner("VERDICT")
    if ok:
        print("  All checks reproduced. Root cause confirmed by ablation:")
        print("  positional field assignment (reads line position, not the label).")
        print("  Evidence strength: DECISIVE for the mechanism (Ablation A isolates")
        print("  it to a single variable). Production error rate 13.75% is exact,")
        print("  not estimated.")
    else:
        print("  ONE OR MORE CHECKS FAILED — see XX lines above.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
