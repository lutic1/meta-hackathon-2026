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

Story mode (owner decision Oct 29, the default) changes how a room
plays and how the Guide helps: the room opens on a five-beat story (the
Architect's welcome, the Trickster's trap, the Riddler's riddles, the
Guide's treasure chest, then the first riddle), the riddles come one at
a time, you walk around the room instead of picking photos from a strip,
and the Guide's help is a chest of 2 hints for the whole game that opens
only when you ask (no hint opens by itself; `HINT_POLICY=ladder` brings
the idle and wrong-attempt hints back). Each room's wizard lines are
written for that room by Muse Spark when it is built. (amended 30 Oct 2026, story mode)

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
.github/workflows/ops.yml  the ten ops actions (Hosted mode and ops below), from the Actions
                           tab or a push to ops/** of one .github/ops/request.json commit
                           on top of master (amended 30 Oct 2026, story mode: ten since
                           story-demo-room)
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
unset, `proposals/` at the repo root); `HOSTED_SPEND_CAP_USD` (below). (amended 29 Oct 2026, correct-course record)
`HINT_POLICY` (`chest`, the default: hints open only from the treasure
chest, `HINT_CAP` of them per Session, default 2; `ladder`: the idle and
wrong-attempt hints as before story mode) and `PROVIDER_STORYTELLER` with
`MODEL_STORYTELLER` for the story stage. (amended 30 Oct 2026, story mode) See
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
video is added as `FULL_DEMO_VIDEO` in `web/src/clip.ts`); since Oct 29
its back opens on two tabs, Tutorial first (the owner's own ten-second
generated video, slowed to 20 s with five burned-in captions, from "Snap
a room. Your photos become the game." to "Open the last lock and walk
out.") and Real play-through (that clip, muted, 1:48 at real speed,
re-recorded Oct 30 on story mode from the judge URL's Demo room; the
card's front loops riddle 1 of the same recording) (amended 30 Oct 2026, story mode); Play shows the
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

The first visit to the landing opens on a full-screen intro (owner
decision Oct 29): the owner's ten-second teaser plays once over the
page, muted with "Sound on", with "Skip intro" (and Escape); at its end
it holds the title with "Replay" and "Enter Keyframe" and enters by
itself after a four-second countdown unless Replay is chosen. Once it
has ended, been skipped or entered, this browser remembers it
(`keyframe.introSeen.v1` in local storage) and it never plays by itself
again; "Play intro" at the top right of the landing replays it. A deep
link (`#/play/...`, `#/build/...`) never shows it, and under reduced
motion it never plays by itself (shown on request, it has the native
controls and "Skip intro" sits top right). Every screen has a way back
to the start: the "Keyframe" wordmark in the top bar ("Keyframe, back to
the start"; on the Play screen through the Leave room confirmation); the
accepted access code opens the Capture screen on its own route,
`#/build-your-own`, with "Back to the three cards" (the browser's Back
works too); and the Build progress screen has "Back to the start", which
first asks "Your room keeps building. Leave this page?" while the job
runs. A new deploy's page replaces a stale one: `index.html` and the
unhashed files under `web/dist` are served `Cache-Control: no-cache`,
the hashed `/assets/` bundles `public, max-age=31536000, immutable`.
(amended 30 Oct 2026, story mode)

Playing a room (story mode, owner decision Oct 29). "Play this room"
starts a Session and opens the story intro on the Scene: five beats in
one speech box that holds one place (the Architect's welcome, which
thanks a player for their own photos and, in a Demo room, welcomes a
visitor to someone else's; the Trickster's trap, "Oh no, you seem to be
trapped!", with the lock's seal on the way out; the Riddler's entrance,
counting the riddles; the Guide lighting the treasure chest with the
Room's chest line, else "Stuck? I keep 2 hints for the whole house.
Choose your moment."; and the Riddler again on the first riddle's photo
with "Start looking"). It waits for the Scene's first photo (at most
4 s), plays once per Session start, and "Skip intro" ends it. When play
starts, the Trickster's bubble over the chest says "2 hints, for the
whole house. Spend them like they're mine." Then the riddles come one
at a time in the riddle note ("Riddle 1 of 4"), each
opening on its start photo with a line saying where it waits; you walk
around the room with Turn left and Turn right, the arrow keys or the
photo's edges, area by area, instead of a thumbnail strip, and "Show all
objects" still outlines everything in view. A Puzzle's evidence card
reaches the play screen only once its lock is open. The chest holds 2
hints for the whole game (`HINT_CAP`): each one asked opens the next
hint for the riddle you are on, an empty chest says so, and nothing
opens by itself (the Trickster's loosen and decoy are refused under the
chest). Solving the exit opens the door into daylight; "Step outside"
docks the escape sheet over the exit photo, which stays lit, with the
stats, the wizards' closing lines and Details (a cold reload of the
escape page, `#/done/<session>`, still opens on the older path, without
the lit door: a follow-up). Every line comes from
the room's own story (`Room.story`, served on the play projection), and
a room built before story mode, whose story is null, gets the fixed
template lines filled from its data. (amended 30 Oct 2026, story mode)

The generated story. A Build now runs a `story` stage after the Dry
run and before `scene` ("Writing the story" on the Build progress
screen): one `muse-spark-1.3` call (role `storyteller`, reasoning low)
over a brief of the room's name, area labels, counts and scenery labels,
never a solution, writes the intro beats, an opening and a solved line
per riddle and the closing lines. Each line must pass the story's line
rules (no solution, target, item, evidence or code word, the room's
name and area labels excepted; at most 160 characters; no exclamation
mark but the trap's; no filler; the chest line counts the hints, the
Riddler's entrance the riddles, the exit's solved line opens the way
out; the visitor's welcome thanks nobody for photos). A reply that fails
is sent back once with its reasons; then every passing line of the last
usable reply is kept and only refused slots take the fixed templates, so
the story never ends a Build. The lines are stored with the Room
(`story.json`, then `Room.story`), and the call is cached and priced in
the ledger like any Build call. (amended 30 Oct 2026, story mode)

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
  replaces one Interactable's polygons, its `instances` and its `box`,
  and an entry naming a `photo` moves the Interactable to that photo; a
  `story` object sets single lines of the stored story, each checked by
  the story stage's own line rules;
  an id that is not a Demo room, an unknown Interactable id or photo, a
  polygon with fewer than 3 points, a point outside its photo's frame or a Room
  the validator refuses (rules 1 to 8) is refused with nothing written.
  Only `room.json` is rewritten, then read back; `job.json` keeps the
  pipeline's own output.
  The patch file (amended 30 Oct 2026, story mode) is `{"reason": ...,
  "interactables": [{"id", "polygons", "photo"?}], "photos": [{"photo",
  "area", "pan"}], "story": {slot: line}}`: polygons in each photo's
  stored-JPEG pixels; `photos`, when present, names every photo of the
  Room exactly once and sets its area and left-to-right pan (one that
  misses a photo, names one twice or names one the Room lacks is
  refused); `story` takes any single-line slot of `Room.story`
  (`architect_welcome`, `architect_welcome_visitor`, `trickster_trap`,
  `riddler_entrance`, `guide_chest`, `trickster_closing`,
  `riddler_closing`, `guide_closing_no_hints`, `guide_closing_hints`;
  never the riddles), and a line the rules refuse, or any story line on a
  Room with no story, refuses the run with the slot and the reason. The
  dry run prints each entry's move (`photo 5 -> 2`), old and new bounds
  and polygon counts, or `unchanged`, each story slot's old and new line,
  or `unchanged`, and the validator verdict; it does not print the
  photos' areas and pans. The real run's one-line summary counts every
  entry of the patch as "re-outlined", unchanged ones included.
  Disclosure: on Thu Oct 29 this action hand-corrected the Demo room
  `room_01M61TZ74F0FP3X9HHTMXGTPB9` (ops run 6 the dry run, ops run 7 the
  write): the floor vent's outline moved onto the grille, and the throw
  pillows gained the pair at the sofa's corner bend that Puzzle 1's riddle
  points at. These two outlines are a hand correction, not a pipeline
  result; the Build view still shows the build as it ran.
  On Fri Oct 30 (amended 30 Oct 2026, story mode) it hand-edited the same
  room three more times: its photos' areas ("front hall", "lounge") and
  pans were hand-seeded and the left pillow pair retraced (ops run 8 the
  dry run, run 9 the write); the wall clock and the decorative tray moved
  to photo 2, where riddle 1 opens and both show, and the double front
  door to photo 0, where it shows head-on, each traced by hand on its new
  photo (run 12 the dry run, run 15 the write; the riddles now start on
  photos 2, 0, 5 and 0); and the Guide's chest line was set to the
  template line "Stuck? I keep two hints for the whole house. Choose your
  moment." because the model's line read as if the Guide were stuck (run
  19 the dry run, run 20 the write). These are hand corrections, not
  pipeline results. The patch file also moves the sectional sofa to
  photo 2 (amended 30 Oct 2026, owner report), traced by hand around the
  whole sectional with both pillow pairs on it, so riddle 3 is solved on
  the lounge view where the pillows are picked up; once applied the
  riddles start on photos 2, 0, 2 and 0.
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
  Since Oct 30 (amended 30 Oct 2026, story mode) the story keeps every
  line that passes and fills only the refused slots from the templates,
  and both runs print each refused attempt's reasons by slot with the
  refused line. A story write must wait until the deployed server knows
  every `Story` field it writes: the schema forbids extra fields, so a
  `room.json` carrying a field the running server's `Story` lacks (for
  example `architect_welcome_visitor` before `f478fe5` is deployed) fails
  to parse there and the room stops loading. Deploy first, then write.
  The Demo room's story was written this way on Fri Oct 30 (ops run 18,
  after deploy run 19 put `a2625b6` on the judge URL): 17 lines from
  model attempt 0 of `muse-spark-1.3`, the call served from the Cache
  that the dry run (run 17) filled. The lines are the model's, except the
  Guide's chest line, set by hand later (above).
- `quota-probe`: `scripts/quota_probe.py` races separate processes for
  the 20 slot keys on an ephemeral Dict, never `keyframe-jobs`: 30
  claimers must win exactly 20 slots, then 8 must win exactly the last.

By push, the request is one commit on top of master that adds only
`.github/ops/request.json`, a JSON object of strings with the keys
`action`, `environment`, `room_id`, `room_name` and `confirm`
(`environment` defaults to `main`, the rest to empty), on a new
`ops/<action>-<n>` branch. The file never lands on master. (amended 29 Oct 2026, correct-course record)
The request job refuses, before any Modal token is used, a commit whose
parent master does not carry or that changes any other file, an unknown
key, a value that is not a one-line string, an unknown action or
Environment, and, for `patch-demo-room` and `story-demo-room`, a
`room_id` that is not a room id. Every write runs as a dry run first,
then as the same request with the confirm word; anything else in
`confirm` is the dry run. For example, on `ops/patch-demo-<n>`:
`{"action": "patch-demo-room", "room_id": "room_01M61TZ74F0FP3X9HHTMXGTPB9"}`,
then on a new branch the same with `"confirm": "patch"`; on
`ops/story-demo-<n>`:
`{"action": "story-demo-room", "room_id": "room_01M61TZ74F0FP3X9HHTMXGTPB9"}`,
then the same with `"confirm": "story"`. One ops run per Environment
runs at a time. (amended 30 Oct 2026, story mode)

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
