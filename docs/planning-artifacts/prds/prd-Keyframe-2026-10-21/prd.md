---
title: Keyframe
status: final
created: 2026-10-21
updated: 2026-10-22
---

# PRD: Keyframe

Luis Ticas · 2026-10-21 · Indie track, Meta Global AI Developer Hackathon (Cerebral Valley)

**At a glance**
- **Status:** final.
- **Tier 1 floor, protected above everything:** FR-1 to FR-30, FR-36, and FR-38 (FR-38 is cut 0, the first Cut taken), plus the Backup video (§10.1).
- **Decisions due Mon Oct 26:** §13 Q2 to Q4 and Q14, the Official Rules check at kickoff (Q1, decoy storage, is the Thu Oct 22 schema review pick; Q9, Q10, Q12 and Q13 were resolved Oct 21).

## 0. Document Purpose

This PRD is for Luis Ticas as builder and reviewer, and for the two runs that consume it next: `bmad-ux` (the UX contract) and `bmad-create-epics-and-stories` (the epic re-extraction). It builds on three approved inputs and does not duplicate them: the product brief (`docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/`, with its addendum and Schema v1), the spec (`docs/specs/spec-keyframe/SPEC.md` and companions), and the architecture spine (`docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md`). The PRD restates requirements at the product level, meaning what a player, a judge, or Luis can do and what must be observably true; mechanism stays in the spine and is cited as "architecture spine AD-n".

FR-1 to FR-36 carry the meaning and numbering of FR1 to FR36 in `docs/planning-artifacts/epics.md`; FR-37 (Clue cards) and FR-38 (Build view) are new. NFR-1 to NFR-13 mirror NFR1 to NFR13 there; NFR-14 (accessibility floor) is new. Numbers are stable ids, so FR-37 sits under §4.7 and FR-38 under §4.2. Vocabulary is anchored in §3 and used verbatim. Inferences are tagged inline as `[ASSUMPTION A-n]` and indexed in §14. Delivery steps (dates, recordings, commits) live in §11, not in FR consequences, so they never become agent acceptance criteria.

## 1. Vision

Keyframe turns the room you are sitting in into an escape room. A player photographs a living room or a study, uploads 6 to 10 JPEG photos in Chrome, and about two minutes later plays a puzzle chain built from their own things: the code is the year printed on their mug; the last lock opens on their bookshelf. No two players get the same room, because no two players own the same objects.

A council of four wizard roles runs the room. The Architect looks at the photos and names the objects; the Riddler writes the puzzle chain and must prove it solvable before anyone plays it; the Guide watches how the player plays and offers help one Rung at a time, never the answer; the Trickster changes the room between puzzles, but only when the Validator agrees the change is fair. The solution never reaches a model prompt or the player's screen, so the player cannot talk the room open. In Local mode the Guide's phrasing model runs on the Mac, and the player profile stays on your machine.

Keyframe remembers the player: the second room greets them from how they played the first and adapts how soon help arrives. For the hackathon, Keyframe shows Meta's model stack taking a solo builder from household photos to a verified, adaptive game in one pipeline, with segmentation, structured agent output, and a small local model each doing what it does best. It also shows its work: the Build view (FR-38) lays out which Meta model did what.

## 1a. Why Now

In 2026 the Meta Model API put object segmentation from a noun phrase (`sam-3.1`), schema-constrained multimodal reasoning (`muse-spark-1.3`), and image generation (`muse-image-1.0`) behind one key, while Llama 3.2 3B runs locally on a 16 GB laptop through Ollama. Turning a casual home photo into typed, clickable objects with a verified puzzle graph over them is now a solo build. The forcing deadline is the hackathon: build Mon Oct 26 to Wed Nov 4 2026, target submission before 9:00 AM ET Wed Nov 4 (hard deadline 9:00 PM ET), judged on Impact 30%, Use of Meta AI Tooling 25%, Technical Depth 20%, Demo 25%.

## 1b. Problem

Escape rooms cost money and travel, are scripted once for everyone, and none is about the player's own things. "AI escape rooms" make one image and a riddle chain; a 2025 Room Escape Artist review found hollow puzzles and a win by typing "blast off". Game masters scaffold help; AI hint-givers dump the answer or never help; none remembers the player.

## 2. Target User

### 2.1 Jobs To Be Done

`[ASSUMPTION A-8: jobs inferred from the brief's "Who This Serves" and demo narrative, confirm]`

- **Functional (player):** turn a familiar room into a 15 to 25 minute puzzle session with nothing to buy, travel to, or write.
- **Emotional (player):** recognize their own objects in a clue; solve with help that scaffolds instead of giving the answer away or refusing.
- **Social (player):** come back for a second room and feel the game remembers how they play.
- **Judge:** verify in minutes that the pipeline is real (own-room build, visible triggers, no win by persuasion) and see which Meta model did what.
- **Finals audience (Mon Nov 9):** understand the loop in one screen-shared run from the M1.
- **Builder (Luis Ticas):** prove capture, integrity, adaptive help, and memory on camera, inside the Spend cap, without trading Tier 1 reliability for scope.

### 2.2 Non-Users (v1)

`[ASSUMPTION A-9: boundary inferred from the spec's non-goals, confirm]`

- Players without a laptop or desktop browser (no native mobile client, no live phone capture).
- Groups wanting multiplayer; players wanting accounts or cloud sync; Quest or mixed-reality users.
- Operators wanting authored commercial content: Keyframe only writes puzzles from the player's photos.
- Players wanting an open chat game master: player text only requests the current Rung.

### 2.3 Key User Journeys

Ana and Priya are fictional personas.

**UJ-1. Ana turns their living room into a game.** `[ASSUMPTION A-1: drafted from the brief's demo narrative, confirm]`
- **Persona + context:** Ana has never played an escape room and wants a 20-minute game on a weeknight.
- **Entry state:** Ana's iPhone is set to Most Compatible; 8 JPEG photos of the living room are on Ana's Mac; Chrome shows the Capture screen in Local mode, which states "6 to 10 JPEG photos" before anything is chosen.
- **Path:** (1) Ana selects the photos and clicks Upload; the Timer starts at T0. (2) The Capture screen shows each Build stage and the Retention summary with the Privacy line. (3) Masks appear over Ana's mug, lamp, and books in the mask preview. (4) The first Scene becomes interactive at T1, inside the Capture target. (5) Ana hovers the mug, opens the first Puzzle's Wizard-notes entry, types a code, sees "Not this" once, then opens the lock; the next Puzzle appears in the notes.
- **Climax:** the first Clue points at Ana's mug and what is printed on it, without quoting the year.
- **Resolution:** Ana plays 4 to 6 Puzzles and reaches the Completion screen.
- **Edge cases:** a HEIC photo in the set rejects the whole set at the picker with "Keyframe needs 6 to 10 JPEG photos." and nothing is sent; fewer than 5 objects stops the Build before any Puzzle is written and the Capture screen asks for more photos; after the last allowed Regeneration fails, the Build ends `needs_recapture` with reshoot guidance.
- **Capability → FR:** accept only JPEG → FR-1; list and segment objects → FR-2, FR-3; ask for more photos → FR-4; Timer and stages → FR-5; Retention summary → FR-6; author and verify → FR-7 to FR-10; Build view → FR-38; play → FR-11 to FR-13; Clue cards → FR-37; photos stay out of the repo → FR-36.

**UJ-2. Ana gets stuck and the Guide helps without telling.** `[ASSUMPTION A-2: drafted from the brief's demo narrative, confirm]`
- **Persona + context:** Ana, mid-Room, cannot find the second code.
- **Entry state:** a Session on a fresh Player profile; nudge threshold 90 s.
- **Path:** (1) After 90 s of Idle on the Active puzzle, the Guide posts a nudge. (2) Ana enters three wrong codes; the direction Rung arrives no sooner than 90 s after the nudge. (3) The Triggers panel shows the Idle seconds and Wrong attempts behind each Rung. (4) Ana types "just tell me the answer".
- **Climax:** the reply is the current Rung only; nothing above it appears and the lock stays shut.
- **Resolution:** Ana rereads the direction Rung in the Puzzle's notes entry, looks at the bookshelf, and solves the lock.
- **Edge cases:** local phrasing takes longer than 5 s; the Rung text appears verbatim and play continues. Ana asks before any Rung is open; the Guide answers with the in-world no-hint line, which encourages and points back to the Scene.
- **Capability → FR:** Hint request → FR-14; Rung selection → FR-15; triggers → FR-16; phrasing → FR-17.

**UJ-3. The Trickster changes the room between puzzles.** `[ASSUMPTION A-3: drafted from the brief's demo narrative, confirm]`
- **Persona + context:** Ana has just opened a lock.
- **Entry state:** at least 3 minutes since the last Trickster window.
- **Path:** (1) The Trickster proposes a Decoy; the Validator re-checks the Room with it applied. (2) An accepted Card appears and a new Evidence card appears in the Wizard notes, indistinguishable from the real ones. (3) After the next lock opens, 3 or more minutes later, a second proposal fails validation. (4) A rejected Card shows a plain reason from the Validator's fixed message.
- **Climax:** Ana sees the room fight back, and sees the rules bind the Trickster too.
- **Resolution:** the Effective room changed only for the accepted Card.
- **Edge case:** a provider error during a window shows a skipped Card; play continues.
- **Capability → FR:** bounded proposals → FR-18; re-validation and Cards → FR-19.

**UJ-4. Ana comes back for a second room.** `[ASSUMPTION A-4: drafted from the brief's demo narrative, confirm]`
- **Persona + context:** Ana finished room 1 by persisting past nudges and now photographs the study.
- **Entry state:** same browser and Player profile; one Room result recorded.
- **Path:** (1) Ana uploads the study photos; the Build runs as in UJ-1. (2) The Greeting cites how Ana played room 1 ("you held out long past the first nudge") and names no object or solution. (3) Ana's positive persistence raises the nudge threshold toward 135 s.
- **Climax:** Ana feels recognized by the game, not tracked by a service.
- **Resolution:** room 2's Clues use objects from the study; the Player profile stays in Ana's browser.
- **Edge case:** Ana opens room 2 in a different browser; there is no Player profile, so the first-room welcome shows and the nudge threshold is 90 s.
- **Capability → FR:** browser Player profile → FR-20; Greeting and thresholds → FR-21; demo results excluded → FR-22; profile never on the server → FR-36.

**UJ-5. Priya, a judge, plays the hosted demo and builds their own room.** `[ASSUMPTION A-5: drafted from the brief's demo narrative, confirm]`
- **Persona + context:** Priya, a hackathon judge, has ten minutes and wants proof the pipeline is real.
- **Entry state:** the hosted URL in a desktop browser; the Access code from the submission.
- **Path:** (1) Priya plays a Demo room from the Hosted landing. (2) Rungs appear verbatim; the Disclosure says no hint model runs in Hosted mode. (3) Priya enters the Access code, which is checked before photo selection, and uploads 6 JPEG photos of their office. (4) After one Regeneration, the Build outlasts the host's 150 s web timeout.
- **Climax:** the Build still completes and Priya's Clues name Priya's own objects.
- **Resolution:** Priya plays the Judge room; it is deleted Tue Nov 10.
- **Edge cases:** a wrong Access code is refused inline and no upload starts; a Build waiting behind another shows the queued state; the 21st Build is refused with a quota message.
- **Capability → FR:** Demo rooms → FR-31; access-coded Builds → FR-32; deletion → FR-33; verbatim Rungs → FR-17; nothing persisted about the judge's profile → FR-36.

