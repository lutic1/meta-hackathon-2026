---
title: "Review: reconcile the spine with Schema v1"
reviewer: Luis Ticas
date: 2026-10-21
subject: ARCHITECTURE-SPINE.md (AD-2, AD-3, AD-4, AD-11, AD-12, ERD) against briefs/brief-Keyframe-2026-10-20/schema-v1.md
verdict: not yet reconciled
---

# Review: reconcile the spine with Schema v1

**Verdict: not yet reconciled.** The spine and Schema v1 agree on the entity set, the eight rules, the dry run, and the regeneration cap. They disagree, or leave open, five things that two parallel agents would build differently: what the rule 5 prompt test can actually check, how a `TricksterEdit` becomes a Room version (and that `loosen` is not a Room change at all), what `dry_run(room_view)` can compute without solutions, what the browser receives, and what the validator's `reasons[]` may contain. All are fixable with text edits to the spine and two lines to carry into the Thu Oct 22 schema review. No structural change.

Inputs read: the spine (all sections), `schema-v1.md`, `SPEC.md` and companions (`stack.md`, `budgets.md`, `player-profile.md`, `delivery-plan.md`, `glossary.md`), the addendum §Schema v1 and §Player profile v1, and the scaffold (`src/providers/base.py`, `src/config.py`).

## Findings

Severity: critical / high / medium / low. Each finding names where it sits and the concrete change.

### H-1 — AD-3's prompt-fixture test cannot pass as written

- **Location:** AD-3 Rule, last clause ("the test suite runs validator rule 5 over every rendered prompt fixture").
- **Problem:** Rule 5's solution tokens for `find` and `order` are interactable *labels*. The dry-run prompt must carry every label (schema §Dry run: "receives the photos, the labels, every clue, and all three rungs"), and the Trickster prompt carries ids and labels to propose a `decoy`. Running rule 5 over those prompts fails on every room that has a `find` or `order` puzzle, so the test either never passes or gets weakened to pass. Rule 5 is a rung check, not a prompt check.
- **Fix (AD-3):** replace the clause with: "a fixture test renders every council prompt from a Room whose solutions are sentinel values and asserts none appears: the `code` string, the `order` id list in sequence, the `use_on` {item, target} pair as a pair, and the `find` target *id*; a second test asserts the `HintPhraser` input is exactly `(rung_text, derived)`, so rule 5 on the rungs is the whole guarantee for the Guide." Keep rule 5 itself where the schema puts it: on `rungs` and `clue` inside `validate`.

### H-2 — `TricksterEdit` versioning is undefined, and `loosen` is not a Room change

- **Location:** AD-12 ("a `TricksterEdit` produces a new Room version written only if `validate` passes"), AD-4 (`trickster_card` event), ERD (`ROOM ||--o{ TRICKSTER_EDIT : versions`).
- **Problem:** Four gaps stack here. (a) Schema v1 has no version field on Room and no room reference on `TricksterEdit`, so "references the unchanged version" has nothing to reference. (b) `loosen` ("unlocks that rung immediately") changes `current_rung`, which AD-4 reserves to `SessionStateMachine.apply`; it produces no new Room, so "every accepted edit is a new Room version" is false for one of four types. (c) An accepted `decoy` adds "a false evidence card", but no Room or Puzzle field can hold it; the new version has nowhere to put it. (d) Edits happen inside a session; a version written to `ArtifactStore` under the room's id would be shared by every session of that room, which breaks the hosted cached demo rooms (CAP-10, several judges on one room) and AD-8's "sessions and their artifacts are deleted as a unit". The ERD hangs edits off ROOM, not SESSION.
- **Fix (AD-12, AD-4, ERD, Structural Seed):**
  - AD-12: "The build's Room (version 1) is immutable. `apply_edit(room, edit) -> Room` in `src/domain/edits.py` is pure; a proposal is accepted only if `validate(apply_edit(room, edit))` passes rules 1 to 8 (no dry run). The accepted edit is appended as a `trickster_card` event with `accepted: true`; the session's effective Room is `apply_edit` folded over its accepted edits, replayed like the rest of the state. A rejected edit appends the same event with `accepted: false` and the effective Room is unchanged. `loosen` is applied by `SessionStateMachine.apply` to `current_rung`, not to the Room." Edits therefore live in the session log (transient, per session) and never in `ArtifactStore`.
  - AD-4: list `trickster_card` as server-appended (see M-5) and name `apply_edit` as the one function that may derive the effective Room.
  - ERD: replace `ROOM ||--o{ TRICKSTER_EDIT : versions` with `SESSION ||--o{ TRICKSTER_EDIT : proposes` and `TRICKSTER_EDIT }o--|| ROOM : edits`.
  - Carry to the Oct 22 schema review: add `Room.version` (int, 1 at build) and `TricksterEdit.room_version` (the version the card references); add `Room.decoys[]` of {puzzle, interactable, attribute} (or make `Puzzle.evidence` a list with `is_decoy`) so an accepted `decoy` has a field.

