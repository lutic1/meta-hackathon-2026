---
title: Keyframe
status: draft
created: 2026-10-21
updated: 2026-10-21
---

# PRD: Keyframe

Luis Ticas · 2026-10-21 · Indie track, Meta Global AI Developer Hackathon (Cerebral Valley)

## 0. Document Purpose

This PRD is for Luis Ticas as builder and reviewer, and for the two runs that consume it next: `bmad-ux` (the UX contract) and `bmad-create-epics-and-stories` (the epic re-extraction). It builds on three approved inputs and does not duplicate them: the product brief (`docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/`, with its addendum and Schema v1), the spec (`docs/specs/spec-keyframe/SPEC.md` and companions), and the architecture spine (`docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md`). The PRD restates requirements at the product level, meaning what a player, a judge, or Luis can do and what must be observably true; mechanism stays in the spine and is cited as "architecture spine AD-n".

FR-1 to FR-36 carry the meaning and numbering of FR1 to FR36 in `docs/planning-artifacts/epics.md`; FR-37 (Clue cards) is new. NFR-1 to NFR-13 mirror NFR1 to NFR13 there. Numbers are stable ids, so FR-37 sits under §4.7. Vocabulary is anchored in §3 and used verbatim. Inferences are tagged inline as `[ASSUMPTION A-n]` and indexed in §14.

## 1. Vision

Keyframe turns the room you are sitting in into an escape room. A player photographs a living room or a study, uploads 6 to 10 JPEG photos in Chrome, and about two minutes later plays a puzzle chain built from their own things: the code is the year printed on their mug, the last lock opens on their bookshelf. No two players get the same room, because no two players own the same objects.

A council of four wizard roles runs the room. The Architect looks at the photos and names the objects; the Riddler writes the puzzle chain and must prove it solvable before anyone plays it; the Guide watches how the player plays and offers help one rung at a time, never the answer; the Trickster changes the room between puzzles, but only when the Validator agrees the change is fair. The solution never reaches a model prompt or the browser, so the player cannot talk the room open. The Guide's phrasing model runs on the player's own Mac, and the player profile stays on your machine.

Keyframe comes back to the player: the second room greets them from how they played the first and adapts how soon help arrives. For the hackathon, Keyframe shows Meta's model stack taking a solo builder from household photos to a verified, adaptive game in one pipeline, with segmentation, structured agent output, and a small local model each doing what it does best.

## 1a. Why Now

In 2026 the Meta Model API put object segmentation from a noun phrase (`sam-3.1`), schema-constrained multimodal reasoning (`muse-spark-1.3`), and image generation (`muse-image-1.0`) behind one key, while Llama 3.2 3B runs locally on a 16 GB laptop through Ollama. Turning a casual home photo into typed, clickable objects with a verified puzzle graph over them is now a solo build. The forcing deadline is the hackathon: build Mon Oct 26 to Wed Nov 4 2026, submission before 9:00 AM ET Wed Nov 4 (deadline 9:00 PM ET), judged on Impact 30%, Use of Meta AI Tooling 25%, Technical Depth 20%, Demo 25%.

## 2. Target User

### 2.1 Jobs To Be Done

`[ASSUMPTION A-8: jobs inferred from the brief's "Who This Serves" and demo narrative, confirm]`

- **Functional (player):** turn a familiar room into a 15 to 25 minute puzzle session with nothing to buy, travel to, or write.
- **Emotional (player):** recognize one's own objects in a clue; solve with help that scaffolds instead of giving the answer away.
- **Social (player):** come back for a second room and feel the game remembers how they play.
- **Judge:** verify in minutes that the pipeline is real (own-room build, visible triggers, no win by persuasion) and see which Meta model did what.
- **Builder (Luis Ticas):** prove capture, integrity, adaptive help, and memory on camera, inside the Spend cap, without trading Tier 1 reliability for scope.

### 2.2 Non-Users (v1)

`[ASSUMPTION A-9: boundary inferred from the spec's non-goals, confirm]`

- Players without a laptop running Chrome (no native mobile client, no live phone capture).
- Groups wanting multiplayer; players wanting accounts or cloud sync; Quest or mixed-reality users.
- Operators wanting authored commercial content: Keyframe only writes puzzles from the player's photos.
- Players wanting an open chat game master: player text only requests the current Rung.

### 2.3 Key User Journeys

Ana and Priya are fictional personas.

**UJ-1. Ana turns their living room into a game.** `[ASSUMPTION A-1: drafted from the brief's demo narrative, confirm]`
- **Persona + context:** Ana has never played an escape room and wants a 20-minute game on a weeknight.
- **Entry state:** Ana's iPhone is set to Most Compatible; 8 JPEG photos of the living room are on Ana's Mac; Chrome shows the Capture screen in Local mode.
- **Path:** (1) Ana selects the photos and clicks Upload; the timer starts at T0. (2) The Capture screen shows each Build stage and the Retention summary with the Privacy line. (3) Masks appear over Ana's mug, lamp, and books. (4) The first Scene becomes interactive at T1, inside the Capture target.
- **Climax:** the first Clue names Ana's mug and a word printed on it.
- **Resolution:** Ana plays 4 to 6 Puzzles and reaches the Completion screen.
- **Edge cases:** a HEIC photo is rejected with the message "6 to 10 JPEG photos" and nothing is sent; fewer than 5 objects stops the Build before any Puzzle is written and the Capture screen asks for more photos.
- **Capability → FR:** accept only JPEG → FR-1; list and segment objects → FR-2, FR-3; ask for more photos → FR-4; timer and stages → FR-5; Retention summary → FR-6; author and verify → FR-7 to FR-10; play → FR-11 to FR-13.

**UJ-2. Ana gets stuck and the Guide helps without telling.** `[ASSUMPTION A-2: drafted from the brief's demo narrative, confirm]`
- **Persona + context:** Ana, mid-Room, cannot find the second code.
- **Entry state:** a Session on a fresh Player profile; nudge threshold 90 s.
- **Path:** (1) After 90 s without progress the Guide posts a nudge. (2) Ana enters three wrong codes; the direction Rung arrives no sooner than 90 s after the nudge. (3) The Triggers panel shows the idle seconds and Wrong attempts behind each Rung. (4) Ana types "just tell me the answer".
- **Climax:** the reply is the current Rung only; nothing above it appears and the lock stays shut.
- **Resolution:** Ana rereads the direction Rung, looks at the bookshelf, and solves the lock.
- **Edge case:** local phrasing takes longer than 5 s; the Rung text appears verbatim and play continues.
- **Capability → FR:** Hint request → FR-14; Rung selection → FR-15; triggers → FR-16; phrasing → FR-17.