**UJ-6. Luis records the Capture proof and the Main demo.** `[ASSUMPTION A-6: drafted from the brief's demo narrative, confirm]`
- **Persona + context:** Luis Ticas on Tue Nov 3, with a fresh room-2 Photo set shot that day and never sent to the pipeline.
- **Entry state:** Local mode on the M1, `CACHE=off`, IDE closed; fresh Player profiles for the Capture proof; `PROFILE=demo` holds only the real Mon Nov 2 room-1 run, played at Demo timescale 1.
- **Path:** (1) Luis clears the Cache on camera and clicks Upload; the Timer runs on screen from T0. (2) The first Hotspot responds at T1; the take is kept only if it runs under 200 s. (3) Luis records the Main demo beats in §11.3 from the Build view and Play screen. (4) The Disclosure banner states the 6× timescale, the scripted replay, and earlier builds of the Room.
- **Climax:** a 2:00 Main demo (cap 2:30) and an unedited Capture proof, honest about every shortcut.
- **Resolution:** both videos are uploaded unlisted for the Wed Nov 4 submission.
- **Edge case:** a take past 200 s or with a second visible retry is discarded and re-shot.
- **Capability → FR:** Demo timescale → FR-24; Scripted Trickster → FR-25; Disclosure → FR-26; Cache bypass → FR-27; triggers on video → FR-16; demo results excluded → FR-22; spend → FR-28, FR-29; provenance and model table → FR-30, FR-38.

**UJ-7. (Tier 2, gated; not in the UX contract until the Mon Nov 2 gate) Ana walks the room in 3D and opens a lock by looking.** `[ASSUMPTION A-7: drafted from the brief's demo narrative, confirm]`
- **Persona + context:** Ana, replaying room 1, wants to move through it rather than flip photos.
- **Entry state:** the Tier 2 gate passed Mon Nov 2.
- **Path:** (1) The Room loads as a walkable 3D scene with reconstructed objects where they stand. (2) Ana walks to the bookshelf and looks at it. (3) The look triggers the `find` lock.
- **Climax:** a lock opens because Ana looked at a real object in a reconstructed room.
- **Resolution:** play continues with the same Puzzles and Guide as Tier 1.
- **Edge case:** WebGL fails to start; the Tier 1 Scenes load instead.
- **Note:** controls, look rule and loading state stay out of the UX contract until the Mon Nov 2 gate passes.
- **Capability → FR:** walkable 3D Room → FR-34.

## 3. Glossary

**Room and capture**
- **Room** — One playable escape room from one Photo set: 5 to 12 Interactables, 4 to 6 Puzzles, provenance. Immutable once stored.
- **room 1**, **room 2** — The two video Rooms Luis records, from two different physical rooms (§13 Q5).
- **Effective room** — The Room as one Session sees it, with that Session's accepted Trickster edits applied; never stored back.
- **Demo room** — A Room seeded on the hosted server for judges; persists.
- **Judge room** — A Room built in Hosted mode with the Access code; deleted Tue Nov 10.
- **Photo set** — The 6 to 10 JPEG photos of one physical room for one Build; downscaled to a 1280 px long edge, originals kept for Tier 2.
- **Input requirement** — The verbatim string "6 to 10 JPEG photos", shown on the Capture screen and in the README before any upload.
- **Interactable** — A typed object from the Photo set: label, photo, box, Hotspot, instance count, attributes the Architect read.
- **Hotspot** — The clickable polygon of one Interactable on its photo, from the `sam-3.1` mask or, failing that, the box rectangle; in the pixel space of the stored 1280 px photo.
- **Scene** — One photo rendered with its Hotspots.
- **Timer** — The on-screen T0-to-T1 clock, stamped by the build clock; never scaled by the Demo timescale.
- **T0**, **T1** — The Upload click; the first Hotspot on the Play screen responding to the pointer.
- **Capture target** — T1 − T0 ≤ 120 s on the M1 with `CACHE=off` and a never-built Photo set, or measured p50 plus 25% if re-based after Oct 27 to 28.

**Council**
- **Council** — The four wizard roles: Architect, Riddler, Guide, Trickster.
- **Architect** — The `muse-spark-1.3` vision call listing objects with clearest photo, box, and readable attributes.
- **Riddler** — The `muse-spark-1.3` call writing the Puzzles from the Interactables.
- **Guide** — Rung selection in code over the Event log, phrased by Llama 3.2 3B on Ollama on the Mac, or verbatim in Hosted mode.
- **Trickster** — The `muse-spark-1.3` role proposing one change between Puzzles from Decoy, Merge, Loosen, Shortcut.
- **Wizard portrait** — One of four Council images, generated once with `muse-image-1.0` and committed.

**Play, puzzles and locks**
- **Session** — One play-through of one Room, 15 to 25 minutes.
- **Event log** — The append-only, server-timestamped record of a Session; Session state replays from it.
- **Puzzle** — One lock in the chain: Lock type, prerequisites, solution, Evidence, Clue, Lore, three Rungs.
- **Active puzzle** — The most recently targeted available unsolved Puzzle (a target is set by a lock input, or by a Hint request naming an available unsolved Puzzle), else the earliest available unsolved Puzzle in the Room's order; never set by a click; null only once the Exit puzzle has opened; Idle-triggered Rungs, Wrong-attempt Rungs and Hint requests apply to it (architecture spine AD-4).
- **Lock type** — `code` (typed, 3 to 6 characters), `order` (3 to 5 Hotspot clicks in sequence, counted only while armed by "Start the sequence"), `use_on` (Inventory item dragged onto a target), `find` (click the target).
- **Exit puzzle** — The one Puzzle per Room whose opening ends the Room.
- **Wrong attempt** — A failed `code` or `use_on` input, or a full-length non-matching armed `order` sequence; never a click alone.
- **Idle** — Seconds since the player's last event (click, lock input, or Hint request) on the session clock; any click resets it; server idle ticks never do.
- **Clue** — Player-facing text pointing at a Puzzle's Evidence. Validator rule 5 checks the Clue and every displayed Evidence attribute (`evidence.visible_attribute`) like a nudge or direction: no solution token, same matching rules; each displayed attribute says where to look (§13 Q12, resolved).
- **Lore** — In-world flavor text per Puzzle, at most 60 words.
- **Evidence** — The Interactable and read attribute a Puzzle's solution depends on.
- **Evidence card** — How the Wizard notes show one piece of Evidence: Interactable label, thumbnail crop, read attribute. Real and Decoy cards look identical and keep a stable order.

**Hints and the Guide**
- **Rung** — A hint level: nudge, direction, near-answer; increasing in length; no solution token beyond the Rule 5 allowance.
- **Rule 5 allowance** — Validator rule 5: nudge and direction hold no solution token; a near-answer may name at most one label of an `order` sequence or one of a `use_on` pair, never a `code` string or its digits, never a `find` target's label; matching is case-folded and counts only whole words longer than three characters.
- **Nudge threshold** — Idle seconds before the nudge: 90 s × (1 + 0.5 × persistence), clamped to 60 to 135 s; 90 s on a fresh Player profile.
- **Hint request** — What all player text, typed or spoken, is reduced to in the browser; returns the Active puzzle's current Rung only.
- **No-hint line** — The Guide's fixed in-world reply to a Hint request when no Rung is open; encouraging, never a refusal (§7).
- **Early ask** — A Hint request made while no Rung is open on the Active puzzle; lowers persistence.

**Trickster edits**
- **Trickster window** — The moment right after a non-exit lock opens, at most once per 3 minutes of session time, when one Trickster proposal may be requested.
- **Game-state summary** — The Trickster's only input about play (FR-18); no Player profile field, no solution.
- **Trickster edit** — One Trickster proposal with its Validator result and outcome.
- **Decoy** — False Evidence added to a non-exit Puzzle by an accepted Trickster edit; shown as an Evidence card identical to real ones; at most one per Puzzle.
- **Merge** — A Trickster edit making one Puzzle require another first (adds a prerequisite).
- **Loosen** — A Trickster edit opening one named Rung of one Puzzle at once (applied to the Session, not the Room).
- **Shortcut** — A Trickster edit removing one prerequisite of one Puzzle, so it may become available early.
- **Scripted Trickster** — The Trickster source that replays recorded (cut 1: pre-authored) proposals bound to one Room; the Validator still runs live.
- **Card** — The on-screen outcome of one Trickster edit: accepted, rejected (with a plain reason from the fixed message), or skipped. Not a Clue card.
- **Card log** — The reopenable list of this Session's Cards.

**Player memory**
- **Room result** — Per-Room time, Rungs used, Wrong attempts, per-Puzzle {Lock type, attempts, Wrong attempts, Rungs used, time to first hint, solved}, Trickster edits seen and accepted, and the raw Event log; all kept in the browser.
- **Player profile** — Room results plus the Derived block, stored in the browser (a local JSON file under cut 2); never on the hosted server.
- **Derived block** — Recomputed after each non-demo Room: `time_to_first_hint_s` (median seconds, or null), `mean_rung_per_lock_type` (0 to 3 per Lock type), `persistence` (−1 to 1: positive when the player keeps trying past the nudge threshold, negative when they ask early), `sessions` (count, at least 0). It is all the Guide model and the Greeting may see; values outside these bounds are refused.
- **Greeting** — The Guide's opening line for a returning player, from the Derived block only; names no object or solution; a fixed template filled from the Derived block when phrasing is unavailable.
- **First-room welcome** — A fixed Guide line shown instead of a Greeting when the Player profile has no Room result.

**Build and verification**
- **Validator** — The eight deterministic rules of Schema v1 (plus rule 9 after the decoy pick), applied to every Room and Trickster edit; reasons never quote a solution token or answer.
- **Schema v1** — The Room, Puzzle, Interactable and Trickster edit contract in `schema-v1.md`; frozen Mon Oct 26, later changes only through `bmad-correct-course`.
- **Dry run** — A `muse-spark-1.3` call that sees photos, labels, Clues, and Rungs, never solutions, and must reach every answer.
- **Regeneration** — Riddler plus Dry run repeated with the failure reasons only; at most 2.
- **Build** — One pipeline run from a Photo set to a stored Room; ends `done`, `failed`, `needs_more_photos`, or `needs_recapture`; in Hosted mode may wait `queued`.
- **Build view** — The surface showing how a Room was built and verified (FR-38).
- **Model table** — Per Build: model id, where it ran, what it did, cached or billed; from provenance. The README carries a product-level version.

**Surfaces**
- **Capture screen**, **Play screen**, **Completion screen** — The upload surface; the Session surface; the surface shown when the Exit puzzle opens (§8).
- **Thumbnail strip** — Scene thumbnails for moving between photos.
- **Inventory** — Interactables collected by solving `find` Puzzles; persists through the Session.
- **Wizard notes** — The panel holding, per available Puzzle, its Clue, Lore, Evidence cards, opened Rungs and lock input, signed with the Wizard portraits. `[ASSUMPTION A-10: grouping inferred, confirm]`
- **Hint area** — Where Rungs, Guide lines, and Cards appear.
- **Triggers panel** — The panel that shows each Rung change with the events that caused it.
- **Clue card** — One image per Puzzle generated from the Clue text only with `muse-image-1.0`, cached, shown with the Clue (Tier 1.5; FR-37).

