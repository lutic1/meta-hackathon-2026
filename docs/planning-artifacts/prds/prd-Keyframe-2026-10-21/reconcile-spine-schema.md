---
title: "Input reconciliation: architecture spine and Schema v1 to PRD, Keyframe"
created: 2026-10-21
author: Luis Ticas
inputs:
  - docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md
  - docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/schema-v1.md
checked:
  - docs/planning-artifacts/prds/prd-Keyframe-2026-10-21/prd.md
  - docs/planning-artifacts/prds/prd-Keyframe-2026-10-21/addendum.md
---

# Input reconciliation: spine and Schema v1 to PRD

## Verdict

The PRD carries the spine's integrity core faithfully: the solution boundary, the server-authoritative event log, the `HintPhraser` input of exactly `(rung_text, derived)`, the 5 s verbatim fallback, the Trickster window and the cap of six calls, the cache and ledger rules, the persisted build job, the two clocks, the scripted source with a live Validator, and the retention dates. The settled facts all land: the dates and judging weights, Llama 3.2 3B on the Mac only, the verbatim Privacy line, SAM 3D on fal.ai at $0.02 in Tier 2 only behind the Sat Oct 31 gate, photos out of the repo, "6 to 10 JPEG photos", the daily export, the one Oct 22 pick, the three items carried to Oct 26, and they/them for Ana and Priya.

What does not land comes in three groups.

1. **Player-visible consequences of the schema the FR structure drops.** Schema v1 makes Evidence visible in play, but the PRD never shows it, so the decoy edit has no surface. The schema says `loosen` unlocks a Rung "immediately", which contradicts FR-15's 90 s spacing and FR-16's trigger list. `merge`, `loosen` and `shortcut` have no stated player effect. The lock payload bounds and the active-puzzle rule are missing.
2. **Absolute privacy and integrity sentences that the spine's own adapters make untrue.** "Only to the Meta Model API and fal.ai" ignores the Baseten and Fireworks fallbacks and Modal storage. "Never reaches a browser" ignores the access-coded full-Room download. The ignore list is vaguer than the tested one.
3. **Demo-honesty and voice details.** The cut 1 wording "scripted reject" is the faked reject that AD-15 exists to prevent. The Disclosure copy has no cut 1 variant. The Greeting has no stated form when the verbatim adapter answers, which happens in Hosted mode, under cut 3 and after a timeout.

This review found 3 high, 10 medium and 11 low gaps. None reopens a settled fact.

## High

### H1. The Retention summary and §6.1 name too few destinations
- **Spine:** AD-5 defines `openai_compatible` adapters (Baseten, Fireworks) as per-role fallbacks for the Riddler and the Trickster. AD-7 and AD-9 store Judge-room photos, originals, sessions and cache on a Modal Volume and in a Modal Dict until Tue Nov 10. `GET /rooms/<room_id>/photos/<i>` is an open route (AD-9 guards only `POST /builds` and the full-Room download). AD-8's retention string quotes only the Meta and fal.ai summaries.
- **PRD:** §6.1 says "Photos and puzzle text go only to the Meta Model API (standard tier) and, in Tier 2, fal.ai". FR-6 names only those two.
- **Why it matters:** this is untrue as soon as a fallback engages (the Riddler and Trickster prompts carry labels, Clues and Rungs) and for every Judge room. The Retention summary is the honesty surface that sits next to the Privacy line.
- **Fix text:** in §6.1 write: "Photos and puzzle text go to the Meta Model API (standard tier). Puzzle text (labels, Clues, Rungs, never photos or solutions) goes to Baseten or Fireworks only when that role's fallback is active. In Tier 2, photos go to fal.ai. In Hosted mode, Judge-room photos, originals and Sessions are stored on Modal until Tue Nov 10." Add to FR-6: "The Retention summary is the same text `GET /meta` serves (architecture spine AD-8) and names every destination in §6.1 with its retention terms." If the fallbacks must not receive puzzle text, say so instead and add a Q to §13.

### H2. Evidence cards are missing from play, so the decoy has no surface
- **Schema / spine:** AD-3 says `PlayView` "drops `solution` and `provenance`, keeps `evidence`". Under decoy option A (recommended), `to_play_view` "merges real evidence and decoys into one unflagged `evidence_cards` list per puzzle, in a stable order seeded by room id". An accepted decoy "adds a false evidence card".
- **PRD:** FR-11 and §8 list the Scene, Thumbnail strip, Inventory, Wizard notes (Clue, Lore) and Cards, but no Evidence. The glossary defines Decoy as false Evidence that "looks identical to real Evidence", yet no FR shows Evidence to anyone.
- **Why it matters:** the UX contract will draw no Evidence surface. The decoy edit, which is UJ-3's main example, would then change nothing the player can see.
- **Fix text:** add a consequence to FR-11: "Wizard notes show each available Puzzle's Evidence cards (Interactable and read attribute). After an accepted `decoy`, the Puzzle's real and decoy cards are indistinguishable and appear in a stable order (architecture spine AD-3; Schema v1 §Open pick)." In §8 Play screen, change "Wizard notes with portraits, Clues, Lore" to "Wizard notes with portraits, Clues, Lore, Evidence cards". In UJ-3 step (2), add "a new Evidence card appears in the Wizard notes, indistinguishable from the real one".

