---
title: "Reconcile: decision logs against the Keyframe PRD"
created: 2026-10-21
scope: prd.md and addendum.md checked against the brief, spec and architecture decision logs
author: Luis Ticas
---

# Reconcile: decision logs against the Keyframe PRD

Inputs compared:

- Brief log: `docs/planning-artifacts/briefs/brief-Keyframe-2026-10-20/.memlog.md`
- Spec log: `docs/specs/spec-keyframe/.memlog.md`
- Architecture log: `docs/planning-artifacts/architecture/architecture-Keyframe-2026-10-21/.memlog.md`
- Also read for builder decisions on tone, because PRD §7 depends on them: the PRD's own log (`prd-Keyframe-2026-10-21/.memlog.md`) and the UX log (`ux-designs/ux-Keyframe-2026-10-21/.memlog.md`). Both record the same builder decision on visual direction and voice.
- Spot-checked against the source text where a log entry points to it: brief.md, brief addendum §Demo and video plan, spec delivery-plan.md, budgets.md, player-profile.md, schema-v1.md, spine AD-4.

Rule applied: entries marked "by user" are builder decisions, and the latest entry on a point supersedes earlier ones (for example, the 60 to 135 s nudge clamp supersedes 60 to 180 s, and "no Glimmer claims anywhere" supersedes a "Glimmer not run" disclosure).

## Verdict

The PRD carries nearly every number, gate, cut, cap and integrity rule correctly, and every settled fact holds: Guide on Llama 3.2 3B via Ollama on the Mac only, the privacy line word for word, SAM 3D Objects cloud-only at $0.02 a call in Tier 2 only, Tier 2 a default no-go behind the Sat Oct 31 night video, JPEG-only input, raw photos never committed, the daily ledger export, the Oct 22 single pick and the Oct 26 carry list. Five things need fixing before the UX contract and epics read the PRD:

1. §7 Aesthetic and Tone contradicts the builder's recorded decision.
2. The success metrics leave out four of the brief's eight success criteria and the demo content that the success signal names.
3. The demo-honesty rule "rehearsed, not faked" is never stated, so a requirement-by-requirement reading only finds a list of disclosures.
4. Cut 1 keeps the superseded "scripted reject" wording.
5. Clue cards (FR-37) run on every Build, which breaks the "once, $0.16" budget and the schema freeze.

The rest are medium or low additions.

## High

### H1. §7 contradicts the builder's tone and visual decision

- Source: PRD log, decision by user: "Lamplit study visual direction, dark only, wry and playful wizard voice, painted candlelit portraits; PRD section 7 follows these." UX log, decisions by user: "Lamplit study: warm dark chrome, parchment-toned cards and notes, serif headings; the UI frames the room photos like a wizard study"; "dark only"; "wry and playful across hints, greetings and cards; the Trickster especially has fun with the player"; "painted, candlelit oil-portrait style".
- PRD as written: §7 is still tagged `[ASSUMPTION A-16 ... no visual references supplied]` and says "Myst-style photo scenes", "terse, never condescending", "the Trickster taunts", "Portraits share one painted style". It says nothing about dark only, Lamplit study, parchment, serif headings or candlelit oil portraits. "Terse" and "taunts" pull the voice away from "wry and playful" and "has fun with the player". A-16 in §14 is now false.
- Fix: rewrite §7 from the builder decision and remove A-16 from §7 and §14:
  - "**Visual direction:** Lamplit study. Warm dark chrome, parchment-toned cards and notes, serif headings; the UI frames the player's room photos like a wizard's study. Dark mode only."
  - "**Wizard voice:** wry and playful in hints, greetings and cards, and never condescending. The Architect observes, the Riddler teases, the Guide encourages, and the Trickster has the most fun with the player."
  - "**Portraits:** painted, candlelit oil-portrait style, one shared style for all four."
  - Keep the Rung, Greeting, Disclosure and Errors lines. Change Greeting to "wry, warm and specific about play style, never about objects, never surveillance-flavored".
  - Drop "Myst-style" unless Luis wants it: no input names it. Keep "Hotspots revealed on hover" as an assumption with its own tag.
  - In FR-23, add the consequence "Portraits share the painted, candlelit oil-portrait style (§7)."

### H2. Success metrics drop brief criteria 2, 4, 5 and 8 and the main-demo content of the success signal

