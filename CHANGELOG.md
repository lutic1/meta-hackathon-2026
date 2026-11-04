# Changelog

All dated entries are in ET. Entries from Mon Oct 26 on are event-period work; the `pre-hackathon-baseline` tag marks the state before.

## Before Oct 26 (baseline): provider interface, mock provider, Meta API stub, tests. No front end, no model calls.

- About 400 lines of Python: `src/providers` (`ModelProvider` ABC, mock provider, Meta Model API stub), `src/config.py` (`Settings` from env), `main.py` smoke CLI, `tests/test_providers.py` (offline). Planning package under `docs/` (brief, spec, PRD, UX contract, architecture spine, epics, sprint status, SIT and UAT records).

## Mon Oct 26: the 97 stories built against the mock provider, one epic at a time. Nothing paid.

- Foundation and domain: the scaffold ratified (pins, `Settings`, the Meta adapter fixes, the boundary tests); Schema v1 and every API model as pydantic models; the Validator rules 1 to 8 with their fixed messages, the Dry run check and the fixture rooms; `to_prompt_view` and `to_play_view` keeping solutions on the server; the session state machine with code and find locks, order sequences and `use_on`; the artifact, session and job stores with their local disk adapters.
- API: the Room, Session, Build and Meta routes (`GET /api/meta`, `/schema`, `/rooms`, `/builds/<job_id>/view`, the Trickster and Effective room routes), the First-room welcome on session start, `web/types` generated from `GET /schema` with a staleness test, the per-Room Disclosure lists.
- Providers and ledger: the `ModelProvider` port with the scripted mock and the fixture replay format; the Meta Model API adapter for chat, segment and image, the OpenAI-compatible Riddler fallback and the Ollama Guide adapter; the spend ledger that reserves, settles and caps every paid call, the model-call cache in front of it, the local ledger file and disk cache, the export and reset script; `scripts/sit.py` with the live-seam cases under `tests/sit/`.
- Pipeline: the persisted build job and ingest stage; the Architect prompt and the architect and segment stages with the Mask preview; the Riddler authoring stage behind the Validator with the regeneration loop ending in `needs_recapture`; the Dry run stage proving every Puzzle solvable; the scene stage writing the immutable Room; the full Build recorded per role and replayed offline.
- Web shell and play: design tokens, self-hosted fonts and the focus ring; the app shell with the Disclosure banner, hash routes and error banner; the Stored Rooms list; photo Scenes with mask Hotspots and the Thumbnail strip; Inventory, Wizard notes with Evidence cards and the portrait; the Code field and find lock feedback; order and `use_on` by drag or select-then-click; the welcome card, the Completion screen, reload resume and reconnecting, the narrow-screen message and Leave room confirmation, the accessibility floor on Scenes and locks.
- Capture and Build view: the Capture screen with the Retention summary, dropzone, Photo tray and one-step upload; the Capture Timer; Capture progress with the Stage list, Regeneration rows and Mask preview; the end states for failed, too few objects, re-capture and Spend cap; the BuildView projection (never carrying a solution) with its header, Model table, puzzle graph, mask overlays, verdict table, Dry run rows and JSON pane.
- Hints: Rungs selected in pure code from the session log; the HintPhraser port with the verbatim adapter; hint requests answering the current Rung or the No-hint line; the Hint area; the Triggers panel; the Greeting composer over the Derived block and the Greeting path on session start.
- Trickster and council: Trickster edits landing only when the Validator passes (rule 9 for Decoys); apply opening Trickster windows and building the Game-state summary; the TricksterSource port with the recorded-proposals artifact and the live source; Trickster Cards in the Hint area and accepted edits reshaping the room in play.
- Hosted: `Settings.mode` and `min_containers`; the Modal app entry with the hosted stores on the keyframe Dicts and the `keyframe-data` Volume; the hosted build runner with its watchdog and the daily ledger snapshot merged into the committed export; the twenty-slot judge build quota, the access-code guard, `POST /access/check` and the per-IP attempt limit; Demo rooms seeded and listed, Judge rooms apart; Judge room deletion with its ids-only record, the purge script, 410 for deleted rooms and the hourly session sweep; the hosted landing with Demo room cards and the access-code build panel.
- Repo: the CI job `check` also runs on pushes to `keyframe/**` branches.