**UJ-3. The Trickster changes the room between puzzles.** `[ASSUMPTION A-3: drafted from the brief's demo narrative, confirm]`
- **Persona + context:** Ana has just opened a lock.
- **Entry state:** at least 3 minutes since the last Trickster window.
- **Path:** (1) The Trickster proposes a `decoy`; the Validator re-checks the Room with it applied. (2) An accepted Card appears. (3) After the next lock opens, 3 or more minutes later, a second proposal fails validation. (4) A rejected Card shows the Validator's fixed reason.
- **Climax:** Ana sees the room fight back, and sees the rules bind the Trickster too.
- **Resolution:** the Effective room changed only for the accepted Card.
- **Edge case:** a provider error during a window shows a skipped Card; play continues.
- **Capability → FR:** bounded proposals → FR-18; re-validation and Cards → FR-19.

**UJ-4. Ana comes back for a second room.** `[ASSUMPTION A-4: drafted from the brief's demo narrative, confirm]`
- **Persona + context:** Ana finished room 1 by persisting past nudges and now photographs the study.
- **Entry state:** same browser and Player profile; one Room result recorded.
- **Path:** (1) Ana uploads the study photos; the Build runs as in UJ-1. (2) The Greeting cites how Ana played room 1 ("you held out long past the first nudge") and names no object or solution. (3) Ana's positive persistence raises the nudge threshold toward 135 s.
- **Climax:** Ana feels recognized by the game, not tracked by a service.
- **Resolution:** room 2's Clues use objects absent from room 1; the Player profile stays in Ana's browser.
- **Capability → FR:** browser Player profile → FR-20; Greeting and thresholds → FR-21; demo results excluded → FR-22.

**UJ-5. Priya, a judge, plays the hosted demo and builds their own room.** `[ASSUMPTION A-5: drafted from the brief's demo narrative, confirm]`
- **Persona + context:** Priya, a hackathon judge, has ten minutes and wants proof the pipeline is real.
- **Entry state:** the hosted URL in Chrome; the Access code from the submission.
- **Path:** (1) Priya plays a Demo room from the hosted landing. (2) Rungs appear verbatim; the Disclosure says no Guide model runs in Hosted mode. (3) Priya enters the Access code and uploads 6 JPEG photos of their office. (4) After one Regeneration, the Build outlasts the host's 150 s web timeout.
- **Climax:** the Build still completes and Priya's Clues name Priya's own objects.
- **Resolution:** Priya plays the Judge room; it is deleted Tue Nov 10.
- **Edge case:** the 21st Build is refused with a quota message.
- **Capability → FR:** Demo rooms → FR-31; access-coded Builds → FR-32; deletion → FR-33; verbatim Rungs → FR-17.

**UJ-6. Luis records the capture proof and the main demo.** `[ASSUMPTION A-6: drafted from the brief's demo narrative, confirm]`
- **Persona + context:** Luis Ticas on Tue Nov 3, with a fresh room-2 Photo set never sent to the pipeline.
- **Entry state:** Local mode on the M1, `CACHE=off`, fresh Player profiles, IDE closed.
- **Path:** (1) Luis clears the Cache on camera and clicks Upload; the timer runs on screen from T0. (2) The first Hotspot responds at T1; the take is kept only under 200 s. (3) For the Main demo Luis runs the persuasion attack, three Rungs at a 6x Demo timescale, the Scripted Trickster, and the room-2 Greeting. (4) The demo disclosure overlay states the 6x timescale, the scripted replay, and earlier builds of the Room.
- **Climax:** a 2:00 Main demo (cap 2:30) and an unedited Capture proof, honest about every shortcut.
- **Resolution:** both videos are uploaded unlisted for the Wed Nov 4 submission.
- **Edge case:** a take past 200 s or with a second visible retry is discarded and re-shot.
- **Capability → FR:** Demo timescale → FR-24; Scripted Trickster → FR-25; Disclosure → FR-26; Cache bypass → FR-27.

**UJ-7. (Tier 2, gated) Ana walks the room in 3D and opens a lock by looking.** `[ASSUMPTION A-7: drafted from the brief's demo narrative, confirm]`
- **Persona + context:** Ana, replaying room 1, wants to move through it rather than flip photos.
- **Entry state:** the Tier 2 gate passed Mon Nov 2.
- **Path:** (1) The Room loads as a walkable 3D scene with reconstructed objects where they stand. (2) Ana walks to the bookshelf and looks at it. (3) The look triggers the `find` lock.
- **Climax:** a lock opens because Ana looked at a real object in a reconstructed room.
- **Resolution:** play continues with the same Puzzles and Guide as Tier 1.
- **Capability → FR:** walkable 3D Room → FR-34.

## 3. Glossary