- Source: spec log, success signal: the submission carries "a main demo of at most 2:30 in which the persuasion attack fails, the Guide escalates three rungs on visible triggers, one Trickster edit is accepted and one validator-rejected, and room 2 greets the player from the room-1 profile". The brief's success criteria are 1 to 8, with criteria 1, 3 and 7 surviving every cut.
- PRD as written: §12 keeps SM-1 (criterion 1), SM-2 (criterion 7), SM-3 (criterion 3), SM-4, SM-5 (part of criterion 6) and SM-6. These have no success metric: criterion 2 (every video room passes the Validator and Dry run within 2 Regenerations, 1 under cut 7), criterion 4 (escalation visible with triggers, hints of about 40 tokens in 5 s or less), criterion 5 (one accepted and one rejected Trickster edit), the Greeting half of criterion 6, and criterion 8 (Tier 2 gate). They appear only as FR consequences, so nothing in §12 says what the Main demo has to show.
- Fix: add to §12 Primary:
  - "**SM-7 Main demo proves the loop:** a Main demo of at most 2:30 shows the persuasion attack failing, three Rungs escalating with their triggers visible, one accepted and one Validator-rejected Trickster edit, and room 2 greeting the player from the room-1 profile. Validates FR-14 to FR-16, FR-19, FR-21."
  - "**SM-8 Every video room verified:** every Room shown on video passes the Validator and the Dry run (Validator only under cut 4) within 2 Regenerations (1 under cut 7). Validates FR-8 to FR-10."
  - Add to Secondary: "**SM-9 Hint latency:** local phrasing of about 40 tokens arrives in 5 s or less from a prompt under 400 tokens (met trivially under cut 3). Validates FR-17."
  - Add a note: "Tier 2, if attempted, is judged only by the Mon Nov 2 gate in FR-34."
  - Add one line under §11.2: "Brief criteria 1, 3 and 7 (SM-1, SM-3, SM-2) survive every Cut."

### H3. The demo-honesty principle "rehearsed, not faked" is missing

- Source: brief log (decision by coach, carried unchanged into the spec delivery plan): "Scripted beats are rehearsed, not faked: real idle time and wrong codes trigger rungs, and the validator runs live on both replayed Trickster edits." The spec delivery plan adds "the greeting reads the real `PROFILE=demo` record". Architecture AD-15: "Prevents a faked reject."
- PRD as written: NFR-12 lists what gets disclosed (6x, scripted replay, earlier builds, Cuts shipped). §6.2 says demo mode "swaps the Trickster's source, never the check". Nowhere does the PRD say that every on-screen beat is caused by real input. UJ-6 shows the beats but not the rule. That rule is what makes the disclosures enough. Without it, a story could stage a Rung, a Greeting or a reject and still meet NFR-12.
- Fix: replace NFR-12 with:
  - "**NFR-12 Demo honesty:** every beat on video is rehearsed, never faked. Real idle time and real Wrong attempts trigger every Rung, compressed only by the Demo timescale. The live Validator decides both replayed Trickster edits. The Greeting reads the real room-1 record on `PROFILE=demo`, played at timescale 1 on Mon Nov 2. The capture timer and Event log are never scaled. The 6x Demo timescale, the Scripted Trickster replay and earlier builds of a Room are disclosed in the last 10 s of the Main demo and in the README. The README states which Cuts shipped, and the UI and README declare the mode used at finals."
  - In UJ-6, replace "fresh Player profiles" with "fresh Player profiles (`PROFILE=demo` holds only the real Mon Nov 2 room-1 run)", because the Greeting needs that record and the inputs require both videos on fresh profiles.

## Medium

### M1. Cut 1 keeps the superseded "scripted reject" wording

- Source: spec log: "the spine supersedes the delivery plan cut-1 wording (proposals scripted, validator live)". Architecture AD-15 amended: "cut 1 uses the same scripted source with pre-authored proposals and no live Spark path, validator still runs. Prevents a faked-reject path under cut 1."
- PRD as written: the §11.2 row for cut 1 reads "Pre-authored Trickster edits plus a scripted reject; Validator still live". FR-25 is correct, but the table row can be read as a staged reject.
- Fix: change the cut 1 row to "Pre-authored Trickster proposals from the scripted source, with no live Trickster calls; the live Validator accepts or rejects every Card".

