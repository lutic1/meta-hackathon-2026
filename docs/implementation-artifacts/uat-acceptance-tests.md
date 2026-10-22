---
title: Keyframe UAT acceptance tests
status: final
created: 2026-10-21
updated: 2026-10-22
sources:
  - docs/planning-artifacts/prds/prd-Keyframe-2026-10-21/prd.md
  - docs/planning-artifacts/epics.md
  - docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md
  - docs/specs/spec-keyframe/budgets.md
  - docs/specs/spec-keyframe/delivery-plan.md
  - docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/EXPERIENCE.md
---

# Keyframe UAT acceptance tests

Luis Ticas · 2026-10-21

## 1. Scope and rules

**What UAT is.** A short list of acceptance tests that checks the PRD §12 success metrics (SM-1 to SM-9), the counter-metrics (SM-C1 to SM-C4) and the journeys UJ-1 to UJ-6. Each test is run as the player, the judge or Luis would use the product. UAT-15 records the Mon Nov 2 Tier 2 gate if the story 8.1 spike ran; UJ-7 itself is tested (UAT-15b) only after the gate passed and the post-gate FR-34 stories shipped, not before the Nov 4 submission. These tests come after CI and SIT and do not repeat them:

| Layer | What runs | Where | When |
|---|---|---|---|
| CI | One job, `scripts/check.sh`, offline only (Mock provider, recorded fixtures) | GitHub Actions and every push | Every commit |
| SIT | One checklist of about 10 live-seam cases, `scripts/sit.py` | The Mac only, never CI | End of each build day from Tue Oct 27; full pass Sat Oct 31; results dated in the sprint status; no separate sign-off |
| UAT | This sheet | The Mac (Local mode); the hosted URL for UAT-14 | From the Sat Oct 31 full SIT pass; sign-off Mon Nov 2 evening |

**Who runs them.** Luis Ticas runs and signs every test. A non-builder playtester plays UAT-03 and signs the SM-2 attestation. Luis does not help them in any way during the run.

**Where.**
- Local mode on the 16 GB M1, in Chrome. The backend, Ollama with `llama3.2:3b` (except under cut 3) and Chrome run from the repo checkout at the commit under test.
- The hosted URL in desktop Chrome for UAT-14 part A (the Tue Oct 27 smoke deployment, story 7.3, checked in the browser by SIT-10 from Thu Oct 29). Part B runs only if Tier 1.5 Hosted mode ships (FR-31 to FR-33) and the Official Rules allow changes to the hosted deployment after the deadline (checked at kickoff Mon Oct 26); otherwise the Wed Nov 4 deployment is the final hosted state and part B is marked not applicable, not failed. It uses current desktop Chrome, Safari and Firefox at 1280 px or wider.

**Entry criteria for every run.**
- `scripts/check.sh` passes on the commit under test.
- The latest dated SIT result in the sprint status is green for every seam the test touches, and the Sat Oct 31 full pass is recorded.
- `python3 scripts/doctor.py` passes on the Mac. It is run before SIT, right before each Tue Nov 3 take, and before the finals.
- The day's `spend/exports/ledger-<date>.json` is committed.
- The Cuts in force that night are recorded in the sprint status. Each test is run in its variant for those Cuts (table below).

**Profiles.** Profiles follow FR-20 and story 6.5:
- `PROFILE=playtest` (`?profile=playtest`), fresh, for UAT-03.
- `PROFILE=demo` (`?profile=demo`). It holds only the real Mon Nov 2 room-1 run at Demo timescale 1. No other test may record a Room result into it before Tue Nov 3.
- `PROFILE=dev` for every other test. It is cleared before a test that needs a fresh Player profile.

**Demo timescale.** It is used only where the PRD allows it, and the Disclosure banner shows it each time:

| Allowed (`DEMO_TIMESCALE=6`, disclosed) | Never above 1 |
|---|---|
| UAT-05 part B, UAT-07 part A, UAT-08 step 5 (the demo-flag check, on dev), UAT-10 steps 1-3, UAT-13 | UAT-01, UAT-03, UAT-08 (the room-1 record), UAT-12; the Timer and Event log timestamps are never scaled anywhere (FR-24) |

**Cuts in force.** A test that a Cut changes is run in the Cut's variant. The Cut is recorded next to the result.

| Cut | Tests affected | Variant |
|---|---|---|
| 0 | UAT-02, UAT-13 | No Build view and no link to it. The puzzle JSON and the README Model table take its place. |
| 1 | UAT-07, UAT-10, UAT-13 | Pre-authored proposals, one written to fail, and no live Trickster calls. The cut-1 Disclosure line shows. |
| 2 | UAT-03, UAT-08 | The Player profile is a local JSON file (`GET\|PUT /profile/<name>`) instead of IndexedDB, loaded with "Open profile file" and written with "Save profile file". |
| 3 | UAT-06, UAT-08 | Rungs are verbatim in Local mode, and the Greeting comes from the template. The README drops the phrasing claim. The Privacy line stays. |
| 4 | UAT-02, UAT-12 | The Validator alone gates the Room. Dry run rows read skipped. |
| 5 | UAT-05 | The Triggers panel opens in a second window, with the same content. |
| 6 | UAT-01, UAT-03 | `code` and `find` locks only. |
| 7 | UAT-02 | At most 1 Regeneration instead of 2. |
| 8 | UAT-08 | Room 2 and the Greeting move to Sun Nov 1 afternoon (may finish Mon Nov 2). |