### H3. `loosen` contradicts FR-15's spacing and FR-16's trigger list
- **Schema / spine:** the `loosen` payload `{puzzle, rung}` "unlocks that rung immediately (applied to session state, not the Room)". AD-12 says `loosen` is applied by `SessionStateMachine.apply` to `current_rung`. AD-4 says `RungChangeEvent.triggered_by` lists event ids, which here is the `trickster_card`.
- **PRD:** FR-15 says each later Rung arrives "at least 90 s after the previous Rung". FR-16 says every Rung change lists "its idle seconds or Wrong attempts". SM-C2 says "do not raise completion by giving Rungs sooner than FR-15 allows".
- **Why it matters:** an accepted `loosen` breaks a testable consequence as written. A test written from FR-15 would fail on the spine's own behavior, or the Trickster would quietly lose `loosen`.
- **Fix text:** in FR-15 add: "Exception: an accepted Trickster `loosen` opens its named Rung at once, inside the Trickster's window rules (FR-18), and is not counted against the 90 s spacing." In FR-16 change the consequence to "lists its idle seconds, Wrong attempts, or the Trickster Card that loosened it". In SM-C2 add "(a `loosen` Card is the only sanctioned early Rung)".

## Medium

### M1. "Never reaches a browser" ignores the full-Room download route
- **Spine:** AD-3 says the `Room` "leaves the server only through the full-Room download `GET /builds/<job_id>/room`". AD-9 guards that route with `X-Access-Code`. The hosted route is §13 Q4.
- **PRD:** §1 says "The solution never reaches a model prompt or the browser". §6.2 says "Solutions never reach a model prompt or a browser". NFR-5 says "solutions never enter a model prompt or play response".
- **Fix text:** in §1 and §6.2 write: "never reaches a model prompt or the play client; the only exit is the access-coded full-Room download for Luis (architecture spine AD-3, AD-9; §13 Q4)." NFR-5 already scopes this correctly.

### M2. The cut 1 wording invites a faked reject, and the Disclosure copy has no cut 1 variant
- **Spine:** AD-15 "Prevents: a faked reject". Cut 1 is realized "through the same scripted source with pre-authored proposals … the validator still runs on every card". The spine's Deferred list supersedes the delivery-plan line "the reject is not evaluated live".
- **PRD:** §11.2 cut 1 reads "Pre-authored Trickster edits plus a scripted reject; Validator still live". The §7 Disclosure example says "Trickster proposals replayed from a recording", which is false under cut 1 because the proposals are pre-authored, not recorded.
- **Fix text:** change cut 1 to "Pre-authored Trickster proposals, one written to fail; the live Validator accepts or rejects each". In §7 add the cut 1 Disclosure: "Trickster proposals were written in advance; the Validator ran live on each." Add to FR-26: "The Disclosure text matches the active Trickster source (live, scripted, cut 1)."

### M3. The player effect of each Trickster edit type is unstated
- **Schema:** `merge` makes `puzzle_b` require `puzzle_a`; `loosen` unlocks a Rung; `shortcut` removes one `requires` edge; there is at most one decoy per Puzzle (rule 9). AD-12: the client refetches `PlayView` when `room_revision` changes.
- **PRD:** FR-18 lists the four names, and only Decoy is defined in §3.
- **Why it matters:** the UX contract needs Card copy and a visible room change for each type. Ana must "see the room fight back" (UJ-3) without the Card exposing a solution.
- **Fix text:** add to §3: "**Merge** — an accepted edit making one Puzzle require another; **Loosen** — opens a named Rung now; **Shortcut** — removes one prerequisite." Add to FR-19: "On acceptance the Play screen reflects the edit at once: a new Evidence card (`decoy`), a Puzzle becoming locked behind another (`merge`), a Rung in the Hint area (`loosen`), or a Puzzle becoming available (`shortcut`). At most one decoy per Puzzle."

