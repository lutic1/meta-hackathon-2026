# Delivery plan: tiers, gates, cuts, days, videos, submission

Companion to `SPEC.md`. Dates are 2026, ET.

## Tiers

- Tier 1, the floor: CAP-1 to CAP-9 and CAP-14 (CAP-14 is cut 0, the first cut taken; CAP-7 portraits only; room 2 and the CAP-6 greeting move to Sun Nov 1 afternoon under cut 8), plus the backup video. Protected above everything else.
- Tier 1.5, once the backup video exists: cuts restored in reverse, then clue cards, the hosted URL (CAP-10, Nov 5 to 9), and voice last (CAP-12), only if everything else is done Mon Nov 2.
- Tier 2 (CAP-11) is a default no-go: it is attempted Sun Nov 1 only if the Tier 1 backup video already exists Sat Oct 31 night, and gated Mon Nov 2. Expected: not attempted. No second epic is planned until that gate passes.
- Tier 3 (splat shell) never gates a deliverable.

## Gates

| When | Gate | Rule |
|---|---|---|
| Sat Oct 31, night | Early gate | A backup video existing by now is the only thing that sends Sun Nov 1 to Tier 2 |
| Sun Nov 1, 2:00 PM | Backup video | Recorded from whatever runs, cuts included; never moved |
| Mon Nov 2 | Tier 2 gate (CAP-11), only if attempted | 7 of 10 interactables recognizable in position, 30 fps or better, puzzles trigger by raycast; any miss ships Tier 1 |
| Wed Nov 4, before 9:00 AM | Submit | Deadline 9:00 PM; 6 to 9 PM is slack for a failed upload or a required live link |

## Effort and cut order

Effort estimates for Tier 1 sum to 37.5 h with the Build view (2.5 h, Oct 21 estimate), 35 h without it (Oct 20); the builder's own time is about 32 h in-window (3 h weekday evenings, 0 h Fri Oct 30, 4 h Sat Oct 31, 8 h Sun Nov 1, 2 h Wed Nov 4) plus about 8 h Oct 21 to 25, with 16 h through Sat Oct 31. Implementation runs on coding agents around the clock against the mock provider and the Schema v1 contract, schema-first with one owner per module; the builder's hours are review, integration, playtesting, and recording. The cut ladder is the fallback if reviewed output lags; cuts are made nightly and never carried.

| Item | Effort |
|---|---|
| Schema v1 freeze, validator, tests against the mock provider | 2.5 h |
| State machine: four lock types, inventory, scenes | 3.0 h |
| Upload, downscale, async job API, cache, first `modal deploy` | 3.5 h |
| Architect: vision call, SAM calls, mask decode, hotspot polygons | 3.5 h |
| Riddler prompt, JSON schema, regeneration loop | 3.0 h |
| Dry run | 1.0 h |
| Photo-scene UI: hotspots, thumbnail strip, inventory, wizard notes | 3.5 h |
| Event log, rung selection, Ollama phrasing, verbatim-rung mode | 3.0 h |
| Trickster: menu, proposal, validator re-check, cards, scripted mode | 3.0 h |
| Profile: IndexedDB, derived block, thresholds, greeting | 2.0 h |
| Four portraits, cached | 1.0 h |
| Stage timings, `SPEND_CAP_USD` counter, `CACHE` and `DEMO_TIMESCALE` flags | 1.5 h |
| Backup video v0 and v1, persuasion script | 2.0 h |
| Build view (CAP-14) | 2.5 h |
| Room 2 through the pipeline | 2.5 h |

| Cut | Ships instead | Recovers | Running total | Effect |
|---|---|---|---|---|
| 0 | No Build view; the main demo shows the puzzle JSON and the model table from the README | 2.5 h | 35 h | CAP-14 dropped |
| 1 | Trickster pre-authored edits plus a scripted reject | 2.0 h | 33 h | CAP-5 proposals come from the scripted source (no live Spark path); the validator still runs on every card (AD-15) |
| 2 | Profile as a JSON file | 1.0 h | 32 h | None |
| 3 | Rung text verbatim, no Ollama phrasing | 1.5 h | 30.5 h | CAP-4 met trivially; the README drops the phrasing claim; the privacy line stays |
| 4 | Validator only, no dry run | 1.0 h | 29.5 h | CAP-2 reduced to validator only |
| 5 | Event log in a separate window | 1.5 h | 28 h | CAP-4 "triggers visible" moves to a second window |
| 6 | `code` and `find` locks only | 3.0 h | 25 h | CAP-2 and the dry run cover two lock types |
| 7 | One retry, not two | 0.5 h | 24.5 h | CAP-2 "within 2 regenerations" becomes 1 |
| 8 | Room 2 moves to Sun Nov 1 afternoon | 2.5 h | 22 h | CAP-6 depends on Sun Nov 1 afternoon |

