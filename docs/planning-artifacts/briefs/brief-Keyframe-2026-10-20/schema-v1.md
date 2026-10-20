---
title: "Schema v1: Keyframe"
status: final
created: 2026-10-20
updated: 2026-10-20
---
# Schema v1: Keyframe

The Tier 1 / Tier 2 contract referenced by `addendum.md` §Schema v1. The field list below is the Oct 20 draft; it is reviewed Thu Oct 22 against the two spikes and frozen Mon Oct 26. Tier 2 changes go through `bmad-correct-course`.

## Fields

Room: `id`, `created`, `profile_name`, `photos[]` (hash, size, downscaled and original paths), `interactables[]`, `puzzles[]`, `exit_puzzle_id`, `provenance` (model ids, prompt hashes, stage timings, regeneration count).

Interactable: `id`, `label` (the noun phrase sent to SAM), `photo` (clearest photo index), `box` (0 to 1000 grid, from the vision call), `mask` (polygon from the decoded SAM raster, null on the box fallback), `instances` (count when plurals are grouped), `attributes[]` (what the vision call reported, verbatim), `tier2` (optional GLB path, placement; pose from fal's metadata JSON if present, else hand-placed [open question, checked in the pre-Oct 26 fal spike]).

Puzzle: `id`, `lock_type` one of `code`, `order`, `use_on`, `find`; `requires[]` (puzzles that must be open first); `solution` (code string, ordered id list, {item, target} pair, or interactable id); `evidence` {`interactable`, `visible_attribute`}; `clue`; `lore` (at most 60 words); `rungs` {`nudge`, `direction`, `near_answer`}. Four to six per room, exactly one with `is_exit: true`.

TricksterEdit: `id`, `type` one of `decoy`, `merge`, `loosen`, `shortcut`; `puzzle`; `payload`; `validator_result` {`ok`, `reasons[]`}; `accepted`; `window`. Both outcomes render as cards.

Payload by type: `decoy`: {interactable, attribute} adds a false `evidence` card tied to an existing interactable (never to the exit puzzle); `merge`: {puzzle_a, puzzle_b} makes puzzle_b require puzzle_a; `loosen`: {puzzle, rung} unlocks that rung immediately; `shortcut`: {puzzle} removes one `requires` edge. Re-validation runs validator rules 1 to 8 on the edited Room (no dry run); a failing result is shown as the rejected card and the Room is unchanged.

## Lock input and inventory

`code` is typed into the lock's field; `order` is the sequence of hotspot clicks since the last wrong attempt; `find` is a click on the target hotspot; `use_on` drags an inventory item onto the target hotspot. Inventory: solving a `find` puzzle moves its interactable into the inventory; `use_on.item` must be an interactable collected by a `find` puzzle listed in `requires` (validator rule 8).

## Validator rules

All deterministic:

1. `requires` forms a DAG.
2. Every puzzle is reachable from the puzzles with no prerequisites; the exit is reachable from every other puzzle.
3. Every interactable named by a solution, evidence, or `use_on` pair exists.
4. `evidence.visible_attribute` appears, case-folded, in the attributes the vision call reported for that interactable.
5. No rung may contain a solution token except as allowed in parentheses. Solution tokens per lock type: `code`: the code string and each of its digits; `order`: the labels of the listed interactables in that sequence (a rung may name at most one of them); `use_on`: the two labels together in one rung (a rung may name one, never both); `find`: the label of the target interactable. `nudge` and `direction` contain no solution token; `near_answer` follows the per-type allowance above; `near_answer` is also checked against `clue`. Matching is case-folded on whole words longer than three characters.
6. `lore` is 60 words or fewer; the three rungs are non-empty and increase in length.
7. Payloads are well-formed: `code` 3 to 6 characters, `order` 3 to 5 ids, `use_on` two distinct ids, `find` one.
8. Every `use_on.item` is the interactable of a `find` puzzle listed in that puzzle's `requires`.

## Dry run

A second `muse-spark-1.3` call receives the photos, the labels, every `clue`, and all three `rungs`, never the solutions, and must return an answer per puzzle in the solution shape; a mismatch is a failure. Any failure regenerates the room with the failures listed in the Riddler prompt; after 2 regenerations the capture screen asks for a re-capture.

## SAM mask selection

One `sam-3.1` call per label on its clearest photo. The mask with the best IoU against the vision box is kept; for a plural label ("books") every mask with IoU above 0.2 is grouped as instances of one interactable; masks under 1% of the image are dropped; the room is capped at 12 interactables, highest vision confidence first. [ASSUMPTION] Minimum: if fewer than 5 survive, the capture screen asks for more photos before any Riddler call, since four to six puzzles need that many distinct objects.