### M4. The Greeting has no defined form when the verbatim adapter answers
- **Spine:** AD-5 says `greet(derived)` times out at 5 s, after which "the verbatim adapter answers (the rung text; a template filled with the numbers)". AD-14 makes the Guide verbatim in Hosted mode. Cut 3 also makes it verbatim.
- **PRD:** UJ-4 and FR-21 describe only the phrased Greeting ("you held out long past the first nudge"). §7 gives its tone but no template.
- **Fix text:** add to FR-21: "When phrasing is unavailable (Hosted mode, cut 3, or past 5 s) the Greeting is a fixed template filled from the Derived block (for example, the number of Sessions and the seconds before the first hint), held to the same tone and naming no object or solution." Add the template line to §7.

### M5. The input requirement must be stated before upload, not only on rejection
- **Spine:** AD-7 says "the README and the capture screen state the input requirement as '6 to 10 JPEG photos'".
- **PRD:** FR-1 states it only in the rejection message. §8 lists "messages for rejected formats".
- **Fix text:** add to FR-1: "The Capture screen and the README state '6 to 10 JPEG photos' before any upload, with the iPhone Most Compatible setting." Add "input requirement" to §8 Capture screen.

### M6. Build failure and waiting states are missing from the UX inputs
- **Spine:** the job statuses include `queued` and `failed`. A runner that dies is marked `failed` with its stage (AD-7). The typed errors include `ProviderError`, `SpendCapExceeded` and `BuildQuotaExceeded` with the envelope `{error: {code, message, stage}}` (AD-13). Hosted mode runs `max_containers=1` (AD-9).
- **PRD:** §8 lists messages only for rejected formats, `needs_more_photos` and `needs_recapture`. FR-28 says "A refused call is surfaced to the player or Luis".
- **Fix text:** in §8 Capture screen add "`queued` state; `failed` with the stage it stopped at; Spend cap reached; Build quota reached (Hosted)". Change FR-28 to: "A refused call ends the Build `failed` with a plain Spend-cap message on the Capture screen; inside play it shows as a skipped Card (FR-19)."

### M7. Lock bounds and the active-puzzle rule are missing
- **Schema:** rule 7 sets `code` at 3 to 6 characters, `order` at 3 to 5 ids, `use_on` as two distinct ids, and `find` as one id.
- **Spine:** AD-4 says "the active puzzle for idle and hint events is the puzzle of the most recent `lock_input` or attempted click".
- **PRD:** neither appears. The UX contract needs the code field length, the expected `order` length, and which Puzzle's Rung a Hint request returns when several Puzzles are open.
- **Fix text:** add to FR-12: "A `code` is 3 to 6 characters; an `order` sequence is 3 to 5 Hotspots." Add to FR-14: "A Hint request returns the Rung of the active Puzzle, which is the one most recently attempted by lock input or click."

### M8. "Hosted" in Ledger, Cache and FR-27 collides with Hosted mode
- **Spine:** AD-6 says "every hosted adapter call", meaning every paid cloud API call, in both modes.
- **PRD:** the glossary says "Ledger — Append-only record of every priced hosted model call". FR-27 says "an identical hosted call". FR-28 says "every uncached hosted call". The glossary defines Hosted mode separately, so a reader can take the Ledger to cover only the Modal deployment.
- **Fix text:** replace "hosted model call" or "hosted call" with "paid cloud model call (Meta Model API, fal.ai, Baseten, Fireworks), in either mode" in the Ledger and Cache entries, FR-27, FR-28 and §4.9.

### M9. The FR-36 ignore list is vaguer than the tested one
- **Spine:** AD-8: "a test asserts `.gitignore` contains `rooms/`, `photos/`, `captures/`, `uploads/`, `*.heic`, `.cache/`". `rooms/` holds the stored originals and Sessions. AD-14: `.env` is ignored, `.env.example` lists every key, and both are tested. AD-9: the live ledger is ignored and the daily exports are committed.
- **PRD:** FR-36 says "Photo input folders, HEIC files, and the Cache are git-ignored".
- **Fix text:** change it to: "`rooms/` (stored photos, originals, Sessions), `photos/`, `captures/`, `uploads/`, `*.heic`, `.cache/` and `.env` are git-ignored, asserted by an offline test; only the daily Ledger exports and outputs are committed." The second FR-36 bullet ("beyond a Session's transient Event log") reads as if the Derived block may sit in the log, while AD-8 says the hosted server "never persists `derived` … and never joins its transient session log to a profile". Reword it to: "The hosted server persists no Derived block or Player profile data and never links a Session log to a profile." The spec reconciliation covers this point at more length.

### M10. The schema freeze and change route are absent
- **Schema / spine:** "The schema freezes Mon Oct 26; later changes go through `bmad-correct-course`."
- **PRD:** §11.1 and §13 Q1 give the Oct 22 pick but not the freeze.
- **Fix text:** add rows to §11.1: "Thu Oct 22: Schema review, decoy pick only" and "Mon Oct 26: Schema v1 frozen; later changes through correct-course". If the UX and epics runs take the freeze as given, add it to §0 instead.

