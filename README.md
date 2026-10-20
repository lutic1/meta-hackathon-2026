# Keyframe

**Meta Global AI Developer Hackathon (Cerebral Valley), Oct 26 to Nov 4, 2026.**
**Indie developer track.**

Keyframe turns any room into a playable 3D escape room. Photograph a
room from a few angles, and about two minutes later you are playing
an escape room inside a 3D version of it, with puzzles built from
your own objects. The game is run by a council of Muse Spark wizard
agents: the Architect rebuilds the room with SAM 3.1 and SAM 3D
Objects, the Riddler writes the puzzle chain, the Guide learns how
you play and hints accordingly (on Muse Glimmer, locally, so play
data never leaves your machine), and the Trickster adjusts
difficulty mid-game. Muse Image paints the wizards and clue cards,
Muse Voice Transcribe lets you talk to them.

Full product brief: [PRODUCT_BRIEF.md](PRODUCT_BRIEF.md)

## Build tiers

- **Tier 1:** Myst-style photo scenes with hotspots, full wizard
  council. Playable end to end. Demo-complete by Day 4 (Oct 30).
- **Tier 2:** Navigable Three.js room from the SAM 3D pipeline.
  Go or no-go gate on Day 7 (Nov 2).
- **Tier 3 (stretch):** Gaussian-splatted photoreal shell.

## This repo

Model-access scaffold for the build. Model access lands at kickoff
on Oct 26, so everything here runs against a mock provider today and
swaps to the Meta Model API on Monday with one client
implementation. `chat` carries the Spark wizard calls,
`generate_image` carries Muse Image. The Three.js front end joins
this repo during the build week.

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
.venv/bin/python main.py chat "You are the Riddler. Greet the player."
.venv/bin/python main.py image "portrait of a wizard game master"
.venv/bin/python -m pytest
```

Configuration: copy `.env.example` to `.env`. `MODEL_PROVIDER=mock`
today, `MODEL_PROVIDER=meta` once the API is wired. See
[docs/MONDAY.md](docs/MONDAY.md) for the plug-in steps.

## Key dates

- Oct 26, 1:00 PM ET: kickoff livestream, hackathon begins
- Oct 30: Tier 1 backup demo video recorded (gate)
- Nov 2: Tier 2 go or no-go (gate)
- Nov 4, 9:00 PM ET: submissions due (submit early in the day)
- Nov 9: closing ceremony, live finals, winners announced

## Pre-existing code note

The scaffold in this repo was written ahead of kickoff as plumbing
and will be disclosed in the submission per the official rules
published at kickoff.