- **Room** — One playable escape room from one Photo set: 5 to 12 Interactables, 4 to 6 Puzzles, provenance. Immutable once stored.
- **Effective room** — The Room as one Session sees it, with that Session's accepted Trickster edits applied; never stored back.
- **Demo room** — A Room seeded on the hosted server for judges; persists.
- **Judge room** — A Room built in Hosted mode with the Access code; deleted Tue Nov 10.
- **Photo set** — The 6 to 10 JPEG photos of one physical room for one Build; downscaled to a 1280 px long edge, originals kept for Tier 2.
- **Interactable** — A typed object from the Photo set: label, photo, box, Hotspot, instance count, attributes the Architect read.
- **Hotspot** — The clickable polygon of one Interactable on its photo, from the `sam-3.1` mask or, failing that, the box rectangle.
- **Scene** — One photo rendered with its Hotspots.
- **Puzzle** — One lock in the chain: Lock type, prerequisites, solution, Evidence, Clue, Lore, three Rungs.
- **Lock type** — `code` (typed), `order` (Hotspot clicks in sequence), `use_on` (Inventory item dragged onto a target), `find` (click the target).
- **Exit puzzle** — The one Puzzle per Room whose opening ends the Room.
- **Wrong attempt** — A failed `code` or `use_on` input, or a completed non-matching `order` sequence; never a click alone.
- **Clue** — Player-facing text pointing at a Puzzle's Evidence; holds no solution token.
- **Lore** — In-world flavor text per Puzzle, at most 60 words.
- **Evidence** — The Interactable and read attribute a Puzzle's solution depends on.
- **Decoy** — False Evidence added to a non-exit Puzzle by an accepted Trickster edit; looks identical to real Evidence.
- **Rung** — A hint level: nudge, direction, near-answer; increasing in length; no solution token beyond the near-answer allowance of Validator rule 5.
- **Hint request** — What all player text, typed or spoken, is reduced to; returns the current Rung only.
- **Hint area** — Where Rungs and Guide lines appear.
- **Triggers panel** — Shows each Rung change with the events that caused it.
- **Council** — The four wizard roles: Architect, Riddler, Guide, Trickster.
- **Architect** — The `muse-spark-1.3` vision call listing objects with clearest photo, box, and readable attributes.
- **Riddler** — The `muse-spark-1.3` call writing the Puzzles from the Interactables.
- **Guide** — Rung selection in code over the Event log, phrased by Llama 3.2 3B on Ollama on the player's Mac, or verbatim in Hosted mode.
- **Trickster** — The `muse-spark-1.3` role proposing one change between Puzzles from `decoy`, `merge`, `loosen`, `shortcut`.
- **Trickster edit** — One Trickster proposal with its Validator result and outcome.
- **Scripted Trickster** — Replays recorded (cut 1: pre-authored) proposals; the Validator still runs live.
- **Card** — The on-screen outcome of one Trickster edit: accepted, rejected (with the fixed reason), or skipped. Not a Clue card.
- **Validator** — The eight deterministic rules of Schema v1 (plus rule 9 with the decoy pick), applied to every Room and Trickster edit; reasons never quote a solution token or answer.
- **Dry run** — A `muse-spark-1.3` call that sees photos, labels, Clues, and Rungs, never solutions, and must reach every answer.
- **Regeneration** — Riddler plus Dry run repeated with the failure reasons only; at most 2.
- **Build** — One pipeline run from a Photo set to a stored Room; ends `done`, `failed`, `needs_more_photos`, or `needs_recapture`.
- **Session** — One play-through of one Room, 15 to 25 minutes.
- **Event log** — The append-only, server-timestamped record of a Session; Session state replays from it.
- **Room result** — Per-Room time, Rungs used, Wrong attempts, and per-Puzzle stats, recorded into the Player profile.
- **Player profile** — Room results plus the Derived block, stored in the browser (a local JSON file under cut 2); never on the hosted server.
- **Derived block** — `time_to_first_hint`, `mean_rung_per_lock_type`, `persistence`, `sessions`: all the Guide model and the Greeting may see.
- **Greeting** — The Guide's opening line for a returning player, from the Derived block only; names no object or solution.
- **Wizard portrait** — One of four Council images, generated once with `muse-image-1.0` and committed.
- **Clue card** — One image per Puzzle generated from the Clue text only with `muse-image-1.0`, cached, shown with the Clue (Tier 1.5).
- **Capture screen**, **Play screen**, **Completion screen** — The upload surface; the Session surface; the surface shown when the Exit puzzle opens (§8).
- **Thumbnail strip** — Scene thumbnails for moving between photos.
- **Inventory** — Interactables collected by solving `find` Puzzles; persists through the Session.
- **Wizard notes** — The panel holding each available Puzzle's Clue and Lore with the Wizard portraits. `[ASSUMPTION A-10: contents inferred, confirm]`
- **Capture target** — T1 − T0 ≤ 120 s on the M1 with `CACHE=off` and a never-built Photo set, or measured p50 plus 25% if re-based after Oct 27 to 28.
- **T0**, **T1** — The Upload click; the first Hotspot responding.
- **Backup video** — The Tier 1 demo recorded by Sun Nov 1 2:00 PM from whatever runs; its existence Sat Oct 31 night is the only early gate to Tier 2.
- **Capture proof** — The unedited, timed T0-to-T1 video of a never-built Room with `CACHE=off`; kept only under 200 s with at most one visible retry.
- **Main demo** — The edited, captioned video: 2:00 target, 2:30 cap.
- **Local mode** — The product on Luis's M1, Guide on Ollama.
- **Hosted mode** — The same product on Modal CPU behind the judge URL; Rungs verbatim; no Guide model.
- **Access code** — Unlocks Judge room Builds in Hosted mode; at most 20 Builds.
- **Ledger** — Append-only record of every priced hosted model call.
- **Spend cap** — `SPEND_CAP_USD`: $80 through Wed Nov 4, $25 from Thu Nov 5; a call that would pass it is refused.
- **Cache** — Stored responses to identical hosted calls, served unbilled when `CACHE=on`.
- **Mock provider** — Offline scripted stand-in for every model; no network, no spend.
- **Cut** — One of eight ordered scope reductions (§11.2), made nightly, never carried.
- **Tier 1** — The floor: FR-1 to FR-30 and FR-36 plus the Backup video.
- **Tier 1.5** — After the Backup video: Cuts restored, Clue cards, Hosted mode for judges, voice last.
- **Tier 2** — The walkable 3D Room; gated, default no-go.
- **Tier 3** — A Scaniverse splat shell; never gates anything.
- **Demo timescale** — `DEMO_TIMESCALE=n`: divides the nudge threshold, Rung spacing, and Trickster window by n; never the capture timer.
- **Disclosure** — Plain on-screen and README text naming each demo shortcut or mode in effect.
- **Retention summary** — Capture-screen statement of where photos and puzzle text go and each service's retention terms.
- **Privacy line** — Verbatim: "the player profile stays on your machine."

## 4. Features

### 4.1 Capture a room from photos

**Description:** The Architect and `sam-3.1` turn a Photo set into Interactables while a visible timer and stage make waiting read as progress. Realizes UJ-1, UJ-5, UJ-6. Mechanism: architecture spine AD-7, AD-18.

#### FR-1: Upload a JPEG photo set

The player can upload 6 to 10 JPEG photos of one room from the browser, each downscaled in the browser and sent with its original in one request. Realizes UJ-1, UJ-5.

**Consequences (testable):**
- Fewer than 6 or more than 10 photos is rejected.
- HEIC, PNG, and every other format are rejected with a message stating "6 to 10 JPEG photos"; no bytes reach a model.
- Each downscale has a 1280 px long edge with EXIF orientation applied; the original is stored unmodified.

#### FR-2: List the room's objects

