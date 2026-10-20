# Picture-Book Any Document

**Meta Global AI Developer Hackathon (Cerebral Valley), Oct 26 to Nov 4, 2026.**
**Theme: Build for Your World.**

Drop in a long PDF, up to 200 pages: a benefits plan, an immigration
guide, a medical leaflet. Get back a 20-panel illustrated picture book
that tells the same content as a story, in the reader's language, at
the reader's reading level, with one consistent guide character in
every panel. Built on Meta's models: Muse Spark reads the whole
document on its 1M-token context and plans the story, Muse Image
draws the panels.

Full product brief: [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md)

## Why

The documents that matter most are the ones people cannot read.
Dense, hundred-page documents go to low-literacy adults, newcomers in
a second language, and kids, and the information never reaches them.
A 20-panel picture book at roughly $0.01 per generated image costs
about 20 cents a book (pricing to be verified at kickoff) and can be
read by the people the original was supposedly written for.

## This repo

Scaffold for the hackathon build. Model access lands at kickoff on
Oct 26, so everything here runs against a mock provider today and
swaps to the Meta Model API on Monday with one client implementation.
The provider interface covers both halves of the product: `chat` for
document reading and story planning, `generate_image` for panels.

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
.venv/bin/python main.py chat "Plan a picture book about this document"
.venv/bin/python main.py image "guide character explaining a hospital visit, panel 1"
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

The scaffold in this repo was written ahead of kickoff as plumbing
and will be disclosed in the submission per the official rules
published at kickoff.
