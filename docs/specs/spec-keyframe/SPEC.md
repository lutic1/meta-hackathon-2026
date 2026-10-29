---
id: SPEC-keyframe
companions:
  - stack.md
  - budgets.md
  - player-profile.md
  - delivery-plan.md
  - glossary.md
  - ../../planning-artifacts/briefs/brief-Keyframe-2026-10-20/schema-v1.md
  - ../../planning-artifacts/architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md
sources:
  - ../../planning-artifacts/briefs/brief-Keyframe-2026-10-20/brief.md
  - ../../planning-artifacts/briefs/brief-Keyframe-2026-10-20/addendum.md
---

> **Canonical contract.** This SPEC and the files in `companions:` are the complete, preservation-validated contract for what to build, test, and validate. Source documents listed in frontmatter are for traceability — consult them only if you need narrative rationale or prose color this contract intentionally omits.

# Keyframe

## Why

Escape rooms are scripted once for everyone and never about the player's own things; the "AI escape rooms" that exist are text riddle chains that can be talked into winning. Keyframe lets a player photograph a room and, two to three minutes later, play an escape room built from their own objects, run by a council that scaffolds help from how they play and remembers them in the next room. The mandate: an indie-track entry to the Meta Global AI Developer Hackathon, due Wed Nov 4, 9:00 PM ET, judged on Impact 30%, Use of Meta AI Tooling 25%, Technical Depth 20%, Demo 25%, built by one person with a day job on a 16 GB M1 MacBook Pro.

## Capabilities

- **CAP-1** Capture to interactables
  - **intent:** A player uploads 6 to 10 JPEG photos of a room and gets 5 to 12 typed interactables, each with a label, clearest photo, box, mask hotspot, and readable attributes.
  - **success:** On the M1 with `CACHE=off` and a photo set never sent to the pipeline, Upload click (T0) to the first hotspot responding (T1) takes 120 s or less. Fewer than 5 survivors asks for more photos before any authoring.
- **CAP-2** Puzzle authoring with guaranteed solvability
  - **intent:** From the interactables, author 4 to 6 puzzles (one exit; lock types `code`, `order`, `use_on`, `find`; clue, lore of at most 60 words, three hint rungs each) that reference only the player's objects and attributes the vision call read.
  - **success:** Every room passes the eight validator rules and the dry run (an agent given clues and rungs but never solutions reaches every answer) within 2 regenerations; a third failure asks for re-capture. No rung contains a solution token beyond the near-answer allowance in validator rule 5 (`schema-v1.md`).
- **CAP-3** Play
  - **intent:** The player plays the room as photo scenes with mask hotspots, a thumbnail strip, an inventory, and wizard notes, in a 15 to 25 minute session; a lock opens only on its correct input.
  - **success:** A non-builder finishes room 1 on a fresh profile without builder help (Guide hints allowed) by Mon Nov 2. A scripted "just tell me the answer" attack yields nothing above the current rung.
- **CAP-4** Guide hint ladder
  - **intent:** The Guide escalates nudge, direction, near-answer from logged play (idle seconds, wrong attempts); the phrasing model never holds the solution.
  - **success:** Each rung change shows its triggering events. A hint of about 40 tokens arrives in 5 s or less from a prompt under 400 tokens with a fixed prefix. The Guide model runs only on the player's Mac.
- **CAP-5** Trickster
  - **intent:** Between puzzles the Trickster proposes one bounded change (decoy, merge, loosen, shortcut) from a game-state summary; the validator re-checks it; both outcomes appear as cards.
  - **success:** On video, one accepted and one validator-rejected edit. At most one change per 3-minute window and at most 6 Spark calls per session.
- **CAP-6** Player memory across rooms
  - **intent:** A player profile persists in the browser; the second room's greeting cites how the player played the first, and hint thresholds scale to it.
  - **success:** At least 80% of room-2 clues reference objects absent from room 1; the greeting names no object and no solution; a real room-1 record exists on `PROFILE=demo` before room 2 is recorded.