## Low

- **L1. Derived names and ranges.** The spine uses `time_to_first_hint_s: float | null` and `persistence in [-1, 1]` (AD-8); the PRD glossary says `time_to_first_hint` with no ranges. Fix: use the spine names, and add to FR-21 "persistence in −1 to 1; values outside the bounds are refused".
- **L2. Provenance field.** `applied_edits[]` was approved Oct 21 (Schema v1 Room; AD-16). FR-30 omits it. Fix: add "and applied Trickster edit ids (empty on the stored Room)".
- **L3. Retention edge.** AD-8 deletes hosted Session logs "24 h after their last event or when their room is deleted", and the app never deletes local `rooms/` or `.cache/`. Fix: add both to FR-33.
- **L4. Cut 2 in Hosted mode.** AD-8 says the `/profile/<name>` route is "absent in hosted mode". The PRD does not say what a judge's profile does under cut 2. Fix: in FR-20 add "Under cut 2, Hosted mode behavior is stated in the README (architecture spine AD-8)", and decide it when cut 2 is taken.
- **L5. Tier 2 counts.** FR-34 says "Up to 20 objects", but the Room caps Interactables at 12 (Schema v1, AD-7). AD-6 seeds `reconstruct3d` at $0.02 inside the ledger, so fal.ai spend draws on `SPEND_CAP_USD`, while NFR-6 lists it as a separate "$6 cash". Fix: "up to 20 reconstructed instances from at most 12 Interactables", and "fal.ai calls are priced in the Ledger against the Spend cap and stay within $6 cash".
- **L6. UJ-1 climax.** "The first Clue names Ana's mug and a word printed on it" can read as the Clue quoting the code. Rule 5 and AD-3 check the Clue for solution tokens. Fix: "the first Clue points at Ana's mug and what is printed on it, without quoting the year".
- **L7. No-hint line tone.** AD-4 returns "a fixed no-hint line when none is open". §7 has no copy for it, and this is the moment the Guide most risks reading as a refusal instead of help. Fix: add to §7: "No-hint line: encouraging and in character, says help is coming, never 'no'." Example: "Look around a little longer; I'll speak up if you stay stuck."
- **L8. No optimistic locks.** AD-4 says "the client renders state and posts events, never infers lock state". Fix: add to FR-12 "A lock shows as open only after the server confirms it."
- **L9. Single retention source.** AD-8 keeps the retention text as one string served by `GET /meta`. FR-6 and FR-26 describe it twice. This is folded into the H1 fix.
- **L10. DOM-only fallback.** AD-11 keeps the hotspot id contract in a DOM-only fallback. The PRD has no rendering fallback. Optional fix: add to NFR-10 "a DOM-only Scene fallback keeps every Hotspot".
- **L11. Spine inconsistency, no PRD change.** AD-13 says Trickster errors "become a rejected card (AD-4)", while AD-4 records them as a skipped card with `reason: provider_unavailable`. The PRD follows AD-4 (FR-19, UJ-3), which is correct. Flag this to the spine owner so AD-13 reads "skipped card".

## Confirmed as landed (spot checks)

- AD-3: sentinel tests (FR-9, FR-14, FR-37); reasons never quote a token (FR-8); the regeneration prompt carries only the reasons (FR-10).
- AD-4: player text never travels as text (FR-14); seventh Trickster call refused (FR-18); skipped Card on a provider error or the Spend cap (FR-19).
- AD-5: Guide input `(rung_text, derived)`, prompt under 400 tokens, 5 s fallback (FR-17); Hosted mode refuses a Guide model (FR-17).
- AD-6: `CACHE=off` still priced; a regeneration is never served its own answer (FR-27).
- AD-7: 6 to 10 JPEG; 1280 px with EXIF applied; originals unmodified (FR-1); fewer than 5 survivors ends `needs_more_photos` (FR-4); a 260 s Build reaches the player by polling (FR-5).
- AD-8: nudge threshold formula and 60 to 135 s clamp (FR-15, FR-21); demo results flagged and excluded (FR-22).
- AD-9: 21st Build refused; access-coded Builds (FR-32); daily exports and the guarded reset (FR-29).
- AD-10: the timescale never touches the capture timer or the Event log (FR-24). FR-24's arithmetic at 6x checks out: about 30 s on Wrong attempts and 45 s on idle.
- AD-12: no Dry run on edits; the stored Room is never mutated (FR-19).
- AD-15: `GET /meta` fields (FR-26).
- Schema v1: lore of at most 60 words; three Rungs increasing in length; exactly one Exit puzzle; inventory from `find`; the `order` buffer resets on a mismatch.
