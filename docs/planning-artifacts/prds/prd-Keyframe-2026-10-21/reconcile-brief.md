---
title: "Input reconciliation: Keyframe PRD against the brief"
status: review
created: 2026-10-21
---

# Input reconciliation: Keyframe PRD against the brief

Luis Ticas · 2026-10-21

Inputs compared: `briefs/brief-Keyframe-2026-10-20/brief.md` and `addendum.md` (with `schema-v1.md` where the addendum points to it) against `prds/prd-Keyframe-2026-10-21/prd.md` and `addendum.md`. Spine and spec were consulted only to see where a PRD choice came from.

## Verdict

The PRD carries almost every load-bearing number and gate from the brief correctly: 6 to 10 JPEG photos with HEIC and PNG rejected, cap 12 and minimum 5 interactables, 15/10/45/30/10 s stage budgets, 120 s Capture target with the p50 plus 25% re-base, 200 s proof rule, 2 Regenerations (1 under cut 7), nudge 90 s × (1 + 0.5 × persistence) clamped 60 to 135 s with fixed 90 s spacing, Trickster once per 3 minutes and 6 Spark calls, Spend cap $80 then $25, daily ceilings $79, fal $0.02 a call with a $6 ceiling, the eight cuts with the right FR mapping, the Sat Oct 31 early gate, Sun Nov 1 2:00 PM Backup video, Mon Nov 2 Tier 2 gate, Wed Nov 4 9:00 AM ET submission, the Privacy line verbatim, the Guide on the Mac only, no Glimmer, standard tier only, raw photos out of the repo, the daily Ledger export as the durable record, and the Thu Oct 22 / Mon Oct 26 / builder-side open items exactly as settled.

