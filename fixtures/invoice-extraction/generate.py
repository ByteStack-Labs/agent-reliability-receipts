"""Build the invoice-extraction fixture: synthetic data, run the fragile
extractor, score it, and write reproducible metrics. Standard library only.

Honest by construction, with the lessons of a prior audit baked in:
  - "Accuracy" is measured against ground truth and never relabeled as
    "confidence." No confidence signal is claimed, because none is measured.
  - The production format `shift_type` is PERSISTED on every record, so the
    per-slice analysis ("which kind of shift breaks it") is reconstructable
    from the saved artifacts.
  - random.seed is fixed, so every number below regenerates identically.
"""
import json, os, random
from extractor import extract, FIELDS

random.seed(42)
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data"); RES = os.path.join(HERE, "results")
os.makedirs(DATA, exist_ok=True); os.makedirs(RES, exist_ok=True)

N = 400
VENDORS = ["Acme Supply", "Globex", "Initech", "Umbrella Co", "Hooli", "Soylent"]
CLIENTS = ["Wayne Ent", "Stark Ind", "Wonka Inc", "Tyrell", "Cyberdyne", "Aperture"]
ITEMS = ["Steel bolts", "Copper wire", "Resin sheets", "Glass panels", "Alloy rods"]
TERMS = ["Net 30", "Net 60", "Net 15", "Due on receipt"]
CUR = ["USD", "EUR", "GBP"]
LABELS = {
    "invoice_id": "Invoice", "vendor": "Vendor", "client": "Client", "date": "Date",
    "item": "Item", "quantity": "Quantity", "unit_price": "Unit Price", "total": "Total",
    "currency": "Currency", "payment_terms": "Terms", "po_number": "PO",
}

def make_record(i):
    qty = random.randint(1, 500); price = round(random.uniform(1, 99), 2)
    return {
        "invoice_id": f"INV-{10000+i}", "vendor": random.choice(VENDORS),
        "client": random.choice(CLIENTS), "date": f"2026-0{random.randint(1,9)}-{random.randint(10,28)}",
        "item": random.choice(ITEMS), "quantity": str(qty), "unit_price": f"{price:.2f}",
        "total": f"{qty*price:.2f}", "currency": random.choice(CUR),
        "payment_terms": random.choice(TERMS), "po_number": f"PO-{random.randint(1000,9999)}",
    }

def fmt_eval(rec):
    # fixed order, one per line, "Label: value", what the extractor expects
    return "\n".join(f"{LABELS[f]}: {rec[f]}" for f in FIELDS)

def fmt_prod(rec, shift):
    fields = list(FIELDS)
    if shift in ("reorder", "mixed"):
        # swap one adjacent semantic pair, the realistic partial failure
        a = random.choice([("vendor","client"), ("payment_terms","po_number"), ("unit_price","total")])
        i, j = fields.index(a[0]), fields.index(a[1]); fields[i], fields[j] = fields[j], fields[i]
    delim = ": "
    if shift in ("delimiter", "mixed"): delim = random.choice([" | ", " => ", "\t", ","])
    if shift == "whitespace":
        return "\n".join(f"{LABELS[f]}:    {rec[f]}  " for f in fields)
    if shift == "compact":  # single line, breaks the one-per-line assumption hard
        return " | ".join(f"{LABELS[f]}: {rec[f]}" for f in fields)
    if shift == "verbose":  # decorative leading line shifts every position by one
        return "=== INVOICE ===\n" + "\n".join(f"{LABELS[f]}: {rec[f]}" for f in fields)
    return "\n".join(f"{LABELS[f]}{delim}{rec[f]}" for f in fields)

# weighted so most shifts are benign (order-preserving) and a minority break it,
# landing near a realistic ~10% silent error rate rather than a catastrophe
SHIFTS = (["delimiter"]*44 + ["whitespace"]*42 + ["reorder"]*8 +
          ["mixed"]*2 + ["compact"]*2 + ["verbose"]*2)

def score(pred, truth):
    correct = sum(1 for f in FIELDS if pred[f] == truth[f])
    return correct / len(FIELDS), int(correct == len(FIELDS))

def run(split, formatter):
    recs, rows = [], []
    for i in range(N):
        rec = make_record(i)
        shift = random.choice(SHIFTS) if split == "production" else None
        text = formatter(rec, shift) if split == "production" else formatter(rec)
        pred = extract(text)
        fa, em = score(pred, rec)
        row = {"field_accuracy": fa, "exact_match": em}
        if split == "production": row["shift_type"] = shift   # PERSISTED
        rows.append(row); recs.append({"text": text, "truth": rec, "shift_type": shift})
    # aggregate
    em_rate = sum(r["exact_match"] for r in rows) / N
    fa_mean = sum(r["field_accuracy"] for r in rows) / N
    metrics = {"split": split, "total": N, "exact_match_rate": round(em_rate, 4),
               "mean_field_accuracy": round(fa_mean, 4)}
    if split == "production":
        # per-slice: exact-match rate within each shift_type (the analysis a
        # dropped shift_type would have made impossible)
        by = {}
        for r in rows:
            s = r["shift_type"]; by.setdefault(s, []).append(r["exact_match"])
        metrics["exact_match_by_shift_type"] = {s: round(sum(v)/len(v), 3) for s, v in sorted(by.items())}
    with open(os.path.join(RES, f"{split}_metrics.json"), "w") as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(DATA, f"{split}.jsonl"), "w") as f:
        for rec in recs: f.write(json.dumps(rec) + "\n")
    return metrics

ev = run("eval", fmt_eval)
pr = run("production", fmt_prod)
print(json.dumps({"eval": ev, "production": pr}, indent=2))
