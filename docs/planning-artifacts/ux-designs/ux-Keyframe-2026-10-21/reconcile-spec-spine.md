---
title: "Input reconciliation: SPEC, profile, delivery plan, spine, Schema v1 against the UX contract"
reviewed: [DESIGN.md, EXPERIENCE.md]
sources:
  - ../../../specs/spec-keyframe/SPEC.md
  - ../../../specs/spec-keyframe/player-profile.md
  - ../../../specs/spec-keyframe/delivery-plan.md (Videos, Submission package)
  - ../../architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md (AD-3, AD-4, AD-7, AD-8, AD-11, AD-12, AD-13, AD-15)
  - ../../briefs/brief-Keyframe-2026-10-20/schema-v1.md
  - ../../prds/prd-Keyframe-2026-10-21/prd.md (consulted for §7 and FR text the UX cites)
date: 2026-10-21
---

# Input reconciliation: spec and spine against the UX contract

## Verdict

Most of it landed. The Lamplit study direction, the dark-only palette, the two-register split, the six-item accessibility floor, the verbatim Privacy line, Hosted mode's First-room welcome, the silent Ollama fallback, pixel-identical Decoy cards, the live Validator on scripted Cards, and the "no demo-only path" rule all match their sources. I recomputed all 33 pairs in the contrast table from the frontmatter hex values, and every ratio is correct.

The gaps cluster in four places:

1. **Leaks and false signals the contract would ship.** Evidence cards show `visible_attribute` verbatim. The order buffer turns exploration clicks into Wrong attempts. The timescale Disclosure sits over a real-time Timer.
2. **Dropped qualitative ideas.** No voice spec covers the generated Clues, Lore and Rungs, where most of the wry voice lives. "Lead with what the room knows" and "lead with the work" appear as quotes only. A first-time player gets no orientation, and the welcome line misdirects.
3. **Video beats with no surface.** The puzzle JSON, the local Guide in the model table, and the `PROFILE=demo` room-2 greeting.
4. **Internal contradictions.** The rule that keeps plain lines off parchment, the Stage list typeface, and Validator messages that only fit Trickster Cards.

Totals: 3 high, 12 medium, 10 low.

## High

