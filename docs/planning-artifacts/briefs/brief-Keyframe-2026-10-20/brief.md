---
title: "Product Brief: Keyframe"
status: final
created: 2026-10-20
updated: 2026-10-22
---
# Product Brief: Keyframe

Luis Ticas · 2026-10-20 · Indie track, Meta Global AI Developer Hackathon (Cerebral Valley), Oct 26 to Nov 4

## Executive Summary

Keyframe turns a room you photograph into a playable escape room in 2 to 3 minutes. SAM 3.1 finds the objects; four "wizard" roles (the council) write a puzzle chain from them and run the game: Architect, Riddler, and Trickster on Muse Spark 1.3; the Guide picks hint rungs in code and phrases them on Llama 3.2 3B running locally through Ollama; the player profile stays on your machine. The first clue names something only you own; the second room knows how you played the first.

Tier 1 (core loop plus backup video) ships Wed Nov 4; Tier 2 3D is gated Mon Nov 2, expected no-go. Demo weighs 25% (Oct 13 Waiver): an unedited 2-minute capture ships beside the edited main video (addendum.md §Demo and video plan).

## The Problem

Escape rooms cost money and travel, are scripted once for everyone, and none is about the player's own things. "AI escape rooms" like AI Escape make one image and a riddle chain; a 2025 Room Escape Artist review found hollow puzzles and a win by typing "blast off". Game masters scaffold help; AI hint-givers dump the answer or never help; none remembers the player.

## Who This Serves

Primary: a player at home with a phone and a browser, in 15- to 25-minute sessions, who recognizes their objects, gets unstuck without the answer, and comes back. Secondary: judges and the Mon Nov 9 finals audience.

## The Solution

In: 6 to 10 phone photos. Out: a puzzle chain from the player's objects.

1. Capture, timed: one `muse-spark-1.3` vision call (the Architect) lists objects, boxes, and readable attributes; one `sam-3.1` call per object gives typed interactables (cap 12 per room).
2. Authoring: one Riddler call writes locks, evidence, lore, three rungs; a validator, and a dry run that never sees solutions; at most 2 regenerations.
3. Play, 15 to 25 minutes: photo scenes with mask hotspots; a Python state machine opens locks; solutions never enter a prompt.
4. Help: the Guide picks the rung in code (nudge after 90 s with no progress or 3 wrong attempts); local Llama 3.2 3B phrases it without the solution.
5. Trickster: at most once per 3 minutes, one re-validated change from a fixed menu; at most 6 Spark calls per session.
6. Return visit: profile in browser IndexedDB; the second room's greeting cites it and hint thresholds scale.

## What Makes This Different

RoomQuest and Haven Studios' prototype stop at photos or generated images; Marble, Hyperscape, and Scaniverse give 3D without object semantics; ROOM//ZERO has a similar council but needs a Quest 3 mesh. As of Oct 20, only Keyframe chains a text-promptable segmenter, a council that verifies a puzzle graph from the player's own objects, and a game master that scaffolds help from logged play; no moat beyond execution speed (addendum.md §Prior art).

## Success Criteria

1. Capture-to-play at or under 120 s, 6 to 10 fresh photos, unedited, `CACHE=off`, on the M1.
2. Every video room passes the validator and dry run (validator only under cut 4) within 2 regenerations (1 under cut 7); no rung holds a solution token (cuts: addendum.md §Hours and cut order).
3. A scripted "just tell me the answer" attack yields nothing above the current rung.
4. Guide escalation visible with triggers; hints of about 40 tokens in 5 s or less from a prompt under 400 tokens with a fixed prefix.
5. One accepted and one validator-rejected Trickster edit; at most one per 3-minute window.
6. At least 80% of room-2 clues use objects absent from room 1; the greeting cites the prior profile.
7. A non-builder finishes room 1 on a fresh profile by Mon Nov 2 without builder help (Guide hints counted); otherwise the builder records a cold run of room 2.
8. Tier 2 gate, Mon Nov 2: 7 of 10 interactables recognizable in position, 30 fps or better, puzzles trigger by raycast. If any check misses, Tier 1 ships.

## Scope