### H-3 — `dry_run(room_view)` cannot be pure and cannot compare answers

- **Location:** AD-12 Rule, first clause ("`validate(room)` and `dry_run(room_view)` are pure functions"); Structural Seed (`council/dryrun.py`).
- **Problem:** The dry run is a `muse-spark-1.3` call (schema §Dry run), so it is not pure, and judging its answers requires `solution`, which `RoomView` has dropped. As written, the one function both lacks I/O and lacks the data it must compare against.
- **Fix (AD-12, Seed):** split it in the text: "`council/dryrun.py: build_dry_run_prompt(room_view, response_schema)` is pure and sees no solution; the pipeline `dryrun` stage makes the call; `domain/validator.py: check_dry_run(room, answers) -> DryRunResult` is pure, takes the full Room, and is the only place answers meet solutions." Change the AD-12 clause to "`validate(room)` and `check_dry_run(room, answers)` are pure functions." The dry run's `response_schema` is a pydantic `DryRunAnswers` model keyed by puzzle id whose values are the per-type solution shapes (reuse the `solution` union from `schema.py`, AD-2).

### H-4 — The browser receives solutions

- **Location:** AD-2 ("the same JSON travels the HTTP API, the job artifacts, and the client"), AD-3 (only models are named), AD-4.
- **Problem:** Nothing in the spine strips `solution` from what the play routes return. A judge with devtools reads every code; the pitch is a game master that cannot be talked into winning. AD-3 guards Spark and Ollama only; AD-4 guards lock *state*, not lock *answers*. `RoomView` is not the fix because the prompt view also drops `evidence`, which the player must see as cards.
- **Fix (AD-3, AD-2):** add to AD-3: "`redact.py` exposes two views from one Room: `to_prompt_view(room)` and `to_play_view(room)`; the play routes return only `PlayView`, which drops `solution` and `provenance`; the full Room leaves the server only through the build-artifact download. The generated `web/types` contain `PlayView`, never `Room`, and the API fixture test asserts no `solution` key in any play response." AD-2 then reads "the same JSON *shapes* travel ..." with `PlayView` as the client shape.

### H-5 — `validator_result.reasons[]` can carry the solution it is protecting

- **Location:** AD-12 ("the rejected card references ..."), AD-3, schema §Validator rule 5 and §Payload ("a failing result is shown as the rejected card"), §Dry run ("regenerates the room with the failures listed in the Riddler prompt").
- **Problem:** A natural rule 5 reason is "near_answer of pz_3 contains '345'". That string is shown to the player on the rejected card and fed to the Riddler on regeneration, so the same text reaches a player and a model prompt. Rule 5's whole point is undone by its own error message.
- **Fix (AD-3 or AD-12):** add: "validator and dry-run reasons are structured, `{rule, puzzle_id, field}` plus a fixed message per rule, and never quote the offending token or an answer; the regeneration prompt carries the reason list only, never the previous draft; the rejected card renders the fixed message." Add the reasons fixture to the H-1 test.

### M-1 — `redact` has no field list; "validator-only fields" is undefined

- **Location:** AD-3 Rule ("drops `solution`, lock targets, and validator-only fields").
- **Problem:** No Schema v1 field is validator-only; `requires` is used by rules 1, 2, 8 but the Trickster needs it (merge, shortcut, "open locks"). "Lock targets" is also undefined: `evidence.interactable` is a target for `find`, and `evidence.visible_attribute` for a `code` puzzle is often the code read off the object, which no rule 5 token list covers. The Riddler needs `attributes[]` (to satisfy rule 4) while the schema's dry run gets labels only.
- **Fix (AD-3, as a convention row):** "`to_prompt_view` keeps `id`, `label`, `attributes`, `instances`, `photo`, and per puzzle `id`, `lock_type`, `requires`, `is_exit`, `clue`, `lore`, `rungs`; it drops `solution`, `evidence`, `provenance`, `photos[].hash` and paths, `box`, `mask`, `tier2`, and `validator_result`. Each builder renders a subset: the dry run renders labels, clues, and rungs only (schema §Dry run); the Trickster adds the game-state summary; the Riddler renders interactables only." Photos reach a prompt as bytes through the adapter, never as paths.

### M-2 — Lock inputs have no event mapping