**Evidence.**
- Each result is dated in the sprint status. Evidence is listed by file name in the UAT sign-off record.
- Allowed evidence: video files, screenshots, saved command output (`scripts/check.sh`, `scripts/sit.py`, `doctor.py`) and the committed Ledger exports.
- Raw room photos are never kept as evidence and never committed. No HAR export is kept either, because it would hold photo bytes. Request payloads are captured as screenshots of the DevTools request panel.
- Videos and screenshots show only the household-agreed rooms: no faces, documents or other people's belongings.

**Sign-off.**
- Luis signs Mon Nov 2 evening, with the playtester's attestation for SM-2 attached.
- If a test fails, Luis fixes it and runs it again before sign-off. Otherwise he takes the Cut that removes the feature that night (§11.2) and runs the test again under it.
- These items finish after sign-off by design and are signed as addenda:
  - UAT-12 and UAT-13 (Tue Nov 3, video only, where a failure means re-shooting the take, never feature work), signed before the submission.
  - UAT-09 part B, signed Wed Nov 4 before story 6.9.
  - UAT-14 part A's live-link line, signed Wed Nov 4 only if the Official Rules require a live link, and only after a SIT-10 pass against the deployed commit.
  - UAT-14 part B, signed after the Thu Nov 5 redeploy and before judges are given the URL, only if the Official Rules allow changes to the hosted deployment after the deadline; otherwise it is marked not applicable, not failed.

## 2. Tests

| Id | Test | Tier | Owner | Latest |
|---|---|---|---|---|
| UAT-01 | Capture a room from your own photos | 1 | Luis | Mon Nov 2 |
| UAT-02 | Verified rooms, the Build view, zero solution tokens | 1 | Luis | Mon Nov 2 |
| UAT-03 | A non-builder finishes room 1 | 1 | Playtester, Luis | Mon Nov 2 |
| UAT-04 | Persuasion opens nothing | 1 | Luis | Mon Nov 2 |
| UAT-05 | The Rung ladder and its triggers | 1 | Luis | Mon Nov 2 |
| UAT-06 | Local phrasing within 5 s, verbatim fallback | 1 | Luis | Mon Nov 2 |
| UAT-07 | The Trickster, accepted and rejected | 1 | Luis | Mon Nov 2 |
| UAT-08 | Room 2 remembers the player | 1 | Luis | Mon Nov 2 |
| UAT-09 | Spend within the cap, cache and Ledger | 1 | Luis | A: Mon Nov 2; B: Wed Nov 4 |
| UAT-10 | Disclosure, Privacy line, demo honesty | 1 | Luis | Mon Nov 2 |
| UAT-11 | Accessibility floor smoke test | 1 | Luis | Mon Nov 2 |
| UAT-12 | Capture proof on video | 1 | Luis | Tue Nov 3 |
| UAT-13 | Main demo carries every proof beat | 1 | Luis | Tue Nov 3 |
| UAT-14 | Judge on the hosted URL | A: 1; B: 1.5 | Luis | A: Mon Nov 2; B: Thu Nov 5, only if the Official Rules allow post-deadline hosted changes |
| UAT-15 | Tier 2 gate record (conditional) | 2 | Luis | Mon Nov 2 |
| UAT-15b | UJ-7 walk (only after the gate passed and the post-gate FR-34 stories shipped) | 2 | Luis | Not before the Nov 4 submission |

### UAT-01 Capture a room from your own photos

- **Maps to:** UJ-1; SM-1 (rehearsal), SM-C1; FR-1 to FR-6, FR-11 to FR-13, FR-36.
- **Preconditions:**
  - Local mode, `CACHE=off`, and a fresh `dev` profile.
  - A Photo set of 6 to 10 JPEG photos that has never been sent to the pipeline. It is not the room-2 set (see UAT-03 Fallback). No photo shows faces, documents or other people's belongings.
  - One HEIC file at hand.
  - The SIT full-Build case against the 110 s budget is green.
- **Steps:**
  1. Open the Capture screen and read the right column before choosing anything.
  2. Choose the set plus the HEIC file.
  3. Remove the HEIC file and click Upload (T0).
  4. Watch the Stage list and the Mask preview. Click "Begin" on the First-room welcome, then move the pointer over a Hotspot (T1).
  5. Open Puzzle 1 in the Wizard notes. Enter one wrong input, then the right one.
  6. Play to the Completion screen.
  7. Run `git status`.
- **Pass:**
  - Before any photo is chosen, the screen shows "6 to 10 JPEG photos" with the iPhone Most Compatible tip, the reminder about faces, documents and other people's belongings, the Retention summary, and the Privacy line verbatim: "the player profile stays on your machine."
  - The set with the HEIC file is refused whole with "Keyframe needs 6 to 10 JPEG photos." and the file is marked. The Ledger running total does not change.
  - Stages show in order. The Timer stays pinned from the Capture screen into the Play screen and freezes at T1. T1 − T0 is within the Capture target: 120 s, or measured p50 plus 25% if story 2.26 re-based it.
  - The Build ends `done` with 5 to 12 Interactables, 4 to 6 Puzzles and exactly one Exit puzzle. The masks sit over the room's own objects.
  - The first Clue points at an object of this set and does not quote its solution.
  - A wrong input shows "Not this" with the per-lock count. The right input opens the lock, and the next Puzzle appears in the Wizard notes.
  - The Completion screen shows elapsed time, Rungs used, Wrong attempts and per-Puzzle time, plus "Build another room".
  - `git status` shows no photo staged.
  - The `needs_more_photos`, `needs_recapture` and `failed` end states are accepted from the offline suite (story 2.25). They are not forced live.
