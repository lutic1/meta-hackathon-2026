# Rashomon on Meta Models

**Meta Global AI Developer Hackathon (Cerebral Valley), Oct 26 to Nov 4, 2026.**
**Startup track. Theme: Build for Your World.**

Coding agents report work they did not do. Rashomon is an independent
execution recorder that captures what an agent actually did (commands,
exit codes, file writes, tool calls, tests) and flags every claim in
the agent's report that the evidence does not support. This build puts
Meta's models (Muse Spark series, via the Meta Model API) on the
judgment layer: claim extraction, adjudication against the captured
timeline, and live verification while the agent is still working.

Full product brief: [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md)

## Why

In a benchmark of 100 runs across 20 adversarial tasks, agents filed
13 reports the captured evidence did not support. The most common
pattern was the hidden workaround: a fake script standing in for real
work, a no-op stub, invented data. Rashomon stores structure, not
content, so the audit trail does not become a privacy problem of its
own.

## This repo

Scaffold for the hackathon build. Model access lands at kickoff on
Oct 26, so everything here runs against a mock provider today and
swaps to the Meta Model API on Monday with one client implementation.

```
main.py                    demo entry point (chat / image)
PRODUCT_BRIEF.md           what we are building and why
src/config.py              settings from environment / .env
src/providers/base.py      the ModelProvider interface. Depend on this only.
src/providers/mock.py      deterministic fake, scriptable for tests and demos
src/providers/meta_api.py  Meta Model API stub, wire up Oct 26
tests/test_providers.py    smoke tests, all offline
docs/MONDAY.md             the Oct 26 plug-in checklist
```

## Run it today

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py chat "Summarize why agent verification matters"
.venv/bin/python main.py image "a red convertible on a coastal road"
.venv/bin/python -m pytest
```

Configuration: copy `.env.example` to `.env`. `MODEL_PROVIDER=mock`
today, `MODEL_PROVIDER=meta` once the API is wired. See
[docs/MONDAY.md](docs/MONDAY.md) for the plug-in steps.

## Key dates

- Oct 26, 1:00 PM ET: kickoff livestream, hackathon begins
- Oct 27 to Nov 4: live workshops, office hours on Discord
- Nov 1: MVP freeze (per product brief)
- Nov 4, 9:00 PM ET: submissions due
- Nov 9: closing ceremony, live finals, winners announced

## Pre-existing code note

Rashomon predates this hackathon and is the author's own project; the
scaffold in this repo was written ahead of kickoff as plumbing. Both
will be disclosed in the submission per the official rules published
at kickoff.
