---
title: "Review: Keyframe PRD readiness for epic and story extraction"
reviewed: docs/planning-artifacts/prds/prd-Keyframe-2026-10-21/prd.md
compared-with: docs/planning-artifacts/epics.md (FR1 to FR36, NFR1 to NFR13)
sources-checked: schema-v1.md, SPEC.md, player-profile.md, budgets.md, stack.md, delivery-plan.md, ARCHITECTURE-SPINE.md
date: 2026-10-21
---

# Review: PRD readiness for epics and stories

## Verdict

**Conditionally ready.** The ids are clean (FR-1 to FR-37, NFR-1 to NFR-13, UJ-1 to UJ-7, SM-1 to SM-6, SM-C1 to SM-C3, A-1 to A-18; no gaps, no duplicates). Every architecture spine AD-n, §-reference, Validator rule number and SM id resolves. Every FR has at least one consequence that a Given/When/Then can assert. FR-1 to FR-36 keep the meaning of FR1 to FR36 in `epics.md`, with one real extension (FR-8 adds a Clue check) and two small narrowings (FR-29, FR-31).

Re-extraction would still produce stories that guess in five places. Fix these first:

1. No FR covers a Build that ends `failed` (provider error after the retry, Spend cap reached mid-Build, dead runner), and FR-28's "surfaced to the player or Luis" says nothing a test can check.
2. FR-15 never defines "without progress" or "a further stall", and never says Rungs are tracked per Puzzle. Rung selection is the core of Epic 3.
3. Nothing defines how the Derived block is computed from Room results (`persistence` above all), so FR-21's adaptive threshold has no input a test can set up from play.
4. Several Tier 1 FRs (FR-17, FR-26, FR-29, FR-36) carry Hosted-mode (Tier 1.5) consequences with no tag, so they would land in Tier 1 stories. `epics.md` already splits FR29 and FR36 by hand.
5. FR-8 says a Clue holds no solution token. Schema v1 rule 5 checks only Rungs (and near-answer against the Clue), so a validator story would test a rule the frozen schema does not define.

The full list follows: 5 high, 17 medium, 13 low.

## Method

I read each FR the way `bmad-create-epics-and-stories` does. I pulled the FR statement and its "Consequences (testable)" bullets, then checked each bullet:

- Can a Given/When/Then assert it offline on the Mock provider (NFR-8)?
- Does it name the error case?
- Does it carry every number the spec and Schema v1 hold?
- Does it keep the meaning of the same-numbered FR in `epics.md`?

Every cross-reference was resolved against its target document.

## Id and cross-reference check

| Check | Result |
|---|---|
| FR ids | FR-1 to FR-37 present once each. FR-37 sits under §4.7 out of numeric order, which §0 explains. OK |
| NFR ids | NFR-1 to NFR-13 present once each. OK |
| UJ, SM, A ids | UJ-1 to UJ-7, SM-1 to SM-6, SM-C1 to SM-C3, A-1 to A-18 all present. Every A-n in §14 appears inline. OK |
| Id format | The PRD uses `FR-n`, `epics.md` uses `FRn`. §0 states the mapping. Re-extraction should pick one format and record the mapping in the epics frontmatter (low) |
| Architecture spine AD-n | AD-3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 18 cited; all exist. "Clue cards are the spine's deferred post-scene stage" resolves to spine §Deferred. OK |
| Validator rules 4, 5, 9 | Resolve to `schema-v1.md` §Validator rules and §Open pick. The PRD never gives that file's path. §0 names the brief folder and §13 Q1 says only `schema-v1.md` (low) |
| §-references | §3, §8, §11.1, §11.2, §13 Q1, §14, SM-C3 all resolve. OK |
| UJ → FR and FR → UJ | Asymmetric backlinks: FR-16, FR-22, FR-28, FR-29, FR-30 cite UJ-6, but UJ-6's Capability → FR line lists only FR-24 to FR-27. FR-37 cites UJ-1, but UJ-1 never mentions a Clue card. FR-36 cites UJ-1, UJ-4, UJ-5, none of which lists FR-36 (low) |
| Cut table §11.2 | Unlisted effects: cut 3 also changes the Greeting (FR-21, which phrases through the same `greet` port); cut 4 also changes FR-10 (Regeneration is then triggered by the Validator alone); cut 6 also narrows FR-9 (low) |
| Spine inconsistency the PRD inherits | Spine AD-4 says a Trickster provider error is a **skipped** card. AD-13 says Trickster errors become a **rejected** card. PRD FR-19 and `epics.md` FR19 both say skipped, which is correct; the spine's AD-13 wording needs a correct-course note (low) |