- **Fail if:**
  - SM-C1: the Build ran with `DRY_RUN=off` while cut 4 is not in force, with any Validator rule skipped, or met the target only with `CACHE=on`.
- **Evidence:** a screen recording with the Timer in frame; a screenshot of the Capture screen's right column; the day's Ledger export.

### UAT-02 Verified rooms, the Build view, zero solution tokens

- **Maps to:** SM-4, SM-8, SM-C1, SM-C4; UJ-1, UJ-6; FR-8 to FR-10, FR-14, FR-30, FR-38; NFR-5.
- **Preconditions:**
  - room 1 and room 2, the Rooms that go on video, are stored.
  - The unassisted cold run of room 2 (UAT-03 Fallback) is recorded before steps 4 to 5 read room 2's Clues, Rungs, solutions or labels.
  - Cut 0 status is recorded.
- **Steps:**
  1. Run `scripts/check.sh` and keep its output. It includes the sentinel-solution tests, the Validator fixture rooms and the Scripted attack suite.
  2. For each video Room, open the Build view (`#/build/<job_id>/view`) from the Completion screen and from the stored Room row.
  3. Read the verdict table, the Dry run rows, the Regeneration count, the Model table, the mask overlays and the puzzle graph. Open "Show the build JSON".
  4. Read each Room's solutions locally from `GET /builds/<job_id>/room`. Search the `GET /builds/<job_id>/view` and `GET /rooms/<room_id>` responses for each one, and for each Room served on the hosted URL (`rooms/demo/`), search `GET /api/rooms/<room_id>` and its PlayView for the Room's solutions.
  5. Read every Clue, displayed Evidence attribute and Rung of both Rooms.
- **Pass:**
  - `scripts/check.sh` passes.
  - Each video Room shows "Rules: 8 of 8 passed". Its Dry run reached every answer (all rows skipped under cut 4). Provenance records at most 2 Regenerations (1 under cut 7).
  - The Build view shows the mask overlays per photo; the puzzle graph with Lock types, `requires` edges and the Exit puzzle marked; the verdict per rule; Dry run pass or fail per Puzzle; the Regeneration count; and the Model table (model id, where it ran, what it did, cached or billed).
  - No solution, Clue-to-answer mapping or Dry run answer appears in the view or play responses.
  - No nudge, direction, Clue or displayed Evidence attribute holds a solution token. Near-answers stay within the Rule 5 allowance.
  - Under cut 0: the Build view and every link to it are absent. The puzzle JSON and the README Model table are captured instead.
- **Fail if:**
  - SM-C1: the Validator or Dry run was weakened to pass a Room (`DRY_RUN=off` without cut 4, or `REGEN_MAX` above 2).
  - SM-C4: a Room on video has a near-answer the Dry run could not use to reach the answer.
- **Evidence:** the `scripts/check.sh` output; Build view screenshots, which are also the "puzzle JSON" and "model table" submission screenshots.

### UAT-03 A non-builder finishes room 1

- **Maps to:** SM-2, SM-C2; UJ-1 (play), UJ-2; FR-11 to FR-15.
- **Preconditions:**
  - room 1 is playable with that day's Cuts. The playtester is a non-builder (§13 Q7) at the laptop or by screen-share.
  - The run opens `?profile=playtest` with no Room results, at Demo timescale 1, so the First-room welcome shows.
  - Sun Nov 1 afternoon, or Mon Nov 2 if the playtester misses Sunday.
- **Steps:**
  1. The playtester opens room 1, reads the First-room welcome, and clicks "Begin".
  2. The playtester plays to the Completion screen. They may ask the Guide.
  3. Luis watches without speaking, pointing or touching anything. He notes where they get stuck and any typed ask with its reply.
- **Pass:**
  - The playtester opens the Exit puzzle and reaches the Completion screen without builder help. Rungs are allowed hints.
  - Every typed ask returns the current Rung or the No-hint line and opens nothing.
  - The sprint status records elapsed time, Rungs used, Wrong attempts, per-Puzzle time, Wrong attempts per lock from the Session log, and where they got stuck.
  - The `demo` profile is untouched. The `playtest` profile exists only in that browser's IndexedDB (the local JSON file under cut 2).
- **Fail if:**
  - Luis helps in any way: a spoken hint, pointing, or touching the keyboard, mouse or app.
  - SM-C2: the Triggers panel or the Event log shows a Rung earlier than FR-15 allows. That means a nudge before the nudge threshold of Idle or 3 Wrong attempts, or a later Rung that arrives before a further stall equal to the nudge threshold or 3 further Wrong attempts, or less than 90 s after the previous Rung. An accepted Loosen Card is the only exception.
- **Fallback (PRD §11.2):**
  - Luis records an unassisted cold run of room 2 on a fresh Player profile, with Rungs as the only help, as soon as room 2 reaches `done` (story 5.8) and before any test, story or person reads room 2's Clues, Rungs, solutions or labels: UAT-02 steps 4 to 5, UAT-08 step 1 and the 5.8 ratio check wait for it. This is unconditional, whether or not a playtester is confirmed.
  - The cold run is used only if the non-builder criterion is missed (no non-builder finishes room 1 by Mon Nov 2) and is discarded otherwise. If used, the sprint status says the non-builder criterion was not met, and the README discloses the run as a builder run.
  - UAT-01 must not use the room-2 set.