The Architect can list the room's objects from one `muse-spark-1.3` vision call over all photos, giving each a clearest photo, a box, and readable attributes. Realizes UJ-1.

**Consequences (testable):**
- One Architect call per Build, all photos in one request, reasoning effort low, within 15 s.
- Attributes are stored verbatim as read and are the only attributes Evidence may cite (Validator rule 4).

#### FR-3: Segment objects into interactables

The system can segment each listed object with one `sam-3.1` call and select masks into 5 to 12 Interactables with polygon Hotspots. Realizes UJ-1.

**Consequences (testable):**
- One call per listed object, at most 12 concurrent, within 10 s for the stage.
- The best-overlapping mask with the Architect's box is kept; plural labels group masks as instances; masks under 1% of the image are dropped; at most 12 Interactables.
- An object with no mask gets its box rectangle as its Hotspot and behaves identically in play.

#### FR-4: Ask for more photos

The player can be asked for more photos when fewer than 5 Interactables survive. Realizes UJ-1.

**Consequences (testable):**
- With 4 or fewer Interactables the Build ends `needs_more_photos` with zero Riddler, Dry run, or Trickster calls.
- The Capture screen asks for more photos of the room.

#### FR-5: Show the timer and build stage

The player can watch a timer from T0 to T1 and the current Build stage, and receives the Room even when the Build outlasts one web request. Realizes UJ-1, UJ-5, UJ-6.

**Consequences (testable):**
- The timer starts on the Upload click and stops when the first Hotspot responds.
- The stage indicator advances through every pipeline stage in order. `[ASSUMPTION A-11: stage labels are plain words, confirm]`
- A 260 s Build (two Regenerations) still completes and reaches the player by polling (architecture spine AD-7).

#### FR-6: Show the retention summary

The player can read where photos and puzzle text go before uploading. Realizes UJ-1.

**Consequences (testable):**
- The Retention summary names the Meta Model API and, in Tier 2, fal.ai, with each service's retention terms.
- The Privacy line appears verbatim on the Capture screen.

### 4.2 Build a verified room

**Description:** No Room reaches a player until the Validator and a solution-blind Dry run agree it is solvable; this separates Keyframe from hollow riddle chains. Realizes UJ-1, UJ-5. Mechanism: architecture spine AD-3, AD-12, AD-13.

#### FR-7: Author the puzzle chain

The Riddler can author 4 to 6 Puzzles that reference only listed Interactables and attributes the Architect read. Realizes UJ-1, UJ-4.

**Consequences (testable):**
- Exactly one Exit puzzle; each Puzzle uses `code`, `order`, `use_on`, or `find` (`code` and `find` only under cut 6).
- Each Puzzle has a Clue, Lore of at most 60 words, and three Rungs.
- One Riddler call per attempt, reasoning effort medium, within 45 s; no reference to an Interactable outside the Room.

#### FR-8: Validate every room

The system can apply the eight Validator rules of Schema v1 to every Room before it is stored. Realizes UJ-1.

**Consequences (testable):**
- A Room failing any rule is never stored or playable.
- No nudge, direction, or Clue contains a solution token; near-answers stay within the per-Lock-type allowance of rule 5.
- Reasons are structured (rule, Puzzle, field) with a fixed message and never quote a solution token or answer.

#### FR-9: Dry-run every room

The system can require a Dry run that sees photos, labels, Clues, and Rungs, never solutions, to reach every answer. Realizes UJ-1.

**Consequences (testable):**
- A sentinel-solution test finds no solution in the Dry run prompt.
- Any mismatched answer fails the Room; reasoning effort low, within 30 s.
- Under cut 4 the Dry run is skipped and the Validator alone gates the Room.

#### FR-10: Regenerate or ask for re-capture

The system can regenerate a failed Room with its failure reasons at most 2 times, then ask for re-capture. Realizes UJ-1, UJ-5.

**Consequences (testable):**
- A Regeneration (about 75 s) carries the reason list only, never the previous draft.
- After the second failed Regeneration (the first under cut 7) the Build ends `needs_recapture` and the Capture screen asks for a re-capture.
- Provenance records the Regeneration count.

### 4.3 Play the room

**Description:** A 15 to 25 minute Session across photo Scenes of the player's own objects; the server judges every lock and the browser never holds a solution. Realizes UJ-1, UJ-2, UJ-5. Mechanism: architecture spine AD-3, AD-4, AD-11.

#### FR-11: Play photo scenes

The player can play the Room as Scenes with mask Hotspots, a Thumbnail strip, a persistent Inventory, and Wizard notes. Realizes UJ-1.

**Consequences (testable):**
- Every Interactable's Hotspot responds and aligns with its object on the photo.
- The Thumbnail strip reaches every photo. `[ASSUMPTION A-12: thumbnails in upload order, confirm]`
- The Inventory persists across Scene changes for the whole Session.

#### FR-12: Open locks only on correct input

The player can open a lock only with its correct input, judged by the server. Realizes UJ-1, UJ-2.

**Consequences (testable):**
- `code` is typed; `order` is a Hotspot-click sequence; `find` is a click on the target; `use_on` drags an Inventory item onto the target.
- Solving a `find` Puzzle moves its Interactable into the Inventory.
- Wrong attempts are counted per lock; a mismatched `order` sequence counts once and resets; a click alone never counts.

#### FR-13: Complete the room

The player can finish by opening the Exit puzzle and see the Completion screen. Realizes UJ-1, UJ-4.

**Consequences (testable):**
- The Completion screen shows elapsed time and Rungs used.
- The Room result is recorded into the Player profile.

#### FR-14: Resist persuasion

The player can type (or speak) anything; it becomes a Hint request that never yields anything above the current Rung. Realizes UJ-2.

**Consequences (testable):**
- The scripted attack "just tell me the answer" returns the current Rung, or the fixed no-hint line when none is open, and opens nothing.
- Player text never travels to the server as text.
- A fixture test finds no solution in any play response.

**Out of Scope:** free conversation with any wizard.

### 4.4 The Guide

**Description:** The Guide reads the Event log, not the player's words: it picks the Rung in code, shows why, and phrases it on the player's Mac. Realizes UJ-2, UJ-4, UJ-5. Mechanism: architecture spine AD-4, AD-5, AD-10.

#### FR-15: Select the rung from play

The Guide can select the Rung from the Event log. Realizes UJ-2.

