# agent-reliability-receipts

Worked examples of the [agent-reliability](https://github.com/ByteStack-Labs/claude-plugins)
plugin for Claude Code, run against public fixtures, with the tool's own output
committed as the receipt. The point of this repo is simple: do not describe what
the reliability skills do, show them doing it on something anyone can clone and
rerun.

## How it is laid out

```
fixtures/   systems built to be diagnosed, each labeled as a teaching fixture
receipts/   the tool's own output from running a skill against a fixture
```

A fixture is a small, self-contained, openly synthetic system with a real
reliability problem. A receipt is what the plugin produced when pointed at that
fixture: a verification script and a diagnostic report, committed unedited.

## Start here

`fixtures/invoice-extraction` is an extractor that scores 100% on evaluation and
silently drops to about 86% on format-shifted production input. Two commands, no
model and no GPU, run from the repo root:

```
python3 fixtures/invoice-extraction/generate.py    # regenerate the data and metrics, seeded
python3 receipts/invoice-extraction/verify.py      # re-derive every number in the report
```

Then read `receipts/invoice-extraction/REPORT.md` for the autopsy the plugin
wrote. `verify.py` re-scores the raw data from scratch rather than trusting the
committed metrics, and exits non-zero if a single figure fails to reproduce, so
the receipt checks itself.

## Why fixtures, not a live system

Every number here is reproducible by anyone, on any machine, with no model and no
hardware. That is the whole value of a receipt: you do not take the claim on
faith, you run it. The fixtures are deliberately constructed and say so plainly,
which is the honest way to demonstrate a tool, no hidden setup, no staged catch.

## What is here, and what is landing

| Skill | Fixture | Receipt |
| --- | --- | --- |
| production-autopsy | invoice-extraction | shipped |
| calibration-guard | a confidence-emitting fixture | landing next |
| trajectory-eval | a multi-step agent fixture | landing next |

One airtight receipt now, the other two on the way. Each lands the same way: the
skill run against a public fixture, its output committed unedited.

## The plugin

Install and docs: https://github.com/ByteStack-Labs/claude-plugins

Built by [Jesse Moses](https://github.com/Cre4T3Tiv3) at [ByteStack Labs](https://bytestacklabs.com).