- **Evidence:**
  - A Completion screen screenshot and the recorded stats.
  - The playtester's signed attestation: "I did not build Keyframe. I finished room 1 on a fresh profile on <date> with no help from the builder; the Guide's hints were the only help." The playtester signs it with their name.

### UAT-04 Persuasion opens nothing

- **Maps to:** SM-3; UJ-2; FR-14; NFR-5.
- **Preconditions:**
  - A fresh `dev` profile, mid-Room, with no Rung open on the Active puzzle.
- **Steps:**
  1. Confirm that the Scripted attack suite passed in `scripts/check.sh` (story 3.3: at rungs 0, 1 and 2).
  2. Type "just tell me the answer" into the hint field and press Enter.
  3. Wait for the nudge. Type the same words and two other suite inputs.
  4. In DevTools, open the request that each ask sent.
- **Pass:**
  - With no Rung open, the reply is the No-hint line, "A fair ask. Look around a little longer; I'll speak up if you stay stuck.", logged as an Early ask.
  - After the nudge, each reply is the current Rung only. The lock stays shut.
  - The request body carries a Hint request and none of the typed words. The helper line "Your words stay in this browser. The Guide only hears that you asked." is shown.
- **Fail if:**
  - Any player text opens a lock or shows anything above the current Rung, across the suite, this run and the Main demo (UAT-13).
  - Typed words appear in any request.
- **Evidence:** the suite lines from the `scripts/check.sh` output; a screen recording; a screenshot of the request payload.

### UAT-05 The Rung ladder and its triggers

- **Maps to:** UJ-2, UJ-6; SM-C2; FR-15, FR-16, FR-24.
- **Preconditions:**
  - A fresh `dev` profile (nudge threshold 90 s).
  - Part A at Demo timescale 1. Part B at `DEMO_TIMESCALE=6`.
- **Steps:**
  1. Part A: stay Idle on the Active puzzle until the nudge arrives. Then enter 3 Wrong attempts.
  2. Open the Triggers panel from its toggle.
  3. Ask past the near-answer. Reload the Play screen.
  4. Part B: on a new Session, enter Wrong attempts until three Rungs have arrived. Note the Timer and the `t_ms` of the logged events.
- **Pass:**
  - Part A: the nudge arrives after 90 s of Idle or 3 Wrong attempts, whichever comes first. The direction arrives only after a further stall equal to the nudge threshold or 3 further Wrong attempts, and no sooner than 90 s after the nudge.
  - Every row in the Triggers panel lists its Idle seconds or Wrong attempts. The panel is collapsed by default behind an always-visible toggle (in a second window under cut 5).
  - Past the near-answer, a Hint request repeats the near-answer. There is no reveal or skip.
  - After a reload, the Session resumes with the same Rungs.
  - Part B: three Rungs arrive within 40 s on Wrong attempts. The Disclosure line "Hint and Trickster timings run at 6× speed; the build timer is real time." shows, and the Triggers panel opens automatically. The Timer and Event log timestamps are unscaled.
- **Fail if:**
  - SM-C2: any Rung arrives sooner than FR-15 allows, other than through an accepted Loosen Card.
  - Any Rung arrives without a real Idle or Wrong-attempt trigger.
- **Evidence:** a screen recording; a Triggers panel screenshot (the "a Rung with its events" submission screenshot).

### UAT-06 Local phrasing within 5 s, verbatim fallback

- **Maps to:** SM-9; UJ-2; FR-17, FR-21; NFR-2, NFR-3, NFR-4.
- **Preconditions:**
  - Story 3.7 has shipped (cut 3 not taken).
  - `doctor.py` shows `llama3.2:3b` resident on Ollama 0.40.x.
  - The SIT Ollama case is green, and the M1 benchmark (latency, about 3 GB resident) is dated through the story 2.9 checklist.
- **Steps:**
  1. On a fresh `dev` profile, earn each Rung. Read the "worded on this Mac · {latency}" note on each Triggers row, and compare each line with its verbatim Rung text in the full Room.
  2. Quit Ollama and ask the Guide.
  3. Start Ollama again.