## FR-by-FR readiness

Rating key: **R** = ready. **R\*** = ready once the listed gap is fixed. **G** = a story would have to guess.

| FR | Rating | Assertable consequences | Gaps (ids refer to the list below) |
|---|---|---|---|
| FR-1 | R\* | count 6 to 10; non-JPEG rejected with "6 to 10 JPEG photos"; 1280 px, EXIF applied; original unmodified | M1 (mixed set, count-rejection message) |
| FR-2 | R\* | one call, all photos, effort low; attributes verbatim | M2 (meaning of "within 15 s"), H1 |
| FR-3 | R\* | ≤12 concurrent; best-overlap mask; 1% drop; ≤12; box fallback | M3 (IoU 0.2, cap ordering, segment errors), L1 ("identically") |
| FR-4 | R\* | `needs_more_photos` with zero Riddler, Dry run or Trickster calls | M4 (what "more photos" means for the next upload) |
| FR-5 | G | timer start and stop; 260 s Build delivered by polling | M5 (stage list, timer on non-`done` ends), H1 |
| FR-6 | R\* | Retention summary names services; Privacy line verbatim | L2 (single source of the text) |
| FR-7 | R\* | one exit; Lock types; Clue, Lore ≤60, 3 Rungs; no outside reference | M2, M6 (unparseable Riddler output) |
| FR-8 | G | fails never stored; reasons structured, never quoting | H5 (Clue check drift), L3 (rules only by reference) |
| FR-9 | R\* | sentinel test; mismatch fails; cut 4 skip | M6 (Dry run error or unparseable answers) |
| FR-10 | R | reasons only; `needs_recapture` after second failure; count in provenance | L4 ("about 75 s" is not a consequence) |
| FR-11 | G | Thumbnail strip reaches every photo; Inventory persists | M7 ("responds and aligns"; Wizard notes have no consequence), M17 (Session resume) |
| FR-12 | R\* | four input forms; `find` → Inventory; Wrong-attempt counting | M8 (input to an unavailable Puzzle, item not held, code matching) |
| FR-13 | R | Completion screen time and Rungs; Room result recorded | none |
| FR-14 | R\* | attack returns current Rung or no-hint line; no text to server; fixture test | L5 (no-hint line text; "or speak" belongs to FR-35) |
| FR-15 | G | formula and clamp; 3 Wrong attempts; 90 s spacing; replay equals live | H2 |
| FR-16 | R\* | each change lists idle seconds or Wrong attempts; cut 5 | M9 (`loosen`-triggered changes) |
| FR-17 | R\* | 5 s timeout and verbatim fallback logged; input = Rung + Derived; hosted refuses a Guide model; cut 3 | H4 (hosted tag), M10 (Ollama down; phrased output not re-checked), L4 ("about 40 tokens") |
| FR-18 | G | one per 3-min window after a lock opens; 7th call refused; no profile or solution; no decoy on exit | M11 (when a window opens; the first window) |
| FR-19 | R\* | accept on rules 1 to 8 (+9); rejected Card and unchanged room; skipped Card on error or cap | M12 (accepted decoy Card must not reveal the decoy; 7th-call outcome) |
| FR-20 | R\* | IndexedDB under `PROFILE`; cut 2 JSON; Session start carries only Derived | M13 (Derived bounds and refusal) |
| FR-21 | G | Greeting from Derived only, names no object or solution; threshold formula | H3, M14 (80% and `PROFILE=demo` are not system behavior; who gets a Greeting; verbatim Greeting) |
| FR-22 | R | demo flag at timescale > 1; flagged results ignored | none |
| FR-23 | R\* | zero image calls in play; placeholder fallback | L6 (date and video are not story consequences) |
| FR-37 | R\* | one image per Puzzle after validation, cached; Clue-only prompt (sentinel); failure never fails Build or T1 | M15 (which Builds get Clue cards; "about $0.16") |
| FR-24 | R | 3 Rungs ≤ 40 s on Wrong attempts at 6x; timer and timestamps unchanged | L7 (no consequence for the Trickster window) |
| FR-25 | R\* | two recorded proposals: one accepted, one rejected; cut 1 | M16 (recorded proposals bound to a room; source exhausted) |
| FR-26 | R\* | status endpoint fields; Disclosure conditions | H4 (hosted tag), L6 (video's last 10 s) |
| FR-27 | R | cache-key fields; hit adds nothing to Ledger; `CACHE=off` still priced; Regeneration never served its own answer | none |
| FR-28 | G | cap values; total survives restart | H1 ("surfaced"), M18 (how the cap changes), L8 (Cache clear keeps Ledger) |
| FR-29 | R\* | startup and post-Build export; reset refused without that day's export | H4 (hosted snapshot tag), D2 (narrowed to Thu Nov 5), L6 ("committed" is builder process) |
| FR-30 | R | provenance fields; spend log from Ledger | none |
| FR-31 | R\* | landing lists Demo rooms, each plays to Completion; verbatim Rungs and Disclosure | D3 ("same behavior"), M19 (live Trickster and Greeting in Hosted mode) |
| FR-32 | R\* | no code → refused; 21st refused; >150 s Build delivered | L9 (wrong code; what counts toward the 20) |
| FR-33 | R\* | Judge data deleted together; Demo rooms persist; logs deleted 24 h after last event | L10 (script vs schedule) |
| FR-34 | R (Tier 2) | up to 20 objects; same scene graph; gate numbers | L11 ("recognizable" is a human gate; fal cap enforcement) |
| FR-35 | R\* | transcription and fallback; spoken attack fails | M20 (transcript passes through the server, against FR-14) |
| FR-36 | R\* | ignore test; no profile on hosted server; standard tier only | H4 (hosted tag), M21 (exact ignore list) |

## Drift against `epics.md` (same-numbered FR)

| Id | `epics.md` | PRD | Kind | Action |
|---|---|---|---|---|
| D1 · FR-8 | eight rules, structured reasons | adds "No nudge, direction, **or Clue** contains a solution token" | Meaning extended past Schema v1 rule 5 | See H5 |
| D2 · FR-29 | "`reset` refuses to run without that day's export" (any day; path `spend/exports/ledger-<date>.json`) | "The **Thu Nov 5** counter reset is refused unless that day's export exists"; path dropped | Narrowed | Replace with: "A counter reset on any day is refused unless that day's export (`spend/exports/ledger-<date>.json`) exists." |
| D3 · FR-31 | "play **cached** demo rooms through **the same API** as local mode" | "with **the same behavior** as Local mode" | Loosened, and contradicted by its own second bullet (verbatim Rungs) | Replace with: "A judge can open the hosted URL and play cached Demo rooms through the same API as Local mode; Rungs appear verbatim." |
| Additive, no action | FR-6 (+Privacy line), FR-12 (+`order` reset, click never counts), FR-17 (+refuse to start, cut 3), FR-21 (+80%, `PROFILE=demo`), FR-23 (+placeholder), FR-24 (+40 s), FR-26 (+last 10 s, README), FR-28 (+cap values), FR-36 (+standard tier) | | Additive, from SPEC CAP success lines | FR-21's additions are success measures; see M14 |
| NFR drift | NFR4 "the player profile stays on the player's machine"; NFR13 "`_bmad/` and `.claude/`" | NFR-4 drops the profile clause; NFR-13 says "planning-tool folders" | Clauses lost | Restore both phrases verbatim (L12) |

## Gaps and fixes

### High

**H1. A Build that ends `failed`, and a refused call, have no testable outcome.**
*Where:* FR-2, FR-3, FR-5, FR-7, FR-28; the glossary lists `failed` as a Build end, but no FR uses it.
*Problem:* a provider error after the one retry (NFR-7), a reached Spend cap during a Build, and a dead runner (spine AD-7 watchdog) all end the Build `failed`. No consequence says what the player sees. "A refused call is surfaced to the player or Luis" names no surface and no content.
*Fix:* add to FR-5:
> "A Build that ends `failed` (a provider error after its one retry, a refused call under the Spend cap, or a runner that stopped) stops the timer and shows the failed stage and a plain retry message on the Capture screen; no partial Room is playable."

Replace FR-28's second bullet with:
> "A refused call ends a Build `failed` with code `spend_cap_exceeded` at its stage (FR-5), shows a skipped Card in play (FR-19), and makes a script exit non-zero, printing the cap and the running total."

**H2. FR-15 rung selection leaves three terms undefined.**
*Where:* FR-15.
*Problem:*
- "Without progress" is undefined. The spine computes idle seconds from the last non-tick event, so any click resets it, and an untested reading would differ.
- "A further stall" has no length.
- Rungs are tracked per Puzzle (spine `current_rung: dict[puzzle_id, 0..3]`), but the PRD never says so, nor which Puzzle is active.
*Fix:* add these bullets to FR-15:
> "Idle seconds count from the player's last event (click, lock input, or Hint request); idle ticks never reset them."
> "Rungs, Wrong attempts and idle seconds are tracked per Puzzle; the active Puzzle is the one of the most recent lock input or attempted click."
> "A further stall is idle time equal to the nudge threshold."

The last bullet matches FR-24's "45 s on idle alone" at 6x (15 s + 15 s + 15 s). Confirm it before freezing.

**H3. The Derived block has no computation rule.**
*Where:* FR-20, FR-21, FR-22; glossary "Derived block".
*Problem:* the threshold formula uses `persistence`, but nothing says how `persistence`, `time_to_first_hint` or `mean_rung_per_lock_type` come from Room results. `player-profile.md` describes persistence only in words ("positive when the player keeps trying past the nudge threshold, negative when they ask early"). A "recompute the Derived block" story cannot assert a value, and FR-21's adaptation cannot be set up from play.
*Fix:* add an FR-21 consequence:
> "After each non-demo Room result the Derived block is recomputed:
> - `sessions` = count of non-demo Room results;
> - `time_to_first_hint` = median of per-Room first-hint seconds (null if none);
> - `mean_rung_per_lock_type` = mean Rungs used per Puzzle, by Lock type, 0 to 3;
> - `persistence` = [formula], clamped to −1 to 1."

Pick the persistence formula now and record it as a new assumption (A-19) if it is not yet decided.

**H4. Tier 1 FRs carry untagged Tier 1.5 consequences.**
*Where:* FR-17 ("Hosted mode runs no Guide model and refuses to start…"), FR-26 ("…or Hosted mode is active"), FR-29 ("Hosted mode snapshots the Ledger daily at 06:00 ET"), FR-36 ("The hosted server stores no Derived block…").
*Problem:* the glossary and §10.1 put FR-17, FR-26, FR-29 and FR-36 in Tier 1. Extraction will place their hosted bullets in Tier 1 stories, ahead of the Backup video. `epics.md` already had to split FR29 and FR36 by hand ("hosted snapshot in Epic 7").
*Fix:* start each of those bullets with "(Hosted mode, Tier 1.5)". Add to §10.1: "Hosted-mode consequences of Tier 1 FRs are Tier 1.5 and ship with FR-31 to FR-33."

**H5. FR-8 adds a Clue check that Schema v1 does not define.**
*Where:* FR-8 bullet 2; glossary "Clue … holds no solution token"; `epics.md` FR8; `schema-v1.md` rule 5.
*Problem:* rule 5 checks Rungs; the near-answer "is also checked against `clue`". It does not forbid solution tokens in a Clue. For a `find` or `order` Puzzle the solution tokens are Interactable labels, so a Clue that names an object (UJ-1's climax names the mug) can collide with a strict reading. A validator story would test a rule the frozen schema does not have.
*Fix:* choose one.
- Keep Schema v1 as frozen and reword the bullet: "No nudge or direction contains a solution token; near-answers stay within the per-Lock-type allowance of rule 5 and are also checked against the Clue." Then drop "holds no solution token" from the glossary's Clue entry.
- Or keep the Clue check and send it through `bmad-correct-course` as a Schema v1 rule-5 amendment before the Mon Oct 26 freeze, stating which tokens a Clue may never contain per Lock type.

### Medium

**M1. FR-1 does not say whether one bad file rejects the whole set, or what a wrong count shows.**
*Fix:* "A set with any non-JPEG file, or with fewer than 6 or more than 10 files, is rejected whole in the browser with the message 'Keyframe needs 6 to 10 JPEG photos'; nothing is uploaded." This aligns with §7's error copy.

**M2. Stage budgets are written as consequences ("within 15 s", "within 45 s", "within 30 s", "within 10 s").**
*Where:* FR-2, FR-3, FR-7, FR-9.
*Problem:* it is unclear whether these are timeouts or measured budgets. Offline mock tests (NFR-8) cannot assert them, and nothing says what happens past the budget. `budgets.md` says a Riddler past 45 s retries at low effort or splits.
*Fix:* move the seconds to NFR-1 only. Where behavior past a budget is intended, state it as a consequence, for example in FR-7: "A Riddler call past 45 s is retried once at reasoning effort low."

**M3. FR-3 lacks numbers the spec holds, and the segment error case.**
*Fix:* "For a plural label every mask with overlap (IoU) above 0.2 is grouped as instances; above 12, the Interactables with the highest Architect confidence are kept." Also state what a `sam-3.1` call that still errors after its one retry does: either "treated as no mask (box rectangle)" or "ends the Build `failed`". Decide which.

**M4. FR-4 "asks for more photos" does not define the next upload.**
*Problem:* the set maximum is 10, so it is unclear whether the player adds to the rejected set or starts a new one.
*Fix:* "The Capture screen asks for more photos of the room with a fixed message; the next Upload is a new Build of 6 to 10 JPEG photos." Or define an add-to-set flow. Either way, state it.

**M5. FR-5 does not list the stages or the timer's behavior when a Build does not end `done`.**
*Fix:* "The stage indicator shows, in order: ingest, architect, segment, author, validate, dry run, scene (spine AD-7); during a Regeneration it shows author, validate and dry run again with the attempt number." Add: "On `needs_more_photos`, `needs_recapture` or `failed` the timer stops and shows the end status." A-11 then covers only the plain-word labels.

**M6. FR-7 and FR-9 do not say what malformed model output counts as.**
*Fix:* add to FR-10: "Riddler output that fails the response schema or exact-id parsing, and Dry run output that is missing or unparseable for any Puzzle, count as a failed attempt and feed a Regeneration with a fixed reason."

**M7. FR-11 uses untestable words, and Wizard notes have no consequence.**
*Fix:* replace bullet 1 with:
> "Each Hotspot polygon is in the stored 1280 px photo's pixel space; a click inside it at any rendered size posts a click for that Interactable, and a hover reveals it."

Add: "Wizard notes list the Clue and Lore of every available Puzzle (prerequisites open) and nothing of a Puzzle still locked." This resolves A-10 or keeps it tagged.

**M8. FR-12 has no error cases for unavailable Puzzles and inputs.**
*Fix:* add:
> "Input for a Puzzle whose prerequisites are not open never opens it and is not a Wrong attempt."
> "A `use_on` drag of an item not in the Inventory is refused."
> "`code` input is compared [exact | case-folded, trimmed]."

Pick the comparison rule.

**M9. FR-16 omits Rung changes caused by a `loosen` edit.**
*Fix:* "A Rung unlocked by an accepted `loosen` Card is listed with that Card as its trigger."

**M10. FR-17 does not cover Ollama being down, or phrased output that leaks.**
*Fix:* "If Ollama is unreachable or errors, the verbatim Rung is shown at once and the fallback logged." Decide whether phrased output is re-checked: "Phrased output containing any rule 5 solution token for the active Puzzle is discarded and the verbatim Rung shown." Without this check, a model that never saw the solution can still emit digits that match a `code`.

**M11. FR-18 does not say when a window opens, or when the first one does.**
*Problem:* "At most one" cannot be asserted positively.
*Fix:* "When a non-exit lock opens and no window has closed in the last 3 minutes of session time (the first window counts from Session start), one window opens and exactly one proposal is requested."

**M12. FR-19 can leak which Evidence is the Decoy, and leaves the 7th call's outcome open.**
*Fix:* "An accepted `decoy` Card never identifies which Evidence is false; in the Play view, decoy and real Evidence are indistinguishable (one test)." And: "A window after the sixth Trickster call opens no proposal and shows no Card."

**M13. FR-20 lacks the Derived block bounds and the refusal.**
*Fix:* "A Session start whose Derived block is outside its bounds (`sessions` ≥ 0, `persistence` −1 to 1, `mean_rung_per_lock_type` 0 to 3) is refused with a 422, and no Session is created."

**M14. FR-21 mixes success measures with system behavior and leaves three cases open.**
*Problem:* "At least 80% of room-2 Clues reference Interactables absent from room 1" depends on photographing a different room; no mechanism enforces it, and the Riddler never sees room 1. "A real room-1 record exists on `PROFILE=demo`" is a delivery step. Who gets a Greeting, and what it says without a Guide model, are both unstated.
*Fix:* move the 80% line to SM-5 only (it is already there) and the `PROFILE=demo` line to UJ-6 or §11.1. Add:
> "A Greeting is shown before the first Scene when the Derived block has `sessions` ≥ 1; a fresh Player profile gets none."
> "Under cut 3 or in Hosted mode the Greeting is a fixed template filled with Derived numbers; past 5 s of local phrasing the template is shown."

**M15. FR-37 does not say which Builds get Clue cards, and its cost line cannot be tested.**
*Problem:* "Up to 12 Clue cards" (two rooms) conflicts with Hosted mode, where up to 20 Judge room Builds could each generate 4 to 6.
*Fix:* "Clue cards are generated for [Local-mode Builds and Demo rooms only | every Build, including Judge rooms, under the Spend cap]." Move "about $0.16" to the addendum's sizing section.

**M16. FR-25 does not say what scripted proposals bind to, or what happens when they run out.**
*Fix:* "Recorded proposals are bound to one `room_id`; on another Room, or after the recording is used up, the scripted source yields no proposal and no Card."

**M17. No FR covers resuming a Session after a reload, or choosing a stored Room.**
*Problem:* the glossary says Session state replays from the Event log, and UJ-7 "replays room 1", but no consequence covers either.
*Fix:* add to FR-11: "Reloading the Play screen resumes the Session from its Event log with the same locks, Inventory and Rungs." Add: "Local mode lists stored Rooms so a finished Room can be played again." Or mark the second as out of scope.

**M18. FR-28 does not say how the cap moves from $80 to $25.**
*Problem:* a story might code a date switch.
*Fix:* "The cap is the `SPEND_CAP_USD` setting: 80 until the Thu Nov 5 reset (FR-29), then 25; no date logic in code."

**M19. FR-31 does not say whether the Trickster runs live in Hosted mode, or what the Greeting does there.**
*Problem:* this decides judge-session spend under the $25 cap.
*Fix:* "In Hosted mode the Trickster runs [live under the Spend cap | scripted]; the Greeting uses the template (M14)."

**M20. FR-35 conflicts with FR-14's "player text never travels to the server as text".**
*Problem:* spine AD-5 puts `transcribe(wav)` on the backend provider port, so audio reaches the server and a transcript exists there. The Retention summary does not name voice audio.
*Fix:* "Audio goes to `muse-voice-transcribe-1.0` through the backend; the transcript is reduced to a Hint request in the same request and is never stored or logged. When voice ships, the Retention summary names voice audio." Alternatively, keep transcription in the browser and say so.

**M21. FR-36 lacks the exact ignore list the spec holds.**
*Fix:* "`.gitignore` contains `rooms/`, `photos/`, `captures/`, `uploads/`, `*.heic` and `.cache/`, asserted by an offline test."

### Low

- **L1** FR-3: "behaves identically in play" becomes "is clickable, can be a `find`, `order` or `use_on` target, and hit-tests like a mask polygon".
- **L2** FR-6: add "The Retention summary text is the status endpoint's retention string (FR-26)". The wording itself waits on §13 Q3.
- **L3** FR-8: the eight rules appear only by reference. Add `docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/schema-v1.md` §Validator rules as the explicit source, or a one-line list, so each rule can become its own acceptance criterion. Rule 7's numbers (`code` 3 to 6 characters, `order` 3 to 5 ids) are otherwise invisible from the PRD.
- **L4** FR-10 "(about 75 s)" and FR-17 "about 40 tokens" are sizing, not consequences. Keep them in NFR-1 and NFR-2 and remove them from the bullets.
- **L5** FR-14: give the fixed no-hint line's text, or name it as a constant owned by the UX contract. Move "(or speak)" to FR-35.
- **L6** Builder-process lines inside FR consequences: FR-23 "(Thu Oct 29)" and "in the Main demo"; FR-26 "The Main demo's last 10 s"; FR-29 "committed with each build day's work". Move them to §11 or NFR-11 and NFR-12, or tag them "(builder story)" so extraction makes them builder stories, not agent ACs.
- **L7** FR-24: add "At n = 6 the Trickster window is 30 s."
- **L8** FR-28: add "Clearing the Cache never changes the Ledger or the running total". UJ-6 clears the Cache on camera.
- **L9** FR-32: "A Build with a missing or wrong Access code is refused"; state whether refused, failed and `needs_*` Builds count toward the 20.
- **L10** FR-33: "on schedule" should say whether a purge script run on Tue Nov 10 counts or a scheduled function is required. The spine has a script.
- **L11** FR-34: "recognizable in position" is a human gate judgment; tag it as such. State whether fal.ai spend is enforced by the Ledger or tracked by hand against $6.
- **L12** NFR-4 and NFR-13: restore "the player profile stays on the player's machine" and "`_bmad/` and `.claude/`".
- **L13** Backlinks: add FR-16, FR-22, FR-28, FR-29, FR-30 to UJ-6's Capability → FR line, FR-37 to UJ-1 (or drop the claim), and FR-36 to UJ-1, UJ-4 and UJ-5. In §11.2 add cut 3 → FR-21, cut 4 → FR-10, cut 6 → FR-9. Add the spine AD-13 vs AD-4 skipped-card note to the spine's correct-course queue.

## Out of scope for this review

§7 Aesthetic and Tone still contradicts the builder's recorded decision (Lamplit study, dark only, wry and playful voice, candlelit portraits). `reconcile-decisions.md` H1 already covers this. It does not block FR extraction, but the UX contract and any portrait story (FR-23) should take the reconciled §7.
