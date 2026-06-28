"""Build the tool-eval fixture: a committed calculator run transcript, scored by the naive
exact-match scorer, with the naive metric written to results/. Standard library only.

The transcript is fixed, not random: an agent run is a record, not a sample, so every
number regenerates identically. The fixture is openly synthetic and labeled as such.

Three of the eight runs are planted with one real flaw each:
  t1: correct value in dollar-and-comma format  -> naive marks it WRONG (false negative)
  t7: a wrong stored ground truth the agent matches -> naive marks it RIGHT (silent error)
  t8: a genuine arithmetic error                -> wrong by every measure
"""
import json, os
from scorer import naive_score

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data"); RES = os.path.join(HERE, "results")
os.makedirs(DATA, exist_ok=True); os.makedirs(RES, exist_ok=True)

RUNS = [
    {"id": "t1", "op": "add", "a": 8231.50, "b": 3383.22, "model_answer": "$11,614.72", "ground_truth": "11614.72"},
    {"id": "t2", "op": "add", "a": 540.00,  "b": 260.00,  "model_answer": "800.00",     "ground_truth": "800.00"},
    {"id": "t3", "op": "mul", "a": 12,      "b": 48.00,   "model_answer": "576.00",     "ground_truth": "576.00"},
    {"id": "t4", "op": "add", "a": 1200.00, "b": 350.50,  "model_answer": "1550.50",    "ground_truth": "1550.50"},
    {"id": "t5", "op": "mul", "a": 7,       "b": 90.00,   "model_answer": "630.00",     "ground_truth": "630.00"},
    {"id": "t6", "op": "add", "a": 99.99,   "b": 0.01,    "model_answer": "100.00",     "ground_truth": "100.00"},
    {"id": "t7", "op": "add", "a": 612.00,  "b": 631.00,  "model_answer": "1234.00",    "ground_truth": "1234.00"},
    {"id": "t8", "op": "mul", "a": 100,     "b": 7.00,    "model_answer": "690.00",     "ground_truth": "700.00"},
]

with open(os.path.join(DATA, "runs.jsonl"), "w") as f:
    for r in RUNS:
        f.write(json.dumps(r) + "\n")

naive_correct = sum(naive_score(r["model_answer"], r["ground_truth"]) for r in RUNS)
metrics = {"scorer": "naive_exact_match", "total": len(RUNS), "accuracy": round(naive_correct / len(RUNS), 4)}
with open(os.path.join(RES, "naive_metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)

print(json.dumps(metrics, indent=2))
