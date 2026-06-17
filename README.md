# agent-reliability-examples

Worked examples of the [agent-reliability](https://github.com/ByteStack-Labs/claude-plugins)
plugin for Claude Code, run against public fixtures, with the tool's own output
committed as the receipt. The point of this repo is simple: do not describe what
the reliability skills do, show them doing it on something anyone can clone and
rerun.

## How it is laid out

```
fixtures/   systems built to be diagnosed, each labeled as a teaching fixture
recipes/    the tool's output from running a skill against a fixture
```

A fixture is a small, self-contained, openly synthetic system with a real
reliability problem. A recipe is what the plugin produced when pointed at that
fixture: a verification script and a diagnostic report, committed unedited.

## Start here

`fixtures/invoice-extraction` is an extractor that scores 100% on evaluation and
silently drops to about 86% on format-shifted production input. Regenerate its
numbers with `python3 generate.py` (standard library only, seeded, no GPU), then
read `recipes/invoice-extraction` for the autopsy the plugin wrote.

## Why fixtures, not a live system

Every number here is reproducible by anyone, on any machine, with no model and no
hardware. That is the whole value of a receipt: you do not take the claim on
faith, you run it. The fixtures are deliberately constructed and say so plainly,
which is the honest way to demonstrate a tool, no hidden setup, no staged catch.

## The plugin

Install and docs: https://github.com/ByteStack-Labs/claude-plugins

Built by [Jesse Moses](https://github.com/Cre4T3Tiv3) at [ByteStack Labs](https://bytestacklabs.com).