## Tue Oct 27: the end-of-build review fixes, the Oct 26 audit fixes, the first live Meta calls, the deploy workflow.

- Review fixes F1 to F13: fixture rooms carry complete job records; architect and segment record their real call receipts; gone sessions and unknown builds show a way out; a stored session reopens after a server restart; regeneration reasons name each puzzle by the Riddler's own `p1..p6` key; a purged Judge room answers `410 room_deleted` on the session room read; tooling references dropped from code ahead of the Nov 4 hygiene.
- Audit of the Oct 26 work and its fixes F14 to F20: the hosted Trickster runs with the cache off; the hosted image carries `proposals/` beside `src`; the earlier-session Disclosure on the Build view; hosted end-state actions keep the Access code's Capture screen; a Merge card names the waiting Puzzle first; one unparseable job record no longer hides every Room; a Judge room's deletion takes every Session that names it; a page's first profile write keeps the results the file holds; an Architect reply off the response shape ends the Build as a provider error; the Build view header numbers sent-back attempts from 1; the hosted deploy fails by name when the `keyframe` Secret lacks a hosted key; the Card, Triggers panel and Mask preview timing fixes on the Play and Capture screens.
- First live Meta calls: the four wizard portraits painted once with muse-image and committed; the SIT's first six cases run live with their recordings committed; the offline replay tests made shape-based so they hold under any valid recording; the fixture scenes repaired to draw the evidence the two code puzzles need; the SIT recording transport honours `HTTPS_PROXY` and `NO_PROXY`.
- Deploy workflow: a second, hand-started workflow `.github/workflows/deploy.yml` runs the pre-deploy ladder and `modal deploy` with the Modal token from the repository's Actions secrets, with the Environment and `MIN_CONTAINERS` as inputs, and stops on a Modal auth error instead of trying to create the Environment. `ci.yml` still holds no secret and no deploy step.

## Wed Oct 28: the first hosted deploy to Modal.

- Run 3 of the deploy workflow, from master `0452a4c`, Environment `main`, `MIN_CONTAINERS` 0: the judge URL https://luis-ticas1--keyframe-web.modal.run serves `web/dist` at `/` and the API under `/api/`; `GET /api/meta` answers 200 hosted, the access check answers ok with 20 builds left, the landing renders clean in Chromium.

## Thu Oct 29: the playtest fixes, the follow-up lanes, the hero-select landing, the intro and the way back, and story mode begins.

- Playtest fix lanes on the owner's decisions of Oct 29 (the first three, P3, P6 and B2, landed late on Oct 28): evidence cards hold the answer back until solved; asking the Guide opens a real hint; the Completion screen celebrates; player wording everywhere; play never blanks; small objects keep their SAM outline; only objects a later puzzle uses go into the Inventory. The correct-course record (`docs/planning-artifacts/sprint-change-proposal-2026-10-29.md`) records every accepted departure from the plan.
- Follow-up lanes C1, V1, G1 to G5, L1 to L3 and R1 to R3: a ten-second clip of the sample room on the landing; an upload byte cap; errors never echo what was sent; one ULID minter; a Demo room is never a Judge room (ops runs 3 to 5); the Trickster only edits puzzles still locked. The docs reconciliation (schema v1, the architecture spine, the epics, EXPERIENCE and DESIGN, README, specs, the SIT run log, the runbooks) against what shipped. Two live replays on the judge URL, on `02965dd` and `d5dc3fa`, each with three testers and an adversarial triage.
- The Hosted landing opens on a hero-select of three spinning cards (H1); the reviewer-feedback round (K1 to K4); the Demo room's vent and pillow outlines hand-corrected through an ops action (D11, ops runs 6 and 7); the quiet top bar (D12); a new deploy's page replaces a stale one (W1).
- Every screen has a way back to the start (N1); Watch the demo at real speed (N2); a full-screen intro on the first visit, once, with replay and skip (M1); the Watch card opens on a captioned tutorial (M2); a resumed video range request is answered.
- Story mode begins: each room gets its own wizard story, written at build time; a two-hint treasure chest and no automatic hints; one riddle at a time; walk around the room instead of a thumbnail strip; the story intro with the Architect, the Trickster's trap, the Riddler and the Guide; an ops action that writes a Demo room's story. Deploy runs 7 to 18, all success.