**Modes, demo and disclosure**
- **Local mode** — The product on Luis's M1, Guide on Ollama.
- **Hosted mode** — The same product on Modal CPU behind the judge URL; Rungs verbatim; no Guide model.
- **Access code** — The code that unlocks Judge room Builds in Hosted mode; at most 20 Builds.
- **Status endpoint** — `GET /meta`, which reports the mode and demo settings, the Disclosure text, and the Retention summary text (FR-26; architecture spine AD-15).
- **Demo timescale** — `DEMO_TIMESCALE=n`: divides the nudge threshold, Rung spacing, and Trickster window by n; never the Timer or Event log timestamps.
- **Scripted attack suite** — The fixed set of persuasion inputs ("just tell me the answer" and variants) run in tests and on video; none may open a lock or yield more than the current Rung.
- **Disclosure** — Plain on-screen and README text naming each demo shortcut or mode in effect.
- **Retention summary** — The one text, served by the status endpoint and shown on the Capture screen, naming every destination of photos and puzzle text in §6.1 with its retention terms.
- **Privacy line** — Verbatim: "the player profile stays on your machine."

**Spend**
- **Paid cloud call** — Any priced model call to the Meta Model API, fal.ai, Baseten, or Fireworks, in either mode.
- **Ledger** — Append-only record of every paid cloud call; kept outside the Cache.
- **Spend cap** — `SPEND_CAP_USD`, the running-total ceiling on paid cloud calls; values and refusal behavior in FR-28.
- **Spend log** — The submission's spend record: the Ledger export plus fal.ai receipts and Modal usage (FR-30).
- **Cache** — Stored responses to identical paid cloud calls, served unbilled when `CACHE=on`.
- **Mock provider** — Offline scripted stand-in for every model; no network, no spend.

**Delivery and tiers**
- **Backup video** — The Tier 1 demo recorded by Sun Nov 1 2:00 PM from whatever runs; its existence Sat Oct 31 night is the only early gate to Tier 2.
- **Capture proof** — The unedited, timed T0-to-T1 video of a never-built Room with `CACHE=off`, from a Photo set shot that day and never sent to the pipeline, with the Cache cleared on camera; kept only if it runs under 200 s, with at most one visible retry.
- **Main demo** — The edited, captioned video: 2:00 target, 2:30 cap; beats in §11.3.
- **Cut** — One of eight ordered scope reductions (§11.2), made nightly, never carried to a later day.
- **Tier 1** — The floor, protected above everything: FR-1 to FR-30, FR-36, and FR-38 (cut 0) plus the Backup video (§10.1).
- **Tier 1.5** — Work attempted only after the Backup video exists, in the order §10.1 sets.
- **Tier 2** — The walkable 3D Room; gated, default no-go.
- **Tier 3** — A Scaniverse splat shell; never gates anything.

## 4. Features

### 4.1 Capture a room from photos

**Description:** The Architect and `sam-3.1` turn a Photo set into Interactables while a visible Timer and stage make waiting read as progress. Realizes UJ-1, UJ-5, UJ-6. Mechanism: architecture spine AD-7, AD-18. Stage budgets: NFR-1.

#### FR-1: Upload a JPEG photo set

The player can upload 6 to 10 JPEG photos of one room from the browser, each downscaled in the browser and sent with its original in one request. Realizes UJ-1, UJ-5.

**Consequences (testable):**
- The Capture screen and the README state the Input requirement, "6 to 10 JPEG photos", with the iPhone Most Compatible tip, before any photo is chosen.
- A set with any non-JPEG file (HEIC, PNG, or any other format), or with fewer than 6 or more than 10 files, is rejected whole at the picker with "Keyframe needs 6 to 10 JPEG photos." and the offending files marked; nothing is uploaded and no bytes reach a model.
- Each downscale has a 1280 px long edge with EXIF orientation applied; the original is stored unmodified.

#### FR-2: List the room's objects

The Architect can list the room's objects from one `muse-spark-1.3` vision call over all photos, giving each a clearest photo, a box, and readable attributes. Realizes UJ-1.

**Consequences (testable):**
- One Architect call per Build, all photos in one request, reasoning effort low (budget: NFR-1).
- Attributes are stored verbatim as read and are the only attributes Evidence may cite (Validator rule 4).

#### FR-3: Segment objects into interactables

The system can segment each listed object with one `sam-3.1` call and select masks into 5 to 12 Interactables with polygon Hotspots. Realizes UJ-1.

**Consequences (testable):**
- One call per listed object, at most 12 concurrent (budget: NFR-1).
- The mask with the best overlap with the Architect's box is kept; for a plural label every mask with IoU above 0.2 is grouped as instances; masks under 1% of the image are dropped; with more than 12, the 12 with the highest Architect confidence are kept.
- An object with no mask gets its box rectangle as its Hotspot; it is clickable and can be a `find`, `order`, or `use_on` target.
- A `sam-3.1` call that still errors after its one retry ends the Build `failed` at the segment stage (FR-5). `[ASSUMPTION A-24: failure handling inferred from architecture spine AD-13, confirm]`

#### FR-4: Ask for more photos

The player can be asked for more photos when fewer than 5 Interactables survive. Realizes UJ-1.

**Consequences (testable):**
- With 4 or fewer Interactables the Build ends `needs_more_photos` with zero Riddler, Dry run, or Trickster calls.
- The Capture screen shows a fixed message asking for more photos of the room, keeps the chosen photos visible, and offers Add photos (up to 10 in all) and Start over; the next Upload is a new Build of 6 to 10 JPEG photos.

#### FR-5: Show the timer and build stage

The player can watch a Timer from T0 to T1 and the current Build stage, and receive the Room even when the Build outlasts one web request. Realizes UJ-1, UJ-5, UJ-6.

**Consequences (testable):**
- The Timer starts on the Upload click, stays pinned from the Capture screen into the Play screen, and stops at T1, then shows the frozen T1 − T0.
- Stages show in order: ingest, architect, segment, author, validate, dry run, scene; during a Regeneration, the author, validate, and dry run stages show again with the attempt number. `[ASSUMPTION A-11: player-facing labels "Reading your photos · Finding objects · Writing puzzles · Testing the room · Setting the scene", and "Rewriting puzzles, attempt n of 2", confirm]`
- A 260 s Build (two Regenerations) still completes and reaches the player by polling (architecture spine AD-7).
- On `needs_more_photos`, `needs_recapture`, or `failed` the Timer stops and shows the end status.
- A Build that ends `failed` (a provider error after its one retry, a refused call under the Spend cap, or a runner that stopped) shows the failed stage, a plain cause class, and a Try again control that starts a new Build with the same photos; no partial Room is playable.
- (Hosted mode, Tier 1.5) A Build waiting for the single runner shows a `queued` state.

#### FR-6: Show the retention summary

The player can read where photos and puzzle text go before uploading. Realizes UJ-1.

**Consequences (testable):**
- The Retention summary is the same text the status endpoint serves (architecture spine AD-8) and names every destination in §6.1 with its retention terms: the Meta Model API (standard tier); Baseten or Fireworks when a role's fallback is active; fal.ai in Tier 2; voice audio when voice ships (FR-35).
- (Hosted mode, Tier 1.5) The Retention summary also states that photos, originals, the Judge room and its Sessions are stored on Modal and deleted Tue Nov 10, that Session logs are deleted 24 h after their last event, and that no Player profile data leaves the browser in Hosted mode.
- The Privacy line appears verbatim on the Capture screen.
- The Capture screen asks the player to leave out faces, documents, and other people's belongings before upload.

### 4.2 Build a verified room

**Description:** No Room reaches a player until the Validator and a solution-blind Dry run agree it is solvable; this separates Keyframe from hollow riddle chains, and the Build view shows that work. Realizes UJ-1, UJ-5, UJ-6. Mechanism: architecture spine AD-3, AD-12, AD-13. Stage budgets: NFR-1.

#### FR-7: Author the puzzle chain

The Riddler can author 4 to 6 Puzzles that reference only listed Interactables and attributes the Architect read. Realizes UJ-1, UJ-4.

**Consequences (testable):**
- Exactly one Exit puzzle; each Puzzle uses `code`, `order`, `use_on`, or `find` (`code` and `find` only under cut 6).
- Each Puzzle has a Clue, Lore of at most 60 words, and three Rungs, written in the wizard voice (§7), so a verbatim Rung reads in character in Hosted mode and under cut 3.
- One Riddler call per attempt, reasoning effort medium; no reference to an Interactable outside the Room.

#### FR-8: Validate every room

The system can apply the eight Validator rules of Schema v1 (`docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/schema-v1.md` §Validator rules) to every Room before it is stored. Realizes UJ-1.

**Consequences (testable):**
- A Room failing any rule is never stored or playable.
- No nudge, direction, Clue, or displayed Evidence attribute contains a solution token (same matching rules); near-answers stay within the Rule 5 allowance and are also checked against the Clue.
- A `code` is 3 to 6 characters; an `order` sequence is 3 to 5 Hotspots (rule 7).
- Reasons are structured (rule, Puzzle, field) with a fixed message and never quote a solution token or answer.

#### FR-9: Dry-run every room

The system can require a Dry run to reach every answer while seeing only photos, labels, Clues, and Rungs, never solutions. Realizes UJ-1.

**Consequences (testable):**
- A sentinel-solution test finds no solution in the Dry run prompt.
- Any mismatched answer fails the Room; reasoning effort low.
- A passing Dry run proves the Clues and three Rungs suffice to reach every answer, so the near-answer Rung is always enough to solve.
- Under cut 4 the Dry run is skipped and the Validator alone gates the Room.

#### FR-10: Regenerate or ask for re-capture

The system can regenerate a failed Room with its failure reasons at most 2 times, then ask for re-capture. Realizes UJ-1, UJ-5.

**Consequences (testable):**
- A Regeneration carries the reason list only, never the previous draft.
- Riddler output that fails the response schema or exact-id parsing, and Dry run output that is missing or unparseable for any Puzzle, count as a failed attempt and feed a Regeneration with a fixed reason (A-24).
- After the second failed Regeneration (the first under cut 7), the Build ends `needs_recapture`; the Capture screen keeps the photos visible and asks for brighter, closer shots where labels and printed text are readable, with Start over.
- Provenance records the Regeneration count.

#### FR-38: Show how the room was built

The player, a judge, and Luis can open a Build view showing how the Room was built and verified, without any solution reaching the browser. Realizes UJ-1, UJ-5, UJ-6. Tier 1, cut 0: the first Cut taken; without it the Main demo shows the puzzle JSON and the Model table from the README.

**Consequences (testable):**
- The Build view shows the mask overlays per photo; the puzzle graph (Puzzles as nodes with Lock type, `requires` edges, the Exit puzzle marked); the Validator verdict per rule; the Dry run pass or fail per Puzzle (skipped under cut 4); the Regeneration count; and the Model table (model id, where it ran, what it did, cached or billed) from provenance.
- It is built from a solution-free projection of the Room; a sentinel-solution test finds no solution, Clue-to-answer mapping, or Dry run answer in its response.
- It is reachable from the Capture screen once the Build ends `done` and from the Completion screen.

**Notes:** the Build view serves the Main demo beats at 0:15 and 1:35 (§11.3) and the puzzle-JSON and model-table screenshots. Its data route is `GET /builds/<job_id>/view`, a solution-free projection (architecture spine AD-3).

### 4.3 Play the room

**Description:** A 15 to 25 minute Session across photo Scenes of the player's own objects; the server judges every lock and the browser never holds a solution. Realizes UJ-1, UJ-2, UJ-5. Mechanism: architecture spine AD-3, AD-4, AD-11.

#### FR-11: Play photo scenes