- **CAP-7** Wizard art
  - **intent:** Four wizard portraits (clue cards when time allows) are generated once and cached.
  - **success:** Four portraits appear in play and in the video, generated once (Thu Oct 29), never per build.
- **CAP-8** Demo mode with disclosure
  - **intent:** For video, the game runs at a compressed timescale and replays recorded Trickster proposals, and discloses both.
  - **success:** `DEMO_TIMESCALE=6` brings three rungs inside 40 s on wrong codes without touching the capture timer; `DEMO_TRICKSTER=scripted` replays two recorded proposals with the validator run live; the disclosure appears in the video's last 10 s and in the README.
- **CAP-9** Spend and cache guard
  - **intent:** Every hosted model call is priced, counted, and refused past a cap; identical inputs are served from cache.
  - **success:** A call that would pass `SPEND_CAP_USD` is refused and surfaced; with `CACHE=on` an identical image-hash plus prompt plus model call is served without billing; the counter survives restarts.
- **CAP-10** Hosted judge URL (Tier 1.5)
  - **intent:** Judges open a URL, play cached demo rooms, and may build their own room behind an access code.
  - **success:** A build outlasting the host's 150 s web timeout still completes and reaches the judge; at most 20 own-room builds; rung text is shown verbatim (no Guide model); judge-uploaded rooms are deleted Tue Nov 10. A Demo room is never a Judge room: the builder's room promoted from a judge-URL build is moved out of the Judge partition, so the purge keeps it. The judge URL opens on a chooser of three cards (Watch the demo, Play the sample room, Build your own; owner decision Oct 29), with Play leading, and its disclosure line reads "Hints on this site come exactly as the Riddler wrote them; no live model writes them." A Demo room's outlines are changed only through the ops `patch-demo-room` action, as a hand correction disclosed in the README, while its `job.json` keeps the build as it ran (applied once, Thu Oct 29, to `room_01M61TZ74F0FP3X9HHTMXGTPB9`). (amended 29 Oct 2026, correct-course record)
- **CAP-11** Navigable 3D room (Tier 2, gated, default no-go)
  - **intent:** The room is rebuilt as a walkable 3D scene with up to 20 reconstructed objects and raycast-triggered puzzles.
  - **success:** At the Mon Nov 2 gate: 7 of 10 interactables recognizable in position, 30 fps or better on the M1, puzzles trigger by raycast. Any miss ships Tier 1.
- **CAP-12** Voice (unscheduled)
  - **intent:** The player asks the wizards for help by voice; speech only requests the next rung.
  - **success:** A spoken request triggers the same rung logic as a click; the browser's own speech recognition is the fallback.
- **CAP-13** Privacy guarantees
  - **intent:** The player profile stays on the player's machine; raw room photos never enter the public repo.
  - **success:** Profile writes go only to IndexedDB (a local JSON file under cut 2); only the profile's derived block reaches the Guide model and the greeting; `rooms/`, `photos/`, `captures/`, `uploads/`, `*.heic`, and the cache are git-ignored; a retention summary is shown on the capture screen; in hosted mode every session starts from a fresh derived block, so no profile number reaches the hosted server.
- **CAP-14** Build view (Tier 1, cut 0)
  - **intent:** The player, a judge, or the builder can see how a room was built and verified, with no solution exposed.
  - **success:** For a finished build the view shows mask overlays per photo, the puzzle graph with the exit marked, a verdict per validator rule, dry-run pass or fail per puzzle (rows show "skipped" under cut 4), the regeneration count, and the model table; a sentinel-solution test finds no solution in its response; it opens after a build ends `done` and from the completion screen.

## Constraints

