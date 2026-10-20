# Meta Global AI Developer Hackathon 2026

Project scaffold for the Meta Global AI Developer Hackathon (Cerebral
Valley), Oct 26 to Nov 4, 2026. Virtual, submissions due Nov 4,
9:00 PM ET. $1M prize pool across indie and startup tracks.

## The idea behind this scaffold

Model access (Muse Spark series, Muse Image, SAM 3.1 through the Meta
Model API) only lands at kickoff on Oct 26. Everything else can be
built now. So all model calls go through one interface
(`src/providers/base.py`), and the app never knows which backend is
behind it:

- `MockProvider` works today. No keys, no network, deterministic.
- `MetaModelProvider` is a stub with the wiring points marked. Filling
  it in on Monday is the only code change needed to go live.

## Run it today

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python main.py chat "Summarize why agent verification matters"
.venv/bin/python main.py image "a red convertible on a coastal road"
.venv/bin/python -m pytest
```

All 7 tests pass against the mock, including two that pin down the
Meta stub's behavior (raises without a key, raises NotImplementedError
with one) so Monday's wiring has a contract to satisfy.

## Layout

```
main.py                  demo entry point (chat / image)
src/config.py            settings from environment / .env
src/providers/base.py    the ModelProvider interface. Depend on this only.
src/providers/mock.py    deterministic fake, scriptable for tests and demos
src/providers/meta_api.py  Meta Model API stub, wire up Oct 26
tests/test_providers.py  smoke tests, all offline
docs/MONDAY.md           the Oct 26 plug-in checklist
```

## Configuration

Copy `.env.example` to `.env`. `MODEL_PROVIDER=mock` today,
`MODEL_PROVIDER=meta` once the API is wired. Model ids can be
overridden with `CHAT_MODEL` and `IMAGE_MODEL`.

## Pre-existing code note

This scaffold was written before the hackathon start on purpose: it is
plumbing, not the project. Hackathon rules (published at kickoff) will
govern what pre-existing code is allowed; standard practice is that
your own prior code is fine when disclosed. If this project builds on
Rashomon, disclose that in the submission.

## Key dates

- Oct 26, 1:00 PM ET: kickoff livestream, hackathon begins
- Oct 27 to Nov 4: live workshops, office hours on Discord
- Nov 4, 9:00 PM ET: submissions due
- Nov 9: closing ceremony, live finals, winners announced