The player can play the Room as Scenes with mask Hotspots, a Thumbnail strip, a persistent Inventory, and Wizard notes. Realizes UJ-1.

**Consequences (testable):**
- Each Hotspot polygon is in the stored 1280 px photo's pixel space; a click inside it at any rendered size posts a click for that Interactable, and a hover reveals it.
- The Thumbnail strip reaches every photo. `[ASSUMPTION A-12: thumbnails in upload order, confirm]`
- The Inventory persists across Scene changes for the whole Session.
- Wizard notes show, for each available Puzzle, its Clue, Lore, Evidence cards (Interactable label, thumbnail crop, read attribute), opened Rungs and lock input; Puzzles with unmet prerequisites are hidden.
- After an accepted Decoy, real and Decoy Evidence cards are indistinguishable and appear in a stable order (one test; architecture spine AD-3; Schema v1 §Open pick).
- Reloading the Play screen resumes the Session from its Event log (Scenes, Inventory, open locks, current Rungs); if the server is unreachable, inputs disable with a reconnecting state and nothing is counted.

#### FR-12: Open locks only on correct input

The player can open a lock only with its correct input, judged by the server. Realizes UJ-1, UJ-2.

**Consequences (testable):**
- Each available Puzzle's lock input sits in its Wizard-notes entry. `code`: a 3 to 6 character field with Submit. `order`: the sequence is armed only by "Start the sequence" in the order Puzzle's entry; only Hotspot clicks made while armed count, in any Scene; a full-length mismatch counts one Wrong attempt and clears the buffer; "Stop the sequence" disarms with no Wrong attempt; exploring clicks made while unarmed never count (architecture spine AD-4, Schema v1). `find`: a click on the target Hotspot. `use_on`: drag an Inventory item onto a Hotspot, or select it and then click the Hotspot, with the Thumbnail strip usable while it is selected.
- Code input is compared trimmed and case-folded. `[ASSUMPTION A-20: code comparison rule, confirm]`
- A lock shows as open only after the server confirms it; a submitted input shows a pending state until the server answers.
- A Wrong attempt shows a plain "Not this" state and the per-lock count; a click alone never counts; a click on a Hotspot that is not a target shows the Interactable's label only.
- Solving a `find` Puzzle visibly moves its Interactable into the Inventory; an empty Inventory has its own empty state.
- An opened lock shows a short open state, then the next available Puzzle appears in the Wizard notes.
- Input for a Puzzle whose prerequisites are not open never opens it and is not a Wrong attempt; a `use_on` with an item not in the Inventory is refused.

#### FR-13: Complete the room

The player can finish by opening the Exit puzzle and see the Completion screen. Realizes UJ-1, UJ-4.

**Consequences (testable):**
- The Completion screen shows elapsed time, Rungs used, Wrong attempts, and per-Puzzle time; active Disclosures stay visible.
- Its one action is "Build another room" (the Capture screen in Local mode, the Hosted landing in Hosted mode); it also links the Build view (FR-38).
- The Room result is recorded into the Player profile.

#### FR-14: Resist persuasion

The player can type anything into the hint field; it becomes a Hint request that never yields anything above the current Rung. Realizes UJ-2.

**Consequences (testable):**
- A Hint request answers for the Active puzzle: the most recently targeted available unsolved Puzzle (targeted by a lock input, or by a Hint request naming an available unsolved Puzzle), else the earliest available unsolved Puzzle in the Room's order; a click never sets it, and it is null only once the Exit puzzle has opened (architecture spine AD-4). The client always omits the Puzzle id; the server resolves it.
- The Scripted attack suite, led by "just tell me the answer", returns the current Rung, or the No-hint line when none is open, and opens nothing.
- When no Rung is open, the Hint request returns the No-hint line: an in-world Guide line that acknowledges the request, says help is coming, and points back to the Scene; it never reads as a refusal and never names an object or solution. It is logged as an Early ask and lowers persistence (§3 Derived block). Whether it also releases the nudge at once is §13 Q9; until decided, it is only logged.
- Typed player text never leaves the browser; only the Hint request enters the Session (voice: FR-35).
- A fixture test finds no solution in any play response.

**Out of Scope:** free conversation with any wizard.

### 4.4 The Guide

**Description:** The Guide reads the Event log, not the player's words: it picks the Rung in code, shows why, and phrases it on the Mac. Realizes UJ-2, UJ-4, UJ-5. Mechanism: architecture spine AD-4, AD-5, AD-10.

#### FR-15: Select the rung from play

The Guide can select the Rung from the Event log. Realizes UJ-2.