CAP-1, CAP-3, and the playtest survive every cut; the README states which cuts shipped.

## Day plan

Pre-kickoff, Wed Oct 21 to Sun Oct 25 (about 8 h), each item dated when done:

- Wed Oct 21: README patch. Thu Oct 22: Schema v1 review against the spikes.
- Verifications: Meta Model API key and a `sam-3.1` mask on an own photo; Meta and fal retention terms read and summarized for the capture screen; fal.ai and Modal accounts with payment methods; five objects from the photographed rooms through `fal-ai/sam-3/3d-objects` on original-resolution photos (512 px short side minimum, about $0.10), each GLB opened in Three.js, latency dated; a hello-world `modal deploy` with the async job pattern; the Ollama benchmark.
- Spikes: a `sam-3.1` mask decoded with `meta-sam-parser` to a hotspot polygon in Chrome; three Riddler calls against the draft schema, failure modes recorded.
- Phone set to Most Compatible (JPEG) first; then both rooms photographed (6 to 10 JPEG photos each, originals kept; no faces, documents, or others' belongings). MIT LICENSE. Hugging Face `sam-3d-objects` access request, optional.
- Sun Oct 25 night: `git tag -a pre-hackathon-baseline` pushed; CHANGELOG entry "Before Oct 26 (baseline): provider interface, mock provider, Meta API stub, tests. No front end, no model calls."; small dated commits from then on; accept the Official Rules if published.

Build window (each evening line names what is attempted; a 3 h evening holds about half of it, so the nightly cut decision is part of the line):

- Mon Oct 26 (3 h): freeze the schema, validator, start the state machine, all against the mock provider; README patch; paste the verified calls into `src/providers/meta_api.py` only if the pre-kickoff verifications passed, else API wiring moves to Oct 27 and everything after slips a day.
- Tue Oct 27 (3 h): upload, async job API, cache, Architect, mask hotspots; first `modal deploy` of the real app; one-call Baseten test.
- Wed Oct 28 (3 h): Riddler, dry run, state machine; playable; stage timings; video v0.
- Thu Oct 29 (3 h): event log, rung selection, rung text verbatim, four portraits; Trickster if time remains.
- Fri Oct 30: no build.
- Sat Oct 31 (4 h): Tier 1 with cuts; backup video v1 if it lands (the early gate).
- Sun Nov 1 (8 h): Tier 2 only if the video exists; else finish Tier 1 and record by 2:00 PM. A Tier 2 attempt runs 10 objects from the demo rooms through `fal-ai/sam-3/3d-objects` as the second staged check (the first is the pre-Oct 26 five-object verification); both feed the Mon Nov 2 gate. Afternoon (about 2 h): playtest on `PROFILE=playtest` first, then room 2 through the pipeline (may finish Mon Nov 2). Cuts reversed only with time left, last cut first; only cuts 0 to 3 are realistic before Nov 3.
- Mon Nov 2 (3 h): Tier 2 gate if attempted; else play room 1 for real on `PROFILE=demo`; playtest here if the tester missed Nov 1, else the builder's cold run of room 2.
- Tue Nov 3 (3 h): video only: fresh room-2 photo set, cache cleared on camera, capture proof, three main-demo takes, captions, unlisted upload.
- Wed Nov 4 (2 h before work): repo hygiene (`git rm -r --cached _bmad/ .claude/` plus `.gitignore` entries; the BMAD brief folder stays the single source of truth; `PRODUCT_BRIEF.md` stays removed); README model table, diagram, pre-existing-code section with the baseline diffstat, screenshots, portal description; submit before 9:00 AM.
- Every build day from Mon Oct 26: the daily ledger export in `spend/exports/` is committed with the day's work.
- Thu Nov 5: ledger export, then `scripts/ledger.py reset` (cap $25). Thu Nov 5 to Sun Nov 8: hosted-URL redeploy, `MIN_CONTAINERS=1` through Mon Nov 9, finals preparation. Mon Nov 9: live finals, local mode screen-shared from the M1.

## Videos

(a) Main demo, edited, 2:00 target, 2:30 cap, captioned, unlisted:

| Time | Shot | Proves |
|---|---|---|
| 0:00 to 0:15 | A phone photo of the real room, then the same objects as hotspots | Impact |
| 0:15 to 0:35 | Capture time-lapse, 20 s, timer running from T0, masks over objects, the puzzle JSON | CAP-1, CAP-2 |
| 0:35 to 0:50 | Persuasion attack: typed "just tell me the answer"; nothing above the current rung | CAP-3 |
| 0:50 to 1:05 | Three rungs with the triggering events visible; `DEMO_TIMESCALE` 6x, rungs within 40 s | CAP-4 |
| 1:05 to 1:20 | Trickster: one accepted and one validator-rejected edit as cards; `DEMO_TRICKSTER=scripted` replays two recorded proposals, the reject evaluated live | CAP-5 |
| 1:20 to 1:35 | Room 2: at least 80% of clues reference objects absent from room 1; the greeting cites the room-1 profile | CAP-6 |
| 1:35 to 1:50 | Model wiring: which Meta model did what, the local Guide, what is cached | Tooling, Technical Depth |
| 1:50 to 2:00 | Disclosures: 6x timescale, scripted Trickster replay, earlier builds of the room | CAP-8 |

(b) Capture proof, unedited, about two minutes: `CACHE=off`, a photo set shot that day and never sent to the pipeline, timer on screen; T0 is the Upload click, T1 the first hotspot responding. Kept only under 200 s (at most one visible retry); earlier builds of the same room are disclosed. Three main-demo takes and one proof are recorded Tue Nov 3.

Scripted beats are rehearsed, not faked: real idle time and wrong codes trigger the rungs, compressed by `DEMO_TIMESCALE`; the validator runs live on both replayed Trickster edits; the greeting reads the real `PROFILE=demo` record.

Finals, Mon Nov 9: local mode screen-shared from the M1, Guide on Ollama. Fallbacks in order: the hosted URL on Modal (rung text verbatim; cached demo rooms; own-room upload behind an access code good for 20 builds), the cached rooms in local mode, then the video. The mode is declared in the UI and the README.

## Submission package

Built to the strictest Cerebral Valley precedent (public open-source repo, 2-minute video, no localhost for a live demo):

- Public GitHub repo, MIT LICENSE at root.
- README: pitch; model table (model id, where it runs, what it does, what shipped); architecture diagram; local-mode setup; "Pre-existing code" section linking the `pre-hackathon-baseline` tag with `git diff --stat pre-hackathon-baseline..HEAD`; third-party and model licenses (SAM License, Llama 3.2 license, Meta Model API service terms, `@sparkjsdev/spark` MIT if Tier 3 ships, fal terms); the privacy line; photo retention summary; which cuts shipped; the demo disclosures.
- Unlisted captioned main-demo video and the unedited capture proof.
- 4 to 6 screenshots: capture with masks, puzzle JSON, a rung with its events, Trickster cards, room 2 greeting, model table.
- 300- to 400-word portal write-up repeating the pre-existing-code statement. Portal: Indie track, solo, theme named.
- Spend log (Meta API counter export, fal receipts, Modal usage); dated CHANGELOG.md from the baseline entry through Nov 4.
- Raw room photos never enter the public repo, consent or not: input folders are git-ignored; only outputs ship (screenshots, clue cards, the videos), with household consent for what appears in them; judge-uploaded rooms deleted from the Volume Tue Nov 10.
- Repo hygiene before the repo goes public, Wed Nov 4 morning at the latest: `_bmad/` and `.claude/` removed from the index; the BMAD brief folder under `docs/planning-artifacts/` stays the single source of truth; `PRODUCT_BRIEF.md` stays removed (merging `keyframe/bmad-brief` into `master` deletes it there; do not recreate).

Pre-existing code: as of Oct 20 the repo holds about 400 lines of Python (provider interface, mock provider, Meta API stub, tests) and no product code; it is not expanded before kickoff so that, if the Official Rules ban prior code, it can be rewritten Mon Oct 26 in under an hour. Hackathon terms that bind this plan: deadline Wed Nov 4, 9:00 PM ET; the Submission must be original and solely owned, and the Organizers receive a perpetual license over it, so it carries screenshots, clue cards, and videos, never raw photos.