### M2. FR-37 Clue cards run per Build and are missing from the schema

- Source: spec log CAP-7: "four wizard portraits (clue cards when restored) generated once and cached ... generated once ... never per build". Spec assumption: "portraits and clue cards $0.16 once". Spec log: Schema v1 "frozen Mon Oct 26; later changes only through bmad-correct-course". The spine lists Clue cards under Deferred as an optional post-scene stage.
- PRD as written: FR-37 makes "one `muse-image-1.0` image per Puzzle (4 to 6 per Room), generated once after the Room passes validation". That covers every Build, including dev rebuilds and up to 20 Judge rooms. The $0.16 "once" figure only holds for the two demo rooms. FR-37 also needs a place to store the image reference, which Schema v1 lacks, and the schema freezes Mon Oct 26 while Clue cards are Tier 1.5 (after Nov 1).
- Fix: in FR-37, replace the first consequence with "Clue cards are generated once per demo Room (the two recorded rooms and the hosted Demo rooms) by an explicit step, cached and priced. Judge rooms and ordinary Builds get none unless Luis enables them, and when enabled each card is priced per Build in the Ledger." Add: "Clue card references live outside the frozen Room (keyed by Puzzle id in the artifact store), or the field is added through `bmad-correct-course`; Schema v1 is not reopened."
- Also check Trickster `decoy` and `merge` against Clue cards: they change Evidence, not Clue text, so the card stays valid. Say so in one line.

### M3. Model table and model-wiring beat are missing (Use of Meta AI Tooling, 25%)

- Source: spec log submission constraint: "README model table and pre-existing-code section with diffstat". Delivery plan: README model table "(model id, where it runs, what it does, what shipped)"; a main-demo beat at 1:35 to 1:50: "Model wiring, 15 s: which Meta model did what, the local Guide, what is cached". The screenshots list includes the model table.
- PRD as written: UJ-5 has the judge wanting to "see which Meta model did what", but no FR or NFR requires the model table or the wiring beat. NFR-13 mentions licenses only.
- Fix: add to NFR-13: "The README carries a model table (model id, where it runs, what it does, whether it shipped), an architecture diagram, local-mode setup, the Privacy line, the Retention summary, the Disclosures and which Cuts shipped." Add to UJ-6 Path (3): "a 15 s model-wiring beat showing which Meta model did what, the local Guide and what is cached".

### M4. The Retention summary and §6.1 leave out hosted storage on Modal

- Source: brief log decision by coach: hosting on Modal CPU, "state in a modal.Dict, artifacts on a Volume". Architecture AD-8 amended retention rules: 24 h Session logs, judge rooms purged Nov 10, demo rooms persist. Spec CAP-10: judge rooms deleted Tue Nov 10.
- PRD as written: §6.1 says "Photos and puzzle text go only to the Meta Model API (standard tier) and, in Tier 2, fal.ai". FR-6 names only those two. In Hosted mode, Judge-room photos, originals and Rooms sit on the Modal Volume until Tue Nov 10, so "only" is false there.
- Fix: in §6.1, write "Photos and puzzle text go only to the Meta Model API (standard tier), to fal.ai in Tier 2, and, in Hosted mode, to Modal storage until Tue Nov 10, as the Retention summary states before upload." In FR-6, add "In Hosted mode the Retention summary also states that photos and the Judge room are stored on Modal and deleted Tue Nov 10, and that Session logs are deleted after 24 h."

### M5. Rungs must carry the wizard voice, and "helps without telling" has two halves