**Consequences (testable):**
- Rungs, Wrong attempts, and Idle seconds are tracked per Puzzle; Idle counts from the player's last event (click, lock input, or Hint request), and server idle ticks never reset it.
- The nudge for the Active puzzle fires after the nudge threshold of Idle, 90 s × (1 + 0.5 × persistence) clamped to 60 to 135 s (90 s on a fresh Player profile), or after 3 Wrong attempts at that lock, whichever is first.
- Direction and near-answer each need a further stall (Idle equal to the nudge threshold, consistent with FR-24's 45 s on idle at 6×) or 3 further Wrong attempts, and arrive at least 90 s after the previous Rung; the 90 s spacing never scales with persistence.
- Exception: an accepted Trickster Loosen opens its named Rung at once, inside FR-18's window rules, and is not counted against the 90 s spacing.
- Replaying an Event log yields the same Rung changes as live play.
- After the near-answer, there is no reveal or skip; a further Hint request repeats the near-answer. `[ASSUMPTION A-21: no reveal control in the MVP, confirm]`

#### FR-16: Show rung triggers

The player can see each Rung change with its triggering events. Realizes UJ-2, UJ-6.

**Consequences (testable):**
- Every Rung change in the Triggers panel lists its Idle seconds, its Wrong attempts, or the Trickster Card that loosened it.
- The Triggers panel is collapsed by default behind an always-visible toggle and opens automatically while a Disclosure is active.
- Under cut 5 the Triggers panel moves to a second window, unchanged in content.

#### FR-17: Phrase the rung locally, or show it verbatim

The Guide can phrase the Rung with Llama 3.2 3B on Ollama in Local mode; Hosted mode shows the Rung text verbatim. Realizes UJ-2, UJ-5.

**Consequences (testable):**
- Local phrasing meets NFR-2 with a fixed prefix; past 5 s the verbatim Rung is shown and the fallback logged; while the Guide phrases, its portrait shows a thinking state.
- If Ollama is unreachable or errors, the verbatim Rung is shown at once and the fallback logged.
- The phrasing input is exactly the Rung text and the Derived block; never room content or a solution.
- (Hosted mode, Tier 1.5) Hosted mode runs no Guide model and refuses to start if configured with one.
- Under cut 3 Local mode also shows Rungs verbatim and the README drops the phrasing claim; the Privacy line stays.

### 4.5 The Trickster

**Description:** The room pushes back between Puzzles, within rules the Validator enforces; both outcomes are shown. Realizes UJ-3, UJ-6. Mechanism: architecture spine AD-4, AD-12, AD-15.

#### FR-18: Propose a bounded change

The Trickster can propose one Decoy, Merge, Loosen, or Shortcut between Puzzles. Realizes UJ-3.

**Consequences (testable):**
- When a non-exit lock opens and no Trickster window has closed in the last 3 minutes of session time, one window opens and exactly one proposal is requested. `[ASSUMPTION A-26: the first window may open no sooner than 3 minutes after Session start, confirm]`
- At most 6 `muse-spark-1.3` calls per Session; the seventh is refused.
- The Game-state summary is open locks, elapsed time, and Rungs used only: no Player profile field and no solution; a Decoy never targets the Exit puzzle.

#### FR-19: Re-validate and show cards

The player can see every Trickster edit as a Card after re-validation; the Effective room changes only on acceptance. Realizes UJ-3.

**Consequences (testable):**
- An edit is accepted only if the Room with it applied passes Validator rules 1 to 8 (plus rule 9 after the decoy pick); no Dry run. At most one Decoy per Puzzle.
- On acceptance the Play screen reflects the edit at once: a new Evidence card (Decoy), a Puzzle now locked behind another (Merge), a Rung in the Hint area (Loosen), or a Puzzle becoming available (Shortcut).
- A Card appears in the Hint area after the lock-open state, stays until dismissed, and is kept in the Card log. Each Card names the edit type and its effect in one plain sentence; a Decoy Card never identifies which Evidence is false.
- A rejected Card shows a plain one-line reason derived from the Validator rule's fixed message, never a token; the Effective room is unchanged; the stored Room is never mutated.
- A provider error or reached Spend cap during a window shows a skipped Card with the same one-line message for either cause, and play continues.
- A window after the sixth Trickster call opens no proposal and shows no Card.

**Notes:** decoy storage follows the Thu Oct 22 pick (§13, Q1).

### 4.6 Player memory

**Description:** The game remembers the player without a server holding their Player profile. Realizes UJ-4. Mechanism: architecture spine AD-8.

#### FR-20: Keep the player profile in the browser

The player can keep their Player profile in their own browser. Realizes UJ-4.

**Consequences (testable):**
- Room results and the Derived block are written only to IndexedDB under the `PROFILE` name (`dev`, `playtest`, `demo`); under cut 2, they are written to a local JSON file on the player's machine.
- A Session start carries the Derived block and nothing else from the Player profile.
- A Session start whose Derived block is outside its bounds (`sessions` at least 0, `persistence` −1 to 1, `mean_rung_per_lock_type` 0 to 3) is refused with a 422 and no Session is created.
- (Hosted mode, Tier 1.5) Hosted mode sends `Derived.fresh()` with every Session start, so no Player profile field leaves the browser; the hosted server persists no Derived block and never joins a Session log to a Player profile.
- (Hosted mode, Tier 1.5) Under cut 2, Hosted-mode Player profile behavior is stated in the README (architecture spine AD-8) and is decided when cut 2 is taken.

#### FR-21: Greet the returning player and adapt thresholds

The returning player can receive a Greeting citing how they played the previous Room, with the nudge threshold scaled to their persistence. Realizes UJ-4.

**Consequences (testable):**
- After each non-demo Room result the Derived block is recomputed: `sessions` = count of non-demo Room results; `time_to_first_hint_s` = median of per-Puzzle time to first hint (null if none); `mean_rung_per_lock_type` = mean Rungs used per Puzzle by Lock type, 0 to 3; `persistence` = the A-19 formula, clamped to −1 to 1. `[ASSUMPTION A-19: persistence is the mean over every Puzzle in the non-demo Room results of +1 for a Puzzle solved after its nudge fired with no Hint request on it, −1 for a Puzzle with an Early ask, and 0 otherwise; 0 when there are none; confirm]`
- A Greeting is shown before the first Scene when `sessions` is at least 1, as a Guide line with portrait, dismissed by "Begin"; a fresh Player profile gets the First-room welcome instead. `[ASSUMPTION A-13: placement and form, confirm]`
- The Greeting uses the Derived block only and names no object and no solution.
- (Hosted mode, Tier 1.5) Hosted mode always shows the First-room welcome, because its Session start carries a fresh Derived block.
- When phrasing is unavailable (cut 3, or past 5 s of local phrasing) the Greeting is a fixed template filled from the Derived block, in the same voice, naming no object or solution (§7).
- With persistence p the nudge threshold is 90 s × (1 + 0.5 × p), within 60 to 135 s.

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
- Four portraits are generated once with `muse-image-1.0` by a script, committed, and shown in play; they share the painted, candlelit oil-portrait style (§7).
- Play makes zero image-generation calls; missing portraits fall back to placeholder art.

#### FR-37: Show a clue card with each clue (Tier 1.5)

The player can see a Clue card beside each Puzzle's Clue, one image per Puzzle generated from the Clue text only. Realizes UJ-1.

**Consequences (testable):**
- Clue cards are generated once per demo Room (the recorded rooms and the hosted Demo rooms) by an explicit step, cached and priced; Judge rooms and ordinary Builds get none unless Luis enables Clue cards for them; when enabled, each card is priced per Build in the Ledger. Never generated in play.
- The prompt is the Clue text only: no solution, Rung, photo, or Player profile field (sentinel-solution test).
- Clue card references live outside the frozen Room (keyed by Puzzle id in the artifact store) or are added through `bmad-correct-course`; Schema v1 is not reopened. Decoy and Merge edits leave the Clue text, and so the card, unchanged.
- Until ready, the Clue card shows a same-size placeholder; a failed Clue card stays blank so the layout never shifts; the card never fails the Build or delays T1. Its alt text is the Clue. `[ASSUMPTION A-14: Clue cards never gate T1 or the Build, confirm]`

**Out of Scope:** Clue cards in Tier 1; images derived from room photos.

### 4.8 Demo mode and disclosure

**Description:** Video-friendly timings and replays, with the Validator, Timer, and Event log kept real and every shortcut disclosed. Realizes UJ-6. Mechanism: architecture spine AD-10, AD-15. Demo honesty: NFR-12.

#### FR-24: Compress demo timings

Luis can set a Demo timescale n that divides the nudge threshold, Rung spacing, and Trickster window by n. Realizes UJ-6.

**Consequences (testable):**
- At `DEMO_TIMESCALE=6`, three Rungs arrive within 40 s on Wrong attempts (30 s nominal; 45 s on idle alone), and the Trickster window is 30 s.
- The Timer and Event log timestamps are unchanged at any timescale.

#### FR-25: Replay Trickster proposals with a live validator

Luis can switch to the Scripted Trickster, which replays recorded proposals while the Validator runs live. Realizes UJ-3, UJ-6.

**Consequences (testable):**
- `DEMO_TRICKSTER=scripted` replays two recorded proposals; the live Validator accepts one and rejects one.
- Recorded proposals are bound to one Room; on another Room, or once the recording is used up, the scripted source yields no proposal and no Card.
- Cut 1 uses the same source with pre-authored proposals, one written to fail, and no live Trickster calls; the Validator still runs on every Card.

#### FR-26: Disclose demo settings

The player, a judge, and the README can see which demo settings are active. Realizes UJ-5, UJ-6.

**Consequences (testable):**
- The status endpoint reports mode, Guide, Trickster source (live, scripted, cut 1), Demo timescale, Cache, Player profile name, Disclosure text, and the Retention summary text (architecture spine AD-15).
- The UI shows a Disclosure whenever the Demo timescale exceeds 1, the Trickster is scripted or cut 1, or Hosted mode is active.
- The Disclosure is a persistent plain-text banner at the top edge of the Capture, Play, and Completion screens and the Hosted landing; it cannot be dismissed and never covers the Scene or its Hotspots; when several apply, their lines are joined.
- The Disclosure text matches the active Trickster source (live, scripted, cut 1) and Demo timescale (§7 Disclosure copy).

### 4.9 Spend and cache guard

**Description:** No paid cloud call goes unpriced or uncounted, identical calls come from the Cache, and every Room records its provenance. Realizes UJ-6. Mechanism: architecture spine AD-6, AD-9, AD-16.

#### FR-27: Cache identical calls

The system can serve an identical paid cloud call from the Cache without billing. Realizes UJ-6.

**Consequences (testable):**
- With `CACHE=on`, a repeat of the same model, schema, full prompt, reasoning effort, image hashes, and attempt number is served from the Cache and adds nothing to the Ledger.
- With `CACHE=off` every call reaches the provider and is still priced.
- A Regeneration is never served its own failed answer.
- Clearing the Cache never touches the Ledger, its exports, or the running total.

#### FR-28: Price, record, and cap spend

The system can price every uncached paid cloud call, record it in the Ledger, and refuse a call that would pass the Spend cap. Realizes UJ-6.

**Consequences (testable):**
- The cap is the `SPEND_CAP_USD` setting, read per mode and enforced per store and per call: local 60 and hosted 20 through Wed Nov 4 (80 in all), local 5 and hosted 20 from the Thu Nov 5 reset (FR-29; 25 in all); the Modal Secret carries the hosted value; the daily export prints the local total, the hosted total and their sum against the combined ceiling; no date logic in code.
- A refused call ends a Build `failed` at its stage, with code `spend_cap_exceeded` and a plain Spend-cap message on the Capture screen (FR-5); in play it shows a skipped Card (FR-19); in a script it makes the script exit non-zero, printing the cap and the running total.
- The running total survives a restart.

#### FR-29: Export the ledger daily

Luis can rely on a daily Ledger export as the durable spend record. Realizes UJ-6.

**Consequences (testable):**
- Local mode writes a dated export (`spend/exports/ledger-<date>.json`) at startup and after every completed Build.
- (Hosted mode, Tier 1.5) Hosted mode snapshots the Ledger daily at 06:00 ET.
- A counter reset on any day is refused unless that day's export exists.

#### FR-30: Record provenance

The system can attach provenance to every Room. Realizes UJ-5, UJ-6.

**Consequences (testable):**
- Every stored Room lists model ids, prompt hashes, stage timings, Regeneration count, spend per stage, and applied Trickster edit ids (empty on the stored Room).
- The submission's Spend log is the Ledger export for paid cloud calls, plus fal.ai receipts and Modal usage attached as-is; pre-kickoff verification spend is listed separately.

### 4.10 Hosted judge URL (Tier 1.5)

**Description:** Judges open a URL, play Demo rooms, and may build a Judge room behind the Access code. Hosted mode runs the same product on Modal CPU; Rungs appear verbatim because no Guide model runs off the Mac. Built after the Backup video; the redeploy and the live-link contingency are in §11.1 (Wed Nov 4 and Thu Nov 5 rows) and §10.1. Realizes UJ-5. Mechanism: architecture spine AD-7, AD-9. Hosted-mode consequences of Tier 1 FRs ship with this feature; they sit in FR-5, FR-6, FR-17, FR-20, FR-29, and FR-36.

#### FR-31: Play demo rooms on the hosted URL

A judge can open the hosted URL and play cached Demo rooms through the same API as Local mode. Realizes UJ-5.

**Consequences (testable):**
- The Hosted landing lists the Demo rooms; each plays to the Completion screen.
- Rungs are verbatim and the Disclosure states Hosted mode.
- The Trickster runs live under the Spend cap or scripted, per §13 Q11; the Disclosure names the source.
- Hosted mode shows the First-room welcome, never a Greeting (FR-21).

#### FR-32: Build a judge room with the access code

A judge can build a Judge room behind the Access code. Realizes UJ-5.

**Consequences (testable):**
- The Access code is checked before photo selection; a missing or wrong Access code is refused inline and no upload starts.
- Every Build accepted with the Access code counts toward the 20, whatever its end status; the 21st is refused with a quota message, and the Demo rooms stay open. `[ASSUMPTION A-25: quota counting, confirm]`
- A Build outlasting the host's 150 s web timeout completes and reaches the judge; an accepted Build has its own URL that resumes polling after the tab is closed.

#### FR-33: Delete judge data on schedule

The system can delete Judge rooms and hosted Session logs on schedule. Realizes UJ-5.

**Consequences (testable):**
- A purge run on Tue Nov 10 (architecture spine AD-8) deletes Judge rooms, originals, Sessions, and Cache entries together; Demo rooms persist.
- Hosted Session logs are deleted 24 h after their last event, or when their Room is deleted.
- The app never deletes local `rooms/` or `.cache/`.
- A Judge room's Completion screen states "Deleted Tue Nov 10"; afterwards its URL states the room was deleted on Tue Nov 10 as promised.

### 4.11 Walkable 3D room (Tier 2, gated, default no-go)

**Description:** The Room becomes a walkable 3D scene of reconstructed objects, and Puzzles trigger by looking. Scheduling and the gate: §10.2 and §11.1. Realizes UJ-7. Mechanism: architecture spine AD-11, Deferred.

#### FR-34: Walk the room in 3D

The player can walk a 3D version of the Room and trigger Puzzles by raycast. Realizes UJ-7.

**Consequences (testable):**
- The scene holds up to 20 reconstructed instances from at most 12 Interactables, by fal.ai SAM 3D Objects ($0.02 a call, cloud only) from original-resolution photos, in the same scene graph as Tier 1.
- Passes the Tier 2 gate (§11.1).
- fal.ai calls are priced in the Ledger against the Spend cap and stay within $6 cash.

### 4.12 Voice help (unscheduled)

**Description:** The player asks the wizards for help aloud; speech becomes a Hint request like typed text. Ships only if everything else is done Mon Nov 2. Realizes UJ-2. Voice transport is a spine Deferred item.

#### FR-35: Ask for help by voice

The player can ask for help by voice and get the same Rung a click would give. Realizes UJ-2.

**Consequences (testable):**
- Speech is transcribed by `muse-voice-transcribe-1.0`, with browser speech recognition as fallback.
- Audio goes to the Meta Model API for transcription (or to the browser's speech service on the fallback); the transcript is reduced to a Hint request and is never stored or logged; only the Hint request enters the Session. When voice ships, the Retention summary names voice audio and both services.
- A spoken request raises a Hint request exactly as a typed one does; a spoken "just tell me the answer" yields nothing above the current Rung and never advances a Rung beyond FR-15.
- When voice ships, a mic control beside "Ask the Guide" has idle, listening, transcribing, and permission-denied states; denied falls back to the hint field.

### 4.13 Privacy guarantees

**Description:** Raw room photos never enter the public repo; only outputs ship (screenshots, Clue cards, the videos). The Player profile stays on the player's machine. Realizes UJ-1, UJ-4, UJ-5. Mechanism: architecture spine AD-8, AD-14.

#### FR-36: Keep photos out of the repo and profiles off the server

The player and Luis can rely on raw room photos never entering the repo and the hosted server never persisting Player profile data. Realizes UJ-1, UJ-4, UJ-5.

**Consequences (testable):**
- `rooms/` (stored photos, originals, Sessions), `photos/`, `captures/`, `uploads/`, `*.heic`, `.cache/` and `.env` are git-ignored, asserted by offline tests; only daily Ledger exports and outputs are committed.
- (Hosted mode, Tier 1.5) The hosted server persists no Derived block or Player profile data and never links a Session log to a Player profile.
- Only the Meta Model API standard tier is used, never the contributor tier.

## 5. Cross-Cutting NFRs

- **NFR-1 Capture performance:** the Capture target; stage budgets Architect 15 s, segmentation 10 s, Riddler 45 s, Dry run 30 s, Scene 10 s; a Regeneration about 75 s; a Capture proof take is kept only if it runs under 200 s. Stage budgets are p50 over at least 5 live Builds measured Oct 27 to 28; a stage over budget never fails the Build. FR-2, FR-3, FR-7, FR-9, and FR-10 refer here.
- **NFR-2 Hint latency:** about 40 tokens in 5 s or less from a prompt under 400 tokens with a fixed prefix.
- **NFR-3 Hardware:** everything local runs on one 16 GB M1 MacBook Pro without CUDA; Guide model near 3 GB resident; demo-recording memory about 10.6 GB; no local SAM 3.1, SAM 3D Objects, or 30B models. Detail: §6.4.
- **NFR-4 Privacy:** the Guide model runs only on the Mac; the Player profile stays on the player's machine; only the Derived block reaches the Guide model and the Greeting; raw room photos are never committed; the Retention summary is shown; standard tier only. Detail: §6.1.
- **NFR-5 Integrity:** solutions never enter a model prompt or play response; Validator reasons never quote a token or answer; only the server's session logic opens locks. Detail: §6.2.
- **NFR-6 Cost:** Spend cap $80 until the Thu Nov 5 reset, then $25, allocated per mode (local 60 and hosted 20, then local 5 and hosted 20); fal.ai at most $6 cash; development runs on the Mock provider with `CACHE=on`. Detail: §6.3.
- **NFR-7 Reliability:** Builds survive the 150 s web timeout and resume at the last completed stage after a restart; provider calls retry once, on rate-limit and server errors only; at most 2 Regenerations.
- **NFR-8 Testability:** every story's tests pass offline on the Mock provider; provider tests use recorded fixtures; dependency-boundary, type-staleness, and ignore-file tests run offline.
- **NFR-9 Rate limits:** within Meta Model API limits (`muse-spark-1.3` 3,000 RPM and 4,000,000 TPM; `sam-3.1` 3,000 RPM; `muse-image-1.0` 150 RPM); segmentation concurrency at most 12.
- **NFR-10 Platform:** Local mode on Chrome on the Mac; Hosted mode on current desktop Chrome, Safari, and Firefox at 1280 px or wider (A-15); Tier 1 Scenes as textured planes in the scene graph Tier 2 reuses (if the Three.js scene graph costs more than 2 h, Scenes are DOM-only and keep every Hotspot, and Tier 2 stays no-go); the Tier 2 gate needs 30 fps or better on the M1. Detail: §6.5.
- **NFR-11 Schedule:** the gates in §11.1; Schema v1 frozen Mon Oct 26, later changes only through `bmad-correct-course`; Fri Oct 30 no build; Cuts made nightly in order. Detail: §6.6.
- **NFR-12 Demo honesty:** every beat on video is rehearsed, never faked.
  - Demo settings change only timing and the Trickster source; no demo path injects events, Rung changes, Greetings, Validator results, or Build output.
  - Real Idle time and real Wrong attempts trigger every Rung, compressed only by the Demo timescale; the live Validator decides both replayed Trickster edits; the Greeting reads the real room-1 record on `PROFILE=demo`, played at timescale 1 on Mon Nov 2; the Timer and Event log are never scaled.
  - The Main demo's capture time-lapse is acceptable only because the unedited Capture proof (§3) accompanies it.
  - The 6× timescale, the Scripted Trickster replay (or cut 1's pre-authored proposals), and earlier builds of a Room are disclosed in the last 10 s of the Main demo and in the README; the README states which Cuts shipped; the UI and README declare the finals mode.
- **NFR-13 Submission and hygiene:** a public MIT repo listing third-party and model licenses, with pre-existing code disclosed against the `pre-hackathon-baseline` tag and its diffstat.
  - The README carries the pitch, a model table (model id, where it runs, what it does, whether it shipped), an architecture diagram, local-mode setup, the Privacy line, the Retention summary, the Disclosures, which Cuts shipped, the pre-existing-code statement with its diffstat, and the licenses.
  - The delivery steps (baseline tag, CHANGELOG, Official Rules, screenshots, portal write-up, repo hygiene) are in the §11.3 submission checklist.
- **NFR-14 Accessibility floor:** every Hotspot is reachable by Tab with a visible focus ring and Enter acts as a click; a "Show all objects" toggle outlines every Hotspot; `use_on` also works by select-then-click; text meets WCAG AA contrast on the dark theme; Rungs, Cards, and the Greeting are announced in a polite live region; motion respects reduced-motion settings.

## 6. Constraints and Guardrails

Each subsection adds detail to one NFR in §5 and does not restate it.

### 6.1 Privacy

Detail for NFR-4.

- The Privacy line appears verbatim on the Capture screen and in the README and holds under every Cut, including cut 3.
- Raw room photos never enter the public repo, consent or not; only outputs ship, with household consent for everything that appears in the videos and screenshots. The Organizers receive those outputs under a perpetual license.
- The two video rooms, room 1 and room 2, are photographed with no faces, documents, or other people's belongings in frame; this applies to every photo sent to a model and every frame of the videos and screenshots.
- Photos and puzzle text go to the Meta Model API (standard tier). The Riddler's or Trickster's prompt (never a solution, never a Player profile field) goes to Baseten or Fireworks only when that role's fallback is active. In Tier 2, photos go to fal.ai. In Hosted mode, Judge-room photos, originals, Rooms, and Sessions are stored on Modal until Tue Nov 10, and Session logs for at most 24 h after their last event. Voice audio, if voice ships, goes to the Meta Model API or the browser's speech service. The Retention summary states all of this before upload.

### 6.2 Integrity

Detail for NFR-5.

- The Dry run, Trickster, Guide, Greeting, Build view, and Clue card inputs see no solution; the only exception is the access-coded full-Room download for Luis (architecture spine AD-3, AD-9; §13 Q4).
- The persuasion attack fails by construction: player text is a Hint request whose ceiling is the current Rung; the failure is shown on video.
- Every Room and Trickster edit passes the Validator; demo mode swaps the Trickster's source, never the check.

### 6.3 Cost

Detail for NFR-6.

- Expected spend about $35, against daily ceilings that total $79; a clean Build about $0.10 (under $0.25 with two Regenerations), a Session about $0.21.
- The $80 cap is set against the $150 Meta Model API credit; if no credit is issued, the plan costs about $35 cash; from Thu Nov 5 the $25 cap runs pay-as-you-go; both caps are allocated per mode (local 60 and hosted 20, then local 5 and hosted 20).
- The daily Ledger export is the durable spend record.

### 6.4 Hardware

Detail for NFR-3.

- No GPU anywhere, local or cloud. On the Mac: Chrome, the backend, Llama 3.2 3B on Ollama. In the cloud: `muse-spark-1.3`, `sam-3.1`, `muse-image-1.0` (and `muse-voice-transcribe-1.0` if voice ships) on the Meta Model API; fal.ai SAM 3D Objects in Tier 2 only; Modal CPU for Hosted mode.

### 6.5 Platform

Detail for NFR-10.

- Local-mode photos come from a phone as JPEG (iPhone set to Most Compatible).
- Judges use the hosted URL. `[ASSUMPTION A-15: Hosted mode supports current desktop Chrome, Safari, and Firefox at 1280 px or wider, Chrome the tested target; below 1024 px the Hosted landing says Keyframe plays on a laptop or desktop browser; confirm]` Finals Mon Nov 9 run Local mode screen-shared from the M1, falling back to the hosted URL, then cached Rooms, then the video.

### 6.6 Build model

Detail for NFR-11.

- Implementation runs around the clock on multiple coding agents (Muse Code and the BMAD build loop), schema-first, one owner per package, against the Mock provider; each story touches one package plus its tests.
- Luis Ticas reviews everything that ships, with about 32 h in-window (around a day job) for review, direction, playtesting, and recording.
- Cuts trigger when reviewed output lags (§11.2).

## 7. Aesthetic and Tone

Visual direction, color mode, voice and portrait style are Luis's decisions from the UX discovery round. Sample lines are illustrative: the UX contract may reword any of them if the rewrite keeps the line's functional intent; this PRD protects requirements, not sentences.

- **Visual direction:** Lamplit study. Warm dark chrome, parchment-toned cards and notes, serif headings; the UI frames the player's own photos like a wizard's study. Dark mode only.
- **Scenes:** the player's real photos, full-bleed, traversed by thumbnails, Hotspots revealed on hover (and by the "Show all objects" toggle, NFR-14) rather than outlined at rest. Lead with what the room knows, never with photorealism.
- **Lead with the work:** lead with the graph and verification (the Build view), never a text riddle; every lock is solved inside the Scene, never by photographing an object.
- **The four wizards:** introduce each wizard by what it consumes and produces, then its voice. Wizard voice: wry and playful in Rungs, Greetings, and Cards, never condescending, one or two sentences. The Architect observes, the Riddler teases, the Guide encourages, the Trickster has the most fun with the player.
- **Portraits:** painted, candlelit oil-portrait style, shared by all four.
- **Register rule:** Rungs, the No-hint line, the Greeting, the First-room welcome, Cards and Build stages are in character; format and count errors, `failed`, Spend cap, quota, Access code and deletion messages are plain; Disclosures are always plain.
- **Rung copy:** scaffolds, never answers. A nudge says where to look, a direction what to notice, a near-answer how to use it; none says "the answer is". Sample Guide nudge: "The shelf has been very quiet. Suspiciously quiet."
- **No-hint line:** in-world and encouraging, never a refusal and never "no hint available"; it acknowledges the ask, says the Guide is watching and help is coming, and invites one more look, with no content about any Puzzle. Sample: "Look around a little longer; I'll speak up if you stay stuck."
- **Greeting:** wry, warm and specific about play style, never about objects, never surveillance-flavored. Template when phrasing is unavailable, sample: "Welcome back. Last time you held out {persistence phrase} before asking; let's see what this room makes of you." First-room welcome, sample: "Welcome to your own room. Find what doesn't belong."
- **Cards:** one plain effect sentence in the Trickster's voice. Samples: Decoy "A new clue has appeared."; Merge "This lock now needs another opened first."; Loosen "The Guide is feeling generous." plus the Rung; Shortcut "A door just opened early."; rejected "The Validator says that wouldn't be fair. Spoilsport."; skipped "The Trickster is quiet this time."
- **Disclosure copy:** plain, out of character, literal. "Hint and Trickster timings run at n× speed; the build timer is real time." / "Trickster proposals replayed from a recording; the Validator ran live." / cut 1: "Trickster proposals were written in advance; the Validator ran live on each." / "Hosted mode: hints are shown as written; no hint model runs here."
- **Errors:** plain and actionable ("Keyframe needs 6 to 10 JPEG photos."; Spend cap: "Keyframe has reached its spending limit, so this room can't be built right now."; the cap is a running total, not a daily limit).
- **Motion, sound, density:** slow and warm (fades, lamplight glow on Hotspot hover), nothing over 300 ms, reduced motion respected; no sound in v1; designed for a 1440 × 900 MacBook viewport, the Scene taking most of the width with the Wizard notes and Hint area in one side column.

## 8. Information Architecture

`[ASSUMPTION A-17: layout, grouping and navigation inferred, confirm]`

- **Navigation:** Local mode opens on the Capture screen with stored Rooms listed below (replay starts a new Session). Capture → Play is automatic when the first Scene is ready; Play → Completion is automatic on the Exit puzzle. Completion's "Build another room" returns to the Capture screen (Local) or the Hosted landing (Hosted). Reload restores the Session from the Event log. "Leave room" confirms and records no Room result.
- **Capture screen:**
  - Before upload: the Input requirement and the iPhone Most Compatible tip; the faces, documents, and belongings reminder; the photo picker and Upload; the Retention summary with the Privacy line.
  - During the Build: the Timer, the current Build stage, and the mask preview (each Interactable's clearest photo with its outline as segmentation completes).
  - Messages: rejected formats or counts, `needs_more_photos` (Add photos, Start over), `needs_recapture` (Start over), `failed` with its stage (Try again), Spend cap reached, `queued` and Build quota reached (Hosted).
  - End states keep the photos visible and stop the Timer; a link to the Build view appears on `done`.
- **Build view:** per FR-38.
- **Room-2 Greeting:** a Guide line with portrait over the first Scene before play, dismissed by "Begin"; the First-room welcome on a fresh Player profile.
- **Play screen:** Scene with Hotspots; Thumbnail strip; Inventory (drag source for `use_on`, with an empty state); Wizard notes with portraits and, per available Puzzle, its Clue, Lore, Evidence cards (Interactable label, thumbnail crop, read attribute), opened Rungs, lock input, and Clue card in Tier 1.5; Hint area with an "Ask the Guide" button beside the hint field (both send one Hint request for the Active puzzle), the Guide thinking state, and the Triggers panel (collapsed by default; a second window under cut 5); Trickster Cards and the Card log.
- **Wizard placement:** the Architect speaks Build stages and the mask preview; the Riddler signs each Clue and Lore in the Wizard notes; the Guide speaks Rungs, the No-hint line, the Greeting, and the First-room welcome in the Hint area; the Trickster speaks every Card. Each line shows its portrait.
- **Completion screen:** elapsed time, Rungs used, Wrong attempts, per-Puzzle time; "Build another room"; link to the Build view; in Hosted mode a Judge room shows "Deleted Tue Nov 10".
- **Disclosure banner:** per FR-26.
- **Hosted landing:** Demo room cards (cover photo, name, Puzzle count, 15 to 25 min); Access-code entry with empty, checking, refused, accepted ("n of 20 builds left") and quota-reached states, checked before photo selection; mode Disclosure; below 1024 px a laptop-or-desktop message (A-15).

## 9. Non-Goals (Explicit)

- Live phone capture, mobile or native apps, Quest or MR.
- Multiplayer, accounts, cloud sync of the Player profile.
- Any hosted or cloud-run Guide model; Muse Glimmer; Muse Wonder; SAM 3D Body.
- Local SAM inference; Modal GPU self-hosting; the contributor tier.
- Puzzle content not derived from the player's photos; free conversation with the wizards.
- Committing raw room photos; a single uncut long video.

## 10. MVP Scope

### 10.1 In Scope
- **Tier 1, the floor, protected above everything:** FR-1 to FR-30, FR-36, and FR-38 (cut 0, the first Cut taken) (of FR-23 and FR-37, only the FR-23 Wizard portraits), with whatever Cuts are in force, plus the Backup video (room 2 and the FR-21 Greeting move to Sun Nov 1 afternoon under cut 8, the expected case; the Backup video does not require them).
- **Tier 1.5, only once the Backup video exists:** second room and cross-session Greeting (under cut 8); Cuts restored last-first, only with time left (only cuts 1 to 3 are realistic before Nov 3); then Clue cards (FR-37); then Hosted mode for judges (FR-31 to FR-33, Nov 5 to 9, or FR-31 by Wed Nov 4 if a live link is required; the Nov 5 to 9 work is subject to §13 Q14); then voice (FR-35).
- Hosted-mode consequences of Tier 1 FRs (tagged "(Hosted mode, Tier 1.5)") are Tier 1.5 and ship with FR-31 to FR-33.

### 10.2 Out of Scope for MVP
- **Tier 2 (FR-34):** default no-go, attempted Sun Nov 1 only if the Backup video exists Sat Oct 31 night. FR-34 gets no epic or stories until the Mon Nov 2 gate passes; expected: not attempted. If fal.ai output lacks a usable pose, Tier 2 falls back to Runware, Segmind, hand-made assets, or a photo billboard. `[NOTE FOR PM]` The walkable room is the most emotionally load-bearing deferral, the "I'm inside my own room" moment. It returns only through the Mon Nov 2 gate and never at the expense of Tier 1 or the Main demo (SM-C3).
- **Tier 3:** never gates a deliverable.
- **Voice (FR-35):** unscheduled; only if everything else is done Mon Nov 2; voice UI stays out of the UX contract until scheduled.
- `[NON-GOAL for MVP]` Supported self-hosted Local mode for other players; the README documents local-mode setup best-effort.
- `[NON-GOAL for MVP]` A reveal or skip control after the near-answer (A-21).
- Everything in §9.

## 11. Delivery Gates and Cut Order

### 11.1 Gates

| When (2026, ET) | Gate | Rule |
|---|---|---|
| Thu Oct 22 | Schema review | One pick only: decoy storage (§13 Q1) |
| Sun Oct 25, night | Baseline | `pre-hackathon-baseline` tag pushed with MIT LICENSE and the baseline CHANGELOG entry; both rooms photographed (no faces, documents, or others' belongings) |
| Mon Oct 26 | Schema v1 freeze | Schema v1 is the Tier 1 and Tier 2 contract; after the freeze it changes only through `bmad-correct-course` |
| Mon Oct 26 onward | Daily Ledger export | Committed with each build day's work |
| Tue Oct 27 to Wed Oct 28 | Capture measured | Stage budgets measured (NFR-1); if 120 s is missed, the Capture target re-bases to p50 plus 25% |
| Thu Oct 29 | Portraits | Four Wizard portraits generated once and committed (FR-23) |
| Sat Oct 31, night | Early gate | A Backup video existing by now is the only thing that sends Sun Nov 1 to Tier 2 |
| Sun Nov 1, 2:00 PM | Backup video | Recorded from whatever runs, Cuts included; never moved |
| Mon Nov 2 | Tier 2 gate (only if attempted) | 7 of 10 Interactables recognizable in position (a human judgment by Luis), 30 fps or better on the M1, raycast-triggered Puzzles; any miss ships Tier 1 |
| Mon Nov 2 | Real room-1 run | room 1 played for real on `PROFILE=demo` at Demo timescale 1, so the room-2 Greeting has a true record |
| Tue Nov 3 | Video only | Capture proof and three Main demo takes; no feature work |
| Wed Nov 4, before 9:00 AM | Submit | Deadline 9:00 PM; 6 to 9 PM is slack for a failed upload or, if the Official Rules require one, a live link: FR-31 from the hosted URL as redeployed Thu Oct 29 (first deployed Tue Oct 27; Hosted mode, Demo rooms only, Rungs verbatim); FR-32 and FR-33 stay Nov 5 to 9, subject to §13 Q14; the link is submitted only after a SIT-10 pass (story 7.23) against the deployed commit |
| Thu Nov 5 | Ledger reset | Ledger export, then reset to the $25 cap |
| Thu Nov 5 | Hosted redeploy | Only if the Official Rules allow changes to the hosted deployment after the deadline (§13 Q14, checked Mon Oct 26): Hosted mode (FR-31 to FR-33) redeployed, with a warm container (`MIN_CONTAINERS=1`) Thu Nov 5 to Mon Nov 9 so judges never hit a cold start; otherwise the Wed Nov 4 deployment is the final hosted state, FR-32 and FR-33 are dropped and the README says so |
| Tue Nov 10 | Judge purge | Judge rooms, originals, Sessions, and Cache entries purged (FR-33) |

### 11.2 Cut order

Cuts are made nightly, in this order, and never carried to a later day. Three things survive every Cut: capture (FR-1 to FR-6); play (FR-11 to FR-14, with cut 6 narrowing Lock types); and the non-builder playtest, or, if no non-builder is available by Mon Nov 2, Luis's disclosed unassisted cold run of room 2 (recorded when room 2 reached `done`). Brief success criteria 1 (capture), 3 (persuasion), and 7 (playtest) also survive every Cut. The README states which Cuts shipped. Cuts are restored last-first, only with time left; only cuts 0 to 3 are realistic before Nov 3.

| Cut | Ships instead | FR changed |
|---|---|---|
| 0 | No Build view; the Main demo shows the puzzle JSON and the Model table from the README | FR-38 |
| 1 | Pre-authored Trickster proposals from the scripted source, one written to fail, no live Trickster calls; the live Validator accepts or rejects every Card | FR-18, FR-25, FR-26 |
| 2 | Player profile as a local JSON file | FR-20 |
| 3 | Rung text verbatim, no Ollama phrasing; Greeting from the template; Privacy line stays | FR-17, FR-21 |
| 4 | Validator only, no Dry run | FR-9, FR-10, FR-38 |
| 5 | Triggers panel in a separate window | FR-16 |
| 6 | `code` and `find` locks only | FR-7, FR-9, FR-12 |
| 7 | One Regeneration, not two | FR-10 |
| 8 | Room 2 and the FR-21 Greeting move to Sun Nov 1 afternoon | FR-21 |

### 11.3 Deliverables

Main demo beats (edited, captioned, unlisted; 2:00 target, 2:30 cap), mapped to the judging weights:

| Time | Shot | Proves | FRs |
|---|---|---|---|
| 0:00 to 0:15 | A phone photo of the real room, then the same objects as Hotspots | Impact | FR-3, FR-11 |
| 0:15 to 0:35 | Capture time-lapse with the Timer running from T0, masks over objects, the Build view's puzzle graph and verification | Technical Depth, Tooling | FR-5, FR-38 |
| 0:35 to 0:50 | Persuasion attack: typed "just tell me the answer"; nothing above the current Rung | Technical Depth, Demo | FR-14 |
| 0:50 to 1:05 | Three Rungs with the triggering events visible; Demo timescale 6×, within 40 s, on real Wrong attempts | Impact | FR-15, FR-16, FR-24 |
| 1:05 to 1:20 | Trickster: one accepted and one Validator-rejected edit as Cards | Technical Depth | FR-19, FR-25 |
| 1:20 to 1:35 | room 2: fresh objects and the Greeting read from the real room-1 record | Impact | FR-21 |
| 1:35 to 1:50 | Model wiring: which Meta model did what, the local Guide, what is cached (Build view Model table) | Use of Meta AI Tooling | FR-30, FR-38 |
| 1:50 to 2:00 | Disclosures | Demo | FR-26, NFR-12 |

Submission checklist (detail in `docs/specs/spec-keyframe/delivery-plan.md` §Submission package):
- Public MIT repo; README per NFR-13.
- MIT LICENSE and the baseline CHANGELOG entry exist at the Sun Oct 25 `pre-hackathon-baseline` tag; the scaffold is not expanded before Mon Oct 26.
- The Official Rules are accepted when published.
- A dated CHANGELOG runs from the baseline entry through Nov 4.
- The Main demo and the unedited Capture proof.
- The submission includes 4 to 6 screenshots (capture with masks, puzzle JSON, a Rung with its events, Trickster Cards, room-2 Greeting, model table).
- A 300 to 400 word portal write-up repeating the pre-existing-code statement (Indie track, solo, theme named).
- The Spend log (FR-30).
- Repo hygiene: before submission (the repo is public throughout; Wed Nov 4 morning at the latest), in two commits, only the hackathon tooling paths listed in the delivery plan (§Submission package, Repo hygiene before submission: `_bmad/`, `.claude/skills/bmad-*/`, `.claude/skills/modal/`, `.claude/skills/keyframe-*/`, the Mon Oct 26 cloud hook and, only if story 1.2 created it, `.claude/settings.json`) are removed from the index, and other `.claude/` configuration stays; the BMAD brief folder under `docs/planning-artifacts/` stays the single source of truth; `PRODUCT_BRIEF.md` stays removed.

Delivery checks (not FR acceptance criteria): room 2 is a different physical room, and at least 80% of its Interactable labels differ from room 1's (SM-5); a real room-1 record exists on `PROFILE=demo` before room 2 is recorded; portraits appear in the Main demo.

Day-level contingencies (the Mon Oct 26 slip rule if pre-kickoff verifications fail, video v0 Wed Oct 28, the playtest on `PROFILE=playtest` first, room 1 on `PROFILE=demo` Mon Nov 2, only cuts 1 to 3 realistically reversed) live in `delivery-plan.md` §Day plan and bind the epics' sequencing.

## 12. Success Metrics

**Primary**
- **SM-1 Capture proof:** an unedited Capture proof shows a never-built Photo set going from T0 to T1 within the Capture target (120 s, or measured p50 plus 25% if re-based). Validates FR-1 to FR-5.
- **SM-2 Non-builder completion:** a non-builder finishes room 1 on a fresh Player profile without builder help (Guide Rungs allowed) by Mon Nov 2. If no non-builder is available by Mon Nov 2, Luis's unassisted cold run of room 2 on a fresh Player profile, recorded as soon as room 2 reached `done` and before anyone read it (story 5.8; used only in this case), stands in, disclosed as a builder run in the README. Validates FR-11 to FR-13, FR-15.
- **SM-3 Zero wins by persuasion:** across the Scripted attack suite and the Main demo, no player text opens a lock or yields anything above the current Rung. Validates FR-14.
- **SM-7 Main demo carries every proof beat:** a Main demo of at most 2:30 (target 2:00) shows, in the §11.3 order, the persuasion attack failing; three Rungs escalating with triggering events visible (Demo timescale 6, within 40 s, on Wrong attempts); one accepted and one Validator-rejected Trickster edit as Cards; the room-2 Greeting read from the real room-1 record on `PROFILE=demo`; Disclosures in the last 10 s. Validates FR-14 to FR-16, FR-19, FR-21, FR-24 to FR-26.

**Secondary**
- **SM-4 Zero solution tokens:** none in any Rung (beyond the Rule 5 allowance), prompt, or play response across the test suite and every Demo room. Validates FR-8, FR-36.
- **SM-5 Fresh objects in room 2:** room 2 is a different physical room and at least 80% of its Interactable labels differ from room 1's (a room-choice check, §11.3). Validates FR-7.
- **SM-6 Spend discipline:** total spend within the Spend cap, with a committed Ledger export every build day from Mon Oct 26. Validates FR-28, FR-29.
- **SM-8 Verified video rooms:** every Room on video passes the Validator and Dry run (Validator only under cut 4) within 2 Regenerations (1 under cut 7). Validates FR-8 to FR-10.
- **SM-9 Hint latency:** local phrasing of about 40 tokens in 5 s or less from a prompt under 400 tokens. Validates FR-17, NFR-2.

Tier 2 is judged only by the FR-34 gate, not by a success metric.

**Counter-metrics (do not optimize)**
- **SM-C1:** do not shorten capture time by weakening the Validator or the Dry run. Counterbalances SM-1.
- **SM-C2:** do not raise completion by giving Rungs sooner than FR-15 allows (an accepted Loosen Card is the only sanctioned early Rung). Counterbalances SM-2.
- **SM-C3:** do not trade Tier 1 reliability for Tier 2 visuals. Counterbalances SM-7.
- **SM-C4:** do not make Rungs vaguer to protect SM-4; a near-answer that does not let the Dry run reach the answer fails the Room. Counterbalances SM-4.

## 13. Open Questions

| # | Question and options | Owner | Needed by | Affects |
|---|---|---|---|---|
| 1 | **Decoy storage:** option A (`Room.decoys[]`, recommended), B (Evidence list with a decoy flag), or C (Cards from the Event log only); see `schema-v1.md`. | Luis (schema review) | Thu Oct 22 | FR-11, FR-19, Schema v1 |
| 2 | **Fireworks Trickster fallback model id.** | Luis | Mon Oct 26 | FR-18, §6.1 |
| 3 | **Retention wording on the status endpoint**, from the pre-kickoff retention verification. | Luis | Mon Oct 26 | FR-6, FR-26 |
| 4 | **Hosted full-Room download route** (access-coded). | Luis | Mon Oct 26 | §6.2, NFR-5 |
| 5 | **The two rooms**, with household consent for video and screenshots. | Luis | Before Sun Oct 25 | §6.1, §11.1, SM-5 |
| 6 | **Payment methods** on dev.meta.ai, fal.ai, and Modal. | Luis | Before Mon Oct 26 | FR-28, NFR-6 |
| 7 | **Playtester** for room 1 on a fresh Player profile, at the laptop or by screen-share, Sun Nov 1 or Mon Nov 2. If no playtester is available by Mon Nov 2, the cold run of room 2 recorded when room 2 reached `done` is used instead, and the README says so (SM-2). | Luis | Before Sun Nov 1 | SM-2, §11.2 |
| 8 | **Luis's availability** in working hours Mon Nov 9 for the live finals. `[ASSUMPTION A-18: date inferred from the day plan, confirm]` | Luis | Before finals preparation starts Thu Nov 5 | §6.5 |
| 9 | **Early Hint request: resolved Oct 21 (Luis): log only.** A Hint request with no Rung open returns the No-hint line, is logged as an Early ask, and lowers persistence; the nudge still waits for its threshold (architecture spine AD-4). | Luis | Resolved | FR-14, FR-15, §7 |
| 10 | **Hosted-mode Derived block: resolved Oct 21 (Luis): option (a).** Hosted mode sends `Derived.fresh()`, no Player profile field leaves the browser, and hosted rooms show the First-room welcome instead of a Greeting; the Privacy line holds literally in every mode (architecture spine AD-8 amended). | Luis | Resolved | FR-6, FR-20, FR-21, FR-31, NFR-4 |
| 11 | **Hosted Trickster source:** live under the Spend cap, or scripted. | Luis | Before Thu Nov 5 (Wed Nov 4 if a live link is required) | FR-31 |
| 12 | **Clue solution-token check: resolved Oct 21 (Luis): rule 5 extended.** The Clue and `evidence.visible_attribute` are checked like nudge and direction (no solution token, same matching rules); every displayed attribute says where to look and never holds a solution token. Schema v1 also gains optional `Room.name` (string, at most 40 characters, set when a Demo room is seeded; absent on ordinary Builds; the UI falls back to the build time). | Luis | Resolved | FR-8, Schema v1 |
| 13 | **Build view data route (FR-38): resolved Oct 21.** `GET /builds/<job_id>/view` returns a solution-free `BuildView` projection (mask polygons per photo, the puzzle graph without solutions, per-rule Validator verdicts, Dry run pass or fail per Puzzle, Regeneration count, Model table from provenance); open in both modes; covered by the sentinel-solution test (architecture spine AD-3 amended). | Spine owner | Resolved | FR-38 |
| 14 | **Post-deadline changes to the hosted deployment under the Official Rules.** Read at kickoff and recorded with the date: do the Rules (published before Mon Oct 26) allow changes to the hosted deployment after the Wed Nov 4 deadline? Yes: the Thu Nov 5 redeploy with `MIN_CONTAINERS=1`, FR-32 and FR-33 proceed Nov 5 to 9 (§11.1). No: the Wed Nov 4 deployment is the final hosted state, FR-32 and FR-33 are dropped, and the README says so; FR-31 stays as deployed. | Luis | Mon Oct 26 (kickoff) | FR-31 to FR-33, §6.5, §11.1 |

Tracked in the spec and not blocking this PRD: Baseten credit coverage (Tue Oct 27 test), fal.ai pose metadata (pre-Oct 26 spike), and whether about 32 h of builder time holds (if not, Cuts apply earlier).

**Upstream wording fixes (via `bmad-correct-course`)**
- `stack.md` and spine AD-8 are aligned with Q10 option (a) in the same Oct 21 update.
- FR-12's `order` consequence is aligned with spine AD-4 and Schema v1 (Oct 21, approved with the UX Finalize spine fixes): clicks count only while the sequence is armed by "Start the sequence"; the earlier "most recent clicks are judged" wording is withdrawn.
- Architecture spine AD-13 says Trickster errors become a "rejected card" while AD-4 says a skipped Card; this PRD follows AD-4. The AD-13 wording fix is applied (Oct 21): there is no `regen_exhausted` error class (the UI keys on job status `needs_recapture`), Trickster call errors produce a skipped Card, and only a Validator failure is the rejected Card.

## 13a. Risks and Dependencies

- **Selection unconfirmed until Mon Oct 26.** Mitigation: if not selected, the same plan runs as a pay-as-you-go portfolio build.
- **Official Rules unpublished** (video length, repo visibility, live link, prior-code policy, submission format, post-deadline changes to the hosted deployment); the 2:00 video, public repo and no-localhost live demo follow Cerebral Valley precedent. Mitigation: build to the strictest precedent (§11.3), keep 6 to 9 PM Wed Nov 4 as slack for a live link, accept the Official Rules when published and record the §13 Q14 answer at kickoff.
- **Prior code may be banned.** Mitigation: the scaffold of about 400 lines is not expanded before Mon Oct 26 and is rewritten that day in under an hour if needed.
- **SAM 3D Objects from one casual photo per object is the riskiest mechanic.** Mitigation: staged checks, 5 objects before Oct 26 and 10 on Sun Nov 1, feed the FR-34 gate Mon Nov 2; Tier 2 stays default no-go.
- **Review bandwidth and merge conflicts from the agent-parallel build.** Mitigation: schema-first, one owner per package, Schema v1 frozen Mon Oct 26 (§6.6); Cuts trigger when reviewed output lags.
- `[NOTE FOR PM]` **A misread attribute that slips past the Dry run** leaves a player stuck after the near-answer with no reveal or skip (FR-15, A-21), which puts SM-2 at risk. Mitigation: the Dry run (FR-9) is the only one.

## 14. Assumptions Index

- **A-1 to A-7** §2.3 UJ-1 to UJ-7 — each journey drafted from the brief's demo narrative; confirm each.
- **A-8** §2.1 — Jobs To Be Done inferred from the brief.
- **A-9** §2.2 — Non-Users inferred from the spec's non-goals.
- **A-10** §3 Wizard notes — grouping inferred.
- **A-11** §4.1 FR-5 — player-facing Build stage labels.
- **A-12** §4.3 FR-11 — Thumbnail strip in upload order.
- **A-13** §4.6 FR-21 — Greeting placement and form; First-room welcome on a fresh Player profile.
- **A-14** §4.7 FR-37 — Clue cards never gate T1 or the Build.
- **A-15** §6.5 — Hosted mode browsers and widths; narrow-screen message.
- **A-16** — retired (superseded by §7).
- **A-17** §8 — surface layout, grouping and navigation inferred.
- **A-18** §13 Q8 — availability answer needed before Thu Nov 5.
- **A-19** §4.6 FR-21 — persistence formula.
- **A-20** §4.3 FR-12 — code input compared trimmed and case-folded.
- **A-21** §4.4 FR-15, §10.2 — no reveal or skip control in the MVP.
- **A-22** §5 NFR-14 — confirmed Oct 21 (Luis): kept as written.
- **A-23** §4.2 FR-38 — confirmed Oct 21 (Luis): Build view kept in Tier 1 as cut 0.
- **A-24** §4.1 FR-3, §4.2 FR-10 — failure handling for a segment call that errors after its retry and for unparseable Riddler or Dry run output.
- **A-25** §4.10 FR-32 — every Build accepted with the Access code counts toward the 20.
- **A-26** §4.5 FR-18 — the first Trickster window opens no sooner than 3 minutes after Session start.