### H1. Evidence cards can show the answer, and only real cards can
- **Where:** EXPERIENCE Component Patterns, Evidence card; UJ-1 step 7. DESIGN Components, Evidence card ("read attribute (`body-sm`)").
- **Source:** Schema v1 Fields (`evidence {interactable, visible_attribute}`), rule 4 (attribute must appear in the vision attributes), rule 5 (checks Rungs, and the near-answer against the Clue, never `evidence`), §Open pick rule 9 (a *decoy's* attribute "contains no solution token under rule 5"). AD-3 keeps `evidence` in `PlayView`.
- **Problem:** A `code` Puzzle's real evidence attribute can be the vision call's verbatim read, for example "printed 'EST. 1987'". The card then shows the code. UJ-1's climax promises the Clue points at the mug "without quoting the year", yet the Evidence card directly under that Clue would quote it. Rule 9 forbids solution tokens only in decoys, so a card that carries digits is always real. That breaks FR-19's "never identifies which Evidence is false". Neither file flags this.
- **Fix:** Add a `[NOTE FOR ARCHITECTURE]` to EXPERIENCE Open Items: extend rule 5 to `evidence.visible_attribute` through `bmad-correct-course` before the Mon Oct 26 freeze. This sits beside PRD Q12, which covers the Clue. Rewrite UJ-1 step 7 so the Evidence card names *where* to look ("has printing on its side") and never the token. Until the rule lands, add an Evidence card rule: an attribute is never displayed if it contains a solution-shaped token.

### H2. No voice spec for the generated in-character text (Clues, Lore, Rungs)
- **Where:** EXPERIENCE Voice and Tone ("Rungs themselves come from the Room") and Register rule. DESIGN Brand & Style.
- **Source:** SPEC Constraints, "wry and playful wizard voice". PRD §7 Rung copy ("A nudge says where to look, a direction what to notice, a near-answer how to use it; none says 'the answer is'"). PRD FR-7 (Clues, Lore and Rungs are written in the wizard voice so a verbatim Rung reads in character). player-profile: under cut 3 and in Hosted mode, Rungs are shown verbatim.
- **Problem:** Most of the wry voice lives in model-authored text, and the contract gives the Riddler prompt nothing to write to. The Riddler authors the Rungs, but the Guide's portrait signs them. A teasing Riddler line shown under the encouraging Guide's face is a voice mismatch, and it is the default in Hosted mode and under cut 3. The where, what and how ladder that makes help scaffold "without telling" is missing from EXPERIENCE entirely.
- **Fix:** Add a "Generated copy" subsection to Voice and Tone that the Riddler prompt quotes. Clue: in the Riddler's teasing voice, one or two sentences, pointing at an object without naming a token. Lore: 60 words at most, wry, never instructive. Rungs: written in the Guide's encouraging voice; the nudge says where to look, the direction what to notice, the near-answer how to use it; never "the answer is"; each Rung is enough to move the player forward (SM-C4). Give one sample per Rung.

### H3. Exploration clicks become Wrong attempts, and the contract states both rules
- **Where:** EXPERIENCE Interaction Primitives. "A click alone never counts as a Wrong attempt (AD-4)" sits beside "Every Hotspot click feeds the server's trailing buffer … a mismatch is one Wrong attempt". Order click progress (pips flash `wrong-ink`, "Not this · n").
- **Source:** AD-4. `order` is judged against the trailing click buffer when it reaches solution length; a mismatch is one Wrong attempt. Clicks still post for every Hotspot.
- **Problem:** While an `order` Puzzle is available, every N clicks spent exploring or solving a `find` Puzzle is judged. The pips flash rust, "Not this · 1, 2, 3" climbs, and three of those fire the nudge (player-profile). The player is told "wrong" for looking around. That contradicts DESIGN's "a Wrong attempt is play, not failure" feel, and it warps the Triggers panel the video depends on. The UX papered over this with two sentences that contradict each other.
- **Fix:** Add a `[NOTE FOR ARCHITECTURE]`. Judge the order buffer only after the player arms the `order` lock (for example, a "Start sequence" control in its notes entry that posts a lock input), or only over clicks on that Puzzle's candidate Hotspots. Until then, the order pips must not flash or count on clicks made before the player engages the order Puzzle.

## Medium

### M1. The hint placeholder invites free conversation
- **Where:** EXPERIENCE Play screen strings, "Ask the Guide anything".
- **Source:** PRD §9 and FR-14 (no free conversation). EXPERIENCE's own Privacy section ("No copy implies the Guide 'read' what was typed"). AD-4 (text is reduced to a `hint_request`).
- **Problem:** "Anything" promises an answer to anything, and it implies the text is read.
- **Fix:** "Stuck? Ask for a hint" or "Type to ask the Guide for a hint". Keep "Ask the Guide" on the button.

### M2. Repeated answers are silent for screen readers
- **Where:** EXPERIENCE Accessibility Floor, live region ("Each item is announced once"). Rung line ("a further Hint request repeats the near-answer").
- **Source:** SPEC and AD-11 (Rungs announced in a polite live region). The CAP-3 persuasion beat.
- **Problem:** An explicit ask that returns the current Rung, or the No-hint line again, is never announced. For a screen-reader user the persuasion climax is silence, and silence reads as "nothing happened".
- **Fix:** Announce the reply to every explicit Hint request, prefixed "The Guide:". Keep once-only for Rungs and Cards that arrive through the poll.

### M3. Demo-honesty copy implies the capture Timer is sped up, and cache is never disclosed
- **Where:** EXPERIENCE Disclosure copy table. DESIGN Disclosure banner ("identical on the Capture, Play and Completion screens").
- **Source:** SPEC CAP-8 ("without touching the capture timer"). AD-10. AD-15 (`Meta.cache`). SPEC CAP-1 (the proof needs `CACHE=off`). delivery-plan Videos ("earlier builds of the room").
- **Problem:** Under `DEMO_TIMESCALE=6`, "Timings shown at 6× speed." sits above the real-time Timer on the Capture screen. That reads as a faked build time, which is the opposite of the truth. `Meta` reports `cache`, yet no line covers a cached build shown under a running Timer.
- **Fix:** Propose through correct-course: "Hint and Trickster timings run at 6× speed; the build timer is real time." Add a server line for `cache: on` whenever the Timer is shown: "Built from cached model responses; this build time is not a fresh build."

### M4. Video beats with no surface
- **Where:** EXPERIENCE Build View ("Main demo use"), UJ-6.
- **Source:** delivery-plan Videos: 0:15 to 0:35 "the puzzle JSON"; 1:20 to 1:35 room-2 greeting; 1:35 to 1:50 "which Meta model did what, the local Guide, what is cached". The screenshot list ("puzzle JSON", "room 2 greeting"). player-profile Profiles (room 1 played for real on `PROFILE=demo`). AD-8 (the client excludes demo results).
- **Problem:**
  - The Build view has no JSON. The full Room JSON carries solutions.
  - The Model table is built from build provenance, so it cannot list the Ollama Guide or the Trickster.
  - UJ-6 never covers the greeting beat. A room 1 played at `DEMO_TIMESCALE>1` is demo-flagged and excluded, which leaves `sessions` at 0, so room 2 shows the First-room welcome and the beat fails.
- **Fix:**
  - State that the puzzle graph stands in for "the puzzle JSON", or add a read-only BuildView JSON pane (which is solution-free).
  - Add Model table rows for session-time models (Guide: `llama3.2:3b` on this Mac, or "verbatim"; Trickster: live, scripted or cut 1, from `GET /meta`), or say that the beat uses the README table.
  - Add a UJ-6 step: room 1 on `?profile=demo` at `DEMO_TIMESCALE=1`, then room 2 with the Greeting.

### M5. "Lead with what the room knows", "lead with the work" and the wizard introductions landed as quotes only
- **Where:** DESIGN Brand & Style (one sentence). EXPERIENCE Hosted landing ("optional Council strip").
- **Source:** SPEC Why (a council that scaffolds help). PRD §7: "Lead with what the room knows, never with photorealism"; "lead with the graph and verification (the Build view), never a text riddle"; "introduce each wizard by what it consumes and produces, then its voice".
- **Problem:** No rule puts these into practice. The Council strip is optional and Hosted-only, and Local mode introduces no wizard at all. The judge's first screen leads with cover photos and an access code, not with the graph and verification. "What the room knows" (read attributes, mask outlines, interactable count) appears only incidentally, in the Architect line and the Evidence cards.
- **Fix:** Make the Council strip required on the Hosted landing, and add it to the Local Capture screen's first visit. Give each Demo room card a "How it was built" link, and put a mask-plus-graph thumbnail on the landing. State a rule: the Capture screen's done state and the Mask preview lead with what was read (labels and attributes), never with renders or decoration.

### M6. No first-run orientation, and the welcome line misdirects
- **Where:** EXPERIENCE First-room welcome ("Welcome to your own room. Find what doesn't belong."). Hotspots are invisible at rest.
- **Source:** SPEC CAP-3 (a non-builder finishes room 1 without builder help). UJ-1 (Ana has never played an escape room). Schema v1 lock types (`code`, `order`, `use_on`, `find`; no odd-one-out). FR-19 (the Decoy stays secret).
- **Problem:** A first-time player must discover hover-reveal, the thumbnails and the notes alone. "Find what doesn't belong" implies a mechanic that does not exist and points straight at the Decoy.
- **Fix:** Replace it with a wry orientation line that names the actions: "Welcome to your own room. Hover to find what I can see; the notes say what I want." Add a one-time plain hint under "Begin" that points to the "Show all objects" toggle. Never mention false clues.

### M7. PRD drafts frozen as verbatim, so the voice stays flat
- **Where:** EXPERIENCE Exact strings ("Every other string is verbatim … must not be paraphrased"), the Cards table, the Stage labels, the Completion heading.
- **Source:** PRD §7 preamble ("sample lines are drafts the UX contract owns"). SPEC Constraints ("wry and playful").
- **Problem:** Card sentences such as "A new clue has appeared." and "This lock now needs another opened first." are flat. "The Trickster has the most fun" lands only in "Spoilsport." "A door just opened early." is inaccurate, because a Shortcut makes a Puzzle available and opens no lock. The Stage labels and "The room is open." carry no Architect or Guide voice.
- **Fix:** Re-tag the PRD samples as drafts. Give each Card a Trickster flourish after the effect clause (for example, Shortcut: "I've taken a wall down. You're welcome."), keeping the effect literal and naming no object. Give the Architect a voice on the Stage list header, not on the labels themselves. Assign the Completion heading to a speaker.

### M8. The drafted Validator messages only fit Trickster Cards
- **Where:** EXPERIENCE Cards, fixed reason messages ("That change would …"). DESIGN Build view Validator verdict table (fixed message per row).
- **Source:** AD-3 and Schema v1 Validator rules: one fixed message per rule, used by `validate` for builds, regeneration prompts, the Build view and rejected Cards.
- **Problem:** "That change …" makes no sense in a Build view row or a regeneration prompt.
- **Fix:** Write a neutral rule message for `validate` ("Two locks wait on each other."). The rejected Card adds its own prefix ("That change would leave …") in the UI, or the spine gets a separate Card variant.

### M9. DESIGN breaks its own register rule
- **Where:** DESIGN Brand & Style ("Plain lines … never sit on parchment") and Do's and Don'ts, against these components:
  - Completion sheet stat labels and "Deleted Tue Nov 10" on parchment.
  - Narrow-screen message.
  - Leave room card.
  - Rejected-Card reason.
  - Feedback chips, the `use_on` chip and the label chip.
  - Stage list token `typography: body-md`, though Typography says "Build stage lines" use `wizard-line`.
  - Card log, which sets Trickster sentences in `body-sm`.
- **Source:** PRD §7 register rule (Build stages are in character; deletion messages are plain).
- **Fix:** Restate the rule: plain *messages* (errors, warnings, Disclosures, deletion, privacy) never sit on parchment, while plain labels and chips may. Move "Deleted Tue Nov 10" off the sheet into a plain strip below it. Set the Stage list in `wizard-line`. Set Card log sentences in the serif.

### M10. The client cannot know the Active puzzle, and select-then-click may drop a click
- **Where:** EXPERIENCE Interaction Primitives (hint request "for the Active puzzle", the `use_on` `puzzle_id` assumption). Hotspot ("posts click unless a `use_on` item is selected").
- **Source:** AD-4. The Active puzzle is "the puzzle of the most recent lock_input or attempted click", and `HintRequestEvent(puzzle_id)` carries it. The client posts "a click for every hotspot click".
- **Problem:** The client never holds solutions, so it cannot know which Puzzle a click "attempts". The UX's client-side choice therefore diverges from the server's definition. Skipping the `click` on select-then-click also departs from "every hotspot click", which changes the `find` and order-buffer behaviour.
- **Fix:** Add a `[NOTE FOR ARCHITECTURE]`: session state should expose `active_puzzle_id`, or the server should resolve `puzzle_id` for hint and `use_on` events. Decide whether select-then-click posts a `click` as well, and record the choice.

### M11. Greeting delivery and truthfulness
- **Where:** EXPERIENCE Greeting template, Greeting component, UJ-2 step 1 and UJ-4 step 2 (thinking state "then" the line).
- **Source:** AD-5 (`greet(derived)` in `council/greeting.py`; the verbatim adapter fills "a template filled with the numbers"). The HTTP surface (no greeting route). SPEC CAP-6 (the greeting cites how the player played). AD-8 (`time_to_first_hint_s` may be null).
- **Problem:**
  - No route returns the greeting or a "phrasing in progress" state, so the client cannot show the Guide's thinking state before a phrased Rung or Greeting arrives.
  - "You held out … before asking" is false for a player who never asked (`time_to_first_hint_s` null).
  - The spine says the template is filled with numbers, while the UX uses phrase buckets.
- **Fix:**
  - Add a `[NOTE FOR ARCHITECTURE]`: the `POST /sessions` response carries the opening line, and session state carries a `phrasing` flag.
  - Add a template branch for "never asked" ("Last time you never asked once; let's see if this room changes that.").
  - Align the template form with AD-5.

### M12. Retention copy is wrong in Hosted mode and ambiguous in Local mode
- **Where:** EXPERIENCE Privacy and retention, expected text ("Your photos stay on this machine under rooms/ …" plus "Hosted additions").
- **Source:** SPEC CAP-13. AD-8 (one retention string served by `GET /meta`; hosted logs deleted after 24 h; judge data purged Tue Nov 10).
- **Problem:** "Stay on this machine" sits right after "go to the Meta Model API" and reads as if the photos never leave. Appended in Hosted mode, the same sentence becomes false.
- **Fix:** Local: "A copy is kept on this machine under rooms/ and is never committed." Make the served string mode-specific, so Hosted *replaces* that sentence rather than appending to it. Optionally add: "Hints are phrased on this Mac by a local model that sees only your play-style numbers."

## Low

- **L1. Source conflict on the cut-4 Dry run.** SPEC CAP-14 says "absent under cut 4"; PRD FR-38 and both UX files show "skipped". Pick one and log it through correct-course.
- **L2. WCAG 1.4.13.** The Hotspot label chip fades after 2 s even while keyboard focus remains. Keep it visible while the Hotspot is focused (DESIGN Hotspot label chip; EXPERIENCE Hotspot label chip).
- **L3. The filmed state crowds out the Wizard notes.** Two Disclosure lines, the Triggers panel opened automatically, stacked Cards and a 280 px Hint area that grows upward can squeeze the notes to nothing at 900 px. Add max heights, and collapse older Cards into the Card log after two (DESIGN Layout).
- **L4. Late Cards and Merge.** A slow Trickster call can land mid-puzzle, and a Merge can hide the entry the player is working on. Add a focus rule and a plain "This puzzle now waits on another" in place of the hidden entry. UJ-3's "more than 3 minutes" ignores the 30 s window at 6×.
- **L5. Mode and profile visibility.** delivery-plan Finals says "The mode is declared in the UI". Local mode shows nothing. Add a small plain "Local mode · profile demo" line in the top bar, or as a Disclosure-style line, so the right profile is recorded.
- **L6. Missing architecture notes on BuildView.** BuildView (AD-3) lists mask polygons but not labels, "where it ran", or per-model cached and billed values, yet the UX displays all three. "Regenerations: n of 2" ignores cut 7 and `REGEN_MAX`.
- **L7. Invented, near-duplicate tokens.** `graph-fail` #E8806C sits beside `wrong` #E58A6C. `pending` duplicates `text-muted`, `pending-ink` duplicates `ink-muted`, `card-accepted-surface` and `card-rejected-surface` duplicate `parchment`, and `graph-skipped` duplicates `text-muted`. The `lore` token lacks `fontStyle: italic`, though the prose says italic.
- **L8. "Helps" depends on being noticed.** An unprompted Rung arrives with only a 200 ms fade, at the bottom of the side column. Add one lamplight glow on the Guide ring when it arrives (static under reduced motion). After the near-answer, an identical repeated line reads as a wall (PRD §13a risk). Let Local phrasing vary the wording on repeats.
- **L9. Order pips have no text alternative.** Add "2 of 4" as an accessible description. EXPERIENCE's `sources` omit SPEC, `player-profile.md` and `delivery-plan.md`, though thresholds and beats come from them.
- **L10. Dead-end actions.** After the Spend cap, "Try again" cannot succeed until a reset; say so. In Hosted mode, "Try again" after `failed` uses another of the 20 builds; say so. The Deleted Judge room notice needs a way to tell "deleted" from "unknown room", and the spine keeps no record of deleted rooms; add a note for architecture.