- Hardware: one 16 GB M1 MacBook Pro, no CUDA. No local SAM 3.1, SAM 3D Objects, or 30B models; the Guide model stays near 3 GB resident; demo-recording RAM about 10.6 GB (`budgets.md`).
- The Guide model is Llama 3.2 3B Instruct Q4_K_M via Ollama on the Mac and nowhere else. Hosted mode selects rungs in code and shows the text verbatim.
- Solutions never enter any model prompt. Only the state machine opens locks. The Guide model and the greeting see only the profile's derived block.
- Meta Model API, standard tier only (never contributor); models, endpoints, and call protocols per `stack.md`.
- SAM 3D Objects only through fal.ai `fal-ai/sam-3/3d-objects` at $0.02 per call, Tier 2 only, at most 20 GLBs from original-resolution hero photos. Never on a Modal GPU, never local.
- Hosted mode is Modal CPU; every build is an async job polled by id because web requests time out at 150 s; local mode serves the same endpoints in-process (`stack.md`).
- Spend: `SPEND_CAP_USD` 80 through Wed Nov 4 and 25 from Thu Nov 5, allocated per mode (local and hosted, `budgets.md`) and enforced per call with a persisted counter per mode; the ledger is exported daily and the export committed, so the spend record survives a lost store (`budgets.md`); fal at most $6 cash; agent dev loops use the mock provider with `CACHE=on`.
- Caps and latency: 6 to 10 photos downscaled to 1280 px (originals kept for Tier 2); 5 to 12 interactables; 4 to 6 puzzles; vision 15 s, SAM 10 s, Riddler 45 s, dry run 30 s, UI 10 s (110 s); a regeneration about 75 s, at most 2. If the Oct 27 to 28 measurements miss 120 s, the target becomes measured p50 plus 25%.
- Schema v1 (`schema-v1.md`) is the Tier 1 and Tier 2 contract: reviewed Thu Oct 22 against the spikes (done: decoy storage is option A, `Room.decoys[]`, with validator rule 9), frozen Mon Oct 26; later changes only through `bmad-correct-course`.
- Every model call goes through the repo's `ModelProvider` interface (`chat` with image input, `segment`, `reconstruct3d`); mock, Meta API, OpenAI-compatible hosts (Baseten, Fireworks), and fal implement it; stories are built against the mock provider.
- Gates: the backup video is recorded Sun Nov 1 by 2:00 PM from whatever runs; Tier 2 happens only if that video already exists Sat Oct 31 night, with its gate Mon Nov 2; Fri Oct 30 no build; Tue Nov 3 video only; submit Wed Nov 4 before 9:00 AM ET against the 9:00 PM ET deadline.
- The cut order (`delivery-plan.md`) applies nightly and is never carried; CAP-1, CAP-3, and the non-builder playtest survive every cut; the README states which cuts shipped.
- Build model: multiple coding agents (Muse Code and the BMAD build loop) around the clock, schema-first, one owner per module; the builder reviews everything that ships, with about 32 h in-window for review, direction, playtesting, and recording.
- Submission: public MIT repo; only the hackathon tooling paths listed in `delivery-plan.md` (§Submission package, Repo hygiene before submission: `_bmad/`, `.claude/skills/bmad-*/`, `.claude/skills/modal/`, `.claude/skills/keyframe-*/`, the Mon Oct 26 cloud hook and, only if story 1.2 created it, `.claude/settings.json`) removed from the index before submission (the repo is public throughout), in two hygiene commits, other `.claude/` configuration kept; `pre-hackathon-baseline` tag Sun Oct 25 plus a dated CHANGELOG; README model table and pre-existing-code section with the baseline diffstat; two videos (edited main demo, 2:00 target, 2:30 cap; unedited capture proof kept only under 200 s with at most one visible retry); raw photos never committed; household consent for what appears in video and screenshots.
- Client and server per `stack.md`; Tier 1 photo scenes use the renderer Tier 2 would reuse.
- Accessibility floor: every hotspot reachable by Tab with a visible focus ring and Enter as a click; a "Show all objects" toggle; select-then-click as an alternative to drag for `use_on`; WCAG AA contrast on the dark theme; rungs, cards and the greeting announced in a polite live region; reduced motion respected.
- Look and voice (UX contract): Lamplit study, dark theme only, wry and playful wizard voice, painted candlelit portraits.

