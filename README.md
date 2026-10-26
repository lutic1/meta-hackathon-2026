# Keyframe

**Meta Global AI Developer Hackathon (Cerebral Valley), Oct 26 to Nov 4, 2026.**
**Indie developer track.**

Keyframe turns any room into a playable escape room. Photograph a
room from a few angles, and two to three minutes later you are
playing an escape room built from your own objects. The game is run
by a council of Muse Spark wizard agents: the Architect finds the
objects with SAM 3.1 (and rebuilds them with SAM 3D Objects in
Tier 2), the Riddler writes and verifies the puzzle chain, the Guide
picks hint rungs from how you play (phrased by Llama 3.2 3B running
locally through Ollama; the player profile stays on your machine),
and the Trickster proposes bounded difficulty changes
mid-game. Muse Image paints the wizards and clue cards, Muse Voice
Transcribe lets you talk to them.

**Input:** 6 to 10 JPEG photos of one room. On an iPhone, set
Settings > Camera > Formats to Most Compatible before shooting;
HEIC and PNG photos are rejected.

Product brief (BMAD):
[docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/brief.md](docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/brief.md),
with the technical depth in
[addendum.md](docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/addendum.md)
beside it.

## Build tiers

- **Tier 1:** Myst-style photo scenes with mask hotspots, full wizard
  council. Playable end to end. Backup demo video by Sun Nov 1,
  2 PM; Saturday night is the early gate that alone unlocks Tier 2.
- **Tier 2:** Navigable Three.js room from SAM 3D Objects (hosted on
  fal.ai). Go or no-go gate on Mon Nov 2.
- **Tier 3 (stretch, never gating):** Gaussian-splatted photoreal
  shell.

## This repo

Model-access scaffold for the build. Model access lands at kickoff
on Oct 26, so everything here runs against a mock provider today and
swaps to the Meta Model API on Monday with one client
implementation. `chat` carries the Spark wizard calls,
`generate_image` carries Muse Image. The Three.js front end joins
this repo during the build week.

```
main.py                    demo entry point (chat / image)
src/config.py              settings from environment / .env
src/providers/base.py      the ModelProvider interface. Depend on this only.
src/providers/mock.py      deterministic fake, scriptable for tests and demos
src/providers/meta_api.py  Meta Model API stub, wire up Oct 26
tests/test_providers.py    smoke tests, all offline
docs/MONDAY.md             the Mon Oct 26 kickoff checklist
docs/planning-artifacts/   BMAD planning documents (product brief, then spec)
_bmad/                     BMAD Method v6 install (hackathon tooling)
.claude/skills/bmad-*/     BMAD skills (hackathon tooling)
.claude/skills/modal/      Modal's official skill (hackathon tooling)
.claude/skills/keyframe-*/ Keyframe dev skills (hackathon tooling)
                           these hackathon tooling paths, plus the Oct 26 cloud
                           hook (and .claude/settings.json only if story 1.2
                           creates it), are removed before submission (the repo
                           is public throughout; list:
                           docs/specs/spec-keyframe/delivery-plan.md,
                           Repo hygiene); other .claude/ configuration stays
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
today, `MODEL_PROVIDER=meta` once the API is wired on Mon Oct 26. See
[docs/MONDAY.md](docs/MONDAY.md) for the kickoff checklist (no paid call on Oct 26; the first live
calls run Tue Oct 27 behind the spend cap through `scripts/sit.py`).

## Key dates

- Oct 25, night: tag `pre-hackathon-baseline`, start CHANGELOG.md
- Oct 26: approval notifications by 9:00 AM ET, kickoff livestream,
  hackathon begins
- Sun Nov 1, 2 PM: Tier 1 backup demo video recorded (gate)
- Mon Nov 2: Tier 2 go or no-go (gate)
- Wed Nov 4, 9:00 PM ET: submissions due (submit in the morning)
- Nov 4 to 8: judging. Nov 9: closing ceremony, live finals, winners

## Pre-existing code note

Everything committed before the `pre-hackathon-baseline` tag was
written ahead of kickoff: the model-provider scaffold and tests,
the BMAD planning documents, and the BMAD tooling. None of it is
product code. It is disclosed here and in the submission; if the
Official Rules (published before Oct 26) exclude prior code, the
scaffold is small enough to be rewritten on Oct 26.
