# tool-eval receipt: the calculator that scored 75% twice

A tool evaluation, scored three ways from the same eight committed runs. Reproduce every
number from this directory with `python3 verify.py` (standard library only, no model, no
GPU). The fixture regenerates with `python3 generate.py` from `fixtures/tool-eval/`.

## What the naive scorer reports

The naive pattern scores a tool by exact string match of the agent's answer against a
stored ground truth. On this transcript that gives **0.750**, six of eight. One number,
and it hides two different mistakes the scorer is making.

## The aggregate is two errors wearing one number

Re-derive the answer from the raw operands, the real ground truth rather than the stored
one, and you also get **0.750**, six of eight. Same headline. But the two scorers fail on
different tasks:

| task | model answer | stored GT  | recomputed | naive | by recompute |
| ---- | ------------ | ---------- | ---------- | ----- | ------------ |
| t1   | `$11,614.72` | `11614.72` | 11614.72   | wrong | right        |
| t7   | `1234.00`    | `1234.00`  | 1243.00    | right | wrong        |
| t8   | `690.00`     | `700.00`   | 700.00     | wrong | wrong        |

- **t1 is a format-only mismatch.** The value is correct; the answer carries a dollar sign
  and a comma. The naive scorer marks a correct answer wrong. An eval false-negative.
- **t7 is a silent error.** The agent's answer matches the stored ground truth exactly, so
  the naive scorer passes it, but the stored ground truth is itself wrong (a transposed
  total: 1234 for 1243). The one tool failure that would actually move money is the one the
  score clears. An eval false-positive.
- **t8 is a true error**, wrong by both, correctly counted.

So the naive 0.750 flags a task that is fine (t1) and clears a task that is broken (t7).
Normalizing format alone lifts the number to **0.875** by recovering t1, but it still
cannot see t7, because t7's problem is not format, it is truth.

## The receipt

`verify.py` re-derives all three accuracies and the slice membership from
`fixtures/tool-eval/data/runs.jsonl`, importing the fixture's own naive scorer for the
naive number, and never reading `results/` back. The figures in this report are therefore
not asserted; they are what the script prints, or the script exits non-zero. A tampered
transcript fails closed: change one answer and the committed numbers stop reproducing.

## The judge layer, kept separate

A model's qualitative feedback on tool quality, naming, docs, error messages, is useful and
belongs alongside this, but it is an opinion, not a measurement. It stays labeled as a judge
layer and is never mixed into the reproducible number above.

---

Built by ByteStack Labs. Extends the failure class shown in Anthropic's tool-evaluation
cookbook with a reproducible verification layer. Every number reproduces from runnable code,
or it does not ship.