- Tier 1, the floor: core loop plus backup video; [ASSUMPTION] 22 h after cuts against 16 h through Sat Oct 31; video gate Sun Nov 1 by 2:00 PM, recorded from whatever runs (zero slack).
- Tier 1.5 (cuts restored in reverse): second room, cross-session greeting, clue cards, hosted URL Nov 5 to 9 (only if the Official Rules, checked Mon Oct 26, allow post-deadline hosted changes; Oct 22), voice last.
- Tier 2 is a default no-go: it comes back only if the Tier 1 backup video already exists Sat Oct 31 night, and Tier 1 and the demo video are protected above everything else. If attempted (Sun Nov 1): fal SAM 3D Objects, at most 20 GLBs. Tier 3, never gating: Scaniverse splat shell.
- Out of scope: addendum.md §Scope boundaries.

Constraints:

- Builder and machine: day job; a 16 GB M1 MacBook Pro (no CUDA) runs Chrome, FastAPI, and the Guide via Ollama. Implementation runs on coding agents (Muse Code and the BMAD build loop) in parallel around the clock, so the per-item estimates are effort; the builder's [ASSUMPTION] about 32 h Oct 26 to Nov 4 go to review, direction, playtesting, and recording.
- Hosted services: `sam-3.1`, `muse-spark-1.3` (standard tier), and `muse-image-1.0` on the Meta Model API; fal.ai in Tier 2 only; Modal CPU hosts the URL (addendum.md §What runs where).
- Guide: Llama 3.2 3B Instruct (Q4_K_M) via Ollama on the Mac and nowhere else; the hosted URL shows rung text verbatim and runs no Guide model. Privacy: see Risks & Open Questions.

## Vision

Any space gets a game layer: the same council writing from whatever the segmenter finds. Later: shared rooms, Quest passthrough puzzles on real furniture; what it learns stays with the player.

## Risks & Open Questions

- Selection is unconfirmed until Mon Oct 26 (else a pay-as-you-go portfolio build, same plan). Official Rules are unpublished; weights, credit, team size, and prizes follow the Oct 13 Waiver ("terms may change"). If the Rules ban prior code, the 400-line scaffold is rewritten Oct 26.
- SAM 3D from one casual photo per object is the riskiest mechanic; staged checks (5 objects before Oct 26, 10 on Sun Nov 1) feed the Nov 2 gate.
- Spend: ceiling $80 of credit via `SPEND_CAP_USD`, allocated per mode (Oct 22: local 60, hosted 20; `docs/specs/spec-keyframe/budgets.md`), about $35 expected (cash if no credit); judging and finals pay-as-you-go, cap $25 (local 5, hosted 20 from Thu Nov 5; credit expiry unstated).
- Privacy: the player profile stays on your machine, whether or not cut 3 phrases the hints (addendum.md §What runs where). Photos and puzzle text go to the Meta Model API and, in Tier 2, fal.ai; retention terms are summarized on the capture screen; judge rooms deleted Nov 10. Raw room photos never enter the public repo, consent or not (the input folders are git-ignored); only outputs ship: screenshots, clue cards, the demo video, with household consent for what appears in them.
- Open questions for Luis: addendum.md §Open questions.

## Next Steps

- Wed Oct 21 to Sun Oct 25 (about 8 h): Schema v1 review Thu Oct 22, verifications, two spikes, 5 fal objects, rooms photographed, MIT LICENSE; tag `pre-hackathon-baseline` Sun Oct 25.
- Mon Oct 26 to Thu Oct 29 (3 h each): core loop on mock, then APIs; video v0 Wed Oct 28. Fri Oct 30: no build.
- Sat Oct 31: Tier 1 with cuts, backup video v1. Sun Nov 1: record by 2:00 PM, then playtest and room 2.
- Mon Nov 2: Tier 2 gate (criterion 8). Tue Nov 3: videos. Wed Nov 4: submit before 9:00 AM ET (deadline 9:00 PM ET). Nov 5 to 8: finals prep; the hosted redeploy (`MIN_CONTAINERS=1`, judge features) only if the Official Rules, checked at kickoff Mon Oct 26, allow post-deadline hosted changes (PRD §13 Q14; Oct 22), else the Wed Nov 4 deployment is the final hosted state (addendum.md §Day plan).

Handoff: `bmad-spec` (solo; no second epic until the Nov 2 gate) rather than `bmad-prd`, the catalog default; then `bmad-architecture`, `bmad-create-epics-and-stories`, `bmad-sprint-planning`, `bmad-build`; Tier 2 schema changes via `bmad-correct-course`.