## Fri Oct 30: story mode finished, the Demo room's story, the riddle 3 fix, sound and music, the card-turn fix, the final live checks.

- Story mode finished overnight: the story check passes the room's name and area labels and keeps the wizards' voices, the rules and the visitor welcome; a failing line falls back to its own template line, and no example or template line names an object (SV4 to SV6); the story box holds one place (SF1); Watch the demo re-recorded on story mode (C2).
- The Demo room's story and hand edits through the ops actions (ops runs 8 to 20, from late Oct 29): its areas and start photos, its story written by the live story step on Modal and corrected by hand with a patch the story's own line rules check (X4), its clock, tray and door moved to the photos where players look (SF2). These are hand corrections of the Demo room, not pipeline output.
- Two story-mode replays and their re-checks on the judge URL, on `ae4361a` and `223201d`, led to X1 to X5: the escape stays in daylight, the intro's Next and story box hold still, the chest clears the turn disc, the Build-your-own back stays inside its stage, the intro waits for the first photo; a beat-1 check on `6cc2666` measured no drift. The docs pass for story mode and a record refresh followed.
- Evening: the tutorial on the Play back and "Play intro" at the top bar's right end (J1); the riddle 3 fix: an item in hand clicks through to its Hotspot and the sectional sofa moves to photo 2 (Q1, ops runs 21 and 22), and an empty-hand click on the sofa says it needs something from the pack (Q2); background music and interactive sounds with a sound toggle (A1); card turns always land face-on (T1).
- Deploy runs 19 to 27, all success; run 27 put `b5a21ca` on the judge URL after CI passed on both branches. Live checks of riddle 3, Q2, and the sound and card turns passed on the judge URL; no full replay ran on `b5a21ca`. The epics and the correct-course record follow J1 to T1.

## Sat Oct 31: a promo sequence for recording the demo video.

- `demo/promo`: a standalone page for the demo video's inspiration segment, run locally, outside the product; CI green on master. Nothing deployed: the judge URL keeps serving `b5a21ca`.

## Sun Nov 1: no commits.

- No code or docs change; the judge URL keeps serving `b5a21ca`.

## Mon Nov 2: no commits.

- No code or docs change; the judge URL keeps serving `b5a21ca`.

## Tue Nov 3: the site warmed for judging.

- Ops run 23 (GitHub run 41764170265, ops/warm-1, Environment `main`, success): the warm action keeps one container running (min containers 1) on https://luis-ticas1--keyframe-web.modal.run from tonight through judging, against cold starts and the transient 502 seen in the second replay. Cooling it after judging is still to do.

## Wed Nov 4: the submission pass.

- The README rewritten for judges, with the models table and the process map, and pointers to the BMAD install (`_bmad/`), the planning outputs under `docs/` and the owner's own skills under `.claude/skills/` (`keyframe-*`).
- MIT license added (`LICENSE`).
- The promo images removed from the repo: the third-party screenshots and the generated hero image under `web/public/promo/`.
- The state before the event is the annotated `pre-hackathon-baseline` tag on `2f740b3` (Oct 26): https://github.com/lutic1/meta-hackathon-2026/tree/pre-hackathon-baseline.