**Consequences (testable):**
- The nudge fires after the nudge threshold without progress, 90 s × (1 + 0.5 × persistence) clamped to 60 to 135 s (90 s on a fresh Player profile), or after 3 Wrong attempts at one lock, whichever is first.
- Direction and near-answer each need a further stall or 3 further Wrong attempts and arrive at least 90 s after the previous Rung; the 90 s spacing never scales with persistence.
- Replaying an Event log yields the same Rung changes as live play.

#### FR-16: Show rung triggers

The player can see each Rung change with its triggering events. Realizes UJ-2, UJ-6.

**Consequences (testable):**
- Every Rung change in the Triggers panel lists its idle seconds or Wrong attempts.
- Under cut 5 the Triggers panel moves to a second window, unchanged in content.

#### FR-17: Phrase the rung locally, or show it verbatim

The Guide can phrase the Rung with Llama 3.2 3B on Ollama in Local mode; Hosted mode shows the Rung text verbatim. Realizes UJ-2, UJ-5.

**Consequences (testable):**
- Local phrasing is about 40 tokens from a prompt under 400 tokens with a fixed prefix, within 5 s; past 5 s the verbatim Rung is shown and the fallback logged.
- The phrasing input is exactly the Rung text and the Derived block; never room content or a solution.
- Hosted mode runs no Guide model and refuses to start if configured with one.
- Under cut 3 Local mode also shows Rungs verbatim and the README drops the phrasing claim; the Privacy line stays.

### 4.5 The Trickster

**Description:** The room pushes back between Puzzles, within rules the Validator enforces; both outcomes are shown. Realizes UJ-3, UJ-6. Mechanism: architecture spine AD-4, AD-12, AD-15.

#### FR-18: Propose a bounded change

The Trickster can propose one `decoy`, `merge`, `loosen`, or `shortcut` between Puzzles. Realizes UJ-3.

**Consequences (testable):**
- At most one proposal per 3-minute window, only right after a lock opens.
- At most 6 `muse-spark-1.3` calls per Session; the seventh is refused.
- The game-state summary holds no Player profile field and no solution; a `decoy` never targets the Exit puzzle.

#### FR-19: Re-validate and show cards

The player can see every Trickster edit as a Card after re-validation; the Effective room changes only on acceptance. Realizes UJ-3.

**Consequences (testable):**
- An edit is accepted only if the Room with it applied passes Validator rules 1 to 8 (plus rule 9 after the decoy pick); no Dry run.
- A rejected Card shows the fixed reason and the Effective room is unchanged; the stored Room is never mutated.
- A provider error or reached Spend cap during a window shows a skipped Card and play continues.

**Notes:** decoy storage follows the Thu Oct 22 pick (§13, Q1).

### 4.6 Player memory

**Description:** The game remembers the player without a server holding their Player profile. Realizes UJ-4. Mechanism: architecture spine AD-8.

#### FR-20: Keep the player profile in the browser

The player can keep their Player profile in their own browser. Realizes UJ-4.

**Consequences (testable):**
- Room results and the Derived block are written only to IndexedDB under the `PROFILE` name (`dev`, `playtest`, `demo`); under cut 2 to a local JSON file on the player's machine.
- A Session start carries the Derived block and nothing else from the Player profile.

#### FR-21: Greet the returning player and adapt thresholds

The returning player can receive a Greeting citing how they played the previous Room, with the nudge threshold scaled to their persistence. Realizes UJ-4.

**Consequences (testable):**
- The Greeting uses the Derived block only and names no object and no solution. `[ASSUMPTION A-13: shown before the first Scene, confirm]`
- With persistence p the nudge threshold is 90 s × (1 + 0.5 × p), within 60 to 135 s.
- At least 80% of room-2 Clues reference Interactables absent from room 1.
- A real room-1 record exists on `PROFILE=demo` before room 2 is recorded.

#### FR-22: Exclude demo results

The system can exclude Room results recorded under a Demo timescale when recomputing the Derived block. Realizes UJ-4, UJ-6.

**Consequences (testable):**
- A Room result recorded with Demo timescale above 1 is flagged as demo.
- Recomputing the Derived block ignores every flagged result.

### 4.7 Wizard art

**Description:** The Council gets Wizard portraits, generated once so play never waits on or pays for images; in Tier 1.5 each Clue gets a Clue card. Realizes UJ-1, UJ-6. Mechanism: architecture spine AD-6; Clue cards are the spine's deferred post-scene stage.

#### FR-23: Show wizard portraits

The player can see four Wizard portraits in play. Realizes UJ-1, UJ-6.

**Consequences (testable):**
- Four portraits are generated once with `muse-image-1.0` (Thu Oct 29), committed, and shown in play and in the Main demo.
- Play makes zero image-generation calls; missing portraits fall back to placeholder art.

#### FR-37: Show a clue card with each clue (Tier 1.5)

The player can see a Clue card beside each Puzzle's Clue, one image per Puzzle generated from the Clue text only. Realizes UJ-1.

**Consequences (testable):**
- One `muse-image-1.0` image per Puzzle (4 to 6 per Room), generated once after the Room passes validation, cached, never generated in play.
- The prompt is the Clue text only: no solution, Rung, photo, or Player profile field (sentinel-solution test).
- Every call is cached and priced in the Ledger; portraits plus up to 12 Clue cards cost about $0.16.
- A failed Clue card leaves the Clue without an image and never fails the Build or delays T1. `[ASSUMPTION A-14: Clue cards never gate T1 or the Build, confirm]`

**Out of Scope:** Clue cards in Tier 1; images derived from room photos.

### 4.8 Demo mode and disclosure

**Description:** Video-friendly timings and replays, with the Validator, capture timer, and Event log kept real and every shortcut disclosed. Realizes UJ-6. Mechanism: architecture spine AD-10, AD-15.

#### FR-24: Compress demo timings

Luis can set a Demo timescale n that divides the nudge threshold, Rung spacing, and Trickster window by n. Realizes UJ-6.

**Consequences (testable):**
- At `DEMO_TIMESCALE=6`, three Rungs arrive within 40 s on Wrong attempts (30 s nominal; 45 s on idle alone).
- The capture timer and Event log timestamps are unchanged at any timescale.

#### FR-25: Replay Trickster proposals with a live validator

Luis can switch to the Scripted Trickster, which replays recorded proposals while the Validator runs live. Realizes UJ-3, UJ-6.

**Consequences (testable):**
- `DEMO_TRICKSTER=scripted` replays two recorded proposals; the live Validator accepts one and rejects one.
- Cut 1 uses the same source with pre-authored proposals and no live Trickster calls; the Validator still runs on every Card.