- Source: brief Problem (the intent the brief log's integrity decisions serve): "Game masters scaffold help; AI hint-givers dump the answer or never help." Builder decision (UX log): wry and playful voice "across hints". Brief log and spec: Hosted mode and cut 3 show rung text verbatim.
- PRD as written: FR-17 covers phrasing, but Hosted mode and cut 3 show the Riddler's Rung text verbatim, and no requirement says those Rungs are written in voice. The PRD guards against "telling" (FR-8, FR-14, SM-C2) but not against "never helping": no requirement says the near-answer has to be enough to solve the Puzzle.
- Fix: in FR-7, add "Clues, Lore and Rungs are written in the wizard voice (§7), so a verbatim Rung reads in character in Hosted mode and under cut 3." In FR-9, add "The Dry run reaches each answer from the Clue and Rungs it sees, so the near-answer Rung is always enough to solve the Puzzle." Add a counter-metric: "**SM-C4:** do not make Rungs vaguer to protect SM-4; a near-answer that fails to unlock the Dry run fails the Room."

### M6. The playtest fallback is missing

- Source: brief log question on the playtester: "(Success criterion 7; otherwise the builder records a cold run of room 2.)" Spec delivery plan, Mon Nov 2: "playtest here if the tester missed Nov 1, else the builder's cold run of room 2."
- PRD as written: SM-2 and Q7 give no fallback.
- Fix: append to SM-2: "If no playtester is available by Mon Nov 2, Luis records a cold run of room 2 instead, and the README says so." Mirror this in Q7.

### M7. The photo-content rule for the rooms is missing

- Source: brief log question on rooms: "6 to 10 photos each, no faces, documents or others' belongings". Spec delivery plan pre-kickoff line: the same rule.
- PRD as written: §6.1 and Q5 cover household consent and keeping photos out of the repo, but not what may appear in the photos that reach the Meta Model API and the videos.
- Fix: add to §6.1: "The demo rooms are photographed with no faces, documents or other people's belongings in frame; this applies to every photo sent to a model and every frame of the videos."

### M8. The dated gates leave out the schema freeze and other fixed dates

- Source: spec log: "Schema v1 ... reviewed Thu Oct 22 against the spikes, frozen Mon Oct 26; later changes only through bmad-correct-course". Brief log: capture target re-based "if the Oct 27 to 28 measurements miss 120 s". Profile: room 1 played for real on `PROFILE=demo` Mon Nov 2. Architecture AD-9 (coach, builder-approved): the Nov 5 reset refuses without that day's export. Brief log: baseline tag Sun Oct 25 night.
- PRD as written: the §11.1 table starts at Sat Oct 31. The freeze and the `bmad-correct-course` rule appear nowhere, which matters because the PRD feeds the epics and FR-37 is new.
- Fix: add rows to §11.1:
  - Thu Oct 22: Schema review, one pick (decoy storage)
  - Sun Oct 25 night: `pre-hackathon-baseline` tag and CHANGELOG baseline; both rooms photographed
  - Mon Oct 26: Schema v1 frozen; later changes only through `bmad-correct-course`
  - Tue Oct 27 to Wed Oct 28: capture measured; re-base to measured p50 plus 25% if 120 s is missed
  - Thu Oct 29: Wizard portraits generated once
  - Mon Nov 2: real room-1 run on `PROFILE=demo` at timescale 1
  - Thu Nov 5: Ledger export, then reset to $25
  - Tue Nov 10: Judge rooms purged

## Low

### L1. The Ledger must survive the on-camera Cache clear

- Source: architecture AD-9 amended (builder-approved): the local live Ledger moves to `spend/ledger.jsonl`, outside the Cache, "so clearing the cache on camera Nov 3 cannot erase it".
- Fix: add to FR-28 or FR-29: "Clearing the Cache never touches the Ledger or its exports."

### L2. Hackathon terms the PRD treats as rules are only precedent

- Source: brief log assumptions: selection is unconfirmed until Mon Oct 26 (otherwise the same plan runs as a pay-as-you-go portfolio build); the Official Rules, the pre-existing-code policy and the submission format are unpublished; "the 2-minute video and public repo come from Cerebral Valley precedent"; if the Rules ban prior code, the scaffold is rewritten Mon Oct 26 in under an hour.
- Fix: add one line to §13's "Tracked" note: "Selection (Mon Oct 26), the Official Rules, the pre-existing-code policy and the submission format are unpublished; the 2:00 video and public repo follow precedent and change if the Rules say otherwise; a prior-code ban means the scaffold is rewritten Mon Oct 26." In the §11.1 Submit row, write "6 to 9 PM is slack for a failed upload or a required live link".

### L3. Repo-hygiene detail is too vague

- Source: brief log decision by user: remove `_bmad/` and the local tool-config folder from the public repo; "the BMAD brief is the single source of truth"; `PRODUCT_BRIEF.md` stays removed. Brief log: CHANGELOG baseline entry Sun Oct 25 night.
- PRD as written: NFR-13 says "planning-tool folders removed from the index", which does not name the folders.
- Fix: in NFR-13, write "the folders named in the delivery plan's Wed Nov 4 hygiene line (`_bmad/` and the local tool-config folder) are removed from the index; the BMAD brief folder stays the single source of truth; `PRODUCT_BRIEF.md` stays removed; a CHANGELOG baseline entry accompanies the tag."

### L4. Tier 1.5 restore limits

- Source: brief log: "Tier 1.5 reverses cuts last-first only with time left; only cuts 1 to 3 are realistic before Nov 3."
- Fix: in §10.1, write "Cuts restored last-first, only with time left (only cuts 1 to 3 are realistic before Nov 3)".

### L5. The Greeting is unspecified when no Guide model runs

- Source: architecture AD-5 amended: `HintPhraser.greet` under 400 tokens with a 5 s timeout and a verbatim fallback; `GUIDE` selects ollama or verbatim; Hosted mode runs no Guide model.
- Fix: add to FR-21: "In Hosted mode, under cut 3, or when phrasing passes 5 s, the Greeting is a fixed template filled from the Derived block, in the same voice."

### L6. Credit context for the Spend cap

- Source: brief log: the cap of $80 comes "of the Meta credit", with cash if no credit is issued; judging and finals run pay-as-you-go because the credit's issue date and expiry are unstated.
- Fix: add to §6.3: "The $80 cap is set against the $150 Meta Model API credit; if no credit is issued the same plan costs about $35 cash; from Thu Nov 5 the $25 cap runs pay-as-you-go."

### L7. The build model appears only in the addendum

- Source: brief log direction by user: implementation runs on multiple coding agents around the clock; Luis's hours go to direction, review, playtesting and recording. Spec log: one owner per module, and the builder reviews everything that ships.
- Fix: add to NFR-8 or §0: "Stories are implemented in parallel by multiple coding agents, one owner per package, each story touching one package plus tests. Luis reviews everything that ships."

### L8. Browser for judges

- Source: UX log (decision by coach, not a builder decision): the hosted judge URL works in "any desktop browser".
- PRD as written: A-15 says "judges use desktop Chrome".
- Fix: align A-15 to "any current desktop browser; Chrome is the tested target", or record the narrower choice in the UX contract.

## Checked and correct (no change)

- Settled facts: Guide on Llama 3.2 3B Q4_K_M via Ollama on the Mac only. Hosted mode shows rung text verbatim and refuses to start with a Guide model (FR-17). No Glimmer claim anywhere (it appears only as a non-goal and a rejected alternative, which is consistent with the builder's later decision superseding the earlier "Glimmer not run" disclosure). Privacy line verbatim (§3, FR-6, §6.1, addendum). SAM 3D Objects cloud-only via fal.ai at $0.02, Tier 2 only, at most 20, $6 cash. Tier 2 default no-go behind the Sat Oct 31 night video. Tier 1 and the demo video protected (§10.1, SM-C3). "6 to 10 JPEG photos" with HEIC and PNG rejected and Most Compatible set. Raw photos never committed, consent or not. Daily ledger export as the durable record (FR-29, §6.3). Judging weights and dates. Oct 22 single pick and Oct 26 carry list (§13 Q1 to Q4, addendum). Open builder items (Q5 to Q8).
- Numbers: capture target and re-base; the 200 s / one-retry rule for takes (glossary, UJ-6); 5 to 12 Interactables; 4 to 6 Puzzles; stage budgets 15/10/45/30/10 s; about 75 s per Regeneration, 260 s worst case; nudge 90 s × (1 + 0.5 × persistence) clamped 60 to 135 s (the latest clamp); 3 Wrong attempts; 90 s spacing that never scales; Trickster one per 3 minutes, at most 6 calls, seventh refused; 6x timescale with three Rungs inside 40 s; 80% fresh objects; Spend cap $80/$25; daily ceilings $79; about $35 expected; build and session costs; rate limits; RAM 10.6 GB demo and 13.8 GB development.
- Integrity: solutions never enter a prompt; server-only lock opening; Hint request returns the current Rung or the fixed no-hint line (spine AD-4); structured Validator reasons; sentinel-solution tests; Trickster edits never mutate the stored Room; skipped Card on provider error or reached cap.
- Persona and authorship rules: Ana and Priya are fictional and use they/them; Luis Ticas is referred to by name with no pronouns.