What did not land is mostly qualitative and demo-facing, which is where an FR structure leaks: the product never states what a stuck player who asks for help actually receives (the brief's "never help" failure mode), the judge-visible proof surfaces the brief leads with (puzzle JSON, `requires` graph, validator and dry-run results, which model did what) have no FR and partly collide with "solutions never reach the browser", and the Hosted-mode path sends the Derived block off the player's machine although the brief justifies the Privacy line by "read by the selection code on the player's machine". Several smaller drops follow (Tier 1 vs 1.5 placement of room 2, live-link contingency, playtest fallback, photo-content rules, "rehearsed, not faked", risks, submission package).

Verdict: **revise before `bmad-ux` and epic re-extraction.** Three high gaps, eight medium, five low. None reopens a settled fact; each fix below is text to add or tighten in `prd.md`.

## High

### H1. A hint request can return nothing; the "helps without telling" contract is undefined

- **Brief:** the problem is that "AI hint-givers dump the answer or never help"; the player "gets unstuck without the answer". Profile `persistence` is "negative when they ask early" (so asking is a meaningful act), and the voice row says speech "only requests the next rung".
- **PRD:** FR-14 returns "the current Rung, or the fixed no-hint line when none is open"; the glossary says a Hint request "returns the current Rung only"; FR-35 gives "the same Rung a click would give". A player who asks at 30 s gets a fixed refusal, and the request has no stated effect on timing. §7 defines Rung copy but not the no-hint line, and no FR guarantees that the three Rungs together are enough to solve the lock.
- **Why it matters:** this is the single moment the brief positions Keyframe against: a game master who scaffolds instead of stonewalling. The PRD prevents "dump the answer" by construction and leaves "never help" to chance.
- **Fix text:** add to FR-14 Consequences: "When no Rung is open, a Hint request returns an in-world Guide line that acknowledges the request, says help is coming, and points the player back to the scene; it never reads as a refusal and never names an object or solution. The request is logged as a `hint_request` and counts as an early ask for `persistence`." Add to §7 under Rung copy: "No-hint line: encouraging and in voice ('Look again before I speak; the room is not done talking'), never 'no hint available'." Add to FR-9 Consequences: "Because the Dry run sees Clues and all three Rungs, a passing Room proves the Rungs are sufficient to reach every answer." Add §13 Q9 for Luis: "Does a Hint request with no Rung open release the nudge immediately (counted as an early ask), or only log the request? Brief voice row reads 'requests the next rung'." Keep the 90 s spacing and the current-Rung ceiling unchanged either way.

### H2. The judge-visible proof the brief leads with has no FR, and part of it conflicts with "never reaches the browser"

- **Brief:** the counter to "RoomQuest or Haven with extra steps" is to "lead with the puzzle JSON, its `requires` graph, the validator, and the dry run; solve a puzzle inside the scene, never by photographing an object; never headline a text riddle". Main demo 0:15 to 0:35 shows "masks over objects, the puzzle JSON"; 1:35 to 1:50 is "model wiring, 15 s: which Meta model did what, the local Guide, what is cached". Screenshots: "capture with masks, puzzle JSON, a rung with its events, Trickster cards, room 2 greeting, model table". Use of Meta AI Tooling is 25% and Technical Depth 20%.
- **PRD:** FR-30 stores provenance and FR-26 exposes a status endpoint, but no FR lets a judge or the video see the puzzle graph, the validator verdict, the dry-run result, mask overlays during capture, or a model-wiring view. §8 has no such surface. Vision and §6.2 say the solution never reaches the browser, so showing "the puzzle JSON" on screen is undefined: either a redacted view or an out-of-band file, and the PRD does not say which.
- **Fix text:** add FR-38 "Show how the room was built" (Tier 1, survives every Cut): "After a Build, Luis or a judge can open a Build view showing mask overlays on each photo, the puzzle graph (`requires` edges, Lock types, Exit puzzle), the Validator verdict per rule, the Dry run verdict per Puzzle (pass or fail only), the Regeneration count, and a model table (model id, where it ran, what it did, cached or billed) from provenance. Consequences: the view is built from a solution-free projection, so solutions, Rung text beyond the nudge, and Validator token matches never appear; a sentinel-solution test covers it; it is reachable from the Completion screen and the Capture screen after `done`." Add it to §8 and §10.1, and map it to Main demo 0:15 to 0:35 and 1:35 to 1:50. Add to §7: "Lead with the graph and the verification, never with a text riddle; every lock is solved inside the Scene, never by photographing an object."

### H3. Hosted mode sends the Derived block off the player's machine; the brief's privacy rationale says it never leaves

- **Brief:** "It holds in every build and does not depend on cut 3: the profile is stored in the browser and read by the selection code on the player's machine ... the hosted URL never runs a Guide model and shows the rung text verbatim."
- **PRD:** FR-20 "A Session start carries the Derived block"; FR-36 "the hosted server stores no Derived block ... beyond a Session's transient Event log". In Hosted mode the selection code runs on Modal CPU (PRD addendum, Guide rung selection row), so the Derived block and the threshold computation are off the player's machine for the Session. The Hosted-mode Greeting is also unspecified (no Guide model runs there). The Privacy line can stay verbatim only if this is either removed or disclosed.
- **Fix text (pick one, Luis decides; record in §13):** (a) Preferred, keeps the brief's sentence literally true: add to FR-20 "In Hosted mode, a Session start sends `Derived.fresh()`; no Player profile field leaves the browser; thresholds use a fresh profile and no Greeting is shown." (b) Keep the transient send and disclose it: add to FR-6 and FR-26 "In Hosted mode the four Derived numbers are sent to the hosted server for the Session and never stored; the Retention summary and README say so beside the Privacy line." In either case add to FR-21: "In Hosted mode the Greeting is a fixed template filled from the Derived block, or absent under (a)."

## Medium

### M1. Room 2 and the Greeting sit in Tier 1 in the PRD; the brief puts them in Tier 1.5 under the expected cut 8

- **Brief:** "Tier 1.5 (cuts restored in reverse): second room, cross-session greeting, clue cards, hosted URL Nov 5 to 9, voice last." The 22 h plan assumes all eight cuts, so cut 8 (room 2 to Sun Nov 1 afternoon) is the expected case.
- **PRD:** §3 Tier 1 is "FR-1 to FR-30 and FR-36", which includes FR-21; the Tier 1.5 glossary entry drops "second room, cross-session greeting".
- **Fix text:** in §3 Tier 1 and §10.1 add "(room 2 and the FR-21 Greeting move to Sun Nov 1 afternoon under cut 8, the expected case; the Backup video does not require them)". In §3 Tier 1.5 restore: "After the Backup video: second room and cross-session Greeting (under cut 8), Cuts restored last-first, Clue cards, Hosted mode for judges, voice last."

### M2. The live-link contingency for Wed Nov 4 was dropped

- **Brief:** "6 to 9 PM is slack for a failed upload or a required live link"; Nov 4 ceiling "$10 (slack for a required live link)"; the strictest precedent is "no localhost for a live demo"; a first `modal deploy` of the real app is a Tier 1 item on Tue Oct 27.
- **PRD:** §11.1 keeps only "slack for a failed upload"; §4.10 places all of Hosted mode at Thu Nov 5 to Sun Nov 8.
- **Fix text:** §11.1 Submit row: "Deadline 9:00 PM; 6 to 9 PM is slack for a failed upload or, if the Official Rules require one, a live link (Hosted mode with Demo rooms only, Rungs verbatim)." Add to §4.10 Description: "If a live link is required at submission, FR-31 (Demo rooms only) ships by Wed Nov 4 9:00 PM ET from the Tue Oct 27 deployment; FR-32 and FR-33 stay Nov 5 to 9."

### M3. The playtest fallback (criterion 7) is missing

- **Brief:** "A non-builder finishes room 1 on a fresh profile by Mon Nov 2 without builder help (Guide hints counted); otherwise the builder records a cold run of room 2." Criteria 1, 3, and 7 survive every cut.
- **PRD:** SM-2 states the primary path only.
- **Fix text:** append to SM-2: "If no non-builder is available by Mon Nov 2, Luis records an unassisted cold run of room 2 on a fresh Player profile, disclosed as a builder run." Add the same fallback to §11.2's "survive every Cut" sentence.

### M4. Photo-content rules for the rooms were dropped

- **Brief:** rooms photographed with "no faces, documents, or others' belongings"; household consent for what appears in outputs.
- **PRD:** keeps consent (§6.1) but not the content rule, and the Capture screen gives the player no guidance.
- **Fix text:** add to §6.1: "Demo and video Photo sets contain no faces, documents, or other people's belongings." Add to FR-6 Consequences: "The Capture screen asks the player to leave out faces, documents, and other people's belongings before upload."

### M5. "Rehearsed, not faked" is only half there

- **Brief:** "Scripted beats are rehearsed, not faked: real idle time and wrong codes trigger the rungs, compressed by `DEMO_TIMESCALE`; the validator runs live on both replayed Trickster edits; the greeting reads the real `PROFILE=demo` record." Capture proof uses "a photo set shot that day and never sent to the pipeline".
- **PRD:** NFR-12 covers disclosure; §6.2 says demo mode never swaps the check. Nothing forbids injecting events, Rungs, or Greetings, and "shot that day" is gone from the Capture proof.
- **Fix text:** add to NFR-12: "Demo settings change only timing (Demo timescale) and the Trickster's source; no demo path injects events, Rung changes, Greetings, Validator results, or Build output. Rungs on video are triggered by real idle time and Wrong attempts; the Greeting reads a real room-1 record played at timescale 1." Glossary Capture proof: "...of a Photo set shot that day and never sent to the pipeline..."

### M6. The Derived block's meaning is not in the PRD

- **Brief:** `persistence` is -1 to 1, "positive when the player keeps trying past the nudge threshold, negative when they ask early"; `time_to_first_hint` is a median in seconds; `mean_rung_per_lock_type` is 0 to 3. The profile also stores Trickster edits seen and accepted.
- **PRD:** glossary lists the four names only, yet FR-15 and FR-21 compute thresholds from `persistence`, and UJ-4's Greeting depends on it. Testers and UX cannot check FR-21 without the definition.
- **Fix text:** glossary Derived block: "`persistence` in -1 to 1 (positive when the player keeps trying past the nudge threshold, negative when they ask early); `time_to_first_hint`, median seconds; `mean_rung_per_lock_type`, 0 to 3; `sessions`, count." Room result: add "Trickster edits seen and accepted".

### M7. No risks section

- **Brief risks the PRD does not carry:** selection unconfirmed until Mon Oct 26 (else a pay-as-you-go build, same plan); Official Rules unpublished (video length, repo visibility, live link, pre-existing-code policy; the 2-minute video and public repo are precedent, not rule); rewrite of the 400-line scaffold on Mon Oct 26 if prior code is banned; SAM 3D from one casual photo is the riskiest mechanic, with staged checks (5 objects before Oct 26, 10 on Sun Nov 1); review bandwidth and merge conflicts from agent-parallel build (schema-first, one owner per module).
- **Fix text:** add §13a "Risks and dependencies" with those five lines, each with its existing mitigation from the brief, and link the Tier 2 staged checks to FR-34.

### M8. The Main demo shot list and the submission package are only partly present

- **Brief:** a time-coded Main demo (opening shot of the real room becoming hotspots for Impact; capture time-lapse; model wiring for Tooling; final 10 s disclosures) and a submission checklist (README model table and diagram, photo retention summary in README, 4 to 6 screenshots, 300- to 400-word write-up repeating the pre-existing-code statement, dated CHANGELOG, portal fields, spend log).
- **PRD:** UJ-6 lists four beats; NFR-13 covers license, hygiene, and baseline; the rest is reached only by an addendum pointer to `delivery-plan.md`.
- **Fix text:** add to §11 a short "11.3 Deliverables" list: Main demo beats mapped to judging weights (0:00 room-to-hotspots, Impact; 0:15 capture with masks and the Build view, Tooling; 0:35 persuasion; 0:50 Rungs with triggers; 1:05 Trickster cards; 1:20 room 2; 1:35 model wiring, Tooling and Technical Depth; 1:50 disclosures), and the submission checklist items above, each as a one-line pointer to `delivery-plan.md`.

## Low

### L1. Spend log source contradicts the brief

- **Brief:** spend log is "Meta API counter export, fal receipts, Modal usage"; pre-kickoff Meta calls (about $5) are cash outside the ceilings.
- **PRD:** FR-30 says the spend log "derives from the Ledger, never hand-kept".
- **Fix text:** FR-30: "The submission's spend log is the Ledger export for Meta Model API and fal.ai calls, plus fal.ai receipts and Modal usage attached as-is; pre-kickoff verification spend is listed separately."

### L2. Problem statement and anti-derivative framing are only implicit

- **Brief:** names the failures Keyframe answers (hollow puzzles, AI Escape's win by typing "blast off", hint-givers that dump or stonewall, no memory) and says to describe each wizard by what it consumes and produces.
- **PRD:** no Problem section; the "consumes and produces" line lives only in the addendum.
- **Fix text:** add §1b "Problem" with the brief's three sentences, and to §7 The four wizards: "Introduce each wizard by what it consumes and produces, then its voice."

### L3. Secondary audience

- **Brief:** secondary users include "the Mon Nov 9 finals audience".
- **Fix text:** add to §2.1: "Finals audience: understands the loop in one screen-shared run from the M1."

### L4. Front-end fallback dropped

- **Brief:** DOM-only scenes if Three.js costs more than 2 h.
- **PRD:** NFR-10 mandates textured planes with no fallback.
- **Fix text:** NFR-10: "...textured planes in the scene graph Tier 2 reuses (DOM-only Scenes if Three.js costs more than 2 h; Tier 2 then stays no-go)." Drop this if the spine has already closed the fallback.

### L5. Pre-kickoff hygiene items

- **Brief:** MIT LICENSE, README patch, and accepting the Official Rules if published, all before the Sun Oct 25 baseline tag.
- **Fix text:** NFR-13: "MIT LICENSE and the baseline CHANGELOG entry exist at the Sun Oct 25 `pre-hackathon-baseline` tag; the Official Rules are accepted when published."

## Checked and consistent (no action)

Settled facts all hold in both PRD files: track, dates, weights, Guide on Llama 3.2 3B via Ollama on the Mac only, no Glimmer in the product, Privacy line verbatim, Hosted URL with verbatim Rungs, fal.ai SAM 3D Objects cloud-only at $0.02 in Tier 2 only, Tier 2 default no-go behind the Sat Oct 31 night Backup video, Tier 1 and the demo video protected above everything, raw photos never in the public repo with only outputs shipping, "6 to 10 JPEG photos" with HEIC and PNG rejected and iPhone on Most Compatible, the daily Ledger export as the durable record, about 32 h of builder time with agents implementing around the clock, the Thu Oct 22 decoy pick (A recommended), the three Mon Oct 26 carries, and the four builder-side open items. Personas Ana and Priya are fictional and use they/them; Luis is named without pronouns. The PRD addendum's note that this PRD sits over the approved spec and reopens nothing is consistent with the brief's original `bmad-spec` handoff.
