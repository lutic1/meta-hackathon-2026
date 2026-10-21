---
title: "Schema v1: Keyframe"
status: final
created: 2026-10-20
updated: 2026-10-21
---
# Schema v1: Keyframe

The Tier 1 / Tier 2 contract referenced by `addendum.md` §Schema v1 and realized once in `src/domain/schema.py` (architecture spine AD-2). The reviewers' changes were approved Oct 21 and are applied below. One pick remains for the Thu Oct 22 review: the decoy storage shape (§Open pick). The schema freezes Mon Oct 26; later changes go through `bmad-correct-course`.

## Fields

Ids are prefixed ULIDs assigned by server code only: `room_`, `pz_`, `ix_`, `te_` (spine AD-18). Pixel coordinates are in the space of the stored downscaled 1280 px JPEG unless a field says otherwise.

Room: `id`, `created`, `photos[]` (`hash` = sha256 of the stored downscaled JPEG bytes, `size`, downscaled and original paths; JPEG only), `interactables[]`, `puzzles[]`, `provenance` (model ids, prompt hashes, stage timings, regeneration count, spend per stage, `applied_edits[]`: ids of accepted Trickster edits folded into a session's effective Room, empty on the stored build Room). No `profile_name`; no `exit_puzzle_id`.

Interactable: `id` (`ix_`, minted by the segment stage after mask selection), `label` (the noun phrase sent to SAM), `photo` (index into `photos[]` in upload order), `box` (`[x0, y0, x1, y1]` in pixels, converted from the vision call's 0 to 1000 grid at segment time), `polygons` (list of polygons `[[x, y], ...]`, one per instance; `null` only before the segment stage completes; when SAM returns nothing the segment stage writes the box rectangle as the single polygon), `instances` (count when plurals are grouped), `attributes[]` (what the vision call reported, verbatim), `tier2` (optional GLB path and placement; the only field in original-photo pixels; pose from fal's metadata JSON if present, else hand-placed).

Puzzle: `id` (`pz_`; the Riddler emits ordinal keys `p1` to `p6`, mapped by the author stage), `lock_type` one of `code`, `order`, `use_on`, `find`; `requires[]` (puzzles that must be open first); `solution`, a tagged union by `lock_type`: `code` {`code`}, `order` {`interactables`: ordered `ix_` list}, `use_on` {`item`, `target`}, `find` {`target`}; `evidence` {`interactable`, `visible_attribute`}; `clue`; `lore` (at most 60 words); `rungs` {`nudge`, `direction`, `near_answer`}; `is_exit`. Four to six per room, exactly one with `is_exit: true`.

TricksterEdit: `id` (`te_`), `type` one of `decoy`, `merge`, `loosen`, `shortcut`; `puzzle`; `payload`, a tagged union by `type`; `validator_result` {`ok`, `reasons[]`}; `accepted`; `window`. Edits live in the session log as `trickster_card` events and never on the stored Room (spine AD-12). Both outcomes render as cards.

Payload by type: `decoy`: {`interactable`, `visible_attribute`} adds a false evidence card for `puzzle`, which is never the exit puzzle (storage per §Open pick); `merge`: {`puzzle_a`, `puzzle_b`} makes `puzzle_b` require `puzzle_a`; `loosen`: {`puzzle`, `rung`} unlocks that rung immediately (applied to session state, not the Room); `shortcut`: {`puzzle`} removes one `requires` edge. Re-validation runs validator rules 1 to 8 (and rule 9 once the decoy pick is made) on `apply_edit(room, edit)` (no dry run); a failing result is shown as the rejected card and the effective Room is unchanged.

API models, shapes defined in the architecture spine: `RoomDraft` (AD-7), `RoomView` and `PlayView` (AD-3), `ArchitectResponse` (AD-18), `DryRunAnswers` (AD-12, keyed by puzzle id, reusing the solution union), `Derived` and `RoomResult` (AD-8), `Meta` (AD-15), and the event models (AD-4). `GET /schema` returns all of them.

## Lock input and inventory

`code` is typed into the lock's field; `order` is judged against the trailing hotspot-click buffer when it reaches solution length (a mismatch is one wrong attempt and resets the buffer); `find` is a click on the target hotspot; `use_on` drags an inventory item onto the target hotspot. Inventory: solving a `find` puzzle moves its interactable into the inventory; `use_on.item` must be an interactable collected by a `find` puzzle listed in `requires` (validator rule 8).

## Validator rules

All deterministic. Reasons are structured `{rule, puzzle_id, field}` with a fixed message per rule and never quote an offending token or an answer (spine AD-3).

1. `requires` forms a DAG.
2. Every puzzle is reachable from the puzzles with no prerequisites; the exit is reachable from every other puzzle.
3. Every interactable named by a solution, evidence, or `use_on` pair exists.
4. `evidence.visible_attribute` appears, case-folded, in the attributes the vision call reported for that interactable.
5. No rung may contain a solution token except as allowed below. Solution tokens per lock type: `code`: the code string and each of its digits; `order`: the labels of the listed interactables in that sequence (a rung may name at most one of them); `use_on`: the two labels together in one rung (a rung may name one, never both); `find`: the label of the target interactable. `nudge` and `direction` contain no solution token; `near_answer` follows the per-type allowance above; `near_answer` is also checked against `clue`. Matching is case-folded. Code strings and each of their digits match as exact whole tokens regardless of length; for label words, only whole words longer than three characters match.
6. `lore` is 60 words or fewer; the three rungs are non-empty and increase in length.
7. Exactly one puzzle has `is_exit: true` (checked first); payloads are well-formed: `code` 3 to 6 characters, `order` 3 to 5 ids, `use_on` two distinct ids, `find` one.
8. Every `use_on.item` is the interactable of a `find` puzzle listed in that puzzle's `requires`.

## Dry run

A second `muse-spark-1.3` call receives the photos, the labels, every `clue`, and all three `rungs`, never the solutions, and returns `DryRunAnswers`, one answer per puzzle in the solution shape; `check_dry_run` compares them in the domain and a mismatch is a failure. Any failure regenerates the room with the structured failure reasons (never the previous draft) in the Riddler prompt; after 2 regenerations the build ends with status `needs_recapture`.

## SAM mask selection

One `sam-3.1` call per label on its clearest photo; selection runs in `domain/masks.py`. The mask with the best IoU against the vision box is kept; for a plural label ("books") every mask with IoU above 0.2 is grouped as instances of one interactable; masks under 1% of the image are dropped; the room is capped at 12 interactables, highest vision confidence first. Polygons come from `meta-sam-parser`'s SVG path, scaled from the mask raster to the frame and simplified. [ASSUMPTION] Minimum: if fewer than 5 survive, the build ends with status `needs_more_photos` before any Riddler call, since four to six puzzles need that many distinct objects.

## Open pick for Thu Oct 22: decoy storage

An accepted `decoy` edit has to live somewhere `apply_edit(room, edit)` can write and `PlayView` can render, without telling the player which card is false. The payload is the same in every option: {`interactable`, `visible_attribute`} plus the edit's `puzzle`. Whichever option is picked adds validator rule 9: the decoy's interactable exists; its `visible_attribute` is one the vision call reported for that interactable; the pair differs from every puzzle's real `evidence`; the target puzzle is not the exit; at most one decoy per puzzle; the attribute text contains no solution token under rule 5.

| | A. `Room.decoys[]` (recommended) | B. `Puzzle.evidence` becomes a list with `is_decoy` | C. No Room field; cards from the session log |
|---|---|---|---|
| Shape | `decoys: [{id: te_, puzzle: pz_, interactable: ix_, visible_attribute}]`, empty on the stored build Room | `evidence: [{interactable, visible_attribute, is_decoy}]`; the Riddler writes one real entry, `apply_edit` appends a decoy | Accepted `trickster_card` events carry the payload; the session's `PlayView` adds them as extra cards; `apply_edit` is a no-op for `decoy` |
| What changes | One new Room field; `to_play_view` merges real evidence and decoys into one unflagged `evidence_cards` list per puzzle, in a stable order seeded by room id | The Riddler response schema, rule 4 (iterates the list), `to_prompt_view` and `to_play_view` (both must strip `is_decoy`) | AD-12's fold rule (the effective Room no longer shows every accepted edit) and `PlayView` assembly (reads the Room and the log) |
| Leak risk | One merge function, one test asserting decoy and real cards are indistinguishable in `PlayView` | A redaction slip exposes `is_decoy`, the same class of leak as a solution; every consumer of `evidence` must remember it | Low for the flag, but what the player sees is defined in two places |
| Validation | Rule 9 runs inside `validate(apply_edit(room, edit))` like every other edit | Same, after rule 4 is reworked | `validate(apply_edit(...))` cannot see the decoy; all decoy checks move into `validate_edit` |
| Provenance | `applied_edits` maps 1:1 to `decoys[].id` | `applied_edits` maps to list entries | `applied_edits` has nothing on the Room to point at |
| Cost to build | About 1 h (field, merge, rule 9, two tests) | About 2 h plus re-testing the Riddler prompt | About 1 h, plus an amendment to AD-12 |

Recommendation: A. It leaves the already-approved `evidence` field, the Riddler schema, rules 1 to 8, and both views untouched except for one merge, and it keeps AD-12 as written.
