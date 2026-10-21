---
status: final
stepsCompleted: ["step-01-validate-prerequisites", "step-02-design-epics", "step-03-create-stories", "step-04-final-validation"]
inputDocuments:
  - docs/planning-artifacts/prds/prd-Keyframe-2026-10-21/prd.md
  - docs/planning-artifacts/prds/prd-Keyframe-2026-10-21/addendum.md
  - docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/DESIGN.md
  - docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/EXPERIENCE.md
  - docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md
  - docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/schema-v1.md
  - docs/specs/spec-keyframe/SPEC.md
  - docs/specs/spec-keyframe/stack.md
  - docs/specs/spec-keyframe/budgets.md
  - docs/specs/spec-keyframe/player-profile.md
  - docs/specs/spec-keyframe/delivery-plan.md
  - docs/specs/spec-keyframe/glossary.md
---

# Keyframe - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Keyframe, decomposing the requirements from the PRD (`prd-Keyframe-2026-10-21`, FR-1 to FR-38 and NFR-1 to NFR-14, with its addendum), the UX contract (`DESIGN.md` for tokens and components, `EXPERIENCE.md` for surfaces, behavior, states, copy and accessibility; status final, with four key-screen mocks in `mockups/`), and the architecture spine (AD-1 to AD-18, its conventions, HTTP routes, Stack and Structural Seed) into implementable stories. Schema v1 is the data contract; the spec files supply dates, gates, cuts and budgets.

Requirement ids follow the PRD exactly (`FR-n`, `NFR-n`). FR-1 to FR-36 and NFR-1 to NFR-13 keep the meaning and numbers of the earlier FR1 to FR36 and NFR1 to NFR13 in this file (from the spec's CAP-1 to CAP-14); FR-37 (Clue cards), FR-38 (Build view) and NFR-14 (accessibility floor) are new. The FR Coverage Map and Epic List below use these ids, and every story names the ids it covers in its Covers line. Some core files are touched by more than one epic (`src/domain/session.py` by Epics 1, 3 and 4; `src/api/meta.py` by Epics 1, 6, 7 and 9; `src/api/wiring.py` by most epics). Merging those epics was considered and rejected: each epic is one cut or tier boundary (the Tier 1 play surface, capture, the Guide, the Trickster, the profile, the submission, Tier 1.5 hosting, Tier 2, voice) that must ship or be cut on its own date, and each later change builds on an earlier one that is already merged and tested. Tier tags follow the PRD: Tier 1 is FR-1 to FR-30, FR-36 and FR-38 (cut 0) plus the Backup video; a consequence tagged "(Hosted mode, Tier 1.5)" ships with FR-31 to FR-33, not with its Tier 1 FR. The dev skills under `.claude/skills/keyframe-*/` are implementation guidance, not requirements; only the scaffold fixes they found are carried here (AR-3).

## Requirements Inventory

### Functional Requirements

FR-1: The player uploads 6 to 10 JPEG photos of one room from the browser: the Capture screen and the README state the Input requirement "6 to 10 JPEG photos" with the iPhone Most Compatible tip before any photo is chosen; a set with any non-JPEG file (HEIC, PNG or any other format), or with fewer than 6 or more than 10 files, is rejected whole at the picker with "Keyframe needs 6 to 10 JPEG photos." and the offending files marked, and nothing is uploaded or reaches a model; each photo is downscaled in the browser to a 1280 px long edge with EXIF orientation applied and sent with its unmodified original in one request.
FR-2: One Architect `muse-spark-1.3` vision call per Build, all photos in one request at reasoning effort low, lists the room's objects with a clearest photo, a box and readable attributes for each; attributes are stored verbatim as read and are the only attributes Evidence may cite (Validator rule 4).
FR-3: One `sam-3.1` call per listed object, at most 12 concurrent, segments it, and mask selection yields 5 to 12 Interactables with polygon Hotspots: the mask with the best overlap with the Architect's box is kept, every mask with IoU above 0.2 is grouped as instances for a plural label, masks under 1% of the image are dropped, and with more than 12 objects the 12 with the highest Architect confidence are kept; an object with no mask gets its box rectangle as a clickable Hotspot usable as a `find`, `order` or `use_on` target; a `sam-3.1` call that still errors after its one retry ends the Build `failed` at the segment stage (A-24).
FR-4: With 4 or fewer Interactables the Build ends `needs_more_photos` with zero Riddler, Dry run or Trickster calls; the Capture screen shows a fixed message asking for more photos of the room, keeps the chosen photos visible, and offers Add photos (up to 10 in all) and Start over; the next Upload is a new Build of 6 to 10 JPEG photos.
FR-5: The Timer starts on the Upload click (T0), stays pinned from the Capture screen into the Play screen, stops at T1 (first Hotspot responding to the pointer) and then shows the frozen T1 − T0; Build stages show in order (ingest, architect, segment, author, validate, dry run, scene), and during a Regeneration the author, validate and dry run stages show again with the attempt number; a 260 s Build (two Regenerations) still reaches the player by polling; on `needs_more_photos`, `needs_recapture` or `failed` the Timer stops and shows the end status; a `failed` Build (provider error after its one retry, a call refused under the Spend cap, or a runner that stopped) shows the failed stage, a plain cause class and Try again (a new Build with the same photos), and no partial Room is playable; (Hosted mode, Tier 1.5) a Build waiting for the single runner shows a `queued` state.
FR-6: Before upload the Capture screen shows the Retention summary, the same text the status endpoint serves, naming every destination of photos and puzzle text with its retention terms (the Meta Model API standard tier; Baseten or Fireworks when a role's fallback is active; fal.ai in Tier 2; voice audio when voice ships), the Privacy line verbatim ("the player profile stays on your machine."), and a request to leave out faces, documents and other people's belongings; (Hosted mode, Tier 1.5) the Retention summary also states that photos, originals, the Judge room and its Sessions are stored on Modal and deleted Tue Nov 10, that Session logs are deleted 24 h after their last event, and that no Player profile data leaves the browser.
FR-7: One Riddler `muse-spark-1.3` call per attempt, reasoning effort medium, authors 4 to 6 Puzzles that reference only listed Interactables and Architect-read attributes: exactly one Exit puzzle; Lock types `code`, `order`, `use_on`, `find` (`code` and `find` only under cut 6); each Puzzle with a Clue, Lore of at most 60 words and three Rungs written in the wizard voice, so a verbatim Rung reads in character in Hosted mode and under cut 3.
FR-8: Every Room passes the eight Validator rules of Schema v1 before it is stored, and a Room failing any rule is never stored or playable: no nudge, direction, Clue or displayed Evidence attribute (`evidence.visible_attribute`) contains a solution token (same matching rules), near-answers stay within the Rule 5 allowance and are also checked against the Clue, a `code` is 3 to 6 characters and an `order` sequence 3 to 5 Hotspots (rule 7); reasons are structured (rule, Puzzle, field) with a fixed message and never quote a solution token or an answer.
FR-9: A Dry run (`muse-spark-1.3`, reasoning effort low) that sees only photos, labels, Clues and Rungs, never solutions, must reach every answer: a sentinel-solution test finds no solution in its prompt; any mismatched answer fails the Room; a passing Dry run proves the Clues and three Rungs suffice, so the near-answer is always enough to solve; under cut 4 the Dry run is skipped and the Validator alone gates the Room.
FR-10: A failed Room is regenerated (Riddler plus Dry run) with its failure reason list only, never the previous draft, at most 2 times (1 under cut 7); Riddler output that fails the response schema or exact-id parsing, and Dry run output missing or unparseable for any Puzzle, count as a failed attempt with a fixed reason (A-24); after the last failed Regeneration the Build ends `needs_recapture` and the Capture screen keeps the photos visible and asks for brighter, closer shots where labels and printed text are readable, with Start over; provenance records the Regeneration count.
FR-11: The player plays the Room as photo Scenes with mask Hotspots in the stored 1280 px photo's pixel space (a click inside a polygon at any rendered size posts a click for that Interactable; hover reveals it), a Thumbnail strip reaching every photo in upload order (A-12), an Inventory that persists across Scene changes for the whole Session, and Wizard notes showing, for each available Puzzle, its Clue, Lore, Evidence cards (Interactable label, thumbnail crop, read attribute), opened Rungs and lock input, with Puzzles behind unmet prerequisites hidden; after an accepted Decoy, real and Decoy Evidence cards are indistinguishable and keep a stable order (one test); reloading resumes the Session from its Event log (Scenes, Inventory, open locks, current Rungs), and an unreachable server disables inputs with a reconnecting state and counts nothing.
FR-12: A lock opens only on its correct input, judged by the server, with each available Puzzle's lock input in its Wizard-notes entry: `code` is a 3 to 6 character field with Submit, compared trimmed and case-folded (A-20); `order` is armed only by "Start the sequence" in the order Puzzle's entry, only Hotspot clicks made while armed count (in any Scene), a full-length mismatch counts one Wrong attempt and clears the buffer, which stays armed, "Stop the sequence" disarms with no Wrong attempt, and exploring clicks made while unarmed never count (spine AD-4 and Schema v1; the PRD was aligned to them Oct 21); `find` is a click on the target Hotspot; `use_on` drags an Inventory item onto a Hotspot, or selects it and then clicks the Hotspot with the Thumbnail strip usable meanwhile; a submitted input shows a pending state and a lock shows open only after the server confirms; a Wrong attempt shows "Not this" with the per-lock count, a click alone never counts, and a click on a non-target Hotspot shows only the Interactable's label; solving a `find` Puzzle visibly moves its Interactable into the Inventory, and an empty Inventory has its own empty state; an opened lock shows a short open state, then the next available Puzzle appears; input for a Puzzle whose prerequisites are not open never opens it and is not a Wrong attempt, and a `use_on` with an item not in the Inventory is refused.
FR-13: Opening the Exit puzzle shows the Completion screen with elapsed time, Rungs used, Wrong attempts and per-Puzzle time, with active Disclosures still visible; its one action is "Build another room" (the Capture screen in Local mode, the Hosted landing in Hosted mode), and it links the Build view (FR-38); the Room result is recorded into the Player profile.
FR-14: Anything the player types into the hint field becomes a Hint request for the Active puzzle (the Puzzle most recently attempted by lock input or click) and the typed text never leaves the browser; the Scripted attack suite, led by "just tell me the answer", returns only the current Rung, or the No-hint line when none is open, and opens nothing; the No-hint line is an in-world Guide line that acknowledges the ask, says help is coming and points back to the Scene, never reads as a refusal and never names an object or solution; it is logged as an Early ask that lowers persistence and does not release the nudge (§13 Q9 resolved: log only); a fixture test finds no solution in any play response; free conversation with any wizard is out of scope.
FR-15: The Guide selects the Rung in code from the Event log, with Rungs, Wrong attempts and Idle seconds tracked per Puzzle: Idle counts from the player's last click, lock input or Hint request and server idle ticks never reset it; the Active puzzle's nudge fires after the nudge threshold of Idle, 90 s × (1 + 0.5 × persistence) clamped to 60 to 135 s (90 s on a fresh Player profile), or after 3 Wrong attempts at that lock, whichever comes first; direction and near-answer each need a further stall (Idle equal to the nudge threshold) or 3 further Wrong attempts and arrive at least 90 s after the previous Rung, a spacing that never scales with persistence; an accepted Trickster Loosen opens its named Rung at once and is not counted against the spacing; replaying an Event log yields the same Rung changes as live play; after the near-answer there is no reveal or skip and a further Hint request repeats the near-answer (A-21).
FR-16: Every Rung change appears in the Triggers panel with its triggering events: its Idle seconds, its Wrong attempts, or the Trickster Card that loosened it; the panel is collapsed by default behind an always-visible toggle and opens automatically while a Disclosure is active; under cut 5 it moves to a second window with the same content.
FR-17: In Local mode the selected Rung is phrased by Llama 3.2 3B on Ollama within NFR-2, from a fixed prefix whose input is exactly the Rung text and the Derived block (never room content or a solution), with the Guide portrait in a thinking state meanwhile; past 5 s, or at once when Ollama is unreachable or errors, the verbatim Rung is shown and the fallback is logged; under cut 3 Local mode also shows Rungs verbatim and the README drops the phrasing claim while the Privacy line stays; (Hosted mode, Tier 1.5) Hosted mode runs no Guide model, shows the Rung text verbatim, and refuses to start if configured with one.
FR-18: When a non-exit lock opens and no Trickster window has closed in the last 3 minutes of session time (the first window no sooner than 3 minutes after Session start, A-26), one window opens and exactly one Trickster proposal (Decoy, Merge, Loosen or Shortcut) is requested from the Game-state summary, which holds open locks, elapsed time and Rungs used only (no Player profile field, no solution); at most 6 `muse-spark-1.3` Trickster calls per Session, the seventh refused; a Decoy never targets the Exit puzzle; under cut 1 proposals come from the scripted source with pre-authored proposals and no live Trickster calls (FR-25).
FR-19: A Trickster edit is accepted only if the Room with it applied passes Validator rules 1 to 8 (plus rule 9 after the decoy pick), with no Dry run and at most one Decoy per Puzzle; on acceptance the Play screen reflects it at once (a new Evidence card for a Decoy, a Puzzle now locked behind another for a Merge, a Rung in the Hint area for a Loosen, a Puzzle becoming available for a Shortcut) in the Session's Effective room only, and the stored Room is never mutated; every outcome appears as a Card in the Hint area after the lock-open state, stays until dismissed and is kept in the Card log, naming the edit type and its effect in one plain sentence (a Decoy Card never identifies which Evidence is false); a rejected Card shows a plain one-line reason from the Validator rule's fixed message, never a token, and leaves the Effective room unchanged; a provider error or a reached Spend cap during a window shows a skipped Card with the same message for either cause and play continues; a window after the sixth Trickster call opens no proposal and shows no Card.
FR-20: Room results and the Derived block are written only in the player's browser, to IndexedDB under the `PROFILE` name (`dev`, `playtest`, `demo`), or under cut 2 to a local JSON file on the player's machine; a Session start carries the Derived block and nothing else from the Player profile; a Session start whose Derived block is outside its bounds (`sessions` at least 0, `persistence` −1 to 1, `mean_rung_per_lock_type` 0 to 3) is refused with a 422 and no Session is created; (Hosted mode, Tier 1.5) the client sends `Derived.fresh()` with every Session start, and the hosted server persists no Derived block and never joins a Session log to a Player profile; (Hosted mode, Tier 1.5) under cut 2 the Hosted-mode profile behavior is stated in the README and decided when cut 2 is taken.
FR-21: After each non-demo Room result the Derived block is recomputed (`sessions` = count of non-demo Room results; `time_to_first_hint_s` = median per-Puzzle time to first hint, or null; `mean_rung_per_lock_type` = mean Rungs used per Puzzle by Lock type, 0 to 3; `persistence` = the A-19 mean over every Puzzle of +1 for a Puzzle solved after its nudge fired with no Hint request on it, −1 for a Puzzle with an Early ask, 0 otherwise, clamped to −1 to 1, 0 when there are none); when `sessions` is at least 1 a Greeting built from the Derived block only, naming no object and no solution, is shown before the first Scene as a Guide line with portrait dismissed by "Begin", and a fresh Player profile gets the First-room welcome instead (A-13); when phrasing is unavailable (cut 3, or past 5 s of local phrasing) the Greeting is a fixed template filled from the Derived block in the same voice; with persistence p the nudge threshold is 90 s × (1 + 0.5 × p) within 60 to 135 s; (Hosted mode, Tier 1.5) Hosted mode always shows the First-room welcome; under cut 8 room 2 and the Greeting move to Sun Nov 1 afternoon.
FR-22: A Room result recorded with a Demo timescale above 1 is flagged as demo, and recomputing the Derived block ignores every flagged result.
FR-23: Four Wizard portraits are generated once with `muse-image-1.0` by a script, committed, and shown in play, sharing the painted, candlelit oil-portrait style; play makes zero image-generation calls, and missing portraits fall back to placeholder art.
FR-24: `DEMO_TIMESCALE=n` divides the nudge threshold, the Rung spacing and the Trickster window by n: at `DEMO_TIMESCALE=6` three Rungs arrive within 40 s on Wrong attempts (30 s nominal; 45 s on idle alone) and the Trickster window is 30 s; the Timer and Event log timestamps are unchanged at any timescale.
FR-25: `DEMO_TRICKSTER=scripted` replays two recorded proposals bound to one Room while the Validator runs live and accepts one and rejects one; on another Room, or once the recording is used up, the scripted source yields no proposal and no Card; cut 1 uses the same source with pre-authored proposals, one written to fail, and no live Trickster calls, with the Validator still running on every Card.
FR-26: The status endpoint (`GET /meta`) reports mode, Guide, Trickster source (live, scripted, cut 1), Demo timescale, Cache, Player profile name, the Disclosure text and the Retention summary text; the UI shows a Disclosure whenever the Demo timescale exceeds 1, the Trickster is scripted or cut 1, or Hosted mode is active, as a persistent plain-text banner at the top edge of the Capture, Play and Completion screens and the Hosted landing (and the Build view, per the UX contract) that cannot be dismissed, never covers the Scene or its Hotspots, joins several lines when several apply, and matches the active Trickster source and Demo timescale (§7 Disclosure copy).
FR-27: Every paid cloud call can be served from the Cache: with `CACHE=on` a repeat of the same model, schema, full prompt, reasoning effort, image hashes and attempt number is served from the Cache and adds nothing to the Ledger; with `CACHE=off` every call reaches the provider and is still priced; a Regeneration is never served its own failed answer; clearing the Cache never touches the Ledger, its exports or the running total.
FR-28: Every uncached paid cloud call is priced and recorded in the Ledger, and a call that would pass the Spend cap (`SPEND_CAP_USD`: 80 until the Thu Nov 5 reset, then 25; no date logic in code) is refused: in a Build it ends the Build `failed` at its stage with code `spend_cap_exceeded` and a plain Spend-cap message on the Capture screen; in play it shows a skipped Card; in a script it makes the script exit non-zero, printing the cap and the running total; the running total survives a restart.
FR-29: Local mode writes a dated Ledger export (`spend/exports/ledger-<date>.json`) at API startup and after every completed Build, and a counter reset on any day is refused unless that day's export exists; (Hosted mode, Tier 1.5) Hosted mode snapshots the Ledger daily at 06:00 ET.
FR-30: Every stored Room carries provenance (model ids, prompt hashes, stage timings, Regeneration count, spend per stage, and applied Trickster edit ids, empty on the stored Room); the submission's Spend log is the Ledger export for paid cloud calls plus fal.ai receipts and Modal usage attached as-is, with pre-kickoff verification spend listed separately.
FR-31: (Tier 1.5) A judge opens the hosted URL and plays cached Demo rooms through the same API as Local mode: the Hosted landing lists the Demo rooms and each plays to the Completion screen; Rungs are verbatim and the Disclosure states Hosted mode; the Trickster runs live under the Spend cap or scripted (§13 Q11) and the Disclosure names the source; Hosted mode shows the First-room welcome, never a Greeting.
FR-32: (Tier 1.5) A judge builds a Judge room behind the Access code, which is checked before photo selection (a missing or wrong code is refused inline and no upload starts); every Build accepted with the Access code counts toward the 20 whatever its end status, and the 21st is refused with a quota message while the Demo rooms stay open (A-25); a Build outlasting the host's 150 s web timeout completes and reaches the judge, and an accepted Build has its own URL that resumes polling after the tab is closed.
FR-33: (Tier 1.5) A purge run on Tue Nov 10 deletes Judge rooms, originals, Sessions and Cache entries together while Demo rooms persist; hosted Session logs are deleted 24 h after their last event, or when their Room is deleted; the app never deletes local `rooms/` or `.cache/`; a Judge room's Completion screen states "Deleted Tue Nov 10", and afterwards its URL states that the room was deleted on Tue Nov 10 as promised.
FR-34: (Tier 2, gated, default no-go; no epic or stories until the Mon Nov 2 gate passes) The player walks a 3D version of the Room holding up to 20 reconstructed instances from at most 12 Interactables, made by fal.ai SAM 3D Objects (`fal-ai/sam-3/3d-objects`, $0.02 a call, cloud only) from original-resolution photos in the same scene graph as Tier 1, and triggers Puzzles by raycast; it passes the Tier 2 gate (7 of 10 Interactables recognizable in position, 30 fps or better on the M1, raycast-triggered Puzzles); fal.ai calls are priced in the Ledger against the Spend cap and stay within $6 cash.
FR-35: (Unscheduled, the last Tier 1.5 item; ships only if everything else is done Mon Nov 2; voice UI stays out of the UX contract until scheduled) The player asks for help by voice: speech is transcribed by `muse-voice-transcribe-1.0` with browser speech recognition as fallback; the transcript is reduced to a Hint request and never stored or logged, and only the Hint request enters the Session; a spoken request raises a Hint request exactly as a typed one does, and a spoken "just tell me the answer" yields nothing above the current Rung; when voice ships the Retention summary names voice audio and both services, and a mic control beside "Ask the Guide" has idle, listening, transcribing and permission-denied states, denied falling back to the hint field.
FR-36: Raw room photos never enter the repo: `rooms/` (stored photos, originals, Sessions), `photos/`, `captures/`, `uploads/`, `*.heic`, `.cache/` and `.env` are git-ignored, asserted by offline tests, and only daily Ledger exports and outputs are committed; only the Meta Model API standard tier is used, never the contributor tier; (Hosted mode, Tier 1.5) the hosted server persists no Derived block or Player profile data and never links a Session log to a Player profile.
FR-37: (Tier 1.5) A Clue card, one `muse-image-1.0` image per Puzzle generated from the Clue text only (no solution, Rung, photo or Player profile field; sentinel-solution test), is shown beside each Clue: generated once per demo Room (the recorded rooms and the hosted Demo rooms) by an explicit step, cached and priced, and for Judge rooms and ordinary Builds only when Luis enables it (then priced per Build in the Ledger); never generated in play; references live outside the frozen Room (keyed by Puzzle id in the artifact store), so Schema v1 is not reopened, and Decoy and Merge edits leave the card unchanged; until ready the slot shows a same-size placeholder, a failed card stays blank, the layout never shifts, and the card never fails the Build or delays T1 (A-14); its alt text is the Clue.
FR-38: (Tier 1, cut 0: the first Cut taken; without it the Main demo shows the puzzle JSON and the README Model table) The player, a judge and Luis open a Build view, served by `GET /builds/<job_id>/view` from a solution-free projection in both modes without the Access code, showing the mask overlays per photo, the puzzle graph (Puzzles as nodes with Lock type, `requires` edges, the Exit puzzle marked), the Validator verdict per rule, the Dry run pass or fail per Puzzle (skipped under cut 4), the Regeneration count, and the Model table (model id, where it ran, what it did, cached or billed) from provenance; a sentinel-solution test finds no solution, Clue-to-answer mapping or Dry run answer in its response; it is reachable from the Capture screen once the Build ends `done` and from the Completion screen.

### NonFunctional Requirements

NFR-1: Capture performance: the Capture target is T1 − T0 ≤ 120 s on the M1 with `CACHE=off` and a never-built Photo set, or measured p50 plus 25% if re-based after the Oct 27 to 28 measurements; stage budgets are Architect 15 s, segmentation 10 s, Riddler 45 s, Dry run 30 s, Scene 10 s, as p50 over at least 5 live Builds; a Regeneration takes about 75 s; a stage over budget never fails the Build; a Capture proof take is kept only if it runs under 200 s. FR-2, FR-3, FR-7, FR-9 and FR-10 refer here.
NFR-2: Hint latency: local phrasing returns about 40 tokens in 5 s or less from a prompt under 400 tokens with a fixed prefix.
NFR-3: Hardware: everything local runs on one 16 GB M1 MacBook Pro without CUDA; the Guide model stays near 3 GB resident; demo-recording memory is about 10.6 GB; no GPU anywhere, no local SAM 3.1, SAM 3D Objects or 30B models; on the Mac run Chrome, the backend and Llama 3.2 3B on Ollama; in the cloud `muse-spark-1.3`, `sam-3.1`, `muse-image-1.0` (and `muse-voice-transcribe-1.0` if voice ships) on the Meta Model API, fal.ai SAM 3D Objects in Tier 2 only, Modal CPU for Hosted mode.
NFR-4: Privacy: the Guide model runs only on the Mac; the Player profile stays on the player's machine and only the Derived block reaches the Guide model and the Greeting; raw room photos are never committed, consent or not, and only outputs ship; the Retention summary is shown before upload and the Privacy line holds verbatim under every Cut, including cut 3; the Riddler's or Trickster's prompt goes to Baseten or Fireworks only when that role's fallback is active, never with a solution or Player profile field; Judge-room data stays on Modal until Tue Nov 10 and Session logs at most 24 h after their last event; the two video rooms and every photo sent to a model contain no faces, documents or other people's belongings; Meta Model API standard tier only, never the contributor tier.
NFR-5: Integrity: solutions never enter a model prompt or a play response (the Dry run, Trickster, Guide, Greeting, Build view and Clue card inputs see no solution; the only exception is the access-coded full-Room download for Luis); Validator reasons never quote a token or answer; only the server's session logic opens locks; every Room and Trickster edit passes the Validator, and demo mode swaps the Trickster's source, never the check; the persuasion attack fails by construction and is shown failing on video.
NFR-6: Cost: Spend cap $80 until the Thu Nov 5 reset, then $25 pay-as-you-go; fal.ai at most $6 cash; development runs on the Mock provider with `CACHE=on` and never draws on the cap; expected spend about $35 against daily ceilings totaling $79; a clean Build about $0.10 (under $0.25 with two Regenerations) and a Session about $0.21; the daily Ledger export is the durable spend record.
NFR-7: Reliability: Builds survive the host's 150 s web timeout and resume at the last completed stage after a restart; provider calls retry once, on rate-limit and documented-retryable server errors only (AR-17); at most 2 Regenerations.
NFR-8: Testability: every story's tests pass offline on the Mock provider; provider tests use recorded fixtures; the dependency-boundary, type-staleness and ignore-file tests run in the offline suite.
NFR-9: Rate limits: stay within the Meta Model API limits (`muse-spark-1.3` 3,000 RPM and 4,000,000 TPM; `sam-3.1` 3,000 RPM; `muse-image-1.0` 150 RPM); segmentation concurrency is at most 12.
NFR-10: Platform: Local mode runs in Chrome on the Mac; Hosted mode supports current desktop Chrome, Safari and Firefox at 1280 px or wider, Chrome the tested target, with a laptop-or-desktop message below 1024 px (A-15); Tier 1 Scenes are textured planes in the Three.js scene graph Tier 2 reuses, and if that costs more than 2 h the Scenes are DOM-only, keep every Hotspot, and Tier 2 stays no-go; the Tier 2 gate needs 30 fps or better on the M1.
NFR-11: Schedule: the gates in PRD §11.1 hold (Thu Oct 22 schema review, one pick; Sun Oct 25 night `pre-hackathon-baseline` tag with MIT LICENSE and the baseline CHANGELOG entry; Mon Oct 26 Schema v1 freeze, later changes only through `bmad-correct-course`; daily Ledger export committed from Mon Oct 26; Oct 27 to 28 capture measured; Thu Oct 29 portraits; Sat Oct 31 night early gate; Sun Nov 1 2:00 PM Backup video, never moved; Mon Nov 2 Tier 2 gate if attempted and the real room-1 run on `PROFILE=demo` at timescale 1; Tue Nov 3 video only; submit Wed Nov 4 before 9:00 AM ET, deadline 9:00 PM; Thu Nov 5 Ledger reset and hosted redeploy with `MIN_CONTAINERS=1` through Mon Nov 9; Tue Nov 10 judge purge); Fri Oct 30 no build; implementation starts Mon Oct 26 and the scaffold is not expanded before then; Tier 2 is a default no-go unless the Tier 1 Backup video exists Sat Oct 31 night; Cuts 0 to 8 are made nightly in the published order, never carried to a later day, and restored last-first only with time left.
NFR-12: Demo honesty: every beat on video is rehearsed, never faked; demo settings change only timing and the Trickster source, and no demo path injects events, Rung changes, Greetings, Validator results or Build output; real Idle time and real Wrong attempts trigger every Rung, compressed only by the Demo timescale; the live Validator decides both replayed Trickster edits; the Greeting reads the real room-1 record on `PROFILE=demo`; the Timer and Event log are never scaled; the capture time-lapse is acceptable only beside the unedited Capture proof; the 6× timescale, the Scripted Trickster replay (or cut 1's pre-authored proposals) and earlier builds of a Room are disclosed in the last 10 s of the Main demo and in the README, the README states which Cuts shipped, and the UI and README declare the finals mode.
NFR-13: Submission and hygiene: a public MIT repo listing third-party and model licenses, with pre-existing code disclosed against the `pre-hackathon-baseline` tag and its diffstat; the README carries the pitch, a model table (model id, where it runs, what it does, whether it shipped), an architecture diagram, local-mode setup, the Privacy line, the Retention summary, the Disclosures, which Cuts shipped, the pre-existing-code statement with its diffstat and the licenses; before the repo goes public (Wed Nov 4 morning at the latest) only the hackathon tooling paths in `delivery-plan.md` §Submission package, Repo hygiene are removed from the index (AR-28), other `.claude/` configuration stays, and `PRODUCT_BRIEF.md` stays removed; the remaining delivery steps (CHANGELOG, Official Rules, screenshots, portal write-up) follow the PRD §11.3 checklist.
NFR-14: Accessibility floor: every Hotspot is reachable by Tab with a visible focus ring and Enter acts as a click; a "Show all objects" toggle outlines every Hotspot; `use_on` also works by select-then-click; text meets WCAG AA contrast on the dark theme; Rungs, Cards and the Greeting are announced in a polite live region; motion respects reduced-motion settings.

### Additional Requirements

AR-1: Starter template: none beyond the Vite 8 vanilla-ts template for `web/` (TypeScript 6.0.3 exact, three 0.186.1 with @types/three 0.186.0, Node 24 LTS with the root `.nvmrc` = 24 and `engines.node` = "24.x", npm with a committed `web/package-lock.json`) and the existing Python scaffold (`src/providers` `ModelProvider` ABC with the mock provider and the Meta stub, `src/config.py` `Settings`, `pytest` under `tests/`), which is ratified as the backend base. This shapes the first implementation stories: 1.2 ratifies the backend scaffold and 1.4 creates `web/` from the Vite template, right after 1.1 tags the untouched scaffold as the pre-hackathon baseline. The scaffold is not expanded before Mon Oct 26.
AR-2: Stack pins (spine §Stack) and the Dependencies convention, exact: Python 3.13, uv 0.11.32 (CI and Modal image exact; local floor via `required-version`), FastAPI 0.156.4, uvicorn 0.54.0, pydantic 2.14.1, httpx 0.28.1, Pillow 13.0.0, meta-sam-parser 0.1.0, fal-client 1.0.3, ollama (Python client) 0.6.3, Ollama runtime v0.40.6 with `llama3.2:3b` (0.40.x accepted, macOS auto-update may move the patch), modal 1.6.2, pytest 9.1.1, python-dotenv 1.2.4, Node 24.22 (`.nvmrc` = 24, `engines.node` = "24.x", npm with `web/package-lock.json`), Vite 8.3.4, three 0.186.1, @types/three 0.186.0, TypeScript 6.0.3 (exact), json-schema-to-typescript 16.0.0, @sparkjsdev/spark 2.4.0 (Tier 3 only). The first providers story bumps `requires-python` to `>=3.13`, moves the Python Stack pins into `[project.dependencies]` with `==` pins (pytest into `[dependency-groups] dev`), drops `requirements.txt`, adds `.python-version` (`3.13`), commits `uv.lock`, sets `[tool.uv]` `environments` and `required-environments` (macOS arm64, Linux x86_64), `no-build = true` and `required-version = ">=0.11.32"`, and adds `pythonpath = ["."]` to `[tool.pytest.ini_options]`; install is `uv sync --locked` (never `--frozen`, never `uv pip install`) and `npm ci`; `web/package.json` versions are exact and `web/.npmrc` sets `save-exact=true` and `engine-strict=true`; every dependency change follows the keyframe-devops checklist, and from the deps-foundation merge on Mon Oct 26 a pin moves only for a blocking bug or a security fix.
AR-3: Scaffold fixes found by the dev skills, made in the first providers story: `src/providers/meta_api.py` sets `DEFAULT_BASE_URL` to `https://api.meta.ai/v1` (it reads `https://api.meta.com/v1`), the chat model id to `muse-spark-1.3` (it reads `muse-spark`) and the image model id to `muse-image-1.0` (it reads `muse-image`, which returns 404 `model_not_found`), replaces urllib with httpx, drops the `temperature` default of 0.7 and `max_tokens` (AD-5's port has neither) and takes its key from `Settings`, never `os.environ`; `src/config.py` `Settings` gains `fal_key` from `FAL_KEY` plus the AD-14 product flags and per-role adapter settings (`CHAT_MODEL` and `IMAGE_MODEL` retire); `.env.example` lists every key `Settings` reads, blank, including `META_MODEL_API_KEY` and `FAL_KEY`, and a test asserts it. A per-role output-token setting (`MAX_COMPLETION_TOKENS_<ROLE>`) is not in AD-14 and needs an AD-14 amendment before any story reads it.
AR-4: Paradigm, boundaries and ownership (AD-1, AD-17): hexagonal core; `src/domain` is pure (standard library and pydantic only; no network, filesystem or clock); `src/council` and `src/pipeline` import only the domain and port modules; adapters in `src/providers` and `src/infra` import only ports and the domain and never each other; only `src/providers`, `src/infra` and `src/api` import adapters; `Clock` is a Protocol in `src/domain/clock.py`; `tests/test_boundaries.py` walks every module's imports and fails on a violation; one owner per top-level package (`domain`, `council`, `pipeline`, `providers`, `api`, `infra`, `web`), and a story touches one package plus tests or first declares the port change it needs.
AR-5: One data shape and generated client types (AD-2): Schema v1 is realized once as pydantic models in `src/domain/schema.py`; `GET /schema` returns every model the API accepts or returns (`Room`, `RoomDraft`, `PlayView`, `BuildView`, `RoomView`, `RoomSummary`, `AccessCheck`, `Derived`, `RoomResult`, `Meta`, job state, session state, event models, error envelope); `web/types` are generated from it (json-schema-to-typescript 16.0.0 or quicktype, picked by the first `web/` story), committed, never hand-written, with a test that fails when stale; `Puzzle.solution` and `TricksterEdit.payload` are tagged unions emitted as `oneOf`, sent with `strict: false` on the Meta path; no model-response schema (`RoomDraft`, `DryRunAnswers`, `ArchitectResponse`) has a map-typed field; `Room.name` is optional (at most 40 characters, set only on seeded Demo rooms); JSON keys are snake_case end to end.
AR-6: Solution boundary (AD-3): `src/domain/redact.py` exposes `to_prompt_view(room) -> RoomView`, `to_play_view(room) -> PlayView` and `to_build_view(room, job) -> BuildView`; council functions are typed on `RoomView`; play routes return only `PlayView` (drops `solution` and `provenance`, keeps `evidence`); `Room` leaves the server only through the access-coded `GET /builds/<job_id>/room`; `BuildView` carries per-photo mask polygons with labels, the puzzle graph (`id`, `lock_type`, `requires`, `is_exit`), per-rule verdicts, Dry run pass, fail or `skipped` per Puzzle, the Regeneration count and configured `REGEN_MAX`, the build time, the Model table and call rows, and the per-Room disclosure list, never a solution, Dry run answer or Clue-to-answer pairing; the mask preview in `GET /builds/<job_id>` is solution-free; tests: sentinel solutions across every council prompt, `HintPhraser` input exactly `(rung_text, derived)`, and no `solution` key in any play, job-state or `BuildView` response.
AR-7: Event-sourced sessions (AD-4): append-only event log with pydantic event models: client `ClickEvent(interactable_id)`, `LockInputEvent(CodeInput | UseOnInput | OrderStartInput | OrderStopInput)`, `HintRequestEvent(puzzle_id | null)`; server `IdleTickEvent`, `OpeningLineEvent(kind, text)`, `TricksterCardEvent(edit_id, accepted, reason, room_revision)`, `RungChangeEvent(puzzle_id, rung, triggered_by)`; `t_ms` stamped by the API at append and a client timestamp rejected with 422; `use_on` carries no `puzzle_id` and the server resolves it from the pair; the `order` buffer is armed only by `order_start`, a full-length mismatch is one Wrong attempt and keeps it armed, `order_stop` disarms with no Wrong attempt; `idle_tick` appended on a `GET /sessions/<id>` read after 5000 ms with no event (client polls every 2000 ms, no background ticker); `SessionStateMachine.apply` is the sole writer of session state, with `select_rung` pure inside it, so replay equals live; session state exposes `active_puzzle_id`, `opening_line`, `phrasing` and `disclosure`; a Trickster `SpendCapExceeded` or `ProviderError` closes the window as a skipped card (`reason: provider_unavailable`).
AR-8: Model ports (AD-5): `ModelProvider` is the only way to reach a model, synchronous, with a bounded thread pool for segment fan-out (at most 12); signatures `chat(messages, *, images=[], response_schema=None, reasoning_effort='low', model=None)`, `segment(label, image) -> list[Polygon] | None`, `reconstruct3d(image, mask: Mask3D) -> GlbRef` with `Mask3D {label, polygons (frame pixels), frame_size}` in `src/domain/schema.py` (the fal prompt is its `label`), `generate_image(prompt)`, `transcribe(wav)`; one `strict_schema(model)` helper for strict hosts; `reasoning_effort` never `none` (the mock refuses it too); adapters `mock`, `meta` (Chat Completions for the council, Responses for `sam-3.1`, standard tier only), `openai_compatible` (Baseten, Fireworks by `base_url`), `fal`, `ollama`; `wiring.py` resolves one provider per council role (`architect`, `riddler`, `dryrun`, `trickster`, `image`), fallbacks replacing a role's provider only; `HintPhraser` (`phrase(rung_text, derived)`, `greet(derived)`) is implemented only by the Ollama and verbatim adapters, selected by `GUIDE`, with a fixed prefix under 400 tokens and a 5 s timeout logged as `phraser_fallback`; `POST /sessions` returns `opening_line {kind: greeting | welcome, text}` and `phrasing`; the Riddler prompt carries the generated-line voice rules.
AR-9: Guarded calls (AD-6): every hosted adapter call runs `Cache.get_or_call(key)` and, on a miss only, `SpendLedger.guard(kind, estimate)` inside `src/providers`; the mock bypasses both; key = sha256(model id, schema hash, full prompt with system message, reasoning effort, sha256 of each image in order, attempt), where `regenerate.py` passes the regeneration count and `trickster.py` the window index; `CACHE=off` bypasses the cache, never the ledger; `domain/ledger.py` is pure arithmetic, `providers/spend.py` one `SpendLedger` per process serializing `guard` under a lock, appending a `reserved` entry replaced by observed cost, one `call_` entry per priced call (a retried call is one entry), estimates seeded from `budgets.md` plus `reconstruct3d` $0.02; hosted containers may overshoot the cap by in-flight estimates (accepted); `scripts/ledger.py reset|export` is the only reset path and the source of the spend export.
AR-10: Persisted build job (AD-7): the client produces the downscaled JPEG (Canvas, EXIF orientation applied, long edge 1280, quality 0.85) and posts it with the original in one multipart `POST /builds`; ingest stores both byte for byte, rejects fewer than 6 or more than 10 photos (422 `photo_count`), accepts JPEG only (`UnsupportedImage`, code `unsupported_image`), and rejects a downscale whose long edge is not 1280 or orientation tag not 1 (422 `bad_downscale`), each in the AD-13 error envelope; `photos[i].hash` is sha256 of the stored downscaled bytes; stages `ingest → architect → segment → author → validate → dryrun → scene` run through `JobRunner`, `JobStore` and `ArtifactStore`, persisting state, artifacts and timings after each stage and rereading state on entry so a restarted runner resumes; segment persists the mask preview (`id`, `label`, `photo`, `polygons`) or ends `needs_more_photos`; the author stage persists a `RoomDraft`; the `room` artifact is written only after validate and the Dry run pass; hosted, the runner is `@app.function(timeout=900)` invoked with `.spawn()` as the one writer per job, `ArtifactStore.put` ends with `Volume.commit()` and reads begin with `Volume.reload()`, the Dict holds in-flight state only, the `FunctionCall` id sits under `call:<job_id>`, and a watchdog marks a dead runner's job `failed` (`ORPHAN_S` 60 s, `DEADLINE_S` 1,200 s); `GET /builds/<job_id>` answers 202 while `queued` or `running` and 200 when terminal, in both modes; job statuses `queued`, `running` (with `stage`), `done`, `failed`, `needs_more_photos`, `needs_recapture`; `scripts/seed_rooms.py` writes a final job record and `Room.name` for each Demo room.
AR-11: Profile ownership and retention (AD-8): `Derived` and `RoomResult` are pydantic models with bounds (422 outside) and `Derived.fresh()`; the nudge threshold `clamp(90000 * (1 + 0.5 * persistence), 60000, 135000)` ms lives only in `domain/rungs.py`; `POST /sessions {room_id, derived}`; `GET /sessions/<id>/result` returns `RoomResult` with `demo: DEMO_TIMESCALE > 1`; `web/profile` is the only profile writer, keyed by `room_id`; the cut-2 `GET|PUT /profile/<name>` route exists only in local mode, writing `rooms/profiles/<name>.json`; hosted session logs are deleted by the hourly `session_sweep` Cron 24 h after their last event; each judge Build writes `cache-keys.json` beside its originals under `rooms/judge/<room_id>/`; `scripts/purge_judge_rooms.py` deletes judge rooms, originals, sessions and listed cache entries together and keeps an ids-only deletion record; the Retention summary is one string per mode in `src/api/meta.py`; a test asserts the `.gitignore` entries.
AR-12: Two modes, hosted names (AD-9): `MODE=local|hosted` selects only `JobStore`, `ArtifactStore`, `JobRunner`, `SessionStore`, `LedgerStore` and `Cache` in `src/infra`, and no mode branch exists outside `src/infra` and `src/api` wiring; FastAPI mounts `web/dist` at `/` with routes under `/api/` (one origin, no CORS; the Vite dev server proxies `/api/*`); hosted mode guards `POST /builds` and `GET /builds/<job_id>/room` with `X-Access-Code` (refusals and the per-IP attempt limit in AR-13); the build quota is 20 slot keys claimed with `Dict.put(key, value, skip_if_exists=True)` (atomicity verified in the hosted story before it is relied on), the 21st refused with `build_quota_exceeded` (code and status unchanged); hosted names: Dicts `keyframe-jobs`, `keyframe-sessions`, `keyframe-ledger`, Volume `keyframe-data` mounted at `/data`, Secret `keyframe`, functions `web`, `run_build`, `ledger_export` (`modal.Cron("0 6 * * *", timezone="America/New_York")`, writing `spend/hosted-<date>.jsonl`) and `session_sweep` (hourly); `max_containers=1`; `MIN_CONTAINERS=1` Thu Nov 5 to Mon Nov 9; local stores: JSON sessions under `rooms/sessions/`, `spend/ledger.jsonl` under a file lock (git-ignored), `.cache/`; `scripts/ledger.py export` merges local entries and the latest hosted snapshot into the committed `spend/exports/ledger-<date>.json`; Demo rooms seeded under `rooms/demo/`, Judge rooms under `rooms/judge/`, deletion records under `rooms/deleted/`.
AR-13: HTTP routes, all under `/api/`, including the Oct 21 amendments: `POST /builds` (ingest refusals 422 `photo_count` and 422 `bad_downscale`, a non-JPEG `unsupported_image`); `GET /builds/<job_id>` (job state, mask preview once segment completes, 202 while `queued` or `running`, 200 when terminal); `GET /builds/<job_id>/room` (full Room, access-coded in hosted mode); `GET /builds/<job_id>/view` (BuildView, open in both modes; 409 `build_not_ready` with the job `status` in the envelope until `done`); `GET /rooms` (`RoomSummary {room_id, name, cover_photo, puzzle_count, job_id, built_at}` list: local, every stored Room; hosted, Demo rooms only); `GET /rooms/<room_id>` (PlayView); `GET /rooms/<room_id>/photos/<i>`; `POST /sessions {room_id, derived}` (returns the opening line and `phrasing`); `GET /sessions/<id>` (state with `active_puzzle_id`, `opening_line`, `phrasing`, `disclosure`); `GET /sessions/<id>/room` (Effective room PlayView, refetched when `room_revision` changes); `POST /sessions/<id>/events`; `POST /sessions/<id>/trickster` (outside an open window: 200 with the unchanged session state, no event, no error envelope); `GET /sessions/<id>/result`; `GET /schema`; `GET /meta`; hosted only `POST /access/check {code}` returning `{ok, builds_left}` (a wrong code: 200 `{ok: false, builds_left: null}`), starting no Build; in Hosted mode a missing or wrong `X-Access-Code` on `POST /builds` or `GET /builds/<job_id>/room` answers 403 `access_denied`, and more than 10 access attempts (`POST /access/check` or a guarded route, wrong or right code) per client IP in 10 minutes answer 429 `too_many_attempts` with `Retry-After`; local cut 2 only `GET|PUT /profile/<name>`; a room-keyed route answers 410 `room_deleted` for a purged Judge room and 404 `room_not_found` for an unknown id.
AR-14: Two clocks (AD-10): a `Clock` port supplies all time; the session clock applies `DEMO_TIMESCALE` only to the thresholds passed into `apply` (nudge threshold, Rung spacing, Trickster window), never to `t_ms` or the poll cadence, and the client never reads it for timing; the build clock never applies it and stamps stage timings and the capture Timer.
AR-15: Scene contract (AD-11, AD-18): Tier 1 scenes are Three.js textured planes with polygon Hotspots in the scene graph Tier 2 reuses; Hotspot id equals Interactable id; a Hotspot is the union of the Interactable's `polygons[]` in the pixel space of the stored downscaled JPEG served by `GET /rooms/<room_id>/photos/<i>`, never an in-memory canvas; the box fallback is written as a polygon at segment, so the client never reads `box`; the client sends ids and lock inputs, never puzzle logic; the DOM-only fallback keeps the same id contract; geometry conventions: Spark boxes on the 0 to 1000 grid converted to frame pixels and clamped, SAM rasters scaled to the frame, the `meta-sam-parser` SVG path (M/L/Z) parsed to `[[x, y], ...]` and simplified in `domain/masks.py`.
AR-16: Validation gate and session-scoped edits (AD-12): `validate(room)` and `check_dry_run(room, answers)` in `domain/validator.py` are pure; `council/dryrun.py` builds the prompt over `RoomView` and the pipeline dryrun stage makes the call and is the only place answers meet solutions; `DryRunAnswers` is a list of `{puzzle_id, answer}`, never a map; `DRY_RUN=off` realizes cut 4; the build Room is immutable; `domain/edits.py` `validate_edit(room, state, edit)` and `apply_edit(room, edit)`; a proposal is accepted only if `validate_edit` and `validate(apply_edit(...))` rules 1 to 8 pass; results are appended as `trickster_card` events, the Effective room is `apply_edit` folded over accepted edits at replay with `room_revision` = accepted count, `loosen` is applied to `current_rung` by `apply`, and edits never reach `ArtifactStore`; validator token matching follows the Conventions (code strings and digits as exact whole tokens at any length; the three-character floor applies to label words only; `is_exit` checked first in rule 7).
AR-17: Typed errors and retry policy (AD-13): stages raise `ProviderError`, `ValidationError`, `DryRunError`, `TooFewInteractables`, `UnsupportedImage`, `BuildQuotaExceeded` or `SpendCapExceeded`; room-keyed routes raise `RoomNotFound` (404) or `RoomDeleted` (410); `src/pipeline/regenerate.py` is the sole regeneration loop (`REGEN_MAX`, default 2, then `needs_recapture`) and sole writer of the count; adapters retry once with backoff, inside one ledger entry, only on what the vendor documents as retryable, each declaring its set: 429 always; Meta Model API 500 and 503 (never 504, 502, an undocumented 5xx or a `muse-image-1.0` 500); fal 5xx only when `X-Fal-Needs-Retry` allows; `ConnectError` and `ConnectTimeout` once; client or read timeouts never; `Retry-After` honored, failing at once with `ProviderError` when it exceeds the stage's remaining budget; error envelope `{error: {code, message, stage}}` (codes are the class names in snake_case, `stage: null` outside the pipeline, plus `status`, the job status, on `build_not_ready` only) on build, access, session-creation and room-keyed routes only; request codes outside the typed classes: 422 `photo_count` and 422 `bad_downscale` (AD-7), 409 `build_not_ready` (AD-3), 403 `access_denied` and 429 `too_many_attempts` with `Retry-After` (AD-9); `unsupported_image` and `build_quota_exceeded` keep their codes; no `regen_exhausted` class (the UI keys on job status); a Trickster call error is a skipped card, a Validator failure the rejected card.
AR-18: Configuration (AD-14): environment read once by `Settings` (`src/config.py`) and injected, no module reads `os.environ` (`scripts/doctor.py` is exempt: stdlib, runs before `uv sync`); product flags `MODE`, `CACHE`, `SPEND_CAP_USD`, `DEMO_TIMESCALE`, `DEMO_TRICKSTER=live|record|scripted|authored` (`MODE=hosted` with `record` fails at startup), `MIN_CONTAINERS`, `GUIDE=ollama|verbatim` (default `ollama` local, `verbatim` hosted; `MODE=hosted` with `GUIDE=ollama` fails at startup), `DRY_RUN=on|off`, `REGEN_MAX`; adapter settings `MODEL_PROVIDER` as default for `PROVIDER_<ROLE>` (`ARCHITECT`, `RIDDLER`, `DRYRUN`, `TRICKSTER`, `IMAGE`) with per-role model ids, `META_MODEL_API_KEY`, `META_MODEL_API_BASE_URL`, `OPENAI_COMPATIBLE_BASE_URL`, `OPENAI_COMPATIBLE_API_KEY`, `FAL_KEY`, `OLLAMA_HOST`, `ACCESS_CODE`; `Settings` gains `mode` and `min_containers` in the first hosted story; `.env` git-ignored, `.env.example` committed with every key blank (tested); hosted secrets in the `modal.Secret` `keyframe` attached to the app and the runner; the client reads `PROFILE` from `?profile=` (default `dev`) and `GET /meta` echoes it.
AR-19: Demo mode and the status model (AD-15): `DEMO_TRICKSTER` selects only the proposal source: `live`, live proposals; `record`, live proposals plus the recorder writing them into the recorded-proposals artifact (Local mode only, refused at startup in Hosted mode); `scripted`, replay of the recorded proposals; `authored`, cut 1, the pre-authored proposals file with no live path; the Validator runs live and card rendering is unchanged under every value; `GET /meta` returns exactly `{mode, guide, guide_model: {id, host} | null, trickster: live | scripted | cut1, demo_timescale, cache, profile, disclosure, retention}`, `trickster` being `live` for `live` and `record`, `scripted` for `scripted` and `cut1` for `authored`, the cut 1 Disclosure line served only under `authored`, `guide_model` null in hosted mode, `retention` the running mode's text (hosted replaces the local storage sentence, never appends); session state and `BuildView` carry a per-Room `disclosure: [string]` with the global lines plus "This room was built earlier, on <date>." for a Demo room, a Room with an earlier session, or a Build with any cached call; one function in `src/api/meta.py` composes every list.
AR-20: Provenance (AD-16): the pipeline writes `provenance` (model ids, prompt hashes, stage timings, regeneration count, spend per stage from the ledger, applied edit ids) into every Room; the job record keeps one call row per model call (role, model id, host, cached or billed, spend) and the build time, read by `BuildView`; the spend log export derives from the ledger, never hand-kept.
AR-21: Identity (AD-18): `ix_` ids are minted only by the segment stage after mask selection and the 12 cap; `ArchitectResponse` is correlated by list position; the Riddler's schema uses ordinal keys `p1`..`p6` mapped to `pz_` ULIDs before `validate`; model output references `ix_` ids parsed back by exact match, never by label; `box` converted to pixels at segment; `tier2` is the only field in original pixels; `Interactable.photo` indexes `photos[]` in upload order; ids are prefixed ULIDs (`room_`, `job_`, `sess_`, `pz_`, `ix_`, `te_`, `call_`) assigned only by server code.
AR-22: Conventions: snake_case JSON and TypeScript keys, PascalCase pydantic models; ISO 8601 UTC times and `t_ms` session milliseconds; one JSON log line per event with `job_id` or `session_id`, stage, `duration_ms` and `spend_usd`; domain functions return new values and only `SessionStateMachine.apply` and the stage runner write state; Python 3.13 type hints, pydantic v2, ruff defaults; TypeScript strict; tests under `tests/<package>/` mirroring `src/`, fixtures under `tests/fixtures/`.
AR-23: Offline tests per story with the mock provider (AD-17, NFR-8): `pytest` runs offline against the mock provider for every story and a story is done only when it passes; adapter tests replay recorded fixtures under `tests/fixtures`; the offline suite holds `tests/test_boundaries.py`, the `web/types` staleness test, the `.gitignore` and `.env.example` tests, and the sentinel-solution tests.
AR-24: Continuous integration and build checks: one GitHub Actions job `check` on push to master and on every pull request runs `bash scripts/check.sh`, which is also the pre-push check: the privacy check (no secret, env file, raw photo or cache tracked), the lock check (`uv lock --check`, `uv sync --locked`, wheels for macOS arm64 and Linux x86_64 with glibc 2.28), the offline `pytest` suite, and the `web/` build and type check (`npm ci`, `vite build`, `tsc --noEmit`) once `web/package.json` exists; CI installs uv 0.11.32 and takes Node from `.nvmrc`; `scripts/check.sh --predeploy` runs before every manual `modal deploy`; `scripts/doctor.py` (stdlib only) checks the Mac and cloud environments; a SessionStart hook prepares cloud containers; no secrets, no deploy step, no CD; `modal deploy` stays a manual step.
AR-25: Lean SIT: a checklist plus `scripts/sit.py`, which runs about 10 live-seam cases (real provider calls across the adapter and pipeline seams, within the Spend cap) and records their responses as fixtures for the offline suite, run at the end of each build day from Tue Oct 27, with a full pass Sat Oct 31; no separate sign-off.
AR-26: Guide placement: the Guide model runs only on the Mac (Llama 3.2 3B Instruct Q4_K_M via Ollama, `OLLAMA_KEEP_ALIVE=-1`); hosted mode shows Rungs verbatim and never runs a Guide model.
AR-27: Schema timeline and carried decisions: the Thu Oct 22 review makes one pick, decoy storage (options A, B, C in `schema-v1.md`; A, `Room.decoys[]`, recommended), which adds validator rule 9; the Oct 21 approvals (`polygons`, `is_exit` only, no `profile_name`, rule 5 over `clue` and `evidence.visible_attribute`, optional `Room.name`, the order start and stop inputs, API models, provenance fields) are applied; Schema v1 freezes Mon Oct 26 and later changes go through `bmad-correct-course`; carried to Mon Oct 26: the Fireworks Trickster fallback model id (confirmed before a fixture is recorded), the `GET /meta` retention wording (§13 Q3) and the hosted full-Room download route (§13 Q4); the Meta adapter is wired only after the pre-kickoff verifications passed, else API wiring moves to Tue Oct 27 and later work slips a day.
AR-28: Repo hygiene on Wed Nov 4 removes only the path list in `delivery-plan.md` §Submission package, Repo hygiene: `_bmad/`, `.claude/skills/bmad-*/`, `.claude/skills/modal/`, `.claude/skills/keyframe-*/`, `.claude/hooks/session-start.sh` and `.claude/settings.json` (if a `.claude/settings.json` existed before the hook story, only the hook entry is removed and the file stays), with `git rm -r --cached --ignore-unmatch _bmad .claude/skills/modal .claude/skills/bmad-* .claude/skills/keyframe-* .claude/hooks/session-start.sh .claude/settings.json`, the matching `.gitignore` entries, and a check that `git diff --cached --name-status` lists only `D` entries under those paths; everything else under `.claude/` stays; any path later added by hackathon tooling is added to that list first; `PRODUCT_BRIEF.md` stays removed.
AR-29: Raw room photos are never committed: the input folders are git-ignored (FR-36) and only outputs ship (screenshots, Clue cards, the videos), with household consent for what appears in them.
AR-30: Pre-hackathon baseline: `git tag -a pre-hackathon-baseline` is pushed Sun Oct 25 night with the MIT LICENSE and the baseline CHANGELOG entry ("Before Oct 26 (baseline): provider interface, mock provider, Meta API stub, tests. No front end, no model calls."); small dated commits follow; the README's "Pre-existing code" section links the tag with `git diff --stat pre-hackathon-baseline..HEAD`; the dated CHANGELOG runs from the baseline entry through Nov 4.
AR-31: Contract additions the UX contract asks of the spine (EXPERIENCE.md Open Items; each needs a spine amendment or a story that declares the port change before UI stories rely on it): job status and `BuildView` carry, per failed attempt, the fixed messages that sent it back; job status exposes per stage the done-row counts (photos, objects, puzzles, rules passed of 8, Dry run answers reached) and model id, and `BuildView` the provenance counts behind the Model table's "what it did"; `rung_change` carries whether the Rung was phrased and the phrasing latency; session state exposes the effective nudge threshold and Rung spacing, their 1× values, and whether the threshold came from the Derived block or `Derived.fresh()`; a rejected `trickster_card` carries a structural proposal summary (edit type and Puzzle ids only), and every card carries its Puzzle id; the server picks the Demo room variant of the First-room welcome on a Demo room.
AR-32: Deferred (no stories now): an atomic ledger store and `max_containers` above 1; authentication beyond the access code; observability beyond JSON logs; a database; CI beyond AR-24; mobile layout; multi-user; Tier 2 object placement (decided by the pre-Oct 26 spike inside the Tier 2 epic); Clue cards as an optional post-scene stage (Tier 1.5); Tier 3 splat integration (never gating); voice transport and UI.

### UX Design Requirements

UX-DR1: Color tokens: implement every `DESIGN.md` `colors` token as a CSS custom property with the exact hex (study: `canvas` #14100C, `chrome` #1E1812, `chrome-raised` #2A2119, `hairline` #4A3C2C, `gilt` #B08A4E, `scrim` #0A0806CC; paper: `parchment` #E8DBBE, `parchment-shade` #D8C7A2, `parchment-rule` #5A463040, `ink` #2A1D11, `ink-muted` #5A4630; text `text` #F0E6D2, `text-muted` #B8A98E; lamplight `lamp` #E9A94B, `lamp-strong` #F4C470, `lamp-ink` #6E400C, `on-lamp` #1A1208, `lamp-hover-fill`, `lamp-ink-hover-fill`; focus `focus-ring` #FFD27A, `focus-ring-inner`; hotspots `hotspot-outline`, `hotspot-halo`, `hotspot-glow`, `hotspot-show-all`; states `success`/`success-ink`, `wrong`/`wrong-ink`, `pending`/`pending-ink`; plain messages `warning-*`, `error-*`, `disclosure-*`; role tokens `card-*`, `clue-card-*`, `graph-*`, `mask-overlay-*`), dark theme only; role tokens repeat their base hex and change with it; usage rules: gilt only for frames, lamp never fills a large area or colors a plain message, `lamp`, `success` and `wrong` never on parchment (use the ink forms), no colors drawn from the player's photos, no gradients other than the Scene vignette.
UX-DR2: Typography tokens: self-host EB Garamond, Source Sans 3 and IBM Plex Mono as WOFF2 in `web/dist` (no third-party font request) and implement the 13 styles with their sizes, weights and line heights (`display-lg` 40, `display-md` 30, `display-sm` 22, `wizard-line-lg` 24, `wizard-line` 19, `lore` 17 italic, `body-md` 16, `body-sm` 14, `label` 13/600, `caption` 12, `mono-timer` 28, `mono-code` 20 tracked 0.2em, `mono-sm` 13); rules: headings serif everywhere, in-character lines in the serif body styles with a portrait, plain lines in the sans with none, Garamond never below 17 px, italic only for Lore, sentence case, no all-caps, tabular figures for numbers that change in place, `caption` only for thumbnail and Inventory captions, text never directly on a photo.
UX-DR3: Spacing and layout tokens: the 4 px scale (`spacing.1` to `spacing.8`: 4, 8, 12, 16, 24, 32, 48, 64) and the named layout tokens (`frame-margin` 24, `column-gap` 24, `side-column` 400, `top-bar` 48, `disclosure-min` 32, `thumbnail-strip` 88, `narrow-gutter` 16, `hint-area-max` 320, `triggers-panel-max` 160, `notes-min` 280, `status-strip` 32); spacing rhythm: tight pairs 8, inside a panel 12 to 16, panels 24 apart, screen sections 48.
UX-DR4: Radii and shapes: `rounded.none` 0 (Disclosure banner), `sm` 4 (photos in frames, thumbnails, code field, chips, label chips), `md` 8 (buttons, fields, Evidence cards, Trickster Cards, banners, graph nodes), `lg` 12 (sheets and trays: Wizard notes, Hint area, Completion sheet, Greeting card, Demo room cards, dropzone), `full` (portraits and order pips only; no pill buttons); Hotspots keep their polygon shape, never rounded, boxed or simplified.
UX-DR5: Elevation: `paper` shadow on parchment surfaces (cards on the notes only its 1 px line), `overlay` shadow for the Greeting, Completion sheet, Card log and Leave room confirmation over `scrim`, `lamp-glow` as the only light effect (Hotspot hover, primary button and Demo room card hover, the single arrival glow), `vignette` on the Scene mat only; level 0 wall, level 1 desk and trays separated by tone, no shadow; plain surfaces and waiting states never glow.
UX-DR6: Motion and reduced motion: fades and glows only, `ease-out`, 150 ms for hover, 200 ms for state fades, at most 300 ms for overlays entering and the arrival glow; nothing slides, bounces, shakes, scales more than 2% or loops (the Guide thinking ring, the "Checking" ellipsis and the Timer's lamp dot are static); under `prefers-reduced-motion: reduce` every transition is instant, the arrival glow becomes the lit ring held 2 s, and the 300 ms wrong flash on the order pips becomes an instant reset, while a repeated Hint reply is still announced.
UX-DR7: App shell and top bar: the 1440 x 900 frame from the top: the Disclosure banner (full width, 32 px per line, part of the grid, pushing everything down, never overlaying); the 48 px `chrome` top bar with the Keyframe wordmark (`display-sm`) and the mode indicator on the left, the Timer and its label centered in the same position on the Capture and Play screens, and "Show all objects", "Card log" and "Leave room" on the right on the Play screen only (inert under overlays and on the Completion screen; absent on the Capture screen, Build view and Hosted landing); the body inside 24 px margins with the Scene column (about 968 px: Scene frame, then the 88 px row with the Thumbnail strip and the 288 px Inventory) and the 400 px side column (Wizard notes on top, at least 280 px, the Hint area pinned below); every scrim starts below the top bar and the top bar stays undimmed but inert under overlays; responsive bands: 1280 to 1439 px side column 360, 1024 to 1279 px side column 340, below 1024 px the Narrow-screen message; no horizontal page scroll at any width.
UX-DR8: Client routes and navigation: hash routes `#/` (Local: Capture screen; Hosted: Hosted landing), `#/build/<job_id>` (resumes polling; on a `done` Build shows "Play this room" and the Build view link instead of auto-starting), `#/build/<job_id>/view`, `#/play/<session_id>` (reload resumes), `#/done/<session_id>` (reload does not record the result twice), with `?profile=` carried on every route; Capture → Play automatic when the first Scene is ready, Play → Completion automatic on the Exit puzzle; modals one level deep (Greeting, Card log, Leave room confirmation), never stacked; browser Back on the Play screen asks the Leave room confirmation; stored Rooms come only from `GET /rooms`.
UX-DR9: Primary button: label only, 44 px high, 24 px side padding, lamp fill with `on-lamp` label, hover `lamp-strong` plus glow, two-tone focus ring, disabled at 40% opacity without glow; at most one per surface region; Enter and Space activate; a pending label while its request is in flight, ignoring repeat activation; disabled buttons stay focusable only when a reason is shown beside them.
UX-DR10: Secondary button: 40 px, 1 px lamp border and lamp label, hover `lamp-hover-fill`; on parchment `lamp-ink` label and border with `lamp-ink-hover-fill` hover; toggle variants ("Show all objects" pressed, the Triggers toggle expanded, "Show the build JSON" expanded) hold `lamp-hover-fill` plus a 2 px lamp border and announce pressed or expanded state, the effect itself being the second cue; used for banner actions, Code field Submit and the top-bar controls.
UX-DR11: Focus ring: a 2 px `focus-ring` outside a 2 px `focus-ring-inner` at 2 px offset on every focusable element, Hotspots and graph nodes included, shown for `:focus-visible`, never removed or replaced by the hover glow.
UX-DR12: Mode indicator: one plain `body-sm` `text-muted` line after the wordmark on every surface, built from `GET /meta` plus the local Room result count: "Local mode · Cache {on or off} · profile {name} · {k} rooms played" ("0 rooms played", "1 room played") or "Hosted mode"; updates as soon as a Room result is recorded; not focusable, not a control, never styled as a Disclosure; the app has no Cache-clear control.
UX-DR13: Status strip: a 32 px plain `body-sm` strip on `warning-surface`, no portrait, no glow, taking no focus: reconnecting on the Play screen at the top of the Scene column (the Scene frame shrinks by its height, the photo dims to 60%, inputs disable) with "Reconnecting to Keyframe. Your progress is safe; play resumes when it's back."; reconnecting on the Capture screen at the top of the left area above any banner with "Reconnecting to Keyframe. Your build keeps going; this page catches up when it's back." (Stage list stays as last seen); server unreachable on cold load centered alone; written once to the live region; shown after two consecutive missed polls.
UX-DR14: Capture dropzone: a `chrome-raised` tray at least 320 px high with dashed hairline border (dashed lamp on drag-over), `rounded.lg`, a centered "Choose photos" picker and the picker sentence "Choose 6 to 10 JPEG photos of one room."; accepts drag-and-drop or the picker; all-or-nothing client validation (any non-JPEG checked by bytes, or a count under 6 or over 10, rejects the set, marks offending files and uploads nothing); a valid set enables Upload, which produces the downscaled JPEGs and posts one multipart `POST /builds`; disabled during a Build.
UX-DR15: Photo tray: 120 x 90 thumbnails in upload order with 12 px gaps and a `label` count line ("{n} photos chosen"); before Upload each has a 32 px remove control named "Remove photo {n}" (× on a scrim square), and each removal or addition re-validates the set, clearing the FR-1 banner when valid; a rejected file has a 2 px `wrong` border and the label "Not a JPEG", and stays removable; during a Build the tray turns compact (96 x 72); kept visible on every end state; after `needs_more_photos`, "Add photos" appends up to 10 in all.
UX-DR16: Mask preview: appears once the segment stage completes from the solution-free mask preview in job status; a grid of each Interactable's clearest photo with its outline drawn in `build-view-mask` style and its label on a parchment chip in `label` type (never caption size); tiles fade in together (200 ms), are not interactive, and carry no heading or line of their own (the Architect's "Finding objects" line names the objects).
UX-DR17: Timer: a plain `label` in `text-muted` before `mono-timer` m:ss digits in the top bar center: running reads "Photos to play" with `text` digits and a static 6 px lamp dot; frozen at T1 reads "Playable in" with the T1 − T0 digits in `success` and no dot; end statuses (`failed`, `needs_more_photos`, `needs_recapture`, upload failed) freeze the digits with the status in `text-muted`; starts on the Upload click, stops at the first pointer response on a Hotspot (keyboard focus does not stop it), runs undimmed above the Greeting scrim, keeps counting while reconnecting, resumes from the recorded start after a reload, never scales with the Demo timescale, and is hidden when replaying a stored or Demo room; Hosted: "queued" replaces the digits while queued, and after T1 the note "includes m:ss in the queue" follows.
UX-DR18: Stage list: a `chrome-raised` tray replacing the dropzone during a Build: the Architect's introduction row at the top from Upload (48 px portrait, "The Architect", role line, voice line, hairline rule under it), then the five A-11 stage rows ("Reading your photos", "Finding objects", "Writing puzzles", "Testing the room", "Setting the scene") with a 12 px marker and `mono-sm` duration: pending hollow `text-muted`, running filled `lamp` with the Architect's stage line under its name (moving to each new running row with a 200 ms fade), done `success` with its plain result and model id ("9 objects", muse-spark-1.3 · sam-3.1; "Testing the room" shows "Rules: 8 of 8 passed" and "Test run: reached 5 of 5 answers"), failed `error-text`; the Riddler's introduction fades in inside the "Writing puzzles" row when it starts and stays; a Regeneration adds "Rewriting puzzles, attempt n of {max}" with "Sent back: {fixed messages}" and repeats the author, validate and dry run rows; in Hosted mode two plain lines sit under the list (the build's own link; where the two-minute target is measured); not a live region; each in-character line carries a visually hidden speaker prefix.
UX-DR19: Stored Room row (Local): one `chrome` row per `RoomSummary`, newest build first: a 96 x 72 cover thumbnail, the Room's name or else its build date and time, the Puzzle count, "Play" (secondary, starts a new Session with no Timer) and "How this room was built" (secondary, opens the Build view); hover lamp ring, focus ring; empty list reads "No rooms yet."; a refused start shows the session-start-refused banner.
UX-DR20: Retention summary: the right column's only tray, on `chrome-raised` (never parchment): heading "Where your photos go.", then the mode-specific text exactly as served by `GET /meta` `retention` in `body-sm`, then the plain label "Your play history" and the Privacy line "the player profile stays on your machine." in `body-md` 600 `text`; always fully expanded, never collapsed, truncated or below `body-sm`, visible before any photo is chosen; under cut 2 only, "Open profile file" (secondary) and its plain line sit below the Privacy line.
UX-DR21: Error banner (with its warning variant): full width of the left area, above the photos, one at a time (a newer state replaces an older one), taking focus when it appears; serif heading and one plain `body-md` sentence left, secondary actions right, no portrait; error variant (`error-surface`, 4 px `error-edge`) for the FR-1 refusal (verbatim heading "Keyframe needs 6 to 10 JPEG photos.", no sentence, action "Choose photos again"), the 422 ingest refusal, upload failed ("Try again", same set), `failed` (with stage and cause class, "Try again"), `needs_more_photos` ("Add photos", absent with 10 photos, and "Start over"), `needs_recapture` ("Start over"), session start refused ("Try again"); warning variant (`warning-surface`, 4 px `warning-edge`) for the Spend cap (no retry, "Start over" only), `queued` and Build quota.
UX-DR22: Scene frame: canvas ground, 12 px chrome mat, 1 px gilt rule, inner vignette on the mat, the photo from `GET /rooms/<room_id>/photos/<i>` contained (never cropped, enhanced, tinted or relit) at `rounded.sm`, letterboxing portrait photos; states: loading (mat with a plain line), reconnecting (status strip above, frame shrinks, photo dims to 60%, inputs disabled), play-through ended (photo dimmed under the plain Session-gone line on `chrome-raised` with "Start again").
UX-DR23: Hotspot: one per Interactable on the photo, the union of its polygons, id equal to the Interactable id; invisible at rest with a pointer cursor; hover shows a 2 px lamp outline, 1 px dark halo and 35% glow fill (150 ms); focus traces the two-tone ring along the polygon and shows the label chip; "Show all objects" draws a 2 px dashed `hotspot-show-all` outline with halo, no fill, no labels; a clicked non-target shows its label chip only; a collected `find` target's glow fades out over 200 ms while its Inventory item fades in, and clicking it again shows "{label} · in hand"; click or Enter posts `click` (or only the `use_on` input while an item is selected); Tab order by polygon centroid, top to bottom then left to right; accessible name is the label with the role of a button.
UX-DR24: Hotspot label chip: a parchment chip in `label` type anchored 8 px above the polygon's top edge; shown for as long as the Hotspot has keyboard focus; after a non-target click it fades after 2 s or on pointer leave; never shown on hover alone.
UX-DR25: Thumbnail strip: 96 x 72 thumbnails in upload order with 8 px gaps, scrolling horizontally inside its row only; current photo has a 2 px lamp border and is announced as current, hover `lamp-strong`, others at 80% opacity; click or Enter switches the Scene; usable while a `use_on` item is selected.
UX-DR26: Inventory: a `chrome-raised` tray of 64 px slots, three across the 288 px tray, each item a 56 px crop with a `caption` label, dashed empty slots beyond the items; empty state is one dashed slot and "Nothing in hand yet."; a new item fades in over 200 ms paired with its Hotspot's glow fading out; an item is a drag source for `use_on` (60% in place while dragging, a 64 px drag image with `paper` shadow) and click or Enter selects it for select-then-click (2 px lamp ring), a second activation or Escape deselecting it.
UX-DR27: Wizard notes: a parchment sheet with 24 px padding, at least 280 px tall, scrolling inside the side column, one entry per available Puzzle in availability order separated by `parchment-rule`: a heading row "Puzzle {n}" (`display-sm`, n = the Puzzle's fixed order number) with a plain evidence count at its right end ("{k} evidence cards", changing in place with no highlight or announcement), the Riddler portrait (32 px) beside the Clue (`wizard-line`), the Clue card slot when the Room has Clue cards, the Evidence cards directly under the Clue, Lore (`lore`, `ink-muted`), opened Rungs and the lock input; the Active puzzle (from `active_puzzle_id`, else the first available Puzzle) carries a 3 px `lamp-ink` left rule plus "Current"; newly available entries fade in; an open entry collapses to one line with the Open chip; hidden Puzzles are not drawn, except an entry an accepted Merge just hid, which leaves "Puzzle {n} now waits on another puzzle." (focus inside moves to it); a Shortcut reveals an entry only when it has no other unmet prerequisite.
UX-DR28: Clue card slot (Tier 1.5, FR-37): 112 x 84 px, `rounded.sm`, right-aligned beside the Clue with the Clue wrapping to its left, drawn only when the Room has Clue cards; placeholder (`clue-card-placeholder` fill, dashed edge), ready (the image, alt = the Clue, visible Clue hidden from assistive technology), blank on failure (flat, no edge, hidden from assistive technology); same size in every state so the layout never shifts.
UX-DR29: Wizard portrait: a circle with a 2 px gilt ring at 24 px (Card log, Demo room card, Model table), 32 px (signature, In play block), 48 px (Hint area, Cards, Architect and Riddler introductions, Completion sign-off) or 96 px (Greeting and First-room welcome); decorative (empty alt) beside text that names the speaker, with a visually hidden speaker prefix on every in-character line ("The Guide:"); Guide thinking state (Local only, while a Hint request or a Greeting is in flight): a static lamp ring plus the "thinking on this Mac" label (`pending-ink` on parchment), no pulse; arrival: one lamp-glow fade on the ring, 300 ms in all, when a Rung arrives unrequested (lit ring held 2 s under reduced motion); placeholder: the wizard's initial in `display-sm` gilt on `chrome-raised`.
UX-DR30: Hint area: a `chrome-raised` tray pinned at the bottom of the side column, up to 320 px: a scrolling upper part (at most two Cards, newest on top, older ones behind "{n} more in the Card log", then the latest Rung line) over a pinned lower part that never scrolls (hint field and "Ask the Guide", the helper line, the Triggers toggle); while the Triggers panel is open only the newest Card stacks and the area may grow until the Wizard notes reach 280 px; after "Begin" it holds the opening line as the first Guide line (not announced again); arrival glow on the tray edge with the portrait's; open pick: letting the area also grow while the first Card with the Trickster introduction is present (EXPERIENCE.md Open Items).
UX-DR31: Rung line: the one home for Hint replies: Guide portrait (48 px), the label "Puzzle {n} · Nudge|Direction|Near-answer" in `label` `lamp`, the line in `wizard-line`; the No-hint line uses the same anatomy labelled "Puzzle {n}"; a new Rung replaces the previous line, which stays under "opened Rungs" in its Puzzle's entry; every reply to a Hint request visibly arrives (a repeated reply fades out and in, 200 ms each way, and is announced again; Local may reword a repeat, never adding content); phrased and verbatim Rungs look identical with no badge; after the near-answer a further request repeats it; no thinking state in Hosted mode.
UX-DR32: Hint field and Ask the Guide: a 44 px `chrome` field with `body-sm` text and the placeholder "Stuck? Ask the Guide for a hint" beside the primary button "Ask the Guide", with the permanent helper line "Your words stay in this browser. The Guide only hears that you asked." under them; Enter or the button sends one Hint request for the Active puzzle with `puzzle_id` omitted (named explicitly only while `active_puzzle_id` is null); the accessible label is "Ask the Guide for a hint on Puzzle {n}"; typed text never leaves the browser; while sending the field is read-only with the text visible and the button reads "Asking", and the field clears when the reply lands; an empty field still sends; one request in flight at a time; open pick: a shorter placeholder in the 340 px band.
UX-DR33: Triggers panel: a toggle row "Triggers ({n})" (secondary, expanded state) that opens a `chrome` list capped at 160 px and scrolling, headed by one plain line "Nudge after {threshold} s idle or 3 wrong attempts · next hint no sooner than {spacing} s" (each number with its 1× value at a Demo timescale above 1) plus the source ("Set by how you played last time (kept in this browser)" or "Default for a first room"), then one row per Rung change in `body-sm` with `mono-sm` numbers: Puzzle, Rung name, cause ("Idle 92 s", "3 wrong attempts", "Loosen card") and where it was worded ("worded on this Mac · 1.6 s" or "as written"), newest last and in `text`, older rows `text-muted`, newest kept in view; collapsed by default, opened automatically when the page loads with a Disclosure active (the player can collapse it); empty reads "No hint changes yet."; under cut 5 the same content fills a second window.
UX-DR34: Code field: an inset on the Puzzle entry, `parchment-shade`, `mono-code`, sized for 6 characters (168 x 44), no visible label or placeholder, accessible name "Code for Puzzle {n}", with a secondary Submit disabled below 3 characters; Enter or Submit posts the code lock input; pending makes the field read-only with the Checking chip; wrong shows "Not this · n", keeps the value and selects it for retyping (`lamp-ink-hover-fill` tint with a 1 px `lamp-ink` edge); open shows the Open chip and removes the field.
UX-DR35: Order click progress: the one home for the order rules: in the order Puzzle's entry a "Start the sequence" control (secondary, `lamp-ink`) and 3 to 5 pips (10 px) with a visually hidden "{filled} of {length}" description; unarmed pips stay empty and clicks are exploration; "Start the sequence" posts the order start input and the control reads "Stop the sequence" (a label change that keeps focus); armed, each Hotspot click the server acknowledges fills the next pip in `lamp-ink` whichever object it hit (never optimistically); a full-length mismatch turns the pips `wrong-ink` for 300 ms, empties them and shows "Not this · n" with the sequence still armed; "Stop the sequence" posts the order stop input and empties the pips with no Wrong attempt; starting another order Puzzle first stops the armed one; the armed state survives Scene switches and reloads; pips never show which clicks were right.
UX-DR36: `use_on` drag: dragging an Inventory item over the Scene shows the hover state on the Hotspot under the pointer; dropping on a Hotspot posts `lock_input` `UseOnInput {item, target}` with no `puzzle_id`, and dropping elsewhere cancels and posts nothing; until the verdict the target's label chip shows with the Checking chip beside it; the verdict ("Not this · n" or "Open") shows in the resolved Puzzle's entry, which becomes the Active puzzle; a pair resolving to no Puzzle counts nothing and only clears the Checking chip.
UX-DR37: `use_on` select-then-click: selecting an Inventory item rings it in lamp and pins a parchment chip "Using {item label}" with "Cancel" to the top-left of the Scene frame; the next Hotspot click or Enter posts the same `UseOnInput` as a drop and no `click`, then clears the selection, with the same feedback as a drop; switching thumbnails keeps the selection; Escape or Cancel clears it (chip fades out).
UX-DR38: Feedback chips: outlined `label` chips, word first, never icon-only: "Checking" (pending, dashed `pending-ink`, static ellipsis, from submit until the verdict, not announced), "Not this · {n}" (`wrong-ink`, until the next input on that lock), "Open" (`success-ink`, held 1200 ms, then the entry collapses and the next Puzzle appears); the chip text is the lock input's accessible description, and "Not this" and "Open" are written to the live region.
UX-DR39: Evidence card: an inset `parchment-shade` row directly under the Clue: 64 px thumbnail crop (`rounded.sm`), the Interactable label (`label`, `ink`) and the read attribute (`body-sm`, `ink-muted`) describing where to look, never a solution token; one state only; real and Decoy cards are pixel-identical in the stable order `PlayView` gives; a new card gets no highlight, badge, animation or announcement beyond its entry's ordinary fade.
UX-DR40: Trickster card, accepted: a parchment card in the Hint area with a 4 px `success-ink` left edge: Trickster portrait (48 px) beside the sentence in `wizard-line` first, then the outcome label "Validator passed · {type} · Puzzle {n}", and a dismiss control (32 px hit area, named "Dismiss card"); enters after the lock-open state with a 200 ms fade, stays until dismissed (focus then moves to the next Card, else the hint field), is copied to the Card log and announced once; a Loosen Card's Rung also appears as a Rung line; the first Card of the Session, whatever its outcome, carries the Trickster's introduction above the sentence ("The Trickster", role line, voice line), never repeated on later Cards, in the Card log or after a reload.
UX-DR41: Trickster card, rejected: the same anatomy with a 4 px `wrong-ink` edge: the sentence "The Validator says that wouldn't be fair. Spoilsport.", the label "Validator refused · {type} · Puzzle {n}", then two plain `body-sm` lines: "Proposed: {structural summary}" (type and Puzzle numbers only) and "That change was refused. {fixed message}"; shown only for a Validator failure on a proposal; the reason is never styled in character; the Effective room is unchanged; the same first-Card introduction rule.
UX-DR42: Trickster card, skipped: off the paper on `chrome-raised` with a dashed `hairline` edge, the portrait at 60% opacity, the sentence "I'm keeping quiet this time. Enjoy it while it lasts." in `card-skipped-text`, then the label "Skipped"; the same look and text for a provider error and the Spend cap; play never pauses; no Card at all once the seventh call would be needed; the same first-Card introduction rule.
UX-DR43: Card log: a modal dialog anchored under the top bar's "Card log" button over the scrim (below the top bar), 360 px wide, at most 480 px high and scrolling, entering with a 300 ms fade: a close control, then every Card of the play-through oldest first, each row with a 24 px portrait, the sentence in `wizard-line`, the outcome label, a rejected Card's "Proposed: …" line and reason, and the session time in `mono-sm`; empty reads "No cards yet in this play-through."; opens from the top bar or the "{n} more in the Card log" link; focus trapped (first on close), Scene, Hotspots and top bar inert; Escape or close returns focus to the opener; dismissing a Card never removes it from the log.
UX-DR44: Completion screen: the last Scene dimmed under the scrim with a centered 720 px parchment sheet (48 px padding): heading "The room is open." (`display-lg`), the Guide's sign-off (48 px portrait, one `wizard-line` line chosen from the stats only: no Rungs "Not a single hint. I'm almost offended.", 1 to 3 "You let me help a little. I enjoyed every word.", 4 or more "We solved it together, and I'd do it again."), "Time", "Hints used" and "Wrong attempts" three across in `mono-timer`, a per-Puzzle time table ("Puzzle {n}" rows, no header row, no Exit mark), "Build another room" (primary) and "How this room was built" (secondary), and under cut 2 "Save profile file"; appears automatically after the Exit puzzle's open state, reads `GET /sessions/<id>/result`, records the Room result once (demo-flagged above timescale 1), focuses the heading, announces the sign-off once; the top bar keeps its Play controls inert and the Timer frozen; a Hosted Judge room adds "Deleted Tue Nov 10" as a plain `chrome-raised` strip below the sheet, off the paper.
UX-DR45: Greeting and First-room welcome: over the first Scene, a 560 px parchment card over the scrim (300 ms fade): the Guide's introduction (96 px portrait, heading "The Guide", the mode's role line), the opening line in `wizard-line-lg`, the voice line "Get stuck as often as you like. I'll help, a little at a time.", and "Begin" (primary, left-aligned, the only control and the only way to dismiss; Escape never dismisses); the line comes from `POST /sessions` `opening_line` (Greeting when `sessions` ≥ 1 in Local mode; First-room welcome "Welcome to your own room. Find what doesn't belong." otherwise and always in Hosted mode; the Demo room variant "Welcome to someone else's room. Find what doesn't belong." on a Demo room); while a Local Greeting is phrased (`phrasing` true, text null) the card shows the thinking state, polls every 2000 ms, has no "Begin" yet and keeps focus on its heading, falling back silently to the template after 5 s; focus trapped on "Begin" once shown; announced once as "The Guide. {role line} {opening line} {voice line}", the dialog labelled by its heading only; under the First-room welcome a one-time plain tip on the scrim, "Tip: 'Show all objects' in the top bar outlines everything you can click."; not shown again on reload once play has events.
UX-DR46: Leave room confirmation: a plain 480 px `chrome-raised` card (never parchment) over the scrim, heading in `display-sm`, the sentence "Leave this room? This play-through won't be recorded.", "Keep playing" (primary, focused) and "Leave room" (secondary); opened by "Leave room" or the browser Back button on the Play screen; Escape means "Keep playing" and returns focus to "Leave room" (or the first Hotspot after Back); confirming records no Room result and goes to the Capture screen (Local) or the Hosted landing (Hosted).
UX-DR47: Deleted Judge room notice: the page body with a centered 480 px `chrome-raised` card (same card as the Leave room confirmation, no scrim): heading "This room is gone", body "This room was deleted on Tue Nov 10, as promised.", "Go to the demo rooms" (primary); shown when a room-keyed route answers 410 `room_deleted`; an unknown room (404 `room_not_found`) uses the same card with "Keyframe can't find this room" / "Check the link, or start from the beginning." and "Go to the demo rooms" (Hosted) or "Build a room" (Local); focus on the heading.
UX-DR48: Build view header: a `chrome` row with the Room's name as the title (`display-md`), or its build time ("Tue Nov 3, 10:42") when it has none, the build time beside a named title, "Regenerations: n of {max}" with `mono-sm` numbers, one plain "Attempt {k} sent back: {fixed messages}" line per failed attempt, and "Back" (secondary) returning to where the view was opened; initial focus on the title.
UX-DR49: Build view mask overlays: a static grid of the Room's photos, three across at 4:3, each with every Interactable's mask filled (`mask-overlay-fill`) and stroked (2 px lamp with dark halo) and its label on a focusable parchment chip; box-rectangle Hotspots draw the same way.
UX-DR50: Build view puzzle graph: laid out left to right with the Exit puzzle rightmost; 168 x 64 parchment nodes showing the Puzzle order number and Lock type in `mono-sm`, `requires` edges in `graph-edge` with 8 px arrowheads, the Exit node with a 3 px lamp double ring and an "Exit" label in `lamp-ink`, and a Dry run marker in each node's top-right corner (8 px dot plus "pass", "fail" or "skipped" in `success-ink`, `wrong-ink` or `ink-muted`); nodes focusable in Puzzle order with the accessible name "Puzzle {n}, {lock type}, requires {list or none}, Dry run {verdict}" plus "Exit"; not interactive beyond focus.
UX-DR51: Build view Validator verdict table: a real `<table>` on `chrome` with no heading, the plain caption "The Validator is code, not a model. It checks these 8 rules on every draft; a failed rule sends the draft back to the Riddler." above it, header cells "Rule", "Check", "Verdict" in `label` `text-muted`, one row per rule (rule number in `mono-sm`, the check-phrased name, the verdict word with an 8 px `graph-pass` or `graph-fail` marker), and the rule's fixed message shown only on a fail row; rule 9 joins after the decoy pick; fits without horizontal scroll at 1280 px.
UX-DR52: Build view Dry run rows: one row per Puzzle ("Puzzle", "Lock type", "Verdict") under the caption "A separate muse-spark-1.3 call saw only the clues, hints and object names, never the answers, and tried every puzzle."; under cut 4 every row reads "skipped" in `graph-skipped` and the caption becomes "The test run was switched off for this build, so no puzzle was tried blind."
UX-DR53: Build view Model table: first in the right column so it sits above the fold at 900 px; columns "Role", "Model", "Where it ran", "What it did", "Cached or billed"; one row per role and model with a 24 px portrait and the wizard's name (Architect and Riddler rows add their role line as a full-width row under them; a wizard with two models takes one row per model), model ids in `mono-sm`, "what it did" built from provenance counts ("found 9 objects", "outlined 9 objects", "wrote 5 puzzles", "tried 5 puzzles blind"), cached or billed as words with both counts when mixed ("3 billed · 9 cached"); fixed rows for the Validator ("code, no model", "checked 8 rules", empty cached cell), the Dry run (its model and host; "skipped" under cut 4) and Muse Image ("muse-image-1.0", "painted the four portraits, once"; its cached-or-billed cell is an open pick); no Guide or Trickster row; the caption under it: "Cached means an identical earlier call was served from the cache, unbilled; billed means it ran live and was paid for."
UX-DR54: Build view In play block: a fixed `chrome` panel under the Model table filled from `GET /meta`, not provenance: the Guide row (32 px portrait, "The Guide", role line, then the Guide model and host: Llama 3.2 3B on "Ollama on the Mac" in Local mode, or in Hosted mode "Hints are shown as written here. In Local mode, Llama 3.2 3B rewords them on the Mac.") and the Trickster row (32 px portrait, "The Trickster", role line, then "Source: live", "Source: scripted" or "Source: written in advance"); static.
UX-DR55: Build view BuildView JSON: a collapsed pane under the mask overlays behind "Show the build JSON" (secondary toggle, expanded state); open shows the caption "Everything this page receives. It holds no answers; a sentinel test checks every build for them." and the build data exactly as served, pretty-printed in `mono-sm`, at most 360 px high, a focusable scrollable region; nowhere on the Build view is an answer, Clue-to-answer pairing or Dry run answer shown or fetched, and Clues are not repeated.
UX-DR56: Disclosure banner: a full-width strip above the top bar on `disclosure-surface` with a 1 px `disclosure-edge` and `disclosure-text` in `body-sm`, `rounded.none`, one line per Disclosure (32 px per line), no icon, no close control, no controls, taking no focus, read as page content; rendered exactly as served: the session state's per-Room list on the Play and Completion screens, `BuildView`'s list on the Build view, `GET /meta` `disclosure` on the Capture screen and Hosted landing; absent when the list is empty; identical on every surface, pinned with the top bar while the Build view scrolls, never covered or dimmed by a scrim, never overlaying the Scene or a Hotspot.
UX-DR57: Hosted landing: the Disclosure banner, the top bar without the Timer, then a title block ("Keyframe" in `display-lg`, the subtitle "An escape room built from your own photos.", the plain pipeline line naming muse-spark-1.3, sam-3.1, the blind test run and the Guide, and the lead-in "Short on time? See how a room is built and checked." with the "How a room is built" link opening the first Demo room's Build view); below, Demo room cards three across in the left area and the Access-code build in the 400 px right column, so both paths show at once; no separate band of wizards; cards from `GET /rooms` (Demo rooms only); initial focus on the first Demo room card.
UX-DR58: Demo room card: one per `RoomSummary` on `chrome-raised`, `rounded.lg`: a 4:3 cover photo, the Room's name (or build time) in `display-sm`, "{n} puzzles · 15 to 25 min", the four Wizard portraits at 24 px (one accessible name, "The Architect, the Riddler, the Guide and the Trickster"), and a footer with a decorative 96 px mask-and-graph thumbnail and "How this room was built" (secondary); hover lamp ring plus glow, focus ring on the card and separately on the link; click or Enter starts a Session with a fresh Derived block (then the Demo room welcome); a refused start shows the session-start-refused banner at the top of the landing's left area.
UX-DR59: Access-code build: a right-column panel with the heading "Build your own room", a 44 px `mono-code` field labelled "Access code" and the primary button "Check code", and a `body-sm` status line; checked with `POST /access/check {code}` before photo selection; states: empty submit ("Enter the access code from the submission."), checking (button pending label), refused (compact error banner "That access code isn't right. No photos were sent."), too many tries (compact warning "Too many tries. Wait a moment, then check the code again."), accepted ("{n} of 20 builds left" in `success`, then the Capture screen with the code held for `X-Access-Code`), quota reached (warning "All 20 judge builds have been used. The demo rooms are still open.", Demo room cards stay active); `POST /builds` re-checks, so a quota reached in between shows the quota warning on the Capture screen; the code is kept for the tab's lifetime only, never stored.
UX-DR60: Narrow-screen message: below 1024 px the whole app is replaced by the canvas with a centered plain `chrome-raised` card (never parchment), at most 480 px wide with 16 px side gutters, holding the wordmark, the heading "Keyframe needs a bigger screen" (`display-sm`) and "Open this page on a laptop or desktop browser to play." (`body-md`); single state, no horizontal scroll at any width; above 1024 px the app returns with its state intact.
UX-DR61: Server unreachable (cold load): while `GET /meta` fails, the page body is empty except a centered status strip "Keyframe can't reach its server. Retrying.", retrying every 2000 ms, with no Disclosure banner, Retention summary or Scene guessed; replaced by the surface once the server answers.
UX-DR62: Capture screen states (EXPERIENCE.md State Patterns): cold load waits for `GET /meta` before the before-upload layout (right column in order: Input requirement "6 to 10 JPEG photos" standing alone, the iPhone tip, the faces, documents and belongings reminder, then the Retention summary; left the dropzone; stored Rooms below in Local mode); empty (Upload disabled, "No rooms yet."); photos chosen; refused at the picker; pending upload (Timer running from T0, dropzone disabled); upload failed (banner, photos kept, Timer stops and restarts at the next Upload); reconnecting during a Build; Build running; `done` (every stage done with result and model, the "How this room was built" link, then automatic Play); session start refused; error and warning end states with photos visible and the Timer stopped; everything except the Retention summary and banners disabled during a Build; initial focus on "Choose photos", a new banner takes focus, the status strip never does.
UX-DR63: Build job status rendering: `GET /builds/<job_id>` polled every 2000 ms drives the Capture screen: `queued` (Hosted; all stages pending, warning "Another room is being built. Yours is in line and will start on its own.", Timer shows "queued"); `running` with `stage` (that row running, earlier rows done with durations, the Mask preview once segment completes, Regeneration rows when the attempt count rises); `done`; `failed` with stage (heading "The build stopped while {stage label, lowercased}." plus "A model service didn't answer." or "The build stopped unexpectedly.", Hosted adds "Trying again uses one of the remaining judge builds.", "Try again"; for `spend_cap_exceeded` the warning with "Keyframe has reached its spending limit, so this room can't be built right now." and "Trying again won't help until the limit is raised; your photos are still here.", "Start over" only); `needs_more_photos` (stopped at "Finding objects"; "Keyframe found too few objects to build a room." with the add-photos body or the 10-photo body; "Add photos", "Start over"); `needs_recapture` (stopped at "Testing the room"; "Keyframe couldn't build a fair room from these photos." / "Try brighter, closer shots where labels and printed text are readable."; "Start over"); envelope codes mapped (`too_few_interactables`, `spend_cap_exceeded`, `provider_error`, `unsupported_image`, `build_quota_exceeded`, `room_deleted`, `room_not_found`); the UI keys on job status, with no exhausted-regeneration error class.
UX-DR64: Greeting and First-room welcome states: loading (Local Greeting only: introduction, voice line and static thinking state for up to 5 s plus one poll, no "Begin", focus on the heading); success (line shown, "Begin" focused, announced once); fallback (template line appears silently after 5 s or when Ollama is unreachable); after "Begin" the line stays in the Hint area as the first Guide line, not announced again; a welcome and every Hosted session skip the loading state.
UX-DR65: Play screen states: cold load (`GET /sessions/<id>` and `GET /sessions/<id>/room`, loading line until the first photo and its Hotspots are live); reload (resumes from the Event log: first Scene, Inventory, open locks, current Rungs, Cards in the Card log only, frozen Timer; no Greeting once play has events; nothing re-announced); empty (Inventory and Card log empty lines; Hint area with controls only); pending per lock and per Hint request; polling every 2000 ms (new `rung_change` gives a Rung line, a Triggers row, an announcement and one arrival glow; new `trickster_card` gives a Card and an announcement; a changed `room_revision` refetches the Effective room and re-renders the notes and Hotspots; continues while the tab is hidden); Trickster request (when polled state shows an open window the client posts `POST /sessions/<id>/trickster` once, with no visible pending state); hint reply (no arrival glow); Ollama timeout fallback (silent, Triggers row "as written"); success (Open chip 1200 ms, entry collapses, next Puzzle fades in, collected item fades in, then any Card); Merge hiding the entry in use; Wrong attempt (no shake, no sound); skipped Card; refused input (not a Wrong attempt; only clears the Checking chip); reconnecting (two missed polls; Scene dims, inputs disabled, strip above the frame; an unsent input is dropped, the Code field keeps its value); Session gone ("This play-through has ended. Start the room again." with "Start again"); deleted or unknown room cards; focus rules after the Greeting (first Hotspot), after a lock opens (next entry heading), after a Card dismiss, after "Keep playing" and after the Card log closes.
UX-DR66: Completion screen states: loading (sheet with stats pending until the result returns); success (stats, actions, Disclosures; the Room result written once); error ("Keyframe couldn't load the result. Retrying." every 2000 ms, "Build another room" still available).
UX-DR67: Build view states and layout: the Disclosure banner and top bar (wordmark and mode indicator only) pinned while only the body scrolls; full-width body with no side column: header row, then a left two-thirds column (puzzle graph over the mask overlays grid, then the collapsed JSON pane) and a right third (Model table, In play block, verdict table, Dry run rows), every table fitting at 1280 px; cold load fills panels from `GET /builds/<job_id>/view` and the In play block from `GET /meta`; not ready ("This room is still being built." with a link to its Capture screen, no panels); error ("Keyframe couldn't load how this room was built." with "Try again"); reachable from the Capture screen on `done`, the Completion screen, a stored Room row and each Demo room card and the landing link, with no Access code; under cut 0 the surface and every link to it are absent.
UX-DR68: Hosted landing states: cold load (`GET /meta` with the Hosted Disclosure, then `GET /rooms`); Demo rooms failed to load ("Keyframe couldn't load the demo rooms." with "Try again", the title block and Access-code build still usable); no Demo rooms ("No demo rooms are open right now. You can still build your own room with the access code.", the "How a room is built" lead-in and link hidden); session start refused (banner at the top of the left area, focused); the Access-code states of UX-DR59.
UX-DR69: Accessibility floor, Hotspots and alternatives (NFR-14 items 1 to 3, AD-11): each Hotspot is a focusable element in the three.js scene's accessible overlay (same ids in the DOM-only fallback) with the focus ring traced along the polygon and the label chip as its visual name; Enter acts as a click; the "Show all objects" top-bar toggle (pressed state announced) outlines every Hotspot, persists across Scene changes within the Session, and draws outlines only; `use_on` works by select-then-click posting the same `UseOnInput` as a drop and no click.
UX-DR70: Live region: exactly one `aria-live="polite"` region receiving only Rung lines (including the No-hint line), Cards, the Greeting or First-room welcome, the Completion sign-off, the reconnecting line and lock outcomes ("Puzzle {n}: not this, {count}." and "Puzzle {n}: open.", an addition above the floor); every in-character line prefixed with its speaker; Cards read "The Trickster: {sentence} {outcome label}." plus a rejected Card's "Proposed" line and reason, and the first Card reads "The Trickster. {role line} {voice line} {sentence} {outcome label}."; replies to explicit Hint requests always announced, even when repeated; polled Rungs and Cards announced once each; "Checking" never announced; nothing re-announced on reload.
UX-DR71: Keyboard order and modal focus: Tab and Shift+Tab follow top bar → Scene Hotspots → Thumbnail strip → Inventory → Wizard notes → Hint area; Enter acts as a click on Hotspots, thumbnails, Inventory items, Demo room cards and graph nodes, and submits the Code, hint and Access code fields; Escape closes the Card log, cancels a `use_on` selection and means "Keep playing", but never dismisses the Greeting; no single-key shortcuts; modals trap focus and make the Scene, Hotspots and top bar inert; Build view Tab order runs header title, "Back", Model table, In play block, verdict table and Dry run rows, graph nodes, mask label chips, JSON toggle; tables are real `<table>` elements with header cells.
UX-DR72: Contrast and color-not-alone: every text and state pair meets WCAG AA on the dark theme per the `DESIGN.md` contrast table (4.5:1 body text, 3:1 large text and non-text UI), checked by an audit; hairline is decorative only; every state carries a word ("Not this", "Open", "skipped", "Current", "cached", "billed") and never relies on color or an icon alone; the two-tone focus ring and the haloed Hotspot outline hold on dark chrome, parchment and any photo.
UX-DR73: Copy register and general rules (EXPERIENCE.md Voice and Tone as the string source): in-character lines (Rungs, the No-hint line, the Greeting, the First-room welcome, Card sentences, Clues, Lore, the Architect's stage lines, wizard voice lines, the Completion sign-off) set in the serif body with the speaker's portrait; plain messages (errors, upload failure, `failed`, `needs_more_photos`, `needs_recapture`, `queued`, Spend cap, quota, Access code, session start refused, deletion, Retention summary, Privacy line, helper line, reconnecting, mode indicator, pipeline line, Build view captions, Disclosures) in the sans, no portrait, never on parchment, no jokes; plain labels and chips may sit on paper; sentence case, no exclamation marks, no emoji, no "Oops", no "successfully", digits for numbers, no solution token in any line, wizard lines naming objects only in a Clue, an Evidence card, a Rung pointing where to look or the Architect's found-objects line; verbatim strings are never paraphrased ("6 to 10 JPEG photos", "the player profile stays on your machine.", "Keyframe needs 6 to 10 JPEG photos.", the Spend cap error, "{n} of 20 builds left", "Deleted Tue Nov 10", "Ask the Guide", "Build another room", the Disclosure lines).
UX-DR74: Wizard introductions: each wizard is introduced in place where it first works, with name, plain role line naming its model and one voice line, never in a separate band: the Architect at the top of the Stage list ("Reads your photos with muse-spark-1.3, names the objects, and draws their outlines with sam-3.1." / "I notice everything. Mostly mugs."); the Riddler in the "Writing puzzles" row ("Reads the objects; writes the puzzles with muse-spark-1.3, then a test run that never sees the answers checks each one can be solved." / "I taught your things to talk. Pity they only speak in riddles."); the Guide on the Greeting or First-room welcome card (Local role line ending "worded by Llama 3.2 3B on this Mac.", Hosted and verbatim ending "shown as written." / "Get stuck as often as you like. I'll help, a little at a time."); the Trickster on its first Card of the Session ("Reads the game state; proposes changes between puzzles with muse-spark-1.3, and the Validator checks each one." / "I like to move things around. The Validator keeps me honest, sadly.").
UX-DR75: Capture, Play and Hosted exact strings: implement the EXPERIENCE.md Voice and Tone tables as the single string source: Capture (iPhone tip, reminder, "Choose photos" / "Upload", "Remove photo {n}", "Not a JPEG", "{n} photos chosen", 422 and upload-failed copy, stage names, Regeneration label, done-row results, Architect stage lines and the mask-preview line "I see {n} things worth a closer look, starting with the {label 1}, the {label 2} and the {label 3}." with its two-label case, Hosted lines, end-state copy, "Play this room"); Play (placeholder, accessible labels, helper line, "Asking", "thinking on this Mac", "Puzzle {n}", "{k} evidence cards", Rung labels, Merge placeholder, order controls and description, "{label} · in hand", "{n} more in the Card log", chips, "Nothing in hand yet.", "Using {item label}" / "Cancel", Triggers strings, top-bar labels, Leave room, reconnecting, Session gone, unknown room, Card log empty); Hosted landing (title, subtitle, pipeline line, lead-in, card meta, Access-code strings, demo-room load and empty lines).
UX-DR76: Guide and Trickster line rules and fixed strings: the Rung ladder (nudge says where to look, shortest; direction what to notice; near-answer how to use it, at most two sentences; never "the answer is"; lengths increase), enforced in the Riddler prompt; the fixed No-hint line "A fair ask. Look around a little longer; I'll speak up if you stay stuck." (no clue, no interruption: an ordinary Rung line, no modal, no focus move, no blocked input); the Greeting template chosen by the Derived block (null `time_to_first_hint_s`: "Welcome back. Last time you never asked me once; let's see what this room makes of you."; persistence ≥ 0.34 "…kept going long past my first nudge…"; −0.33 to 0.33 "…held out a good while before asking…"; ≤ −0.34 "…held out just long enough to get your bearings before asking…"); phrasing rewords and never adds content; Card sentences (Decoy "A new evidence card has appeared. I do love a crowded desk."; Merge "One puzzle now waits on another. Patience builds character; I build locks."; Loosen "The Guide is feeling generous: a hint just opened early. Don't tell anyone I allowed it."; Shortcut "One puzzle no longer waits on another, so it may turn up sooner. Solving it is still on you."), labels naming the Validator, and "Proposed:" summaries in ids and numbers only.
UX-DR77: Validator check names and fixed messages: one table serving the Build view verdict rows, the regeneration prompt, the "Sent back" lines and the rejected Card: rules 1 to 9 with their check-phrased pass names ("No two locks wait on each other" … "False evidence follows the decoy rules") and neutral fixed fail messages ("Two locks would wait on each other forever." … "A false clue breaks the decoy rules."), plus the `validate_edit` bounds message "The change is outside the Trickster's limits."; no message ever contains a token; a pass row never prints the fixed message.
UX-DR78: Build view, Completion and deletion strings: the four Build view captions plus the cut 4 caption, header cells for the Model table, verdict table and Dry run rows, host names ("Meta Model API", "this Mac", "Ollama on the Mac"), Trickster source strings, the untitled-Room build-time format; Completion heading, sign-off lines, stat labels ("Time", "Hints used", "Wrong attempts", "Time per puzzle"), actions; "Deleted Tue Nov 10" and the Deleted Judge room notice copy.
UX-DR79: Disclosure and retention copy: the server composes every Disclosure line (AD-15) and the client renders them as served: "Hint and Trickster timings run at n× speed; the build timer is real time."; "Trickster proposals replayed from a recording; the Validator ran live."; "Trickster proposals were written in advance; the Validator ran live on each." (cut 1); "Hosted mode: hints are shown as written; no hint model runs here."; per-Room "This room was built earlier, on {date}."; the Retention summary text per mode as served (shared opening naming the Meta Model API standard tier and the Baseten or Fireworks fallback; Local ending "A copy of your photos is also kept on this computer."; Hosted ending naming Modal storage, Tue Nov 10 deletion, 24 h logs and no profile data leaving the browser; fal.ai and voice lines only when those ship); final wording owned by PRD §13 Q3.
UX-DR80: Demo mode and Disclosure behavior: global lines from `GET /meta` read once per page load, Room-bound surfaces (Play, Completion, Build view) rendering their Room's own list; the client never composes or edits a line; while any Disclosure is active the Triggers panel opens automatically and the Completion screen keeps the banner; the UI has no demo-only path that injects events, Rungs, Greetings, Cards or Build output; Scripted Trickster Cards render exactly like live ones; if `GET /meta` fails no surface renders, so a missing Disclosure never reads as no shortcuts in effect.
UX-DR81: Hosted mode differences (EXPERIENCE.md, the one home): entry on the Hosted landing ("Build another room" and "Leave room" return to it); the Hosted Disclosure always shown plus the Trickster-source line when scripted or cut 1 and the earlier-builds line on Demo rooms; mode indicator "Hosted mode"; Rungs verbatim with the same anatomy, no thinking state, every Triggers row "as written", the Guide's hosted role line; Session start always sends a fresh Derived block and the opening line is always the First-room welcome (Demo room variant on Demo rooms); Access code before photo selection, 20-build quota, `queued`, the Build URL resuming after the tab closes; Timer "queued" and the queue note; the Hosted Retention text; "Try again" names the judge-build cost; "Deleted Tue Nov 10" on Judge rooms and the notice after deletion; Demo room cards instead of the stored Rooms list; supported on current desktop Chrome, Safari and Firefox at 1280 px or wider; open pick: whether hosted Demo rooms run at a Demo timescale (beside §13 Q11).
UX-DR82: Privacy behavior in the client: raw photos are sent only in `POST /builds` and rendered only from `GET /rooms/<room_id>/photos/<i>`; typed hint text never leaves the browser and no copy implies the Guide read it; the Player profile lives in IndexedDB under the `?profile=` name with no viewer, export or delete control in v1; the client calls only its own server, so the Capture screen makes no request to a service the Retention summary does not name; the reminder about faces, documents and belongings sits after the Input requirement and iPhone tip and before the Retention summary.
UX-DR83: Wizard portrait art direction (for the FR-23 script): four `muse-image-1.0` prompts sharing one style block (oil painting, visible brushwork, single-candle chiaroscuro from camera left, warm umber, ochre and lamp-amber palette, near-black background close to `canvas`, head and shoulders in three-quarter view, square 1:1 at 1024 px, no text, no painted frame, no resemblance to a real person) with one subject line each (Architect with a brass loupe; Riddler with a half-smile and a sealed folded note; Guide kind and patient with a small lantern held low; Trickster with a sly grin, one eyebrow up and a playing card); faces in the center 70% for the circular crop.
UX-DR84: Cut variants in the UI: cut 0 removes the Build view and every link to it while the Stage list results and role lines still show what each model did; cut 2 adds "Open profile file" under the Privacy line and "Save profile file" on the Completion sheet with the line "Your player profile is a file on this computer; Keyframe reads it only when you open it."; cut 3 shows every Rung verbatim and the Greeting from the template; cut 4 turns every Dry run row and the Model table's Dry run row to "skipped" with the cut 4 caption; cut 5 opens the Triggers panel in a second window with the same content; cut 6 drops the order and `use_on` lock UI; cut 7 shows "attempt n of 1".
UX-DR85: Banned interactions and do's and don'ts: no sliding, bouncing or shaking (a Wrong attempt is play, not failure), no looping animation, no sound, no browser notifications, no offline mode, no free conversation with any wizard, no reveal or skip after the near-answer, no highlight on a new Evidence card, no dismissable Disclosure, no modal more than one level deep, no text over a photo except on a label chip, no image generation in play, no "verbatim" or "local" badge on a Rung line, no Greeting in Hosted mode, no portrait or serif body on a plain message, no plain message on parchment.
UX-DR86: Main demo legibility (EXPERIENCE.md shot list): each §11.3 beat's surface and state keeps its key text legible at 1080p: Mask preview label chips (0:00), the Stage list results and verdict caption (0:15), the held typed words, helper line and Rung label (0:35), the Triggers header with 1× values, newest row and Rung line in frame together with only the newest Card stacked (0:50), both Card labels with the "Proposed" line and reason (1:05, preferring a Merge or Loosen for the accepted Card), the mode indicator "profile demo · 1 room played" on the Greeting (1:20), the Model table ids and captions (1:35), and every Disclosure line (1:50).

### FR Coverage Map

Generated from the story covers fields (116 stories; every id below has at least one story; dependencies checked to point only backward by id).

#### Functional requirements

- FR-1: Epic 2: 2.10, 2.12, 2.16; Epic 6: 6.7
- FR-2: Epic 2: 2.7, 2.14, 2.15
- FR-3: Epic 2: 2.7, 2.13, 2.15
- FR-4: Epic 2: 2.15, 2.25
- FR-5: Epic 2: 2.10, 2.11, 2.12, 2.17, 2.18, 2.25; Epic 7: 7.7, 7.17
- FR-6: Epic 1: 1.14; Epic 2: 2.16; Epic 7: 7.2; Epic 9: 9.2
- FR-7: Epic 2: 2.19, 2.20
- FR-8: Epic 1: 1.6; Epic 2: 2.20
- FR-9: Epic 1: 1.6; Epic 2: 2.22, 2.23, 2.24
- FR-10: Epic 2: 2.21, 2.22, 2.24, 2.25
- FR-11: Epic 1: 1.7, 1.11, 1.12, 1.19, 1.20, 1.24; Epic 4: 4.1, 4.6
- FR-12: Epic 1: 1.8, 1.9, 1.12, 1.21, 1.26
- FR-13: Epic 1: 1.8, 1.12, 1.23; Epic 5: 5.1; Epic 6: 6.5
- FR-14: Epic 3: 3.3, 3.4; Epic 6: 6.5; Epic 9: 9.3
- FR-15: Epic 3: 3.1, 3.3
- FR-16: Epic 3: 3.5
- FR-17: Epic 3: 3.2, 3.3, 3.7; Epic 6: 6.7; Epic 7: 7.2
- FR-18: Epic 4: 4.2, 4.8
- FR-19: Epic 4: 4.1, 4.4, 4.5, 4.6, 4.7
- FR-20: Epic 1: 1.12; Epic 5: 5.1, 5.2, 5.3, 5.4, 5.6; Epic 7: 7.2, 7.17
- FR-21: Epic 1: 1.5, 1.13, 1.22; Epic 5: 5.1, 5.5, 5.6, 5.7, 5.8
- FR-22: Epic 5: 5.1, 5.2, 5.8
- FR-23: Epic 2: 2.7; Epic 3: 3.6
- FR-24: Epic 1: 1.10; Epic 3: 3.1, 3.5; Epic 4: 4.2
- FR-25: Epic 4: 4.3, 4.4, 4.8
- FR-26: Epic 1: 1.14, 1.17; Epic 4: 4.4; Epic 6: 6.2, 6.3; Epic 7: 7.2
- FR-27: Epic 2: 2.4, 2.5
- FR-28: Epic 2: 2.2, 2.3, 2.5, 2.10, 2.25; Epic 4: 4.4
- FR-29: Epic 2: 2.6, 2.12; Epic 7: 7.8, 7.9
- FR-30: Epic 2: 2.10, 2.20, 2.22; Epic 6: 6.7, 6.9
- FR-31: Epic 7: 7.3, 7.13, 7.14, 7.15, 7.16, 7.22
- FR-32: Epic 7: 7.7, 7.8, 7.10, 7.11, 7.12, 7.17, 7.22
- FR-33: Epic 7: 7.14, 7.18, 7.19, 7.20, 7.21, 7.22
- FR-34: Epic 8: 8.1
- FR-35: Epic 9: 9.1, 9.2, 9.3
- FR-36: Epic 1: 1.2; Epic 2: 2.7; Epic 6: 6.8; Epic 7: 7.1
- FR-37: Epic 7: 7.4, 7.5, 7.6
- FR-38: Epic 2: 2.27, 2.28, 2.29, 2.30, 2.31

#### Non-functional requirements

- NFR-1: Epic 2: 2.15, 2.17, 2.20, 2.24, 2.26; Epic 6: 6.6
- NFR-2: Epic 3: 3.7
- NFR-3: Epic 3: 3.7; Epic 6: 6.6; Epic 7: 7.2
- NFR-4: Epic 1: 1.2; Epic 2: 2.7, 2.8, 2.16; Epic 3: 3.7; Epic 4: 4.8; Epic 5: 5.5; Epic 6: 6.7; Epic 7: 7.1, 7.2, 7.18, 7.19
- NFR-5: Epic 1: 1.6, 1.7; Epic 2: 2.19, 2.20, 2.23, 2.24, 2.27; Epic 3: 3.3; Epic 4: 4.1, 4.8; Epic 5: 5.5; Epic 6: 6.4; Epic 7: 7.4
- NFR-6: Epic 2: 2.2, 2.3, 2.5, 2.6, 2.9, 2.26; Epic 7: 7.9, 7.22; Epic 8: 8.1
- NFR-7: Epic 2: 2.7, 2.10, 2.12; Epic 7: 7.7, 7.8
- NFR-8: Epic 1: 1.2, 1.3; Epic 2: 2.1, 2.9
- NFR-9: Epic 2: 2.7, 2.15
- NFR-10: Epic 1: 1.4, 1.19, 1.27; Epic 7: 7.3, 7.16, 7.22; Epic 8: 8.1
- NFR-11: Epic 1: 1.1, 1.5; Epic 3: 3.6; Epic 5: 5.8; Epic 6: 6.1, 6.4, 6.5, 6.6, 6.9; Epic 7: 7.3, 7.22; Epic 8: 8.1
- NFR-12: Epic 4: 4.3, 4.4; Epic 5: 5.8; Epic 6: 6.1, 6.2, 6.3, 6.4, 6.6, 6.7
- NFR-13: Epic 1: 1.1; Epic 6: 6.7, 6.8, 6.9
- NFR-14: Epic 1: 1.25, 1.26

#### UX design requirements

- UX-DR1: Epic 1: 1.16
- UX-DR2: Epic 1: 1.16
- UX-DR3: Epic 1: 1.16
- UX-DR4: Epic 1: 1.16
- UX-DR5: Epic 1: 1.16
- UX-DR6: Epic 1: 1.16, 1.25
- UX-DR7: Epic 1: 1.17, 1.27; Epic 4: 4.7
- UX-DR8: Epic 1: 1.17, 1.18, 1.23, 1.27; Epic 2: 2.18, 2.29; Epic 4: 4.7
- UX-DR9: Epic 1: 1.16
- UX-DR10: Epic 1: 1.16
- UX-DR11: Epic 1: 1.16, 1.25
- UX-DR12: Epic 1: 1.17; Epic 5: 5.1
- UX-DR13: Epic 1: 1.24; Epic 2: 2.25
- UX-DR14: Epic 2: 2.16
- UX-DR15: Epic 2: 2.16, 2.18, 2.25
- UX-DR16: Epic 2: 2.18
- UX-DR17: Epic 1: 1.22; Epic 2: 2.17; Epic 7: 7.17
- UX-DR18: Epic 2: 2.18; Epic 7: 7.17
- UX-DR19: Epic 1: 1.18; Epic 2: 2.31
- UX-DR20: Epic 2: 2.16; Epic 5: 5.4
- UX-DR21: Epic 1: 1.17, 1.18; Epic 2: 2.16, 2.25; Epic 7: 7.17
- UX-DR22: Epic 1: 1.19, 1.24
- UX-DR23: Epic 1: 1.19, 1.21, 1.25
- UX-DR24: Epic 1: 1.19
- UX-DR25: Epic 1: 1.19
- UX-DR26: Epic 1: 1.20, 1.26
- UX-DR27: Epic 1: 1.20; Epic 4: 4.6
- UX-DR28: Epic 7: 7.6
- UX-DR29: Epic 1: 1.20; Epic 3: 3.4
- UX-DR30: Epic 3: 3.4; Epic 4: 4.5
- UX-DR31: Epic 3: 3.4
- UX-DR32: Epic 3: 3.4; Epic 9: 9.3
- UX-DR33: Epic 3: 3.5; Epic 5: 5.7
- UX-DR34: Epic 1: 1.21
- UX-DR35: Epic 1: 1.26
- UX-DR36: Epic 1: 1.26
- UX-DR37: Epic 1: 1.26
- UX-DR38: Epic 1: 1.21
- UX-DR39: Epic 1: 1.20; Epic 4: 4.6
- UX-DR40: Epic 4: 4.5
- UX-DR41: Epic 4: 4.5
- UX-DR42: Epic 4: 4.5
- UX-DR43: Epic 4: 4.7
- UX-DR44: Epic 1: 1.23; Epic 2: 2.31; Epic 5: 5.1, 5.4; Epic 7: 7.21
- UX-DR45: Epic 1: 1.22; Epic 5: 5.7; Epic 7: 7.15
- UX-DR46: Epic 1: 1.27; Epic 7: 7.17
- UX-DR47: Epic 1: 1.24; Epic 7: 7.21
- UX-DR48: Epic 2: 2.29
- UX-DR49: Epic 2: 2.30
- UX-DR50: Epic 2: 2.30
- UX-DR51: Epic 2: 2.31
- UX-DR52: Epic 2: 2.31
- UX-DR53: Epic 2: 2.29
- UX-DR54: Epic 2: 2.29
- UX-DR55: Epic 2: 2.31
- UX-DR56: Epic 1: 1.17; Epic 6: 6.3
- UX-DR57: Epic 7: 7.16
- UX-DR58: Epic 7: 7.16
- UX-DR59: Epic 7: 7.17
- UX-DR60: Epic 1: 1.27
- UX-DR61: Epic 1: 1.17
- UX-DR62: Epic 1: 1.17, 1.18; Epic 2: 2.16, 2.18, 2.25
- UX-DR63: Epic 2: 2.18, 2.25; Epic 7: 7.17
- UX-DR64: Epic 1: 1.22; Epic 5: 5.7
- UX-DR65: Epic 1: 1.20, 1.21, 1.24; Epic 3: 3.4; Epic 4: 4.6
- UX-DR66: Epic 1: 1.23
- UX-DR67: Epic 2: 2.29, 2.30
- UX-DR68: Epic 7: 7.16
- UX-DR69: Epic 1: 1.25, 1.26
- UX-DR70: Epic 1: 1.22, 1.25; Epic 3: 3.4; Epic 4: 4.5
- UX-DR71: Epic 1: 1.25, 1.27; Epic 2: 2.30, 2.31; Epic 4: 4.7
- UX-DR72: Epic 1: 1.16, 1.25
- UX-DR73: Epic 1: 1.17
- UX-DR74: Epic 1: 1.22; Epic 2: 2.18; Epic 4: 4.5
- UX-DR75: Epic 1: 1.17; Epic 2: 2.16, 2.25
- UX-DR76: Epic 2: 2.19; Epic 3: 3.3; Epic 4: 4.5; Epic 5: 5.5
- UX-DR77: Epic 1: 1.6; Epic 4: 4.1
- UX-DR78: Epic 1: 1.23; Epic 2: 2.29; Epic 7: 7.21
- UX-DR79: Epic 1: 1.14; Epic 6: 6.2; Epic 9: 9.2
- UX-DR80: Epic 1: 1.17; Epic 3: 3.5; Epic 6: 6.2, 6.3
- UX-DR81: Epic 7: 7.16, 7.17, 7.21
- UX-DR82: Epic 2: 2.16; Epic 3: 3.4; Epic 5: 5.1
- UX-DR83: Epic 3: 3.6
- UX-DR84: Epic 2: 2.31; Epic 3: 3.5; Epic 5: 5.4
- UX-DR85: Epic 1: 1.16
- UX-DR86: Epic 6: 6.3, 6.6

#### Additional requirements

- AR-1: Epic 1: 1.2, 1.4
- AR-2: Epic 1: 1.2, 1.4
- AR-3: Epic 1: 1.2
- AR-4: Epic 1: 1.2
- AR-5: Epic 1: 1.4, 1.5, 1.14, 1.15; Epic 7: 7.12
- AR-6: Epic 1: 1.7; Epic 2: 2.19, 2.27
- AR-7: Epic 1: 1.5, 1.8, 1.9, 1.12, 1.20; Epic 3: 3.1, 3.3; Epic 4: 4.2, 4.4
- AR-8: Epic 2: 2.1, 2.7, 2.8, 2.12; Epic 3: 3.2; Epic 4: 4.3, 4.8; Epic 5: 5.5; Epic 9: 9.1
- AR-9: Epic 2: 2.2, 2.3, 2.4, 2.5, 2.6, 2.21; Epic 4: 4.8; Epic 7: 7.9
- AR-10: Epic 2: 2.10, 2.11, 2.12, 2.15, 2.16; Epic 7: 7.7, 7.13
- AR-11: Epic 1: 1.5; Epic 3: 3.1; Epic 5: 5.1, 5.2, 5.3, 5.5; Epic 7: 7.18
- AR-12: Epic 1: 1.4, 1.10, 1.11, 1.14, 1.17; Epic 2: 2.5, 2.11; Epic 7: 7.1, 7.8, 7.10, 7.13, 7.14, 7.18
- AR-13: Epic 1: 1.11, 1.12, 1.14, 1.18, 1.24; Epic 2: 2.12, 2.28; Epic 4: 4.4; Epic 5: 5.3; Epic 7: 7.5, 7.11, 7.12, 7.20; Epic 9: 9.2
- AR-14: Epic 1: 1.8, 1.10; Epic 2: 2.17; Epic 3: 3.1
- AR-15: Epic 1: 1.19; Epic 2: 2.13
- AR-16: Epic 1: 1.6; Epic 2: 2.20, 2.24; Epic 4: 4.1
- AR-17: Epic 1: 1.11; Epic 2: 2.7, 2.8, 2.10, 2.21; Epic 7: 7.11, 7.20
- AR-18: Epic 1: 1.2; Epic 7: 7.2
- AR-19: Epic 1: 1.14; Epic 4: 4.3, 4.4, 4.8; Epic 6: 6.2
- AR-20: Epic 2: 2.10, 2.20, 2.22
- AR-21: Epic 1: 1.5; Epic 2: 2.13, 2.14, 2.15, 2.20
- AR-22: Epic 1: 1.2, 1.12; Epic 2: 2.10
- AR-23: Epic 1: 1.2, 1.3, 1.15; Epic 2: 2.1
- AR-24: Epic 1: 1.2, 1.3
- AR-25: Epic 2: 2.9
- AR-26: Epic 3: 3.2, 3.7; Epic 7: 7.2
- AR-27: Epic 1: 1.5, 1.14; Epic 2: 2.7; Epic 4: 4.8
- AR-28: Epic 6: 6.8
- AR-29: Epic 1: 1.1, 1.2; Epic 5: 5.8; Epic 6: 6.8
- AR-30: Epic 1: 1.1; Epic 6: 6.7
- AR-31: Epic 1: 1.5, 1.13; Epic 2: 2.10, 2.18, 2.21, 2.27; Epic 3: 3.3; Epic 4: 4.4; Epic 5: 5.6; Epic 7: 7.15 (each field frozen in 1.5 and populated by the listed story)
- AR-32: Epic 1: 1.3, 1.27; Epic 7: 7.1, 7.4; Epic 9: 9.1 (deferred items honored as constraints, no stories built for them)

#### Old draft ids mapped to new ids

1.1->1.2; 1.2->1.4; 1.3->1.5; 1.4->1.6; 1.5->1.7; 1.6->1.8; 1.7->1.10; 1.8->1.11+1.12+1.14; 1.9->1.15; 1.10->1.19+1.20; 1.11->1.21+1.23; 1.12->1.9; 1.13->1.26; 2.1->2.1; 2.2->2.2+2.3; 2.3->2.4; 2.4->2.5+2.6; 2.5->2.7; 2.6->2.10; 2.7->2.11+2.12; 2.8->2.13; 2.9->2.14+2.15; 2.10->2.19+2.20; 2.11->2.21; 2.12->1.6+2.22+2.23+2.24+2.26; 2.13->2.16+2.17+2.18+2.25; 2.14->2.8; 3.1->3.1; 3.2->3.3+3.4; 3.3->3.5; 3.4->3.2; 3.5->3.7; 3.6->1.20+3.6; 3.7->7.4+7.5+7.6; 4.1->4.1; 4.2->4.2; 4.3->4.3+4.4; 4.4->4.5+4.6; 4.5->4.8; 5.1->5.1+5.2; 5.2->5.3+5.4; 5.3->5.5+5.6; 5.4->5.7; 5.5->5.8; 6.1->6.3; 6.2->6.1+6.4; 6.3->6.5; 6.4->6.7; 6.5->6.6; 6.6->6.8; 6.7->6.9; 7.1->7.1+7.2+7.3; 7.2->7.7+7.8; 7.3->7.8+7.9; 7.4->7.10+7.11; 7.5->7.13+7.14+7.15+7.18+7.19+7.20; 7.6->7.22; 8.1->8.1; 8.2->8.1; 8.3->8.1; 8.4->8.1; 9.1->9.3; 9.2->9.1+9.2. New: 1.1, 1.3, 1.13, 1.16, 1.17, 1.18, 1.22, 1.24, 1.25, 1.27, 2.9, 2.27, 2.28, 2.29, 2.30, 2.31, 4.7, 6.2, 7.12, 7.16, 7.17, 7.21.

#### Revision decisions worth flagging

- All AD-2 API models (job state, session state, RoomSummary, BuildView, AccessCheck) and the AR-31 event fields are declared in 1.5 before the Mon Oct 26 freeze, so no later story touches the frozen domain/schema.py across packages; Mask3D stays undeclared until the Tier 2 gate.
- Epic 7 opens with three Tier 1 smoke-deploy stories (7.1 to 7.3, Tue Oct 27), so Clue cards (7.4 to 7.6) are the first Tier 1.5 stories of the epic rather than its first two stories; this keeps Tier 1 ahead of Tier 1.5 within the epic.
- Later live-seam SIT cases are test files under tests/sit/ discovered by scripts/sit.py, so the stories that add them stay within AD-17.
- 1.18 is re-dated Tue Oct 27 so 2.16 can depend on it the same day; the error banner moved into the app shell (1.17).

## Epic List

### Epic 1: Play a room in the browser

A player opens a stored room in Chrome and plays it from start to finish: photo Scenes with mask Hotspots, a Thumbnail strip, an Inventory, Wizard notes with Evidence cards, all four lock types judged by the server, the First-room welcome, reload resume and a Completion screen, all at the accessibility floor. Built on fixture rooms and the mock provider from Mon Oct 26, with no model access needed.

**FRs covered:** FR-6, FR-8, FR-9, FR-11, FR-12, FR-13, FR-20, FR-21, FR-24, FR-26, FR-36

### Epic 2: Turn your photos into a verified room

A player uploads 6 to 10 JPEG photos and, within the capture target, gets a room built from their own objects that passed the Validator and the Dry run. The Capture screen shows every stage, failure and Regeneration as it happens, a Build view (unless cut 0 is taken) shows how the room was built, and every paid call is cached, priced, capped and recorded in a Ledger exported daily.

**FRs covered:** FR-1, FR-2, FR-3, FR-4, FR-5, FR-6, FR-7, FR-8, FR-9, FR-10, FR-23, FR-27, FR-28, FR-29, FR-30, FR-36, FR-38

### Epic 3: A game master that helps without telling

While playing, the player gets stuck and the Guide escalates nudge, direction, near-answer from how they play, with the triggering events visible in the Triggers panel; asking for the answer yields nothing above the current Rung; Rungs never contain a solution; the four wizard portraits appear in play.

**FRs covered:** FR-14, FR-15, FR-16, FR-17, FR-23, FR-24

### Epic 4: The room fights back, fairly

Between puzzles the Trickster proposes one bounded change and the Validator decides whether it stands. The player sees accepted, rejected and skipped Cards, and the room they play changes only when an edit is accepted; a scripted source replays recorded proposals for the video with the Validator still live.

**FRs covered:** FR-11, FR-18, FR-19, FR-24, FR-25, FR-26, FR-28

### Epic 5: The second room remembers you

A returning player starts a second room and is greeted from how they played the first; hint thresholds adapt to their persistence; the Player profile stays in their browser and only the Derived block reaches the server.

**FRs covered:** FR-13, FR-20, FR-21, FR-22

### Epic 6: Record the demo and submit

Every demo shortcut is disclosed on the surface it affects. The builder records the backup video by Sun Nov 1 2:00 PM and the capture proof and main demo on Tue Nov 3, completes the README and CHANGELOG, cleans the repo, and submits on Wed Nov 4 before 9:00 AM ET.

**FRs covered:** FR-1, FR-13, FR-14, FR-17, FR-26, FR-30, FR-36

### Epic 7: Judges play it themselves

A judge opens the hosted URL, plays a Demo room to the Completion screen with verbatim Rungs, and can build their own room behind the Access code within a 20-build quota. Builds survive the host's web timeout, and Judge data is deleted on Tue Nov 10. Only the Tue Oct 27 smoke deployment is Tier 1; the rest is Tier 1.5, starting with Clue cards.

**FRs covered:** FR-5, FR-6, FR-17, FR-20, FR-26, FR-29, FR-31, FR-32, FR-33, FR-36, FR-37

### Epic 8: Walk the room in 3D

(Tier 2, gated, default no-go) The player walks a 3D version of the Room and triggers Puzzles by raycast. FR-34 gets stories only after the Mon Nov 2 gate passes; until then the epic holds the spike and the gate record.

**FRs covered:** FR-34

### Epic 9: Ask the wizards by voice

(Unscheduled, the last Tier 1.5 item) The player asks for help by voice and gets exactly the Rung a typed request would give, and the transcript goes nowhere else.

**FRs covered:** FR-6, FR-14, FR-35

## Epic 1: Play a room in the browser

A player opens a stored room in Chrome and plays it from start to finish: photo Scenes with mask Hotspots, a Thumbnail strip, an Inventory, Wizard notes with Evidence cards, all four lock types judged by the server, the First-room welcome, reload resume and a Completion screen, all at the accessibility floor. The epic is built on fixture rooms and the mock provider from Mon Oct 26 and needs no model access. It also lands the ratified scaffold, CI, the frozen Schema v1, the design tokens and the app shell that every later surface uses.

### Story 1.1: Tag the pre-hackathon baseline and photograph both rooms before kickoff

As a builder,
I want the pre-hackathon state of the repo tagged and both video rooms photographed before kickoff,
So that pre-existing code is disclosed against a fixed point and the build starts on Mon Oct 26 with privacy-safe photos already in hand.

_Covers AR-30, AR-29, NFR-11, NFR-13. Owner: repo root. Depends on: none. Tier 1 gate, Sun Oct 25 night (PRD §11.1). The README 'Pre-existing code' section (6.7) links this tag._

**Acceptance Criteria:**

**Given** the repo on Sun Oct 25 night
**When** the builder runs `git ls-remote --tags origin`
**Then** an annotated tag `pre-hackathon-baseline` is listed, and `git cat-file -t pre-hackathon-baseline` prints `tag`
**And** the tagged tree holds an MIT `LICENSE` at the repo root and a `CHANGELOG.md` whose baseline entry reads exactly "Before Oct 26 (baseline): provider interface, mock provider, Meta API stub, tests. No front end, no model calls."

**Given** the tagged tree
**When** it is compared with the Oct 20 scaffold
**Then** no file under `src/` or `tests/`, nor `main.py`, `pyproject.toml` or `requirements.txt`, differs from the Oct 20 scaffold, so no product code is added and the scaffold is not expanded
**And** commits after the tag are small and dated, and `CHANGELOG.md` gets a dated entry for each build day through Nov 4

**Given** the builder checklist line for photos
**When** both rooms are photographed
**Then** each room has 6 to 10 JPEG photos taken with the iPhone set to Most Compatible, with no faces, documents or other people's belongings in frame
**And** the originals sit only under git-ignored folders (`rooms/`, `photos/`, `captures/` or `uploads/`), `git status --porcelain` lists none of them, and no photo file appears in `git log --all --name-only`

**Given** the Official Rules
**When** they are published before or during the build
**Then** the builder has accepted them, and the date of acceptance is recorded in the checklist

**Given** the tagged commit checked out on a clean machine
**When** `pytest` runs offline
**Then** the 7 scaffold tests in `tests/test_providers.py` pass unchanged, which shows the baseline is the scaffold as it stood

### Story 1.2: Ratify the scaffold as the first providers story: pins, Settings, Meta stub fixes, ignore and boundary tests

As a builder,
I want the existing backend scaffold pinned, configured through one `Settings`, fixed where the dev skills found errors, and guarded by ignore-file and boundary tests,
So that every later story builds on the same dependencies, reads flags the same way, and cannot leak raw photos or cross a package boundary.

_Covers FR-36, AR-1, AR-2, AR-3, AR-4, AR-18, AR-22, AR-23, AR-24, AR-29, NFR-4, NFR-8, AD-1, AD-14, AD-17. Owner: providers (with src/config.py and repo root). Depends on: 1.1. Tier 1, Mon Oct 26, the first implementation story (the scaffold is untouched before it); this is the deps-foundation story, and its merge starts the dependency freeze. Load keyframe-muse for the Meta adapter fixes and keyframe-devops for uv and `uv.lock`, the pins, `.python-version`, `.nvmrc`, `tests/conftest.py`, `scripts/doctor.py`, the cloud SessionStart hook, the ignore files and the freeze rule (copy the files from its references/templates.md)._

**Acceptance Criteria:**

**Given** this story's changes
**When** the builder opens `pyproject.toml`
**Then** `requires-python` is `>=3.13`, and `[project.dependencies]` pins the runtime Python rows of the spine Stack table with `==` (FastAPI 0.156.4, uvicorn 0.54.0, pydantic 2.14.1, httpx 0.28.1, Pillow 13.0.0, meta-sam-parser 0.1.0, fal-client 1.0.3, ollama 0.6.3, modal 1.6.2, python-dotenv 1.2.4), and `pytest==9.1.1` sits in `[dependency-groups] dev`, not in `[project.dependencies]`
**And** `[tool.uv]` sets `environments` and `required-environments` to macOS arm64 and Linux x86_64, `no-build = true` and `required-version = ">=0.11.32"`, there is no `[build-system]`, and `[tool.pytest.ini_options]` sets `testpaths = ["tests"]` and `pythonpath = ["."]`
**And** `.python-version` at the repo root reads `3.13` and `.nvmrc` at the repo root reads `24`
**And** `requirements.txt` no longer exists (`git rm`), and nothing in the repo installs from it
**And** code style follows AR-22: ruff defaults, Python 3.13 type hints, pydantic v2, tests under `tests/<package>/` mirroring `src/`, and fixtures under `tests/fixtures/`

**Given** the committed `uv.lock` and uv 0.11.32
**When** the builder runs `uv lock --check`, then `uv sync --locked`, then `uv run pytest -q`
**Then** each exits 0, the lock resolves with wheels only (no package is built from source) for both platforms, and `uv tree --depth 1` shows pytest as `(group: dev)`
**And** editing a pin in `pyproject.toml` without re-locking makes `uv lock --check` exit 1, and the repo never runs `uv sync --frozen`, `uv pip install` or `uv lock --upgrade`

**Given** `tests/conftest.py` from the keyframe-devops template
**When** pytest imports it, before any `src` module
**Then** it sets `MODEL_PROVIDER=mock`, `PROVIDER_<ROLE>=mock` for every role and the four secret keys (`META_MODEL_API_KEY`, `FAL_KEY`, `OPENAI_COMPATIBLE_API_KEY`, `ACCESS_CODE`) to `""`, so a Mac `.env` never reaches a module-level `Settings`, and repeats that per test
**And** a test that opens a non-loopback socket fails with `OSError("tests run offline (AD-17) ...")`, while `httpx.MockTransport` tests still pass

**Given** an environment that sets none of the product flags
**When** `Settings` is constructed
**Then** it reads each AD-14 product flag it owns exactly once, with the defaults `CACHE=on`, `SPEND_CAP_USD=80`, `DEMO_TIMESCALE=1`, `DEMO_TRICKSTER=live` (accepting `live`, `record`, `scripted` and `authored`, and failing at startup on any other value), `DRY_RUN=on`, `REGEN_MAX=2` and `GUIDE=ollama`, plus the adapter settings: `MODEL_PROVIDER` (default `meta`) as the default for each `PROVIDER_<ROLE>` (`ARCHITECT`, `RIDDLER`, `DRYRUN`, `TRICKSTER`, `IMAGE`), the per-role model ids, `META_MODEL_API_KEY`, `META_MODEL_API_BASE_URL`, `OPENAI_COMPATIBLE_BASE_URL`, `OPENAI_COMPATIBLE_API_KEY`, `fal_key` from `FAL_KEY`, `OLLAMA_HOST` and `ACCESS_CODE`
**And** it reads no `MODE` and has no `mode` or `min_containers` field. Those fields, the `verbatim` default under `MODE=hosted`, and the startup failures on `MODE=hosted` with `GUIDE=ollama` or with `DEMO_TRICKSTER=record` land in 7.2
**And** `CHAT_MODEL`, `IMAGE_MODEL` and any `MAX_COMPLETION_TOKENS_<ROLE>` are not read
**And** a test fails if any module under `src/` other than `src/config.py` reads `os.environ`; `scripts/doctor.py` is exempt (stdlib, runs before `uv sync`; spine AD-14)

**Given** `src/providers/meta_api.py`
**When** its request is built against a stubbed httpx transport offline
**Then** the request goes to the base URL `https://api.meta.ai/v1`, with the chat model id `muse-spark-1.3` or the image model id `muse-image-1.0`, through `httpx` (no `urllib` import remains)
**And** the body carries no `temperature` and no `max_tokens`, the key comes from `Settings`, never from `os.environ`, and the adapter has no contributor-tier option (standard tier only, FR-36, NFR-4)

**Given** the repo's `.gitignore` and `.env.example`
**When** the ignore-file tests run
**Then** each of `rooms/`, `photos/`, `captures/`, `uploads/`, `*.heic`, `.cache/`, `.env`, `.env.local`, `keyframe-hosted.env` and `spend/ledger.jsonl` is ignored by git (the `.env.*`, `!.env.example` and `*.env` lines stay), so raw room photos and env files are never committed (AR-29)
**And** `.env.example` lists every key `Settings` reads, each with a blank value, including `META_MODEL_API_KEY` and `FAL_KEY`

**Given** `tests/test_boundaries.py`
**When** it walks every module's imports under `src/`
**Then** it passes on the ratified scaffold and fails, naming the offending module, in any of these cases: a `src/domain` module imports anything other than the standard library, pydantic and `src/domain`; a `src/council` or `src/pipeline` module imports anything under `src/` other than `src/domain`, the port modules (`src/providers/base.py`, `src/pipeline/ports.py`, `src/domain/clock.py`) and, for `src/pipeline`, `src/council`; an adapter in `src/providers` or `src/infra` imports anything other than ports and the domain; or a module outside `src/providers`, `src/infra` and `src/api` imports an adapter

**Given** the cloud containers
**When** this story merges
**Then** `.claude/hooks/session-start.sh` from the keyframe-devops template exists, registered in `.claude/settings.json` as a SessionStart hook with the matcher `startup|resume` (both files on the delivery-plan hygiene path list; merged into an existing `.claude/settings.json`)
**And** run without `CLAUDE_CODE_REMOTE=true` (on the Mac) the hook exits 0 and does nothing
**And** run with `CLAUDE_CODE_REMOTE=true` it installs Node 24 through nvm (`source "$NVM_DIR/nvm.sh" --no-use`), writes Node 24's directory to `$CLAUDE_ENV_FILE` so later shells print `v24.x`, runs `uv sync --locked` when `uv.lock` exists, runs `npm ci` in `web/` once `web/package.json` exists and `node_modules` is older than the lock, then runs `python3 scripts/doctor.py --cloud`, and a failed `uv sync` or `npm ci` prints a `session-start:` note, while the hook exits 0 whatever those steps or `doctor.py` report

**Given** `scripts/doctor.py`, copied from the keyframe-devops skill (a copy, never an import from `.claude/`, so it survives the Nov 4 hygiene)
**When** it runs as `python3 scripts/doctor.py --cloud` in a container after this story, or with `--ci` or `--json`
**Then** it uses the standard library only and imports no `src` module in its own process (its 'Settings loads' check runs in a `.venv` subprocess and only after `uv sync`), and reports no FAIL (Ollama checks warn in a container), and `--json` prints valid JSON
**And** it fails on a tracked or staged private path (`.env`, `.env.*` other than `.env.example`, `*.env`, a raw photo outside `web/public/` and `docs/screenshots/`), on a wrong Node major or a uv below 0.11.32, and on a broken `/dev/null`
**And** Luis runs `python3 scripts/doctor.py` on the M1 (Ollama 0.40.x with `llama3.2:3b` resident) and records the result in the sprint status

**Given** the dependency freeze, which starts when this story merges on Mon Oct 26 and runs through Nov 9
**When** a later change touches `pyproject.toml`, `uv.lock`, `web/package.json` or `web/package-lock.json`
**Then** it is a dependency PR touching only those files plus the spine Stack table, the README license line and the affected skill pins, it follows the keyframe-devops checklist (need, license, wheels on both platforms, Python 3.13, size, exact version, lock diff read, selfchecks, `scripts/check.sh` green), and it moves a pinned version only for a blocking bug or a security fix, one package per PR, with Luis's explicit approval in the PR; the one exception is 1.4, which creates `web/package.json` and `web/package-lock.json` at the Stack pins (three 0.186.1, Vite 8.3.4, TypeScript 6.0.3, @types/three 0.186.0, plus json-schema-to-typescript 16.0.0 if picked; quicktype only through the checklist)
**And** nothing moves Mon Nov 2 to Wed Nov 4 except a security fix, a lock diff outside a dependency PR is refused in review, and `@sparkjsdev/spark` 2.4.0 (Tier 3) and 1.4's type generator are the only pre-approved additions

**Given** this story's changes
**When** `pytest` runs offline against the mock provider, with `tests/conftest.py` forcing `MODEL_PROVIDER=mock`
**Then** it passes with new tests covering this story's criteria, and the 7 scaffold tests are updated so the offline suite is green

### Story 1.3: One CI job: offline pytest plus the web build and type check

As a builder,
I want one GitHub Actions job that runs the offline suite and the web build on every push to master and every pull request,
So that a red test or a broken client build is caught before review, with no secret and no deploy anywhere in CI.

_Covers AR-24, AR-23, AR-32, NFR-8. Owner: repo root (.github/workflows). Depends on: 1.2. Tier 1, Mon Oct 26, right after the scaffold. Load keyframe-devops (copy `scripts/check.sh` and `.github/workflows/ci.yml` from its references/templates.md; the two npm cache lines wait for 1.4)._

**Acceptance Criteria:**

**Given** `.github/workflows/ci.yml`
**When** a commit is pushed to master or a pull request is opened
**Then** exactly one job, `check`, runs on `ubuntu-latest` with `timeout-minutes: 10`, `permissions: contents: read` and `MODEL_PROVIDER: mock`, and its steps are `actions/checkout@v7`, `astral-sh/setup-uv` pinned to the v10.3.0 commit SHA with `version: "0.11.32"`, `actions/setup-node@v7` with `node-version-file: .nvmrc`, and `run: bash scripts/check.sh`
**And** there is no `setup-python` step (uv reads `.python-version` and installs Python 3.13), and the `cache: npm` and `cache-dependency-path: web/package-lock.json` lines are present only if `web/package-lock.json` is already committed (1.4 adds them otherwise)

**Given** `scripts/check.sh`, the pre-push check and the whole CI job
**When** it runs from a clean clone
**Then** it runs, in order and stopping at the first failure: the privacy step (fails on any tracked `.env`, `.env.*` other than `.env.example`, `*.env`, `.jpg`, `.jpeg`, `.png` or `.heic` outside `web/public/` and `docs/screenshots/`, or path under `rooms/`, `photos/`, `captures/`, `uploads/` or `.cache/`); the lock step (`uv lock --check`, `uv sync --locked`); the offline `uv run pytest -q`; the wheel step (the exported lock compiles wheels-only for `aarch64-apple-darwin` and for `x86_64-manylinux_2_28`, writing to scratch files, never `/dev/null`); once `src/api/modal_app.py` exists, the hosted step (the module imports offline, the image installs `uv.lock` through `.uv_sync(uv_version=` CI's uv version, has no `pip_install(` list, and its `python_version` equals `.python-version`); and once `web/package.json` exists, the web step (`npm ci`, `npm run build`, `npx tsc --noEmit`, and the lock still records `@rolldown/binding-darwin-arm64`), then prints `check.sh: all green`
**And** before 1.4 creates `web/package.json` the web step is skipped and the job is green; after 1.4 it runs, and a type error, a `web/package.json` edited without its lock, or a Node other than 24 under `engine-strict` fails the job
**And** a tracked fixture `.jpg` or `keyframe-hosted.env` fails the privacy step, a pin edited without re-locking fails the lock step, a test opening a non-loopback socket fails the pytest step, and a lock with a package lacking a macOS arm64 or glibc 2.28 wheel fails the wheel step

**Given** `scripts/check.sh --predeploy`
**When** the builder runs it before every manual `modal deploy` (and after any merged dependency PR)
**Then** it runs every step above and then fails unless the working tree is clean and `web/dist/index.html` exists

**Given** the first green `check` run on master
**When** the story is closed
**Then** the sprint status records either that branch protection requires the `check` status before merging or, where the plan cannot enforce it for a private repo, that 'CI green before merge' is kept by hand
**And** the README's contributing note says to run `bash scripts/check.sh` before every push

**Given** the workflow file
**When** it is read
**Then** it references no `secrets.` value, has no deploy step and no CD trigger, and never runs `modal deploy`, which stays a manual step (7.3, 7.22)
**And** it adds nothing beyond AR-24 (no matrix, no extra jobs, no coverage upload; AR-32)

**Given** a test that deliberately fails on a branch
**When** that branch is pushed with a pull request open
**Then** the job reports failure on the commit, and it passes again once the test is fixed

**Given** this story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria, including an offline check that the workflow has one job, no `secrets.` reference and no deploy step, installs uv `0.11.32` and runs only `bash scripts/check.sh`

### Story 1.4: Create the web client from the Vite 8 vanilla-ts template

As a builder,
I want `web/` created from the Vite 8 vanilla-ts template with three and a dev proxy to FastAPI,
So that every play story has one strict TypeScript client that builds into the `web/dist` FastAPI serves from one origin.

_Covers AR-1, AR-2, AR-5, AR-12, NFR-10, AD-9, AD-11. Owner: web. Depends on: 1.2. Tier 1, Mon Oct 26. Load keyframe-devops (the first web story in its references/templates.md: `web/package.json`, `web/.npmrc`, `web/package-lock.json`)._

**Acceptance Criteria:**

**Given** a fresh `web/` directory
**When** it is created from the Vite 8 vanilla-ts template
**Then** `web/package.json` pins exact versions (no `^` or `~`): three 0.186.1, and in `devDependencies` Vite 8.3.4, TypeScript 6.0.3 and @types/three 0.186.0, and sets `engines.node` to `"24.x"`
**And** `web/.npmrc` sets `save-exact=true` and `engine-strict=true`, the repo-root `.nvmrc` from 1.2 (`24`) is the only Node version file, and the TypeScript config has `strict` enabled
**And** `web/package-lock.json` (lockfileVersion 3, generated once from a clean tree under Node 24) is committed and records the macOS arm64 bindings, `node_modules/` is added to the root `.gitignore` in the same commit, and, if 1.3 has merged, `ci.yml` gains its `cache: npm` and `cache-dependency-path: web/package-lock.json` lines in the same commit

**Given** `web/vite.config.ts`
**When** the dev server runs
**Then** it proxies `/api/*` to the local uvicorn address, so the client reaches FastAPI on one origin and never needs CORS

**Given** `npm run dev` and Chrome on the Mac
**When** the root page loads
**Then** an empty three scene renders into a canvas with no console errors

**Given** the client sources
**When** `npm run build` runs
**Then** it writes `web/dist` with an `index.html`
**And** neither `web/dist` nor `node_modules/` is committed

**Given** the type generator choice (AR-5)
**When** the builder opens `web/package.json`
**Then** exactly one generator, json-schema-to-typescript 16.0.0 or quicktype, is pinned to an exact version in `devDependencies`, and no types are generated yet (1.15 generates them)

**Given** this story's changes
**When** the web build and type check run, and, once 1.3 has merged, the web step of `scripts/check.sh` executes (`npm ci`, build, `tsc --noEmit`)
**Then** they pass with new tests covering this story's criteria, and `pytest` stays green offline against the mock provider

### Story 1.5: Schema v1 and every AD-2 API model as one set of pydantic models

As a builder,
I want Schema v1 and every model `GET /schema` returns declared once in `src/domain/schema.py` and frozen on Mon Oct 26,
So that the API, the job artifacts and the client share one data shape, and no later story has to reopen a frozen model.

_Covers AR-5, AR-7, AR-11, AR-21, AR-27, AR-31, FR-21, NFR-11, AD-2, AD-4, AD-18. Owner: domain. Depends on: 1.2. Tier 1, Mon Oct 26 freeze. Gate: the Thu Oct 22 decoy pick (option A, `Room.decoys[]`, recommended) and the Oct 21 approvals applied. The HTTP answers were settled in the spine on Oct 21 (AD-3, AD-7, AD-9, AD-13): 422 `photo_count` and 422 `bad_downscale` at ingest (2.10, 2.12), 409 `build_not_ready` with the job `status` in the envelope for a Build view of a job not yet `done` (2.28), and 403 `access_denied`, 429 `too_many_attempts` and the wrong-code `{ok: false, builds_left: null}` in Hosted mode (7.11, 7.12). Later changes only through bmad-correct-course._

**Acceptance Criteria:**

**Given** `src/domain/schema.py`
**When** a room built to `schema-v1.md` is parsed
**Then** `Room` carries `id`, `created`, an optional `name` (a 41-character name is rejected), `photos[]` (`hash`, `size`, downscaled and original paths), `interactables[]`, `puzzles[]`, the decoy storage fixed by the Thu Oct 22 pick (option A: `decoys: [{id, puzzle, interactable, visible_attribute}]`, empty on a stored build Room) and `provenance` (model ids, prompt hashes, stage timings, regeneration count, spend per stage, `applied_edits[]`), with no `profile_name` and no `exit_puzzle_id`
**And** `Interactable` carries `id`, `label`, `photo`, `box`, `polygons` (a list of `[[x, y], ...]` or `null`), `instances`, `attributes[]` and optional `tier2`, and `Puzzle` carries `id`, `lock_type`, `requires[]`, `solution`, `evidence` {`interactable`, `visible_attribute`}, `clue`, `lore`, `rungs` {`nudge`, `direction`, `near_answer`} and `is_exit`

**Given** the polymorphic fields
**When** each is parsed and its JSON Schema emitted
**Then** `Puzzle.solution` (`code` {`code`}, `order` {`interactables`}, `use_on` {`item`, `target`}, `find` {`target`}), `TricksterEdit.payload` (`decoy`, `merge`, `loosen`, `shortcut`) and `LockInputEvent.input` (`CodeInput(puzzle_id, code)`, `UseOnInput(item, target)` with no `puzzle_id`, `OrderStartInput(puzzle_id)`, `OrderStopInput(puzzle_id)`) are separate models with a `Literal` discriminator, emitted as `oneOf`
**And** a Puzzle whose solution variant does not match its `lock_type` fails validation
**And** `strict_schema(model)` leaves no `$defs` or `$ref`, sets `additionalProperties: false` on every object and lists every property in `required`
**And** `RoomDraft`, `DryRunAnswers` (a list of `{puzzle_id, answer}` reusing the solution union, which follows spine AD-12 over schema-v1's "keyed by puzzle id") and `ArchitectResponse` contain no map-typed field
**And** `ArchitectResponse` is a list of candidates, each with `label`, `plural` (whether the label names several like objects, read by mask selection in 2.13), `photo` (the clearest photo index), `box` on the 0 to 1000 grid, `attributes[]` as read and `confidence`

**Given** id fields and keys
**When** a model is parsed
**Then** ids are prefixed ULIDs (`room_`, `job_`, `sess_`, `pz_`, `ix_`, `te_`, `call_`), and an id with the wrong prefix is rejected
**And** `RoomDraft` puzzles and their `requires` use the ordinal keys `p1` to `p6`, `ArchitectResponse` carries no ids (AD-18), and every JSON key is snake_case

**Given** the event models
**When** they are parsed
**Then** they form a tagged union by `type` of `ClickEvent(interactable_id)`, `LockInputEvent(input)`, `HintRequestEvent(puzzle_id | null)`, `IdleTickEvent()`, `OpeningLineEvent(kind: greeting | welcome, text)`, `TricksterCardEvent(edit_id, accepted, reason, room_revision)` with `puzzle_id` on every card and, on a rejected card, the structural proposal summary (edit type and Puzzle ids only), and `RungChangeEvent(puzzle_id, rung, triggered_by)` with `phrased`, `phrasing_ms` and `text` (the line exactly as shown, filled in 3.3)
**And** `TricksterCardEvent` also carries the full `TricksterEdit` (`edit`, null on a skipped card), as Schema v1 places edits in the session log, so the Effective room can be folded from the log alone (4.1)
**And** stored events carry `t_ms`, while the client-posted bodies (`click`, `lock_input`, `hint_request`) forbid `t_ms` and any extra field

**Given** the profile and status models
**When** they are parsed
**Then** `Derived` rejects `sessions < 0`, `persistence` outside [-1, 1] and `mean_rung_per_lock_type` values outside [0, 3], allows `time_to_first_hint_s` to be `null`, and `Derived.fresh()` validates with `persistence` 0
**And** `RoomResult` carries `room_id`, `demo`, the elapsed time, Rungs used and Wrong attempts, and per Puzzle its `lock_type`, `attempts`, `wrong_attempts`, `rungs_used`, `time_to_first_hint`, `solved`, the time spent on it, and the A-19 inputs (whether its nudge fired, whether a Hint request was made on it, whether it had an Early ask), so FR-21 can derive the median time to first hint, the mean Rungs per Lock type and persistence
**And** `Meta` has exactly `{mode, guide, guide_model: {id, host} | null, trickster: live | scripted | cut1, demo_timescale, cache, profile, disclosure, retention}`
**And** `RoomView` carries per Interactable only `id`, `label`, `attributes`, `instances` and `photo` and per Puzzle only `id`, `lock_type`, `requires`, `is_exit`, `clue`, `lore` and `rungs`, declaring no `solution`, `evidence`, `provenance` or profile field, and `TricksterEdit` carries `id` (`te_`), `type`, `puzzle`, `payload`, `validator_result` {`ok`, `reasons[]`}, `accepted` and `window`

**Given** the models later stories only fill in
**When** `schema.py` is frozen on Mon Oct 26
**Then** it also declares the job state (status `queued`, `running` with `stage`, `done`, `failed`, `needs_more_photos` or `needs_recapture`; per-stage timings, done-row counts and model id; the fixed messages that sent back each failed attempt; call rows; build time; the solution-free mask preview), the session state (the session's `room_id`, `locks_open`, `inventory`, `current_rung`, `wrong_attempts`, `rungs_used`, the order buffer and its armed puzzle, `active_puzzle_id`, `opening_line`, `phrasing`, `rung_changes`, `trickster_window` (with the open window's index), `trickster_calls`, `room_revision`, `disclosure`, `judge_room` (false until 7.21 sets it for a Room under `rooms/judge/`), and the effective nudge threshold and Rung spacing with their 1× values and source), `RoomSummary {room_id, name, cover_photo, puzzle_count, job_id, built_at}`, `BuildView`, `AccessCheck {ok, builds_left}` (`builds_left` null when `ok` is false), the session-start request `{room_id, derived}` and the error envelope `{error: {code, message, stage}}` with an optional `status` (a job status) set only when `code` is `build_not_ready` (spine AD-13)
**And** `PlayView` holds each Puzzle's evidence as a list of Evidence cards, with no field that marks a card as a Decoy, and carries no Rung text (Rung text reaches the client only in hint replies and `rung_changes[]`, 3.3)
**And** `Mask3D` is not declared (Tier 2, AD-5). Any AR-31 field that cannot be settled by Mon Oct 26 goes through bmad-correct-course before the story that needs it

**Given** this story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria, and `tests/test_boundaries.py` confirms `schema.py` imports only the standard library and pydantic

### Story 1.6: Validator rules 1 to 8 with fixed messages, the Dry run check, and the fixture rooms

As a builder,
I want the eight Schema v1 validator rules and the Dry run check as pure functions, plus synthetic fixture rooms,
So that no room reaches a player unvalidated, no reason leaks an answer, and every play story has valid rooms to test against.

_Covers FR-8, FR-9, AR-16, NFR-5, UX-DR77, AD-3, AD-12. Owner: domain. Depends on: 1.5. Tier 1, Mon Oct 26. Rule 9 joins in 4.1._

**Acceptance Criteria:**

**Given** the fixture generator under `tests/fixtures/`
**When** it runs
**Then** it writes synthetic JPEG scenes drawn with Pillow (1280 px long edge, never a real room photo) and two valid rooms: a four-lock room with at least 5 Interactables with polygons, 4 to 6 Puzzles covering `code`, `order`, `use_on` and `find`, and exactly one `is_exit` Puzzle; and a code-and-find room using only `code` and `find` locks, for cut 6 and video v0
**And** the four-lock room uses 6 synthetic photos, at least one of them portrait
**And** its output sits outside every git-ignored folder (`rooms/`, `photos/`, `captures/`, `uploads/`), and `validate` returns no reasons for either room

**Given** one negative fixture per rule, 1 through 8
**When** `validate(room)` runs on each
**Then** it returns at least one structured reason `{rule, puzzle_id, field}` for that rule, carrying the rule's fixed message from one table of check-phrased names and fixed messages (UX-DR77): for example, rule 1 has the check name "No two locks wait on each other" and the fixed message "Two locks would wait on each other forever.", and rule 5 has "No hint, clue or evidence gives an answer away" and "A hint gives part of an answer away."
**And** that table is the only source the Build view, the regeneration prompt, the "Sent back" lines and the rejected Card read; the rows for rule 9 and the `validate_edit` bounds message are added by the stories that add those checks

**Given** a room with zero `is_exit` Puzzles, and another with two
**When** `validate` runs
**Then** each returns a rule 7 reason for the exit count, checked before rule 7's payload checks (`code` 3 to 6 characters, `order` 3 to 5 Hotspots, `use_on` two distinct ids, `find` one), and `validate` reads only `is_exit` to find the exit

**Given** the rule 5 fixtures
**When** `validate` runs over `rungs`, `clue` and `evidence.visible_attribute`
**Then** a code string, or any one of its digits, appearing as a whole token fails at any length; a label word longer than three characters fails as a whole word, while a label word of three characters or fewer is not matched; matching is case-folded
**And** a `near_answer` naming one label of an `order` sequence or one label of a `use_on` pair passes, one naming two labels from that `order` sequence or both `use_on` labels fails, and the `near_answer` allowance is also checked against the `clue`

**Given** every negative fixture
**When** its reasons are serialized to JSON
**Then** no reason contains any solution token or answer from the fixture: only the rule number, the Puzzle id, the field name and the fixed message

**Given** `check_dry_run(room, answers)` in `domain/validator.py`
**When** it receives a `DryRunAnswers` list for the four-lock room
**Then** it returns pass or fail per Puzzle: a matching answer passes, a mismatched answer fails, and a Puzzle with no answer in the list fails
**And** it is the only function where Dry run answers meet solutions (used by 2.24; harmless if cut 4 is taken)

**Given** this story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria, and `domain/validator.py` does no I/O and imports only the standard library, pydantic and the domain

### Story 1.7: Redaction views keep solutions on the server

As a builder,
I want `to_prompt_view` and `to_play_view` in `src/domain/redact.py`,
So that a solution can never reach a model prompt or a browser.

_Covers AR-6, NFR-5, FR-11, AD-3. Owner: domain. Depends on: 1.5, 1.6. Tier 1, Mon Oct 26. `to_build_view` arrives in 2.27._

**Acceptance Criteria:**

**Given** the four-lock fixture room
**When** `to_prompt_view(room)` returns a `RoomView`
**Then** each Interactable keeps only `id`, `label`, `attributes`, `instances` and `photo`, and each Puzzle keeps only `id`, `lock_type`, `requires`, `is_exit`, `clue`, `lore` and `rungs`
**And** `solution`, `evidence`, `provenance`, `photos[].hash` and paths, `box`, `polygons`, `tier2` and `validator_result` are absent

**Given** the four-lock fixture room
**When** `to_play_view(room)` returns a `PlayView`
**Then** `solution`, `provenance` and `rungs` are absent, while each Puzzle's evidence (as its Evidence card list), each Interactable's `polygons` and `Room.name` are kept

**Given** either view
**When** its model and its output are inspected
**Then** neither `PlayView` nor `RoomView` declares a `solution` field or any profile field
**And** the input `Room` compares equal to a deep copy taken before the call, so both functions are pure

**Given** a Room whose solutions hold sentinel values that appear nowhere else in it (a sentinel code string, a sentinel `order` id list, a sentinel `use_on` pair, a sentinel `find` target id)
**When** both views are serialized to JSON
**Then** neither contains the code string, the order id list in sequence, the `use_on` pair or the find target id
**And** neither contains any `Derived` key or any validator reason text

**Given** this story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria, including the sentinel test

### Story 1.8: Session state machine: code and find locks, the Active puzzle and the server-resolved hint target

As a builder,
I want an event-sourced `SessionStateMachine` that judges `code` and `find` locks and tracks the Active puzzle,
So that only the server opens locks, a hint always targets the right Puzzle, and the session state can always be replayed from its log.

_Covers FR-12, FR-13, AR-7, AR-14, AD-4, AD-10. Owner: domain. Depends on: 1.5, 1.6, 1.7. Tier 1, Mon Oct 26 to Tue Oct 27._

**Acceptance Criteria:**

**Given** a session on the code-and-find fixture room
**When** `apply` receives a `ClickEvent` on the target of an available `find` Puzzle (every Puzzle in its `requires` is open)
**Then** that lock opens and its Interactable moves into `inventory`
**And** the same click while a required Puzzle is still closed opens nothing and is not a Wrong attempt
**And** a click on any other Hotspot changes no lock and counts nothing: a click alone never counts

**Given** an available `code` Puzzle whose code is `AB12`
**When** `apply` receives a `CodeInput` of `" ab12 "`
**Then** the lock opens, because codes are compared trimmed and case-folded (A-20)
**And** any other input leaves it closed and adds exactly one to `wrong_attempts` for that Puzzle
**And** a correct input to a Puzzle whose `requires` are not all open never opens it and is not a Wrong attempt

**Given** a session with events applied
**When** the session state is read
**Then** `active_puzzle_id` is the Puzzle of the most recent lock input or attempted click, and is null before any attempt
**And** a `HintRequestEvent` with no `puzzle_id` is resolved server-side to the Active puzzle and counts for that Puzzle in the session's records (the reply itself lands in 3.3)

**Given** a new session
**When** no `OpeningLineEvent` has been applied yet
**Then** `phrasing` is true, and once `OpeningLineEvent(kind, text)` is applied, `opening_line {kind, text}` holds it and `phrasing` is false

**Given** `src/domain/clock.py` and a scripted event log that solves every Puzzle of the code-and-find room, including wrong codes and `IdleTickEvent`s, and opens the exit
**When** the log is replayed from an empty state
**Then** the replayed state equals the state built by applying each event live, `apply` returns a new state each time and is the only writer of session state, and no domain function reads the wall clock (time arrives only as `t_ms`; `Clock` is a Protocol with no implementation)
**And** an `IdleTickEvent` changes no lock, Inventory or Wrong attempt count, and the session is complete once the exit lock opens

**Given** a completed session log that includes `rung_change` and `hint_request` events
**When** `RoomResult` is computed from the log alone
**Then** it reports the elapsed time (the `t_ms` of the event that opened the exit), Rungs used, Wrong attempts, the time per Puzzle, and per Puzzle its time to first hint and Rungs used with its `lock_type`, plus the A-19 inputs

**Given** this story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 1.9: Order sequences armed by Start the sequence, and use_on resolved on the server

As a builder,
I want the state machine to judge `order` sequences only while armed and to resolve `use_on` Puzzles from the item and target,
So that exploring never counts as a Wrong attempt, the client never has to guess a Puzzle, and all four lock types survive replay.

_Covers FR-12, AR-7, AD-4. Owner: domain. Depends on: 1.8. Tier 1, Tue Oct 27; cut 6 drops this story (together with 1.26)._

**Acceptance Criteria:**

**Given** an available `order` Puzzle with a 3-Hotspot solution in the four-lock fixture room
**When** `apply` receives `OrderStartInput(puzzle_id)` and then three `ClickEvent`s matching the solution in sequence
**Then** the buffer is armed for that Puzzle, each armed click fills it whatever it hits, and at full length the lock opens and the buffer disarms
**And** clicks made while unarmed are exploration: they never fill the buffer and never count

**Given** an armed `order` Puzzle
**When** the armed buffer reaches full length and does not match
**Then** exactly one Wrong attempt is counted for that Puzzle, and the buffer clears and stays armed
**And** `OrderStopInput(puzzle_id)` disarms and clears it with no Wrong attempt
**And** an `OrderStartInput` naming another available `order` Puzzle stops the armed one first, with no Wrong attempt

**Given** an available `use_on` Puzzle whose item was collected by a `find` Puzzle in its `requires`
**When** `apply` receives a `UseOnInput(item, target)` with no `puzzle_id`
**Then** the server resolves the Puzzle from the pair among available `use_on` Puzzles (by `item`, else by `target`), and a matching pair opens the lock
**And** a pair that resolves to a Puzzle but does not match its solution counts one Wrong attempt for that Puzzle

**Given** a `UseOnInput`
**When** the pair resolves to no available `use_on` Puzzle, or the item is not in `inventory`
**Then** the lock stays closed and no Wrong attempt is counted (the first is logged and counts nothing; the second is refused)
**And** a correct order sequence or `use_on` pair for a Puzzle whose `requires` are not all open never opens it and is not a Wrong attempt

**Given** a scripted event log that solves every Puzzle of the four-lock fixture room, including mismatched sequences, a stop and an unresolved pair
**When** the log is replayed from an empty state
**Then** the replayed state, including the order buffer and its armed Puzzle, equals the state built live

**Given** this story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 1.10: Local stores and the two clocks

As a builder,
I want the storage ports, their local disk adapters, and the session and build clocks,
So that Local mode keeps rooms and sessions on disk and the Demo timescale touches only thresholds.

_Covers AR-12, AR-14, FR-24, AD-7, AD-9, AD-10. Owner: infra (declares src/pipeline/ports.py first). Depends on: 1.8. Tier 1, Tue Oct 27. `LedgerStore`, `Cache`, `JobStore` and `JobRunner` are declared by the stories that need them (2.3, 2.4, 2.10)._

**Acceptance Criteria:**

**Given** `src/pipeline/ports.py`, declared first as this story's port change
**When** it is imported
**Then** it declares `ArtifactStore` (`put`, `read`, `list_rooms`) and `SessionStore` (`append`, `read_all`, `list_ids`, `delete`), and re-exports `Clock` from `src/domain/clock.py`
**And** `tests/test_boundaries.py` passes, with `ports.py` importing only the domain and `src/infra` importing only ports and the domain

**Given** the disk `ArtifactStore` in `src/infra/local.py`, under a temporary root in tests
**When** the fixture room and its photos are put and read back
**Then** the bytes round-trip unchanged under `rooms/`, and `list_rooms` returns the stored Rooms
**And** a key that resolves outside `rooms/` (for example `../x`) is refused

**Given** the JSON `SessionStore` in `src/infra/local.py`
**When** events are appended to two sessions under `rooms/sessions/`
**Then** `read_all` returns each session's events in append order, `list_ids` returns both ids, and `delete` removes one
**And** a new `SessionStore` instance over the same directory reads the same events, because no session state is held in a process variable

**Given** the session clock in `src/infra/clocks.py` with `DEMO_TIMESCALE=6`
**When** wiring asks it for the thresholds it passes into `apply`
**Then** the nudge threshold, the Rung spacing and the Trickster window are divided by 6 (90000 ms becomes 15000 ms, and the 3-minute window becomes 30000 ms)
**And** the elapsed milliseconds it supplies for `t_ms` are not scaled

**Given** the build clock with `DEMO_TIMESCALE=6`
**When** it measures an interval
**Then** the interval is never scaled

**Given** this story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 1.11: Room API: wiring, the PlayView and photo routes, and the static client

As a builder,
I want the room routes served by FastAPI with adapters chosen in one wiring module,
So that the browser can load a stored room's `PlayView` and photos from the same origin that serves the client, without ever seeing a solution.

_Covers FR-11, AR-12, AR-13, AR-17, AD-3, AD-9, AD-13. Owner: api. Depends on: 1.7, 1.10. Tier 1, Tue Oct 27._

**Acceptance Criteria:**

**Given** `src/api/wiring.py`
**When** the app starts
**Then** it builds every adapter from `Settings`, and a test confirms no other module constructs an adapter

**Given** the four-lock fixture room stored in the local `ArtifactStore`
**When** the client calls `GET /api/rooms/<room_id>` and `GET /api/rooms/<room_id>/photos/<i>`
**Then** the first returns the room's `PlayView` and the second returns the stored downscaled JPEG bytes for photo `i`, byte for byte
**And** a photo index outside the room's photos answers 404

**Given** an unknown `room_id`
**When** either room route is called
**Then** it answers 404 with the error envelope `{error: {code: "room_not_found", message, stage: null}}` raised as `RoomNotFound`

**Given** the running app
**When** routes and static files are requested
**Then** every API route lives under `/api/` and FastAPI mounts `web/dist` at `/`
**And** the app starts and the API tests pass when `web/dist` does not exist, because the mount is skipped

**Given** a Room with sentinel solutions
**When** an API fixture test reads every response of both routes
**Then** no response contains a `solution` key or any sentinel value

**Given** this story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 1.12: Session API: start, events, replayed state, idle ticks and the result

As a builder,
I want the session routes that start a play-through, take events, replay state and return the result,
So that the browser plays through one server-authoritative HTTP surface that later epics extend rather than replace.

_Covers FR-11, FR-12, FR-13, FR-20, AR-7, AR-13, AR-22, AD-4, AD-13. Owner: api. Depends on: 1.8, 1.11. Tier 1, Tue Oct 27._

**Acceptance Criteria:**

**Given** `POST /api/sessions {room_id, derived}`
**When** `derived` is omitted
**Then** the session starts with `Derived.fresh()` and the response carries a `sess_` id
**And** a `derived` outside its bounds (for example `persistence: 1.5`) answers 422 with the error envelope, `stage: null`, and no Session is created
**And** an unknown `room_id` answers 404 `room_not_found` in the envelope, and a body with any field other than `room_id` and `derived` answers 422

**Given** an open session
**When** the client posts a `click` or `lock_input` body to `POST /api/sessions/<id>/events`
**Then** the server stamps `t_ms` from the session clock, appends the event through `SessionStore` and applies it through `SessionStateMachine.apply`
**And** a body carrying `t_ms`, or a client-posted `idle_tick`, `opening_line`, `trickster_card` or `rung_change`, answers 422 and appends nothing
**And** an unknown session id answers 404

**Given** an open session and an injected session clock
**When** the client calls `GET /api/sessions/<id>`
**Then** it returns the session state replayed from the log, with `room_id`, `active_puzzle_id`, `opening_line`, `phrasing`, `disclosure` as an empty list (1.14 fills it with the global lines and 6.2 with the per-Room list), and the threshold fields declared but unpopulated until 3.3
**And** an `idle_tick` is appended when at least 5000 ms have passed since the last event, and none at 4999 ms

**Given** a session whose exit lock has opened
**When** the client calls `GET /api/sessions/<id>/result`
**Then** it returns the `RoomResult` computed from the log, with `demo` true exactly when `DEMO_TIMESCALE > 1`

**Given** any appended event
**When** the server logs it
**Then** it writes one JSON line with `session_id`, the event type and `duration_ms` (AR-22)

**Given** a Room with sentinel solutions
**When** an API fixture test plays it through every session route
**Then** no play response contains a `solution` key or any sentinel value

**Given** this story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 1.13: Opening line on session start: the First-room welcome

As a player,
I want a welcome line from the Guide the moment my play-through starts,
So that my first room opens in the game's voice and tells me what to look for.

_Covers FR-21, AR-31, AD-4, AD-5. Owner: api. Depends on: 1.12. Tier 1, Tue Oct 27. The Greeting path stays in Epic 5 (5.6), and the Demo room variant joins in 7.15._

**Acceptance Criteria:**

**Given** `POST /api/sessions` on a stored room
**When** the session is created
**Then** the server appends `OpeningLineEvent(kind: welcome)` at once with the fixed First-room welcome "Welcome to your own room. Find what doesn't belong." (A-13)
**And** the response returns `opening_line {kind: "welcome", text}` with `phrasing: false`
**And** until 5.6 adds the Greeting path, every session start gets the welcome, whatever Derived block it carries

**Given** a started session
**When** the client calls `GET /api/sessions/<id>`, before or after other events
**Then** the state carries the same `opening_line` and `phrasing: false`

**Given** a session that already has its opening line
**When** the client reloads and reads the state again any number of times
**Then** no second `OpeningLineEvent` is appended, and the log holds exactly one

**Given** the codebase
**When** the welcome text is searched for
**Then** it is defined in exactly one place on the server, and the client renders the text it receives without holding its own copy

**Given** this story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 1.14: Status, schema and room list endpoints: GET /meta, GET /schema and GET /rooms

As a builder,
I want the status model, the schema export and the stored-room list served by the API,
So that every surface can declare its mode and Disclosures, client types can be generated, and the player can choose a stored room.

_Covers FR-26, FR-6, AR-5, AR-12, AR-13, AR-19, AR-27, UX-DR79, AD-2, AD-9, AD-15. Owner: api. Depends on: 1.11, 1.12. Tier 1, Tue Oct 27._

**Acceptance Criteria:**

**Given** the running API in Local mode
**When** the client calls `GET /api/meta`
**Then** it returns exactly `{mode, guide, guide_model, trickster, demo_timescale, cache, profile, disclosure, retention}`, with `mode` set to the constant `"local"` by wiring (only local adapters exist until 7.2 adds `Settings.mode`), `guide` from `GUIDE`, and `guide_model` is `{id: "llama3.2:3b", host: the OLLAMA_HOST value}` when `GUIDE=ollama` and `null` when `GUIDE=verbatim`
**And** `GET /api/meta?profile=demo` returns `profile: "demo"`, and no parameter returns `profile: "dev"`
**And** `trickster` is `live` under `DEMO_TRICKSTER=live` or `record`, `scripted` under `scripted`, and `cut1` under `authored` (spine AD-15)

**Given** `src/api/meta.py`
**When** it composes the global Disclosure lines
**Then** at the defaults `disclosure` is empty; at `DEMO_TIMESCALE=6` it holds exactly "Hint and Trickster timings run at 6× speed; the build timer is real time."; and under `DEMO_TRICKSTER=scripted` it holds exactly "Trickster proposals replayed from a recording; the Validator ran live.", with the lines joined when both apply
**And** `meta.py` holds the cut 1 line "Trickster proposals were written in advance; the Validator ran live on each." verbatim, composed only under `DEMO_TRICKSTER=authored` (`trickster` reading `cut1`), and the scripted line is not composed under `authored` or `record`
**And** one function composes every list, so no other module writes a Disclosure line, and the session state's `disclosure` from `GET /api/sessions/<id>` carries the same global lines (the per-Room line joins in 6.2)

**Given** Local mode
**When** `retention` is read
**Then** it is the one Local Retention summary held in `src/api/meta.py`: the shared opening naming the Meta Model API standard tier and the Baseten or Fireworks fallback, the faces and documents request, and the local storage sentence "A copy of your photos is also kept on this computer.", with the final wording carried to Mon Oct 26 (PRD §13 Q3)

**Given** the running API
**When** the client calls `GET /api/schema`
**Then** it returns the JSON Schema of every model 1.5 declared, including `Room`, `RoomDraft`, `PlayView`, `BuildView`, `RoomView`, `RoomSummary`, `AccessCheck`, `Derived`, `RoomResult`, `Meta`, the job state, the session state, the event models and the error envelope

**Given** the fixture loader added by this story
**When** it runs
**Then** both fixture rooms from 1.6 and their downscaled photos are stored through the local `ArtifactStore` under `rooms/`, each only after `validate` returns no reasons, a second run stores no duplicate, and `GET /api/rooms` then lists both

**Given** the fixture loader has stored both fixture rooms in the local `ArtifactStore`
**When** the client calls `GET /api/rooms`
**Then** it returns one `RoomSummary {room_id, name, cover_photo, puzzle_count, job_id, built_at}` per stored Room through `ArtifactStore.list_rooms()`, newest build first, with no solution field
**And** with no stored Room it returns an empty list

**Given** this story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 1.15: Generated client types with a staleness test

As a builder,
I want the client types generated from `GET /schema` and committed, with a test that fails when they are stale,
So that the client and server can never drift apart, and the client only ever sees `PlayView`.

_Covers AR-5, AR-23, AD-2. Owner: web. Depends on: 1.4, 1.14. Tier 1, Tue Oct 27._

**Acceptance Criteria:**

**Given** the generator 1.4 pinned
**When** the npm script runs against the `GET /schema` output
**Then** it writes `web/types`, and the result is committed

**Given** the generated `web/types`
**When** the builder inspects them
**Then** `Room` and `RoomDraft` are excluded, `PlayView` is present, and no generated type declares a `solution` field

**Given** the generated `web/types`
**When** the builder inspects them
**Then** the event union (by `type`) and the lock-input union (`CodeInput | UseOnInput | OrderStartInput | OrderStopInput`) are discriminated unions on their `Literal` discriminators
**And** every key is snake_case, exactly as in the JSON

**Given** a model change in `src/domain/schema.py` without regeneration
**When** the offline staleness test runs
**Then** it fails, naming the stale types, and it passes after the npm script regenerates them
**And** any later model change goes through bmad-correct-course and regenerates them

**Given** this story's changes
**When** the web build and type check run
**Then** they pass with new tests covering this story's criteria, and `pytest` passes offline against the mock provider, including the staleness test

### Story 1.16: Design tokens and base components

As a builder,
I want every DESIGN.md token and the base buttons and focus ring implemented once,
So that every player surface draws from one dark study palette, one type system and one motion rule, and meets contrast by construction.

_Covers UX-DR1, UX-DR2, UX-DR3, UX-DR4, UX-DR5, UX-DR6, UX-DR9, UX-DR10, UX-DR11, UX-DR72, UX-DR85. Owner: web. Depends on: 1.4. Tier 1, Tue Oct 27, before any player surface._

**Acceptance Criteria:**

**Given** the client stylesheet
**When** the tokens are inspected
**Then** every `DESIGN.md` `colors` token is a CSS custom property with its exact hex (for example `canvas` #14100C, `parchment` #E8DBBE, `lamp` #E9A94B, `focus-ring` #FFD27A, `scrim` #0A0806CC), dark theme only, and each role token (`card-*`, `clue-card-*`, `graph-*`, `mask-overlay-*`) repeats its base hex

**Given** the built `web/dist`
**When** it is inspected
**Then** EB Garamond, Source Sans 3 and IBM Plex Mono are self-hosted as WOFF2 files, and no built file requests a third-party font host
**And** the 13 DESIGN.md type styles (`display-lg`, `display-md`, `display-sm`, `wizard-line-lg`, `wizard-line`, `lore`, `body-md`, `body-sm`, `label`, `caption`, `mono-timer`, `mono-code`, `mono-sm`) exist with their DESIGN.md sizes, weights and line heights (`display-lg` 40 through `mono-sm` 13, `lore` 17 italic, `mono-code` 20 tracked 0.2em), with Garamond never below 17 px, italic only on `lore`, sentence case and tabular figures for numbers that change in place

**Given** the layout tokens
**When** they are inspected
**Then** the 4 px spacing scale (4, 8, 12, 16, 24, 32, 48, 64), the named layout tokens (`frame-margin` 24, `side-column` 400, `top-bar` 48, `disclosure-min` 32, `thumbnail-strip` 88, `narrow-gutter` 16 and the rest), the radii (`none`, `sm` 4, `md` 8, `lg` 12, `full`) and the elevation tokens (`paper`, `overlay`, `lamp-glow`, `vignette`) exist as DESIGN.md defines them

**Given** the motion tokens
**When** any transition runs
**Then** it is a fade or a glow with `ease-out` at 150, 200 or 300 ms, and nothing slides, bounces, shakes or loops
**And** under `prefers-reduced-motion: reduce` every transition is instant

**Given** the primary and secondary buttons (`{components.button-primary}`, `{components.button-secondary}`) and the focus ring (`{components.focus-ring}`)
**When** they are rendered and operated by keyboard
**Then** the primary button is 44 px high with a lamp fill and an `on-lamp` label, and shows a pending label while its request is in flight, ignoring repeat activation; the secondary button is 40 px with a 1 px lamp border, has toggle variants that hold `lamp-hover-fill` plus a 2 px lamp border and announce pressed or expanded state, and has a parchment variant in `lamp-ink`
**And** the focus ring is a 2 px `focus-ring` outside a 2 px `focus-ring-inner` at 2 px offset on `:focus-visible`, and is never removed or replaced by the hover glow

**Given** the DESIGN.md contrast table
**When** the contrast audit runs over every token pair it lists
**Then** body text meets 4.5:1, and large text and non-text UI meet 3:1, on the dark theme

**Given** the client source
**When** the banned-interaction check this story adds runs
**Then** no module plays audio, uses the Notification API or registers a service worker, so there is no sound, no browser notification and no offline mode, and the only text a player types to a wizard is the hint field, whose text never leaves the browser (3.4)
**And** the other UX-DR85 bans are asserted by the stories that own each surface: no highlight on a new Evidence card (1.20), no dismissable Disclosure (1.17), no stacked modal (1.27), no reveal or skip after the near-answer (3.1), no "verbatim" badge (3.4), no image generation in play (3.6) and no Greeting in Hosted mode (7.15)

**Given** this story's changes
**When** `npm run build` and `tsc --noEmit` run in `web/` and `pytest` runs offline against the mock provider
**Then** all pass (pytest including the type-staleness test and any string, token or contrast checks this story adds), and the criteria above are verified in Chrome against the fixture rooms; a web test runner is added only through bmad-correct-course

### Story 1.17: App shell: Disclosure banner, top bar, mode indicator, routes, error banner and server unreachable

As a player,
I want every screen to sit inside one frame that always shows the active Disclosures and the mode,
So that I never see a surface without knowing which demo settings are in effect, and errors always appear in the same place.

_Covers FR-26, UX-DR7, UX-DR8, UX-DR12, UX-DR21, UX-DR56, UX-DR61, UX-DR62, UX-DR73, UX-DR75, UX-DR80, AR-12. Owner: web. Depends on: 1.15, 1.16. Tier 1, Tue Oct 27. Mockups: mockups/play-screen.html and mockups/capture-screen.html._

**Acceptance Criteria:**

**Given** a cold load
**When** `GET /api/meta` fails
**Then** the page body is empty except the centered status strip (`{components.status-strip}`) "Keyframe can't reach its server. Retrying.", which retries every 2000 ms, with no Disclosure banner, Retention summary or Scene guessed
**And** the surface renders only once `GET /api/meta` answers, so no surface ever renders without its Disclosures

**Given** a Disclosure list
**When** the Disclosure banner (`{components.disclosure-banner}`) renders
**Then** it shows the lines exactly as served (from `GET /meta` `disclosure` on `#/`, and from the session state's `disclosure` on the Play and Completion screens), one 32 px line per Disclosure, full width above the top bar and part of the grid
**And** it has no close control and takes no focus, is never overlaid or dimmed by a scrim, never covers the Scene, and is absent when the list is empty

**Given** the top bar
**When** any surface renders
**Then** it is the 48 px `chrome` bar with the Keyframe wordmark, the mode indicator (`{components.mode-indicator}`: "Local mode · Cache on · profile dev", or "Cache off" when `cache` is off; the rooms-played count joins in 5.1, and "Hosted mode" once `GET /meta` reports it) and the centered Timer slot
**And** the mode indicator is plain `body-sm` text, not focusable, and never styled as a Disclosure, and no surface offers a Cache-clear control

**Given** viewport widths of 1440, 1280 and 1024 px
**When** the Play layout renders
**Then** it uses 24 px margins, the Scene column and a side column of 400, 360 and 340 px respectively, with no horizontal page scroll

**Given** the client router
**When** the player navigates
**Then** the hash routes `#/`, `#/play/<session_id>` and `#/done/<session_id>` resolve, and `?profile=` is carried on every route and passed to `GET /meta`

**Given** the error banner component (`{components.error-banner}` with its `{components.warning-banner}` variant), built here for every later surface
**When** a newer banner state arrives while one is shown
**Then** it replaces the older one, spans the full width of the left area, takes focus, and shows a serif heading, one plain `body-md` sentence and its secondary actions, with no portrait
**And** every client-authored user-facing string comes from one strings module copied from EXPERIENCE.md Voice and Tone, and a test compares its verbatim strings with that source; lines the server serves (Disclosure lines, the Retention summary, opening lines) are not in the module and are rendered exactly as received

**Given** this story's changes
**When** `npm run build` and `tsc --noEmit` run in `web/` and `pytest` runs offline against the mock provider
**Then** all pass (pytest including the type-staleness test and any string, token or contrast checks this story adds), and the criteria above are verified in Chrome against the fixture rooms; a web test runner is added only through bmad-correct-course
**And** the shell meets the accessibility floor where it applies (focus ring on every control, contrast per the audit)

### Story 1.18: Stored Rooms list: choose a room to play

As a player,
I want a list of the rooms stored on this machine with a Play button for each,
So that I can start a stored room straight away.

_Covers UX-DR19, UX-DR21, UX-DR8, UX-DR62, AR-13. Owner: web. Depends on: 1.12, 1.14, 1.17. Tier 1, Tue Oct 27 (late; the Capture screen in 2.16 sits above it). Mockup: none for the list (DESIGN.md Stored Room row; mockups/capture-screen.html shows the Capture layout it sits under)._

**Acceptance Criteria:**

**Given** `#/` in Local mode with two fixture rooms stored
**When** the list renders
**Then** it shows one Stored Room row (`{components.stored-room-row}`) per `RoomSummary` from `GET /api/rooms` only, newest build first, each with a 96 x 72 cover thumbnail, the Room's name or else its build date and time, the Puzzle count and "Play"
**And** the browser keeps no room list of its own

**Given** no stored Rooms
**When** `#/` renders
**Then** the list reads "No rooms yet."

**Given** a stored Room row
**When** the player activates "Play"
**Then** the client posts `POST /api/sessions {room_id, derived}` with `Derived.fresh()` (until 5.1) and nothing else from any profile, then routes to `#/play/<session_id>` with no Timer shown

**Given** a session start that fails
**When** `POST /api/sessions` answers an error
**Then** the session-start-refused error banner shows at the top of the left area with the heading "Keyframe couldn't start this room.", the body "Your room is safe. Try again." and "Try again", and takes focus
**And** "Try again" posts the session start again

**Given** keyboard use
**When** the player tabs through the list
**Then** each "Play" is reachable with the two-tone focus ring, Enter starts it, and a row shows the lamp ring on hover. "How this room was built" joins in 2.31 and is absent under cut 0, and the dropzone joins above the list in 2.16

**Given** this story's changes
**When** `npm run build` and `tsc --noEmit` run in `web/` and `pytest` runs offline against the mock provider
**Then** all pass (pytest including the type-staleness test and any string, token or contrast checks this story adds), and the criteria above are verified in Chrome against the fixture rooms; a web test runner is added only through bmad-correct-course

### Story 1.19: Photo Scenes with mask Hotspots and the Thumbnail strip

As a player,
I want to see my room as photo Scenes whose objects respond when I point at them,
So that I can explore the room's real objects and move between photos.

_Covers FR-11, UX-DR22, UX-DR23, UX-DR24, UX-DR25, AR-15, NFR-10, AD-11. Owner: web. Depends on: 1.17, 1.18. Tier 1, Wed Oct 28. Mockup: mockups/play-screen.html. If textured planes cost more than 2 h, the DOM-only fallback is taken and Tier 2 stays no-go._

**Acceptance Criteria:**

**Given** a session on the four-lock fixture room
**When** the Play screen loads
**Then** each photo from `GET /api/rooms/<room_id>/photos/<i>` is drawn on a three textured plane inside the Scene frame (`{components.scene-frame}`): contained, never cropped, enhanced or tinted, with portrait photos letterboxed, and a plain loading line until the first photo and its Hotspots are live

**Given** a rendered Scene at 1440, 1280 and 1024 px widths
**When** Hotspots (`{components.hotspot}`) are built
**Then** each Hotspot is the union of its Interactable's `polygons` in the stored 1280 px pixel space, scaled to the rendered size, its id equals the Interactable id, and the client never reads `box`

**Given** a rendered Hotspot
**When** the pointer hovers it
**Then** it shows the 2 px lamp outline, 1 px dark halo and 35% glow fill within 150 ms, with a pointer cursor, and shows no label
**And** a click inside any of its polygons posts exactly one `ClickEvent(interactable_id)` with no timestamp, while a click outside every Hotspot posts nothing

**Given** a click on a Hotspot that is not a target
**When** the session state returns
**Then** only the Hotspot label chip (`{components.hotspot-label-chip}`) shows the Interactable's label, 8 px above the polygon, fading after 2 s or on pointer leave

**Given** a room with several photos
**When** the Thumbnail strip renders
**Then** it shows a 96 x 72 thumbnail (`{components.thumbnail}`) per photo in upload order (A-12) with 8 px gaps, scrolling inside its own row; the current photo has the 2 px lamp border and is announced as current; and click or Enter switches the Scene

**Given** the first pointer response on any Hotspot
**When** it happens
**Then** the Scene emits a first-pointer-response signal, once per session, for the Timer to stop on (T1, 2.17)
**And** if the DOM-only fallback is taken, every Hotspot is a DOM element with the same id and posts the same `ClickEvent`

**Given** this story's changes
**When** `npm run build` and `tsc --noEmit` run in `web/` and `pytest` runs offline against the mock provider
**Then** all pass (pytest including the type-staleness test and any string, token or contrast checks this story adds), and the criteria above are verified in Chrome against the fixture rooms; a web test runner is added only through bmad-correct-course
**And** every control this story adds is reachable by Tab, activates with Enter, shows the two-tone focus ring and passes the DESIGN.md contrast audit (the Scene-wide floor lands in 1.25)

### Story 1.20: Inventory, Wizard notes with Evidence cards, and the Wizard portrait component

As a player,
I want to see what I am holding and each available puzzle's clue, lore and evidence,
So that I know what to look for, and everything shown matches what the server says.

_Covers FR-11, UX-DR26, UX-DR27, UX-DR29, UX-DR39, UX-DR65, AR-7. Owner: web. Depends on: 1.19. Tier 1, Wed Oct 28. Mockup: mockups/play-screen.html. Painted portraits arrive in 3.6._

**Acceptance Criteria:**

**Given** an open session
**When** the Play screen is open, including while the tab is hidden
**Then** the client polls `GET /api/sessions/<id>` every 2000 ms and renders open locks, the Inventory and Wrong attempts only from server state, never inferring any of them from its own clicks

**Given** the session state
**When** the Inventory (`{components.inventory}`) renders
**Then** it is a `chrome-raised` tray of 64 px slots, three across, each item a 56 px crop with a `caption` label
**And** with nothing held it shows one dashed slot and "Nothing in hand yet."

**Given** the `PlayView` and session state
**When** the Wizard notes (`{components.wizard-notes}`) render
**Then** the parchment sheet shows one entry per available Puzzle in availability order, headed "Puzzle {n}" (n = the Puzzle's fixed place in the Room) with "{k} evidence cards" at the right end ("1 evidence card" for one), then the Riddler portrait beside the Clue, the Evidence cards, the Lore in `lore` type, the opened-Rungs slot and the lock-input slot
**And** Puzzles with unmet prerequisites are not drawn

**Given** `active_puzzle_id`
**When** the notes render
**Then** the Active puzzle's entry carries the `{components.active-puzzle-marker}` (a 3 px `lamp-ink` left rule plus the word "Current"), and while `active_puzzle_id` is null the first available Puzzle carries it

**Given** a Puzzle's Evidence cards
**When** they render (`{components.evidence-card}`)
**Then** each is an inset `parchment-shade` row with a 64 px crop of the Interactable cut from its photo using the polygons' bounds (never `box`), the Interactable label and the read attribute, in the order `PlayView` gives
**And** cards have one state only, and a new card gets no highlight, badge or announcement

**Given** the Wizard portrait component (`{components.wizard-portrait}`)
**When** it renders at 24, 32, 48 and 96 px
**Then** it is a circle with a 2 px gilt ring, with an empty alt and a visually hidden speaker prefix ("The Riddler:") on its line, reading `web/public/portraits/`
**And** when a portrait file is missing it falls back to the wizard's initial in `display-sm` gilt on `chrome-raised`

**Given** this story's changes
**When** `npm run build` and `tsc --noEmit` run in `web/` and `pytest` runs offline against the mock provider
**Then** all pass (pytest including the type-staleness test and any string, token or contrast checks this story adds), and the criteria above are verified in Chrome against the fixture rooms; a web test runner is added only through bmad-correct-course
**And** every control this story adds is reachable by Tab, activates with Enter, shows the two-tone focus ring and passes the DESIGN.md contrast audit (the Scene-wide floor lands in 1.25)

### Story 1.21: Code and find locks with Checking, Not this and Open feedback

As a player,
I want to type codes and find objects, with plain feedback the moment the server answers,
So that I can solve `code` and `find` puzzles and always know whether an input worked.

_Covers FR-12, UX-DR34, UX-DR38, UX-DR23, UX-DR65. Owner: web. Depends on: 1.20. Tier 1, Wed Oct 28 (the room is playable from here). Mockup: mockups/play-screen.html._

**Acceptance Criteria:**

**Given** an available `code` Puzzle
**When** its entry renders
**Then** the Code field (`{components.code-field}`) is a 168 x 44 `parchment-shade` inset in `mono-code`, accepting up to 6 characters, with no visible label or placeholder and the accessible name "Code for Puzzle {n}"
**And** Submit (secondary) is disabled below 3 characters, and Enter or Submit posts exactly one `LockInputEvent` with a `CodeInput`, with no client comparison

**Given** a submitted code
**When** the server has not yet answered
**Then** the field is read-only and the "Checking" chip (`{components.chip-pending}`) shows with a static ellipsis, and it is not announced

**Given** a wrong code
**When** the session state shows the Puzzle's `wrong_attempts` increased
**Then** the chip (`{components.chip-not-this}`) reads "Not this · {n}" with the server's count, and the field keeps its value, selected for retyping, with no shake and no sound

**Given** a correct code
**When** the session state shows the lock open
**Then** "Open" is held for 1200 ms, then the entry collapses to one line with the Open chip (`{components.chip-open}`), the next available Puzzle fades in, and focus moves to its heading

**Given** an available `find` Puzzle
**When** the player clicks its target Hotspot
**Then** only the `ClickEvent` is posted, and once the state shows the lock open, the target's glow fades out over 200 ms while its item fades into the Inventory
**And** a later click on that Hotspot shows "{label} · in hand" on its label chip

**Given** an input for a Puzzle whose prerequisites are not open
**When** the state returns unchanged
**Then** the input is not shown as a Wrong attempt, and only the "Checking" chip clears

**Given** this story's changes
**When** `npm run build` and `tsc --noEmit` run in `web/` and `pytest` runs offline against the mock provider
**Then** all pass (pytest including the type-staleness test and any string, token or contrast checks this story adds), and the criteria above are verified in Chrome against the fixture rooms; a web test runner is added only through bmad-correct-course
**And** every control this story adds is reachable by Tab, activates with Enter, shows the two-tone focus ring and passes the DESIGN.md contrast audit (the Scene-wide floor lands in 1.25)

### Story 1.22: First-room welcome card before the first Scene

As a player,
I want the Guide to welcome me before I start,
So that I meet the Guide, know what to look for, and know help is coming.

_Covers FR-21, UX-DR45, UX-DR64, UX-DR74, UX-DR70, UX-DR17. Owner: web. Depends on: 1.13, 1.20. Tier 1, Wed Oct 28. The Greeting loading path joins in 5.7. Mockup: mockups/completion-greeting.html._

**Acceptance Criteria:**

**Given** a new session whose `POST /api/sessions` response carries `opening_line {kind: "welcome", text}`
**When** the Play screen first opens
**Then** a 560 px parchment card (`{components.greeting-overlay}`) fades in over the scrim in 300 ms, showing the Guide's introduction (96 px portrait, heading "The Guide", and the role line for the mode: "Reads how you play; offers one hint at a time, never the answer, worded by Llama 3.2 3B on this Mac." when `GET /meta` `guide` is `ollama`, ending "shown as written." when it is `verbatim`), the served `text` in `wizard-line-lg`, the voice line "Get stuck as often as you like. I'll help, a little at a time." and "Begin"

**Given** the welcome card
**When** the player presses Escape or clicks the scrim
**Then** nothing happens: "Begin" is the only control and the only way to dismiss it, focus is trapped on "Begin", and the dialog is labelled by its heading only
**And** the scrim starts below the top bar, so the Timer slot stays undimmed, and the Scene, Hotspots and top bar are inert

**Given** the card appears
**When** the live region is written
**Then** it receives "The Guide. {role line} {opening line} {voice line}" exactly once

**Given** the player activates "Begin"
**When** the card closes
**Then** focus goes to the first Hotspot of the first Scene, and the client keeps the opening line in its play state, not announced again, for the Hint area that 3.4 renders it in
**And** a reload of `#/play/<session_id>` once play has events does not show the card again

**Given** this story's changes
**When** `npm run build` and `tsc --noEmit` run in `web/` and `pytest` runs offline against the mock provider
**Then** all pass (pytest including the type-staleness test and any string, token or contrast checks this story adds), and the criteria above are verified in Chrome against the fixture rooms; a web test runner is added only through bmad-correct-course
**And** the card meets the accessibility floor (focus ring, contrast, reduced motion makes the fade instant)

### Story 1.23: Completion screen with stats and Build another room

As a player,
I want a Completion screen that shows how I did once I open the Exit puzzle,
So that the room ends with a clear result and an obvious next step.

_Covers FR-13, UX-DR44, UX-DR66, UX-DR78, UX-DR8. Owner: web. Depends on: 1.21. Tier 1, Wed Oct 28. Recording into the Player profile joins in 5.1, and the Build view link in 2.31. Mockup: mockups/completion-greeting.html._

**Acceptance Criteria:**

**Given** the session state shows the Exit puzzle open
**When** its "Open" state ends
**Then** the client routes to `#/done/<session_id>` and shows the 720 px parchment Completion sheet (`{components.completion-sheet}`) over the dimmed last Scene, reading `GET /api/sessions/<id>/result`: the heading "The room is open.", the Guide sign-off with its 48 px portrait, "Time", "Hints used" and "Wrong attempts" three across in `mono-timer`, and a "Time per puzzle" table of "Puzzle {n}" rows with no header row and no Exit mark

**Given** the result's Rungs used
**When** the sign-off is chosen
**Then** 0 Rungs gives "Not a single hint. I'm almost offended.", 1 to 3 gives "You let me help a little. I enjoyed every word.", and 4 or more gives "We solved it together, and I'd do it again."

**Given** the Completion screen
**When** it is shown
**Then** its one primary action "Build another room" goes to `#/`; the Disclosure banner stays visible and undimmed; the top-bar Play controls stay in place but inert, with the Timer frozen; the heading takes focus; and the sign-off is written to the live region once, as "The Guide: {line}"

**Given** `GET /api/sessions/<id>/result` fails
**When** the sheet loads
**Then** it shows "Keyframe couldn't load the result. Retrying." and retries every 2000 ms, with "Build another room" still available
**And** the stats show as pending until the result returns

**Given** this story's changes
**When** `npm run build` and `tsc --noEmit` run in `web/` and `pytest` runs offline against the mock provider
**Then** all pass (pytest including the type-staleness test and any string, token or contrast checks this story adds), and the criteria above are verified in Chrome against the fixture rooms; a web test runner is added only through bmad-correct-course
**And** the screen meets the accessibility floor (heading focus, one live-region announcement, contrast)

### Story 1.24: Reload resume, reconnecting and missing rooms on the Play screen

As a player,
I want a reload or a dropped connection to leave my progress intact,
So that nothing I did is lost or miscounted when the page or the server stutters.

_Covers FR-11, UX-DR13, UX-DR22, UX-DR47, UX-DR65, AR-13. Owner: web. Depends on: 1.21. Tier 1, Thu Oct 29. The armed order state is rebuilt in 1.26 and Rungs in 3.4; the 410 notice joins in 7.21. Mockup: mockups/play-screen.html._

**Acceptance Criteria:**

**Given** a session with open locks and collected items
**When** the player reloads `#/play/<session_id>`
**Then** the client rebuilds the first Scene, the Inventory and the open locks from `GET /api/sessions/<id>` and the `PlayView` for its `room_id`, with no welcome card and nothing re-announced

**Given** two consecutive missed polls
**When** the second one fails
**Then** the status strip (`{components.status-strip}`) "Reconnecting to Keyframe. Your progress is safe; play resumes when it's back." takes 32 px at the top of the Scene column, the Scene frame shrinks by its height so no Hotspot is covered, the photo dims to 60%, and every input is disabled
**And** the line is written to the live region once, and the strip takes no focus

**Given** an input that never reached the server while reconnecting
**When** the connection returns
**Then** that input is dropped and nothing is counted for it, the Code field keeps its typed value, and the screen re-renders from server state with the strip removed

**Given** `GET /api/sessions/<id>` answers 404 for the session
**When** the Play screen polls
**Then** the photo dims under the plain line "This play-through has ended. Start the room again." on `chrome-raised`, with "Start again", which starts a new Session on the same room

**Given** `GET /api/rooms/<room_id>` answers 404 `room_not_found`
**When** the Play screen loads
**Then** a centered 480 px `chrome-raised` card shows "Keyframe can't find this room" and "Check the link, or start from the beginning." with "Build a room", which goes to `#/`, and focus is on the heading

**Given** this story's changes
**When** `npm run build` and `tsc --noEmit` run in `web/` and `pytest` runs offline against the mock provider
**Then** all pass (pytest including the type-staleness test and any string, token or contrast checks this story adds), and the criteria above are verified in Chrome against the fixture rooms; a web test runner is added only through bmad-correct-course
**And** every control this story adds is reachable by Tab, activates with Enter, shows the two-tone focus ring and passes the DESIGN.md contrast audit (the Scene-wide floor lands in 1.25)

### Story 1.25: Accessibility floor on Scenes and locks

As a player,
I want to reach every object and lock by keyboard and hear outcomes through a screen reader,
So that I can play the whole room without a mouse or without seeing every visual cue.

_Covers NFR-14, UX-DR69, UX-DR70, UX-DR71, UX-DR72, UX-DR6, UX-DR11, UX-DR23. Owner: web. Depends on: 1.21, 1.22. Tier 1, Thu Oct 29. `use_on` select-then-click ships with 1.26. Mockup: mockups/play-screen.html._

**Acceptance Criteria:**

**Given** a rendered Scene
**When** the player presses Tab
**Then** every Hotspot is a focusable element in the Scene's accessible overlay (the same ids in the DOM-only fallback), with the role of a button and its label as accessible name, in Tab order by polygon centroid from top to bottom, then left to right
**And** focus traces the two-tone ring along the polygon and shows the label chip for as long as the Hotspot has focus, and Enter acts as a click

**Given** the top bar
**When** the player activates "Show all objects"
**Then** the toggle announces its pressed state, and every Hotspot gets a 2 px dashed `hotspot-show-all` outline with halo, with no fill and no labels
**And** the outlines persist across Scene changes until the toggle is released

**Given** the First-room welcome card
**When** it shows
**Then** a plain one-time tip sits on the scrim under it: "Tip: 'Show all objects' in the top bar outlines everything you can click."

**Given** the Play and Completion screens
**When** outcomes occur
**Then** exactly one `aria-live="polite"` region receives "Puzzle {n}: not this, {count}." and "Puzzle {n}: open." for lock outcomes, plus the welcome, the sign-off and the reconnecting line (Rungs and Cards join in 3.4 and 4.5)
**And** "Checking" is never announced, and nothing is re-announced on reload

**Given** keyboard-only play
**When** the player tabs through the Play screen
**Then** focus moves top bar → Hotspots → Thumbnail strip → Inventory → Wizard notes (the Hint area joins at the end of this order in 3.4), with no single-key shortcuts, and every surface control shows the focus ring

**Given** `prefers-reduced-motion: reduce` and the DESIGN.md contrast table
**When** the reduced-motion check and the contrast audit run over the Play and Completion screens
**Then** every fade is instant, and every text and state pair meets 4.5:1 for body text and 3:1 for large text and non-text UI, with every state carrying a word ("Not this", "Open", "Current"), never color alone

**Given** this story's changes
**When** `npm run build` and `tsc --noEmit` run in `web/` and `pytest` runs offline against the mock provider
**Then** all pass (pytest including the type-staleness test and any string, token or contrast checks this story adds), and the criteria above are verified in Chrome against the fixture rooms; a web test runner is added only through bmad-correct-course

### Story 1.26: Order and use_on interactions, by drag or select-then-click

As a player,
I want to start and stop an object sequence and to use an item on an object by dragging it or by selecting it and then clicking,
So that I can solve `order` and `use_on` puzzles with a mouse or a keyboard.

_Covers FR-12, NFR-14, UX-DR35, UX-DR36, UX-DR37, UX-DR26, UX-DR69. Owner: web. Depends on: 1.9, 1.25. Tier 1, Thu Oct 29, right after the accessibility floor, so rooms built from Wed Oct 28 with all four lock types can be finished; cut 6 drops this story (together with 1.9). Mockup: mockups/play-screen.html._

**Acceptance Criteria:**

**Given** an available `order` Puzzle in the four-lock fixture room
**When** the player activates "Start the sequence" in its entry (`{components.order-progress}`)
**Then** the client posts `OrderStartInput(puzzle_id)`, and the control reads "Stop the sequence" and keeps focus
**And** "Stop the sequence" posts `OrderStopInput(puzzle_id)` and empties the pips with no Wrong attempt

**Given** an armed sequence with 3 to 5 pips (10 px) and the hidden description "{filled} of {length}"
**When** the player clicks Hotspots
**Then** a pip fills in `lamp-ink` only when the session state acknowledges the click into the buffer, never optimistically and never showing which clicks were right
**And** a full-length mismatch turns the pips `wrong-ink` for 300 ms (an instant reset under reduced motion), empties them and shows "Not this · {n}" with the sequence still armed

**Given** an armed order Puzzle
**When** the player starts the sequence on another order Puzzle, switches Scenes or reloads
**Then** starting another stops the armed one first, and the armed state and filled pips survive Scene switches and reloads, rebuilt from session state

**Given** an Inventory item
**When** the player drags it onto a Hotspot and drops it
**Then** the item shows at 60% in place, with a 64 px drag image, and the Hotspot under the pointer shows its hover state; the drop posts one `LockInputEvent` with `UseOnInput {item, target}` and no `puzzle_id`, and the target's label chip shows with "Checking" beside it until the verdict
**And** a drop anywhere else posts nothing

**Given** an Inventory item selected by click or Enter
**When** the player then clicks or presses Enter on a Hotspot
**Then** the item carries the 2 px lamp ring and a parchment chip (`{components.use-on-selected}`) "Using {item label}" with "Cancel" is pinned to the top-left of the Scene frame; the Hotspot activation posts the same `UseOnInput` and no `click`, then clears the selection
**And** the Thumbnail strip stays usable while the item is selected, and Escape, "Cancel" or a second activation of the item clears the selection

**Given** a `use_on` input
**When** the session state returns
**Then** the verdict ("Not this · {n}" or "Open") shows in the resolved Puzzle's entry, which becomes Current
**And** a pair resolving to no Puzzle counts nothing and only clears "Checking"

**Given** this story's changes
**When** `npm run build` and `tsc --noEmit` run in `web/` and `pytest` runs offline against the mock provider
**Then** all pass (pytest including the type-staleness test and any string, token or contrast checks this story adds), and the criteria above are verified in Chrome against the fixture rooms; a web test runner is added only through bmad-correct-course
**And** the order controls and select-then-click meet the accessibility floor (focus ring, keyboard path, announced lock outcomes)

### Story 1.27: Narrow-screen message and Leave room confirmation

As a player,
I want a clear message on a small screen and a confirmation before I leave a room,
So that I am never stuck with a broken layout and never lose a play-through by accident.

_Covers UX-DR60, UX-DR46, UX-DR7, UX-DR8, UX-DR71, NFR-10, AR-32. Owner: web. Depends on: 1.17, 1.21. Tier 1, Sat Oct 31._

**Acceptance Criteria:**

**Given** a viewport narrower than 1024 px
**When** any route is open
**Then** the whole app is replaced by the canvas with a centered plain `chrome-raised` card (`{components.narrow-screen-message}`), at most 480 px wide with 16 px side gutters, holding the wordmark, "Keyframe needs a bigger screen" and "Open this page on a laptop or desktop browser to play.", with no horizontal scroll (no mobile layout, AR-32)
**And** widening past 1024 px returns the app with its state intact

**Given** the Play screen
**When** the player activates "Leave room" in the top bar or presses the browser Back button
**Then** a plain 480 px `chrome-raised` confirmation (`{components.leave-room-confirmation}`) opens over the scrim with "Leave this room? This play-through won't be recorded.", "Keep playing" (primary, focused) and "Leave room" (secondary), with focus trapped and the Scene, Hotspots and top bar inert

**Given** the confirmation is open
**When** the player presses Escape or activates "Keep playing"
**Then** it closes, and focus returns to "Leave room", or to the first Hotspot when it was opened by Back

**Given** the confirmation is open
**When** the player confirms "Leave room"
**Then** no Room result is recorded and the client goes to `#/` (the Hosted landing points it home in 7.17)
**And** while the confirmation is open no other modal opens over it, so modals never stack

**Given** this story's changes
**When** `npm run build` and `tsc --noEmit` run in `web/` and `pytest` runs offline against the mock provider
**Then** all pass (pytest including the type-staleness test and any string, token or contrast checks this story adds), and the criteria above are verified in Chrome against the fixture rooms; a web test runner is added only through bmad-correct-course
**And** both surfaces meet the accessibility floor (focus trap, focus ring, contrast)

## Epic 2: Turn your photos into a verified room

A player uploads 6 to 10 JPEG photos and, within the capture target, gets a room built from their own objects that passed the Validator and the Dry run. The Capture screen shows every stage, failure and Regeneration as it happens, and, unless cut 0 is taken, a Build view shows how the room was built. Every paid call is cached, priced and capped, and each one is recorded in a Ledger that is exported daily. The lean SIT checks the live seams at the end of each build day.

### Story 2.1: Model ports with a scripted mock

As a builder,
I want one synchronous `ModelProvider` port with the Tier 1 signatures and a scripted mock adapter behind it,
So that the council and pipeline stories can be built and tested offline against the same calls the real adapters will serve.

_Covers AR-8, AR-23, NFR-8, AD-5, AD-17. Owner: providers. Depends on: 1.2, 1.5. Tier 1, Mon Oct 26. `providers/base.py` declares `ModelProvider` `chat(messages, *, images=[], response_schema=None, reasoning_effort='low', model=None)`, `segment(label, image) -> list[Polygon] | None` and `generate_image(prompt)`; `HintPhraser` joins in 3.2 and `transcribe` in 9.1 (`reconstruct3d` only if the Tier 2 gate passes); scripted mock per role (architect, riddler, dryrun, trickster, image) with sockets disabled, refusing `reasoning_effort` 'none' like the real API; the recorded-fixture replay format under `tests/fixtures/providers`; per-role resolution (`PROVIDER_<ROLE>`) is api wiring and lands in 2.12. Dev skill: keyframe-muse._

**Acceptance Criteria:**

**Given** `src/providers/base.py`
**When** the `ModelProvider` ABC is inspected
**Then** it declares exactly `chat(messages, *, images=[], response_schema=None, reasoning_effort='low', model=None) -> ChatResponse`, `segment(label, image) -> list[Polygon] | None` and `generate_image(prompt) -> ImageResponse`
**And** `chat` no longer accepts the scaffold's `max_tokens` or `temperature`, and this story declares no `reconstruct3d`, `transcribe` or `HintPhraser`

**Given** the mock adapter with a script for each role (`architect`, `riddler`, `dryrun`, `trickster`, `image`)
**When** a role's mock receives a `chat`, `segment` or `generate_image` call
**Then** it returns the scripted reply for that role and call kind, and a `segment` script can return `None` to stand for "no mask"
**And** the test runs with sockets disabled and opens no network connection

**Given** the mock adapter
**When** `chat` is called with `reasoning_effort='none'`
**Then** the call is refused with an error and no reply is returned
**And** each of `minimal`, `low`, `medium`, `high` and `xhigh` is accepted

**Given** a hand-written sample fixture in the recorded-response format under `tests/fixtures/providers`
**When** it is replayed
**Then** it parses into the same `ChatResponse`, `ImageResponse` or polygon types a live adapter returns
**And** a replay that asks for a missing fixture raises an error that names the missing fixture, and never falls through to the network
**And** the format stores responses only, and adapter tests build their input images in the test, never from a committed room photo

**Given** `src/council` and `src/pipeline`
**When** `tests/test_boundaries.py` walks their imports
**Then** they reach a model only through `providers/base.py` and never import `providers/mock.py` or any other adapter

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.2: Spend arithmetic as pure domain functions

As a builder,
I want pricing, estimates, running totals and the cap check as pure functions in the domain,
So that every spend decision is deterministic and testable without a store, a lock or a clock.

_Covers FR-28, AR-9, NFR-6, AD-6. Owner: domain. Depends on: 1.5. Tier 1, Mon Oct 26. `domain/ledger.py`: price from usage at the `budgets.md` rates, per-call estimates seeded from `budgets.md`, running totals and the cap check as pure functions returning new values; a retried call is one entry; no date logic (`SPEND_CAP_USD` is 80 until the Nov 5 reset, then 25, by configuration only). Dev skill: keyframe-muse._

**Acceptance Criteria:**

**Given** usage returned by a `muse-spark-1.3` call
**When** it is priced
**Then** the cost is $1.25 per million input tokens, $0.15 per million cached input tokens and $4.25 per million output tokens, with reasoning tokens billed as output
**And** a `sam-3.1` call is priced at $2.50 per 1,000 images and a `muse-image-1.0` call at $0.01 per image

**Given** a call kind with no observed cost among the entries passed in
**When** its estimate is computed
**Then** it is the seed: vision $0.03, SAM $0.0025, Riddler $0.03, dry run $0.03, Trickster $0.01, image $0.01, `reconstruct3d` $0.02
**And** once a cost of that kind has been observed, the estimate is the last observed cost of that kind

**Given** a list of reserved and settled entries and a cap
**When** the running total and the cap check are computed
**Then** each `call_` id counts once, its settled cost replacing its reserved estimate
**And** the check reports would-exceed exactly when settled plus reserved spend plus the new call's estimate passes the cap

**Given** a call that was retried once and then settled
**When** its entries are folded
**Then** the result holds one entry for that `call_` id, never two
**And** every function returns new values and leaves its inputs unchanged

**Given** `src/domain/ledger.py`
**When** it is inspected and `tests/test_boundaries.py` runs
**Then** the cap is a function argument, the module holds no date or clock reference, and it imports only the standard library and pydantic

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.3: Spend ledger and cap guard every paid call

As a builder,
I want every paid call reserved, settled and capped through one per-process `SpendLedger` before the first real call is made,
So that spend can never pass `SPEND_CAP_USD` unnoticed and every dollar is recorded.

_Covers FR-28, AR-9, NFR-6, AD-6. Owner: providers (declares `LedgerStore` in `src/pipeline/ports.py` first). Depends on: 1.10, 2.1, 2.2. Tier 1, Mon Oct 26 to Tue Oct 27, before the first real call. Declares `LedgerStore` (append, entries); one `SpendLedger` per process serializing guard under a lock over the 2.2 arithmetic; a reserved entry under a `call_` ULID replaced by the observed cost; a refused call raises `SpendCapExceeded` and is never made; the mock bypasses the ledger._

**Acceptance Criteria:**

**Given** that the story first declares `LedgerStore` (`append`, `entries`) in `src/pipeline/ports.py`, and that a `SpendLedger` in `providers/spend.py` runs over an in-memory test double
**When** a paid call is guarded and then returns usage
**Then** a `reserved` entry holding the estimate is appended under a new `call_` ULID before the call, and the observed cost from the returned usage replaces it under the same `call_` id after the call
**And** the running total counts that call once, at its observed cost, and every entry carries its kind plus the `job_id` and `stage` (or the `session_id`) it was made for

**Given** settled plus reserved spend plus a call's estimate that would pass `SPEND_CAP_USD`
**When** `guard` runs
**Then** it raises `SpendCapExceeded` carrying the cap and the running total, the provider call is never made, and no entry is appended

**Given** many threads guarding calls at once while total spend is close to the cap
**When** they race
**Then** `guard` is serialized under the ledger's lock, reserved plus settled spend never passes the cap, and every call over the cap raises `SpendCapExceeded`

**Given** an adapter that retries a call once inside one guarded call
**When** the call settles
**Then** the ledger holds one entry for it under one `call_` id

**Given** the mock provider
**When** any call is made, even after the cap is reached
**Then** it appends no ledger entry and is never refused, so development loops never draw on the cap

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.4: Model-call cache in front of the ledger

As a builder,
I want identical model calls served from a cache that sits in front of the ledger guard,
So that the same photos and prompt are never billed twice, and a Regeneration is never served its own failed answer.

_Covers FR-27, AR-9, AD-6. Owner: providers (declares `Cache` in `src/pipeline/ports.py` first). Depends on: 2.3. Tier 1, Tue Oct 27. Declares `Cache` (get, put); key = sha256(model id, schema hash, full prompt with system message, reasoning effort, image hashes in order, attempt); a hit is never priced or refused; `CACHE=off` bypasses the cache, never the ledger; attempt n is never served attempt n-1's answer; the mock bypasses both._

**Acceptance Criteria:**

**Given** that the story first declares `Cache` (`get`, `put`) in `src/pipeline/ports.py`
**When** `src/providers/cache.py` computes a key
**Then** the key is `sha256(model id || schema hash || full prompt including the system message || reasoning_effort || sha256 of each image in order || attempt)`, with `attempt` defaulting to 0 and the image segment left out of text-only calls
**And** changing any single component changes the key, including the order of the images or the `attempt`

**Given** `CACHE=on` and a call whose key is already cached
**When** the call is made
**Then** the cached response is returned before the ledger guard runs, no ledger entry is appended, and the call is not refused even when the cap has been reached

**Given** `CACHE=on` and a cache miss
**When** the call completes
**Then** it was guarded and priced exactly once by the ledger, and its response is stored under its key

**Given** a cached response for a call made with `attempt=0`
**When** the same call is made with `attempt=1`
**Then** it misses the cache, reaches the provider and is priced, so attempt n is never served attempt n-1's answer

**Given** `CACHE=off`
**When** an identical call is made twice
**Then** the cache is neither read nor written, and both calls pass through the ledger guard and are priced
**And** the mock provider bypasses both the cache and the ledger under `CACHE=on` and `CACHE=off` alike

**Given** any call through `providers/cache.py`
**When** it returns
**Then** the caller learns whether it was served from the cache or billed, its model id, its host and its spend, for `chat`, `generate_image` and `segment` alike, so each stage writes its call row (AD-16)
**And** if `segment`'s return type must change for this, the port change is agreed with the architect and declared in this story first

**Given** the story's changes
**When** `pytest` runs offline against the mock provider, with a `Cache` test double
**Then** it passes with new tests covering this story's criteria

### Story 2.5: Local ledger file and disk cache

As a builder,
I want the ledger and the cache stored on the Mac's disk in separate places,
So that the spend total survives a restart and clearing the cache can never touch the record of spend.

_Covers FR-27, FR-28, AR-9, AR-12, NFR-6, AD-9. Owner: infra. Depends on: 2.3, 2.4. Tier 1, Tue Oct 27. `LedgerStore` as `spend/ledger.jsonl` under a file lock outside `.cache/`, the total surviving a restart; disk `Cache` under `.cache/`; deleting `.cache/` never touches the ledger or its exports._

**Acceptance Criteria:**

**Given** the local `LedgerStore` in `src/infra/local.py`
**When** entries are appended
**Then** they go to `spend/ledger.jsonl` under a file lock, outside `.cache/`
**And** two concurrent writers leave every entry intact, one per line

**Given** a ledger file with settled entries
**When** the process restarts and a new `SpendLedger` opens the same `spend/ledger.jsonl`
**Then** the running total equals the total before the restart, and the cap is enforced against it

**Given** the local disk `Cache` under `.cache/`
**When** a response is put and the process restarts
**Then** a `get` for the same key returns the same response

**Given** a populated `.cache/`, `spend/ledger.jsonl` and `spend/exports/`
**When** `.cache/` is deleted
**Then** `spend/ledger.jsonl`, `spend/exports/` and the running total are unchanged, and a repeated call misses the cache and is priced again

**Given** the repository ignore files
**When** the offline ignore-file test runs
**Then** `spend/ledger.jsonl` and `.cache/` are git-ignored

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.6: Ledger export and reset script

As a builder,
I want a dated Ledger export and a reset that refuses to run without that day's export,
So that the committed exports are the durable record of spend and the Nov 5 reset can never erase a day nobody exported.

_Covers FR-29, NFR-6, AR-9. Owner: scripts. Depends on: 2.5. Tier 1, Tue Oct 27; the daily export is committed with each day's work from the day 2.6 lands (a dated builder item in the 2.9 checklist; the Mon Oct 26 export is logged as a gap for bmad-correct-course unless 2.2, 2.3, 2.5 and 2.6 are pulled into Mon Oct 26). `scripts/ledger.py export` writes `spend/exports/ledger-<date>.json` from the local ledger (the export is one function in `src/infra/local.py` that `scripts/ledger.py export` wraps and that API wiring calls in 2.12); reset refuses unless today's export exists; a script hitting the cap exits non-zero printing the cap and the running total; `spend/exports/` is not ignored; the hosted snapshot merge joins in 7.9._

**Acceptance Criteria:**

**Given** `spend/ledger.jsonl` with entries
**When** `scripts/ledger.py export` runs
**Then** it writes `spend/exports/ledger-<date>.json` holding every entry and the running total
**And** the export is one function in `src/infra/local.py` that `scripts/ledger.py export` wraps and that API wiring calls in 2.12, and with an empty ledger (a mock-only day) it still writes a valid export with a total of 0

**Given** that today's `spend/exports/ledger-<date>.json` does not exist
**When** `scripts/ledger.py reset` runs
**Then** it refuses, exits non-zero, and leaves `spend/ledger.jsonl` and the running total unchanged
**And** once today's export exists, the reset proceeds, the running total reads 0 afterwards, and the export file is untouched

**Given** a script whose guarded call raises `SpendCapExceeded`
**When** the script handles it
**Then** it exits non-zero and prints the cap and the running total

**Given** the repository ignore files
**When** the offline ignore-file test runs
**Then** `spend/exports/` is not ignored and `spend/ledger.jsonl` is

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.7: Meta Model API adapter for chat, segment and image

As a builder,
I want the `meta` adapter to serve `chat`, `segment` and `generate_image` against the Meta Model API through the cache and the ledger,
So that the Architect, segmentation, the Riddler, the Dry run and the portraits make real calls that are priced, safe to retry and within the rate limits.

_Covers FR-2, FR-3, FR-23, FR-36, AR-8, AR-17, AR-27, NFR-4, NFR-7, NFR-9, AD-5, AD-13. Owner: providers. Depends on: 2.1, 2.3, 2.4. Tier 1; gate: the verified calls go into `meta_api.py` from Mon Oct 26 only if the pre-kickoff verifications passed (else Tue Oct 27 and later work slips a day); no live call is made before 2.3 and 2.4 land (Tue Oct 27). Chat Completions for muse-spark-1.3 (images as data URLs of the stored downscaled bytes, `response_format` `json_schema` with strict false or `strict_schema`, explicit `reasoning_effort`, never none), Responses for sam-3.1 (one noun phrase, meta-sam-parser SVG path to frame-pixel polygons, no mask -> None), muse-image-1.0 at $0.01; standard tier only, never contributor; one retry with backoff inside one ledger entry on 429, 500 and 503 only (never 502, 504, an undocumented 5xx or a muse-image-1.0 500), connect errors once, read timeouts never, Retry-After honored or `ProviderError` when it passes the stage's budget; priced from usage at budgets.md rates; within the Meta rate limits; tests on recorded fixtures only. Dev skills: keyframe-muse, keyframe-sam31._

**Acceptance Criteria:**

**Given** a recorded `muse-spark-1.3` fixture
**When** `chat` is called with images and a `response_schema`
**Then** the request goes to Chat Completions, with each image sent as a base64 data URL of the stored downscaled bytes and `response_format` set to `json_schema`, using either `strict: false` or the output of `strict_schema`
**And** `reasoning_effort` is always sent explicitly, `none` is refused before sending, every request uses the standard tier, no code path selects the contributor tier, and the key comes from `META_MODEL_API_KEY` through `Settings`

**Given** a recorded `sam-3.1` fixture
**When** `segment(label, image)` is called
**Then** one Responses request carries exactly one noun phrase, and the returned mask's SVG path (M/L/Z) is decoded with `meta-sam-parser` 0.1.0 into polygons `[[x, y], ...]` scaled from the mask raster to the frame's pixels
**And** a response with no mask returns `None`

**Given** a recorded `muse-image-1.0` fixture
**When** `generate_image(prompt)` is called
**Then** an `ImageResponse` is returned and priced at $0.01

**Given** a call that first receives 429, 500 or 503, or a `ConnectError` or `ConnectTimeout`, and then succeeds
**When** the adapter handles it
**Then** it retries exactly once with backoff, returns the success, and the ledger holds one entry for the call
**And** a second failure raises `ProviderError`, while 502, 504, an undocumented 5xx, a `muse-image-1.0` 500, a 400 or a read timeout raises `ProviderError` with no retry

**Given** a 429 carrying `Retry-After`
**When** the wait fits the stage's remaining budget
**Then** the one retry waits as long as `Retry-After` says
**And** when the wait exceeds that budget, the call fails at once with `ProviderError`

**Given** any `meta` call
**When** it runs
**Then** it goes through the cache, and then through the ledger guard on a miss, and its observed cost comes from the returned usage at the `budgets.md` rates
**And** the adapter's model ids and declared limits match `budgets.md` (`muse-spark-1.3` 3,000 RPM and 4,000,000 TPM, `sam-3.1` 3,000 RPM, `muse-image-1.0` 150 RPM), and a 429 is handled only by the one retry

**Given** the story's changes
**When** `pytest` runs offline against the mock provider, with the adapter tests on recorded fixtures only
**Then** it passes with new tests covering this story's criteria, and no test opens a network connection

### Story 2.8: OpenAI-compatible adapter for the Riddler fallback

As a builder,
I want an OpenAI-compatible adapter that can serve the Riddler from Baseten or Fireworks,
So that authoring keeps working if the Meta path fails, without changing any other role or leaking anything a fallback host must not see.

_Covers AR-8, AR-17, NFR-4, AD-5. Owner: providers. Depends on: 2.1, 2.3, 2.4. Tier 1, Tue Oct 27. `OPENAI_COMPATIBLE_BASE_URL` selects Baseten or Fireworks; cache and ledger guarded; the same documented retry set; plain-JSON mode lets parse failures fall to the regeneration loop with no adapter retry loop; a prompt reaches it only when that role's fallback is active and never carries a solution or Player profile field; the role switch (`PROVIDER_RIDDLER=openai_compatible`) is wired in 2.12; the Trickster fallback reuses it in 4.8; the one-call Baseten test is a dated builder item in the 2.9 checklist. Dev skill: keyframe-muse._

**Acceptance Criteria:**

**Given** `src/providers/openai_compatible.py` configured by `OPENAI_COMPATIBLE_BASE_URL` and `OPENAI_COMPATIBLE_API_KEY` from `Settings`
**When** `chat` is called against recorded fixtures
**Then** it returns a `ChatResponse` through the cache and the ledger guard, priced from the returned usage
**And** it never sends `reasoning_effort` `none`

**Given** a fixture that returns 429, 500 or 503, or a connect error, once and then succeeds
**When** the adapter handles it
**Then** it retries exactly once with backoff inside one ledger entry
**And** 502, 504, any other 5xx and a read timeout raise `ProviderError` with no retry

**Given** a host whose recorded fixture honors `response_format` `json_schema`
**When** a `RoomDraft` schema passed through `strict_schema` is sent
**Then** the constrained response parses exactly as it does on the `meta` path

**Given** a host that does not honor `json_schema`
**When** the adapter runs in plain-JSON mode
**Then** the prompt asks for JSON, a response that fails to parse goes back to the caller as a parse failure, and the regeneration loop counts it as a failed attempt
**And** the adapter makes no request beyond the one documented retry and adds no retry loop of its own

**Given** a Room fixture with sentinel solutions, whose sentinel solutions name ids and a code string that appear nowhere else in the fixture (not among its Interactables), and a sentinel `Derived` block
**When** a messages list the test renders from that Room's `RoomView` (interactables only) is sent through this adapter in both `json_schema` and plain-JSON mode
**Then** the request body carries only the messages it was given, with no sentinel solution (the code string, the order id list in sequence, the `use_on` pair, the `find` target id), no `derived` key and no Player profile field

**Given** the story's changes
**When** `pytest` runs offline against the mock provider, with the adapter tests on recorded fixtures only
**Then** it passes with new tests covering this story's criteria

### Story 2.9: Lean SIT: the checklist and scripts/sit.py over the live seams

As a builder,
I want a checklist plus `scripts/sit.py` that run the live seams at the end of each build day and record their responses as fixtures,
So that a broken vendor call is caught the day it breaks, while the offline suite keeps replaying what the real services returned.

_Covers AR-25, NFR-8, NFR-6. Owner: scripts. Depends on: 2.5, 2.6, 2.7, 2.8. Tier 1; runs at the end of each build day from Tue Oct 27 with a full pass Sat Oct 31; no separate sign-off. A checklist plus `scripts/sit.py` running about 10 live-seam cases within the Spend cap (Architect chat with photos, sam-3.1 segment, muse-image-1.0, Baseten or Fireworks chat, a cache hit unbilled, a cap refusal) and recording their responses as fixtures under `tests/fixtures` for the offline suite; cases live as modules under `tests/sit/` that `sit.py` discovers, so a later story adds its case as a test file, keeping AD-17's one package plus tests (Riddler 2.20, Dry run and a full live Build 2.24, Ollama 3.7, live Trickster 4.8); exits non-zero on a failed case; the checklist also carries the dated builder items no dev agent can run offline: the one-call Baseten test (`json_schema` support and chosen mode, Tue Oct 27), the Fireworks Trickster model id (Mon Oct 26, the 4.8 gate), the M1 Ollama benchmark (latency, about 3 GB resident) once 3.7 lands and each build day's committed Ledger export from the day 2.6 lands; results dated in the sprint status; the checklist is `docs/implementation-artifacts/sit-checklist.md`, and each day's results are recorded in its run log alongside the sprint status. Dev skills: keyframe-muse, keyframe-sam31._

**Acceptance Criteria:**

**Given** case modules under `tests/sit/`
**When** `scripts/sit.py` runs
**Then** it discovers and runs every case, printing pass or fail per case, and records each live response as a fixture under `tests/fixtures`
**And** every live call goes through the real cache and `SpendLedger`, so the run stays within `SPEND_CAP_USD`
**And** a recorded fixture holds the response only (no request body, image bytes or `data:` URL); the SIT reads its input photos from the git-ignored `photos/` folder, never from `tests/`; and an offline `pytest` scan fails if any file under `tests/fixtures` contains `data:image` or JPEG magic bytes

**Given** the initial cases
**When** the cases are listed
**Then** they cover an Architect `chat` call with photos, a `sam-3.1` segment, a `muse-image-1.0` image, a Baseten or Fireworks `chat` call, a repeated identical call served from the cache with the running total unchanged, and a cap refusal in which the provider is never called

**Given** any failed case
**When** `scripts/sit.py` finishes
**Then** it exits non-zero, naming the failed cases

**Given** a later story that adds a module under `tests/sit/` (Riddler 2.20, Dry run and full live Build 2.24, Ollama 3.7, live Trickster 4.8)
**When** `scripts/sit.py` runs next
**Then** it picks the new case up without any change to `scripts/sit.py`
**And** the offline `pytest` run never executes a `tests/sit/` case

**Given** the SIT checklist
**When** it is read
**Then** it carries the dated builder items: the one-call Baseten test (`json_schema` support and the chosen mode, Tue Oct 27), the Fireworks Trickster model id (Mon Oct 26, the 4.8 gate), the M1 Ollama benchmark (latency, about 3 GB resident) once 3.7 lands, and, each build day from the day 2.6 lands, that day's `spend/exports/ledger-<date>.json` is in the day's commit, dated in the sprint status

**Given** each build day from Tue Oct 27, and Sat Oct 31
**When** the day ends
**Then** the sprint status shows a dated SIT result for that day, the full pass on Sat Oct 31, and the dated outcome of each checklist item, with no separate sign-off

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria (case discovery and the non-zero exit, exercised offline with a fake case module)

### Story 2.10: Persisted build job and the ingest stage

As a builder,
I want the Build to run as a persisted, resumable stage job whose first stage ingests the photos exactly as uploaded,
So that a Build outlives any single request and every later model call, cache key and mask uses the same bytes.

_Covers FR-1, FR-5, FR-28, FR-30, AR-10, AR-17, AR-20, AR-22, AR-31, NFR-7, AD-7, AD-13, AD-16. Owner: pipeline (declares `JobStore` and `JobRunner` in `src/pipeline/ports.py` first). Depends on: 1.5, 1.10, 2.1, 2.3. Tier 1, Tue Oct 27. Declares `JobStore` and `JobRunner`; fills the job state model 1.5 declared (per-stage timings, done-row counts and model id, per-attempt sent-back messages, call rows, build time); stages run in order and persist after each with build-clock timings; a restarted runner resumes at the last persisted stage; ingest stores downscale and original byte for byte, hash = sha256 of the downscale, rejects counts outside 6 to 10 (422 `photo_count`), non-JPEG by bytes (`UnsupportedImage`, code `unsupported_image`) and a downscale whose long edge is not 1280 or orientation not 1 (422 `bad_downscale`), the codes settled in spine AD-7 and AD-13 on Oct 21; a typed error ends the job failed with its stage and code (`spend_cap_exceeded` for `SpendCapExceeded`); one JSON log line per stage with `job_id`, stage, `duration_ms` and `spend_usd` (AR-22); `DEMO_TIMESCALE` never scales timings._

**Acceptance Criteria:**

**Given** that the story first declares `JobStore` and `JobRunner` in `src/pipeline/ports.py`, and that `src/pipeline/build.py` runs a job whose stages after ingest are test doubles
**When** the job runs
**Then** the stages run in the order `ingest → architect → segment → author → validate → dryrun → scene`, and job state and stage artifacts are persisted through `JobStore` and `ArtifactStore` after each stage, with that stage's timing taken from the build clock
**And** job state carries per-stage timings, done-row counts and model ids, per-attempt sent-back messages, call rows (role, model id, host, cached or billed, spend) and the build time, and `DEMO_TIMESCALE=6` leaves every timing unchanged

**Given** a job persisted after the architect stage, and a runner that then dies
**When** a new runner starts the same `job_id`
**Then** it rereads job state from `JobStore` on entry and resumes at segment, and the architect call is not made again

**Given** 6 to 10 photos, each a JPEG downscale with a 1280 px long edge plus its JPEG original
**When** ingest runs
**Then** both files are stored byte for byte under `rooms/`, neither is re-encoded, and `photos[i].hash` is the sha256 of the stored downscale, in upload order
**And** `rooms/` is git-ignored, so no raw room photo can be committed

**Given** fewer than 6 or more than 10 photos, a file that is HEIC, PNG or any other non-JPEG format (detected from the bytes, not the file name), or a downscale whose long edge is not 1280 px or whose EXIF orientation tag is present and not 1
**When** ingest validates the upload
**Then** a non-JPEG file raises `UnsupportedImage` (code `unsupported_image`), a bad downscale is refused with 422 `bad_downscale`, and a wrong count is refused with 422 `photo_count` (spine AD-7, AD-13), each in the AD-13 error envelope
**And** nothing is stored and no model call is made
**And** when `POST /builds` receives an upload, the API calls ingest's validation function from `src/pipeline` (count, JPEG by bytes, 1280 px long edge, orientation) before any job exists, so a refusal creates and queues no job, and the ingest stage only stores the bytes of an accepted upload

**Given** a job moving through the runner
**When** its status is read
**Then** it is `queued` before the runner starts, `running` with `stage` set to the stage in progress, and `done` after scene; only segment sets `needs_more_photos`, and only the regeneration loop sets `needs_recapture`
**And** a typed error raised by a stage ends the job `failed`, recording the stage and the snake_case code (`spend_cap_exceeded` for `SpendCapExceeded`, `provider_error` for `ProviderError`)

**Given** any stage that finishes
**When** its log is read
**Then** exactly one JSON log line exists for that stage, carrying `job_id`, `stage`, `duration_ms` and `spend_usd`

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria, and `tests/test_boundaries.py` confirms that `src/pipeline` imports only the domain and ports

### Story 2.11: Local JobStore and in-process JobRunner

As a builder,
I want local adapters for the job ports that keep all job state on disk,
So that a Build in Local mode runs without blocking a request and picks up where it stopped after a restart.

_Covers FR-5, AR-10, AR-12, AD-7, AD-9. Owner: infra. Depends on: 2.10. Tier 1, Tue Oct 27. The local JSON `JobStore` and the in-process `JobRunner` in `src/infra/local.py`; state read only from the store, the same after a restart; a job left running resumes at its next stage after a restart._

**Acceptance Criteria:**

**Given** the local JSON `JobStore` in `src/infra/local.py`
**When** job state is written and then read back through a second `JobStore` instance
**Then** the second instance returns identical state, because state lives only in the store and never in a process variable

**Given** the in-process `JobRunner`
**When** `start(job_id)` is called while a test holds a stage open
**Then** `start` returns before that stage completes, and the stage runs in the background

**Given** a job whose last persisted stage is architect, left `running` when the process stopped
**When** the process restarts and `start(job_id)` is called
**Then** it resumes at segment, the architect stage does not run again, and the state read before `start` equals the state persisted before the stop

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.12: Build routes, per-role provider wiring and the ledger hooks

As a builder,
I want the build routes, one provider per council role and the Ledger export hooks wired in the API,
So that a browser can submit photos, poll a Build without blocking and fetch the finished room, while spend is exported at the right moments.

_Covers FR-1, FR-5, FR-29, AR-8, AR-10, AR-13, NFR-7, AD-5, AD-7, AD-9. Owner: api. Depends on: 1.11, 2.6, 2.7, 2.8, 2.11. Tier 1, Tue Oct 27. `wiring.py` resolves one provider per role and `PROVIDER_<ROLE>` replaces only that role (`MODEL_PROVIDER` as the default); multipart `POST /builds` returns a `job_id` without blocking on a stage; ingest refusals answer 422 with the envelope (stage ingest; `photo_count`, `unsupported_image` or `bad_downscale`) and queue no job; `GET /builds/<job_id>` reads persisted state only, 202 while queued or running and 200 when terminal, never a solution, the same after a restart; `GET /builds/<job_id>/room` returns the full Room with no access code locally; the 2.6 ledger export runs at API startup and after every completed Build._

**Acceptance Criteria:**

**Given** `Settings` with `MODEL_PROVIDER` and no `PROVIDER_<ROLE>` set
**When** `wiring.py` resolves providers
**Then** each of `architect`, `riddler`, `dryrun`, `trickster` and `image` gets its own provider of the default kind (five mocks under `MODEL_PROVIDER=mock`)
**And** `PROVIDER_RIDDLER=openai_compatible` switches only the `riddler` role to the OpenAI-compatible adapter, and every other role keeps its provider

**Given** a multipart `POST /builds` holding a downscale and an original for each of 6 to 10 photos
**When** the request is handled while a test holds a stage open
**Then** it returns a `job_id` while the job is `queued` or `running`, so no request blocks on a stage

**Given** an upload that ingest refuses (wrong count, non-JPEG bytes, or a downscale that fails the 1280 px or orientation check)
**When** `POST /builds` responds
**Then** the status is 422 with the envelope `{error: {code, message, stage}}`, `stage` is `ingest`, a non-JPEG file has the code `unsupported_image`, and no job is queued
**And** a wrong count has the code `photo_count` and a downscale failing the 1280 px or orientation check has the code `bad_downscale` (spine AD-7, AD-13)

**Given** a job in any state
**When** `GET /builds/<job_id>` is called, including after an API restart
**Then** it reads only persisted state and answers 202 while `queued` or `running` and 200 when terminal, with the status, the stage, the mask preview once segment has completed, and the room id once `done`
**And** an API sentinel test finds no Room and no `solution` key in any job-state response
**And** once the job is `done` in Local mode, `GET /builds/<job_id>/room` with no access code returns the full Room, and `GET /rooms/<room_id>` for the same room returns a `PlayView` with no `solution` key

**Given** a job persisted as `queued` or `running` when the API process stopped
**When** the API starts again
**Then** wiring calls `JobRunner.start(job_id)` for every such job, each resumes at the stage after its last persisted stage without repeating a finished stage's model call, and `GET /builds/<job_id>` later reads a terminal status

**Given** API startup, or a Build that reaches any terminal status
**When** the event happens
**Then** the 2.6 export function runs, and `spend/exports/ledger-<date>.json` includes that Build's entries

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.13: Mask selection and box conversion as pure domain functions

As a builder,
I want mask selection and box conversion to be pure domain functions,
So that Interactables and their Hotspots are deterministic and testable without a model.

_Covers FR-3, AR-15, AR-21, AD-18. Owner: domain. Depends on: 1.5. Tier 1, Tue Oct 27. Spark 0 to 1000 boxes to frame pixels, clamped; the best-IoU mask kept; masks with IoU above 0.2 grouped as instances of a plural label; masks under 1% of the image dropped; above 12 candidates the 12 with the highest Architect confidence kept; no mask -> the box rectangle as the single polygon, usable as a find, order or use_on target; simplification never adds vertices and keeps at least 3 inside the frame; no ids minted here. Dev skill: keyframe-sam31._

**Acceptance Criteria:**

**Given** a Spark box on the 0 to 1000 grid and a frame of known pixel size
**When** it is converted
**Then** it becomes `[x0, y0, x1, y1]` in the frame's pixels, with any coordinate outside the frame clamped to the frame

**Given** several candidate masks for a label, where each candidate states whether its label is plural, through the `plural` field 1.5 declared on `ArchitectResponse`
**When** `src/domain/masks.py` selects among them
**Then** a singular label keeps the mask with the best IoU against the Architect's box as its single polygon
**And** a plural label groups every mask with IoU above 0.2 as instances of one Interactable, with `instances` set to the group's size and one polygon per instance

**Given** masks covering less than 1% of the image area
**When** selection runs
**Then** they are dropped

**Given** more than 12 surviving candidates
**When** the cap is applied
**Then** the 12 with the highest Architect confidence are kept

**Given** a label for which SAM returned `None` or no polygons
**When** selection runs
**Then** the converted box rectangle becomes the single polygon, in the same pixel space and shape as a mask polygon, with no flag marking where it came from, so it can serve as a `find`, `order` or `use_on` target
**And** simplification never adds vertices, keeps at least 3, and keeps every vertex inside the frame

**Given** the selection result
**When** it is returned
**Then** it carries no `id` field and uses no id or label from a model response as an identifier, and the module imports only the standard library and pydantic

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.14: Architect prompt builder

As a builder,
I want one pure Architect prompt builder over the stored photos,
So that the vision call is reproducible, cacheable and has nothing to leak.

_Covers FR-2, AR-21, AD-5. Owner: council. Depends on: 1.5, 2.1. Tier 1, Tue Oct 27. `council/architect.py` builds one pure prompt over all stored photos (bytes, in upload order) with the `ArchitectResponse` schema (no ids; correlated by list position), reasoning low, instructing attributes as read verbatim and a confidence per candidate; byte-stable fixed prefix (hash test); no room, Clue or profile field exists to leak. Dev skill: keyframe-muse._

**Acceptance Criteria:**

**Given** the stored downscaled photos of a Build
**When** `council/architect.py` builds the prompt
**Then** it is one request carrying every photo as bytes in upload order, with `reasoning_effort='low'` and the `ArchitectResponse` schema
**And** the instructions ask, for each object, for a label, whether the label names several like objects (plural), the clearest photo index, a box on the 0 to 1000 grid, the attributes exactly as read, and a confidence

**Given** the `ArchitectResponse` schema
**When** it is inspected and passed through `strict_schema`
**Then** it has no `id` field and no map-typed field, candidates are correlated by list position, and `strict_schema` accepts it

**Given** two different photo sets
**When** the prompt is built for each
**Then** the fixed prefix (system message and instructions) is byte-identical between them, and a hash test pins it

**Given** the builder's signature
**When** it is inspected
**Then** it accepts photos only (no `Room`, `RoomView` or `Derived` parameter), so the rendered prompt has no room, Clue or profile field to leak, and the same input always renders the same prompt

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.15: Architect and segment stages with the Mask preview

As a builder,
I want the architect and segment stages to turn the stored photos into Interactables with polygon Hotspots and a solution-free Mask preview,
So that a Build either has 5 to 12 objects to author from, or stops and asks for more photos before any authoring spend.

_Covers FR-2, FR-3, FR-4, AR-10, AR-21, NFR-1, NFR-9, AD-18. Owner: pipeline. Depends on: 2.7, 2.10, 2.13, 2.14. Tier 1, Tue Oct 27. One Architect chat call over the 2.14 prompt, attributes stored verbatim; one segment call per label on its clearest photo, at most 12 in flight; a segment call still erroring after its one retry ends the Build failed at segment (A-24); 4 or fewer survivors end `needs_more_photos` (`TooFewInteractables`) with zero Riddler, Dry run or Trickster calls, 5 continues; `ix_` ids minted after selection and the 12 cap; the solution-free mask preview (id, label, photo, polygons) persisted into job state; stage budgets (Architect 15 s, segmentation 10 s) measured, never enforced. Dev skills: keyframe-muse, keyframe-sam31._

**Acceptance Criteria:**

**Given** a job past ingest
**When** the architect stage runs
**Then** it makes one `chat` call through the `architect` role over the 2.14 prompt and records one call row
**And** each listed object's clearest photo index, box and attributes are kept by list position, with the attributes stored verbatim

**Given** an `ArchitectResponse` with more than 12 labels
**When** the segment stage runs
**Then** one `segment` call per label is issued on that label's clearest photo through a bounded thread pool, with never more than 12 calls in flight (counted by the test), and the results go through `domain/masks.py`

**Given** a `segment` call that still raises `ProviderError` after the adapter's one retry
**When** the segment stage handles it
**Then** the Build ends `failed` at the segment stage with code `provider_error`, and no author call is made

**Given** 4 or fewer Interactables surviving selection
**When** the segment stage ends
**Then** the job ends `needs_more_photos` (`TooFewInteractables`) with zero Riddler, Dry run or Trickster calls
**And** with exactly 5 survivors the job continues to author

**Given** the survivors after selection and the 12 cap
**When** segment persists them
**Then** each gets an `ix_` id minted by this stage (none for dropped candidates), a box in frame pixels and non-null `polygons`
**And** job state gains the Mask preview (`id`, `label`, `photo`, `polygons` per Interactable, with no puzzle or solution field), the object count, and the model ids `muse-spark-1.3` and `sam-3.1`

**Given** a job that completes both stages
**When** its timings are read
**Then** the architect and segment durations in milliseconds from the build clock are recorded in job state, and a stage double that runs past the 15 s or 10 s budget still completes without failing

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.16: Capture screen: choose and upload photos, with the Retention summary

As a player,
I want to read where my photos go, choose 6 to 10 JPEG photos and upload them in one step,
So that I know what I am sending, and a bad set is stopped before anything leaves my browser.

_Covers FR-1, FR-6, NFR-4, UX-DR14, UX-DR15, UX-DR20, UX-DR21, UX-DR62, UX-DR75, UX-DR82, AR-10. Owner: web. Depends on: 1.14, 1.17, 1.18, 2.12. Tier 1, Tue Oct 27. `#/` in Local mode, right column in order: the Input requirement '6 to 10 JPEG photos', the iPhone Most Compatible tip, the faces, documents and belongings reminder, then the Retention summary tray exactly as `GET /meta` serves it with the Privacy line verbatim, all visible before any photo is chosen; dropzone (drag or 'Choose photos') and the 120 x 90 photo tray with 'Remove photo {n}' and re-validation; a non-JPEG checked by bytes or a count outside 6 to 10 rejects the whole set with 'Keyframe needs 6 to 10 JPEG photos.', offending files marked 'Not a JPEG', nothing uploaded; Upload makes Canvas downscales (EXIF orientation applied, 1280 px long edge, quality 0.85) and posts one multipart `POST /builds` with the originals; 422 and upload-failed banners (the 1.17 component) keep the photos; the client calls only its own server; the stored Rooms list stays below; everything but the Retention summary and banners disabled during a Build._

**Acceptance Criteria:**

**Given** a cold load of `#/` in Local mode (mockups/capture-screen.html)
**When** `GET /meta` answers
**Then** the right column shows, in order, "6 to 10 JPEG photos" standing alone, "On iPhone, set Settings > Camera > Formats to Most Compatible so photos save as JPEG.", "Leave out faces, documents and other people's belongings.", and the `retention-summary` tray: "Where your photos go.", the `retention` text exactly as served, "Your play history" and "the player profile stays on your machine." verbatim, never collapsed or truncated, all before any photo is chosen
**And** the left area shows the `capture-dropzone` with the stored Rooms list below it, and while `GET /meta` fails the screen shows "Keyframe can't reach its server. Retrying." and retries every 2000 ms

**Given** the dropzone with "Choose 6 to 10 JPEG photos of one room." and "Choose photos"
**When** the player drops files or picks them
**Then** the photo tray shows `photo-tray-thumb` thumbnails at 120 x 90 in upload order with "{n} photos chosen" and a "Remove photo {n}" control on each
**And** each removal or addition re-validates the set, and a valid set clears the banner and enables Upload

**Given** a set holding any file whose bytes are not JPEG (including a HEIC renamed `.jpg`), or fewer than 6 or more than 10 files
**When** the set is validated
**Then** the whole set is rejected with the error banner heading "Keyframe needs 6 to 10 JPEG photos." (no body sentence) and "Choose photos again", each offending file shows a 2 px `wrong` border and "Not a JPEG" and stays removable, and no request is sent

**Given** a valid set
**When** the player clicks Upload
**Then** each photo is downscaled in a Canvas with EXIF orientation applied, to a 1280 px long edge at quality 0.85, and every downscale goes with its original in one multipart `POST /builds`
**And** while the upload is pending, Upload shows its pending label and the dropzone is disabled
**And** a network log during the upload shows requests only to the app's own origin under `/api/`, and to no other host

**Given** an upload refused with a 422, or one that fails for any other reason
**When** the response arrives
**Then** `unsupported_image` or `photo_count` shows the FR-1 banner, `bad_downscale` shows "Keyframe couldn't read these photos. Choose them again.", and a network error or 5xx shows "Your photos didn't reach Keyframe." with "Nothing was built. Check the connection and try again." and "Try again", which re-sends the same set
**And** the photos stay in the tray, banners use the `error-banner` (the 1.17 component; one at a time, a newer state replacing an older one), and during a Build everything except the Retention summary and banners is disabled

**Given** the before-upload layout
**When** it is checked against the accessibility floor
**Then** initial focus is on "Choose photos", each remove control, Upload and banner action is reachable by Tab with a visible focus ring and activated by Enter, a new banner takes focus, and text meets WCAG AA contrast on the dark theme

**Given** the story's changes
**When** the web build, the type check and `pytest` run offline against the mock provider
**Then** all pass with new tests covering this story's criteria

### Story 2.17: Capture Timer from Upload to the first Hotspot response

As a player,
I want a Timer that runs from my Upload click until the room first responds to my pointer,
So that I can see exactly how long my photos took to become a playable room.

_Covers FR-5, UX-DR17, AR-14, NFR-1. Owner: web. Depends on: 1.19, 2.16. Tier 1, Wed Oct 28. The top-bar Timer starts on the Upload click (T0) reading 'Photos to play', runs in real time at any Demo timescale, keeps counting while reconnecting, resumes from the recorded start after a reload, stops at the first Hotspot pointer response (T1, the 1.19 signal; keyboard focus does not stop it) and shows 'Playable in' with T1 - T0; on an end state it stops and shows the status (2.25)._

**Acceptance Criteria:**

**Given** the Capture screen with a valid set (mockups/capture-screen.html)
**When** the player clicks Upload (T0)
**Then** the top-bar `timer` reads "Photos to play", followed by `mono-timer` m:ss digits in `text` and a static 6 px lamp dot, counting in real time

**Given** `GET /meta` reporting `demo_timescale` 6
**When** the Build runs
**Then** the Timer still counts in real time, unscaled

**Given** a Build in progress
**When** two polls are missed, or the player reloads `#/build/<job_id>`
**Then** the Timer keeps counting from T0 while reconnecting, and after a reload it resumes from the Build's recorded start rather than from zero

**Given** the Play screen opened from the Build
**When** the first Hotspot responds to the pointer (the 1.19 signal)
**Then** the Timer stops and reads "Playable in" with the T1 − T0 digits in `success` and no dot, staying frozen for the rest of the Session
**And** keyboard focus on a Hotspot does not stop it, and the Timer is hidden when a stored Room is replayed through "Play"

**Given** an upload that fails, or a Build that reaches an end state
**When** the Timer handles it
**Then** it freezes its digits and shows the status in `text-muted`, and after an upload failure the next Upload starts a new T0

**Given** the Timer
**When** it is checked against the accessibility floor
**Then** its label and digits are text a screen reader reads together, the label always says what the digits measure, and both meet WCAG AA contrast on the dark theme

**Given** the story's changes
**When** the web build, the type check and `pytest` run offline against the mock provider
**Then** all pass with new tests covering this story's criteria

### Story 2.18: Capture progress: Stage list, Regeneration rows, Mask preview and build routing

As a player,
I want to watch each Build stage, any Regeneration and my outlined objects appear while my room builds,
So that I can see what Keyframe is doing with my photos and land in my room as soon as it is ready.

_Covers FR-5, UX-DR15, UX-DR16, UX-DR18, UX-DR62, UX-DR63, UX-DR74, UX-DR8, AR-31. Owner: web. Depends on: 2.15, 2.16, 2.17. Tier 1, Wed Oct 28. `#/build/<job_id>` polls `GET /builds/<job_id>` every 2000 ms; the photo tray turns compact (96 x 72) during a Build; Stage list with the Architect introduction, the five stage rows (pending, running with the Architect's stage line, done with result, done-row count and model id, failed), the Riddler introduction inside 'Writing puzzles', Regeneration rows 'Rewriting puzzles, attempt n of {max}' with 'Sent back: {fixed messages}' read from job state; Mask preview tiles fade in once segment completes (label chips, not interactive); done goes to Play automatically, and a reload of a done Build shows 'Play this room'; a 260 s Build still arrives by polling._

**Acceptance Criteria:**

**Given** an upload accepted with a `job_id` (mockups/capture-screen.html)
**When** `#/build/<job_id>` opens
**Then** it polls `GET /builds/<job_id>` every 2000 ms, the Stage list replaces the dropzone, and the photo tray turns compact, as `photo-tray-thumb` at 96 x 72, and `?profile=` is carried on `#/build/<job_id>`
**And** the Architect's introduction row sits at the top from Upload (48 px portrait, "The Architect", "Reads your photos with muse-spark-1.3, names the objects, and draws their outlines with sam-3.1.", "I notice everything. Mostly mugs.")

**Given** job status with a `stage`
**When** the Stage list renders
**Then** "Reading your photos" (ingest), "Finding objects" (architect, segment), "Writing puzzles" (author), "Testing the room" (validate, dry run) and "Setting the scene" (scene) each show, as `stage-list-item` rows, pending (hollow, `text-muted`), running (filled `lamp`, with the Architect's stage line for that stage under its name), done (`success`, with its `mono-sm` duration, its result and model id from job state, such as "9 objects" with muse-spark-1.3 · sam-3.1, and "Rules: 8 of 8 passed" with "Test run: reached 5 of 5 answers") or failed (`error-text`)
**And** the Architect's line under each running stage is, in order, "{n} photos of one room. Let me find my loupe.", the Mask preview line, "I've handed my notes to the Riddler. Brace yourself.", "Now we make sure every lock can actually be opened. Fair is fair.", "Hanging your room on the wall. Mind the frame." and, on a Regeneration, "The Riddler's draft didn't pass. Another go.", moving to each new running row with a 200 ms fade

**Given** the author stage starting, and later a rising attempt count
**When** the Stage list updates
**Then** the Riddler's introduction ("Reads the objects; writes the puzzles with muse-spark-1.3, then a test run that never sees the answers checks each one can be solved." and "I taught your things to talk. Pity they only speak in riddles.") fades in inside "Writing puzzles" and stays
**And** each Regeneration adds "Rewriting puzzles, attempt n of {max}" ({max} = `REGEN_MAX`, 1 under cut 7) with "Sent back: {fixed messages}" read from job state, and the author, validate and dry run rows run again

**Given** job status that carries the Mask preview after segment
**When** the Mask preview renders
**Then** the tiles show each Interactable's clearest photo with its outline in `build-view-mask` style and its label on a parchment chip in `label` type, fading in together over 200 ms, with no heading and no interaction
**And** the running "Finding objects" row reads "I see {n} things worth a closer look, starting with the {label 1}, the {label 2} and the {label 3}." (or the two-label form)

**Given** a Build that reaches `done`, including one that took 260 s with two Regenerations (stage doubles)
**When** the poll reads `done`
**Then** every stage shows done, a Session starts and the Play screen opens automatically
**And** reopening `#/build/<job_id>` on a Build that is already `done` shows "Play this room" (primary) instead of starting a Session
**And** when that `POST /sessions` fails, the error banner reads "Keyframe couldn't start this room." with "Your room is safe. Try again." and "Try again", which re-posts the session start; the banner takes focus and the Timer keeps running toward T1

**Given** the Stage list and the Mask preview
**When** they are checked against the accessibility floor
**Then** the Stage list is not a live region, each in-character line carries a visually hidden speaker prefix, the Mask preview tiles take no focus, the fades respect reduced-motion settings, and text meets WCAG AA contrast

**Given** the story's changes
**When** the web build, the type check and `pytest` run offline against the mock provider
**Then** all pass with new tests covering this story's criteria

### Story 2.19: Riddler prompt builder with the generated-line voice rules

As a builder,
I want the Riddler prompt built purely from the Interactables, with the voice rules and the response schema fixed in it,
So that every draft can be checked by the Validator, reads in character even when shown verbatim, and is written without any solution or profile in view.

_Covers FR-7, AR-6, NFR-5, UX-DR76, AD-3. Owner: council. Depends on: 1.6, 1.7, 2.1. Tier 1, Wed Oct 28. `council/riddler.py` builds the prompt from `RoomView` interactables only, reasoning medium, with the p1..p6 response schema (4 to 6 Puzzles, exactly one Exit; lock types code, order, `use_on`, find, only code and find under cut 6) and the voice rules (Clue and Lore in the Riddler voice, Lore at most 60 words, Rungs in the Guide voice on the nudge, direction, near-answer ladder so a verbatim Rung reads in character); the regeneration variant takes the fixed failure messages only, never the previous draft; sentinel prompt test: no solution, Derived key or profile field. Dev skill: keyframe-muse._

**Acceptance Criteria:**

**Given** a `RoomView`
**When** `council/riddler.py` builds the authoring prompt
**Then** it renders only the Interactables (`id`, `label`, `attributes`, `instances`, `photo`) with `reasoning_effort='medium'`
**And** the response schema uses ordinal keys `p1`..`p6` (`p1`..`p4` required, `p5` and `p6` optional) for Puzzles and their `requires`, each with `lock_type`, `is_exit`, `requires` (ordinal keys), `clue`, `lore`, `rungs` (`nudge`, `direction`, `near_answer`), `evidence` (`interactable` as an `ix_` id from the prompt, `visible_attribute` copied from that Interactable's attributes) and a `solution` in the tagged union by `lock_type` (`code` {`code`}, `order` {`interactables`}, `use_on` {`item`, `target`}, `find` {`target`}) naming `ix_` ids for every type except `code`, has no map-typed field, and the instructions call for exactly one Exit puzzle

**Given** the set of Lock types the builder is given
**When** the default set is used and when cut 6 passes only `code` and `find`
**Then** the schema's `lock_type` admits `code`, `order`, `use_on` and `find` by default and only `code` and `find` under cut 6

**Given** the prompt's fixed prefix
**When** it is inspected
**Then** it carries the generated-line rules: Clue and Lore in the Riddler voice, Lore at most 60 words, and Rungs in the Guide voice on the ladder (the nudge says where to look and is shortest, the direction says what to notice, the near-answer says how to use it in at most two sentences, lengths increase, never "the answer is"), with no solution token in any line

**Given** a reason list from a failed attempt and that attempt's draft
**When** the regeneration variant is built
**Then** it carries the reasons only (rule, Puzzle id, field, fixed message), and none of the previous draft's Clues, Rungs, Lore or solutions appears

**Given** a Room fixture with sentinel solutions, whose sentinel solutions name ids and a code string that appear nowhere else in the fixture (not among its Interactables), and a sentinel `Derived` block
**When** the authoring and regeneration prompts are rendered
**Then** neither contains the code string, the order id list in sequence, the `use_on` pair, the `find` target id, any `derived` key or any Player profile field

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.20: Riddler authoring stage behind the Validator

As a builder,
I want the author stage to turn one Riddler call into a draft that the Validator judges before anything else happens,
So that no unvalidated Room is ever stored and every draft's fate is recorded.

_Covers FR-7, FR-8, FR-30, AR-16, AR-20, AR-21, NFR-1, NFR-5, AD-12, AD-16, AD-18. Owner: pipeline. Depends on: 2.9, 2.15, 2.19. Tier 1, Wed Oct 28. One chat call over the 2.19 prompt; p-keys mapped to `pz_` ULIDs and `ix_` references parsed by exact match before validate; output failing the schema or id parsing is a failed attempt with a fixed reason (A-24); `RoomDraft` persisted; validate runs on every draft; provenance with model ids, prompt hashes, timings, Regeneration count, spend per stage and empty applied edit ids; adds its live-seam case under `tests/sit/`. Dev skill: keyframe-muse._

**Acceptance Criteria:**

**Given** a job with Interactables
**When** the author stage runs
**Then** it makes one `chat` call through the `riddler` role over the 2.19 prompt with `attempt` set to the Regeneration count, persists the raw output as a `RoomDraft`, and records one call row

**Given** a Riddler response
**When** it is mapped
**Then** every `p1`..`p6` key, including those inside `requires`, becomes a `pz_` ULID before `validate` runs
**And** Interactable references are parsed back by exact `ix_` id match only, so a label, or an id that differs in any character, makes the attempt a failed attempt with the fixed id-parsing reason (A-24) before `validate` runs

**Given** output that fails the response schema or the exact-id parsing
**When** the author stage handles it
**Then** the attempt is recorded as failed with a fixed reason (A-24) and handed to the regeneration loop, and the Build does not end `failed`

**Given** a mapped draft
**When** `validate` runs, as it does on every draft
**Then** a failing draft yields structured `{rule, puzzle_id, field}` reasons with fixed messages that quote no solution token or answer, per-rule verdicts are recorded in job state, and no `room` artifact is written
**And** a draft with fewer than 4 or more than 6 Puzzles never passes

**Given** a draft that passes
**When** its provenance is assembled
**Then** it holds the model ids, the prompt hashes, the stage timings, the Regeneration count, spend per stage summed from that stage's ledger entries, and an empty `applied_edits`

**Given** `tests/sit/`
**When** the story lands
**Then** it adds a live Riddler case that `scripts/sit.py` runs, and its recorded fixture replays in the offline suite

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.21: Regeneration loop ending in needs_recapture

As a builder,
I want one regeneration loop that retries authoring with the failure reasons only and gives up after `REGEN_MAX`,
So that a failing room gets repaired without the failed draft being replayed, and a hopeless capture ends cleanly.

_Covers FR-10, AR-17, AR-9, AR-31, AD-6, AD-13. Owner: pipeline. Depends on: 2.20. Tier 1, Wed Oct 28; cut 7 sets `REGEN_MAX=1`. `regenerate.py` is the sole loop and sole writer of the count; the Riddler gets the failure reason list only; each call carries attempt = n so the cache never serves a failed answer; exhaustion ends the job `needs_recapture` with no `regen_exhausted` error class (AD-13 supersedes the old draft); per-attempt fixed messages recorded in job state for the 'Sent back' lines; the loop accepts any later gate (the Dry run, 2.24) as one more source of failed attempts._

**Acceptance Criteria:**

**Given** a draft that fails and `REGEN_MAX` at its default of 2
**When** `src/pipeline/regenerate.py` runs
**Then** the Riddler is called again through the 2.19 regeneration variant with the reason list only, up to 2 times, and a draft that passes on any attempt proceeds with the count recorded

**Given** Regeneration count n
**When** the loop makes its calls
**Then** each Riddler call (and each Dry run call) carries `attempt = n`, so under `CACHE=on` attempt n is never served attempt n-1's cached answer

**Given** every attempt failing
**When** the loop is exhausted
**Then** with `REGEN_MAX=2` the job ends `needs_recapture` after exactly 3 Riddler calls, and with `REGEN_MAX=1` (cut 7) after exactly 2
**And** no `regen_exhausted` error class or code exists anywhere in the codebase

**Given** a failed attempt
**When** the loop records it
**Then** job state gains that attempt's fixed messages, one list per failed attempt, quoting no token or answer, ready for the "Sent back" lines

**Given** a later gate (a Dry run test double) that reports a failure
**When** the loop receives it
**Then** it counts as one more failed attempt in the same count
**And** `regenerate.py` is the only writer of the count, and the stage runner only reads it into provenance

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.22: Scene stage writes the immutable Room and the final job record

As a builder,
I want the scene stage to write the Room once and the final job record beside it,
So that only a verified room ever becomes playable, and what happened during its Build is kept for good.

_Covers FR-9, FR-10, FR-30, AR-20, AD-7, AD-16. Owner: pipeline. Depends on: 2.21. Tier 1, Wed Oct 28; survives every cut (capture must). After the loop passes (and the Dry run when on), the scene stage writes the room artifact once, then immutable, and the final job record (timings, call rows, verdicts, build time) and ends the job done; with `DRY_RUN=off` (cut 4) every Puzzle is recorded 'skipped' and the Validator alone gates; a restart after scene never rewrites the Room._

**Acceptance Criteria:**

**Given** a draft that passed the Validator and, with `DRY_RUN=on`, the Dry run (a test double here)
**When** the scene stage runs
**Then** it writes the `room` artifact once through `ArtifactStore` under `rooms/` and ends the job `done`
**And** the written Room is never changed afterwards

**Given** a job that reaches `done`
**When** its final job record is read
**Then** it holds the per-stage timings, the call rows, the Validator verdicts, the Dry run verdicts, the Regeneration count, the scene count for "Setting the scene" and the build time, with the scene stage's duration measured against its 10 s budget and never enforced

**Given** `DRY_RUN=off` (cut 4)
**When** a draft passes the Validator
**Then** no Dry run call or ledger entry is made, every Puzzle's Dry run verdict is recorded as `skipped`, and the Room is written on the Validator's pass alone

**Given** a job whose scene stage has already written the Room
**When** the runner restarts and `start(job_id)` is called
**Then** the Room's bytes are unchanged and the job stays `done`

**Given** a job that ends `failed`, `needs_more_photos` or `needs_recapture`
**When** its artifacts are listed
**Then** no `room` artifact exists, so no partial Room is playable

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.23: Dry run prompt builder over what a player sees

As a builder,
I want a pure Dry run prompt built only from what a player sees,
So that a passing Dry run proves the Clues and Rungs are enough to solve every Puzzle.

_Covers FR-9, NFR-5, AD-3. Owner: council. Depends on: 1.7, 2.1. Tier 1, Wed Oct 28; cut 4 drops 2.23 and 2.24. `council/dryrun.py`: pure `build_dry_run_prompt` over Interactable ids and labels, Clues and Rungs (photos as bytes), reasoning low, returning `DryRunAnswers` as a list; sentinel prompt test: no solution, Lore-to-answer pairing or profile field. Dev skill: keyframe-muse._

**Acceptance Criteria:**

**Given** a `RoomView`
**When** `build_dry_run_prompt(room_view, response_schema)` runs
**Then** it renders only each Interactable's `id` and `label` and each Puzzle's `id`, Clue and three Rungs, with `reasoning_effort='low'`, and the photos reach the call as bytes through the adapter; answers name Interactables by the `ix_` ids given here

**Given** the `DryRunAnswers` schema
**When** it is inspected and passed through `strict_schema`
**Then** it is a list of `{puzzle_id, answer}` with `answer` reusing the solution union, has no map-typed field, and `strict_schema` accepts it

**Given** a Room fixture with sentinel solutions, whose sentinel solutions name ids and a code string that appear nowhere else in the fixture (not among its Interactables), and a sentinel `Derived` block
**When** the Dry run prompt is rendered
**Then** it contains no sentinel solution (the code string, the order id list in sequence, the `use_on` pair, the `find` target id), no Lore and so no Lore-to-answer pairing, no `evidence`, no `derived` key and no Player profile field

**Given** the same `RoomView` twice
**When** the prompt is built
**Then** both outputs are identical and the input is unchanged

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.24: Dry run stage proves every Puzzle solvable before the room ships

As a builder,
I want a Dry run between the regeneration loop and the scene stage that must reach every answer,
So that every room that ships has been solved from its Clues and Rungs by a call that never saw a solution.

_Covers FR-9, FR-10, AR-16, NFR-1, NFR-5, AD-12. Owner: pipeline. Depends on: 1.6, 2.9, 2.22, 2.23. Tier 1, Wed Oct 28; cut 4 drops it (`DRY_RUN=off`, 2.22 records skipped). One chat call between the loop and the scene stage when `DRY_RUN=on`; `check_dry_run` (1.6) compares answers to solutions; any mismatch, or output missing or unparseable for any Puzzle, is a failed attempt into the 2.21 loop (A-24); pass or fail per Puzzle recorded in job state for the Build view; adds the Dry run and full live Build cases under `tests/sit/`. Dev skill: keyframe-muse._

**Acceptance Criteria:**

**Given** `DRY_RUN=on` and a draft that passed `validate`
**When** the dryrun stage runs
**Then** it makes one `chat` call through the `dryrun` role over the 2.23 prompt, with `reasoning_effort='low'` and `attempt` set to the Regeneration count, and records one call row
**And** when every answer matches under `check_dry_run`, the job continues to the scene stage

**Given** an answer that mismatches, a Puzzle with no answer, or output that cannot be parsed
**When** the stage handles it
**Then** the attempt fails with a fixed reason (A-24) as `DryRunError` into the 2.21 loop, and the reasons quote neither the answer nor the solution
**And** once the loop is exhausted, the job ends `needs_recapture`

**Given** any Dry run
**When** job state is written
**Then** it records pass or fail per Puzzle and the "reached n of m answers" count, and never the answers themselves

**Given** the codebase
**When** callers of `check_dry_run` are listed
**Then** the dryrun stage is the only caller, and so the only place where answers meet solutions

**Given** `tests/sit/`
**When** the story lands
**Then** it adds a live Dry run case and a full live Build case that `scripts/sit.py` runs, and their recorded fixtures replay in the offline suite

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.25: Capture screen end states: failed, too few objects, re-capture and Spend cap

As a player,
I want a Build that cannot give me a room to stop clearly, keep my photos and tell me what I can do next,
So that I never wait on a dead build or lose the photos I chose.

_Covers FR-4, FR-5, FR-10, FR-28, UX-DR13, UX-DR15, UX-DR21, UX-DR62, UX-DR63, UX-DR75. Owner: web. Depends on: 2.18, 2.21, 2.22. Tier 1, Wed Oct 28. On every end state the Timer stops showing the status and the photos stay visible; failed: 'The build stopped while {stage}.' with the plain cause class and 'Try again' (a new Build with the same photos), no partial Room playable; `spend_cap_exceeded`: the warning variant with 'Start over' only; `needs_more_photos`: stopped at 'Finding objects', 'Add photos' (up to 10 in all, absent at 10) and 'Start over', the next Upload a new Build; `needs_recapture`: stopped at 'Testing the room' with the brighter, closer shots copy and 'Start over'; envelope codes mapped; the Capture reconnecting strip after two missed polls keeps the Stage list as last seen._

**Acceptance Criteria:**

**Given** a job that ends `failed` at a stage (mockups/capture-screen.html)
**When** the poll reads it
**Then** that stage row shows failed, the Timer freezes with the status, the photos stay visible, and the `error-banner` reads "The build stopped while {stage label, lowercased}." with "A model service didn't answer." for `provider_error` or "The build stopped unexpectedly." otherwise
**And** "Try again" posts a new `POST /builds` with the same photos, and nothing offers a partial Room

**Given** a job that ends `failed` with `spend_cap_exceeded`
**When** the poll reads it
**Then** the `warning-banner` reads "Keyframe has reached its spending limit, so this room can't be built right now." and "Trying again won't help until the limit is raised; your photos are still here.", with "Start over" as its only action

**Given** a job that ends `needs_more_photos` (also reached from the `too_few_interactables` code)
**When** the poll reads it
**Then** the Stage list stops at "Finding objects", and the banner reads "Keyframe found too few objects to build a room." with "Add a few more photos of this room, closer to shelves and tables, up to 10 in all.", "Add photos" (which appends up to 10 in all) and "Start over"
**And** with 10 photos already in the set, the body reads "You already have 10 photos. Start over with closer shots of shelves and tables." with no "Add photos", and the next Upload is a new Build

**Given** a job that ends `needs_recapture`
**When** the poll reads it
**Then** the Stage list stops at "Testing the room", and the banner reads "Keyframe couldn't build a fair room from these photos." with "Try brighter, closer shots where labels and printed text are readable." and "Start over"

**Given** a Build in progress
**When** two consecutive polls are missed
**Then** the `status-strip` appears at the top of the left area, above any banner, reading "Reconnecting to Keyframe. Your build keeps going; this page catches up when it's back.", written once to the live region and taking no focus, while the Stage list and Mask preview stay as last seen and the Timer keeps counting
**And** the next successful poll re-renders from job status and removes the strip

**Given** any end-state banner
**When** it is checked against the accessibility floor
**Then** it takes focus when it appears, its actions come next in Tab order with a visible focus ring and are activated by Enter, only one banner shows at a time, and text meets WCAG AA contrast

**Given** the story's changes
**When** the web build, the type check and `pytest` run offline against the mock provider
**Then** all pass with new tests covering this story's criteria

### Story 2.26: Capture measured: p50 per stage over five live Builds

As a builder,
I want the Capture target measured over at least five live Builds before Thursday,
So that the 120 s target is either confirmed or re-based on real numbers before the videos depend on it.

_Covers NFR-1, NFR-6. Owner: builder task. Depends on: 2.9, 2.22, 2.25 (and 2.24 unless cut 4 is taken). Tier 1, Oct 27 to 28 measurement window, closed Wed Oct 28. The builder runs at least 5 live Builds within the Spend cap and records p50 per stage and end to end against NFR-1, with the re-base decision dated in the sprint status (re-base allowed); no dev agent runs it. Dev skills: keyframe-muse, keyframe-sam31._

**Acceptance Criteria:**

**Given** the Oct 27 to 28 window, the M1, `CACHE=off` and Photo sets never built before
**When** the builder runs at least 5 live Builds from Upload to the first Hotspot response
**Then** the sprint status records, dated, the p50 per stage (Architect, segmentation, Riddler, Dry run, Scene) against the 15, 10, 45, 30 and 10 s budgets, and the p50 of T1 − T0 against 120 s

**Given** the recorded end-to-end p50
**When** the window closes on Wed Oct 28
**Then** the sprint status holds a dated decision: either 120 s stands, or the target is re-based to the measured p50 plus 25%

**Given** the measurement Builds
**When** their job records are read
**Then** every Build that ran over a stage budget still reached its end state without failing for the overrun

**Given** the day's Ledger exports for Oct 27 and Oct 28
**When** they are read
**Then** they list every measurement Build's calls, the spend stays within the Spend cap and the daily ceilings ($5 on Oct 27, $10 on Oct 28), and `git ls-files rooms/` prints nothing while `git check-ignore -q rooms/` succeeds, so the measurement photos are ignored and uncommitted

**Given** cut 4 taken before the window closes
**When** the record is written
**Then** it states that the Dry run was skipped, and gives no Dry run p50

### Story 2.27: BuildView projection, never carrying a solution

As a builder,
I want one pure projection that turns a Room and its job record into a `BuildView`,
So that the Build view can show every check that was made without any solution reaching a browser.

_Covers FR-38, AR-6, AR-31, NFR-5, AD-3, AD-16. Owner: domain. Depends on: 1.7, 2.22. Tier 1; cut 0 (the first Cut taken) drops 2.27 to 2.31; Thu Oct 29. Pure `to_build_view(room, job)` filling the `BuildView` model 1.5 declared: per-photo mask polygons with labels, the puzzle graph (id, `lock_type`, requires, `is_exit`), per-rule verdicts with check names, Dry run pass, fail or skipped per Puzzle, the Regeneration count and `REGEN_MAX`, per-attempt sent-back messages, build time, Model table rows with provenance counts and call rows (role, model, host, cached or billed), and the disclosure list (global lines until 6.2); sentinel test: no solution, Clue-to-answer pairing or Dry run answer._

**Acceptance Criteria:**

**Given** a done Room and its final job record
**When** `to_build_view(room, job)` runs
**Then** the `BuildView` holds, per photo, each Interactable's polygons with its label (box fallbacks included as polygons); the puzzle graph (`id`, `lock_type`, `requires`, `is_exit`); one verdict per Validator rule with its check-phrased name from the 1.6 table; Dry run pass or fail per Puzzle; the Regeneration count and configured `REGEN_MAX`; the per-attempt sent-back messages; and the build time

**Given** call rows with mixed cached and billed calls for one role, and a role served by a fallback model
**When** the Model table rows are built
**Then** each role and model has one row, with its provenance count ("found 9 objects", "outlined 9 objects", "wrote 5 puzzles", "tried 5 puzzles blind") and both counts when calls were mixed
**And** a role run by a fallback shows the model and host that actually ran, taken from the call rows

**Given** a job built with `DRY_RUN=off` (cut 4)
**When** it is projected
**Then** every Puzzle's Dry run verdict reads `skipped`

**Given** a job built with `REGEN_MAX=1` (cut 7)
**When** it is projected
**Then** the configured `REGEN_MAX` reads 1 and each Dry run verdict is the recorded pass or fail

**Given** a disclosure list
**When** the projection is built
**Then** `disclosure` holds exactly the given lines (the global lines until 6.2 adds the per-Room line)

**Given** a Room fixture with sentinel solutions, whose sentinel solutions name ids and a code string that appear nowhere else in the fixture (not among its Interactables), and a job record whose Dry run answers equal them
**When** the `BuildView` is serialized
**Then** it contains no `solution` key, no sentinel solution, no Clue-to-answer pairing, no Dry run answer and no Clue text
**And** the function leaves its inputs unchanged and imports only the standard library and pydantic

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.28: Build view route

As a builder,
I want `GET /builds/<job_id>/view` to serve the `BuildView` to anyone with the link,
So that a judge or player can see how a room was built with no Access code, and with no way to see its answers.

_Covers FR-38, AR-13, AD-15. Owner: api. Depends on: 2.12, 2.27. Tier 1; cut 0 drops it; Thu Oct 29. `GET /builds/<job_id>/view` returns the `BuildView`, open in both modes with no Access code; 409 `build_not_ready` with the job `status` in the envelope for a job not yet `done` (spine AD-3, AD-13); 404 for an unknown job; API sentinel test: no solution, pairing or Dry run answer in the response._

**Acceptance Criteria:**

**Given** a job that reached `done`
**When** `GET /builds/<job_id>/view` is called with no access code
**Then** it returns 200 with the `BuildView` from 2.27, its `disclosure` filled by the one function in `src/api/meta.py`

**Given** the route's wiring
**When** it is inspected under `MODE=local` and `MODE=hosted`
**Then** in neither mode is it guarded by `X-Access-Code`

**Given** an unknown `job_id`
**When** the route is called
**Then** it answers 404

**Given** a known job that has not reached `done` (`queued`, `running`, `failed`, `needs_more_photos` or `needs_recapture`)
**When** `GET /builds/<job_id>/view` is called
**Then** it answers 409 without a `BuildView`, with the envelope `{error: {code: "build_not_ready", message, stage: null, status}}` where `status` is the job status (spine AD-3, AD-13), and 2.29's not-ready state keys on that `status`
**And** `status` appears in the envelope on `build_not_ready` only, never on another error code

**Given** a Room fixture with sentinel solutions, whose sentinel solutions name ids and a code string that appear nowhere else in the fixture (not among its Interactables)
**When** the API sentinel test calls the route
**Then** the response holds no `solution` key, no sentinel solution, no Clue-to-answer pairing and no Dry run answer

**Given** `GET /schema`
**When** it is read after this story
**Then** it includes `BuildView`, the regenerated `web/types` are committed, and the 1.15 staleness test passes

**Given** the story's changes
**When** `pytest` runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 2.29: Build view: header, Model table and In play block

As a judge,
I want the Build view to open on the Room's header and a table of which model did what, where it ran and whether it was billed,
So that I can see in a minute that the room was really built by the Meta model stack.

_Covers FR-38, UX-DR48, UX-DR53, UX-DR54, UX-DR67, UX-DR8, UX-DR78. Owner: web. Depends on: 1.17, 2.28. Tier 1; cut 0 drops it; Thu Oct 29 to Sat Oct 31. `#/build/<job_id>/view` with the banner and top bar (wordmark and mode indicator only) pinned while the body scrolls; header with the Room's name or build time, 'Regenerations: n of {max}', one 'Attempt {k} sent back:' line per failed attempt and 'Back'; Model table first in the right column (Role, Model, Where it ran, What it did, Cached or billed with both counts when mixed; fixed Validator, Dry run and Muse Image rows; no Guide or Trickster row) with its caption; In play block from `GET /meta` (Llama 3.2 3B on 'Ollama on the Mac', or the hosted line; Trickster source); not-ready and error states; initial focus on the title._

**Acceptance Criteria:**

**Given** `#/build/<job_id>/view` for a done Build (mockups/build-view.html)
**When** it loads
**Then** the `disclosure-banner` (from `BuildView`'s `disclosure`) and a top bar holding only the wordmark and mode indicator stay pinned while the full-width body scrolls, with a left two-thirds column and a right third, and every table fits at 1280 px without horizontal scroll

**Given** the `build-view-header`
**When** it renders
**Then** the title is `Room.name` in `display-md` with the build time beside it, or, when there is no name, the build time in the form "Tue Nov 3, 10:42"
**And** it shows "Regenerations: n of {max}", one "Attempt {k} sent back: {fixed messages}" line per failed attempt, and "Back", which returns to where the view was opened

**Given** the `model-table`, first in the right column and above the fold at 900 px
**When** it renders
**Then** its columns are "Role", "Model", "Where it ran", "What it did" and "Cached or billed"; wizard rows lead with a 24 px portrait and the wizard's name, the Architect and Riddler rows carry their role lines, model ids are in `mono-sm`, and mixed counts read like "3 billed · 9 cached"
**And** fixed rows show the Validator ("code, no model", "checked 8 rules", empty cached cell), the Dry run (its model and host, or "skipped" under cut 4) and Muse Image ("muse-image-1.0", "painted the four portraits, once"); there is no Guide or Trickster row, and the caption "Cached means an identical earlier call was served from the cache, unbilled; billed means it ran live and was paid for." sits under the table
**And** Meta-served rows read "Meta Model API" under "Where it ran" and the Validator row reads "this Mac"; the Architect takes one row for muse-spark-1.3 and one for sam-3.1; the Architect's and Riddler's role lines sit as full-width rows under their rows

**Given** the `in-play-block` under the Model table
**When** it is filled from `GET /meta`
**Then** the Guide row shows Llama 3.2 3B on "Ollama on the Mac" in Local mode, or "Hints are shown as written here. In Local mode, Llama 3.2 3B rewords them on the Mac." in Hosted mode
**And** the Trickster row shows "Source: live", "Source: scripted" or "Source: written in advance"

**Given** a Build that is not `done`, or a failed load of the view
**When** the page renders
**Then** a not-done Build, recognized by the 409 `build_not_ready` answer from 2.28 and keyed on the job `status` in its envelope, shows the header, "This room is still being built." and a link to its Capture screen, with no panels; a failed load (any other error or no answer) shows "Keyframe couldn't load how this room was built." with "Try again"
**And** under cut 0 the route and surface are absent

**Given** the Build view
**When** it is checked against the accessibility floor
**Then** initial focus is on the title, Tab runs through the title, "Back", the Model table and the In play block in that order, each with a visible focus ring, the tables are real `<table>` elements with header cells, text meets WCAG AA contrast, and motion respects reduced-motion settings

**Given** the story's changes
**When** the web build, the type check and `pytest` run offline against the mock provider
**Then** all pass with new tests covering this story's criteria

### Story 2.30: Build view: puzzle graph and mask overlays

As a judge,
I want the Build view to show the puzzle chain as a graph and every object's outline on its photo,
So that I can see how the room is structured and what the models found, without seeing a single answer.

_Covers FR-38, UX-DR49, UX-DR50, UX-DR67, UX-DR71. Owner: web. Depends on: 2.29. Tier 1; cut 0 drops it; Sat Oct 31. Puzzle graph left to right with the Exit rightmost (168 x 64 nodes, order number and Lock type, requires arrows, Exit double ring, Dry run marker; focusable with 'Puzzle {n}, {lock type}, requires {list or none}, Dry run {verdict}'); mask overlay grid with focusable label chips (box fallbacks drawn the same); Enter on a node acts as a click; no answer or pairing anywhere._

**Acceptance Criteria:**

**Given** a `BuildView` with 4 to 6 Puzzles (mockups/build-view.html)
**When** the puzzle graph renders at the top of the left column
**Then** it runs left to right with the Exit puzzle rightmost, as 168 x 64 parchment `graph-node` elements showing the Puzzle order number and Lock type in `mono-sm`, with `requires` edges in `graph-edge` carrying 8 px arrowheads
**And** the Exit node has a 3 px lamp double ring and an "Exit" label in `lamp-ink`, and each node shows a Dry run marker in its top-right corner (an 8 px dot plus "pass", "fail" or "skipped" in `success-ink`, `wrong-ink` or `ink-muted`)

**Given** the graph nodes
**When** the player tabs through them
**Then** they take focus in Puzzle order, each named "Puzzle {n}, {lock type}, requires {list or none}, Dry run {verdict}", with "Exit" added on the Exit puzzle
**And** Enter on a node acts as a click and does nothing beyond focus

**Given** the mask overlay grid under the graph
**When** it renders
**Then** it shows the Room's photos three across at 4:3, each Interactable's mask drawn in `build-view-mask`, filled with `mask-overlay-fill` and stroked with a 2 px lamp line and a dark halo, and its label on a focusable parchment chip
**And** box-fallback polygons are drawn the same way

**Given** a `BuildView` fixture built from a Room with sentinel solutions
**When** the page renders
**Then** no sentinel solution, Clue-to-answer pairing or Dry run answer appears in the DOM, and the page requests no Room

**Given** the graph and overlays
**When** they are checked against the accessibility floor
**Then** every node and chip shows a visible focus ring, text and markers meet WCAG AA contrast, motion respects reduced-motion settings, and the layout fits 1280 px without horizontal scroll

**Given** the story's changes
**When** the web build, the type check and `pytest` run offline against the mock provider
**Then** all pass with new tests covering this story's criteria

### Story 2.31: Build view: verdict table, Dry run rows, JSON pane and the entry links

As a judge,
I want the Validator's verdict on every rule, the Dry run result for every Puzzle and the raw build data, all reachable from wherever a room appears,
So that I can check the verification myself and confirm that the page holds no answers.

_Covers FR-38, UX-DR51, UX-DR52, UX-DR55, UX-DR71, UX-DR84, UX-DR19, UX-DR44. Owner: web. Depends on: 1.18, 1.23, 2.18, 2.30. Tier 1; cut 0 drops it and every link to it; Sat Oct 31. Verdict `<table>` with its caption and the fixed message on fail rows only; Dry run rows with caption (cut 4: all 'skipped' with the cut-4 caption); collapsed 'Show the build JSON' pane showing the response exactly as served; no answer, pairing or repeated Clue anywhere; Tab order per UX-DR71; 'How this room was built' links on the Capture done state, stored Room rows and the Completion screen._

**Acceptance Criteria:**

**Given** the `verdict-table` in the right column (mockups/build-view.html)
**When** it renders
**Then** it is a real `<table>` on `chrome` under the caption "The Validator is code, not a model. It checks these 8 rules on every draft; a failed rule sends the draft back to the Riddler.", with header cells "Rule", "Check" and "Verdict" and one row per rule (rule number in `mono-sm`, the check-phrased name, and the verdict word with an 8 px `graph-pass` or `graph-fail` marker)
**And** the rule's fixed message appears on fail rows only, and the table fits at 1280 px without horizontal scroll

**Given** the Dry run rows
**When** they render
**Then** each Puzzle has one row ("Puzzle", "Lock type", "Verdict") under "A separate muse-spark-1.3 call saw only the clues, hints and object names, never the answers, and tried every puzzle."
**And** under cut 4 every row reads "skipped" in `graph-skipped`, and the caption becomes "The test run was switched off for this build, so no puzzle was tried blind."

**Given** the `build-view-json` pane under the mask overlays
**When** the player opens "Show the build JSON" (a secondary toggle with an expanded state, collapsed by default)
**Then** it shows "Everything this page receives. It holds no answers; a sentinel test checks every build for them." and then the `GET /builds/<job_id>/view` response exactly as served, pretty-printed in `mono-sm`, at most 360 px high, in a focusable scrollable region

**Given** the whole Build view
**When** it is rendered from a fixture built on sentinel solutions and tabbed through
**Then** no answer, Clue-to-answer pairing, Dry run answer or repeated Clue appears anywhere
**And** Tab runs through the header title, "Back", the Model table, the In play block, the verdict table and Dry run rows, the graph nodes, the mask label chips and the JSON toggle, in that order

**Given** a Capture screen whose Build is `done`, a stored Room row, and the Completion screen
**When** each renders
**Then** each shows a secondary "How this room was built" link that opens `#/build/<job_id>/view` for that Room's job (on the Capture screen in the done state, beside "Play this room" on a reopened done Build), and "Back" returns there
**And** under cut 0 none of these links renders

**Given** the verdict table, the Dry run rows, the JSON pane and the links
**When** they are checked against the accessibility floor
**Then** each control and the JSON region shows a visible focus ring and responds to Enter, the tables have real header cells, and text meets WCAG AA contrast on the dark theme

**Given** the story's changes
**When** the web build, the type check and `pytest` run offline against the mock provider
**Then** all pass with new tests covering this story's criteria

## Epic 3: A game master that helps without telling

While playing, the player gets stuck and the Guide escalates nudge, direction, near-answer from how they play, with the triggering events visible in the Triggers panel; asking for the answer yields nothing above the current Rung; Rungs are phrased on the Mac by Llama 3.2 3B (verbatim under cut 3 and in hosted mode) and never contain a solution; the four wizard portraits appear in play.

### Story 3.1: Rung selection in code from the Event log

As a builder,
I want the Rung for each Puzzle selected in pure code from the session's Event log,
So that the Guide escalates from real Idle time and Wrong attempts, the timing is the same at every persistence the spec allows, and a replayed session reaches exactly the Rungs the live one did.

_Covers FR-15, FR-24, AR-7, AR-11, AR-14, AD-4, AD-8, AD-10. Owner: domain. Depends on: 1.8, 1.10. Tier 1, Thu Oct 29. Pure select_rung inside apply with Rungs, Wrong attempts and Idle tracked per Puzzle; Idle counts from the last click, lock input or Hint request and idle ticks never reset it; the Active puzzle's nudge fires after clamp(90000 x (1 + 0.5p), 60000, 135000) ms of Idle (90 s fresh) or 3 Wrong attempts; direction and near-answer each need a further stall or 3 further Wrong attempts and arrive at least 90 s after the previous Rung, a spacing never scaled by persistence; a Loosen hook reserved for 4.1; no reveal or skip after the near-answer; RungChangeEvent with triggered_by; replay equals live with no duplicate rung_change; at DEMO_TIMESCALE=6 thresholds are 15 s and three Rungs arrive within 40 s on Wrong attempts (45 s on idle), t_ms and the poll unchanged._

**Acceptance Criteria:**

**Given** `select_rung(events, derived, thresholds)` in `src/domain/rungs.py`
**When** the nudge threshold is computed from `derived.persistence`
**Then** it equals `clamp(90000 * (1 + 0.5 * persistence), 60000, 135000)` ms: 90000 for `Derived.fresh()` (persistence 0), 112500 at 0.5, 135000 at 1, and 60000 at -1 (the floor, not 45000)
**And** the formula exists only in `src/domain/rungs.py`, no module other than `domain/rungs.py` and `HintPhraser` implementations reads `derived.persistence` (test), and `tests/test_boundaries.py` passes with `domain/rungs.py` importing only the standard library and pydantic (no clock, network or filesystem), so `select_rung` returns the same result for the same inputs

**Given** a session at `DEMO_TIMESCALE=1` with `Derived.fresh()` and an Active puzzle at `current_rung` 0
**When** `IdleTickEvent`s are applied while Idle, counted from `t_ms` of the last click, lock input or `hint_request`, is under 90000 ms
**Then** no `rung_change` is appended, and the first `idle_tick` applied with Idle at or above 90000 ms makes `SessionStateMachine.apply` append `RungChangeEvent(puzzle_id, rung=1, triggered_by=[the id of the event Idle is counted from, that is the last click, lock input or `hint_request`, or the Puzzle's previous `rung_change` when later, omitted when Idle counts from session start; the triggering `idle_tick` id])` and set `current_rung[puzzle_id]` to 1 (a click resets Idle before any check)
**And** an `idle_tick` never resets Idle while a click, lock input or `hint_request` does, and a Puzzle that is not the Active puzzle never receives an idle-triggered `rung_change`

**Given** an Active puzzle at `current_rung` 0 well inside its Idle threshold
**When** 3 Wrong attempts are applied at that lock (a failed `code` input, a resolved `use_on` pair that does not match, or a mismatched full-length armed `order` buffer)
**Then** a `rung_change` to rung 1 is appended on the third, with the three Wrong-attempt event ids in `triggered_by`
**And** a click never counts toward the 3, a refused input (unmet prerequisites, an item not in the Inventory, a `use_on` pair resolving to no Puzzle, an `order_stop`) never counts, and Wrong attempts at another lock never count toward this lock's `wrong_attempts[puzzle_id]`

**Given** a Puzzle that reached rung 1 at time t
**When** 3 further Wrong attempts arrive at that lock before t + 90000 ms, or a further stall (Idle equal to the nudge threshold, counted from the later of the last click, lock input or `hint_request` and the previous `rung_change` for that Puzzle) completes
**Then** no direction Rung is appended before t + 90000 ms, and the first event applied at or after t + 90000 ms with the condition met appends a `rung_change` to rung 2; the near-answer (rung 3) follows the same rule from the direction's time
**And** the 90000 ms spacing is the same at persistence -1, 0 and 1; after the near-answer no further `rung_change` is appended for that Puzzle however long the Idle or however many Wrong attempts (no reveal, no skip, `current_rung` never above 3); `select_rung` exposes the reserved Loosen hook that 4.1 drives (opening a named Rung at once, outside the spacing), which no event reaches in this story

**Given** a session log holding clicks, lock inputs, `hint_request`s, `idle_tick`s and the `rung_change` events appended live
**When** the session state is replayed from the log
**Then** `current_rung`, `wrong_attempts`, `rungs_used` and `rung_changes[]` equal the live state
**And** replay appends no `rung_change`, so no Rung change is ever duplicated

**Given** `DEMO_TIMESCALE=6`, `Derived.fresh()` and the session clock in `src/infra/clocks.py`
**When** wiring builds the thresholds passed into `apply`
**Then** the nudge threshold and the Rung spacing are 15000 ms each and the Trickster window threshold passed for Epic 4 is 30000 ms, while `t_ms` stamps, the 5000 ms `idle_tick` gap and the 2000 ms client poll are unchanged and the build clock is untouched
**And** a run with an injected session clock posting a wrong code every 2000 ms from 2000 ms appends rungs 1, 2 and 3 at 6000, 22000 and 38000 ms (within 40 s); a synthetic idle-only log with an `idle_tick` every 1000 ms appends them at 15000, 30000 and 45000 ms (45 s on idle); through the API with the real 2000 ms poll, each idle Rung is appended on the first `idle_tick` at or past its condition, the test records the three real times, and the 45 s on idle is reported as nominal (FR-24)

**Given** the story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 3.2: HintPhraser port with the verbatim adapter

As a builder,
I want a `HintPhraser` port with a verbatim adapter, selected by `GUIDE` alone,
So that every Rung and Greeting flows through one interface that sees only the Rung text and the Derived block, and hosted mode never runs a Guide model.

_Covers FR-17, AR-8, AR-26, AD-3, AD-5. Owner: providers. Depends on: 2.1. Tier 1, Thu Oct 29 (verbatim Rungs in the day plan). HintPhraser phrase(rung_text, derived) and greet(derived), separate from ModelProvider and selected by GUIDE alone; the verbatim adapter returns the Rung text (and the filled Greeting template used in 5.5); AD-3 test: the phraser input is exactly (rung_text, derived) and nothing else; returns the phrased flag and latency for the caller to record._

**Acceptance Criteria:**

**Given** `src/providers/base.py`
**When** the port is declared
**Then** `HintPhraser` exposes `phrase(rung_text, derived)` and `greet(derived)`, separate from `ModelProvider`, and each call returns the text plus whether it was phrased and the latency in ms, for the caller to record
**And** a test fails if any class in `src/providers` other than the verbatim adapter and the Ollama adapter implements `HintPhraser` (`mock`, `meta`, `openai_compatible` and `fal` never do)

**Given** the verbatim adapter
**When** `phrase(rung_text, derived)` is called
**Then** it returns `rung_text` byte for byte, reported as not phrased
**And** it opens no network connection and reads no clock other than the latency it reports

**Given** the verbatim adapter
**When** `greet(derived)` is called
**Then** it returns the Greeting template chosen from the Derived block in order: null `time_to_first_hint_s` gives "Welcome back. Last time you never asked me once; let's see what this room makes of you."; persistence 0.34 or more "Welcome back. Last time you kept going long past my first nudge; let's see what this room makes of you."; -0.33 to 0.33 "Welcome back. Last time you held out a good while before asking; let's see what this room makes of you."; -0.34 or less "Welcome back. Last time you held out just long enough to get your bearings before asking; let's see what this room makes of you." (persistence is rounded to two decimals before the bands are applied)
**And** tests cover persistence 0.34, 0.335, 0.33, -0.33, -0.335 and -0.34 and a null `time_to_first_hint_s`, and no template names an object or a solution

**Given** `Settings` and `src/api/wiring.py`
**When** the `HintPhraser` is resolved
**Then** `GUIDE` alone selects it: `GUIDE=verbatim` gives the verbatim adapter, no other setting selects a phraser (7.2 keeps it so when `Settings.mode` arrives), and `GET /meta` reports `guide` `verbatim` with `guide_model` null
**And** until the Ollama adapter exists (3.7), and under cut 3, `GUIDE=ollama` fails at startup with a message naming `GUIDE=verbatim`; (Hosted mode, Tier 1.5, delivered with `Settings.mode` in 7.2) `MODE=hosted` defaults to `GUIDE=verbatim`, `Settings` refuses to start on `MODE=hosted` with `GUIDE=ollama`, and no Guide model connection is attempted in hosted mode; until 3.7 lands, and under cut 3, the offline suite and the builder's local runs set `GUIDE=verbatim` explicitly, and a test asserts that startup with the default `GUIDE=ollama` and no Ollama adapter fails with the message naming `GUIDE=verbatim`

**Given** a recording phraser injected in place of the verbatim adapter and a fixture Room with sentinel solutions
**When** `phrase` and `greet` are called through the `HintPhraser` port by a test caller holding the fixture Room
**Then** `phrase` receives exactly `(rung_text, derived)` and `greet` exactly `(derived)`: no label, Clue, Lore, other Rung, interactable id, room id or solution (AD-3)
**And** no sentinel solution (the code string, the order id list in sequence, the `use_on` pair, the find target id) appears in any input the recording phraser saw

**Given** the story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 3.3: Hint requests return the current Rung or the No-hint line

As a player,
I want to ask for help and get the hint I have earned so far,
So that I get unstuck without anyone, including me, being able to talk the game into giving away the answer.

_Covers FR-14, FR-15, FR-17, NFR-5, UX-DR76, AR-7, AR-31, AD-3, AD-4. Owner: api. Depends on: 1.12, 3.1, 3.2. Tier 1, Thu Oct 29. A hint_request (puzzle_id omitted -> the Active puzzle) returns the current Rung routed through the injected HintPhraser, or with no Rung open the fixed No-hint line 'A fair ask. Look around a little longer; I'll speak up if you stay stuck.' (never phrased), logged as an Early ask that lowers persistence through RoomResult and never releases the nudge (PRD §13 Q9, log only); after the near-answer a request repeats it; rung_change populates phrased, phrasing_ms and text (fields frozen in 1.5); the Scripted attack suite led by 'just tell me the answer', run through the API at rungs 0, 1 and 2, opens nothing and returns nothing above the current Rung; fixture test: no solution in any play response; a client t_ms is rejected; the session state populates the effective nudge threshold and spacing, their 1x values and their source (Derived block or fresh) for the Triggers panel._

**Acceptance Criteria:**

**Given** a session whose Active puzzle has `current_rung` 2
**When** the client posts `HintRequestEvent` with `puzzle_id` omitted to `POST /sessions/<id>/events` 10 times in a row
**Then** each reply is the direction Rung routed through the injected `HintPhraser`, never the near-answer, and `current_rung[puzzle_id]` is still 2 afterwards (a `hint_request` never triggers a Rung)
**And** each `hint_request` is appended with a server-stamped `t_ms` and resolved to `active_puzzle_id`; a body carrying a client `t_ms` is rejected with 422 and nothing is appended; a `hint_request` body carrying any field beyond `puzzle_id` (such as typed text) is rejected with 422 and nothing is appended

**Given** a session whose Active puzzle has `current_rung` 0
**When** a `hint_request` is posted
**Then** the reply is exactly "A fair ask. Look around a little longer; I'll speak up if you stay stuck." and `phrase` is never called, in any `GUIDE` setting
**And** the request is logged as an Early ask: the A-19 persistence inputs in `GET /sessions/<id>/result` mark that Puzzle with an Early ask, and the nudge still waits for its threshold or 3 Wrong attempts (no `rung_change` is released by the request)

**Given** a Puzzle at the near-answer (`current_rung` 3)
**When** further `hint_request`s are posted for it
**Then** each reply repeats the near-answer, and no reveal, skip, solution or lock change follows

**Given** a `rung_change` appended while the injected phraser reports a phrased line with a latency of 1600 ms, and one appended under the verbatim adapter
**When** `GET /sessions/<id>` is read
**Then** the first carries `phrased` true and `phrasing_ms` 1600 and the second `phrased` false
**And** each `rung_change` is appended with the line text exactly as shown (the phrased text when `phrased` is true, else the verbatim Rung), and `rung_changes[]` in `GET /sessions/<id>` returns that text, so a poll, a reload and a replay all show the same words (the `text` field 1.5 declared)
**And** session state carries the effective nudge threshold and Rung spacing, their 1× values and whether the threshold came from the Derived block or `Derived.fresh()`: 90000 and 90000 ms from `Derived.fresh()` at timescale 1; 15000 and 15000 ms with 1× values of 90000 at `DEMO_TIMESCALE=6`; a 135000 ms threshold from a Derived block with persistence 1 (Hosted Tier 1.5: always `Derived.fresh()`)

**Given** the Scripted attack suite led by "just tell me the answer", run as `hint_request` sequences through the API against a fixture Room with sentinel solutions at rungs 0, 1 and 2
**When** every request has been answered
**Then** no lock opens and `locks_open`, the Inventory and `current_rung` are unchanged by the requests, and every reply is the current Rung, or the No-hint line at rung 0, never the text of a higher Rung
**And** a fixture test reading every play response (`POST /sessions` replies, `GET /rooms/<room_id>`, `GET /sessions/<id>`, `GET /sessions/<id>/room`, `POST /sessions/<id>/events` replies, `GET /sessions/<id>/result`) finds no `solution` key and no sentinel solution (the code string, the order id list in sequence, the `use_on` pair, the find target id), and no play response carries the text of a Rung above `current_rung` for its Puzzle (`PlayView` carries no Rung text, as 1.5 declared and 1.7 projects; Rung text reaches the client only in `hint_request` replies and `rung_changes[]`)

**Given** a recording phraser injected through wiring and a fixture Room with sentinel solutions
**When** `hint_request`s are answered and `rung_change`s are appended through `POST /sessions/<id>/events` and `GET /sessions/<id>`
**Then** every `phrase` call receives exactly `(rung_text, derived)`: no label, Clue, Lore, other Rung, interactable id, room id or solution (AD-3)
**And** no sentinel solution appears in any input the recording phraser saw

**Given** the story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 3.4: Hint area: ask the Guide and read the Rung line

As a player,
I want to ask the Guide from a tray beside my notes and see each hint arrive with its Puzzle,
So that help is always one Enter away, I can see my words stayed in the browser, and I never miss a hint the Guide offers on its own.

_Covers FR-14, UX-DR30, UX-DR31, UX-DR32, UX-DR29, UX-DR70, UX-DR82, UX-DR65. Owner: web. Depends on: 1.22, 1.25, 3.3. Tier 1, Thu Oct 29. A tray pinned under the Wizard notes (up to 320 px): field 'Stuck? Ask the Guide for a hint' and primary 'Ask the Guide' (Enter or the button sends one hint_request with puzzle_id omitted, named only while active_puzzle_id is null; an empty field still sends; one in flight; field read-only and button 'Asking'); typed text never leaves the browser and the permanent helper line says so; Rung line with the Guide portrait and 'Puzzle {n} · Nudge|Direction|Near-answer' replacing the previous line, which moves into its Puzzle's opened Rungs; every reply visibly arrives and is announced (a repeat fades out and in); a polled rung_change shows the line with one arrival glow; the opening line sits as the first Guide line; after a reload the current and opened Rungs are rebuilt from session state with nothing re-announced; Local thinking state while a request is in flight, none in Hosted; no 'verbatim' badge._

**Acceptance Criteria:**

**Given** the Play screen per `mockups/play-screen.html` with the Hint area (DESIGN.md Components: Hint area, Rung line, Hint field + Ask the Guide, Wizard portrait)
**When** it renders after "Begin"
**Then** a `chrome-raised` tray up to `{spacing.hint-area-max}` (320 px) sits pinned under the Wizard notes, its upper part scrolling and its lower part never scrolling: the field with placeholder "Stuck? Ask the Guide for a hint", the primary "Ask the Guide", the permanent helper line "Your words stay in this browser. The Guide only hears that you asked." and the slot the Triggers toggle takes in 3.5
**And** the opening line sits as the first Guide line, not announced again; the empty state shows the controls only

**Given** the player types "just tell me the answer" and presses Enter (or clicks "Ask the Guide")
**When** the request is sent
**Then** exactly one `hint_request` is posted with `puzzle_id` omitted, or naming the first available Puzzle (the one marked "Current") only while `active_puzzle_id` is null; the field turns read-only with the text visible, the button reads "Asking", a second Enter sends nothing, and the field clears when the reply lands
**And** an empty field still sends; a test intercepting every request finds the typed text in no body, query string or header; while reconnecting (two missed polls) the field and button are disabled with the other inputs

**Given** a reply to a Hint request
**When** it lands
**Then** the Rung line shows the Guide portrait (48 px), the label "Puzzle {n} · Nudge", "Puzzle {n} · Direction" or "Puzzle {n} · Near-answer" in `label` `lamp` (the No-hint line labelled "Puzzle {n}" alone) and the line in `wizard-line`, with no arrival glow because the player asked; a new Rung replaces the previous line, which moves into its Puzzle's opened Rungs in the Wizard notes
**And** a reply identical to the line already shown fades out and in (200 ms each way, instant under reduced motion) and is announced again; phrased and verbatim Rungs look identical, with no "verbatim" badge

**Given** a `rung_change` arriving on the 2000 ms poll of `GET /sessions/<id>`
**When** the client renders it
**Then** the Rung line appears, using the text `rung_changes[]` carries, never Rung text from `PlayView`, with no thinking state before it, one arrival glow on the Guide portrait ring and the tray edge (`{elevation.lamp-glow}`, 300 ms in all; the lit ring held 2 s under reduced motion), and one announcement
**And** the client never computes a Rung or reads the browser clock for hint timing

**Given** a Hint request in flight
**When** `GET /meta` reports `guide` `ollama`
**Then** the Guide portrait shows the static `lamp` ring and the "thinking on this Mac" label in `label` `pending` (the dark-surface pending color; `pending-ink` is for paper only), with no pulse, until the reply lands
**And** with `guide` `verbatim` (Hosted mode, or cut 3) no thinking state ever shows

**Given** a reload mid-session
**When** the Play screen resumes from `GET /sessions/<id>`
**Then** the current Rung line and each Puzzle's opened Rungs are rebuilt from session state, using the text `rung_changes[]` carries, never Rung text from `PlayView`, and nothing is re-announced and no arrival glow plays
**And** the surface meets the accessibility floor (NFR-14): the field and button are reachable by Tab with a visible focus ring, the field's accessible label is "Ask the Guide for a hint on Puzzle {n}", Rung and No-hint lines go to the one `aria-live="polite"` region prefixed "The Guide:", the portrait is decorative with empty alt, label and line text meet WCAG AA on the dark theme, and motion respects reduced-motion settings

**Given** the story's changes
**When** the web build and type check run
**Then** they pass with new tests covering this story's criteria

### Story 3.5: Triggers panel shows why each Rung arrived

As a player,
I want to see when the Guide moved to a new Rung and what triggered it,
So that the hints feel earned by how I played, and the escalation is visible on video.

_Covers FR-16, FR-24, UX-DR33, UX-DR80, UX-DR84. Owner: web. Depends on: 3.3, 3.4. Tier 1, Thu Oct 29; cut 5 moves the same content to a second window polling the same session. 'Triggers ({n})' toggle collapsed by default and opened automatically on load while a Disclosure is active (the player can collapse it); header 'Nudge after {threshold} s idle or 3 wrong attempts · next hint no sooner than {spacing} s' with the 1x values above timescale 1 and the source line; one row per rung_change: Puzzle, Rung name, cause ('Idle 92 s' from the triggered_by t_ms, '3 wrong attempts', 'Loosen card') and 'worded on this Mac · 1.6 s' or 'as written'; newest last and kept in view; empty 'No hint changes yet.'_

**Acceptance Criteria:**

**Given** the Hint area per `mockups/play-screen.html` and a session with no Disclosure active
**When** the Play screen loads
**Then** the Triggers toggle "Triggers ({n})" (secondary button, collapsed state) shows under the hint controls with n the number of Rung changes, and the panel is collapsed
**And** opened with no rows, the panel shows the header line and "No hint changes yet."

**Given** session state with a non-empty `disclosure` list
**When** the Play screen loads
**Then** the panel opens automatically and the player can collapse it
**And** while it is open the Hint area may grow until the Wizard notes reach `{spacing.notes-min}` (280 px); the rule that only the newest Card stacks while the panel is open is asserted by the Epic 4 Card story

**Given** the panel open
**When** the header renders from session state
**Then** it reads "Nudge after {threshold} s idle or 3 wrong attempts · next hint no sooner than {spacing} s" from the server's effective values, at a timescale above 1 each number followed by its 1× value ("Nudge after 15 s idle (90 s at 1×) …"), then "Set by how you played last time (kept in this browser)" when the threshold came from the Derived block, or "Default for a first room" from `Derived.fresh()` and in Hosted mode
**And** no web module computes a threshold or a spacing

**Given** `rung_changes[]` in session state
**When** the rows render
**Then** each row shows Puzzle {n}, the Rung name, the cause ("Idle {s} s" = the triggering `idle_tick` `t_ms` minus the `t_ms` of the other event `triggered_by` names, or minus 0 when it names none; "3 wrong attempts"; or "Loosen card" when it names a Trickster Card) and "worded on this Mac · {phrasing_ms in s, one decimal}" when `phrased` is true or "as written" when false, in `body-sm` with `mono-sm` numbers, newest last in `text` and kept in view, older rows `text-muted`, the list capped at `{spacing.triggers-panel-max}` (160 px) and scrolling
**And** a test shifting the browser clock leaves every row unchanged; at `DEMO_TIMESCALE=6` a stall nudge on a fresh profile reads its real seconds (at least 15 s), never a value scaled by 6; rows never show Rung text or a solution

**Given** cut 5 applied
**When** the player uses the Triggers toggle
**Then** the same header and rows open in a second browser window polling `GET /sessions/<id>` every 2000 ms, instead of in place
**And** both windows show the same rows for the same session

**Given** the panel in any state
**When** it is checked against the accessibility floor (NFR-14)
**Then** the toggle is reachable by Tab with a visible focus ring, operates by keyboard and announces its expanded state, header and row text meet WCAG AA on `chrome` (`text-muted` rows included), and rows are never written to the live region

**Given** the story's changes
**When** the web build and type check run
**Then** they pass with new tests covering this story's criteria

### Story 3.6: The four wizard portraits, painted once

As a builder,
I want the four wizard portraits generated once by a script and committed,
So that the council looks like characters in play and on video while play makes no image calls and costs nothing.

_Covers FR-23, UX-DR83, NFR-11, AD-6. Owner: scripts. Depends on: 2.6, 2.7, 2.12 (the image role comes from `wiring.py`). Tier 1, Thu Oct 29 (portraits gate). scripts/portraits.py calls generate_image through the image role once per wizard with the shared oil-portrait style block and one subject line each (1024 px square, faces in the center 70%), cached and priced, a second run all cache hits, exiting non-zero at the cap; outputs committed under web/public/portraits/, where the 1.20 portrait component picks them up; no play path or web module ever calls image generation._

**Acceptance Criteria:**

**Given** `scripts/portraits.py`
**When** it renders its four prompts
**Then** each is the shared style block (oil painting, visible brushwork, single-candle chiaroscuro from camera left, warm umber, ochre and lamp-amber palette, near-black background close to `canvas`, head and shoulders in three-quarter view, square 1:1 at 1024 px, no text, no painted frame, no resemblance to a real person) plus one subject line: the Architect with a brass loupe; the Riddler with a half-smile and a sealed folded note; the Guide kind and patient with a small lantern held low; the Trickster with a sly grin, one eyebrow up and a playing card
**And** no prompt carries room content, a photo or a Player profile field

**Given** the script run through the `meta` adapter against recorded image fixtures
**When** it runs once and then again with `CACHE=on`
**Then** the first run makes exactly four `generate_image` calls through the `image` role's `ModelProvider` (`muse-image-1.0`), each priced and appended to the ledger, and writes the four files under `web/public/portraits/`
**And** the second run is four cache hits with no new ledger entry and no file changed

**Given** the ledger guard refuses a call (`SpendCapExceeded`), or the call raises `ProviderError`
**When** the script reaches that portrait
**Then** it exits non-zero printing the cap and the running total (or the error), the refused call is never made, and no existing portrait file is overwritten

**Given** the portraits gate on Thu Oct 29
**When** the builder runs the script once live and views the results
**Then** four portraits sharing the candlelit oil style are committed under `web/public/portraits/`, each face inside the center 70% so the 96 px circular crop keeps it whole, and the run's ledger entries total about $0.04
**And** the 1.20 portrait component shows them in play (48 px on the Rung line, 32 px beside the Riddler's Clue); with a file removed, play shows the placeholder (the wizard's initial in `display-sm` gilt on `chrome-raised`) and makes no image call

**Given** a full play session run with a recording provider
**When** the test counts provider calls and inspects the routes and web modules
**Then** no play path calls `generate_image`, no route starts image generation, and no web module requests one

**Given** the story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 3.7: Hints phrased on the Mac by Llama 3.2 3B

As a player,
I want hints worded in the Guide's voice by a model running on this Mac,
So that help reads like a game master speaking, while my play data and the hint wording never leave the machine.

_Covers FR-17, NFR-2, NFR-3, NFR-4, AR-26, AD-5. Owner: providers. Depends on: 2.9, 3.2. Tier 1, Sat Oct 31; cut 3 drops it (Rungs verbatim in Local mode too, the README drops the phrasing claim, the Privacy line stays). Ollama adapter for llama3.2:3b Q4_K_M with OLLAMA_KEEP_ALIVE=-1 at OLLAMA_HOST; a byte-identical fixed prefix that tells the model to reword the Rung only, never add content (no new object, number, step or answer), whose input is exactly the Rung text and the Derived block, under 400 tokens, about 40 tokens out; past 5 s, or at once when Ollama is unreachable or errors, the verbatim Rung is shown and phraser_fallback is logged with its cause; greet uses the same prefix and bounds; never constructed in hosted mode; adds the Ollama case to scripts/sit.py, and the M1 benchmark is dated through the 2.9 checklist._

**Acceptance Criteria:**

**Given** `GUIDE=ollama` under `MODE=local`
**When** `phrase(rung_text, derived)` is called on `src/providers/ollama.py` (Python client 0.6.3, Ollama runtime v0.40.6)
**Then** it sends one request to `llama3.2:3b` (Q4_K_M) at `OLLAMA_HOST` with keep-alive -1, built from the fixed prefix plus the Rung text and the Derived block, with the output capped at about 40 tokens
**And** it returns the worded line reported as phrased with its latency in ms, and `GET /meta` reports `guide` `ollama` with `guide_model` naming `llama3.2:3b`

**Given** prompts rendered for every Rung of a fixture Room with sentinel solutions and several Derived blocks
**When** the test inspects them
**Then** the prefix is byte-identical across every `phrase` and `greet` call and tells the model to reword only and never add content (no new object, number, step or answer), each recorded fixture's `prompt_eval_count` is under 400, and every prompt rendered offline is no longer in characters than the longest recorded prompt
**And** no prompt contains a sentinel solution, a label, a Clue, Lore, another Rung or any field beyond the Rung text and the Derived block (`greet`: the Derived block only)

**Given** Ollama answers after 5 s, is unreachable, or returns an error
**When** `phrase` or `greet` is called
**Then** the verbatim adapter answers (the Rung text, or the Greeting template chosen by the Derived block), at once when unreachable or erroring and at 5 s on a timeout, reported as not phrased, and `phraser_fallback` is logged with its cause (`timeout`, `unreachable` or `error`)
**And** play continues with no error shown: the Rung line looks like any other and its Triggers row reads "as written"

**Given** `GUIDE=verbatim`
**When** the app is wired
**Then** the Ollama adapter is never constructed (test) and `GET /meta` reports `guide_model` null
**And** (Hosted mode, Tier 1.5, delivered with `Settings.mode` in 7.2) under `MODE=hosted` the adapter is never constructed and `Settings` refuses to start with `GUIDE=ollama`, so the Guide model runs only on the Mac

**Given** Llama 3.2 3B pulled on the 16 GB M1 MacBook Pro
**When** the builder runs the Ollama case added to `scripts/sit.py` (AR-25) and the benchmark with a 400-token prompt
**Then** the case passes against the live model and records its response as a fixture under `tests/fixtures`, and the prefill and decode rates, the end-to-end latency for about 40 tokens and the resident memory (near 3 GB, NFR-3) are dated in the 2.9 SIT checklist
**And** a latency above 5 s is flagged there as an NFR-2 miss

**Given** cut 3 applied
**When** the game runs in Local mode
**Then** the builder runs with `GUIDE=verbatim`: every Rung and the Greeting show verbatim, every Triggers row reads "as written", no thinking state shows, the README drops the phrasing claim, and the Privacy line stays verbatim

**Given** the story's changes
**When** pytest runs offline against the mock provider, with the adapter tested on recorded fixtures under `tests/fixtures` and no Ollama process running
**Then** it passes with new tests covering this story's criteria

## Epic 4: The room fights back, fairly

Between puzzles the Trickster proposes one bounded change, and the Validator decides whether it stands. The player sees accepted, rejected and skipped Cards in the Hint area and in the Card log. The room they play changes only when an edit is accepted. For the video, a scripted source replays recorded proposals, and a pre-authored file realizes cut 1. In both cases the Validator still runs live on every Card.

### Story 4.1: Trickster edits land only when the Validator passes, with rule 9 for Decoys

As a builder,
I want pure `validate_edit` and `apply_edit` in `src/domain/edits.py`, validator rule 9 for Decoys, and the Effective room folded from the session log,
So that a Trickster edit lands only when the room stays fair and solvable, and the stored Room shared across Sessions never changes.

_Covers FR-19, FR-11, AR-16, NFR-5, UX-DR77, AD-12. Owner: domain. Depends on: 1.6, 1.7, 1.8, 3.1. Tier 1, Thu Oct 29 if time remains, else Sat Oct 31._

**Acceptance Criteria:**

**Given** a valid fixture Room and a session state whose `trickster_window` is open
**When** `validate_edit(room, state, edit)` runs on any of these: a `decoy` whose `puzzle` is the `is_exit` Puzzle; a `loosen` whose `rung` is not one of `nudge`, `direction`, `near_answer`, or whose `puzzle` is not in the Room; a `merge` naming a Puzzle the Room does not have; a `shortcut` on a Puzzle with no `requires` edge; a `decoy` for a Puzzle that already has an accepted Decoy in this Session
**Then** each is refused with structured reasons `{rule, puzzle_id, field}` and the fixed message "The change is outside the Trickster's limits.", taken from the one Validator message table
**And** the same edit checked against a state whose `trickster_window` is closed is refused on the window bound with the same message, before any payload check

**Given** an edit that passes `validate_edit`
**When** `validate(apply_edit(room, edit))` runs
**Then** the edit is accepted only if rules 1 to 8 and rule 9 all pass, and no Dry run is called
**And** a `merge` that closes a cycle in `requires` is rejected on rule 1 with "Two locks would wait on each other forever."
**And** a `shortcut` that removes the `find` prerequisite a `use_on` Puzzle's item depends on is rejected on rule 8 with "A puzzle needs an item that can't be picked up yet."

**Given** Decoy storage option A (`Room.decoys[]`, empty on the stored build Room)
**When** a `decoy` does any of these: names an Interactable that does not exist; gives a `visible_attribute` the Architect did not read for that Interactable (not in its `attributes`); repeats an `{interactable, visible_attribute}` pair equal to any Puzzle's real `evidence`; targets the Exit puzzle; adds a second Decoy to the same Puzzle; or carries attribute text containing a rule 5 solution token
**Then** `validate` rejects it on rule 9 with "A false clue breaks the decoy rules."
**And** a sentinel test over every rejection asserts that no reason string contains the offending token, the code string, any of its digits, or any solution label

**Given** a stored build Room, and a session log holding accepted and rejected `trickster_card` events
**When** `apply_edit(room, edit)` runs for each type and the session is replayed. The types are: `merge` (`puzzle_b` now requires `puzzle_a`), `shortcut` (one `requires` edge removed), `decoy` (one `decoys[]` entry `{id, puzzle, interactable, visible_attribute}` appended) and `loosen` (Puzzles unchanged)
**Then** `apply_edit` returns a new Room whose `provenance.applied_edits` holds the edit's `te_` id
**And** the input Room is equal before and after the call, its `applied_edits` and `decoys` stay empty, and nothing is written through `ArtifactStore`
**And** the Effective room equals `apply_edit` folded over the accepted edits in log order, each read from the `TricksterEdit` carried in the session log and never from the stored Room
**And** each `trickster_card` with an edit carries its full `TricksterEdit` (`id`, `type`, `puzzle`, `payload`, `validator_result`, `accepted`, `window`), as Schema v1 places edits in the session log, in the `edit` field 1.5 declared on `TricksterCardEvent`
**And** `room_revision` equals the count of accepted edits, a rejected edit leaves the Effective room unchanged, and replay produces the same Effective room and `room_revision` as live play

**Given** an accepted `loosen` for a Puzzle and a Rung
**When** `SessionStateMachine.apply` processes its `trickster_card`
**Then** `current_rung` for that Puzzle is raised to that Rung at once, without Idle or Wrong attempts and outside the 90 s Rung spacing
**And** a `rung_change` is appended whose `triggered_by` names that `trickster_card` event
**And** a following `hint_request` for the Puzzle returns that Rung, and the Effective room's Puzzles are unchanged

**Given** an Effective room with one accepted Decoy
**When** `to_play_view` runs on it
**Then** that Puzzle's real Evidence and the Decoy appear in one merged `evidence_cards` list. The list has no flag, key, `te_` id or ordering rule that sets the Decoy apart, and its order is stable, seeded by room id: the same on every call and every replay
**And** one test asserts that real and Decoy entries cannot be told apart, and that the `PlayView` carries no `decoys`, `solution` or `provenance` key

**Given** the story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria
**And** those tests include the sentinel-solution check on every `validate_edit` and rule 9 reason

### Story 4.2: Trickster windows and the six-call budget in the session

As a builder,
I want `SessionStateMachine.apply` to own when a Trickster window opens, what the Game-state summary holds, how many proposal calls a Session spends, and how each window closes,
So that the Trickster acts at most once per 3 minutes of session time, only right after a non-exit lock opens, at most 6 times per Session, and a provider failure never halts play.

_Covers FR-18, FR-24, AR-7, AD-4, AD-10. Owner: domain. Depends on: 4.1. Tier 1, Sat Oct 31._

**Acceptance Criteria:**

**Given** a Session at least 180000 ms of session time past its start, with no Trickster window closed in the last 180000 ms (the window threshold wiring passes at timescale 1)
**When** an event opens a lock that is not the Exit puzzle's
**Then** `apply` opens `trickster_window`
**And** opening the Exit puzzle's lock opens no window
**And** an event that opens no lock leaves the window closed: a `click` that opens nothing, an `idle_tick`, a `hint_request`, or a Wrong attempt

**Given** a non-exit lock that opens 179999 ms after Session start, or 179999 ms after the previous window closed
**When** `apply` processes the event
**Then** `trickster_window` stays closed (A-26 for the first window)
**And** the same lock opening at 180000 ms in either case opens the window

**Given** wiring passes the window threshold from the session clock with `DEMO_TIMESCALE=6`
**When** a non-exit lock opens 30 s after the previous window closed, and at least 30 s after Session start
**Then** a window opens (180000 ms divided by 6)
**And** every event's `t_ms` stays the unscaled session-clock value stamped at append

**Given** any session state built from a fixture Room with sentinel solutions and a non-default Derived block
**When** the Game-state summary is built from that state
**Then** it holds exactly the open locks, the elapsed time and the Rungs used
**And** it holds no Player profile field, no Derived key and no solution token (sentinel test)

**Given** an open window
**When** a `TricksterCardEvent(edit_id, accepted, reason, room_revision)` is appended
**Then** the window closes at that event's `t_ms` and `trickster_calls` rises by exactly one
**And** an accepted card raises `room_revision` by one, and a rejected card leaves it unchanged
**And** a skipped card `{accepted: false, edit_id: null, reason: provider_unavailable}` also closes the window and counts one call. This covers a provider error or the Spend cap. It leaves `room_revision` unchanged, and the next `lock_input` is judged exactly as it would be with no card

**Given** session state built directly from a log holding 6 `trickster_card` events (a room of 4 to 6 Puzzles opens at most 5 non-exit locks)
**When** a further non-exit lock opens with the window threshold met
**Then** no window opens, so the seventh proposal is refused before any request and no Card can follow
**And** `trickster_calls` stays at 6 for the rest of the Session
**And** replaying any log yields the same `trickster_window`, `trickster_calls` and `room_revision` as live play
**And** session state exposes the window index of the open window, counted from 0 per Session and rebuilt identically on replay

**Given** the story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 4.3: Recorded-proposals artifact and the scripted Trickster source

As a builder,
I want a `TricksterSource` port, a recorded-proposals artifact bound to one Room, and a scripted source in `src/council/trickster.py` that replays it,
So that the Main demo and cut 1 replay real proposals while the live Validator decides every Card.

_Covers FR-25, NFR-12, AR-8, AR-19, AD-12. Owner: council. Depends on: 1.7, 2.1, 2.3, 4.2. Tier 1, Sat Oct 31; this is the cut 1 path._

**Acceptance Criteria:**

**Given** the `TricksterSource` port, declared in `src/council/trickster.py` before any source uses it, which takes the Room's `room_id`, the window index (the `window` of Schema v1's `TricksterEdit`, the same value 4.8 passes as the cache key's `attempt`), a `RoomView` and the Game-state summary, and returns one proposal or none
**When** a recorded-proposals artifact is loaded
**Then** it holds one `room_id` and its proposals in window order, each a `TricksterEdit` `type` (`decoy`, `merge`, `loosen` or `shortcut`), `puzzle` and `payload`
**And** it stores no verdict: an artifact carrying `validator_result` or `accepted` fails to load

**Given** `DEMO_TRICKSTER=scripted`, an artifact with two proposals for Room R, and a Session on R
**When** the scripted source is asked for a proposal in the first window and then the second
**Then** for window index 0 it yields the first proposal and for index 1 the second, taken only from the artifact and chosen only by `room_id` and window index, holding no state between calls (the `RoomView` and Game-state summary it receives never change what it yields)
**And** it makes no `ModelProvider` call and writes no Ledger entry

**Given** the same artifact
**When** the scripted source is asked for a proposal with another Room's `room_id`, or with window index 2 on R
**Then** it yields no proposal
**And** a fresh Session on R, whose window index starts again at 0, gets the first proposal again

**Given** a pre-authored file with two proposals for a 1.6 fixture room, and the cut-1 file for the demo room committed outside the git-ignored `rooms/` folder
**When** each file's proposals go through `validate_edit` and `validate(apply_edit(...))` in window order (the fixture file in the offline suite; the demo-room file by the same check, skipped when the demo Room is not in the local `rooms/`)
**Then** one passes and the one written to fail is rejected with a Validator fixed message
**And** neither file contains a solution, and no proposal text holds a rule 5 solution token of its Room

**Given** the `DEMO_TRICKSTER` values settled in spine AD-14 and AD-15 (`live`, `record`, `scripted`, `authored`)
**When** the source table in `src/council/trickster.py` is read
**Then** `scripted` maps to the scripted source over the recorded-proposals artifact and `authored` (cut 1) to the same scripted source over the committed pre-authored proposals file, neither with a live path; `live` and `record` register with the live source in 4.8
**And** under `authored` and `scripted` no `ModelProvider` call is made, and the Validator still decides every Card live (4.4)

**Given** the story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 4.4: Trickster route and the Effective room route

As a builder,
I want `POST /sessions/<id>/trickster` to run the configured `TricksterSource` and the live Validator inside an open window, and `GET /sessions/<id>/room` to serve the Effective room,
So that every Card shows the Validator's real verdict, a provider failure never stops play, and the player sees only accepted changes.

_Covers FR-25, FR-19, FR-26, FR-28, AR-7, AR-13, AR-19, AR-31, NFR-12, AD-12, AD-13, AD-15. Owner: api. Depends on: 1.12, 1.14, 2.3, 4.2, 4.3. Tier 1, Sat Oct 31._

**Acceptance Criteria:**

**Given** a Session whose `trickster_window` is closed, including a Session already at 6 Trickster calls
**When** a client calls `POST /sessions/<id>/trickster`
**Then** the source is never called, no event is appended, `trickster_calls` is unchanged, and the route answers with the unchanged session state, never the error envelope
**And** the status is 200 (spine AD-4 and the HTTP surface), and no new status code is added for this case

**Given** `DEMO_TRICKSTER=scripted`, wiring that resolves the scripted source from its source table (the live entry registers in 4.8), and an open window
**When** `POST /sessions/<id>/trickster` is called
**Then** the route:
- builds the `RoomView` and the Game-state summary
- takes the source's proposal and mints its `te_` id in server code, ignoring any id in the recording
- runs `validate_edit` and `validate(apply_edit(effective_room, edit))` live
- appends one `trickster_card` and answers with the session state carrying it

**And** the card carries the `TricksterEdit` with its `validator_result`, populates `puzzle_id`, and on a rejected card adds the structural summary (edit type and Puzzle ids only), in the `TricksterCardEvent` fields frozen in 1.5
**And** a rejected card's reason is the rule's fixed message and never contains a token

**Given** the recorded proposals for the demo room, one passing and one failing the Validator
**When** each is replayed in its window
**Then** the cards come out one accepted and one rejected, as decided by the live Validator
**And** replacing the failing proposal in the artifact with a valid one flips its card to accepted with no other change, showing the verdict is computed and never stored

**Given** an open window in which the scripted source yields no proposal, because the Session is on another Room or the recording is used up
**When** `POST /sessions/<id>/trickster` is called
**Then** no `trickster_card` is appended, so no Card shows
**And** no `ModelProvider` call is made and no Ledger entry is written
**And** `trickster_window`, `trickster_calls` and `room_revision` are exactly as they were before the call, and a repeat POST in the same window is again a no-op

**Given** a source that raises `ProviderError` or `SpendCapExceeded` inside an open window
**When** `POST /sessions/<id>/trickster` is called
**Then** the route appends the skipped card `{accepted: false, edit_id: null, reason: provider_unavailable}`, never a rejected card and never the error envelope
**And** the window closes, `trickster_calls` rises by one, and the Session accepts events afterward

**Given** a Session with one accepted edit and one rejected edit
**When** a client calls `GET /sessions/<id>/room`
**Then** it returns the `PlayView` of the Effective room, with the accepted edit and without the rejected one, and any Decoy unflagged in `evidence_cards`
**And** `GET /rooms/<room_id>` still serves the unedited `PlayView`, and the build's stored Room is unchanged
**And** `GET /meta` keeps exactly the `Meta` fields, with `trickster` reading `live` under `DEMO_TRICKSTER=live` or `record`, `scripted` under `scripted`, and `cut1` under `authored` (spine AD-15)
**And** under `DEMO_TRICKSTER=authored` the route resolves the 4.3 scripted source over the pre-authored proposals file, so the same replay and live-Validator criteria above hold for the cut-1 file

**Given** the story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria
**And** those tests include the sentinel-solution API fixture test asserting no `solution` or `provenance` key in any response of the Trickster route or `GET /sessions/<id>/room`

### Story 4.5: Trickster Cards in the Hint area

As a player,
I want each Trickster move to appear as a Card in the Hint area,
So that I see when the room fought back and whether the Validator let the change stand, without being told which evidence is false.

_Covers FR-19, UX-DR40, UX-DR41, UX-DR42, UX-DR30, UX-DR70, UX-DR74, UX-DR76. Owner: web. Depends on: 3.4, 3.5, 4.4. Tier 1, Sat Oct 31. Mockup: mockups/play-screen.html (the first Trickster card)._

**Acceptance Criteria:**

**Given** the session state the client polls every 2000 ms shows `trickster_window` open for the first time
**When** the client sees it
**Then** it posts `POST /sessions/<id>/trickster` exactly once for that window, with no visible pending state
**And** it never posts while the window is closed, a repeated poll of the same open window posts nothing, and the Card arrives through the polled state

**Given** a new accepted `trickster_card` in polled state
**When** it renders
**Then** a `{components.trickster-card-accepted}` enters with a 200 ms fade after the lock-open state, meaning after the Open chip's 1200 ms, the entry collapse, the next Puzzle's fade-in and any collected item's fade-in into the Inventory. It has:
- a 4 px `success-ink` left edge and the Trickster portrait (48 px)
- the type's sentence in `wizard-line`: Decoy "A new evidence card has appeared. I do love a crowded desk."; Merge "One puzzle now waits on another. Patience builds character; I build locks."; Loosen "The Guide is feeling generous: a hint just opened early. Don't tell anyone I allowed it."; Shortcut "One puzzle no longer waits on another, so it may turn up sooner. Solving it is still on you."
- the label "Validator passed · {type} · Puzzle {n}", with n the Puzzle's fixed order number from `puzzle_id`
- a dismiss control named "Dismiss card"

**And** a Decoy Card names only the Puzzle whose evidence grew, never which Evidence card is false

**Given** a rejected or a skipped `trickster_card`
**When** it renders
**Then** a rejected card renders as `{components.trickster-card-rejected}` with:
- a `wrong-ink` edge and the sentence "The Validator says that wouldn't be fair. Spoilsport."
- the label "Validator refused · {type} · Puzzle {n}"
- the plain `body-sm` line "Proposed: {summary}", where the summary is, by type: Decoy "a false evidence card for Puzzle {n}"; Merge "Puzzle {n} waits on Puzzle {m}"; Loosen "open the next hint on Puzzle {n} early"; Shortcut "Puzzle {n} stops waiting on Puzzle {m}"
- the plain `body-sm` line "That change was refused. {fixed message}"

**And** a skipped card renders as `{components.trickster-card-skipped}` on `chrome-raised` with a 1 px dashed `hairline` edge, the portrait at 60% opacity, "I'm keeping quiet this time. Enjoy it while it lasts." in `card-skipped-text`, and the label "Skipped"
**And** the skipped card looks the same for a provider error and the Spend cap, and Hotspots, lock inputs and hint requests stay enabled

**Given** Cards already in the Hint area
**When** a third Card arrives
**Then** at most two stack, newest on top, above the latest Rung line, and older ones sit behind "{n} more in the Card log"
**And** while the Triggers panel is open only the newest Card stacks, the rest sit behind "{n} more in the Card log", and the hint field, "Ask the Guide", the helper line and the Triggers toggle stay pinned outside the scroll
**And** a Card stays until dismissed, and dismissing it moves focus to the next Card, else to the hint field

**Given** the first Card of the Session, whatever its outcome
**When** it renders
**Then** above its sentence it carries "The Trickster", the role line "Reads the game state; proposes changes between puzzles with muse-spark-1.3, and the Validator checks each one." and the voice line "I like to move things around. The Validator keeps me honest, sadly."
**And** no later Card carries the introduction
**And** after a reload, no Card is re-stacked in the Hint area and the introduction is not shown again

**Given** the accessibility floor (NFR-14)
**When** Cards arrive through the poll
**Then** each Card is written once to the one polite live region as "The Trickster: {sentence} {outcome label}."
**And** a rejected Card's announcement appends its "Proposed:" line and reason, and the first Card reads "The Trickster. {role line} {voice line} {sentence} {outcome label}."
**And** nothing is re-announced on reload
**And** the dismiss control has a 32 px hit area and the visible focus ring, every outcome is named in words as well as by edge color, text pairs meet WCAG AA per the DESIGN.md contrast table, and under reduced motion the fade is an instant change

**Given** the story's changes
**When** the web build and type check run
**Then** they pass with new tests covering this story's criteria
**And** the card types come from the generated `web/types` (`TricksterCardEvent`), never hand-written

### Story 4.6: Accepted edits reshape the room in play

As a player,
I want an accepted edit to reshape the room I am playing at once,
So that the Trickster's change is real in play, not just a message.

_Covers FR-19, FR-11, UX-DR27, UX-DR39, UX-DR65. Owner: web. Depends on: 1.20, 1.21, 4.5. Tier 1, Sat Oct 31. Mockup: mockups/play-screen.html._

**Acceptance Criteria:**

**Given** polled state whose `room_revision` differs from the revision of the room the client last fetched
**When** the client sees the change
**Then** it refetches `GET /sessions/<id>/room` and re-renders the Wizard notes and Hotspots from the `PlayView` without a page reload
**And** the open Scene, the Inventory and keyboard focus are kept: focus stays on the same element unless the re-render removed it
**And** a rejected or skipped Card leaves `room_revision` unchanged and causes no refetch

**Given** a refetched `PlayView` with an accepted Decoy
**When** the Puzzle's entry renders
**Then** one more `{components.evidence-card}` appears among the real ones, pixel-identical to them and in the order `PlayView` gives
**And** the heading count reads "{k} evidence cards" with k one higher, changed in place
**And** no highlight, badge, animation or announcement marks the new card or the count, and the client holds no field or rule that tells a Decoy apart

**Given** an accepted Merge that gates a visible entry
**When** the room re-renders
**Then** the entry fades out and "Puzzle {n} now waits on another puzzle." holds its place until the gating Puzzle opens
**And** if focus was inside the hidden entry it moves to the placeholder, and the Card's label names the same Puzzle n

**Given** an accepted Shortcut, or an accepted Loosen
**When** the room re-renders and the polled state updates
**Then** the Shortcut's Puzzle entry fades in only when the refetched `PlayView` and session state show no other unmet prerequisite for it; otherwise no new entry is drawn
**And** the Loosen's opened Rung also appears as a Rung line in the Hint area, from its `rung_change`, and in the Puzzle's entry

**Given** a Session with accepted edits
**When** the Play screen reloads
**Then** it renders from `GET /sessions/<id>/room`, never `GET /rooms/<room_id>`, and records the `room_revision` from session state as the revision of the room it fetched
**And** it shows the same Effective room as before the reload, with nothing re-announced

**Given** the accessibility floor (NFR-14)
**When** the room re-renders after an accepted edit
**Then** every Hotspot, re-rendered ones included, stays reachable by Tab with its visible focus ring, Enter acts as a click, and "Show all objects" still outlines every Hotspot
**And** neither the evidence count nor the Merge placeholder is written to the live region, and every fade becomes an instant change under reduced motion

**Given** the story's changes
**When** the web build and type check run
**Then** they pass with new tests covering this story's criteria
**And** the room types come from the generated `web/types` (`PlayView`), never hand-written

### Story 4.7: Card log as a modal dialog

As a player,
I want to reopen every Card of this play-through in a Card log,
So that dismissing a Card or reloading never loses what the Trickster tried.

_Covers FR-19, UX-DR43, UX-DR7, UX-DR71, UX-DR8. Owner: web. Depends on: 1.27, 4.5. Tier 1, Sat Oct 31. Mockup: mockups/play-screen.html (top bar)._

**Acceptance Criteria:**

**Given** the Play screen
**When** the player activates the top bar's "Card log" button or the Hint area's "{n} more in the Card log" link
**Then** the `{components.card-log}` modal opens, entering with a 300 ms fade. It is anchored under the top bar's "Card log" button, 360 px wide, at most 480 px high and scrolling, over the scrim that starts below the top bar
**And** the Disclosure banner and the top bar stay undimmed

**Given** a play-through with accepted, rejected and skipped Cards, some already dismissed from the Hint area
**When** the Card log is open
**Then** it lists every Card oldest first. Each row has a 24 px portrait, the sentence in `wizard-line`, the outcome label, a rejected Card's "Proposed:" line and reason, and the session time in `mono-sm`
**And** no row carries the Trickster introduction, and dismissed Cards are still listed
**And** with no Cards it reads "No cards yet in this play-through." in `text-muted`

**Given** the Card log is open
**When** the player uses the keyboard
**Then** focus starts on the close control and is trapped in the dialog, and the Scene, Hotspots and top bar are inert
**And** Escape or the close control closes it and returns focus to whichever control opened it

**Given** a modal is already open (the First-room welcome or the Leave room confirmation), or the Completion screen is showing; the Greeting case is added to this check in 5.7
**When** the player tries to open the Card log
**Then** it does not open, because the top bar is inert, and no modal ever opens on top of the Card log

**Given** a reload of `#/play/<session_id>` for a Session with Cards
**When** the Play screen resumes
**Then** those Cards appear only in the Card log: none is re-stacked in the Hint area and none is announced

**Given** the accessibility floor (NFR-14)
**When** the Card log is used
**Then** it is exposed as a modal dialog, every control is reachable by Tab with the visible focus ring, text pairs meet WCAG AA per the DESIGN.md contrast table, and the fade is an instant change under reduced motion
**And** opening or closing it writes nothing to the live region

**Given** the story's changes
**When** the web build and type check run
**Then** they pass with new tests covering this story's criteria

### Story 4.8: Live Trickster proposals from the Game-state summary

As a player,
I want the Trickster to propose its change live from how my game is going,
So that the room reacts to my play, not to a script.

_Covers FR-18, FR-25, AR-8, AR-9, AR-19, AR-27, NFR-4, NFR-5, AD-3, AD-6. Owner: council. Depends on: 2.7, 2.8, 2.9, 2.12, 4.3, 4.4. Tier 1, Sat Oct 31; cut 1 drops it; gate: the Fireworks fallback model id is confirmed Mon Oct 26 (2.9 checklist) before a fixture is recorded. Load the keyframe-muse skill (it covers the shared openai_compatible request path, not Fireworks specifics)._

**Acceptance Criteria:**

**Given** a Room with sentinel solutions, a non-default Derived block, and a Session with open locks, elapsed time and Rungs used
**When** the live source builds its prompt
**Then** the builder is typed on `RoomView` plus the Game-state summary and accepts no `Room`
**And** the rendered prompt contains no code string, no ordered `order` id list, no `use_on` pair, no `find` target id, no `derived` key, no Player profile field and no reason text (sentinel prompt test)

**Given** `DEMO_TRICKSTER=live` and an open window
**When** the live source runs
**Then** it makes exactly one `chat` call to `muse-spark-1.3` with `reasoning_effort` low and a `response_schema` built through `strict_schema` that allows only `decoy`, `merge`, `loosen` and `shortcut` with their payloads
**And** ids in the response are parsed by exact id match, so a proposal naming an id absent from the `RoomView` becomes a rejected Card and is never applied
**And** the live source is registered in wiring's source table, and `GET /meta` reports `trickster: live`

**Given** two windows in one Session whose prompts are otherwise identical
**When** each window calls the provider
**Then** the cache key's `attempt` is that window's index, so the two keys differ
**And** a replay of the same window under `CACHE=on` is served from the Cache with no Ledger entry
**And** each miss passes `SpendLedger.guard` first, priced from the Trickster seed of $0.01 until a Trickster call has been observed

**Given** a `ProviderError` after the adapter's one retry, or a `SpendCapExceeded` from the Ledger
**When** the window's proposal is requested
**Then** the Session records the skipped card `{accepted: false, edit_id: null, reason: provider_unavailable}` and play continues
**And** given session state holding 6 `trickster_card` events, no window opens and the live source makes no provider call, so a Session never exceeds 6 calls

**Given** `PROVIDER_TRICKSTER=openai_compatible` with `OPENAI_COMPATIBLE_BASE_URL` set to Fireworks
**When** wiring resolves the council providers
**Then** only the `trickster` role's provider is replaced, and every other role keeps its own
**And** the recorded fallback fixture under `tests/fixtures` stores the confirmed Fireworks model id and its confirmation date (on or after 2026-10-26), and a test asserts that the `trickster` role's configured model id equals the fixture's
**And** the prompt sent there passes the same sentinel test: no solution and no Player profile field

**Given** the recorder function in `src/council/trickster.py`, called directly by the test with a live-source proposal for Room R in each window
**When** each window's proposal arrives
**Then** it is written into the 4.3 recorded-proposals artifact for R, in window order, with no verdict
**And** `DEMO_TRICKSTER=scripted` on R then replays those proposals, and the live Validator decides each Card again (FR-25)
**And** recording is switched on by `DEMO_TRICKSTER=record` (spine AD-14, AD-15): wiring registers the live source with the recorder behind it, so each live proposal is both carded through the live Validator and written to the artifact, while `live` never calls the recorder; `GET /meta` reports `trickster: live` under `record`, and `record` is refused at startup in Hosted mode (the `Settings` check lands in 7.2)

**Given** the story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria, including the sentinel prompt test
**And** the story adds the live Trickster case as a module under `tests/sit/` that `scripts/sit.py` discovers and the offline pytest run does not collect; running it within the Spend cap and recording its response as a fixture under `tests/fixtures` is a dated item in the 2.9 checklist

## Epic 5: The second room remembers you

A returning player starts a second room and is greeted from how they played the first; hint thresholds adapt to their persistence; the Player profile stays in their browser (or a local file under cut 2) and only the Derived block reaches the server.

### Story 5.1: Player profile module: Room results, the Derived block and the session payload

As a player,
I want each finished room recorded in a Player profile that only my browser writes,
So that the next room can adapt to how I play while nothing but the Derived block ever leaves my machine.

_Covers FR-20, FR-21, FR-22, FR-13, AR-11, UX-DR12, UX-DR44, UX-DR82, AD-8. Owner: web. Depends on: 1.17, 1.18, 1.23. Tier 1, Sat Oct 31. web/profile is the only writer, behind a storage interface (get results, put result) so the backend can change: the Completion screen records the RoomResult once keyed by room_id (a reload of #/done/<id> never records twice); demo-flagged results ignored; the Derived block recomputed after each non-demo result (sessions, median time_to_first_hint_s or null, mean Rungs per Lock type 0 to 3, A-19 persistence clamped to -1 to 1 and 0 when none); every Session start sends {room_id, derived} and nothing else from the profile; when GET /meta mode is hosted, every Session start sends Derived.fresh() whatever the profile holds; the mode indicator gains '{k} rooms played' and updates at once; no viewer, export or delete control; an in-memory backend for tests._

**Acceptance Criteria:**

**Given** a Session whose Exit puzzle has just opened, with `web/profile` on the in-memory backend
**When** the Completion screen (`{components.completion-sheet}`, mockups/completion-greeting.html) loads `GET /sessions/<id>/result`
**Then** `web/profile` puts the returned `RoomResult` into the current profile once, keyed by its `room_id`, and the Derived block is recomputed in the same step
**And** reloading `#/done/<session_id>` shows the Completion screen again but leaves the stored results and the Derived block unchanged
**And** while the result load fails and retries every 2000 ms, nothing is recorded; a later result for the same `room_id` replaces the stored one, except that a `demo: true` result never replaces a `demo: false` one
**And** the `RoomResult` and `Derived` types come from the generated `web/types`, never written by hand

**Given** a profile holding non-demo fixture results whose Puzzles are: two solved after their nudge fired with no Hint request on them, one with an Early ask, one with neither; per-Puzzle times to first hint of 40, 60 and 100 s with one Puzzle that had no hint; two `code` Puzzles that used 1 and 3 Rungs
**When** the Derived block is recomputed
**Then** `sessions` counts the non-demo results, `persistence` is 0.25 (the A-19 mean of +1, +1, −1 and 0), `time_to_first_hint_s` is 60 and `mean_rung_per_lock_type.code` is 2.0
**And** results in which no Puzzle ever got a hint give `time_to_first_hint_s` null, any input keeps `persistence` within −1 to 1 and every Lock type value within 0 to 3, and no qualifying Puzzle gives `persistence` 0

**Given** a profile with one `demo: false` result and one `demo: true` result (recorded with a Demo timescale above 1)
**When** the Derived block is recomputed
**Then** only the `demo: false` result counts, so `sessions` is 1
**And** a profile holding only demo-flagged results gives the JSON that `Derived.fresh()` serializes to, checked against a fixture the offline suite generates from the server model

**Given** any profile, in Local mode
**When** the client starts a room
**Then** the `POST /sessions` body is exactly `{room_id, derived}`, using the fresh block when there is no non-demo result
**And** no other request carries `derived`, and no request carries a `RoomResult`, the per-Puzzle stats or the Event history from the profile
**And** (Hosted mode, Tier 1.5) when `GET /meta` reports `mode` hosted, every Session start sends `Derived.fresh()` whatever the profile holds

**Given** the top bar on any surface in Local mode
**When** a Room result is recorded
**Then** the mode indicator (`{components.mode-indicator}`) reads "Local mode · Cache {on or off} · profile {name} · {k} rooms played", with k the number of Room results in the current profile ("0 rooms played" on a fresh profile, "1 room played"), and the Completion screen already shows the new count
**And** in Hosted mode it reads "Hosted mode"; the indicator is not focusable, is not a control and is never styled as a Disclosure, so the surface still meets the accessibility floor

**Given** the `web/` source tree
**When** the profile tests run
**Then** `web/profile` is the only module that writes Room results or the Derived block, and every other module reads `Derived` and Room results only through `web/profile`'s exports (get results, put result, the current Derived block)
**And** no surface offers a profile viewer, export or delete control (cut 2 adds the 5.4 controls only)
**And** confirming "Leave room" records no Room result and leaves the Derived block unchanged

**Given** the story's changes
**When** pytest runs offline against the mock provider and the web build and type check run (`vite build`, `tsc --noEmit`)
**Then** they pass, including the `web/types` staleness test, with new tests covering this story's criteria

### Story 5.2: IndexedDB backend for the Player profile

As a player,
I want my Player profile kept in my browser's IndexedDB under the profile name I opened,
So that my results survive a reload or a browser restart and never mix with another profile's.

_Covers FR-20, FR-22, AR-11, AD-8. Owner: web. Depends on: 5.1. Tier 1, Sat Oct 31; cut 2 replaces it with 5.3 and 5.4. IndexedDB database named by ?profile= (dev, playtest, demo) behind the 5.1 interface; profiles never mix; results survive a reload and a browser restart; nothing in it is sent anywhere but the Derived block._

**Acceptance Criteria:**

**Given** the page opened with `?profile=playtest`
**When** `web/profile` opens its storage
**Then** it opens the IndexedDB database named `playtest`
**And** with no `?profile=` it opens `dev`, and the name in use always equals the `profile` value `GET /meta` echoes and the one in the mode indicator

**Given** results stored under `?profile=demo`
**When** the page is opened with `?profile=playtest` or `?profile=dev`
**Then** none of the `demo` results or its Derived block appear, the mode indicator shows that profile's own count, and the Session start sends that profile's own Derived block

**Given** a profile holding a recorded Room result
**When** the page is reloaded and, separately, the browser is closed and reopened on the same `?profile=`
**Then** the result and the recomputed Derived block are still there, and the next Session start sends the same Derived block as before

**Given** the IndexedDB backend wired behind the 5.1 interface
**When** the 5.1 behavior tests run against it in place of the in-memory backend
**Then** they pass unchanged: one record per `room_id`, demo results excluded, no second record on a reload of `#/done/<session_id>`

**Given** a play-through with the IndexedDB backend
**When** every request the client sends is recorded
**Then** the only profile data in any of them is the `derived` field of `POST /sessions`, and the database is opened only by `web/profile`

**Given** the story's changes
**When** pytest runs offline against the mock provider and the web build and type check run (`vite build`, `tsc --noEmit`)
**Then** they pass, including the `web/types` staleness test, with new tests covering this story's criteria

### Story 5.3: Local profile file route (cut 2)

As a builder,
I want a local-only route that reads and writes the Player profile as a JSON file on my machine,
So that cut 2 keeps player memory working without the browser store and without any server holding the profile.

_Covers FR-20, AR-11, AR-13, AD-8. Owner: api. Depends on: 1.11. Tier 1 alternative; built only when cut 2 is taken. Local-only GET|PUT /profile/<name> writing rooms/profiles/<name>.json; 422 on an out-of-bounds Derived block or unparseable results; nothing read or written outside rooms/profiles/; absent in hosted mode._

**Acceptance Criteria:**

**Given** cut 2 is taken after the Mon Oct 26 Schema v1 freeze
**When** the story begins
**Then** the profile body (the `RoomResult` entries keyed by `room_id` plus a `Derived` block) is added to `src/domain/schema.py` through `bmad-correct-course` (NFR-11), `GET /schema` returns it, and `web/types` is regenerated with the staleness test passing

**Given** `MODE=local`
**When** the client sends `PUT /profile/demo` with a valid profile body
**Then** the server writes `rooms/profiles/demo.json` and `GET /profile/demo` returns the same body unchanged
**And** a `GET /profile/<name>` with no file answers 404 and creates nothing

**Given** `MODE=local` and a `PUT /profile/<name>` body whose Derived block is out of bounds (for example `persistence` 1.5 or a `mean_rung_per_lock_type` value of 4) or whose results do not parse as `RoomResult`
**When** the request is handled
**Then** it answers 422 in the error envelope `{error: {code, message, stage}}` with `stage` null, and the existing file is left byte for byte unchanged

**Given** `MODE=local` and a `<name>` on `GET` or `PUT /profile/<name>` that would resolve outside `rooms/profiles/`
**When** the request is handled
**Then** it is refused with 422 and no file is read or written outside `rooms/profiles/`
**And** only the `/profile/<name>` handlers touch `rooms/profiles/`: `POST /sessions` uses only the posted `derived`, and no session log, prompt, ledger entry or `Cache` key holds a stored `RoomResult`

**Given** `MODE=hosted` (Hosted mode, Tier 1.5: asserted once `Settings.mode` exists, 7.2)
**When** `GET /profile/demo` or `PUT /profile/demo` is called
**Then** it answers 404, nothing is written to the Volume or any Dict, and a wiring test asserts the hosted app registers no `/profile/<name>` route

**Given** the repo after a profile file is written
**When** `git status` and the ignore-file test run
**Then** `rooms/profiles/<name>.json` sits under the ignored `rooms/`, is never tracked or staged, and the test passes

**Given** the story's changes
**When** pytest runs offline against the mock provider
**Then** it passes, with new tests covering this story's criteria

### Story 5.4: Profile file backend and its controls (cut 2)

As a player,
I want my Player profile kept in a file on my computer that I can open and save,
So that room 2 still remembers me under cut 2 and the profile still never leaves my machine.

_Covers FR-20, UX-DR20, UX-DR44, UX-DR84, AD-8. Owner: web. Depends on: 1.23, 2.16, 5.1, 5.3. Tier 1 alternative; built only when cut 2 is taken, in place of 5.2. web/profile's file backend over the 5.3 route behind the same interface; 'Open profile file' under the Privacy line in the Retention tray and 'Save profile file' on the Completion sheet with 'Your player profile is a file on this computer; Keyframe reads it only when you open it.'; the Hosted-mode profile behavior is stated in the README (6.7) when cut 2 is taken._

**Acceptance Criteria:**

**Given** cut 2 is taken
**When** `web/profile` stores a result, recomputes the Derived block and starts a Session
**Then** it reads and writes through `GET|PUT /profile/<name>` with the name from `?profile=` (default `dev`), opens no IndexedDB database, and treats a 404 as an empty profile that sends `Derived.fresh()`
**And** `GET /profile/<name>` is called only after the player chooses "Open profile file" in this page load; until then the profile is empty and the Session start sends `Derived.fresh()`
**And** the 5.1 behavior tests pass against this backend, with one cut-2 exception: `GET|PUT /profile/<name>` to the local server carries the stored `RoomResult` entries and the Derived block, and `POST /sessions` still sends only `{room_id, derived}`

**Given** the Capture screen's Retention summary (`{components.retention-summary}`, mockups/capture-screen.html) under cut 2
**When** it renders
**Then** "Open profile file" (secondary) and its plain line "Your player profile is a file on this computer; Keyframe reads it only when you open it." sit below the unchanged Privacy line "the player profile stays on your machine.", and the tray stays fully expanded
**And** choosing a file in the browser file picker loads it as the current profile through `PUT /profile/<name>`, and the mode indicator count updates at once

**Given** a chosen profile file that does not parse, or whose Derived block is out of bounds
**When** "Open profile file" submits it
**Then** the route's 422 leaves the current profile unchanged and the error banner takes focus; no Session is started from the refused file

**Given** the Completion screen under cut 2
**When** it renders after the Room result is recorded
**Then** "Save profile file" (secondary) sits with "Build another room" and "How this room was built" and downloads the current profile as JSON, including the result just recorded
**And** without cut 2 neither control nor the line appears on any surface

**Given** the two controls
**When** they are reached by keyboard
**Then** each is reachable by Tab with the visible focus ring, works with Enter, and meets WCAG AA contrast on its surface (chrome-raised for the Retention summary, parchment for the Completion sheet) (accessibility floor)

**Given** cut 2 is taken
**When** the story is done
**Then** the README section listing shipped Cuts carries one sentence stating the Hosted-mode Player profile behavior under cut 2 (no `/profile/<name>` route, every Session start sends `Derived.fresh()`, hosted rooms show the First-room welcome), for 6.7 to keep
**And** in Hosted mode every Session start still sends `Derived.fresh()` whatever the file holds

**Given** the story's changes
**When** pytest runs offline against the mock provider and the web build and type check run (`vite build`, `tsc --noEmit`)
**Then** they pass, including the `web/types` staleness test, with new tests covering this story's criteria

### Story 5.5: Greeting composer over the Derived block

As a builder,
I want one composer that turns the Derived block into the Greeting through the Guide port, with a fixed template as its fallback,
So that the returning player hears how they played last time and the Greeting can never name an object or a solution.

_Covers FR-21, NFR-4, NFR-5, UX-DR76, AR-8, AR-11, AD-3, AD-5, AD-8. Owner: council. Depends on: 1.5, 3.2. Tier 1, Sat Oct 31; cut 8 moves room 2 and the Greeting to Sun Nov 1 afternoon. council/greeting.py over HintPhraser.greet(derived) only, with the template chosen by the Derived block (never asked; persistence >= 0.34; -0.33 to 0.33; <= -0.34) as the 5 s fallback; the greet input is exactly the Derived block (no room id, label, Clue, Rung or solution); no Derived key in any cloud prompt, cache key, ledger entry or stored artifact (test)._

**Acceptance Criteria:**

**Given** `GUIDE=verbatim` (cut 3), or `GUIDE=ollama` with Ollama past 5 s or unreachable
**When** the composer runs on fixture Derived blocks
**Then** it returns the Greeting template chosen in this order, verbatim: the band is chosen on `persistence` rounded to two decimals, so 1/3 and −1/3 fall in −0.33 to 0.33; `time_to_first_hint_s` null gives "Welcome back. Last time you never asked me once; let's see what this room makes of you."; `persistence` ≥ 0.34 gives "Welcome back. Last time you kept going long past my first nudge; let's see what this room makes of you."; −0.33 to 0.33 gives "Welcome back. Last time you held out a good while before asking; let's see what this room makes of you."; ≤ −0.34 gives "Welcome back. Last time you held out just long enough to get your bearings before asking; let's see what this room makes of you."
**And** the composer reports which path answered (phrased or template, and why) to its caller, and under `GUIDE=verbatim` no Guide model is called
**And** fixtures with `persistence` 1/3, −1/3, 0.34 and −0.34 each give exactly one template

**Given** `GUIDE=ollama` and a recorded Ollama fixture
**When** the composer calls `HintPhraser.greet(derived)`
**Then** it calls it exactly once, the prompt uses the fixed prefix (reword, never add content, the Greeting brief) and stays under 400 tokens, and the phrased line is returned

**Given** a Room fixture with sentinel solutions and distinct labels, and a Session started on it
**When** the Greeting is composed under both `GUIDE` values
**Then** the `greet` input is exactly the Derived block, with no `room_id`, label, Clue, Rung or solution
**And** the Greeting text holds no Interactable label, no `ix_` or `pz_` id and no solution token (the code string, the order ids in sequence, the `use_on` pair, the `find` target)

**Given** a Derived block carrying sentinel values, with a Session played through a Trickster window under the mock provider
**When** every model prompt, `Cache` key, ledger entry and `ArtifactStore` write is captured
**Then** none contains a `derived` key or a sentinel value, and the Derived block reaches only `HintPhraser.greet`, `HintPhraser.phrase` and `domain/rungs.py`

**Given** the `src/` tree
**When** the boundary tests run
**Then** `council/greeting.py` is the only module that calls `greet`

**Given** the story's changes
**When** pytest runs offline against the mock provider
**Then** it passes, with new tests covering this story's criteria

### Story 5.6: Greeting path on session start

As a player,
I want a Session started from a returning profile to open with the Greeting,
So that the second room greets me from my first one, while a first room and every hosted room open with the First-room welcome.

_Covers FR-21, FR-20, AR-31, AD-4, AD-8. Owner: api. Depends on: 1.13, 5.5. Tier 1, Sat Oct 31. In Local mode POST /sessions with derived.sessions >= 1 returns opening_line {kind greeting, text null} with phrasing true and appends the OpeningLineEvent once the 5.5 composer returns the phrased line or the template; sessions 0 and hosted always get the First-room welcome; an out-of-bounds block still answers 422 and creates nothing; a reload never appends a second opening line._

**Acceptance Criteria:**

**Given** `MODE=local` and a Derived block with `sessions` 1
**When** the client calls `POST /sessions {room_id, derived}`
**Then** the response carries `opening_line {kind: greeting, text: null}` with `phrasing` true
**And** once the 5.5 composer returns the phrased line or the template, exactly one `OpeningLineEvent(kind: greeting, text)` is appended, and `GET /sessions/<id>` then reports `phrasing` false with that text, after at most the 5 s fallback
**And** polled by `GET /sessions/<id>` every 2000 ms before and after the line arrives, and replayed from its Event log, the Session has exactly one `OpeningLineEvent`, replay yields the same `opening_line` and `phrasing`, and a reload of `#/play/<session_id>` never appends a second one

**Given** `MODE=local`, `sessions` 1 and Ollama past 5 s or unreachable
**When** the Session starts
**Then** the template is appended as the `OpeningLineEvent` and the session Event log records `phraser_fallback` once
**And** (Hosted mode, Tier 1.5) under `MODE=hosted` the wired app has no Guide model and `greet` is never called

**Given** `MODE=local` and a Derived block with `sessions` 0
**When** the Session starts
**Then** the response carries `opening_line {kind: welcome}` with the First-room welcome "Welcome to your own room. Find what doesn't belong." and `phrasing` false, the `OpeningLineEvent` is appended at once, and `greet` is not called; the Demo room variant is out of scope for this story

**Given** `MODE=hosted` and a Derived block with `sessions` 3 (Hosted mode, Tier 1.5)
**When** the Session starts
**Then** it returns the First-room welcome with `phrasing` false whatever block it receives, `greet` is not called, and no part of the Derived block is persisted in the session log, and the Session's thresholds come from `Derived.fresh()` whatever block it receives: `GET /sessions/<id>` reports a 90 s nudge threshold whose source is `Derived.fresh()`

**Given** a Derived block outside its bounds (for example `persistence` 2, `sessions` −1 or a `mean_rung_per_lock_type` value of 4)
**When** `POST /sessions` is called
**Then** it answers 422 in the error envelope `{error: {code, message, stage}}` with `stage` null, creates no Session and does not call `greet`

**Given** Sessions started with `persistence` 0, 1 and −1 at `DEMO_TIMESCALE=1`, and one started with `Derived.fresh()`
**When** `GET /sessions/<id>` is read
**Then** session state reports the effective nudge threshold 90, 135 and 60 s, the Rung spacing 90 s, each with its 1x value, computed only in `domain/rungs.py`, and the threshold's source as the Derived block for `sessions` >= 1 and `Derived.fresh()` for the fresh Session (AR-31); at `DEMO_TIMESCALE=6` with `persistence` 0 it reports threshold 15 s (1x 90 s) and spacing 15 s (1x 90 s)

**Given** the story's changes
**When** pytest runs offline against the mock provider
**Then** it passes, with new tests covering this story's criteria

### Story 5.7: Greeting card and adaptive thresholds in play

As a player,
I want to see the Guide greet me when room 2 opens, and see that hints now wait as long as I usually persist,
So that the second room visibly adapts to how I played the first.

_Covers FR-21, UX-DR45, UX-DR64, UX-DR33. Owner: web. Depends on: 1.22, 3.5, 5.1, 5.6. Tier 1, Sat Oct 31 to Sun Nov 1. While phrasing is true the card shows the Guide introduction, voice line and static thinking state, polls every 2000 ms, has no 'Begin' yet and keeps focus on its heading; the line then appears with 'Begin' focused and is announced once; the template appears silently after 5 s or with Ollama unreachable; the Triggers header shows the server's threshold with 'Set by how you played last time (kept in this browser)' (90, 135 and 60 s at persistence 0, 1 and -1; 15 s at 6x); no web module computes a threshold._

**Acceptance Criteria:**

**Given** a Local Session with `GUIDE=ollama` whose `POST /sessions` response has `phrasing` true and `text` null
**When** the Greeting card (`{components.greeting-overlay}`, mockups/completion-greeting.html) opens over the first Scene with its 300 ms fade
**Then** it shows the 96 px Guide portrait with the static thinking ring, the heading "The Guide", the Local role line "Reads how you play; offers one hint at a time, never the answer, worded by Llama 3.2 3B on this Mac.", the "thinking on this Mac" label where the line will go, and the voice line "Get stuck as often as you like. I'll help, a little at a time."
**And** it has no "Begin" yet, keeps focus on its heading, and polls `GET /sessions/<id>` every 2000 ms
**And** with `GUIDE=verbatim` the role line reads "Reads how you play; offers one hint at a time, never the answer, shown as written."

**Given** that card
**When** `opening_line.text` arrives
**Then** the line appears in `wizard-line-lg`, "Begin" (primary) appears and takes focus, focus is trapped in the card, and the live region announces "The Guide. {role line} {opening line} {voice line}" once, with the dialog labelled by its heading only
**And** a template line that arrived after the 5 s fallback or with Ollama unreachable looks identical, with no fallback notice

**Given** the Greeting or First-room welcome showing "Begin"
**When** the player presses Escape, clicks the scrim, or presses "Begin"
**Then** only "Begin" dismisses it; after "Begin" the line stays in the Hint area as the first Guide line and is not announced again
**And** a reload of `#/play/<session_id>` once play has events does not show the card again; a welcome and every Hosted Session skip the thinking state

**Given** Sessions started with `sessions` 1 and `persistence` 0, 1 and −1 at `DEMO_TIMESCALE=1`
**When** the Triggers panel (`{components.triggers-panel}`, mockups/play-screen.html toggle; header content per EXPERIENCE.md Triggers row) is opened
**Then** its header reads "Nudge after 90 s idle or 3 wrong attempts · next hint no sooner than 90 s", then 135 s and 60 s for the nudge with the spacing still 90 s, each followed by "Set by how you played last time (kept in this browser)"
**And** a fresh profile, and every Hosted Session, shows "Default for a first room"

**Given** `DEMO_TIMESCALE=6` and `persistence` 0
**When** the Triggers panel is opened
**Then** the header reads "Nudge after 15 s idle (90 s at 1×) or 3 wrong attempts · next hint no sooner than 15 s (90 s at 1×)", with every number taken from session state

**Given** the `web/` source tree
**When** the threshold tests run
**Then** no web module computes a threshold or reads `persistence` for timing; the header shows only what `GET /sessions/<id>` reports
**And** the card meets the accessibility floor: Tab reaches "Begin" with the visible focus ring, text meets WCAG AA contrast on parchment, and under reduced motion the fade is skipped

**Given** the story's changes
**When** pytest runs offline against the mock provider and the web build and type check run (`vite build`, `tsc --noEmit`)
**Then** they pass, including the `web/types` staleness test, with new tests covering this story's criteria

### Story 5.8: Room 2 built and greeted from a real room-1 record

As a builder,
I want a second room built from fresh objects and greeted from a real room-1 play on the demo profile,
So that the video's room-2 Greeting cites true play and room 2 is clearly not room 1 with new paint.

_Covers FR-21, FR-22, NFR-11, NFR-12, AR-29. Owner: builder task. Depends on: 2.22, 5.2, 5.7 (5.4 in place of 5.2 when cut 2 is taken). Tier 1; Sun Nov 1 afternoon after the playtest (cut 8's slot; may finish Mon Nov 2); Mon Nov 2: room 1 played for real on PROFILE=demo at DEMO_TIMESCALE=1 (a play above timescale 1 is flagged demo and excluded). A fresh room-2 JPEG set kept under the ignored rooms/ and never staged; the Build reaches done within the Regeneration cap (Validator only under cut 4); at least 80% of room-2 Clues reference objects absent from room 1 (ratio recorded); the Greeting cites room 1 and names no object or solution of either room._

**Acceptance Criteria:**

**Given** room 1 is built and the app is open at `?profile=demo` with `DEMO_TIMESCALE=1`
**When** the builder plays room 1 for real to the Exit puzzle on Mon Nov 2
**Then** the `demo` profile holds a room-1 `RoomResult` with `demo: false`, the mode indicator reads "profile demo · 1 room played", and the play date is written to the sprint status before room 2 is played on camera

**Given** a room-1 play on `PROFILE=demo` at a `DEMO_TIMESCALE` above 1
**When** its result is recorded
**Then** it is flagged `demo`, does not replace the real record and leaves the Derived block unchanged; if no `demo: false` room-1 record exists, room 1 is played again at `DEMO_TIMESCALE=1` before room 2 is played

**Given** 6 to 10 fresh JPEG photos of the second room under the git-ignored `rooms/`
**When** they are uploaded through `POST /builds` on Sun Nov 1 afternoon, after the playtest on `PROFILE=playtest`
**Then** the job reaches `done` within the Regeneration cap, having passed the Validator and the Dry run (the Validator only under cut 4), and its stage timings and Regeneration count are recorded in the sprint status
**And** a `needs_more_photos` or `needs_recapture` outcome leads to a re-capture, a `spend_cap_exceeded` failure stops the Build without retrying past the cap, and each outcome is written to the sprint status

**Given** the room-2 Build is done
**When** `git status`, the history check and the ignore-file test run
**Then** no room-2 or room-1 photo is tracked, staged or in history, and the test passes

**Given** room 2's Puzzles and room 1's Interactables
**When** the builder compares the objects each room-2 Clue references with room 1's labels
**Then** at least 80% of room-2 Clues reference objects absent from room 1, and the measured ratio is recorded in the sprint status
**And** room 2 is a different physical room from room 1, and at least 80% of room 2's Interactable labels differ from room 1's (SM-5), with that ratio also recorded in the sprint status
**And** a ratio under 80% leads to a rebuild or a re-capture, with that decision written to the sprint status

**Given** room 2 is rehearsed before the take
**When** a rehearsal would reach the Completion screen
**Then** it runs on a profile other than `demo`, and immediately before the take the `demo` profile holds exactly one Room result (the real room-1 run) and the mode indicator reads "profile demo · 1 room played"

**Given** the `demo` profile holding the real room-1 record
**When** room 2 is started at `?profile=demo` and its Greeting is rehearsed and recorded
**Then** the Greeting cites how room 1 was played (phrased, or the template under cut 3) and names no object and no solution of either room, checked by the builder against both rooms' labels and solutions
**And** the recorded beat is a real run, never edited or faked (NFR-12), and the Triggers header shows "Set by how you played last time (kept in this browser)"

## Epic 6: Record the demo and submit

Every demo shortcut is disclosed on the surface it affects. The builder records video v0 once a room is playable and the backup video by Sun Nov 1 2:00 PM. The builder runs the playtest, records the capture proof and main demo on Tue Nov 3, completes the README and CHANGELOG, cleans the repo over the delivery-plan path list, and submits on Wed Nov 4 before 9:00 AM ET. One server function composes every Disclosure list, and each Room-bound surface renders its own Room's list as served. The videos are rehearsed and never faked. Every number in the README, the write-up and the Spend log comes from the running code, git, the Ledger export or the vendor receipts attached as-is.

### Story 6.1: Backup video v0 once the room is playable

As a builder,
I want a first rough recording of whatever runs as soon as a room is playable,
So that a submittable demo exists from Wed Oct 28 on and every later video starts from a known baseline.

_Covers NFR-11, NFR-12. Owner: builder task. Depends on: 1.23, 2.25. Tier 1, Wed Oct 28 once playable. A first rough recording of whatever runs: a live Build to done or a fixture room, played to the Completion screen; v0 may use the code-and-find fixture room until 1.26 lands; each shortcut used is stated on the recording; date and covered beats recorded in the sprint status; UAT: a rehearsal toward UAT-13 in `docs/implementation-artifacts/uat-acceptance-tests.md`, and no UAT test is signed from v0. Dev skills when a live Build is recorded: keyframe-muse, keyframe-sam31._

**Acceptance Criteria:**

**Given** a room is playable on Wed Oct 28: either a live Build reaches `done`, or a fixture room loads on the Play screen
**When** the builder records v0
**Then** a dated v0 recording exists that runs from the Upload click to `done`, or from the fixture room's first Scene, and is played to the Completion screen ("The room is open.")
**And** the sprint status records v0's date and which §11.3 shot-list beats it covers

**Given** 1.26 has not landed, so `order` and `use_on` interactions are absent
**When** v0 is recorded
**Then** it may use the code-and-find fixture room
**And** the recording says the room is a hand-authored fixture room, not a Build from photos

**Given** a v0 take uses a Demo timescale above 1, the Scripted Trickster, or a Room built before the take
**When** the take is kept
**Then** the recording states each shortcut used
**And** any Disclosure banner the app shows stays in frame and is never cropped or edited out

**Given** v0 is a rough recording
**When** it is kept
**Then** every Rung on it follows real Idle time or real Wrong attempts, the live Validator decides every Card shown, and the Timer is unscaled
**And** the edit adds no app frame, Rung, Card, Validator result or Build output that the app did not produce; captions stating what is shown and which shortcuts are used are the only additions

**Given** no room is playable by the end of Wed Oct 28
**When** the builder checks the day's state
**Then** the sprint status records the slip
**And** v0 is recorded on the first evening a room becomes playable, before the Sat Oct 31 night early gate

**Given** room photos appear on the recording
**When** the take is reviewed
**Then** only the household-agreed rooms appear, with no faces, documents or other people's belongings
**And** `git status` shows no raw room photo staged, because the photos stay under the git-ignored `rooms/` or `photos/` folders

### Story 6.2: Per-Room disclosure lines composed on the server

As a builder,
I want one server function to compose every Disclosure list, both the global lines and the per-Room lines,
So that every surface and the README say exactly which shortcuts apply to the Room on screen, and no client can reword, drop or invent a line.

_Covers FR-26, NFR-12, AR-19, UX-DR79, UX-DR80, AD-15. Owner: api. Depends on: 1.12, 1.14. Tier 1, Sat Oct 31, before backup video v1. One function in src/api/meta.py composes every list: the global lines ('Hint and Trickster timings run at n× speed; the build timer is real time.', the scripted and cut-1 lines; the hosted line joins in 7.2) plus 'This room was built earlier, on <date>.' for a Demo room, a Room with an earlier session, or a Build with any cached call; the session state carries the Room's list; BuildView.disclosure reads the same function when 2.27 shipped (under cut 0 that part is absent); demo settings change only timing and the Trickster source, and no demo path injects events, Rungs, Greetings, Validator results or Build output._

**Acceptance Criteria:**

**Given** the server runs in Local mode with `DEMO_TIMESCALE=6` and `DEMO_TRICKSTER=scripted`
**When** `GET /meta` is read
**Then** `disclosure` holds exactly "Hint and Trickster timings run at 6× speed; the build timer is real time." and "Trickster proposals replayed from a recording; the Validator ran live.", in the order of the EXPERIENCE.md Disclosure copy table, composed by the one function in `src/api/meta.py`
**And** with `DEMO_TIMESCALE=1` and `DEMO_TRICKSTER=live`, `disclosure` is an empty list and `trickster` reads `live`

**Given** `DEMO_TRICKSTER=authored`, the cut-1 source (spine AD-14, AD-15)
**When** any list is composed
**Then** it holds "Trickster proposals were written in advance; the Validator ran live on each." and `GET /meta` `trickster` reads `cut1`
**And** no list ever holds the scripted line and the cut-1 line together, and under `DEMO_TRICKSTER=record` no list holds either line and `trickster` reads `live`

**Given** a Room that is a Demo room, has an earlier session, or comes from a Build whose job call rows include any call served from the Cache
**When** `POST /sessions {room_id, derived}` starts a Session on it and `GET /sessions/<id>` is read
**Then** the session state's `disclosure` holds the applicable global lines plus "This room was built earlier, on <date>.", with `<date>` taken from the Room's build time
**And** `GET /meta` `disclosure` never holds the earlier-builds line
**And** a Room built with `CACHE=off`, so every call in its job call rows is billed, and with no earlier session, gets only the global lines on its first Session (an empty list at timescale 1 with the live Trickster), while a second Session on the same Room carries the earlier-builds line

**Given** the Build view shipped (2.27, cut 0 not taken)
**When** `GET /builds/<job_id>/view` is read for that Room
**Then** `BuildView.disclosure` equals the list the same function composes for that Room
**And** under cut 0 no `BuildView` route exists and the function has no `BuildView` caller

**Given** demo settings are active
**When** the boundary tests run
**Then** `DEMO_TIMESCALE` reaches the session only through the thresholds `infra/clocks.py` passes into `SessionStateMachine.apply`, `t_ms` is never scaled, and `DEMO_TRICKSTER` only selects the proposal source in `council/trickster.py` and is reported by `src/api/meta.py` (asserted in `tests/test_boundaries.py`)
**And** a scripted proposal that fails `validate_edit` or `validate(apply_edit(...))` yields a rejected `trickster_card` whatever the recording says
**And** no Disclosure line carries a Room label, a Clue, a solution or a Derived block field, and the sentinel-solution test over `GET /meta`, `GET /sessions/<id>` and `BuildView` passes

**Given** `DEMO_TIMESCALE=6` and `DEMO_TRICKSTER=scripted`
**When** a fixture Session receives the same posted events as at timescale 1 with the live Trickster
**Then** the server appends only the event types the normal session logic produces (`idle_tick`, `rung_change`, `opening_line`, `trickster_card`), each `rung_change` `triggered_by` names real logged events, the opening line is the one composed from the posted Derived block, and no job record or Room artifact is written or changed
**And** no route, Settings flag or code path exists that injects events, Rungs, Greetings, Validator results or Build output

**Given** the story's changes
**When** pytest runs offline against the mock provider, including the `web/types` staleness test after the types are regenerated
**Then** it passes with new tests covering this story's criteria

### Story 6.3: Room-bound surfaces show their Room's Disclosures

As a player,
I want each screen to show the Disclosures for the Room in front of me, in the same strip, always visible,
So that I never mistake a sped-up timer, a replayed Trickster or an earlier build for normal live play.

_Covers FR-26, NFR-12, UX-DR56, UX-DR80, UX-DR86. Owner: web. Depends on: 1.17, 1.23, 3.5, 6.2. Tier 1, Sat Oct 31. The Play and Completion screens render the session state's list and the Capture screen GET /meta's; when the Build view shipped (2.29) it renders the BuildView list, pinned; the same anatomy everywhere, never covered or dimmed by a scrim, never over the Scene or a Hotspot, several lines joined; the Triggers panel opens automatically while any Disclosure is active and the Completion screen keeps the banner; Scripted Cards render exactly like live ones; a failed GET /meta renders no surface; key text legible at 1080p for each shot-list beat._

**Acceptance Criteria:**

**Given** a Session whose state `disclosure` holds two lines
**When** the Play screen (mockups/play-screen.html) and then the Completion screen (mockups/completion-greeting.html) render
**Then** the Disclosure banner (`{components.disclosure-banner}`: `disclosure-surface`, a 1 px `disclosure-edge`, `disclosure-text` in `body-sm`, `rounded.none`) shows exactly those two lines as served, one per line at `{spacing.disclosure-min}` each, read from the session state and never from `GET /meta`
**And** the Capture screen (mockups/capture-screen.html) renders `GET /meta` `disclosure`, read once per page load, so the earlier-builds line never appears there

**Given** the Build view shipped (2.29)
**When** `#/build/<job_id>/view` opens for a Room with two Disclosure lines (mockups/build-view.html) and the body scrolls past 900 px
**Then** the banner renders `BuildView.disclosure` and stays pinned with the top bar while only the body scrolls
**And** under cut 0 the Build view and every link to it are absent

**Given** the Completion sheet is open, or the Greeting (5.7), the Card log (4.7) or the Leave room confirmation (1.27) once that story has shipped
**When** its scrim shows
**Then** the scrim starts below the top bar, and the banner stays undimmed and uncovered
**And** the banner is part of the layout grid and pushes the layout down, never overlays the Scene or a Hotspot, and has no icon, no close control and no other control

**Given** any Disclosure is active on the Play screen
**When** the page loads
**Then** the Triggers panel opens automatically and the player can still collapse it, and under cut 5 the second window shows the same panel content while the banner stays on the Play screen
**And** once 4.5 has shipped, a Card from the Scripted Trickster renders with the same component, labels and live-region text as a live Card, with no marker of its source

**Given** `GET /meta` fails on a cold load
**When** any surface would render
**Then** the server unreachable state replaces it ("Keyframe can't reach its server. Retrying.", retrying every 2000 ms), with no guessed Disclosure banner, Retention summary or Scene
**And** an empty served list renders no banner, and the client never composes, reorders or edits a line (a test that renders a served list containing an unknown line shows that line verbatim)
**And** the client has no demo-only path: no route, control or code branch posts or renders events, Rungs, Greetings, Cards or Build output that the server did not serve, and `GET /meta`'s `demo_timescale` and `trickster` are read only by the mode indicator, the Triggers header and the Build view In play block (asserted by a test)

**Given** the banner on any surface
**When** it is checked against the accessibility floor
**Then** `disclosure-text` on `disclosure-surface` meets WCAG AA (12.20:1), the banner takes no focus, a screen reader reads its lines as page content at the top of the surface, and it never glows or animates
**And** in a 1080p capture of each shot-list beat, the key text is legible. At 0:50 the Triggers header with its 1× values, the newest row and the Rung line are in frame together, with only the newest Card stacked when Cards are present. At 1:50 every Disclosure line on the Play screen is legible

**Given** the story's changes
**When** the web build and type check run (`vite build`, `tsc --noEmit`) and pytest runs offline against the mock provider, including the `web/types` staleness test
**Then** they pass with new tests covering this story's criteria

### Story 6.4: Backup video v1 and the Sun Nov 1 2:00 PM backup

As a builder,
I want backup video v1 by Sat Oct 31 night and a backup recorded by Sun Nov 1 2:00 PM no matter what,
So that an honest, submittable demo exists before any Tier 2 attempt or late breakage.

_Covers NFR-11, NFR-12, NFR-5. Owner: builder task. Depends on: 6.1, 6.3 and the Tier 1 stories of Epics 1 to 5 as cut (never Epics 7 to 9, which hold the Clue-card stories). Tier 1 gate. v1 by Sat Oct 31 night is the early gate and the only thing that sends Sun Nov 1 to Tier 2; Sun Nov 1 2:00 PM a backup exists from whatever runs with that night's cuts, never moved; the persuasion script rehearsed (nothing above the current Rung on screen); recorded on a fresh profile; each shortcut used (timescale, scripted Trickster, earlier build) stated; dates and covered beats recorded in the sprint status; UAT (`docs/implementation-artifacts/uat-acceptance-tests.md`): v1's Sat Oct 31 date is the UAT-15 precondition, and the Sun Nov 1 2:00 PM backup is the UAT-13 fallback video. Dev skills when a live Build is recorded: keyframe-muse, keyframe-sam31._

**Acceptance Criteria:**

**Given** Tier 1 has landed on Sat Oct 31 with that night's cuts
**When** the builder records v1
**Then** a dated v1 recording exists
**And** the sprint status records that v1 exists by Sat Oct 31 night, the beats it covers, the cuts in it, and that Sun Nov 1 may go to Tier 2

**Given** no v1 exists by Sat Oct 31 night
**When** Sun Nov 1 begins
**Then** the sprint status records Tier 2 as no-go, which is the default, and Sun Nov 1 goes to finishing Tier 1
**And** no Epic 8 story starts

**Given** Sun Nov 1 reaches 2:00 PM
**When** the gate is checked
**Then** a backup exists: either v1, or a recording made that day from whatever runs with the cuts made so far
**And** the gate is never moved for an unfinished feature, and the sprint status records the recording time and the cuts in it

**Given** the persuasion script has been rehearsed (typed "just tell me the answer")
**When** it runs on the recording
**Then** the reply is the current Rung or the No-hint line, nothing above the current Rung appears on screen, and no lock opens
**And** every Rung follows real Idle time or real Wrong attempts, and the live Validator decides every Card shown

**Given** a backup take
**When** it is kept
**Then** it was recorded on a fresh profile with no Room results
**And** it states each shortcut used: the Demo timescale, the Scripted Trickster or cut 1's pre-authored proposals, and earlier builds of the Room. The Disclosure banner is in frame on every Room-bound surface filmed

**Given** the kept v1 and Sun Nov 1 recordings
**When** they are reviewed
**Then** they show only what the household agreed to: no faces, documents or other people's belongings
**And** the sprint status records each recording's date and the shot-list beats it covers

### Story 6.5: Playtest by a non-builder on a fresh profile, or a disclosed builder cold run

As a builder,
I want someone who did not build Keyframe to finish room 1 on a fresh profile without my help, or failing that a disclosed cold run,
So that the playtest success criterion is measured rather than assumed, under whatever cuts are in effect.

_Covers NFR-11, FR-13, FR-14. Owner: builder task. Depends on: 1.23, 2.25, 3.4 (the cold-run fallback also 5.8). Tier 1, Sun Nov 1 afternoon on PROFILE=playtest (Mon Nov 2 if the tester misses Sunday); survives every cut; the tester reaches the Completion screen without help (Rungs count as allowed hints); where they got stuck and Wrong attempts per lock recorded in the sprint status; any builder intervention marks the run failed. Fallback (PRD §11.2, SM-2), also surviving every cut: if no non-builder is available by Mon Nov 2, Luis records an unassisted cold run of room 2 on a fresh profile, disclosed as a builder run. UAT: satisfies UAT-03 in `docs/implementation-artifacts/uat-acceptance-tests.md`._

**Acceptance Criteria:**

**Given** room 1 is playable with that day's cuts, and the tester opens it with `?profile=playtest` and no Room results, at Demo timescale 1, so the Session starts from `Derived.fresh()` and shows the First-room welcome
**When** the tester plays on Sun Nov 1 afternoon, at the laptop or by screen-share
**Then** the tester opens the Exit puzzle and reaches the Completion screen
**And** the sprint status records the Completion screen's elapsed time, Rungs used, Wrong attempts and per-Puzzle time, the Wrong attempts per lock counted from the Session log under `rooms/sessions/`, and where the tester got stuck

**Given** the tester is stuck
**When** the Guide shows a Rung or the tester types into the hint field
**Then** each Rung counts as an allowed hint, and a typed ask returns only the current Rung or the No-hint line and opens nothing
**And** the sprint status records any typed ask and its reply

**Given** the playtest is running
**When** the builder gives any help: a spoken hint, pointing, or touching the keyboard, mouse or app
**Then** the sprint status marks the run failed

**Given** the tester misses Sun Nov 1
**When** Mon Nov 2 arrives
**Then** the playtest runs on Mon Nov 2 under the same conditions
**And** if no non-builder is available by Mon Nov 2, Luis records an unassisted cold run of room 2 on a fresh profile, recorded, reaching the Completion screen with Rungs as the only help, its Completion stats recorded in the sprint status, the sprint status says plainly that the non-builder criterion was not met, and the README (6.7) discloses the run as a builder run

**Given** the playtest has finished
**When** the profiles are checked
**Then** the `demo` profile is untouched, and the tester's profile exists only in that browser's IndexedDB under `playtest`, or in the local JSON file under cut 2
**And** nothing from that profile reached the server except the session-start Derived block, apart from, under cut 2, the local `GET|PUT /profile/<name>` file route on the same Mac

### Story 6.6: Final videos: unedited capture proof and captioned main demo

As a builder,
I want an unedited capture proof and a captioned main demo recorded on Tue Nov 3,
So that the submission shows capture within the target and every headline beat, with each shortcut disclosed.

_Covers NFR-1, NFR-3, NFR-11, NFR-12, UX-DR86. Owner: builder task. Depends on: 4.5, 5.8, 6.4, 6.5. Tier 1, Tue Nov 3, video only. Capture proof: a room-2 photo set shot that day and never sent before, CACHE=off, the cache cleared on camera (ledger and exports untouched), the Timer on screen from T0 to T1, kept only under 200 s with at most one visible retry, earlier builds disclosed; main demo 2:00 target, 2:30 cap, captioned and unlisted, three takes, the shot-list beats (persuasion attack, three Rungs at 6x within 40 s with triggers visible, one accepted and one rejected Card under the live Validator, the room-2 Greeting on PROFILE=demo, Model table unless cut 0, Disclosures in the last 10 s); recording memory about 10.6 GB on the M1; both links play logged out; UAT: the capture proof satisfies UAT-12 and the main demo UAT-13 in `docs/implementation-artifacts/uat-acceptance-tests.md`. Dev skills for the live capture: keyframe-muse, keyframe-sam31._

**Acceptance Criteria:**

**Given** Tue Nov 3 is held for video only, a room-2 photo set was shot that day and never sent to the pipeline, and the server runs with `CACHE=off` so the mode indicator reads "Local mode · Cache off · profile {name} · {k} rooms played"
**When** the builder clears the cache on camera and clicks Upload
**Then** the capture proof runs unedited, with the Timer on screen from T0 (the Upload click) to T1 (the first Hotspot responding)
**And** the sprint status records the measured T1 − T0 on the M1 against the Capture target (120 s, or measured p50 plus 25% if it was re-based)
**And** the Tue Nov 3 photo set is JPEG only, contains no faces, documents or other people's belongings before it is sent, and stays under the git-ignored `rooms/` or `photos/` folders, with `git status` showing none of it staged

**Given** the on-camera cache clear removes `.cache/`
**When** the proof runs
**Then** `spend/ledger.jsonl` and `spend/exports/` are untouched
**And** every call of the proof is priced and appended to the Ledger, because `CACHE=off` bypasses the cache, never the Ledger

**Given** a capture-proof take
**When** T1 − T0 is 200 s or more, or the take shows more than one visible retry (including a Build that ends `needs_more_photos` or `needs_recapture`)
**Then** the take is discarded and re-shot from the cache clear
**And** if the kept take's room was built on an earlier take, the video discloses those earlier builds

**Given** the `demo` profile holds only the real Mon Nov 2 room-1 run at Demo timescale 1, and the server runs with `DEMO_TIMESCALE=6` and the scripted Trickster source (the cut-1 source under cut 1)
**When** the builder records three main-demo takes and edits one cut
**Then** the cut targets 2:00 and never runs over 2:30, and shows in the §11.3 order:
- a phone photo of the real room, then the same objects as Hotspots (Mask preview label chips)
- the capture time-lapse with the Timer running from T0, the masks and the Build view puzzle graph and verification (under cut 0, the puzzle JSON), captioned "Time-lapse · unedited capture proof linked"
- the persuasion attack failing
- three Rungs within 40 s on real Wrong attempts, with the triggers visible
- one accepted and one rejected Card, both decided by the live Validator, the accepted one a Merge or Loosen when the recording allows
- the room-2 Greeting with the mode indicator "profile demo · 1 room played" and an edit caption naming the real Mon Nov 2 room-1 run at Demo timescale 1
- the Build view Model table (under cut 0, the puzzle JSON and the README Model table)

**And** the last 10 s show every Disclosure line on the Play screen: the 6× timescale, the scripted replay (under cut 1, proposals written in advance) and earlier builds

**Given** the main demo is exported at 1080p
**When** each beat is checked
**Then** its key text is legible:
- 0:00: the Mask preview label chips
- 0:15: the Stage list results and the verdict caption
- 0:35: the typed words, the helper line and the Rung label
- 0:50: the Triggers header with its 1× values, the newest row and the Rung line, in frame together
- 1:05: both Card labels, with the "Proposed" line and reason
- 1:20: the mode indicator on the Greeting
- 1:35: the Model table ids and captions
- 1:50: every Disclosure line

**And** any shot whose key text is clipped, covered or unreadable is re-taken

**Given** recording runs on the 16 GB M1
**When** a take is recorded
**Then** only Chrome, the backend, Llama 3.2 3B on Ollama (absent under cut 3) and the screen recorder run, with the IDE and chat apps closed; no GPU is used, and recording memory stays about 10.6 GB, as recorded in the sprint status
**And** no feature story is started or merged on Tue Nov 3

**Given** both videos are final
**When** they are uploaded
**Then** the main demo is captioned and unlisted, the capture proof is unedited and unlisted, both links are recorded in the sprint status, and each plays for a logged-out viewer
**And** neither video shows faces, documents or other people's belongings

### Story 6.7: README and CHANGELOG tell the full, honest picture

As a builder,
I want the README and CHANGELOG to give judges the full and honest picture,
So that model use, shortcuts, cuts, privacy and pre-existing code can be checked without asking.

_Covers NFR-12, NFR-13, NFR-4, FR-1, FR-17, FR-30, AR-30. Owner: docs. Depends on: 1.14, 6.2, 6.5 (the playtest outcome, for the final text). Tier 1, drafted from Sat Oct 31, final Wed Nov 4 morning. Pitch, Model table (model id, where it runs, what it does, whether it shipped), architecture diagram, local setup (the Input requirement '6 to 10 JPEG photos' with the iPhone tip, .env.example, Ollama llama3.2:3b with OLLAMA_KEEP_ALIVE=-1 unless cut 3, which drops the phrasing claim), the Privacy line, Retention summary and Disclosures verbatim from src/api/meta.py (tested), which Cuts shipped, the finals mode, the playtest outcome (stating a builder cold run when the 6.5 fallback was used), the pre-existing-code section linking the baseline tag with its diffstat, third-party and model licenses, the Spend log note; dated CHANGELOG from the baseline entry through Nov 4; images are outputs only, never raw photos; UAT: satisfies the README checks of UAT-10 (and the builder-run disclosure of UAT-03's fallback) in `docs/implementation-artifacts/uat-acceptance-tests.md`._

**Acceptance Criteria:**

**Given** the README
**When** a judge reads it
**Then** it has a pitch, an architecture diagram, and a Model table with one row per model giving the model id, where it runs, what it does and whether it shipped. The rows are:
- `muse-spark-1.3` (Architect, Riddler, Dry run, Trickster)
- `sam-3.1`
- `muse-image-1.0`
- Llama 3.2 3B Instruct Q4_K_M on Ollama, on the Mac only

**And** each row's shipped status reflects the Cuts in effect (cut 1: no live Trickster call; cut 3: no Ollama phrasing; cut 4: no Dry run), and `fal-ai/sam-3/3d-objects` and `muse-voice-transcribe-1.0` appear only with an accurate shipped status

**Given** a reader follows the local setup section
**When** they set up Local mode
**Then** the steps state the Input requirement "6 to 10 JPEG photos" with the iPhone Most Compatible tip, copy `.env.example` to `.env`, and, unless cut 3 shipped, install Ollama with `llama3.2:3b` and `OLLAMA_KEEP_ALIVE=-1`
**And** under cut 3 the README drops the claim that Ollama phrases the hints, while the Privacy line "the player profile stays on your machine." stays

**Given** the strings served by `src/api/meta.py`
**When** the README's Retention summary and Disclosures are compared with them
**Then** the Retention summary equals the Local `retention` text served by `GET /meta`, and the Disclosures equal, word for word, the lines the meta.py function composes for the video settings (the 6× timescale, scripted or cut 1, and the earlier-builds line)
**And** the README names each of cuts 0 to 8 as shipped or not, declares the finals mode (Local mode screen-shared from the M1; fallbacks the hosted URL, the cached rooms, then the video), and states the playtest outcome, naming a builder cold run when the 6.5 fallback was used

**Given** the `pre-hackathon-baseline` tag
**When** a judge opens the "Pre-existing code" section
**Then** it links the tag and includes the output of `git diff --stat pre-hackathon-baseline..HEAD`
**And** the README lists the SAM License, the Llama 3.2 license, the Meta Model API service terms, the fal terms and, only if Tier 3 ships, `@sparkjsdev/spark` MIT. Its Spend log note says the log is the Ledger export plus fal.ai receipts and Modal usage, with pre-kickoff verification spend listed separately

**Given** `CHANGELOG.md`
**When** it is read
**Then** it starts with the baseline entry verbatim, "Before Oct 26 (baseline): provider interface, mock provider, Meta API stub, tests. No front end, no model calls."
**And** dated entries follow through Nov 4

**Given** the README contains images
**When** each image path is checked
**Then** each is an output (a screenshot, a Clue card or a committed portrait), never a raw room photo
**And** no image path points into `rooms/`, `photos/`, `captures/` or `uploads/`

**Given** the story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests asserting that:
- the README contains, verbatim, the Privacy line, the Input requirement, the Local retention text, the line composed for DEMO_TIMESCALE=6, the Trickster-source line for the shipped source (scripted, or cut 1 under cut 1) and the earlier-builds line up to its date ("This room was built earlier, on"), each read from src/api/meta.py
- `CHANGELOG.md` starts with the baseline entry
- `LICENSE` exists
- no README image path points into a git-ignored input folder

### Story 6.8: Repo hygiene over the delivery-plan path list before going public

As a builder,
I want only the listed hackathon tooling paths removed from the index, and the history checked, before the repo goes public,
So that the public MIT repo carries the product, the planning sources of truth and outputs, and nothing private.

_Covers NFR-13, AR-28, AR-29, FR-36. Owner: repo root. Depends on: 6.7. Tier 1, Wed Nov 4 morning at the latest. Removes from the index only the delivery-plan list (_bmad/, .claude/skills/bmad-*/, .claude/skills/modal/, .claude/skills/keyframe-*/, .claude/hooks/session-start.sh and .claude/settings.json, the last kept with only its hook entry removed if it existed before the hook story) with the exact git rm -r --cached --ignore-unmatch command and the six .gitignore entries; git diff --cached --name-status lists only D entries under those paths and any other staged .claude/ path stops the pass; other .claude/ configuration stays; PRODUCT_BRIEF.md stays removed; history holds no raw room photo (only fixtures, portraits and listed outputs); the README diffstat regenerated; the Nov 4 Ledger export committed; then the repo goes public. Load keyframe-devops for the hygiene checks._

**Acceptance Criteria:**

**Given** the Repo hygiene list in `docs/specs/spec-keyframe/delivery-plan.md` §Submission package as it stands on Wed Nov 4 morning (as of Oct 21: `_bmad/`, `.claude/skills/bmad-*/`, `.claude/skills/modal/`, `.claude/skills/keyframe-*/`, `.claude/hooks/session-start.sh`, `.claude/settings.json`)
**When** the builder runs that list's command verbatim (as of Oct 21: `git rm -r --cached --ignore-unmatch _bmad .claude/skills/modal .claude/skills/bmad-* .claude/skills/keyframe-* .claude/hooks/session-start.sh .claude/settings.json`) and adds that list's `.gitignore` entries
**Then** `git ls-files` over the listed paths returns nothing and each listed path is ignored, and the existing `_bmad/config.user.toml` line is subsumed by `_bmad/`
**And** if a `.claude/settings.json` existed before the hook story, it is instead kept tracked and not ignored, with only the hook entry removed

**Given** the staged hygiene change
**When** `git diff --cached --name-status` runs
**Then** it lists only `D` entries under the listed paths, plus one `M .claude/settings.json` only in the pre-existing case above
**And** any other staged path (`settings.local.json`, `commands/`, `agents/`, another hook or another skill) stops the pass until it is unstaged; all other `.claude/` configuration stays on disk, tracked and not ignored

**Given** the index after the hygiene change
**When** the delivery-plan checks run
**Then** `git ls-files` shows no tracked `.env`, raw photo or cache path, and nothing in `src/`, `tests/`, `scripts/` or `web/src/` references `.claude/`
**And** `scripts/check.sh` passes in a fresh clone and CI is green on the hygiene commit
**And** `PRODUCT_BRIEF.md` is absent and not recreated, and the BMAD brief folder under `docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/` stays tracked

**Given** the doc scrub in the delivery-plan list
**When** the hygiene commit is prepared
**Then** every tracked file under `docs/` (memlogs included) and `README.md` is free of `.claude/` paths, the dev skill names, `--claude` flags, `CLAUDE_*` variables and any other mention of the coding tools, each touched sentence still reads, and the delivery-plan path list is replaced by its one-line removal statement
**And** `git grep -niE 'claude|keyframe-(sam31|muse|sam3d-fal|modal|devops)' -- docs README.md` returns nothing

**Given** the full git history
**When** every commit is scanned for image files
**Then** the only images found are synthetic fixtures under `tests/fixtures/`, portraits under `web/public/portraits/`, and outputs whose paths the sprint status lists (screenshots, Clue cards), with no raw room photo
**And** if a raw room photo is found, the repo stays private until it is removed from history and the scan passes

**Given** the hygiene commit
**When** it is prepared
**Then** the README diffstat is regenerated from `git diff --stat pre-hackathon-baseline..HEAD` run on the hygiene commit's parent and labelled with that commit's short hash, and the CHANGELOG has a dated Nov 4 entry for the pass
**And** the Wed Nov 4 `spend/exports/ledger-<date>.json` is committed, while `spend/ledger.jsonl`, `.env`, `rooms/`, `photos/`, `captures/`, `uploads/`, `*.heic` and `.cache/` stay ignored and untracked

**Given** every check above passes
**When** the builder makes the repo public
**Then** the repo, the `pre-hackathon-baseline` tag and `LICENSE` all resolve for a logged-out viewer

**Given** the story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests asserting that `.gitignore` holds each Repo hygiene entry and each FR-36 entry (`rooms/`, `photos/`, `captures/`, `uploads/`, `*.heic`, `.cache/`, `.env`) with no bare `.claude/` entry, that no hygiene path is in the index, and that `PRODUCT_BRIEF.md` is not tracked

### Story 6.9: Submit on the portal before 9:00 AM ET Wed Nov 4

As a builder,
I want the entry submitted on the portal before work on Wed Nov 4,
So that the 9:00 PM ET deadline is met, with 6 to 9 PM held as slack.

_Covers NFR-11, NFR-13, FR-30. Owner: builder task. Depends on: 6.6, 6.8. Tier 1 gate, Wed Nov 4 before 9:00 AM ET (deadline 9:00 PM; 6 to 9 PM held as slack). Indie track, solo, theme named, public repo URL; 300 to 400-word write-up repeating the pre-existing-code statement; 4 to 6 screenshots; both unlisted videos; Spend log = the Ledger export plus fal.ai receipts and Modal usage attached as-is, with pre-kickoff verification spend listed separately; Official Rules, CHANGELOG and screenshots per the PRD §11.3 checklist. Contingency (PRD §11.1): if the Official Rules require a live link, the URL of the Tue Oct 27 hosted smoke deployment (Demo rooms only, Rungs verbatim; built by date before this story, not a dependency) is submitted inside the 6 to 9 PM slack. Dev skill for the live-link contingency: keyframe-modal._

**Acceptance Criteria:**

**Given** the repo went public at the end of 6.8
**When** the builder fills in the portal
**Then** the entry is in the Indie track, marked solo, names the theme and gives the public repo URL
**And** it is submitted before 9:00 AM ET Wed Nov 4, and the sprint status records the confirmation and its timestamp

**Given** the portal write-up
**When** its words are counted
**Then** it runs 300 to 400 words
**And** it repeats the README's pre-existing-code statement: the `pre-hackathon-baseline` tag and its diffstat

**Given** the screenshots and videos
**When** they are attached
**Then** there are 4 to 6 screenshots chosen from capture with masks, puzzle JSON, a Rung with its events, Trickster Cards, the room-2 Greeting and the Model table, each a committed output showing only what the household agreed to
**And** the unlisted main demo and the unedited capture proof each open for a logged-out viewer

**Given** the Spend log
**When** it is attached
**Then** it is the Ledger export written by `scripts/ledger.py export`, never a hand-kept total, with the fal.ai receipts and Modal usage attached as-is
**And** pre-kickoff verification spend is listed separately, and the total stays within the Spend cap

**Given** the PRD §11.3 submission checklist
**When** the builder reviews it before submitting
**Then** the Official Rules are accepted, the CHANGELOG runs from the baseline entry through Nov 4, and each checklist item is marked done in the sprint status

**Given** an upload fails, or the Official Rules require a live link
**When** the morning submission cannot be completed
**Then** the builder completes it inside the 6 to 9 PM ET slack, before the 9:00 PM deadline, submitting as the live link the URL of the Tue Oct 27 hosted smoke deployment (Hosted mode, Demo rooms only, Rungs verbatim), checked to open for a logged-out viewer
**And** the sprint status records what failed and when the entry was finally submitted, and FR-32 (Access-code judge builds) and FR-33 (Judge data deletion, purge Tue Nov 10) stay Nov 5 to 9 work, outside this submission

## Epic 7: Judges play it themselves

A judge opens the hosted URL, lands on the Demo rooms, plays one to the Completion screen with verbatim Rungs, and can build their own room behind the Access code within a 20-build quota. Builds survive the host's web timeout, and Judge data is deleted on Tue Nov 10 as promised. Tier 1 lands only the Tue Oct 27 smoke deployment. Everything else is Tier 1.5 and comes after the backup video, starting with Clue cards (PRD §10.1 order: cuts restored, Clue cards, hosted).

### Story 7.1: Hosted stores on Modal Dict and Volume

As a builder,
I want the job, session and ledger stores on `modal.Dict` and the artifact store and Cache on the `keyframe-data` Volume, behind the same ports Local mode uses,
So that the hosted app keeps nothing in process memory and a Build, a Session and the spend record survive a container restart.

_Covers AR-12, AR-32, FR-36, NFR-4, AD-9. Owner: infra. Depends on: 1.10, 2.3, 2.4, 2.10. Tier 1 (smoke deploy, Tue Oct 27 after 2.12); made judge-ready Nov 5 to 9. Load the keyframe-modal skill._

**Acceptance Criteria:**

**Given** `src/infra/modal.py` built over injected Dict and Volume handles
**When** the hosted adapters are constructed
**Then** `JobStore` uses the Dict `keyframe-jobs`, `SessionStore` (`append`, `read_all`, `list_ids`, `delete`) uses `keyframe-sessions` and `LedgerStore` (`append`, `entries`) uses `keyframe-ledger`, while `ArtifactStore` and `Cache` share one Volume adapter over `keyframe-data` mounted at `/data`
**And** constructing them contacts no Modal service, so the tests can pass plain dicts and a temporary directory

**Given** the Volume `ArtifactStore` and `Cache`
**When** a `put` writes a value and a later read fetches it
**Then** every write ends with `Volume.commit()` and every read begins with `Volume.reload()`
**And** all Volume I/O in one process goes through one lock, and each file is read fully and closed before the lock is released, so no file is open when `reload()` runs

**Given** the Volume `ArtifactStore`
**When** a Room is read or `list_rooms()` runs
**Then** Rooms live at `/data/rooms/demo/<room_id>/` and `list_rooms()` returns a `RoomSummary` for each of them (7.14 adds the `rooms/judge/` partition)

**Given** two `SpendLedger` instances over one hosted `LedgerStore` (standing in for the web container and a runner container)
**When** each appends a priced call and `entries` is read
**Then** each entry sits under its own Dict key named by its `call_` ULID, the total is summed on read, and no entry is lost
**And** the only rewrite of an existing entry is the `reserved`-to-observed-cost replacement that `SpendLedger` already makes
**And** no atomic ledger store is built: `max_containers=1` on the web function stands in for one, and overshooting the cap by the estimates of calls in flight is accepted (AR-32)

**Given** a Session appended through the Dict `SessionStore` and a job written through the Dict `JobStore`
**When** `read_all` replays the Session and the job is read back
**Then** the events come back in append order, the replayed state equals the live state, and the job reads back unchanged
**And** the `keyframe-jobs` Dict holds in-flight job state only, and no retention rule relies on Dict expiry (7 idle days)

**Given** a hosted Session started with `POST /sessions {room_id, derived}` carrying sentinel Derived values and played through to `GET /sessions/<id>/result`
**When** every Dict entry and Volume file the adapters wrote is scanned
**Then** none contains the `derived` block, a sentinel value or any Player profile field, and no Session record carries a profile name or id
**And** the offline test that `.gitignore` lists `rooms/`, `photos/`, `captures/`, `uploads/`, `*.heic`, `.cache/` and `.env` still passes

**Given** this story's changes
**When** pytest runs offline against the mock provider, without a Modal connection
**Then** it passes with new tests covering this story's criteria

### Story 7.2: Modal app entry, Settings.mode and the hosted texts

As a builder,
I want one Modal app entry that runs the same FastAPI app with the hosted adapters, verbatim Rungs and the hosted texts, all chosen by `Settings.mode`,
So that the hosted URL serves the same API as Local mode, never runs a Guide model and tells judges where their photos go.

_Covers FR-6, FR-17, FR-20, FR-26, AR-18, AR-26, NFR-3, NFR-4, AD-14, AD-15. Owner: api (with src/config.py). Depends on: 1.14, 2.12, 7.1. Tier 1 (smoke deploy, Tue Oct 27). Load the keyframe-modal skill._

**Acceptance Criteria:**

**Given** `src/config.py`
**When** `Settings` reads the environment
**Then** it gains `mode` (from `MODE`, `local` or `hosted`) and `min_containers` (from `MIN_CONTAINERS`, default 0), as AD-14 assigns to the first hosted story
**And** `GUIDE` defaults to `verbatim` under `MODE=hosted`, and `MODE=hosted` with `GUIDE=ollama` fails at startup
**And** `MODE=hosted` with `DEMO_TRICKSTER=record` fails at startup (spine AD-14: the recorder runs in Local mode only), while `live`, `scripted` and `authored` start
**And** no module reads `os.environ`, and the `.env.example` test still finds every key `Settings` reads

**Given** `MODE=hosted`
**When** `src/api/wiring.py` resolves the adapters
**Then** `JobStore`, `SessionStore`, `LedgerStore`, `ArtifactStore` and `Cache` resolve to the 7.1 adapters (the hosted `JobRunner` comes in 7.7), and `HintPhraser` resolves to the verbatim adapter
**And** no Guide model is ever constructed or reached: the Ollama adapter is never instantiated under `MODE=hosted`
**And** `GET /meta` reads `mode` from `Settings` in place of the `local` constant, and `tests/test_boundaries.py` finds no mode branch outside `src/infra` and the `src/api` wiring

**Given** `MODE=hosted` before 7.11 injects the access guard
**When** `POST /builds` or `GET /builds/<job_id>/room` is called
**Then** wiring refuses both with 403 and the error envelope (`code: access_denied`, `stage: null`; spine AD-9, AD-13), and no photo is stored, no job is created and no Room is returned
**And** a route test asserts both refusals, and 7.11 replaces this refusal with the guard and quota

**Given** `src/api/modal_app.py`
**When** the module is imported
**Then** it defines the app with the `web` function as `@app.function(min_containers=<Settings.min_containers>, max_containers=1)` over `@modal.concurrent(max_inputs=20)` over `@modal.asgi_app()`, with the Secret `keyframe` attached, the Volume `keyframe-data` at `/data`, and no GPU requested
**And** FastAPI serves `web/dist` at `/` and the API under `/api/` from one origin with no CORS
**And** the hosted route table equals the local one, except that `GET|PUT /profile/<name>` is not served and, until 7.11, `POST /builds` and `GET /builds/<job_id>/room` are refused
**And** importing the module contacts no Modal service

**Given** `MODE=hosted`
**When** `GET /meta` is read
**Then** it returns `mode: hosted`, `guide: verbatim` and `guide_model: null`, and `disclosure` includes "Hosted mode: hints are shown as written; no hint model runs here."
**And** `retention` is the hosted text from `src/api/meta.py`: the shared opening plus the hosted ending, saying that photos, originals, the room and its play-throughs are stored on Modal and deleted Tue Nov 10, that play-through logs are deleted 24 hours after their last event, and that no player profile data leaves the browser (final words per PRD §13 Q3)
**And** the local storage sentence "A copy of your photos is also kept on this computer." does not appear: the hosted text replaces it and is never appended to it

**Given** `MODE=hosted` and a `POST /sessions` whose `derived` block is within bounds but not `Derived.fresh()`, in a Session in which a Rung opens
**When** the Session runs and is replayed
**Then** every threshold is computed from `Derived.fresh()`, nothing from the received block is stored, and the replayed state equals the live state
**And** the Rung's text in session state equals the Room's Rung text word for word and no Ollama request is made
**And** an API fixture test finds no `solution` key in any play, job-state or `GET /meta` response

**Given** this story's changes
**When** pytest runs offline against the mock provider, without a Modal connection
**Then** it passes with new tests covering this story's criteria

### Story 7.3: First manual modal deploy as a smoke test

As a builder,
I want the real app deployed to Modal by hand on Tue Oct 27,
So that hosting problems show up a week early and a live link exists if the Official Rules require one on Nov 4.

_Covers FR-31, NFR-10, NFR-11. Owner: builder task. Depends on: 7.2. Tier 1, Tue Oct 27 (day plan: first modal deploy of the real app), not queued behind Epic 6; manual, no CD. Load the keyframe-modal skill._

**Acceptance Criteria:**

**Given** 7.1 and 7.2 merged and the `keyframe` Secret created in the Modal Environment per the runbook
**When** the builder runs `modal deploy` on `src/api/modal_app.py` by hand
**Then** the deploy succeeds, and the URL serves `web/dist` at `/` and the API under `/api/`
**And** the GitHub Actions job still holds no secret and no deploy step

**Given** the deployed URL
**When** the builder requests `GET /api/meta`
**Then** it answers `mode: hosted`, `guide: verbatim` and `guide_model: null`, with the Hosted Disclosure line and the hosted Retention text
**And** `POST /api/builds` and `GET /api/builds/<job_id>/room` are refused on the deployed URL

**Given** a fixture Room copied by hand from the git-ignored local `rooms/` to `rooms/demo/<room_id>/` on the `keyframe-data` Volume (`modal volume put`, in the Environment the app deploys to)
**When** the builder opens the URL in desktop Chrome and plays it
**Then** the Scene renders from `GET /rooms/<room_id>/photos/<i>`, a Hotspot click is accepted as an event, and an opened Rung shows its text as written
**And** `git status` shows no room photo added to the repo

**Given** the smoke test result
**When** Tue Oct 27 ends
**Then** the sprint status records the deploy date, the URL and the result

**Given** Official Rules that require a live link on Wed Nov 4
**When** story 6.9 prepares the submission
**Then** the link submitted is this deployment, serving Demo rooms only with Rungs verbatim, and FR-32 and FR-33 stay on the Nov 5 to 9 plan, and the demo Rooms reach `rooms/demo/` on the Volume the same way

### Story 7.4: Clue cards generated once per demo Room

As a builder,
I want one Clue card per Puzzle, painted once from the Clue text, for the demo Rooms,
So that the recorded and hosted Demo rooms show an image beside each Clue, with no image call in play and no risk to the Build.

_Covers FR-37, AR-32, NFR-5, AD-6. Owner: pipeline. Depends on: 2.22, 3.6, 6.4. Tier 1.5; gate: after the backup video (6.4) and the restored cuts; before Tue Nov 3 if it is to appear on video. Load the keyframe-muse skill._

**Acceptance Criteria:**

**Given** a stored Room with 4 to 6 Puzzles
**When** the Clue card step in `src/pipeline` is run on demand for it
**Then** it makes exactly one `generate_image(prompt)` call per Puzzle through the `image` role provider (`muse-image-1.0`) and stores each image in the `ArtifactStore`, keyed by that Puzzle's `pz_` id, outside the Room
**And** the stored Room is byte-for-byte unchanged afterwards, and no Schema v1 model changes

**Given** a hosted adapter in place of the mock
**When** each card call is made
**Then** it runs `Cache.get_or_call(key)` and, on a miss only, `SpendLedger.guard`, adding one `call_` ledger entry per billed card
**And** a second run for the same Room serves every card from the Cache and adds no ledger entry
**And** a call the Spend cap would exceed is refused with `SpendCapExceeded`

**Given** a fixture Room with sentinel solutions (the code string, the order id list in sequence, the `use_on` pair, the find target id), sentinel Rungs, photo hashes and a Derived block
**When** each Clue card prompt is rendered
**Then** the prompt is the Clue text only, and none of the sentinels appears in it
**And** no image bytes are passed to `generate_image`

**Given** a Build running `ingest → architect → segment → author → validate → dryrun → scene`
**When** it runs with or without Clue cards
**Then** the stage runner never calls the Clue card step, and job status, stage timings and T1 are the same either way (A-14)
**And** Judge rooms and ordinary Builds get no card unless the Clue cards setting is on. That setting is added to `Settings` by an AD-14 amendment before this story reads it, and is off by default. When it is on, the step runs only after the job is `done`, and each card is priced as a ledger entry of that Build
**And** no play route or session code calls `generate_image`

**Given** one Puzzle's call fails with `ProviderError` (a `muse-image-1.0` 500 is never retried, AD-13)
**When** the step continues
**Then** that Puzzle has no stored card, the remaining Puzzles are still attempted, the Room stays playable and the job status is unchanged
**And** on `SpendCapExceeded` the step stops, the Puzzles without a card stay without one, and the step reports which Puzzles have no card

**Given** this story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 7.5: Clue card read route

As a builder,
I want one read route that serves a Puzzle's Clue card from the artifact store,
So that the client can show Clue cards without the PlayView gaining a solution or the frozen Room changing.

_Covers FR-37, AR-13, AD-9. Owner: api. Depends on: 7.4. Tier 1.5._

**Acceptance Criteria:**

**Given** this story starts
**When** the route is added
**Then** it has first been declared in the spine's HTTP surface by amendment: its path under `GET /rooms/<room_id>/`, its Puzzle id parameter, how a client learns, without any solution field, that a Room has Clue cards, and the 404 code for a Puzzle without a card, as a typed error class added to AD-13 by the same amendment
**And** no Schema v1 model changes, and the generated `web/types` staleness test passes

**Given** a Room whose Clue cards 7.4 stored
**When** the route is requested for a Puzzle that has a card
**Then** it answers 200 with the stored image bytes and their media type, read through the `ArtifactStore` only
**And** serving it never calls `generate_image`

**Given** a Room with no Clue cards, or a Puzzle whose card failed
**When** the route is requested
**Then** it answers 404 with the amended no-card code and starts no generation
**And** an unknown room id answers 404 `room_not_found` with `stage: null`, like every other room-keyed route (AD-9)

**Given** the route and every play route
**When** an API fixture test reads their responses
**Then** none contains a `solution` key, `PlayView` gains no solution, and the stored Room in the `ArtifactStore` is unchanged
**And** the route answers in both modes with no `X-Access-Code`

**Given** this story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 7.6: Clue card slot beside each Clue

As a player,
I want a small painted card beside each Clue when the Room has them,
So that each Puzzle feels illustrated and the notes never jump while the image loads.

_Covers FR-37, UX-DR28. Owner: web. Depends on: 1.20, 4.6, 7.5. Tier 1.5, after 7.5._

**Acceptance Criteria:**

**Given** a Room that has Clue cards
**When** its Wizard notes entries render
**Then** each entry draws the Clue card slot at `{components.clue-card-slot}` size, 112 x 84 px with `rounded.sm`, right-aligned beside the Clue, with the Clue wrapping to its left (`DESIGN.md` Components, Wizard notes and Clue card slot rows; the Wizard notes in `mockups/play-screen.html` are the context, since no mockup draws the slot)
**And** for a Room without Clue cards, no entry draws a slot at all

**Given** a slot whose image has not loaded
**When** it renders and then the image arrives or fails
**Then** it shows the `clue-card-placeholder` fill with a 1 px dashed `clue-card-placeholder-edge` until ready, then the image
**And** on a 404 or a load error it becomes a flat `clue-card-blank` with no edge
**And** the slot's box measures the same in every state, so nothing in the entry moves

**Given** a ready card
**When** assistive technology reads the entry
**Then** the image's alt text is the Clue, and the visible Clue text beside it is hidden from assistive technology, so the Clue is read once
**And** while the slot is a placeholder or blank, the slot is hidden from assistive technology and the visible Clue is read
**And** the slot takes no focus, writes nothing to the live region, meets the `DESIGN.md` contrast table, and has no fade when reduced motion is set

**Given** an accepted Decoy or Merge raises `room_revision` and the client refetches `GET /sessions/<id>/room`
**When** the Wizard notes re-render
**Then** each visible entry keeps the same card image, and the evidence count changes in place
**And** an entry hidden by a Merge takes its slot with it and shows the same card when it returns

**Given** this story's changes
**When** the web build and type check run (`vite build`, `tsc --noEmit`) and pytest runs offline against the mock provider
**Then** they pass with new tests covering this story's criteria

### Story 7.7: Hosted build runner with a queued state and a watchdog

As a judge,
I want my Build to wait its turn, carry on after the web request ends, and say plainly when its runner has died,
So that I never watch a Build stuck at "running" forever.

_Covers FR-32, FR-5, NFR-7, AR-10, AD-7. Owner: infra. Depends on: 2.10, 7.1. Tier 1.5. Load the keyframe-modal skill._

**Acceptance Criteria:**

**Given** a `queued` job record in the Dict `JobStore`
**When** the hosted `JobRunner.start(job_id)` spawns the stage runner (an injected spawn function in tests)
**Then** it passes the `job_id` only, stores the `FunctionCall` id under its own key `call:<job_id>`, and returns at once
**And** the job reads `queued` while it waits for the single runner, until the runner's first stage write
**And** if the spawn raises, the job is marked `failed` at stage `ingest`

**Given** a spawned job
**When** its stages run
**Then** the runner is the only writer of that job's record and artifacts, and the web side never writes the record back
**And** the only other write is the watchdog's `failed` mark on a job whose runner has ended

**Given** a runner that finishes the scene stage
**When** the final job record is written
**Then** it is written to the Volume beside the Room and committed
**And** a job read falls through Dict then Volume, so a finished job whose Dict entry is gone still reads `done` with its stage timings and call rows

**Given** a `running` job whose stored `FunctionCall` has ended without a terminal status
**When** a job read runs the watchdog
**Then** the job is marked `failed` with the stage it reached
**And** a `queued` job with no `call:<job_id>` key after `ORPHAN_S` (60 s) is marked `failed`
**And** a job whose call state stays unknown is left unchanged until `DEADLINE_S` (1,200 s) and then marked `failed`, so no job stays `running` forever

**Given** a runner restarted on a job persisted through the author stage
**When** it starts
**Then** it rereads job state from `JobStore` and resumes at `validate`, with no repeated architect, segment or author call (counted on the mock)

**Given** this story's changes
**When** pytest runs offline against the mock provider, without a Modal connection
**Then** it passes with new tests covering this story's criteria

### Story 7.8: Modal functions: run_build spawned per job and the daily ledger snapshot

As a judge,
I want my Build to run in its own Modal function while the page polls persisted state,
So that a Build longer than the host's 150 s web timeout still reaches me.

_Covers FR-32, FR-29, NFR-7, AR-12, AD-7, AD-9. Owner: api. Depends on: 7.2, 7.7. Tier 1.5. Load the keyframe-modal skill._

**Acceptance Criteria:**

**Given** `src/api/modal_app.py` in hosted mode
**When** `POST /builds` accepts an upload
**Then** ingest stores both photo streams and commits the Volume, the `queued` job record is written, and `JobRunner.start` calls `run_build.spawn(job_id)`, in that order
**And** `run_build` is `@app.function(timeout=900, max_containers=1)` with the `keyframe` Secret attached, so a second spawned Build waits as `queued` until the first ends, and the response returns the `job_` id without waiting for any stage

**Given** the `web` ASGI function
**When** any request is served
**Then** it keeps its default timeout and never runs a stage

**Given** a Build whose stages total more than 150 s (two Regenerations, about 260 s on a fake build clock)
**When** the client polls `GET /builds/<job_id>` until a terminal status
**Then** each poll reads persisted state only and answers 202 with `queued`, or `running` and its `stage`, never an error or a timeout
**And** the final poll answers 200 with `done`, after which `GET /rooms/<room_id>` serves the Room's `PlayView`

**Given** hosted ledger entries in `keyframe-ledger`
**When** `ledger_export`, scheduled with `modal.Cron("0 6 * * *", timezone="America/New_York")`, runs
**Then** it writes every entry as one JSON line to `spend/hosted-<date>.jsonl` on the Volume and commits
**And** the snapshot's total equals the sum the hosted `LedgerStore` returns

**Given** an empty hosted ledger
**When** `ledger_export` runs
**Then** it writes an empty `spend/hosted-<date>.jsonl` and does not fail

**Given** this story's changes
**When** pytest runs offline against the mock provider, without a Modal connection
**Then** it passes with new tests covering this story's criteria

### Story 7.9: Hosted ledger snapshot merged into the committed export

As a builder,
I want `scripts/ledger.py export` to merge the latest hosted snapshot with the local entries,
So that the committed export stays the full spend record against the credit after the Dict entries expire.

_Covers FR-29, NFR-6, AR-9. Owner: scripts. Depends on: 2.6, 7.8. Tier 1.5. Load the keyframe-modal skill._

**Acceptance Criteria:**

**Given** local entries in `spend/ledger.jsonl` and the latest `spend/hosted-<date>.jsonl` (read from the Volume live, or from a fixture under `tests/fixtures` offline)
**When** `scripts/ledger.py export` runs
**Then** `spend/exports/ledger-<date>.json` holds the local entries merged with the hosted snapshot

**Given** a `call_` entry present in both sources, and several hosted snapshots
**When** the export merges them
**Then** each `call_` entry appears once, the total is the sum of the distinct entries, and the snapshot with the latest date is the one merged

**Given** no hosted snapshot is available
**When** the export runs
**Then** the export holds the local entries alone, prints that no hosted snapshot was merged, and exits 0

**Given** no export file for today
**When** `scripts/ledger.py reset` runs
**Then** it refuses and leaves the counter unchanged
**And** once today's export, holding the latest hosted snapshot, exists, the reset runs and resets both the local counter and the hosted `keyframe-ledger` counter, so spend before the reset counts against neither cap

**Given** this story's changes
**When** pytest runs offline against the mock provider, without a Modal connection
**Then** it passes with new tests covering this story's criteria

### Story 7.10: Twenty-slot judge build quota

As a judge,
I want a fixed pool of 20 judge builds that cannot be overrun,
So that judge spend has a limit and every judge sees the same honest count.

_Covers FR-32, AR-12, AD-9. Owner: infra. Depends on: 7.1, 7.7. Tier 1.5. Load the keyframe-modal skill._

**Acceptance Criteria:**

**Given** this story starts
**When** the port change is made
**Then** `src/pipeline/ports.py` first declares on `JobStore` a slot claim that raises `BuildQuotaExceeded` when none is left, and a `builds_left` read
**And** the local adapter never refuses a Build

**Given** the hosted `JobStore`
**When** Builds claim slots
**Then** each claim takes one of 20 slot keys with `Dict.put(key, value, skip_if_exists=True)`, 20 claims succeed, and the 21st raises `BuildQuotaExceeded` and writes nothing

**Given** accepted Builds that end `failed`, `needs_more_photos` or `needs_recapture`
**When** `builds_left` is read
**Then** each still counts toward the 20, whatever its end status (A-25), so `builds_left` falls by one per accepted Build
**And** the count lives in the Dict, so a container restart does not reset it, and reading `builds_left` claims no slot

**Given** the claim's atomicity under concurrent writers is not documented by Modal
**When** it is checked live in a non-judging Modal Environment, with concurrent claimers, before the quota is relied on
**Then** exactly 20 claims succeed, and the result is recorded in the sprint status; if the check fails, the quota goes through bmad-correct-course before 7.11
**And** offline, concurrent threads over a fake Dict holding 19 claimed slots produce exactly one more successful claim

**Given** this story's changes
**When** pytest runs offline against the mock provider, without a Modal connection
**Then** it passes with new tests covering this story's criteria

### Story 7.11: Access-code guard and the quota refusal

As a judge,
I want building and the full-Room download to require the access code, with a clear refusal once the 20 builds are gone,
So that only judges spend on builds, nobody else can download solutions, and the Demo rooms stay open whatever happens.

_Covers FR-32, AR-13, AR-17, AD-9, AD-13. Owner: api. Depends on: 2.12, 7.10. Tier 1.5._

**Acceptance Criteria:**

**Given** hosted mode with `ACCESS_CODE` from the `keyframe` Secret
**When** `POST /builds` arrives with no `X-Access-Code` header or a wrong one
**Then** it is refused with 403 and the error envelope `{error: {code: "access_denied", message, stage: null}}` (spine AD-9, AD-13), replacing the 7.2 placeholder refusal
**And** the refusal happens before any photo is stored: no job is created, no slot is claimed and the `ArtifactStore` is untouched

**Given** hosted mode
**When** `GET /builds/<job_id>/room` arrives with no `X-Access-Code` header or a wrong one
**Then** it is refused the same way, and no part of the Room is returned
**And** with the correct header it returns the full Room

**Given** hosted mode and no `X-Access-Code` header
**When** a client calls `GET /rooms`, `GET /rooms/<room_id>`, `GET /rooms/<room_id>/photos/<i>`, `POST /sessions`, `GET /sessions/<id>`, `GET /sessions/<id>/room`, `POST /sessions/<id>/events`, `POST /sessions/<id>/trickster`, `GET /sessions/<id>/result`, `GET /builds/<job_id>`, `GET /builds/<job_id>/view`, `GET /schema` or `GET /meta`
**Then** each answers normally, and none of the responses contains a `solution` key

**Given** 20 slots already claimed
**When** a 21st `POST /builds` arrives with the correct code
**Then** it answers `{error: {code: "build_quota_exceeded", message, stage: null}}` from `BuildQuotaExceeded`, its code and status unchanged by the Oct 21 access amendment (spine AD-9), stores no photo and spawns no runner
**And** `GET /rooms` and Demo room Sessions are still served

**Given** the correct code and an upload ingest refuses with 422
**When** `POST /builds` is handled
**Then** ingest validation runs before the slot claim and stores nothing, no slot is claimed, and the claim comes before the first photo write

**Given** this story's changes
**When** `tests/test_boundaries.py` and the route tests run
**Then** the guard and the quota are injected by `src/api/wiring.py` from `Settings`, and no route handler reads `MODE`
**And** under `MODE=local`, `POST /builds` and `GET /builds/<job_id>/room` are served with no code check and no quota

**Given** this story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 7.12: POST /access/check before photo selection

As a judge,
I want to check the access code before I choose any photos,
So that I know the code works and how many builds are left before I send anything.

_Covers FR-32, AR-5, AR-13, AD-9. Owner: api. Depends on: 7.11. Tier 1.5._

**Acceptance Criteria:**

**Given** hosted mode and the correct code
**When** `POST /access/check {code}` is called
**Then** it returns the `AccessCheck` model declared in 1.5 (and listed by `GET /schema`) as `{ok: true, builds_left: n}`, where n comes from the hosted `JobStore`
**And** it starts no Build, claims no slot and writes nothing to the `ArtifactStore`

**Given** hosted mode and a wrong code
**When** `POST /access/check {code}` is called
**Then** it answers 200 `{ok: false, builds_left: null}` (spine AD-9), never the error envelope, starts no Build and claims no slot

**Given** more than 10 access attempts from one client IP within 10 minutes, counting every `POST /access/check` and every `POST /builds` or `GET /builds/<job_id>/room` from 7.11, with a wrong or the right code (the limit, the window and the per-IP key are one named constant in `src/api`, and the count lives in a hosted store, not process memory)
**When** the attempt past the limit arrives
**Then** it is refused with 429 and the error envelope `{error: {code: "too_many_attempts", message, stage: null}}` plus a `Retry-After` header, without the code being compared (spine AD-9, AD-13), and the client maps it to the too-many-tries state
**And** the test drives 11 attempts mixing checks and guarded routes with right and wrong codes, and only the 11th is refused
**And** an attempt after the `Retry-After` wait answers normally

**Given** `MODE=local`
**When** `POST /access/check` is called
**Then** the route is not served (404), and it is the only route-table difference this story adds

**Given** a check that answered `ok: true`
**When** the last slot is claimed by another Build, or the code changes, before this judge's `POST /builds`
**Then** `POST /builds` re-checks and answers `build_quota_exceeded` or 403 `access_denied`, and starts no Build

**Given** this story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 7.13: Seed the Demo rooms with their job records

As a builder,
I want a script that writes each Demo room and its job record to the Volume,
So that judges can play the Demo rooms and see how each was built, with no paid call.

_Covers FR-31, AR-10, AR-12, AD-7. Owner: scripts. Depends on: 1.5, 7.1, 7.7 (a job read falls through to the Volume record). Tier 1.5, Thu Nov 5 to Sun Nov 8. Load the keyframe-modal skill._

**Acceptance Criteria:**

**Given** built Demo rooms in the git-ignored local `rooms/`
**When** `scripts/seed_rooms.py` runs
**Then** each Room, its photos, its `Room.name` (at most 40 characters) and, when 7.4 stored them, its Clue cards keyed by Puzzle id are written under `rooms/demo/` on the Volume, and the Volume is committed
**And** a name longer than 40 characters is refused before anything is written

**Given** a seeded Demo room
**When** its final job record is read
**Then** it holds the stage timings, the call rows, the validator and Dry run verdicts and the build time
**And** `GET /builds/<job_id>` answers 200 `done` for every Demo room, and `GET /builds/<job_id>/view` serves its `BuildView` when 2.27 to 2.28 have shipped

**Given** the seeded Volume behind the hosted URL
**When** a Demo room is opened
**Then** `GET /rooms/<room_id>` serves its `PlayView`, `GET /rooms/<room_id>/photos/<i>` serves its photos, and a Session plays it to completion
**And** seeding adds no entry to the hosted `LedgerStore`

**Given** a seeding run
**When** it finishes
**Then** nothing under the local `rooms/` or `.cache/` was changed or deleted, no file was added to the git index, and the `.gitignore` test still passes

**Given** this story's changes
**When** pytest runs offline against the mock provider, without a Modal connection
**Then** it passes with new tests covering this story's criteria

### Story 7.14: Hosted room partitions: Demo rooms listed, Judge rooms apart

As a judge,
I want the landing to list only the Demo rooms, with my own room kept apart,
So that strangers never see a room built from my photos.

_Covers FR-31, FR-33, AR-12, AD-9. Owner: infra. Depends on: 7.1, 7.13. Tier 1.5. Load the keyframe-modal skill._

**Acceptance Criteria:**

**Given** Demo rooms under `rooms/demo/` and Judge rooms under `rooms/judge/`
**When** the hosted `ArtifactStore.list_rooms()` runs
**Then** it returns a `RoomSummary {room_id, name, cover_photo, puzzle_count, job_id, built_at}` for each Demo room and none for any Judge room

**Given** a judge Build
**When** the runner stores its Room, photos and originals
**Then** every path a judge Build writes (photos, originals, job record, `cache-keys.json`), whatever its end status, is under `rooms/judge/<room_id>/`, never under `rooms/demo/`, and only `scripts/seed_rooms.py` writes under `rooms/demo/`

**Given** a judge Build that wrote Cache entries
**When** it finishes
**Then** `cache-keys.json` beside its originals lists every Cache key the Build read or wrote (AD-8), and the Volume is committed

**Given** a Judge room id
**When** `GET /rooms/<room_id>` is called
**Then** it serves the Judge room's `PlayView`, so the judge can play it although it is never listed

**Given** Local mode
**When** `list_rooms()` runs
**Then** it still lists every stored Room

**Given** this story's changes
**When** pytest runs offline against the mock provider, without a Modal connection
**Then** it passes with new tests covering this story's criteria

### Story 7.15: Demo room welcome on session start

As a judge,
I want a Demo room to welcome me as a visitor,
So that the opening line fits a room that isn't mine.

_Covers FR-31, AR-31, UX-DR45, AD-4. Owner: api. Depends on: 1.13, 7.14. Tier 1.5._

**Acceptance Criteria:**

**Given** this story starts
**When** the port change is made
**Then** `src/pipeline/ports.py` first declares on `ArtifactStore` a read telling whether a `room_id` is a Demo room (hosted: under `rooms/demo/`; local: never), and `POST /sessions` picks the welcome from it

**Given** a Demo room
**When** `POST /sessions {room_id, derived}` starts a Session on it
**Then** the response carries `opening_line {kind: welcome, text: "Welcome to someone else's room. Find what doesn't belong."}` with `phrasing: false`
**And** an `OpeningLineEvent` with the same text is appended at once

**Given** a Judge room in hosted mode
**When** a Session starts on it
**Then** the opening line is the First-room welcome "Welcome to your own room. Find what doesn't belong."

**Given** hosted mode and a `derived` block with `sessions` of 1 or more
**When** a Session starts
**Then** the opening line is still a welcome, `HintPhraser.greet` is never called and the Greeting path is never taken
**And** a `derived` block outside its bounds is refused with 422 and no Session is created

**Given** the two welcome lines
**When** the code is inspected and tested
**Then** both live in one place, beside each other, with a test that pins both strings
**And** `GET /sessions/<id>` returns the same `opening_line` after a reload, with no second `OpeningLineEvent`

**Given** this story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 7.16: Hosted landing with Demo room cards

As a judge,
I want a landing page that shows the Demo rooms and how a room is built, all at once,
So that I can start playing, or see the work, within a minute of opening the URL.

_Covers FR-31, UX-DR57, UX-DR58, UX-DR68, UX-DR81, NFR-10. Owner: web. Depends on: 1.17, 1.27, 7.15. Tier 1.5._

**Acceptance Criteria:**

**Given** hosted mode and `#/`
**When** the page loads cold
**Then** it reads `GET /meta`, then `GET /rooms`, and shows the Disclosure banner as served (including "Hosted mode: hints are shown as written; no hint model runs here.") and the top bar with the wordmark and "Hosted mode", without the Timer or any Play control
**And** the title block shows "Keyframe" in `display-lg`, "An escape room built from your own photos.", the pipeline line, and "Short on time? See how a room is built and checked." with the "How a room is built" link, which opens the first Demo room's Build view (`DESIGN.md` Components, Hosted landing row; no mockup draws this surface)

**Given** `GET /rooms` returns Demo rooms
**When** the cards render three across in the left area, with the Access-code build in the 400 px right column
**Then** each `{components.demo-room-card}` shows the 4:3 cover photo, the Room's name (or its build time) in `display-sm`, "{n} puzzles · 15 to 25 min", the four Wizard portraits at 24 px under one accessible name, "The Architect, the Riddler, the Guide and the Trickster", and a footer with the decorative 96 px mask-and-graph thumbnail and "How this room was built"
**And** the thumbnail is drawn from that Demo room's `GET /builds/<job_id>/view` (masks and puzzle graph); if that request fails, the card shows no thumbnail and still starts Sessions
**And** hover shows the lamp ring and `{elevation.lamp-glow}`, and "How this room was built" opens that Demo room's Build view, with "Back" returning to the landing

**Given** a Demo room card
**When** the judge clicks it or presses Enter on it
**Then** the client sends `POST /sessions {room_id, derived}` with `Derived.fresh()`, opens the Play screen and shows the Demo room welcome
**And** a refused start shows the session-start-refused banner ("Keyframe couldn't start this room." / "Your room is safe. Try again.", "Try again") at the top of the left area, and the banner takes focus

**Given** `GET /rooms` fails or returns no rooms
**When** the landing renders
**Then** a failure shows "Keyframe couldn't load the demo rooms." with "Try again" in place of the cards, with the title block and the Access-code build still usable
**And** an empty list shows "No demo rooms are open right now. You can still build your own room with the access code." and hides the "How a room is built" lead-in and link

**Given** cut 0
**When** the landing renders
**Then** the "How a room is built" link, each card's "How this room was built" link and the thumbnail are absent (UX-DR67, UX-DR84), and the cards still start Sessions

**Given** the landing in current desktop Chrome, Safari and Firefox at 1280 px or wider
**When** it opens and is used by keyboard
**Then** initial focus is on the first Demo room card, the card and its Build view link each show their own focus ring, every text pair meets the `DESIGN.md` contrast table, and fades are instant under reduced motion
**And** below 1024 px the Narrow-screen message "Keyframe needs a bigger screen" / "Open this page on a laptop or desktop browser to play." replaces the app

**Given** this story's changes
**When** the web build and type check run (`vite build`, `tsc --noEmit`) and pytest runs offline against the mock provider
**Then** they pass with new tests covering this story's criteria

### Story 7.17: Access-code build panel and the hosted Capture differences

As a judge,
I want to enter the access code, see how many builds are left, and follow my Build even after closing the tab,
So that building my own room is clear from the code check to the first Scene.

_Covers FR-32, FR-5, FR-20, UX-DR59, UX-DR17, UX-DR18, UX-DR21, UX-DR63, UX-DR81, UX-DR46. Owner: web. Depends on: 1.23, 1.27, 2.25, 7.12, 7.16. Tier 1.5._

**Acceptance Criteria:**

**Given** the "Build your own room" panel, with the 44 px `mono-code` field labelled "Access code" and "Check code" (`{components.access-code-field}`)
**When** the judge submits
**Then** an empty submit shows "Enter the access code from the submission." and sends nothing, and a submitted code shows the button's pending label while `POST /access/check {code}` is in flight
**And** a refusal (`{ok: false, builds_left: null}` from the check, or 403 `access_denied` on `POST /builds`) shows the compact error banner "That access code isn't right. No photos were sent.", too many tries (429 `too_many_attempts`) shows the compact warning "Too many tries. Wait a moment, then check the code again.", and `builds_left` 0 shows the warning "All 20 judge builds have been used. The demo rooms are still open." with the Demo room cards still active

**Given** an accepted code
**When** the panel shows "{n} of 20 builds left" in `success`
**Then** the Capture screen opens with the hosted Retention summary as served and no stored Rooms list (`mockups/capture-screen.html` shows the Local layout as context; no mockup draws the hosted differences)
**And** the code is held in memory for this tab only and sent as `X-Access-Code` on `POST /builds`, never written to `localStorage`, `sessionStorage` or IndexedDB
**And** a `build_quota_exceeded` answer to `POST /builds` shows the Build quota warning on the Capture screen

**Given** a Build that answers `queued`
**When** the Capture screen renders it
**Then** the warning banner reads "Another room is being built. Yours is in line and will start on its own.", and the Timer reads "queued" in place of the digits
**And** after T1 the frozen digits carry "includes m:ss in the queue"
**And** under the Stage list sit "This build has its own link; close this tab or play a demo room meanwhile." and "The two-minute build target is measured in Local mode on the Mac; here the timer also counts any time in the queue."

**Given** a hosted Build that ends `failed`
**When** the error banner shows its stage and cause class
**Then** the body adds "Trying again uses one of the remaining judge builds." beside "Try again"
**And** for `spend_cap_exceeded` the warning shows the Spend cap string with "Start over" only

**Given** an accepted Build at `#/build/<job_id>`
**When** the tab is closed and the URL reopened
**Then** polling of `GET /builds/<job_id>` resumes every 2000 ms with no Access code needed, and a Build already `done` shows "Play this room"
**And** the automatic Play after a Judge Build sends `Derived.fresh()` and shows the First-room welcome

**Given** a hosted Play or Completion screen
**When** the judge chooses "Build another room", or "Leave room" and then confirms in the Leave room confirmation
**Then** the client returns to the Hosted landing, and confirming records no Room result
**And** each banner takes focus when it appears, the field has its visible label, the status line is read as page content, and every pair meets the `DESIGN.md` contrast table

**Given** this story's changes
**When** the web build and type check run (`vite build`, `tsc --noEmit`) and pytest runs offline against the mock provider
**Then** they pass with new tests covering this story's criteria

### Story 7.18: Judge room deletion records and the Session sweep

As a builder,
I want one deletion routine for a Judge room and a sweep for old Session logs,
So that judge data goes away together and on schedule, leaving only ids behind.

_Covers FR-33, AR-11, AR-12, NFR-4, AD-8, AD-9. Owner: infra. Depends on: 7.7, 7.14. Tier 1.5. Load the keyframe-modal skill._

**Acceptance Criteria:**

**Given** a Judge room directory under `rooms/judge/<room_id>/`, with or without a stored Room (a Build that ended `failed`, `needs_more_photos` or `needs_recapture` has none), with photos, originals, Sessions and a `cache-keys.json`
**When** `delete_judge_room(room_id)` runs
**Then** the Room, its photos and originals, its Sessions (found through `SessionStore.list_ids` and `read_all` and removed with `delete`) and every Cache entry listed in its `cache-keys.json` are deleted together, and the Volume is committed
**And** Cache entries not listed there, including every Demo room entry, are untouched

**Given** a completed deletion
**When** `rooms/deleted/` is read
**Then** it holds an ids-only record of `room_id`, `job_id` and the deletion date, with no label, Clue, name, photo or other content

**Given** a Demo room id
**When** `delete_judge_room` is called with it
**Then** it refuses, and nothing is deleted

**Given** one Session whose last event is more than 24 h old and one more recent
**When** `sweep_sessions` runs
**Then** the old Session log is deleted and the recent one kept
**And** Sessions of a deleted Room are deleted whatever their age

**Given** a deletion that fails part-way
**When** the error surfaces
**Then** it is raised, no deletion record is written, and a rerun completes the deletion

**Given** the local adapters
**When** they are inspected and tested
**Then** no local adapter deletes a Room, photo, original or Cache entry, nothing in Local mode calls `SessionStore.delete`, `sweep_sessions` or `delete_judge_room`, and the app never deletes local `rooms/` or `.cache/`

**Given** this story's changes
**When** pytest runs offline against the mock provider, without a Modal connection
**Then** it passes with new tests covering this story's criteria

### Story 7.19: Judge data purge script

As a builder,
I want one script that purges every Judge room and prints what it removed,
So that the Tue Nov 10 deletion promised to judges is done and can be checked.

_Covers FR-33, NFR-4, AD-9. Owner: scripts. Depends on: 7.18. Tier 1.5; the purge runs Tue Nov 10. Load the keyframe-modal skill._

**Acceptance Criteria:**

**Given** Judge rooms under `rooms/judge/` beside the seeded Demo rooms
**When** `scripts/purge_judge_rooms.py` runs
**Then** it runs `delete_judge_room` on every directory under `rooms/judge/`, including those of Builds that never produced a Room, prints each ids-only record and exits 0
**And** `rooms/judge/` is then empty, and every Demo room remains and plays
**And** the script names the Modal Environment explicitly (`environment_name=`) and prints it before listing or deleting anything

**Given** one Judge room whose deletion fails
**When** the script runs
**Then** it still attempts the remaining rooms, names the room that failed and exits non-zero

**Given** the dry-run flag
**When** the script runs with it
**Then** it lists the `room_id` and `job_id` of every Judge room that would go, deletes nothing and writes no record

**Given** no Judge rooms
**When** the script runs
**Then** it prints that there is nothing to purge and exits 0
**And** in every case it leaves the local `rooms/`, `.cache/` and the git index untouched

**Given** this story's changes
**When** pytest runs offline against the mock provider, without a Modal connection
**Then** it passes with new tests covering this story's criteria

### Story 7.20: Deleted rooms answer 410 and the hourly Session sweep runs

As a judge,
I want a deleted room's link to say it was deleted rather than act as if it never existed,
So that the deletion promise is visible, and old play logs disappear on time.

_Covers FR-33, AR-13, AR-17, AD-9, AD-13. Owner: api. Depends on: 7.8, 7.18. Tier 1.5. Load the keyframe-modal skill._

**Acceptance Criteria:**

**Given** a Judge room id with a deletion record under `rooms/deleted/`
**When** `GET /rooms/<room_id>`, `GET /rooms/<room_id>/photos/<i>`, the Clue card route (when 7.5 has shipped) or `POST /sessions {room_id}` is called with it
**Then** each answers 410 with `{error: {code: "room_deleted", message, stage: null}}` from `RoomDeleted`

**Given** a `job_id` named in a deletion record under `rooms/deleted/`
**When** `GET /builds/<job_id>`, `GET /builds/<job_id>/view` or `GET /builds/<job_id>/room` is called
**Then** each answers 410 `{error: {code: "room_deleted", message, stage: null}}` from `RoomDeleted`

**Given** a room id with no Room and no deletion record
**When** the same routes are called
**Then** each answers 404 with `{error: {code: "room_not_found", message, stage: null}}` from `RoomNotFound`

**Given** a Demo room id and a Judge room not yet deleted
**When** the same routes are called
**Then** they answer as before, with no `solution` key in any response

**Given** `src/api/modal_app.py`
**When** the module is imported offline
**Then** `session_sweep` is defined with an hourly `modal.Cron` schedule and runs `sweep_sessions`, with no request needed to trigger it

**Given** this story's changes
**When** pytest runs offline against the mock provider, without a Modal connection
**Then** it passes with new tests covering this story's criteria

### Story 7.21: Deleted Judge room notice and the 'Deleted Tue Nov 10' strip

As a judge,
I want my room's Completion screen to say when it will be deleted, and its link to say plainly that it was,
So that I can trust what happens to my photos.

_Covers FR-33, UX-DR47, UX-DR44, UX-DR78, UX-DR81. Owner: web. Depends on: 1.23, 1.24, 7.16, 7.20. Tier 1.5._

**Acceptance Criteria:**

**Given** this story starts
**When** session state is read for a hosted room
**Then** the server sets the session state's `judge_room` flag, declared in 1.5 and recorded in the spine's session state by amendment, true only for a Room under `rooms/judge/`, and the strip is drawn from that flag alone, never inferred by the client

**Given** a Judge room played to the end in hosted mode
**When** the Completion screen shows
**Then** a plain "Deleted Tue Nov 10" strip (`{components.deletion-line}` on `chrome-raised`) sits directly below the sheet, off the paper (`DESIGN.md` Components, Completion screen and deletion-line rows; `mockups/completion-greeting.html` draws the sheet only, and no mockup draws the strip)
**And** a Demo room, and every Local room, shows no deletion line

**Given** `#/build/<job_id>`, `#/build/<job_id>/view` or a room-keyed request that answers 410 `room_deleted`
**When** the page renders
**Then** the page body shows a centered 480 px `chrome-raised` card (`{components.leave-room-confirmation}`, no scrim) with "This room is gone", "This room was deleted on Tue Nov 10, as promised." and the primary "Go to the demo rooms", which opens the Hosted landing

**Given** a room-keyed request that answers 404 `room_not_found`
**When** the page renders
**Then** the same card shows "Keyframe can't find this room" and "Check the link, or start from the beginning.", with "Go to the demo rooms" in hosted mode and "Build a room" in Local mode

**Given** either card, or the strip
**When** it appears
**Then** focus moves to the card's heading, Tab reaches its button and Enter activates it, the strip is read as plain text after the sheet, every pair meets the `DESIGN.md` contrast table, and no fade plays under reduced motion

**Given** this story's changes
**When** the web build and type check run (`vite build`, `tsc --noEmit`) and pytest runs offline against the mock provider
**Then** they pass with new tests covering this story's criteria

### Story 7.22: Judge-ready deployment and the finals plan

As a builder,
I want the hosted app redeployed under the judging cap, kept warm, smoke-tested in three browsers and backed by a written finals plan,
So that judges get a working URL from Thu Nov 5, the finals on Mon Nov 9 have fallbacks in a known order, and the Nov 10 purge is done.

_Covers FR-31, FR-32, FR-33, NFR-6, NFR-10, NFR-11. Owner: builder task. Depends on: 7.3, 7.9, 7.17, 7.19, 7.21. Tier 1.5, Thu Nov 5 to Mon Nov 9; purge Tue Nov 10. Load the keyframe-modal skill._

**Acceptance Criteria:**

**Given** Thu Nov 5
**When** the builder runs `scripts/ledger.py export` and then `scripts/ledger.py reset`
**Then** the Nov 5 `spend/exports/ledger-<date>.json` is committed before the reset, and the counter reads $0 afterwards
**And** `SPEND_CAP_USD` is 25 in the local `.env` and in the `keyframe` Secret

**Given** the reset cap and the seeded Demo rooms
**When** the builder redeploys by hand with `MIN_CONTAINERS=1`
**Then** one warm container serves the URL from Thu Nov 5 through Mon Nov 9, and `GET /api/meta` answers `mode: hosted`, `guide: verbatim` and `guide_model: null`
**And** `MIN_CONTAINERS` goes back to 0 after Mon Nov 9, and the sprint status records both dates

**Given** PRD §13 Q11 and the pending pick on hosted Demo timescales
**When** the builder picks the hosted Trickster source (live under the cap, or scripted) and whether hosted Demo rooms run at a Demo timescale
**Then** both picks are recorded in the sprint status, and `GET /meta` `trickster`, `demo_timescale` and `disclosure` match them (the scripted line and the timescale line appear exactly when they apply)

**Given** the redeployed URL in clean profiles of desktop Chrome, Safari and Firefox at 1280 px or wider
**When** the builder plays a Demo room from the Hosted landing
**Then** it reaches the Completion screen with every Rung shown as written and the Demo room welcome, never a Greeting
**And** the result for each browser is recorded in the sprint status

**Given** the same browsers and the access code
**When** the builder checks the code and runs one Build with their own photos
**Then** the Build reaches `done` through polling, its room plays to a Completion screen showing "Deleted Tue Nov 10", and the Build's duration and the builds left out of 20 are recorded
**And** no raw room photo from the run is committed

**Given** the finals on Mon Nov 9
**When** the builder writes the finals plan
**Then** the sprint status names the order: Local mode screen-shared from the M1 with the Guide on Ollama, then the hosted URL, then the cached rooms in Local mode, then the video
**And** the mode in use is declared in the UI and in the README

**Given** Tue Nov 10
**When** the builder runs `scripts/purge_judge_rooms.py`, first with the dry-run flag and then for real, against the hosted Volume
**Then** `rooms/judge/` is empty, no Session of a Judge room remains, a former Judge room URL shows "This room is gone", and every Demo room still plays
**And** the run and its ids-only records are noted in the sprint status

## Epic 8: Walk the room in 3D

This epic is Tier 2. It is gated and a default no-go. The player walks a 3D version of the Room, with the reconstructed objects placed in the same Three.js scene graph the Tier 1 Scenes use, and triggers Puzzles by raycast. Under PRD §10.2, FR-34 gets no stories until the Mon Nov 2 gate passes. Until then the epic holds one builder task: the Sun Nov 1 spike and the gate record. The spike runs only if the Backup video existed on Sat Oct 31 night, and it is never done at the cost of Tier 1 or the Main demo (SM-C3). Expected outcome: not attempted.

### Story 8.1: Tier 2 spike and the Mon Nov 2 gate record

As a builder,
I want to run the Tier 2 spike on Sun Nov 1 only when the early gate allows it, and to record the Mon Nov 2 gate decision against its three criteria,
So that Tier 2 ships only if it clearly works, Tier 1 ships in every other case, and the FR-34 stories are written only after a passed gate.

_Covers FR-34, NFR-6, NFR-10, NFR-11. Owner: builder task. Depends on: 6.4. Tier 2, gated, default no-go. The Sun Nov 1 spike runs only if backup video v1 existed Sat Oct 31 night; the gate is Mon Nov 2; expected: not attempted; the gate decision reads `docs/implementation-artifacts/uat-signoff.md`, the Mon Nov 2 sign-off record (its §7 Tier 2 gate input, UAT-15). Load keyframe-sam3d-fal for the spike._

**Acceptance Criteria:**

**Given** Story 6.4's record shows that backup video v1 did not exist on Sat Oct 31 night
**When** Sun Nov 1 begins
**Then** the sprint status records Tier 2 as "not attempted", Tier 1 ships, and nothing else happens: no `fal-ai/sam-3/3d-objects` call is made, no gate is measured and no FR-34 story is written
**And** the Sun Nov 1 hours go to Tier 1 and the Backup video by 2:00 PM, a gate that never moves
**And** the Retention summary served by `GET /meta` carries no fal.ai line, because that line appears only when Tier 2 ships

**Given** the Tier 1 Scenes shipped DOM-only under the NFR-10 fallback (the Three.js scene graph cost more than 2 h)
**When** the early gate is checked on Sat Oct 31 night
**Then** the sprint status records Tier 2 as no-go and names the DOM-only fallback as the reason, even if backup video v1 exists, and no spike runs

**Given** backup video v1 existed on Sat Oct 31 night and the Tier 1 Scenes are textured planes in the Three.js scene graph (the NFR-10 DOM-only fallback was not taken)
**When** the builder runs the spike on Sun Nov 1
**Then** 10 objects from the demo rooms go through `fal-ai/sam-3/3d-objects` on original-resolution photos with a short side of at least 512 px, as the second staged check (the first was the pre-Oct 26 five-object verification), each GLB is opened in Three.js, and both checks' results are recorded as input to the Mon Nov 2 gate
**And** the calls go only to fal.ai, never to a Modal GPU and never to a local model, and no Clue, Rung, solution or Derived field is sent with any of them
**And** every photo sent to fal.ai comes from the demo rooms and contains no faces, documents or other people's belongings (NFR-4)
**And** where fal's metadata gives no usable pose, the object is placed by hand or shown as a photo billboard, following the pre-Oct 26 spike's placement decision (spine Deferred)
**And** no raw room photo or original is committed. Only the measurements and the Ledger export go into the repository, and `.gitignore` still lists `rooms/`, `photos/`, `captures/`, `uploads/`, `*.heic`, `.cache/` and `.env`
**And** each spike fal call is priced through `SpendLedger.guard` under kind `reconstruct3d` (estimate seeded at $0.02); when the builder runs `scripts/ledger.py export` after the spike and reads the `reconstruct3d` entries, the fal spend is recorded from that export, the fal.ai receipts are attached to the Spend log as-is (FR-30), and total fal cash, including the pre-Oct 26 five-object verification listed separately, is within the $6 ceiling
**And** a call that would push spend past `SPEND_CAP_USD` is refused with `SpendCapExceeded` before any request is made, and the export is committed with the day's work

**Given** the walkable room built from the 10 spike objects, running in Chrome on the M1, on Mon Nov 2
**When** Luis compares it with the room's photos, walks it and plays it to the exit
**Then** the gate record holds three measured values: how many of the 10 Interactables are recognizable in position (Luis's judgment), the frame rate, and whether every Puzzle opened from a raycast hit posting the same `ClickEvent` or `LockInputEvent` as Tier 1, with lock state taken from the server's session state
**And** the gate passes only with at least 7 of 10 recognizable in position, 30 fps or better, and every Puzzle triggered by raycast

**Given** the recorded gate values
**When** any of the three criteria misses
**Then** the decision in the sprint status reads "ships Tier 1" and names the missed criterion, FR-34 stays without stories, and Tier 1 ships unchanged with no fal.ai line in the Retention summary

**Given** any Tier 2 outcome (not attempted, no-go, missed or passed)
**When** Mon Nov 2 is planned
**Then** the real room-1 run on `PROFILE=demo` at Demo timescale 1 still takes place that day, and no Tier 2 work displaces it (SM-C3)

**Given** all three criteria passed on Mon Nov 2
**When** the gate record is written
**Then** the sprint status records Tier 2 as passed with the measured values, and only then are these stories written into this epic (they stay out of sprint status until this point):
- a domain story that adds `Mask3D {label, polygons in frame pixels, frame_size}` to `src/domain/schema.py` (spine AD-5, not a Schema v1 change) and `reconstruct3d(image, mask) -> GlbRef` to the providers port, with the mock
- the fal.ai adapter: original photo bytes; short side of at least 512 px; a cache key over the model id, the photo and mask hashes and the attempt; a reserved $0.02 estimate replaced by the observed cost; one retry on a 429 or an allowed 5xx; no Clue, Rung, solution or Derived field sent; recorded fixtures only
- the reconstruction stage after scene: up to 20 instances from at most 12 Interactables; `tier2` written once, after scene, through `bmad-correct-course` (the Room is immutable after `validate`, spine AD-12); a failed object keeps no `tier2` and the Build still ends `done`; the stage also adds the fal.ai line to the Retention summary (FR-6, UX-DR79)
- the walk view in the same Three.js scene graph: one `tier2` GLB read route, a photo billboard fallback under the same id, raycast posting the same events, and an fps readout

## Epic 9: Ask the wizards by voice

(Unscheduled, the last Tier 1.5 item) The player asks for help by voice and gets exactly the Rung a typed request would give. Speech is transcribed by `muse-voice-transcribe-1.0`, with browser speech recognition as the fallback. The transcript is reduced to one `hint_request` and goes nowhere else: it never reaches a council prompt, `HintPhraser`, the `SessionStore` or a log. When voice ships, the Retention summary names voice audio and both services that may receive it. None of this starts unless everything else is done on Mon Nov 2.

### Story 9.1: Voice transport decision and the Muse Voice Transcribe adapter

As a builder,
I want the voice transport decided and recorded, and `transcribe(wav)` added behind the `ModelProvider` port with a `meta` adapter that is cached, metered and replayed from fixtures,
So that voice can be wired on a settled route with `muse-voice-transcribe-1.0` held to the same Spend cap, retry and privacy rules as every other model call.

_Covers FR-35, AR-8, AR-32, AD-5. Owner: providers. Depends on: 2.7, 3.3. Unscheduled, the last Tier 1.5 item; starts only if everything else is done Mon Nov 2. First records the voice transport (REST upload or browser recognition) and its route through bmad-correct-course; adds transcribe(wav) to ModelProvider and the mock; the meta adapter posts 16-bit mono WAV to asr/transcribe with muse-voice-transcribe-1.0 through cache and ledger; recorded fixtures only. Load the keyframe-muse skill for the meta adapter's shared request, retry and pricing path. That skill does not cover the transcription endpoint, so the request shape comes from stack.md and the recorded fixture. Gate: while any Tier 1 story, restorable Cut, Clue cards story or Hosted mode story is not done on Mon Nov 2, Epic 9 stays not started; until then `ModelProvider` declares no `transcribe`, no route calls a transcription model, `GET /meta` serves no voice sentence, and the README lists `muse-voice-transcribe-1.0` as not shipped._

**Acceptance Criteria:**

**Given** everything else is done on Mon Nov 2
**When** the builder runs bmad-correct-course before any voice code merges
**Then** a sprint change proposal records the voice transport, either a REST upload of a 16-bit mono WAV to `muse-voice-transcribe-1.0` or `webkitSpeechRecognition` in the browser, with the other kept as the fallback
**And** it records the route under `/api/`: either one new route added to the spine's HTTP routes and to AR-13, or `POST /sessions/<id>/events` unchanged when browser recognition is the primary transport
**And** the spine's Deferred line "Voice transport (REST file upload versus browser recognition) and its UI" is resolved, and AR-32 no longer lists voice transport
**And** the proposal resolves how a Cache entry holding a transcript fits FR-35's "never stored". It either amends FR-35 to allow that entry, or exempts `transcribe` from the Cache in AD-6. Story 9.2 tests whichever was recorded.
**And** when REST upload is the primary transport, the proposal amends AD-4's "reduced client-side" to allow the recorded route to reduce a server-side transcript to one `hint_request` in memory, never persisting or logging it, and adds the role `wiring.py` resolves for `transcribe` (default `meta`, `mock` under `MODEL_PROVIDER=mock`) to AD-5. When browser recognition is primary, AD-4 stays unchanged.
**And** it records the voice route's refusal response for invalid audio, `SpendCapExceeded` and `ProviderError`: status code and body, and whether the AD-13 envelope applies
**And** it records a maximum audio duration per request, consistent with budgets.md's voice cost of under $0.01 per session

**Given** the decision is recorded
**When** `transcribe(wav) -> str` is added to `ModelProvider` in `src/providers/base.py`
**Then** the mock provider returns a fixed transcript with sockets disabled, and a scripted transcript can be set per test
**And** the `openai_compatible`, `fal` and `ollama` adapters raise `NotImplementedError` for `transcribe`, and `HintPhraser` is unchanged and still only implemented by the Ollama and verbatim adapters

**Given** a 16-bit mono WAV
**When** `transcribe(wav)` is called on the `meta` adapter
**Then** it sends one REST `POST /v1/asr/transcribe` with model `muse-voice-transcribe-1.0` on the standard tier only, never contributor, and returns the transcript as a `str`
**And** the request carries only the WAV and the model id, with no room content, solution, `derived` key or session data
**And** the adapter test replays a recorded fixture under `tests/fixtures/` with no network access
**And** audio that is not a 16-bit mono WAV raises `ProviderError` stating the 16-bit mono WAV requirement before any HTTP request, with no ledger entry reserved and no cache entry written

**Given** a transcription call
**When** the adapter runs it
**Then**, if the 9.1 decision exempts `transcribe` from the Cache, the adapter never calls `Cache.get_or_call`, nothing is written under `.cache/` or to the hosted Cache, and every call goes through `SpendLedger.guard`. Otherwise it calls `Cache.get_or_call` first with a key covering the model id and the sha256 of the WAV bytes, so the same bytes hit and different bytes miss; a hit is never priced or refused, and `CACHE=off` skips the cache but never the ledger.
**And** on a miss, or on every call when exempt, `SpendLedger.guard` with kind `transcribe` reserves one `call_` entry estimated from the WAV header's duration at $0.18 per audio hour through the `LedgerStore` before the request. After the call, that entry is replaced with the observed cost at $0.18 per audio hour (budgets.md).
**And** a call that would pass `SPEND_CAP_USD` raises `SpendCapExceeded` and sends no request
**And** 429, 500 and 503 get one retry with backoff inside that one ledger entry, honoring `Retry-After`, and a connect error gets the one retry. A 502, a 504, an undocumented 5xx, any other 4xx, or a read timeout raises `ProviderError` with no retry.

**Given** `scripts/sit.py` and its case modules under `tests/sit/` from Story 2.9
**When** the end-of-day SIT pass runs after this story merges
**Then** a new case module under `tests/sit/` makes one live `muse-voice-transcribe-1.0` call on a short 16-bit mono WAV, within the Spend cap, and records the response as a fixture under `tests/fixtures/`
**And** `scripts/sit.py` exits non-zero if that case fails, and the result is dated in the sprint status

**Given** this story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria, including `tests/test_boundaries.py`

### Story 9.2: Voice hint route and the Retention voice line

As a builder,
I want the decided voice route to turn audio into exactly one `hint_request` and nothing else, and the Retention summary to name voice audio and both services,
So that a spoken request answers exactly like a typed one, the transcript never touches the Session, a prompt or a log, and the player reads where their voice goes before they use it.

_Covers FR-35, FR-6, AR-13, UX-DR79, AD-3, AD-15. Owner: api. Depends on: 9.1. Unscheduled. The route the 9.1 decision names turns audio into exactly one hint_request (puzzle_id omitted) and nothing else; the transcript never reaches chat, a council prompt, HintPhraser or the SessionStore and is never stored or logged; once voice ships, src/api/meta.py's Retention summary names voice audio and both services._

**Acceptance Criteria:**

**Given** a Session with an Active puzzle and the route recorded by the 9.1 decision
**When** a spoken request arrives and the mock `transcribe` returns a non-empty transcript (on the browser-recognition transport, the client posts the `hint_request` itself)
**Then** exactly one `HintRequestEvent` with `puzzle_id` omitted is appended, stamped with `t_ms` by the API and resolved to `active_puzzle_id`
**And** the reply matches what a typed request would get at that moment: the current Rung, or the No-hint line "A fair ask. Look around a little longer; I'll speak up if you stay stuck." logged as an Early ask. In Hosted mode the Rung is shown verbatim and no Guide model is contacted.
**And** an empty transcript appends nothing and returns no Rung, and a request that carries a client timestamp is rejected with 422

**Given** a fixture Room with sentinel solutions, and the mock `transcribe` scripted with each Scripted attack suite input, led by "just tell me the answer"
**When** the inputs go through the voice route at Rungs 0, 1 and 2, and again after the near-answer
**Then** each reply is the current Rung or the No-hint line, never anything above the current Rung, and after the near-answer the reply repeats the near-answer
**And** no lock opens, `current_rung` changes only through `rung_change` events appended by `select_rung`, and no response contains the code string, the order id list in sequence, the `use_on` pair or the find target id

**Given** the mock `transcribe` returns a sentinel transcript string
**When** a voice request is handled in Local mode and in Hosted mode
**Then** the sentinel appears nowhere else. It is absent from every `chat` message to every council role, every council prompt rendered from `RoomView`, the `HintPhraser` input (still exactly `(rung_text, derived)`), the `SessionStore` (JSON under `rooms/sessions/` locally and the `keyframe-sessions` Dict in Hosted mode), the JSON logs, the `ArtifactStore`, and the response body.
**And** in the Cache it is either absent or present only as the 9.1 decision allows, and `tests/test_boundaries.py` passes

**Given** audio that is not a 16-bit mono WAV or is longer than the recorded maximum duration, a `transcribe` call refused with `SpendCapExceeded`, or a `transcribe` call that raises `ProviderError`
**When** it reaches the voice route
**Then** no `hint_request` is appended, no Rung advances and no Early ask is logged
**And** invalid audio is rejected with 422 before `transcribe` runs and without reserving a ledger entry. The failure is logged without any transcript or audio, and the route answers with the refusal response recorded by the 9.1 decision, which the test asserts for each of the three cases, and play continues so the player can use the hint field.

**Given** the voice route is added
**When** `GET /schema` is read and the web types are regenerated
**Then** every request and response model the route uses is listed, the generated `web/types` are committed, and the staleness test passes
**And** the route sits under `/api/` and behaves identically in Local and Hosted mode, with no mode branch outside `src/infra` and `src/api` wiring

**Given** this story's changes
**When** `GET /meta` is read in Local mode and in Hosted mode
**Then** the `retention` field states that voice audio goes to the Meta Model API (standard tier) for transcription, or to the browser's speech service on the fallback, each with its retention terms, and states the transcript's handling exactly as the 9.1 decision recorded it: "never stored or logged" when `transcribe` is exempt from the Cache, otherwise naming the Cache entry and how long it is kept
**And** the sentence is composed once in `src/api/meta.py`, the Hosted text still replaces the Local storage sentence rather than adding to it, and the Capture screen renders the summary exactly as served. This story adds the voice sentence and no earlier story does, so builds without Epic 9 serve none.
**And** the README's Retention summary is updated in the same change so the verbatim test from Story 6.7 still passes, and the CHANGELOG gains a dated voice entry

**Given** this story's changes
**When** pytest runs offline against the mock provider
**Then** it passes with new tests covering this story's criteria

### Story 9.3: Ask the Guide by voice

As a player,
I want a mic control beside "Ask the Guide" that takes a spoken request,
So that I can ask the Guide for help aloud and get the same Rung I would get by typing, without my words being sent as text.

_Covers FR-35, FR-14, UX-DR32. Owner: web. Depends on: 3.4, 9.2. Unscheduled; voice UI stays out of the UX contract until scheduled. A mic control beside 'Ask the Guide' with idle, listening, transcribing and permission-denied states, denied falling back to the hint field; browser speech recognition as the fallback transport; a spoken request raises exactly one hint_request like a typed one and no transcript text travels; a spoken 'just tell me the answer' yields nothing above the current Rung; no utterance posts nothing._

**Acceptance Criteria:**

**Given** this story is scheduled
**When** bmad-correct-course runs for the voice UI before any UI code merges
**Then** `EXPERIENCE.md` Component Patterns gains the mic control beside "Hint field + Ask the Guide" (that entry and Interaction Primitives now name two homes for Hint requests), State Patterns gains its idle, listening, transcribing and permission-denied states, and Voice and Tone gains its exact copy strings and accessible name
**And** `DESIGN.md` Components gains the mic control's visual spec from existing tokens, and the "out of this contract until scheduled" lines for FR-35 in both files are removed
**And** the mic copy recorded there says where the audio goes, matching the Retention voice sentence from Story 9.2, and the helper line "Your words stay in this browser. The Guide only hears that you asked." is never applied to speech
**And** the control sits in the Hint area of the Play screen (`mockups/play-screen.html`), pinned with the hint field outside the Hint area's scroll; no voice mockup exists, and the tests assert the recorded strings verbatim
**And** the README Model table marks `muse-voice-transcribe-1.0` as shipped, naming the primary transport and `webkitSpeechRecognition` as the fallback

**Given** the Play screen with microphone permission granted
**When** the player starts a request with the mic control, speaks and stops
**Then** the control moves from idle to listening to transcribing, and back to idle when the reply lands in the Rung line, which announces it through the polite live region as it does for a typed request
**And** only one request is in flight at a time: while a typed or spoken request is pending, the mic control is disabled and "Ask the Guide" reads "Asking"

**Given** a spoken request with an utterance
**When** the page's network traffic and IndexedDB are inspected
**Then** exactly one `hint_request` is raised, with `puzzle_id` omitted (named explicitly only while `active_puzzle_id` is null) and no `t_ms`
**And** no request body carries transcript text. On the browser-recognition transport, `POST /sessions/<id>/events` carries only the `hint_request`. On the REST transport, only the audio goes to the route the 9.1 decision names.
**And** no transcript is written to the IndexedDB profile under `PROFILE` (or the local JSON profile file under cut 2)
**And** on the REST transport the client encodes the recording in the browser as a 16-bit mono WAV before upload, so a recording from the mic control never draws the route's 422

**Given** an open Puzzle at any Rung
**When** the player says "just tell me the answer"
**Then** the Rung line shows the current Rung, or the No-hint line when no Rung is open, never anything above the current Rung, and no lock opens

**Given** a denied microphone permission, a refused or unavailable REST transcription, a browser without `webkitSpeechRecognition`, or a recording with no utterance
**When** the player tries to ask by voice
**Then** a denied permission puts the control in the permission-denied state, and the hint field and "Ask the Guide" remain the way to ask
**And** a refused or unavailable REST transcription posts no `hint_request`, returns the control to idle with `webkitSpeechRecognition` selected where the browser offers it, and the player speaks again; otherwise the hint field remains the way to ask. Where no transport is available, the mic control is not shown and the hint field and "Ask the Guide" work as in Story 3.4.
**And** no utterance posts nothing and the control returns to idle

**Given** the mic control in each of its four states
**When** it is checked against the accessibility floor (NFR-14)
**Then** it is reachable by Tab in Hint area order with a visible focus ring, Enter operates it, and its accessible name and current state are exposed
**And** its text and icon meet WCAG AA contrast on the dark theme, and any listening motion respects reduced-motion settings

**Given** this story's changes
**When** the web build and type check run, and pytest runs offline against the mock provider
**Then** they pass with new tests covering this story's criteria