#### FR-26: Disclose demo settings

The player, a judge, and the README can see which demo settings are active. Realizes UJ-5, UJ-6.

**Consequences (testable):**
- A status endpoint reports mode, Guide, Trickster source (live, scripted, cut 1), Demo timescale, Cache, Player profile name, Disclosure text, and retention text (architecture spine AD-15).
- The UI shows a Disclosure whenever the Demo timescale exceeds 1, the Trickster is scripted, or Hosted mode is active.
- The Main demo's last 10 s and the README carry the Disclosures.

### 4.9 Spend and cache guard

**Description:** No hosted call goes unpriced or uncounted, identical calls come from the Cache, and every Room records its provenance. Realizes UJ-6. Mechanism: architecture spine AD-6, AD-9, AD-16.

#### FR-27: Cache identical calls

The system can serve an identical hosted call from the Cache without billing. Realizes UJ-6.

**Consequences (testable):**
- With `CACHE=on`, a repeat of the same model, schema, full prompt, reasoning effort, image hashes, and attempt number is served from the Cache and adds nothing to the Ledger.
- With `CACHE=off` every call reaches the provider and is still priced.
- A Regeneration is never served its own failed answer.

#### FR-28: Price, record, and cap spend

The system can price every uncached hosted call, record it in the Ledger, and refuse a call that would pass the Spend cap. Realizes UJ-6.

**Consequences (testable):**
- The Spend cap is $80 through Wed Nov 4 and $25 from Thu Nov 5.
- A refused call is surfaced to the player or Luis.
- The running total survives a restart.

#### FR-29: Export the ledger daily

Luis can rely on a daily Ledger export as the durable spend record. Realizes UJ-6.

**Consequences (testable):**
- Local mode writes a dated export at startup and after every Build, committed with each build day's work from Mon Oct 26.
- Hosted mode snapshots the Ledger daily at 06:00 ET.
- The Thu Nov 5 counter reset is refused unless that day's export exists.

#### FR-30: Record provenance

The system can attach provenance to every Room. Realizes UJ-5, UJ-6.

**Consequences (testable):**
- Every stored Room lists model ids, prompt hashes, stage timings, Regeneration count, and spend per stage.
- The submission's spend log derives from the Ledger, never hand-kept.

### 4.10 Hosted judge URL (Tier 1.5)

**Description:** Judges open a URL, play Demo rooms, and may build a Judge room behind the Access code. Hosted mode runs the same product on Modal CPU; Rungs appear verbatim because no Guide model runs off the player's Mac. Built after the Backup video, judge-ready Thu Nov 5 to Sun Nov 8. Realizes UJ-5. Mechanism: architecture spine AD-7, AD-9.

#### FR-31: Play demo rooms on the hosted URL

A judge can open the hosted URL and play Demo rooms with the same behavior as Local mode. Realizes UJ-5.

**Consequences (testable):**
- The hosted landing lists the Demo rooms; each plays to the Completion screen.
- Rungs are verbatim and the Disclosure states Hosted mode.

#### FR-32: Build a judge room with the access code

A judge can build a Judge room behind the Access code. Realizes UJ-5.

**Consequences (testable):**
- A Build without the Access code is refused; the 21st Build is refused with a quota message.
- A Build outlasting the host's 150 s web timeout completes and reaches the judge.

#### FR-33: Delete judge data on schedule

The system can delete Judge rooms and hosted Session logs on schedule. Realizes UJ-5.

**Consequences (testable):**
- Judge rooms, originals, Sessions, and Cache entries are deleted together Tue Nov 10; Demo rooms persist.
- Hosted Session logs are deleted 24 h after their last event.

### 4.11 Walkable 3D room (Tier 2, gated, default no-go)

**Description:** The Room becomes a walkable 3D scene of reconstructed objects, and Puzzles trigger by looking. Attempted only if the Backup video exists Sat Oct 31 night; gated Mon Nov 2; expected not attempted. Realizes UJ-7. Mechanism: architecture spine AD-11, Deferred.

#### FR-34: Walk the room in 3D

The player can walk a 3D version of the Room and trigger Puzzles by raycast. Realizes UJ-7.

**Consequences (testable):**
- Up to 20 objects are reconstructed by fal.ai SAM 3D Objects ($0.02 a call, cloud only) from original-resolution photos, in the same scene graph as Tier 1.
- Gate, Mon Nov 2: 7 of 10 Interactables recognizable in position, 30 fps or better on the M1, raycast-triggered Puzzles; any miss ships Tier 1.
- fal.ai spend stays within $6 cash.

### 4.12 Voice help (unscheduled)

**Description:** The player asks the wizards for help aloud; speech becomes a Hint request like typed text. Ships only if everything else is done Mon Nov 2. Realizes UJ-2.

#### FR-35: Ask for help by voice

The player can ask for help by voice and get the same Rung a click would give. Realizes UJ-2.

**Consequences (testable):**
- Speech is transcribed by `muse-voice-transcribe-1.0`, with browser speech recognition as fallback.
- A spoken "just tell me the answer" yields nothing above the current Rung.

### 4.13 Privacy guarantees

**Description:** Raw room photos never enter the public repo; only outputs ship (screenshots, Clue cards, the videos). The Player profile stays on the player's machine. Realizes UJ-1, UJ-4, UJ-5. Mechanism: architecture spine AD-8.

#### FR-36: Keep photos out of the repo and profiles off the server

The player and Luis can rely on raw room photos never entering the repo and the hosted server never persisting Player profile data. Realizes UJ-1, UJ-4, UJ-5.

**Consequences (testable):**
- Photo input folders, HEIC files, and the Cache are git-ignored, asserted by an offline test.
- The hosted server stores no Derived block or Player profile beyond a Session's transient Event log.
- Only the Meta Model API standard tier is used, never the contributor tier.

## 5. Cross-Cutting NFRs