- **Location:** AD-4 event list; schema §Lock input and inventory.
- **Problem:** The schema defines four input gestures; AD-4 offers `click` and `lock_input` with no payloads. `order` is "the sequence of hotspot clicks since the last wrong attempt", but nothing says what a wrong attempt is for `order` (the server infers it; the client only sends clicks). `use_on` is a drag, which is neither a click nor a typed code. Whether a `click` on a non-target counts as a wrong attempt (it feeds the 3-wrong-attempts nudge) is unstated. The state-machine owner and the `web/` owner will each decide.
- **Fix (AD-4, Conventions):** "`click` {interactable_id}; `lock_input` {puzzle_id, code} for `code`, {item, target} for `use_on`. `find` is a `click` on the target; `order` is judged on each `click` against the trailing sequence and a wrong attempt is recorded when the sequence reaches the solution's length and differs, which resets it; a `click` that is not a `find` target and completes no `order` is not an attempt. The server resolves `use_on` and `find` to a puzzle; the client never names the puzzle for those two." Add `wrong_attempts[puzzle_id]`, `attempts`, `rungs_used`, and the `order` buffer to the state the machine owns (AD-4 lists four fields; the profile per-puzzle record in `player-profile.md` needs these).

### M-3 — `current_rung` is a scalar; rungs are per puzzle

- **Location:** AD-4 state fields; schema `Puzzle.rungs`.
- **Problem:** Several puzzles can be open at once (DAG), each with three rungs. "Which puzzle is the player stuck on" is a rule nobody has written, and the nudge thresholds in `player-profile.md` are per lock.
- **Fix (AD-4):** "`current_rung` is `dict[puzzle_id, 0..3]`; the active puzzle for idle and hint events is the puzzle of the most recent `lock_input` or attempted `click`; a `hint_request` names its puzzle." 

### M-4 — Author-stage artifact contradicts the write gate

- **Location:** AD-7 ("persist job state plus stage artifacts ... after each stage"), AD-12 ("a Room is written to `ArtifactStore` only after `validate` passes").
- **Problem:** The `author` stage's artifact is a Room that has not been validated. Both rules cannot hold for the same key.
- **Fix (AD-12):** "The `author` stage persists a `RoomDraft` (the Riddler's raw output, kept for provenance and the regeneration count); the job's `room` artifact, the only key the play routes read, is written once `validate` (and `dry_run`, unless cut 4) passes." One line in the Seed: `schema.py` holds `RoomDraft`, `Room`, `PlayView`, `PromptView`.

### M-5 — Which events the client may post

- **Location:** AD-4 ("the client renders state and posts events"), AD-10 (a `Clock` port supplies all time).
- **Problem:** `trickster_card` is server-originated (a proposal plus validator result), and `idle_tick` posted by the client would let the browser clock drive the nudge, which AD-10 forbids. The list reads as if the client posts all five.
- **Fix (AD-4):** "client-posted: `click`, `lock_input`, `hint_request`; server-appended: `idle_tick` (from the session `Clock`), `trickster_card`. Every event is stamped by the server clock on append; client timestamps are ignored."

### M-6 — Hotspot geometry: two coordinate spaces and one polygon for many instances

- **Location:** AD-11 ("polygon hotspots", "hotspot id equals interactable id"), Conventions ("masks as polygons in image pixel space"); schema `Interactable.box` (0 to 1000 grid), `mask` (polygon, null on fallback), `instances`.
- **Problem:** `box` is normalized, `mask` is in pixels, and the convention does not say pixels of which image (the client renders the 1280 px JPEG). On the box fallback the client must build a hotspot from a differently scaled shape. A grouped plural ("books", `instances` 3) has three SAM masks and one `mask` field, so either two instances lose their hotspot or `mask` is secretly a multipolygon.
- **Fix (Conventions, and carry to Oct 22):** "Hotspot geometry is in pixel coordinates of the downscaled 1280 px image; `mask` is a list of polygons (one per instance) and the hotspot is their union; when `mask` is null the `segment` stage writes the `box` rectangle, scaled to the same space, as the single polygon, so the client never reads `box`." Schema change: `mask: polygon[] | null`.

### M-7 — Trickster-specific constraints are outside rules 1 to 8

- **Location:** AD-12; schema §Payload by type ("never to the exit puzzle", `loosen` {puzzle, rung}, `shortcut` removes one `requires` edge).
- **Problem:** "decoy never on the exit puzzle", "the rung exists", "the edge exists", and "at most one change per window, only between puzzles" are not validator rules, so the spine does not say which module refuses them or whether a refused proposal is a rejected card or a silent drop. A `loosen` edit changes no Room, so rules 1 to 8 on "the edited Room" are vacuous for it.
- **Fix (AD-12):** "`validate_edit(room, state, edit)` in `domain/edits.py` checks the per-type payload constraints and the window and between-puzzles bounds before `apply_edit`; a constraint failure is a rejected card with its own reason code (so the demo's live reject can come from either check)."

### M-8 — `Room.profile_name` puts a profile key on a server artifact

