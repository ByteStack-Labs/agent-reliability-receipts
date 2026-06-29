"""Build the calibration-guard fixture: a committed batch of confident binary-classifier
predictions, scored by the naive reliability read, with that naive summary written to
results/. Standard library only.

Seeded so the random parts come out identical on every run. The fixture is openly
synthetic and labeled as such. It is built with one real flaw: most predictions are
roughly calibrated, but a concentrated pocket is highly confident and usually wrong, so
the model is most confident exactly where it is least correct. The naive read (high
accuracy, high mean confidence) cannot see that pocket.
"""
import json, os, random
from naive_read import naive_summary

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data"); RES = os.path.join(HERE, "results")
os.makedirs(DATA, exist_ok=True); os.makedirs(RES, exist_ok=True)

random.seed(42)
N = 500
records = []
for i in range(N):
    if random.random() < 0.82:
        # well-behaved: stated confidence roughly matches probability of being correct
        c = round(random.uniform(0.60, 0.98), 2)
        p_correct = c
    else:
        # the miscalibrated pocket: very high confidence, usually wrong
        c = round(random.uniform(0.90, 0.99), 2)
        p_correct = 0.30
    correct = random.random() < p_correct
    actual = random.randint(0, 1)
    predicted = actual if correct else 1 - actual
    records.append({"id": f"p{i:03d}", "confidence": c, "predicted": predicted, "actual": actual})

with open(os.path.join(DATA, "predictions.jsonl"), "w") as f:
    for r in records:
        f.write(json.dumps(r) + "\n")

metrics = naive_summary(records)
with open(os.path.join(RES, "naive_metrics.json"), "w") as f:
    json.dump(metrics, f, indent=2)

print(json.dumps(metrics, indent=2))