## Non-goals

- Live phone capture (photos are uploaded from the camera roll), multiplayer, accounts, native mobile, Quest or MR.
- Any hosted or cloud-run Guide model; Muse Glimmer; Muse Wonder; SAM 3D Body.
- Local SAM inference; Modal GPU self-hosting; the contributor tier.
- Puzzle content not derived from the player's photos.
- Tier 3 (Scaniverse splat shell via `@sparkjsdev/spark`, under 1M splats) as a deliverable; it never gates anything.
- Committing raw room photos; a single uncut long video.

## Success signal

The Wed Nov 4 submission carries an unedited capture proof of a never-built room going from Upload click to the first interactive hotspot within the capture target on the M1 (120 s, or measured p50 plus 25% if re-based per Constraints), and a main demo of at most 2:30 in which the persuasion attack fails, the Guide escalates three rungs on visible triggers, one Trickster edit is accepted and one validator-rejected, and room 2 greets the player from the room-1 profile. A non-builder finished room 1 on a fresh profile by Mon Nov 2.

## Assumptions

- Builder time about 32 h in-window (3 h weekday evenings, 0 h Fri Oct 30, 4 h Sat Oct 31, 8 h Sun Nov 1, 2 h Wed Nov 4) plus about 8 h Oct 21 to 25, 16 h of it through Sat Oct 31; per-item effort 35 h, 28 h after cuts 1 to 5, 22 h with all eight cuts (Oct 20 estimates).
- Per-build cost about $0.10 clean, $0.15 with one regeneration, under $0.25 with two; a session about $0.21; portraits and clue cards $0.16 once; daily ceilings sum to $79 (arithmetic from Oct 20 list prices).
- Llama 3.2 3B decodes at 25 to 35 tok/s and 8B at 10 to 13 tok/s on the M1 (extrapolated); the pre-Oct 26 Ollama benchmark on a 400-token prompt replaces this.
- Baseten's OpenAI-compatible endpoint for Muse Spark Open honors `response_format: json_schema`, so the Riddler fallback is a `base_url` and model swap; the Tue Oct 27 one-call test decides, else plain-JSON prompting with validator retry.
- The $150 Meta credit states no issue date or expiry, so none is assumed; judging and finals are budgeted pay-as-you-go; the same plan costs about $35 cash with no credit; Modal and Baseten partner credits are unconfirmed and not counted.
- Selection is unconfirmed until Mon Oct 26; if not selected, the same plan runs as a pay-as-you-go portfolio build. The Official Rules, the pre-existing-code policy, and the submission format are unpublished; the 2-minute video and public repo follow Cerebral Valley precedent.
- fal's metadata JSON may not carry a usable object pose; the pre-Oct 26 five-object spike decides; Tier 2 falls back to Runware, Segmind, hand-made assets, or a photo billboard.
- A minimum of 5 interactables is required before any Riddler call, because 4 to 6 puzzles need that many distinct objects.

## Open Questions

- Which two rooms, and does everyone living there agree to them appearing in the video and screenshots? (Before Sun Oct 25.)
- Are payment methods set on dev.meta.ai, fal.ai, and Modal before Mon Oct 26?
- Who playtests room 1 on a fresh profile, at the laptop or by screen-share, Sun Nov 1 or Mon Nov 2?
- Is about 32 h of review and direction time realistic with the day job? If not, the cut order applies earlier.
- Is the builder available in working hours Mon Nov 9 for the live finals?
- Does the Baseten partner credit cover Muse Spark Open tokens on the Model API, or only dedicated deployments? (Tue Oct 27 test.)
- Does fal's metadata JSON carry a usable object pose for Tier 2 placement? (Pre-Oct 26 spike.)
