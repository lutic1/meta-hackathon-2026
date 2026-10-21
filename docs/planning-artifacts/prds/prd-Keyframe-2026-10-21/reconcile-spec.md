---
title: "Input reconciliation: spec to PRD, Keyframe"
created: 2026-10-21
author: Luis Ticas
inputs:
  - docs/specs/spec-keyframe/SPEC.md
  - docs/specs/spec-keyframe/stack.md
  - docs/specs/spec-keyframe/budgets.md
  - docs/specs/spec-keyframe/player-profile.md
  - docs/specs/spec-keyframe/delivery-plan.md
  - docs/specs/spec-keyframe/glossary.md
checked:
  - docs/planning-artifacts/prds/prd-Keyframe-2026-10-21/prd.md
  - docs/planning-artifacts/prds/prd-Keyframe-2026-10-21/addendum.md
---

# Input reconciliation: spec to PRD

## Verdict

Mostly landed. Numbers, thresholds, caps, the cut ladder, the gate table, the privacy line, the integrity rules (no solution in any prompt, server-only lock opening, persuasion as a Hint request), and every settled fact come through correctly, and nothing in the PRD contradicts a settled fact. What did not land is concentrated in four places:

1. **The demo contract.** The spec's Success signal (what the main demo must show) has no Success Metric. The eight-beat shot list is missing, including the impact opener and the model-wiring beat. The "rehearsed, not faked" honesty rule is reduced to "disclose shortcuts".
2. **The build-process contract the epics run needs.** The Schema v1 freeze on Mon Oct 26 with changes only through `bmad-correct-course`, "no second epic until the Tier 2 gate passes", and "the builder reviews everything that ships" are all absent.
3. **Submission-package items.** The CHANGELOG, the README model table, the screenshots, the portal write-up and the spend-log sources are missing. The "required live link" slack is also gone.
4. **A few qualitative and privacy rules.** The photographing rule (no faces, documents, or others' belongings), what persistence means, the tone of the no-hint line, and an honest statement of what Hosted mode sees.

One PRD line contradicts the inputs (FR-30, spend log "never hand-kept"). There is also one internal date inconsistency (hosted window).

## What landed correctly (spot-checked)

- Capture: 6 to 10 JPEG photos, HEIC/PNG rejected, 1280 px, originals kept, 5 to 12 Interactables, fewer than 5 means `needs_more_photos` before any Riddler call, the 120 s target and the p50 plus 25% re-base rule, stage budgets 15/10/45/30/10 s, a regeneration about 75 s, at most 2, about 260 s (FR-1 to FR-10, NFR-1).
- Integrity: eight validator rules, a solution-blind dry run, the rule 5 near-answer allowance, structured reasons that never quote a token, the persuasion attack failing by construction (FR-8, FR-9, FR-14, §6.2).
- Guide: nudge 90 s × (1 + 0.5 × persistence) clamped to 60 to 135 s, 3 wrong attempts, 90 s fixed spacing, about 40 tokens in 5 s or less from under 400 tokens, Mac only, verbatim in Hosted mode, cut 3 behavior (FR-15 to FR-17).
- Trickster: one change per 3-minute window, at most 6 Spark calls, fixed menu, re-validation, accepted and rejected cards, scripted replay with the validator live (FR-18, FR-19, FR-25).
- Memory: IndexedDB under `PROFILE`, Derived block only, Greeting names no object or solution, 80% fresh objects, a real room-1 record on `PROFILE=demo` (FR-20, FR-21).
- Spend: $80 through Wed Nov 4, $25 from Thu Nov 5, persisted counter, daily export at 06:00 ET hosted and at startup plus after every build locally, the reset refused without that day's export, fal $6, mock provider with `CACHE=on` (FR-27 to FR-29, NFR-6, addendum §3).
- Gates and cuts: Sat Oct 31 night early gate, Sun Nov 1 2:00 PM backup video (never moved), Mon Nov 2 Tier 2 gate (7 of 10, 30 fps, raycast), Tue Nov 3 video only, submit before 9:00 AM ET Wed Nov 4; eight cuts in order, nightly, never carried; CAP-1, CAP-3 and the playtest survive every cut (§11).
- Settled facts: the Guide is Llama 3.2 3B via Ollama on the Mac only; no Glimmer; the privacy line is verbatim; SAM 3D Objects runs on fal.ai only at $0.02, Tier 2 only, default no-go; raw photos never committed; judging weights; the decision schedule (§13 and addendum §4) matches exactly.
- Personas: Ana and Priya are named fictional personas referred to as they/them. Luis Ticas is referred to by name throughout.

## Gaps

### G1 (high). The spec's Success signal has no Success Metric

**Where:** `prd.md` §12. **Source:** SPEC §Success signal, CAP-4, CAP-5, CAP-6 and CAP-8 success lines.

The spec defines done as a main demo of at most 2:30 that shows four things: the persuasion attack failing, three rungs escalating on visible triggers, one Trickster edit accepted and one validator-rejected, and room 2 greeting the player from the room-1 profile. SM-1 to SM-3 cover the capture proof, the playtest and persuasion. No SM covers the main demo as a whole, the visible-trigger rungs, the Trickster pair, or the greeting on camera. Demo is 25% of the score, and the PRD's metrics would pass with none of those beats on video.

**Fix (add to §12 Primary):**
> **SM-4 Main demo carries every proof beat:** the edited Main demo runs at most 2:30 (target 2:00) and shows, in order: the persuasion attack failing; three Rungs escalating with their triggering events visible (`DEMO_TIMESCALE=6`, within 40 s, on Wrong attempts); one accepted and one Validator-rejected Trickster edit as Cards; and the room-2 Greeting read from the real room-1 record on `PROFILE=demo`. The Disclosures appear in the last 10 s. Validates FR-14 to FR-16, FR-19, FR-21, FR-24 to FR-26.

Renumber the current secondaries.

### G2 (high). The main-demo shot list is missing, including the impact opener and the model-wiring beat that serves the Tooling score

**Where:** `prd.md` UJ-6, §4.8, §12. **Source:** delivery-plan.md §Videos (a) and §Submission package.

UJ-6 summarizes the takes. It drops the timed eight-beat structure and two beats that map directly to judging weights:
- 0:00 to 0:15, a phone photo of the real room, then the same objects as hotspots (Impact, 30%).
- 1:35 to 1:50, model wiring: which Meta model did what, the local Guide, and what is cached (Use of Meta AI Tooling 25%, Technical Depth 20%).

The 0:15 to 0:35 capture time-lapse (20 s, timer running from T0, masks over objects, the puzzle JSON) is also missing.

The README model table, which also serves the Tooling score, appears nowhere in the PRD. The table lists model id, where it runs, what it does, and what shipped.

**Fix:** Add a §4.8 Note (or a new FR-26a "Main demo structure"):

> The Main demo follows this beat order: 0:00 to 0:15 real-room photo to the same objects as Hotspots; 0:15 to 0:35 capture time-lapse with the timer running from T0, masks, puzzle JSON; 0:35 to 0:50 persuasion attack; 0:50 to 1:05 three Rungs with triggers at 6x; 1:05 to 1:20 Trickster accept and reject; 1:20 to 1:35 room-2 Greeting and fresh objects; 1:35 to 1:50 model wiring (which Meta model did what, the local Guide, what is cached); 1:50 to 2:00 Disclosures. Captioned, unlisted.

Also add to NFR-13:

> The README carries a model table (model id, where it runs, what it does, what shipped) and an architecture diagram.

### G3 (high). Demo honesty landed as "disclose shortcuts" but lost "rehearsed, not faked"

**Where:** `prd.md` NFR-12, FR-24 to FR-26, UJ-6. **Source:** delivery-plan.md §Videos ("Scripted beats are rehearsed, not faked …") and §Videos (b).

Disclosure is only half of the spec's honesty rule. The other half constrains how each beat is produced:
- Real idle time and real wrong codes trigger the rungs (compressed only by the timescale, never injected).
- The validator runs live on both replayed Trickster edits.
- The greeting reads the real `PROFILE=demo` record.
- The capture proof uses a photo set shot that day and never sent to the pipeline, with the cache cleared on camera.

The PRD captures pieces of this (FR-25 live validator, FR-21 real record, UJ-6 cache cleared). It never states the rule, so a downstream story could satisfy NFR-12 with a disclosed but synthetic event injection. The addendum's "the unedited capture proof covers trust" is the reason the main demo may use a time-lapse. The PRD body never says the time-lapse depends on the proof.

**Fix (extend NFR-12):**
> Scripted beats are rehearsed, never faked. Rungs on video are triggered by real idle time and real Wrong attempts, compressed only by the Demo timescale, never by injected events. The Validator runs live on both replayed Trickster edits. The Greeting reads the real `PROFILE=demo` record. The Capture proof uses a Photo set shot that day and never sent to the pipeline, with the Cache cleared on camera. The Main demo's capture time-lapse is acceptable only because the unedited Capture proof accompanies it.

### G4 (high). Schema v1 freeze and the change rule are missing

**Where:** `prd.md` §11.1, NFR-11, §13. **Source:** SPEC §Constraints ("reviewed Thu Oct 22 against the spikes, frozen Mon Oct 26; later changes only through `bmad-correct-course`"), delivery-plan.md day plan Mon Oct 26.

The PRD names the Thu Oct 22 decoy pick but never the Mon Oct 26 freeze or the correct-course rule. For a build run by several implementers in parallel, schema-first with one owner per module, the freeze is the load-bearing gate. It is also the reason the epics run can treat Schema v1 as fixed.

**Fix:** add a row to §11.1:

> | Mon Oct 26 | Schema v1 freeze | Schema v1 is the Tier 1 and Tier 2 contract; after the freeze it changes only through `bmad-correct-course` |

Add "Schema v1 frozen Mon Oct 26" to NFR-11.

### G5 (medium). "No second epic until the Tier 2 gate passes" is missing from the PRD body

**Where:** `prd.md` §10.2, §4.11. **Source:** delivery-plan.md §Tiers.

The PRD's named downstream consumer is `bmad-create-epics-and-stories`. Without this rule, FR-34 reads as a normal FR to break into stories. The addendum mentions it only as rationale in a rejected-alternatives row.

**Fix (add to §10.2 Tier 2 bullet):**
> FR-34 gets no epic or stories until the Mon Nov 2 gate passes; expected: not attempted. If fal output lacks a usable pose, Tier 2 falls back to Runware, Segmind, hand-made assets, or a photo billboard.

### G6 (medium). Build-model and review constraints are missing

**Where:** `prd.md` §6 or NFR-11. **Source:** SPEC §Constraints (Build model), delivery-plan.md §Effort and cut order.

The spec's build model has five parts:
- Multiple implementers (Muse Code and the BMAD build loop) work around the clock.
- The build is schema-first, with one owner per module.
- Stories are built against the mock provider.
- The builder reviews everything that ships.
- Luis has about 32 h in-window, around a day job.

The addendum covers the hours. The PRD body never says that Luis reviews everything that ships. That rule is what the cut ladder's trigger ("if reviewed output lags") depends on. It also drops Muse Code, a Meta tool that belongs in the model-wiring story for the Tooling score.

**Fix (new §6.6 Build model):**
> Implementation runs around the clock on Muse Code and the BMAD build loop, schema-first, one owner per module, against the Mock provider. Luis Ticas reviews everything that ships, with about 32 h in-window (around a day job) for review, direction, playtesting and recording. Cuts trigger when reviewed output lags.

### G7 (medium). Submission package items did not land, and FR-30 contradicts the spend-log sources

**Where:** `prd.md` NFR-13, FR-30. **Source:** SPEC §Constraints (Submission), delivery-plan.md §Submission package.

Missing from the PRD:
- A dated `CHANGELOG.md` from the baseline entry ("Before Oct 26 (baseline): provider interface, mock provider, Meta API stub, tests. No front end, no model calls.") through Nov 4.
- 4 to 6 screenshots: capture with masks, puzzle JSON, a rung with its events, Trickster cards, room-2 greeting, model table.
- A 300- to 400-word portal write-up that repeats the pre-existing-code statement. The portal entry is Indie track, solo, theme named.
- The README's photo retention summary, its demo disclosures, and the list of cuts shipped (partly in NFR-12).
- The rule that the BMAD brief folder stays the single source of truth.

**Contradiction:** FR-30 says "The submission's spend log derives from the Ledger, never hand-kept". The spec's spend log has three sources: the Meta API counter export, fal receipts, and Modal usage. Modal compute is not a priced model call in the Ledger.

**Fix:** Extend NFR-13:
> A dated CHANGELOG from the `pre-hackathon-baseline` entry through Nov 4; 4 to 6 screenshots (capture with masks, puzzle JSON, a Rung with its events, Trickster Cards, room-2 Greeting, model table); a 300 to 400 word portal write-up repeating the pre-existing-code statement (Indie track, solo, theme named). The BMAD brief folder under `docs/planning-artifacts/` stays the single source of truth; the planning-tool folders removed are exactly the two named in delivery-plan.md §Submission package.

Change the second FR-30 consequence to:
> The submission's spend log is the Ledger export for model calls, plus fal.ai receipts and Modal usage.

### G8 (medium). "Or a required live link" slack, and the unconfirmed submission-format assumptions, were dropped

**Where:** `prd.md` §11.1 Submit row, §1a, NFR-13. **Source:** delivery-plan.md §Gates ("6 to 9 PM is slack for a failed upload or a required live link") and §Submission package ("no localhost for a live demo"); SPEC §Assumptions (selection unconfirmed until Mon Oct 26; Official Rules, pre-existing-code policy and submission format unpublished; Cerebral Valley precedent).

The PRD states the 2-minute video and public repo as facts and keeps only "slack for a failed upload". Hosted mode is scheduled Nov 5 to 9. If the rules require a live link on Nov 4, the slack window is the only plan for it, and the PRD has lost that.

**Fix:** Restore the gate text:
> Deadline 9:00 PM; 6 to 9 PM is slack for a failed upload or a required live link.

Add an assumption:
> `[ASSUMPTION A-19]` Selection is unconfirmed until Mon Oct 26 (else the same plan runs pay-as-you-go). The Official Rules, the pre-existing-code policy and the submission format are unpublished; the 2-minute video, the public repo and "no localhost live demo" follow Cerebral Valley precedent. If the rules ban prior code, the about 400-line scaffold is rewritten Mon Oct 26 in under an hour; the Official Rules are accepted when published.

### G9 (medium). The photographing privacy rule is missing

**Where:** `prd.md` §6.1, UJ-1 entry state, Q5. **Source:** delivery-plan.md day plan ("6 to 10 JPEG photos each, originals kept; no faces, documents, or others' belongings").

This rule decides what can appear in the videos and screenshots, which the Organizers receive under a perpetual license. The PRD keeps household consent but drops the content rule.

**Fix (add to §6.1):**
> Demo-room photos show no faces, documents, or others' belongings; household consent covers everything that appears in the videos and screenshots.

### G10 (medium). Derived-block meaning and the stored room fields were flattened to names

**Where:** `prd.md` §3 (Derived block, Room result), FR-21, §7 Greeting. **Source:** player-profile.md §Stored per room, §Derived block.

The PRD lists the four field names but not what they mean:
- `persistence` runs from -1 to 1. It is positive when the player keeps trying past the nudge threshold and negative when they ask early.
- `time_to_first_hint` is the median in seconds.
- `mean_rung_per_lock_type` runs from 0 to 3.
- The block is recomputed after each room.

The PRD's Room result also drops two stored items: the Trickster edits seen and accepted, and the raw event log. The Greeting copy ("you held out long past the first nudge", §7 "warm and specific about play style") can only be written and tested against these meanings. The UX contract needs them to draft Greeting variants.

**Fix:** Expand the §3 Derived block entry:
> `time_to_first_hint` (median seconds), `mean_rung_per_lock_type` (0 to 3), `persistence` (-1 to 1: positive when the player keeps trying past the nudge threshold, negative when they ask early), `sessions`; recomputed after each Room.

Expand Room result:
> … per-Puzzle {Lock type, attempts, Wrong attempts, Rungs used, time to first hint, solved}, Trickster edits seen and accepted, and the raw Event log, all kept in the browser.

### G11 (medium, qualitative). "Helps without telling" can collapse into "never helps"

**Where:** `prd.md` FR-14 (fixed no-hint line), §7, FR-21 (Greeting under cut 3 and Hosted mode). **Source:** SPEC Why ("a council that scaffolds help from how they play"); CAP-12 ("speech only requests the next rung"); the brief's framing that AI hint-givers "dump the answer or never help".

**Problem 1, the no-hint line.** The PRD has a player who asks before the nudge receive "the fixed no-hint line". §7 defines tone for Rungs, the Greeting, Disclosures and errors, but not for this line. Yet it is the most likely line a stuck, impatient player sees, and the scripted attack sees it when no Rung is open. Written as a refusal, it reproduces the "never help" failure the product exists to fix.

**Problem 2, the Greeting without a model.** The Guide's phrasing model is absent under cut 3 and in Hosted mode, and the PRD does not say how the Greeting is produced then.

**Problem 3, wording drift.** CAP-12 says "next rung", while the PRD says "current Rung". The behavior matches the spine; only the wording differs.

**Fix:** Add to §7:
> **No-hint line:** in-world and encouraging, never a refusal; it acknowledges the ask, says the Guide is watching, and invites one more look, with no content about any Puzzle (e.g. "The Guide is watching. Look once more; I will speak when the room has kept you long enough.").

Add to FR-21:
> Under cut 3 and in Hosted mode the Greeting is a fixed template filled from the Derived block, same constraints.

Add to FR-35:
> A spoken request raises a Hint request exactly as a click does; it never advances a Rung beyond FR-15.

### G12 (medium). Hosted mode's access to the Derived block is not stated

**Where:** `prd.md` FR-20, FR-36, §6.1. **Source:** stack.md §Privacy line ("the profile is stored in the browser and read by the selection code on the player's machine … It holds in every build"). The spine's AD-8 (hosted receives `derived` per session, never persists it) is the resolution.

FR-20 sends the Derived block at every Session start, so in Hosted mode it reaches Modal. FR-36 says only that the hosted server "stores no Derived block … beyond a Session's transient Event log", which is ambiguous. The stack.md sentence is literally true only in Local mode. The Privacy line stays true, because the profile never leaves the browser, but the PRD should say exactly what Hosted mode sees, so the README and Retention summary can be honest.

**Fix (add to FR-20):**
> In Hosted mode the Derived block is sent with each Session start, held only for that Session, never persisted, and never joined to a Player profile; the Player profile itself never leaves the browser.

Note for Luis: stack.md's "read by the selection code on the player's machine" wording should match, via correct-course if the spec is touched.

### G13 (low). The exact git-ignore list was paraphrased

**Where:** `prd.md` FR-36. **Source:** SPEC CAP-13 success.

"Photo input folders, HEIC files, and the Cache" loses `rooms/`, which holds judge and local rooms derived from photos, and the exact folder names the offline test asserts.

**Fix:**
> `rooms/`, `photos/`, `captures/`, `uploads/`, `*.heic`, and the Cache directory are git-ignored, asserted by an offline test.

### G14 (low). The hosted warm container and window dates are inconsistent

**Where:** `prd.md` §4.10 description ("judge-ready Thu Nov 5 to Sun Nov 8") versus §10.1 ("Nov 5 to 9"). **Source:** stack.md (`MIN_CONTAINERS=1` Thu Nov 5 to Mon Nov 9), delivery-plan.md day plan.

**Fix (in §4.10):**
> Redeployed Thu Nov 5; a warm container (`MIN_CONTAINERS=1`) runs Thu Nov 5 to Mon Nov 9 so judges never hit a cold start.

### G15 (low). Fallbacks and small bounds were dropped

**Where:** NFR-10, FR-18, §6.1. **Source:** stack.md (front end, Trickster rows, privacy line), player-profile.md §Trickster bounds.

Three items did not carry over:
- The DOM-only scenes fallback if Three.js costs more than 2 h.
- The game-state summary contents (open locks, time, Rungs used).
- If voice ships, audio goes to the Meta Model API. That affects FR-14's "never travels as text" (transcription happens off-device) and the Retention summary.

**Fix:**
- NFR-10: "DOM-only Scenes if the Three.js scene graph costs more than 2 h."
- FR-18: "The game-state summary is open locks, elapsed time and Rungs used only."
- FR-35: "Audio is sent to the Meta Model API for transcription and the Retention summary says so; only the resulting Hint request enters the Session."

### G16 (low). Day-plan contingencies were dropped

**Where:** `prd.md` §11. **Source:** delivery-plan.md §Day plan.

Missing items:
- On Mon Oct 26, the verified calls go in only if the pre-kickoff verifications passed. Otherwise API wiring moves to Oct 27 and everything after slips a day.
- Backup video v0 on Wed Oct 28.
- The playtest runs on `PROFILE=playtest` first, and room 1 is played for real on `PROFILE=demo` Mon Nov 2.
- Only cuts 1 to 3 are realistic to reverse before Nov 3.

**Fix:** add a one-line pointer in §11:
> Day-level contingencies (Mon Oct 26 slip rule, video v0 Wed Oct 28, playtest on `PROFILE=playtest`, room 1 on `PROFILE=demo` Mon Nov 2, only cuts 1 to 3 realistically reversed) live in delivery-plan.md §Day plan and bind the epics' sequencing.

## Additions in the PRD not in the spec (not contradictions)

FR-22 (demo results excluded), FR-33's 24 h hosted log deletion, FR-17's refusal to start Hosted mode with a Guide model, FR-19's skipped Card, and NFR-7's single retry come from the architecture spine or `epics.md`. They are consistent with the spec. FR-37 (Clue cards) matches the spec's Tier 1.5 scope and the $0.16 figure. A-14 (Clue cards never gate T1) is a reasonable inference. §7 Aesthetic and Tone is correctly tagged as an inference: neither the spec nor the brief supplies tone or visual references, and nothing in §7 conflicts with them.