- **NFR-1 Capture performance:** the Capture target; stage budgets Architect 15 s, segmentation 10 s, Riddler 45 s, Dry run 30 s, Scene 10 s; a Regeneration about 75 s; Capture proof takes kept only under 200 s.
- **NFR-2 Hint latency:** about 40 tokens in 5 s or less from a prompt under 400 tokens with a fixed prefix.
- **NFR-3 Hardware:** everything local runs on one 16 GB M1 MacBook Pro without CUDA; Guide model near 3 GB resident; demo-recording memory about 10.6 GB; no local SAM 3.1, SAM 3D Objects, or 30B models.
- **NFR-4 Privacy:** the Guide model runs only on the player's Mac; only the Derived block reaches the Guide model and the Greeting; raw room photos are never committed; the Retention summary is shown; standard tier only.
- **NFR-5 Integrity:** solutions never enter a model prompt or play response; Validator reasons never quote a token or answer; only the server's session logic opens locks.
- **NFR-6 Cost:** Spend cap $80 through Wed Nov 4, $25 from Thu Nov 5; fal.ai at most $6 cash; development runs on the Mock provider with `CACHE=on`.
- **NFR-7 Reliability:** Builds survive the 150 s web timeout and resume at the last completed stage after a restart; provider calls retry once, on rate-limit and server errors only; at most 2 Regenerations.
- **NFR-8 Testability:** every story's tests pass offline on the Mock provider; provider tests use recorded fixtures; dependency-boundary, type-staleness, and ignore-file tests run offline.
- **NFR-9 Rate limits:** within Meta Model API limits (`muse-spark-1.3` 3,000 RPM and 4,000,000 TPM; `sam-3.1` 3,000 RPM; `muse-image-1.0` 150 RPM); segmentation concurrency at most 12.
- **NFR-10 Platform:** Chrome on the Mac; Tier 1 Scenes as textured planes in the scene graph Tier 2 reuses; the Tier 2 gate needs 30 fps or better on the M1.
- **NFR-11 Schedule:** the gates in §11.1; Fri Oct 30 no build; Cuts made nightly in order.
- **NFR-12 Demo honesty:** the 6x Demo timescale, the Scripted Trickster replay, and earlier builds of a Room are disclosed in the video and README; the README states which Cuts shipped.
- **NFR-13 Submission and hygiene:** public MIT repo listing third-party and model licenses; planning-tool folders removed from the index before the repo goes public (Wed Nov 4 morning at the latest); `PRODUCT_BRIEF.md` stays removed; pre-existing code disclosed with the `pre-hackathon-baseline` tag and diffstat; the scaffold not expanded before Mon Oct 26.

## 6. Constraints and Guardrails

### 6.1 Privacy
- The Privacy line appears verbatim on the Capture screen and in the README and holds under every Cut, including cut 3.
- Raw room photos never enter the public repo, consent or not; only outputs ship, with household consent for what appears in them.
- Photos and puzzle text go only to the Meta Model API (standard tier) and, in Tier 2, fal.ai, as the Retention summary states before upload.

### 6.2 Integrity
- Solutions never reach a model prompt or a browser: the Dry run, Trickster, Guide, Greeting, and Clue card prompts see none (architecture spine AD-3).
- The persuasion attack fails by construction: player text is a Hint request whose ceiling is the current Rung; the failure is shown on video.
- Every Room and Trickster edit passes the Validator; demo mode swaps the Trickster's source, never the check.

### 6.3 Cost
- Caps per NFR-6; expected spend about $35 under $79 of daily ceilings; a clean Build about $0.10 (under $0.25 with two Regenerations), a Session about $0.21.
- The daily Ledger export, committed each build day, is the durable spend record.

### 6.4 Hardware
- One 16 GB M1 MacBook Pro, no CUDA, no GPU anywhere. On the Mac: Chrome, the backend, Llama 3.2 3B on Ollama. In the cloud: `muse-spark-1.3`, `sam-3.1`, `muse-image-1.0` (and `muse-voice-transcribe-1.0` if voice ships) on the Meta Model API; fal.ai SAM 3D Objects in Tier 2 only; Modal CPU for Hosted mode.

### 6.5 Platform
- Players use Chrome on a Mac with JPEG photos from a phone (iPhone set to Most Compatible).
- Judges use the hosted URL. `[ASSUMPTION A-15: judges use desktop Chrome, confirm]` Finals Mon Nov 9 run Local mode screen-shared from the M1, falling back to the hosted URL, then cached Rooms, then the video.

## 7. Aesthetic and Tone

`[ASSUMPTION A-16: inferred from the brief's council framing; no visual references supplied, confirm]`

- **Scenes:** Myst-style photo scenes: the player's real photos, full-bleed, traversed by thumbnails, Hotspots revealed on hover rather than outlined at rest. Lead with what the room knows, never with photorealism.
- **The four wizards:** in-world, terse, never condescending; one or two sentences each. The Architect observes, the Riddler teases, the Guide encourages, the Trickster taunts. Portraits share one painted style.
- **Rung copy:** scaffolds, never answers. A nudge says where to look, a direction what to notice, a near-answer how to use it; none says "the answer is".
- **Greeting:** warm and specific about play style, never about objects, never surveillance-flavored.
- **Disclosure copy:** plain, out of character, literal ("Timings shown at 6x speed. Trickster proposals replayed from a recording; the Validator ran live.").
- **Errors:** plain and actionable ("Keyframe needs 6 to 10 JPEG photos").

## 8. Information Architecture

`[ASSUMPTION A-17: layout and grouping inferred, confirm]`

- **Capture screen:** photo picker, Upload, timer, current Build stage, Retention summary with the Privacy line; messages for rejected formats, `needs_more_photos`, `needs_recapture`.
- **Room-2 Greeting:** before the first Scene of a returning player's Room.
- **Play screen:** Scene with Hotspots; Thumbnail strip; Inventory (drag source for `use_on`); Wizard notes with portraits, Clues, Lore, and Clue cards in Tier 1.5; lock inputs per Lock type; Hint area with a hint-request field and the Triggers panel (a second window under cut 5); Trickster Cards.
- **Completion screen:** time and Rungs used; entry to the next Room.
- **Demo disclosure overlay:** active Disclosures whenever a demo setting or Hosted mode is on.
- **Hosted landing:** Demo rooms, Access-code entry for a Judge room Build, mode Disclosure.

## 9. Non-Goals (Explicit)

- Live phone capture, mobile or native apps, Quest or MR.
- Multiplayer, accounts, cloud sync of the Player profile.
- Any hosted or cloud-run Guide model; Muse Glimmer; Muse Wonder; SAM 3D Body.
- Local SAM inference; Modal GPU self-hosting; the contributor tier.
- Puzzle content not derived from the player's photos; free conversation with the wizards.
- Committing raw room photos; a single uncut long video.

## 10. MVP Scope

