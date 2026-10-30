# Glossary

Companion to `SPEC.md`.

| Term | Meaning |
|---|---|
| Council | The four wizard roles that build and run a room: Architect, Riddler, Guide, Trickster. One orchestrator, four role prompts; the Guide's model is local, the others run on `muse-spark-1.3`. |
| Architect | The vision call that lists objects, picks the clearest photo per object, and returns boxes and readable attributes; its labels drive the `sam-3.1` calls. |
| Riddler | The call that writes the puzzle chain (puzzles, requires graph, clues, lore, rungs) from the interactables. |
| Guide | Rung selection in code over the event log, plus a local phrasing model (Llama 3.2 3B on Ollama) that never holds the solution. |
| Trickster | The role that proposes one bounded mid-game change from a fixed menu; the validator decides whether it applies. |
| Interactable | A typed object from the player's photos: label, photo, box, mask hotspot, instances, attributes (`schema-v1.md`). Capped at 12 per room, minimum 5. |
| Puzzle, lock type | A lock on the chain: `code` (typed), `order` (click sequence), `use_on` (inventory item onto a target), `find` (click the target). 4 to 6 per room, exactly one exit. |
| Rung | A hint level: nudge, direction, near-answer. Three per puzzle, increasing in length, none holding a solution token except the near-answer allowance in validator rule 5. |
| Treasure chest | Story mode's hint policy (`HINT_POLICY=chest`, the default): the Guide's 2 hints (`HINT_CAP`) for a whole Session, each asked one opening the next Rung of the riddle in play; no Rung opens by itself. (amended 30 Oct 2026, story mode) |
| Story | The Room's wizard lines (`Room.story`): the five-beat intro, an opening and a solved line per riddle, the closing lines. Written at build time by the `story` stage (`muse-spark-1.3`, role `storyteller`), each line checked by the story's line rules, a refused line filled from the fixed templates; null on a Room built before story mode, which plays the templates. (amended 30 Oct 2026, story mode) |
| Area, pan | A photo's place in story mode: the part of the room it shows and its left-to-right order there, which the walk turns through instead of a thumbnail strip. (amended 30 Oct 2026, story mode) |
| Validator | The nine deterministic rules in `schema-v1.md`: rules 1 to 8 on every room, rules 1 to 9 on a Trickster edit (rule 9 covers Decoys, stored as `Room.decoys[]`). |
| Dry run | A second Spark call that sees photos, labels, clues, and rungs, never solutions, and must reach every answer; failure regenerates the room. |
| Regeneration | A repeat of Riddler plus dry run after a failure; at most 2, then re-capture. |
| Cut n | One of the eight scope reductions in `delivery-plan.md`, applied nightly in order and never carried. |
| Tier 1 / 1.5 / 2 / 3 | Floor (photo scenes, full council, backup video); cuts restored plus hosted URL and voice; walkable 3D room, gated, default no-go; splat shell, never gating. |
| T0, T1 | Upload click; first hotspot responding. The capture target is T1 − T0 ≤ 120 s. |
| Backup video | The Tier 1 demo recording made Sun Nov 1 by 2:00 PM from whatever runs; its existence Sat Oct 31 night is the only early gate to Tier 2. |
| Capture proof | The unedited, timed video of a never-built room, `CACHE=off`, kept only under 200 s. |
| Derived block | The four profile features (`time_to_first_hint`, `mean_rung_per_lock_type`, `persistence`, `sessions`) that are all the Guide model and the greeting may see. |
| Privacy line | "the player profile stays on your machine." Verbatim in the README and on the capture screen. |
| Local mode, hosted mode | The pipeline in-process on the Mac; the same code on Modal CPU behind the judge URL. Same endpoints, same async job API. |
| Mock provider | The `ModelProvider` implementation with scripted replies that agents build and test against; no network, no spend. |