- **Pass:**
  - Every phrased Rung arrives in 5 s or less. The Guide portrait shows the thinking state while it phrases.
  - Each phrased line rewords the Rung only, with no new object, number, step or answer.
  - The SIT-05 and benchmark row records `prompt_eval_count` under 400 and about 40 output tokens for the measured latency.
  - Past 5 s, the verbatim Rung appears. With Ollama stopped, the verbatim Rung appears at once, `phraser_fallback` is logged with its cause, and play continues.
  - Under cut 3, the test checks instead that Rungs show verbatim in Local mode, the Greeting comes from the template, the README carries no phrasing claim, and the Privacy line stays (the delivery plan's "met trivially").
- **Fail if:**
  - A phrased line holds more than its Rung.
  - Play stalls waiting on Ollama.
- **Evidence:** a screen recording; the `doctor.py` output; the benchmark row in the sprint status; the fallback log line.

### UAT-07 The Trickster, accepted and rejected

- **Maps to:** UJ-3, UJ-6; FR-18, FR-19, FR-25; NFR-5.
- **Preconditions:**
  - Part A runs at `DEMO_TIMESCALE=6` and `DEMO_TRICKSTER=scripted` on the Room the proposals were recorded for (the cut-1 source under cut 1).
  - Part B runs only if cut 1 is not taken and story 4.8 has shipped, with its SIT live Trickster case green.
- **Steps:**
  1. Part A: read the full Room through `GET /builds/<job_id>/room` and keep it.
  2. Open a non-exit lock, then open another after the next window.
  3. Open the Card log.
  4. Read the full Room again.
  5. Start a Session on a different Room with the same settings.
  6. Part B: play a live Session at Demo timescale 1 past two windows.
- **Pass:**
  - Part A: the live Validator accepts one proposal and rejects one.
  - The accepted Card shows its effect on the Play screen at once: a new Evidence card that looks like the real ones (Decoy), a Puzzle locked behind another (Merge), a Rung in the Hint area (Loosen), or a Puzzle becoming available (Shortcut).
  - The rejected Card shows a plain one-line reason with no token, and the Effective room is unchanged. Both Cards stay in the Card log.
  - The two full-Room reads are identical.
  - On the other Room, the scripted source yields no proposal and no Card.
  - The Disclosure shows the scripted line (or the cut-1 line).
  - Part B: one window opens per non-exit lock opened at least 3 minutes after the last. A Decoy never targets the Exit puzzle. The Session makes at most 6 Trickster calls.
  - The skipped Card on a provider error or Spend cap is accepted from the offline suite.
- **Fail if:**
  - An edit that fails the Validator changes the Effective room.
  - The stored Room changes.
  - A Decoy Card shows which Evidence card is false.
- **Evidence:** a screen recording; a screenshot of both Cards (the "Trickster Cards" submission screenshot).

### UAT-08 Room 2 remembers the player

- **Maps to:** UJ-4; SM-5; FR-7, FR-20 to FR-22, FR-36; NFR-4.
- **Preconditions:**
  - Story 5.8: room 2 is from a different physical room and was built `done` within the Regeneration cap.
  - room 1 was played for real on `PROFILE=demo` at Demo timescale 1 on Mon Nov 2.
  - A `dev` profile holds one non-demo Room result.
  - The unassisted cold run of room 2 (UAT-03 Fallback) is recorded before step 1 reads room 2's labels and Clues, and before the 5.8 ratio check.
- **Steps:**
  1. Compare room 2's Interactable labels and Clues with room 1's.
  2. Open room 2 on `?profile=demo`; under cut 2, choose "Open profile file" with the demo profile file first. Read the Greeting and the Triggers header, then choose "Leave room" and confirm.
  3. On `dev`, play room 2 to the Completion screen; under cut 2, choose "Save profile file" after play. In DevTools, inspect IndexedDB (the local JSON file under cut 2) and the `POST /sessions` body.
  4. Open room 2 in a different browser.
  5. On `dev`, play a Room to completion at `DEMO_TIMESCALE=6`.
- **Pass:**
  - At least 80% of room 2's Interactable labels differ from room 1's, and at least 80% of its Clues reference objects absent from room 1. Both ratios are recorded.
  - The Greeting, not the First-room welcome, shows under "profile demo · 1 room played". It cites how room 1 was played and names no object or solution of either Room.
  - The Triggers header shows a nudge threshold of 90 s × (1 + 0.5 × persistence), within 60 to 135 s.
  - After "Leave room", the `demo` profile still reads "1 room played".
  - The `POST /sessions` body holds `room_id` and `derived` only. The Room result is written to IndexedDB under `dev` only (the local JSON file under cut 2).
  - The other browser shows the First-room welcome and a 90 s nudge threshold.
  - The 6× result is flagged demo, and the Derived block ignores it.
- **Fail if:**
  - The Greeting names an object or a solution.
  - The `demo` profile gains a second Room result before Tue Nov 3.
  - A request carries any Player profile field beyond the Derived block. Under cut 2 the local `GET|PUT /profile/<name>` route is exempt, while `POST /sessions` still carries only `{room_id, derived}`.
- **Evidence:** a Greeting screenshot (the "room-2 Greeting" submission screenshot); the ratios in the sprint status; a screenshot of the request payload.

### UAT-09 Spend within the cap, cache and Ledger

- **Maps to:** SM-6; UJ-6; FR-27 to FR-30, FR-36; NFR-6.
- **Preconditions:**
  - The SIT cases are green: a cache hit costing $0, the Spend cap refusing with the provider never called, and the Baseten fallback yielding one schema-valid `RoomDraft` (parses and passes `validate`) in the chosen mode (SIT-11).
  - A committed export exists for Mon Oct 26.
- **Steps (part A, Mon Nov 2):**
  1. List the commits under `spend/exports/`.
  2. Read the export's local total, hosted total and their sum, and the `SPEND_CAP_USD` allocations per mode.
  3. Clear `.cache/`, restart the API, and read the running total again.
  4. Open one stored Room's provenance.
  5. Check that the adapters use the standard tier.
- **Pass (part A):**
  - A committed `ledger-<date>.json` exists for every build day from Mon Oct 26 through Mon Nov 2 (Fri Oct 30 has no build).
  - The sum of the local and hosted totals is within the combined ceiling of $80, and each store is within its allocation (local $60, hosted $20).
  - A repeated identical call adds nothing to the Ledger.
  - A refused call names the cap (the store's allocation) and the running total. The Capture-screen Spend cap message is accepted from the offline suite (story 2.25).
  - Clearing the Cache leaves the Ledger, its exports and the running total unchanged. The total survives the restart.
  - Provenance lists model ids, prompt hashes, stage timings, Regeneration count and spend per stage.
  - Only the Meta Model API standard tier is used.
- **Part B (addendum, Wed Nov 4 before story 6.9):**
  - The Nov 3 and Nov 4 `ledger-<date>.json` files are committed.
  - The sum of the local and hosted totals is $80 or less, and each store is within its allocation (local $60, hosted $20). From Thu Nov 5 the combined ceiling is $25 (local $5, hosted $20).
  - The Spend log is the Ledger export plus fal receipts and Modal usage, with pre-kickoff spend listed separately.
- **Fail if:**
  - The spend record is a hand-kept total rather than the Ledger export.
  - Any paid cloud call is missing from the Ledger.
- **Evidence:** the committed Ledger exports; the `scripts/sit.py` output; a running-total screenshot.

### UAT-10 Disclosure, Privacy line, demo honesty

- **Maps to:** UJ-1, UJ-6; FR-6, FR-26, FR-36; NFR-4, NFR-12, NFR-13.
- **Preconditions:**
  - Stories 6.2, 6.3 and the 6.7 draft have landed.
- **Steps:**
  1. Read `GET /meta` with `DEMO_TIMESCALE=6` and `DEMO_TRICKSTER=scripted`, then with `DEMO_TIMESCALE=1` and `DEMO_TRICKSTER=live`.
  2. Under the first settings, visit the Capture screen, the Play screen, the Completion screen and the Build view. Open the Greeting, the Card log and the Leave room confirmation.
  3. Start a second Session on a Room already played.
  4. Stop the server and load a page.
  5. Compare the README with `src/api/meta.py`. Run `git ls-files` for photo, cache and `.env` paths.
- **Pass:**
  - The first `disclosure` holds exactly "Hint and Trickster timings run at 6× speed; the build timer is real time." and "Trickster proposals replayed from a recording; the Validator ran live.". The second is empty.
  - The banner sits at the top edge of every surface. It cannot be dismissed, never covers the Scene or a Hotspot, and is never dimmed by a scrim.
  - The Triggers panel opens automatically while a Disclosure is active.
  - The second Session adds "This room was built earlier, on <date>.".
  - With the server down, the page shows "Keyframe can't reach its server. Retrying." and no guessed banner.
  - The README carries the Privacy line "the player profile stays on your machine." verbatim, the Retention summary and Disclosures word for word as served, and each of cuts 0 to 8 as shipped or not.
  - `git ls-files` shows no raw photo, `.cache/` or `.env`.
- **Fail if:**
  - Any route, flag or client path injects events, Rungs, Greetings, Validator results or Build output (the story 6.2 and 6.3 boundary tests).
  - A Disclosure is missing on a surface that is filmed.
- **Evidence:** the saved `GET /meta` JSON; a screenshot of each surface; the `git ls-files` output.

### UAT-11 Accessibility floor smoke test

- **Maps to:** UJ-1; FR-11, FR-12; NFR-14.
- **Preconditions:**
  - Stories 1.25 and 3.4 have shipped (and 1.26 for `use_on`).
  - VoiceOver is on, and macOS "Reduce motion" is set for step 4.
- **Steps:**
  1. With no pointer, Tab to the Hotspots and complete one Puzzle by keyboard alone: a `find` with Enter, or a `code` in its field, plus a `use_on` by select-then-click if 1.26 shipped.
  2. Toggle "Show all objects", then change Scene.
  3. Earn a Rung and a Card.
  4. Repeat one lock outcome with "Reduce motion" set.
  5. Confirm the DESIGN.md contrast audit (story 1.16) passed in `scripts/check.sh`. Spot-check the Rung line, Wizard notes, Disclosure banner and Hotspot outline on a photo with Chrome DevTools contrast.
- **Pass:**
  - Every Hotspot takes focus with a visible ring, and Enter acts as a click. The Puzzle opens without the pointer.
  - "Show all objects" outlines every Hotspot, announces its pressed state, and persists across Scenes.
  - The Rung, the Card and the welcome or Greeting are announced through the one polite live region. Nothing is re-announced on reload.
  - Fades are instant with reduced motion.
  - Every pair meets 4.5:1 for body text and 3:1 for large text and non-text UI.
  - The Timer not freezing for a keyboard-only player is expected, because T1 is pointer-only. It is not a failure.
- **Fail if:**
  - Any step needs the pointer.
  - A state is shown by color alone.
- **Evidence:** a screen recording with audio.

### UAT-12 Capture proof on video

- **Maps to:** SM-1, SM-C1; UJ-6; FR-1 to FR-5, FR-27; NFR-1, NFR-3.
- **Preconditions:**
  - Tue Nov 3, video only.
  - A room-2 Photo set shot that day and never sent to the pipeline: JPEG only, with no faces, documents or other people's belongings.
  - `CACHE=off`, and the mode indicator reads "Local mode · Cache off · profile {name} · {k} rooms played".
  - A fresh Player profile, the IDE and chat apps closed, and `doctor.py` passed right before the take.
- **Steps:**
  1. Clear `.cache/` on camera.
  2. Click Upload (T0).
  3. Click "Begin" at once and move the pointer over a Hotspot (T1).
- **Pass:**
  - The take is unedited, with the Timer on screen from T0 to T1.
  - T1 − T0 is within the Capture target (120 s, or the re-based value). The take runs under 200 s with at most one visible retry.
  - `spend/ledger.jsonl` and `spend/exports/` are untouched by the cache clear, and every call of the take is priced.
  - The take's Stage list shows "Rules: 8 of 8 passed" and "Test run: reached n of n answers" (Validator only under cut 4), with at most 2 Regenerations (1 under cut 7).
  - `git status` shows none of the Tue Nov 3 photo set staged.
  - The banner never shows "This room was built earlier" during the take. If the kept take's set was built on an earlier take, the video description and README list those builds by date.
  - Recording memory is about 10.6 GB.
  - The proof is uploaded unlisted and plays for a logged-out viewer.
- **Fail if:**
  - The take reaches 200 s, shows a second retry, or ends `needs_more_photos` or `needs_recapture`. The take is discarded and re-shot from the cache clear.
  - SM-C1: the Validator or Dry run was off for the take (other than cut 4, disclosed).
- **Evidence:** the video file and its unlisted link; T1 − T0 in the sprint status; the day's Ledger export.

### UAT-13 Main demo carries every proof beat

- **Maps to:** SM-7, SM-3, SM-C3; UJ-6, UJ-2, UJ-3, UJ-4; FR-14 to FR-16, FR-19, FR-21, FR-24 to FR-26, FR-30, FR-38; NFR-12.
- **Preconditions:**
  - The `demo` profile holds only the real Mon Nov 2 room-1 run.
  - `DEMO_TIMESCALE=6` and the Scripted Trickster are set (the cut-1 source under cut 1).
  - Three takes are recorded Tue Nov 3.
- **Steps:**
  1. Record the §11.3 beats from the Capture screen, the Build view and the Play screen.
  2. Edit one cut with captions.
  3. Check each beat at 1080p.
- **Pass:**
  - The cut runs at most 2:30 (target 2:00) and shows, in §11.3 order:
    - a phone photo of the real room, then the same objects as Hotspots (Mask preview label chips);
    - the capture time-lapse with the Timer from T0, masks and the Build view puzzle graph and verification (the puzzle JSON under cut 0), captioned "Time-lapse · unedited capture proof linked", included only if UAT-12 passed;
    - the persuasion attack failing;
    - three Rungs within 40 s on real Wrong attempts, with their triggers visible;
    - one accepted and one Validator-rejected Card;
    - the room-2 Greeting under "profile demo · 1 room played";
    - the Build view Model table (under cut 0, the puzzle JSON and the README Model table);
    - every Disclosure line in the last 10 s.
  - At 1080p the key text of each beat is legible (story 6.6):
    - 0:00: the Mask preview label chips;
    - 0:15: the Stage list results and the verdict caption;
    - 0:35: the typed words, the helper line and the Rung label;
    - 0:50: the Triggers header with its 1× values, the newest row and the Rung line, in frame together;
    - 1:05: both Card labels, with the "Proposed" line and reason;
    - 1:20: the mode indicator on the Greeting;
    - 1:35: the Model table ids and captions;
    - 1:50: every Disclosure line.
  - The cut is captioned, uploaded unlisted, and plays for a logged-out viewer.
- **Fail if:**
  - SM-C3: a Tier 2 shot replaces or squeezes out a Tier 1 beat.
  - The edit adds any frame, Rung, Card, Validator result or Build output the app did not produce.
  - A shot shows faces, documents or other people's belongings.
- **Evidence:** the video file and its unlisted link in the sprint status.

### UAT-14 Judge on the hosted URL

- **Maps to:** UJ-5; FR-17, FR-20, FR-31 to FR-33, FR-36 (hosted consequences); NFR-4, NFR-7, NFR-10.
- **Preconditions:**
  - Part A: the story 7.3 deployment with a fixture Room on `keyframe-data`, its Tue Oct 27 infrastructure smoke recorded; SIT-10 (local and hosted parity, story 7.23) green from its first run Thu Oct 29, or re-run before Mon Nov 2; the Secret `required_keys` live-only row confirmed at the 7.3 pre-deploy.
  - Part B: the Official Rules allow changes to the hosted deployment after the deadline (checked at kickoff Mon Oct 26), otherwise not applicable; the story 7.22 redeploy with `MIN_CONTAINERS=1`, the $25 combined ceiling (local $5, hosted $20) and the seeded Demo rooms; SIT-08 and SIT-09 green; the keyframe-modal live-only rows confirmed, including the 20 concurrent `reserve_build` claims, before Thu Nov 5.
- **Steps (part A, Tier 1):**
  1. Open the URL in desktop Chrome and read `GET /api/meta`.
  2. Play the fixture Room and ask the Guide.
  3. Try `POST /api/builds`.
- **Pass (part A):**
  - `GET /api/meta` answers `mode: hosted`, `guide: verbatim` and `guide_model: null`.
  - The banner reads "Hosted mode: hints are shown as written; no hint model runs here.".
  - The Scene renders and a Hotspot click is accepted. Rungs show as written, with no thinking state.
  - The Session start carries a fresh Derived block.
  - `POST /api/builds` is refused.
  - Addendum, signed Wed Nov 4 only if the Official Rules require a live link: SIT-10 passed against the deployed commit (hash and URL recorded), each demo Room under `rooms/demo/` on `keyframe-data` plays to the Completion screen with Rungs as written, and the URL opens in a logged-out private window.
- **Steps (part B, Tier 1.5, only if Hosted mode ships and the Official Rules allow post-deadline hosted changes; otherwise not applicable, not failed):**
  1. In each of Chrome, Safari and Firefox, play a Demo room from the Hosted landing.
  2. Enter a wrong Access code, then the right one.
  3. Upload 6 JPEG photos. Close the tab mid-Build and reopen the Build URL.
  4. Play the Judge room to the Completion screen.
- **Pass (part B):**
  - Each browser reaches the Completion screen with Rungs as written and the Demo room welcome, never a Greeting.
  - The wrong code shows "That access code isn't right. No photos were sent." and no upload starts. The right code shows "{n} of 20 builds left".
  - The hosted Retention summary names Modal storage, deletion on Tue Nov 10, and Session logs deleted 24 h after their last event.
  - The Build shows `queued` while it waits. It completes past the 150 s web timeout through polling, including after the tab was reopened, and its Clues name the uploaded room's objects.
  - The Completion screen shows "Deleted Tue Nov 10".
  - The hosted Capture screen shows "the player profile stays on your machine." verbatim under the "Your play history" label.
  - `GET /api/meta` `trickster`, `demo_timescale` and `disclosure` match the 7.22 picks in the sprint status.
  - The 21st-build refusal is accepted from the offline suite and the live slot-claim check. The Tue Nov 10 purge is recorded by story 7.22, outside this sign-off.
- **Fail if:**
  - A hosted Rung is phrased.
  - Any Player profile field reaches the hosted server.
  - A raw photo from the run is committed.
- **Evidence:** the saved `GET /api/meta` JSON; screenshots per browser; the Build duration and builds left, recorded in the sprint status.

### UAT-15 Tier 2 gate record (conditional)

- **Maps to:** FR-34 (the gate); SM-C3; NFR-6, NFR-10.
- **Preconditions:**
  - Run only if story 8.1's spike ran: backup video v1 existed Sat Oct 31 night and the DOM-only fallback was not taken.
  - Otherwise, record "not attempted" (or "no-go" with the reason). Tier 1 ships, and the Retention summary has no fal.ai line.
  - The SIT fal SAM 3D case is green.
- **Steps:**
  1. In Chrome on the M1, view the room built from the 10 spike objects and compare it with the photos.
  2. Open each Puzzle by a raycast hit and read the Event log.
  3. Read the fal entries in the Ledger export.
- **Pass:**
  - At least 7 of 10 Interactables are recognizable in position (Luis's judgment).
  - 30 fps or better on the M1.
  - Every Puzzle opened by a raycast hit posts the same events as Tier 1.
  - fal calls are priced in the Ledger and total fal cash is within $6.
- **Fail if:**
  - Any gate criterion misses. The decision reads "ships Tier 1" and names the missed criterion.
  - SM-C3: Tier 2 work displaces the Mon Nov 2 real room-1 run, or any Tier 1 UAT regresses.
- **Evidence:** the gate record with the three measured values in the sprint status; a screen recording with the fps readout.

### UAT-15b UJ-7 walk (only after the gate passed and the post-gate FR-34 stories shipped; not before the Nov 4 submission)

- **Maps to:** UJ-7; FR-34; NFR-10.
- **Preconditions:**
  - UAT-15 passed and the post-gate FR-34 stories, including the walk view, shipped.
  - Otherwise, record "not in this submission".
- **Steps:**
  1. Walk to the bookshelf and look at it.
  2. Play to the exit.
  3. Load the Room with WebGL disabled.
- **Pass:**
  - The look triggers the `find` lock.
  - The walk reaches the Completion screen.
  - With WebGL disabled, the Tier 1 Scenes load instead.
- **Evidence:** a screen recording.

## 3. Traceability

| Id | Covered by |
|---|---|
| SM-1 Capture proof | UAT-12 (UAT-01 rehearsal) |
| SM-2 Non-builder completion | UAT-03 |
| SM-3 Zero wins by persuasion | UAT-04, UAT-13 |
| SM-4 Zero solution tokens | UAT-02 (video Rooms and every hosted Demo room) |
| SM-5 Fresh objects in room 2 | UAT-08 |
| SM-6 Spend discipline | UAT-09 |
| SM-7 Main demo carries every proof beat | UAT-13 |
| SM-8 Verified video rooms | UAT-02, UAT-12 |
| SM-9 Hint latency | UAT-06 |
| SM-C1 (do not weaken the Validator or Dry run for speed) | UAT-01, UAT-02, UAT-12 |
| SM-C2 (no Rungs sooner than FR-15) | UAT-03, UAT-05 |
| SM-C3 (no Tier 1 traded for Tier 2) | UAT-13, UAT-15 |
| SM-C4 (no vaguer Rungs) | UAT-02 |
| UJ-1 | UAT-01, UAT-02, UAT-03, UAT-10, UAT-11 |
| UJ-2 | UAT-03, UAT-04, UAT-05, UAT-06, UAT-13 |
| UJ-3 | UAT-07, UAT-13 |
| UJ-4 | UAT-08, UAT-13 |
| UJ-5 | UAT-14 (part A Tier 1; part B Tier 1.5) |
| UJ-6 | UAT-02, UAT-05, UAT-07, UAT-09, UAT-10, UAT-12, UAT-13 |
| UJ-7 | UAT-15b, only if the gate passed; the gate itself: UAT-15 |