- **Location:** schema Room fields; AD-8, ERD note ("`PROFILE` ... live only in the client").
- **Problem:** The Room is written by the server (AD-7, AD-12) and, hosted, lives on the Volume. A `profile_name` on it is the join between a room and a player profile that AD-8 says the server never holds. The value is only `dev|playtest|demo`, so the exposure is small, but the rule is absolute and the ERD shows no ROOM to PROFILE relation.
- **Fix (carry to Oct 22, note in AD-8):** drop `profile_name` from Room; the client keys `ROOM_RESULT` by `room_id` inside the profile it already owns.

### M-9 — Exit is stored twice

- **Location:** schema Room `exit_puzzle_id` and Puzzle `is_exit`; AD-2 ("one data shape"); rule 2 ("the exit").
- **Problem:** No rule checks that the two agree; rule 2 does not say which it reads. One Riddler output with `is_exit` on pz_4 and `exit_puzzle_id` pz_5 passes the validator.
- **Fix (Conventions, carry to Oct 22):** keep `is_exit` only and make "exactly one `is_exit`" rule 7's first check, or keep `exit_puzzle_id` and drop `is_exit`; `validate` reads the kept one.

### L-1 — Polymorphic `solution` and `payload` need a stated union encoding

- **Location:** AD-2 (`GET /schema` to TypeScript); schema Puzzle `solution`, TricksterEdit `payload`.
- **Fix (Conventions):** "variants by `lock_type` and `type` are tagged unions: separate pydantic models with a `Literal` discriminator, emitted as `oneOf`, so the generated TypeScript is a discriminated union." Also rename in prose: `solution` is the puzzle's lock payload (rule 7), `payload` is the Trickster edit's; the spine's "lock targets" wording should go.

### L-2 — `provenance` differs between schema and AD-16

- **Location:** AD-16 ("spend per stage"); schema Room `provenance` (model ids, prompt hashes, stage timings, regeneration count).
- **Fix:** carry "spend per stage (from the ledger) and applied edit ids" into the Oct 22 review; AD-16 is right.

### L-3 — Rule 5's word-length filter exempts codes

- **Location:** schema rule 5 ("whole words longer than three characters") versus "`code`: the code string and each of its digits".
- **Fix (Conventions, carry to Oct 22):** "code strings and digits match as exact whole tokens regardless of length; the three-character floor applies to label words only." The rung "turn it 3 times" fails for code 345; that is the schema's choice, and the fixture test should cover it.

### L-4 — Segment-stage caps have no typed error

- **Location:** AD-13 error set; schema §SAM mask selection (cap 12, minimum 5).
- **Fix (AD-13):** "fewer than 5 survivors raises `ValidationError` with `stage: segment` and code `too_few_interactables`; the UI asks for more photos on that code and for re-capture on `regen_exhausted`." Name the IoU selection as `domain/masks.py` (pure) called by the `segment` stage so two agents do not both write it.

### L-5 — ERD omissions

- **Location:** ERD.
- **Fix:** add `JOB ||--o| ROOM : produces` and `ROOM ||--|{ PHOTO : from`; drop `accepted` or define it as `validator_result.ok and applied` since the two are otherwise redundant; define `TricksterEdit.window` and the state's `trickster_window` as the integer index `floor(session_ms / window_ms)` on the session clock (AD-10 scales `window_ms`).

## What already reconciles

- Entities and names match: Room, Interactable, Puzzle, TricksterEdit, the four lock types, the four edit types, the three rungs, and `provenance` as a Room field (ERD `ROOM ||--|| PROVENANCE`).
- Keys are snake_case in both (`exit_puzzle_id`, `visible_attribute`, `validator_result`, `near_answer`, `puzzle_a`).
- Ownership is right: rules 1 to 8 are one `validate` in `src/domain/validator.py`, called from the pipeline `validate` stage and again at Trickster time; no second implementation is implied anywhere.
- "No dry run on a Trickster edit" (schema) matches AD-12's wording once H-2's text replaces it.
- Inventory: "solving a `find` moves its interactable into the inventory" is exactly the `inventory` field AD-4 reserves to the state machine; rule 8 is the static counterpart.
- Minimum 5 before any Riddler call (schema assumption, CAP-1) sits naturally in the `segment` stage ahead of `author` in the AD-7 order.
- Regeneration at most 2 then re-capture: schema, SPEC, AD-13, and the pipeline state diagram agree.

## Suggested order

H-1, H-3, H-4, H-5 are spine text edits with no schema change. H-2 needs the Oct 22 review to add `Room.version`, `TricksterEdit.room_version`, and a home for decoys, and the spine edit can land now with those names. M-6, M-8, M-9, L-2, L-3 are the schema-review carry list; the rest are spine conventions.
