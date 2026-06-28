# agent-reliability-receipts

Worked examples of the [agent-reliability](https://github.com/ByteStack-Labs/claude-plugins)
plugin for Claude Code, run against public fixtures, small programs we build on purpose to
fail in one real way, with the tool's own output saved as the receipt. The point of this
repo is simple: do not describe what the reliability skills do, show them doing it on
something anyone can clone and rerun.

## Why this exists

When the job moves from building to orchestrating, reviewers sit on top of AI agents
doing the execution, and the output outnumbers the eyes that can read it. Trust in that
work cannot rest on supervision, because no one is reading every line. It has to rest on
evidence that regenerates on demand. A receipt is that evidence: a number you can
re-derive from the raw data yourself, one that fails closed, erroring out rather than
quietly passing, when it does not reproduce.

A receipt is also a teaching artifact. In a team where agents do the execution, the
fastest way for anyone to build real understanding of a failure is to clone it, rerun
it, and watch it break on the slice that carries it, the group of cases sharing one
trait, like every invoice longer than a page. That is how the pipeline stays alive when
the code was not written by hand.

## How it is laid out

```
fixtures/   the small test programs above, each carrying one real flaw
receipts/   the tool's own output from running a skill against a fixture
```

A fixture is self-contained and openly synthetic, so we can publish it. A receipt is what
the plugin produced when pointed at that fixture: a verification script and a diagnostic
report, committed unedited, saved to the repo exactly as the tool produced it.

## Start here

`fixtures/invoice-extraction` is an extractor that scores a perfect 100% on its
evaluation, the controlled test set a model is graded on before launch. On production
input, the live data it must handle once deployed, that same extractor silently drops to
about 86% as soon as the format shifts. Two commands, no model and no GPU, run from the
repo root:

```
python3 fixtures/invoice-extraction/generate.py    # regenerate the data and metrics, seeded
python3 receipts/invoice-extraction/verify.py      # re-derive every number in the report
```

Then read `receipts/invoice-extraction/REPORT.md` for the autopsy the plugin wrote.
`verify.py` re-scores the raw data from scratch rather than trusting the saved metrics,
and exits non-zero if a single figure fails to reproduce, so the receipt checks itself.

## Why fixtures, not a live system

Every number here is reproducible because the fixtures are synthetic, seeded so the
random parts come out identical on every run, and run on the standard library with no
model and no GPU. A real client system cannot be published; a fixture can, which means
the method is auditable in the open even when the engagement behind it is not.

## What is here, and what is landing

| Skill                | Fixture                       | Receipt       |
| -------------------- | ----------------------------- | ------------- |
| **production-autopsy** | `invoice-extraction`          | shipped       |
| **tool-eval**          | `tool-eval`                   | shipped       |
| **calibration-guard**  | a confidence-emitting fixture | landing next  |
| **trajectory-eval**    | a multi-step agent fixture    | landing next  |

One airtight receipt now, the other two on the way. Until a skill's receipt is here,
its results are not yet reproducible and should not be cited as proven.

## License

MIT. See [LICENSE](LICENSE).

---

Built by Jesse Moses at [ByteStack Labs](https://bytestacklabs.com), production reliability
for AI and ML systems. Every number reproduces from runnable code, or it does not ship.