### 10.1 In Scope
- **Tier 1, the floor, protected above everything:** FR-1 to FR-30 and FR-36 (portraits only under FR-23), with whatever Cuts are in force, plus the Backup video.
- **Tier 1.5, only once the Backup video exists:** Cuts restored last-first, then Clue cards (FR-37), then Hosted mode for judges (FR-31 to FR-33, Nov 5 to 9), then voice (FR-35).

### 10.2 Out of Scope for MVP
- **Tier 2 (FR-34):** default no-go, attempted Sun Nov 1 only if the Backup video exists Sat Oct 31 night. `[NOTE FOR PM]` The walkable room is the most emotionally load-bearing deferral, the "I'm inside my own room" moment. It returns only through the Mon Nov 2 gate and never at the expense of Tier 1 or the Main demo (SM-C3).
- **Tier 3:** never gates a deliverable.
- **Voice (FR-35):** unscheduled; only if everything else is done Mon Nov 2.
- Everything in §9.

## 11. Delivery Gates and Cut Order

### 11.1 Gates

| When (2026, ET) | Gate | Rule |
|---|---|---|
| Sat Oct 31, night | Early gate | A Backup video existing by now is the only thing that sends Sun Nov 1 to Tier 2 |
| Sun Nov 1, 2:00 PM | Backup video | Recorded from whatever runs, Cuts included; never moved |
| Mon Nov 2 | Tier 2 gate (only if attempted) | 7 of 10 Interactables in position, 30 fps or better, raycast Puzzles; any miss ships Tier 1 |
| Tue Nov 3 | Video only | Capture proof and three Main demo takes; no feature work |
| Wed Nov 4, before 9:00 AM | Submit | Deadline 9:00 PM; 6 to 9 PM is slack for a failed upload |

### 11.2 Cut order

Cuts are made nightly, in this order, and never carried to a later day. Capture (FR-1 to FR-6), play (FR-11 to FR-14, with cut 6 narrowing Lock types), and the non-builder playtest survive every Cut; the README states which Cuts shipped.

| Cut | Ships instead | FR changed |
|---|---|---|
| 1 | Pre-authored Trickster edits plus a scripted reject; Validator still live | FR-18, FR-25 |
| 2 | Player profile as a local JSON file | FR-20 |
| 3 | Rung text verbatim, no Ollama phrasing; Privacy line stays | FR-17 |
| 4 | Validator only, no Dry run | FR-9 |
| 5 | Triggers panel in a separate window | FR-16 |
| 6 | `code` and `find` locks only | FR-7, FR-12 |
| 7 | One Regeneration, not two | FR-10 |
| 8 | Room 2 moves to Sun Nov 1 afternoon | FR-21 |

## 12. Success Metrics

**Primary**
- **SM-1 Capture proof:** an unedited Capture proof shows a never-built Photo set going from T0 to T1 within the Capture target (120 s, or measured p50 plus 25% if re-based). Validates FR-1 to FR-5.
- **SM-2 Non-builder completion:** a non-builder finishes room 1 on a fresh Player profile without builder help (Guide Rungs allowed) by Mon Nov 2. Validates FR-11 to FR-13, FR-15.
- **SM-3 Zero wins by persuasion:** across the scripted attack suite and the Main demo, no player text opens a lock or yields anything above the current Rung. Validates FR-14.

**Secondary**
- **SM-4 Zero solution tokens:** none in any Rung (beyond the rule 5 allowance), prompt, or play response across the test suite and every Demo room. Validates FR-8, FR-36.
- **SM-5 Fresh objects in room 2:** at least 80% of room-2 Clues reference Interactables absent from room 1. Validates FR-7, FR-21.
- **SM-6 Spend discipline:** total spend within the Spend cap, with a committed Ledger export every build day from Mon Oct 26. Validates FR-28, FR-29.

**Counter-metrics (do not optimize)**
- **SM-C1:** do not shorten capture time by weakening the Validator or the Dry run. Counterbalances SM-1.
- **SM-C2:** do not raise completion by giving Rungs sooner than FR-15 allows. Counterbalances SM-2.
- **SM-C3:** do not trade Tier 1 reliability for Tier 2 visuals. Counterbalances the Main demo.

## 13. Open Questions

1. **Decoy storage:** option A (`Room.decoys[]`, recommended), B (Evidence list with a decoy flag), or C (Cards from the Event log only); see `schema-v1.md`. Needed Thu Oct 22.
2. **Fireworks Trickster fallback model id.** Needed Mon Oct 26.
3. **Retention wording on the status endpoint**, from the pre-kickoff retention verification. Needed Mon Oct 26.
4. **Hosted full-Room download route** (access-coded). Needed Mon Oct 26.
5. **The two rooms**, with household consent for video and screenshots. Needed before Sun Oct 25.
6. **Payment methods** on dev.meta.ai, fal.ai, and Modal. Needed before Mon Oct 26.
7. **Playtester** for room 1 on a fresh Player profile, at the laptop or by screen-share, Sun Nov 1 or Mon Nov 2. Needed before Sun Nov 1.
8. **Luis's availability** in working hours Mon Nov 9 for the live finals. Needed before finals preparation starts Thu Nov 5. `[ASSUMPTION A-18: date inferred from the day plan, confirm]`

Tracked in the spec and not blocking this PRD: Baseten credit coverage (Tue Oct 27 test), fal.ai pose metadata (pre-Oct 26 spike), and whether about 32 h of builder time holds (if not, Cuts apply earlier).

## 14. Assumptions Index

- **A-1 to A-7** §2.3 UJ-1 to UJ-7 — each journey drafted from the brief's demo narrative; confirm each.
- **A-8** §2.1 — Jobs To Be Done inferred from the brief.
- **A-9** §2.2 — Non-Users inferred from the spec's non-goals.
- **A-10** §3 Wizard notes — contents inferred.
- **A-11** §4.1 FR-5 — Build stage labels in plain words.
- **A-12** §4.3 FR-11 — Thumbnail strip in upload order.
- **A-13** §4.6 FR-21 — Greeting before the first Scene.
- **A-14** §4.7 FR-37 — Clue cards never gate T1 or the Build.
- **A-15** §6.5 — judges use desktop Chrome.
- **A-16** §7 — Aesthetic and Tone inferred; no visual references supplied.
- **A-17** §8 — surface layout and grouping inferred.
- **A-18** §13 Q8 — availability answer needed before Thu Nov 5.
