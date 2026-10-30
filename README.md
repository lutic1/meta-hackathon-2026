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
HEIC and PNG photos are rejected. Each photo is at most 20 MiB (its
1280 px downscale at most 2 MiB); a larger one is refused with 413
`upload_too_large` before anything is stored. (amended 29 Oct 2026, correct-course record)

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

## Cuts shipped

- **Cut 2, the Player profile as a file:** in Local mode the profile
  is `rooms/profiles/<name>.json` on your computer, read only after
  "Open profile file" (and once before a page's first write, so a
  write never drops results the file already holds) and downloaded
  with "Save profile file".
  In Hosted mode there is no `/profile/<name>` route, every Session start sends `Derived.fresh()`, and hosted rooms show the First-room welcome.

Cut 0 (no Build view) is not taken. It is a build-time switch,
`CUT_0` in `web/src/router.ts`, false in this build; set true, it drops
every link to the Build view and `#/build/<job_id>/view` resolves as an
unknown route, with no request to `/api/builds/<job_id>/view`. (amended 29 Oct 2026, correct-course record)

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
web/                       Vite + TypeScript + three client; builds into web/dist
tests/                     offline tests (conftest blocks every non-loopback socket)
scripts/check.sh           pre-push check and the whole CI job (--predeploy before modal deploy)
scripts/doctor.py          Mac and cloud environment check, stdlib only
.github/workflows/ci.yml   one job, check: runs scripts/check.sh on pushes to master
                           and keyframe/** branches and on pull requests
.github/workflows/deploy.yml  from the Actions tab or a push of a master commit to deploy/main,
                           deploy/main-warm or deploy/dev: check.sh --predeploy, then modal
                           deploy with the Modal token from the Actions secrets
.github/workflows/ops.yml  the nine ops actions (Hosted mode and ops below), from the Actions
                           tab or a push to ops/** of one .github/ops/request.json commit
                           on top of master
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

(amended 29 Oct 2026, correct-course record)

## Run it today

```bash
uv sync --locked
uv run python main.py chat "You are the Riddler. Greet the player."
uv run python main.py image "portrait of a wizard game master"
uv run pytest -q
uv run uvicorn src.api.app:app   # /api/* routes; serves web/dist at / once it is built
cd web && npm ci && npm run dev      # the dev server proxies /api/* to uvicorn on 127.0.0.1:8000
```

Python 3.13 and uv 0.11.32 or newer (`.python-version`, `uv.lock`);
Node 24 (`.nvmrc`, `web/package-lock.json`) for the web client. `python3
scripts/doctor.py` checks the machine.

Configuration: copy `.env.example` to `.env`. Playing needs no key: the
server starts without `MODEL_API_KEY`, builds a paid model adapter only
when a Build first calls it, and plays the stored rooms and the fixture
rooms `uv run scripts/load_fixtures.py` stores. `MODEL_PROVIDER=mock` runs
Builds on the deterministic mock (fixture work and the tests; its call
rows name the `mock` host, never a live one); `MODEL_PROVIDER=meta` runs
live Builds, and a Build whose provider setting is missing ends `failed`
naming it. Keys beyond the obvious: `MODEL_ARCHITECT`, `MODEL_RIDDLER`,
`MODEL_DRYRUN`, `MODEL_STORYTELLER` (story mode), `MODEL_TRICKSTER` and `MODEL_IMAGE` (per-role model ids,
default `muse-spark-1.3`, and `muse-image-1.0` for images);
`DEMO_PROPOSALS_DIR` (the folder of recorded and authored Trickster
proposals that `DEMO_TRICKSTER=scripted`, `authored` and `record` use;
unset, `proposals/` at the repo root); `HOSTED_SPEND_CAP_USD` (below). (amended 29 Oct 2026, correct-course record) See
[docs/MONDAY.md](docs/MONDAY.md) for the kickoff checklist (no paid call on Oct 26; the first live
calls run Tue Oct 27 behind the spend cap through `scripts/sit.py`).

## Contributing

Run `bash scripts/check.sh` before every push. It is the whole CI
job (`.github/workflows/ci.yml`, one job named `check`, on every push
to master or a `keyframe/**` branch and on every pull request): the privacy
check, `uv lock --check`, `uv sync --locked`, the offline `pytest`
suite, the wheel check for macOS arm64 and Linux x86_64, and, once
`web/` exists, `npm ci`, the Vite build and `tsc --noEmit`. CI holds
no secret and never deploys; `modal deploy` stays a manual step after
`bash scripts/check.sh --predeploy`, run by hand or through the second
workflow, `.github/workflows/deploy.yml` (started from the Actions tab with
the Environment and `MIN_CONTAINERS` as inputs, or by pushing a commit
master already carries to `deploy/main`, `deploy/main-warm` or
`deploy/dev`, with the Modal token from the repository's Actions
secrets), which runs the same ladder, then `modal deploy` and a
`GET /api/meta` smoke test. The push path exists by the owner's decision
of Oct 29; `.github/workflows/ops.yml` takes the same two paths, a push
to `ops/**` carrying its inputs in `.github/ops/request.json`.

## Hosted mode and ops

The judge URL runs `src/api/modal_app.py` on Modal: app `keyframe` with
`web` (one container of 20 concurrent inputs, `MIN_CONTAINERS` from
Settings), `run_build` (spawned per Build, timeout 900 s) and two Crons,
`ledger_export` (06:00 America/New_York) and `session_sweep` (minute 17
of every hour); Dicts `keyframe-jobs` (job state, `call:<job_id>`, the 20
`build:<n>` quota slots), `keyframe-sessions` and `keyframe-ledger`;
Volume `keyframe-data` at `/data` (`rooms/demo/`, `rooms/judge/`,
`rooms/deleted/`, `cache/`, `spend/`). The Secret `keyframe` must hold
`MODEL_API_KEY`, `FAL_KEY` and `ACCESS_CODE` (its `required_keys`, so a
deploy without one fails); `SPEND_CAP_USD` (the hosted allocation,
default 20) and `OPENAI_COMPATIBLE_API_KEY` are optional.
`HOSTED_SPEND_CAP_USD` in the local `.env` (default 20) is the hosted
allocation the local ledger export adds to the local one for the
combined ceiling, and must equal `SPEND_CAP_USD` in the hosted Secret;
the export records `local_cap_usd`, `hosted_cap_usd` and
`hosted_cap_source` (`env` or `default`) beside `ceiling_usd`.

The judge URL opens on a chooser of three cards on a dark stage (owner
decision Oct 29): Watch the demo, Play the sample room and Build your
own. The cards deal in with a spin; hover or focus brings one forward,
and choosing one turns it over to its back panel. Watch plays the demo
clip with controls (the landing's play-through clip, until a full demo
video is added as `FULL_DEMO_VIDEO` in `web/src/clip.ts`); Play shows the
Demo room, its hosts, how to play and "Play this room"; Build shows how
a room is built and the access-code Build. Play leads at rest ("No
upload needed") and is the first Tab stop; the Build card reads "Access
code required", and its back says "Judges: the code is in the
submission." Pause motion holds every loop, and under reduced motion the
cards crossfade instead of spinning. The wizards' cast, the Riddler's
sample page and How a room is built follow below the fold. Every hosted
screen carries one disclosure line, served by `GET /api/meta`: "Hints on
this site come exactly as the Riddler wrote them; no live model writes
them."

`.github/workflows/ops.yml` runs one action in the Modal Environment
chosen (`main` or `dev`, default `main`):

- `ledger-export`: `scripts/ledger.py export`, uploaded as a workflow
  artifact to download and commit; the workflow never commits.
- `purge-dry-run`, and `purge` only when `confirm` is the word `purge`:
  `scripts/purge_judge_rooms.py`. A listed id that is also a Demo room is
  kept (`kept <room_id>: a Demo room`) and gets no deletion record.
- `warm` and `cool`: the `keyframe/web` autoscaler's minimum set to 1 or
  0, then its settings printed; `autoscaler-settings` only prints them.
- `promote` (needs `room_id` and `room_name`): `scripts/promote_room.py`
  moves a Judge room to `rooms/demo/<room_id>/` under that name. It
  uploads the Demo copy, checks that it reads back, then removes the
  Judge copy; it writes no deletion record and leaves the claimed quota
  slot, Sessions and Cache entries alone. Run again once the Judge copy
  is gone, it reports the room already promoted. A Demo room is never a
  Judge room.
- `patch-demo-room` (needs `room_id`): `scripts/patch_demo_room.py`
  applies `ops/patches/<room_id>.json` (on master) to that Demo room's
  outlines, a dry run unless `confirm` is the word `patch`. Each entry
  replaces one Interactable's polygons, its `instances` and its `box`;
  an id that is not a Demo room, an unknown Interactable id, a polygon
  with fewer than 3 points, a point outside its photo's frame or a Room
  the validator refuses (rules 1 to 8) is refused with nothing written.
  Only `room.json` is rewritten, then read back; `job.json` keeps the
  pipeline's own output.
  Disclosure: on Thu Oct 29 this action hand-corrected the Demo room
  `room_01M61TZ74F0FP3X9HHTMXGTPB9` (ops run 6 the dry run, ops run 7 the
  write): the floor vent's outline moved onto the grille, and the throw
  pillows gained the pair at the sofa's corner bend that Puzzle 1's riddle
  points at. These two outlines are a hand correction, not a pipeline
  result; the Build view still shows the build as it ran.
- `story-demo-room` (needs `room_id`): `scripts/story_demo_room.py`
  writes the wizard story onto a Demo room built before story mode, a
  dry run unless `confirm` is the word `story`. It runs on Modal with the
  `keyframe` Secret and the story stage's own code: the storyteller's
  lines, sent back once when they break a line rule, else the fixed
  templates, the call cached and recorded in the hosted ledger under the
  room's job id. The dry run prints the brief, every line by slot, which
  path wrote it and the spend; a real run sets `Room.story` in
  `room.json` only, then reads it back. An id that is not a Demo room is
  refused; `job.json`, the photos, Sessions and the quota are untouched.
- `quota-probe`: `scripts/quota_probe.py` races separate processes for
  the 20 slot keys on an ephemeral Dict, never `keyframe-jobs`: 30
  claimers must win exactly 20 slots, then 8 must win exactly the last.

By push, the request is one commit on top of master that adds only
`.github/ops/request.json`, a JSON object of strings with the keys
`action`, `environment`, `room_id`, `room_name` and `confirm`
(`environment` defaults to `main`, the rest to empty), on a new
`ops/<action>-<n>` branch. The file never lands on master. (amended 29 Oct 2026, correct-course record)

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
