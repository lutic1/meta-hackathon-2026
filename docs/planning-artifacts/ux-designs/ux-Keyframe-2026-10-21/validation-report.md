# Validation Report — Keyframe

- **DESIGN.md:** `docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/DESIGN.md`
- **EXPERIENCE.md:** `docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/EXPERIENCE.md`
- **Run at:** 2026-10-21

## Overall verdict

The pair works as a contract: a consumer can extract it cleanly. All 53 component names match one to one across `DESIGN.md` Components and `EXPERIENCE.md` Component Patterns. All 167 `{path.to.token}` references resolve, and all 33 contrast ratios in the table give the same result when recomputed from the frontmatter hex. Six of the seven UJs have a full Key Flow, and UJ-7 is a deliberate placeholder. Nothing blocks a build. The weak spots are bloat and a few contract gaps. `EXPERIENCE.md` restates architecture mechanics and repeats its own rules in up to five places, which is a drift risk. Four states have no defined home: network loss on the Capture screen, a refused session start, the modality of the Card log, and the Guide thinking state for an unrequested Rung. Twenty color tokens are aliases instead of hex values.

The two extra lenses shift where the risk sits. The judge's-eye demo lens carries the report's only critical and all nine highs: the spines are honest (the Disclosure banner, mode indicator and identical Real and Decoy cards hold up), but what a judge sees undersells what was built. The Meta models are named only in the Build view, which is cut 0, so attribution can vanish entirely; verification reads as a rubber stamp; the persuasion attack, the accepted Decoy and the local Llama phrasing are visual non-events; and the hosted path does not show the product in ten minutes. The voice and copy lens passes all four of the builder's copy conditions, the verbatim Privacy line and the plain Disclosures, with six medium lines to fix before the mocks. The lenses converge on three spots: "Welcome to your own room" is false in a Demo room, "A new clue has appeared" names the wrong thing and shows no change, and the side-column Hint area overflows its 320 px cap in the filmed beats. Most fixes are copy and placement edits; four judge fixes need a solution-free field flagged `[NOTE FOR ARCHITECTURE]`.

## Category verdicts

- Flow coverage — strong
- Token completeness — adequate
- Component coverage — strong
- State coverage — adequate
- Visual reference coverage — adequate
- Bloat & overspecification — thin
- Inheritance discipline — adequate
- Shape fit — strong

## Findings by severity

### Critical (1)

**[Judge's-eye demo]** — Meta models are named only in the Build view, which is cut 0 (§ EXPERIENCE Voice and Tone › Wizard introductions; Hosted landing strings; DESIGN Stage list; Brand & Style)
Model identity appears only in the Build view's Model table and In play block. FR-38 is cut 0, the first Cut taken (PRD §11.2). The role lines put `muse-spark-1.3` and `sam-3.1` under one wizard with no names, and the Hosted landing names no model. Under cut 0 the product shows no Meta model at all; without it a judge sees the models only after two clicks. The Tooling score (25) then depends on the video's 15 s beat and the README.
Fix: Name the model in each plain role line, so attribution survives cut 0 and appears in the first minute of every path (for example, Architect: "Reads your photos with muse-spark-1.3; sam-3.1 outlines each object it names."). Done Stage list rows show the model beside the duration in `mono-sm` ("sam-3.1 × 9 · 6.1 s"). Add one plain line to the Hosted landing title block. Keep role lines in `body-sm` sans.

### High (9)

**[Judge's-eye demo]** — Model table drops "what it did" and falls below the fold (§ DESIGN Build view: Model table; Layout › Build view; EXPERIENCE Build View › Content)
FR-38 defines model id, where it ran, what it did, cached or billed; DESIGN substitutes the wizard's role line, identical on the Architect's two rows. The Dry run and the Validator have no row, so the strongest Technical Depth claim is not on the table. The right column stacks verdicts and Dry run rows above the Model table, which falls below the fold at 900 px with a two-line banner.
Fix: Add a "What it did" column from provenance counts ("Named 11 objects from 8 photos", "Solved 5 of 5 without the answers"). Add a fixed Validator row and a Dry run row. Reorder the right column to Model table, In play block, Validator verdicts, Dry run rows.

**[Judge's-eye demo]** — Verification reads as a rubber stamp (§ DESIGN Build view: Validator verdict table, Dry run row, header; EXPERIENCE fixed reason messages; Capture › Stage list (Regeneration))
A stored Room always passes, so the table is always eight green rows, each printing the failure-worded fixed message beside "pass", which reads as a contradiction. Dry run rows never say the solver never saw the answers, and "Regenerations: 1 of 2" never says what was caught. The one moment that proves the Validator works, a leak caught and sent back, is never shown.
Fix: Give each rule a check-phrased name for pass rows and show the fixed message only on fail. Caption each table. Show the failed attempt's fixed messages on the Regeneration row ("Sent back: A hint gives part of an answer away."). `[NOTE FOR ARCHITECTURE: job status and BuildView carry per-attempt fixed reason messages.]`

**[Judge's-eye demo]** — Capture screen reports no outcomes (§ EXPERIENCE Capture stage names; Build job statuses; Hosted Mode Differences; DESIGN Stage list)
The only verification view that survives cut 0 merges the Architect and SAM, merges validate and dry run, and shows durations only. After the Mask preview nothing changes for a minute or more. On a hosted Judge room Priya watches static rows and is never told the build has its own resumable link.
Fix: Done rows carry a plain result ("Testing the room · 8 of 8 rules · blind test reached 5 of 5 answers"); split "Testing the room" into two lines when done. In Hosted mode add: "This build has its own link. You can close this tab and come back, or play a demo room meanwhile." `[NOTE FOR ARCHITECTURE: job status exposes interactable, puzzle, rule-pass and dry-run-pass counts.]`

**[Judge's-eye demo]** — The persuasion beat does not read on screen (§ EXPERIENCE Hint field + Ask the Guide; Play screen strings; UJ-2 step 4; DESIGN Hint field)
On Enter the field clears at once and the reply is the same Rung line fading out and back in. Neither the camera nor a judge trying the attack sees that the words were reduced to a Hint request, and may read it as "the app ignored me". FR-14's strongest privacy and integrity property has no copy on the Play screen.
Fix: Keep the typed text visible and read-only while "Asking". Add a permanent helper line under the field: "Your words stay in this browser. The Guide only hears that you asked."

**[Judge's-eye demo]** — The accepted Decoy is a visual non-event (§ EXPERIENCE Cards (Accepted Decoy label); UJ-3 step 2; UJ-6)
The new Evidence card is pixel-identical, gets no highlight, and the label omits the Puzzle number, which goes beyond FR-19. A judge sees "A new clue has appeared" and nothing changes, which reads as hollow or staged.
Fix: Label it "Accepted · Decoy · Puzzle {n}". Show an Evidence count in each Puzzle heading row so it ticks up. In UJ-6 prefer a Merge or Loosen as the recorded accepted proposal.

**[Judge's-eye demo]** — First 30 seconds on the hosted URL open on a caveat (§ EXPERIENCE Hosted landing (title, subtitle); DESIGN Layout › Hosted landing; Demo room card)
The first line a judge reads is the hosted hint caveat. The subtitle names neither the models nor verification, the wizards are unnamed 24 px portraits, "15 to 25 min" tells a ten-minute judge not to play, and "How a room is built" gives no hint it is the one-minute path.
Fix: Add one plain pipeline line under the subtitle naming `muse-spark-1.3`, `sam-3.1`, the blind test and the Guide. Give "How a room is built" the lead-in "Short on time? See how a room is built and checked." Keep "15 to 25 min".

**[Judge's-eye demo]** — The local Llama Guide is invisible in play (§ EXPERIENCE Ollama fallback; Triggers panel; Wizard portrait (thinking); Build View › In play (Hosted); DESIGN Do's and Don'ts)
Phrased and verbatim Rungs look identical and the fallback is silent. On video a verbatim fallback can appear in the 0:50 beat while the 1:35 beat claims local phrasing. In Hosted mode Llama reads as absent or cut.
Fix: Leave the Rung line unbadged; put provenance on Triggers rows ("worded on this Mac · 1.6 s" or "as written (wording took over 5 s)"). Thinking label: "thinking on this Mac". Rewrite the Hosted In play Guide row to explain Local mode. `[NOTE FOR ARCHITECTURE: rung_change carries the phrased-or-fallback flag and latency.]`

**[Judge's-eye demo]** — Adaptive help is invisible (§ EXPERIENCE Triggers panel; Triggers rows; UJ-4 step 4; DESIGN Triggers panel)
The effective nudge threshold, its source and the 90 s spacing appear nowhere. At 6× a row reads "Idle 15 s" with no reference value, which can read as contradicting the PRD's 90 s.
Fix: Add a Triggers header: "Nudge after {threshold} s idle or 3 Wrong attempts · each next Rung no sooner than {spacing} s", with timescale and profile-source suffixes. Film it in the 1:20 beat. `[NOTE FOR ARCHITECTURE: session state exposes the effective threshold and spacing.]`

**[Judge's-eye demo]** — Capture proof Timer is dimmed and unlabelled (§ DESIGN Layout & Spacing (scrims); Elevation level 3; Timer; EXPERIENCE Timer; Open Items)
Scrims dim the top bar, so the running Timer sits under an 80% scrim right before T1, the most watched number in the proof. When it freezes the digits carry no label.
Fix: Start every scrim below the top bar, which stays legible but inert. Label the digits "Photos to play" while running and "Playable in" once stopped. In UJ-6 step 2, Luis clicks "Begin" as soon as the card appears.

### Medium (23)

**[Token completeness]** — Twenty color tokens are aliases, not hex (§ DESIGN.md frontmatter, lines 50–51, 63–81)
`pending`, `pending-ink`, all seven `card-*`, the three `clue-card-*`, and six `graph-*` entries are references. The spec types `colors` as hex strings, so a token pipeline that mirrors the frontmatter gets the string `'{colors.parchment}'` where it expects a color.
Fix: Write the resolved hex on each role token and keep the alias in a trailing comment, or move the role aliases into the `components` block, where references are allowed.

**[Component coverage]** — Toggles have no pressed or expanded look (§ DESIGN.md line 749; EXPERIENCE.md lines 315, 505)
"Show all objects" is an NFR-14 floor toggle whose pressed state is announced, but the DESIGN.md Secondary button row and `components.button-secondary` define rest and hover only. The "Triggers" toggle and the "Show the build JSON" toggle have the same gap.
Fix: Add a pressed/expanded state to the Secondary button row and token (for example a `lamp-hover-fill` background with the label in `lamp-strong`) and name the three toggles that use it.

**[State coverage]** — Capture screen has no network-loss state (§ EXPERIENCE.md lines 29, 337, 446)
Foundation says losing the network shows the reconnecting state, but that state and its status strip are defined only for the Play screen. Nothing covers a failed `POST /builds` upload (beyond the 422 refusal) or missed `GET /builds/<job_id>` polls: where the strip sits, whether the Timer runs, whether the Stage list freezes.
Fix: Add "Reconnecting (Build)" and upload-failure rows to Capture State Patterns, and give the Status strip row a Capture placement.

**[State coverage]** — "Session start refused" has no surface (§ EXPERIENCE.md Exact strings, line 239)
No state row says where a failed `POST /sessions` shows, what action it offers or where focus goes. It can fail after `done` on Capture, after a Demo room card click, or after a stored Room "Play".
Fix: Add a row to Capture and Hosted landing State Patterns, for example an error banner with "Try again" and focus on the banner.

**[State coverage]** — Card log modality is ambiguous (§ DESIGN.md lines 711, 720, 796; EXPERIENCE.md lines 73, 358, 448, 607)
DESIGN.md calls it a popover, but Elevation, Layout and Demo Mode put it under a scrim, and Navigation counts it as a one-deep modal. Play "Disabled" lists only the Greeting and Leave room overlays as making Hotspots inert, and the Card log row states no focus trap.
Fix: Declare it either a non-modal popover (no scrim, Scene live, no trap) or a modal (scrim token on `components.card-log`, focus trapped, Hotspots inert) and align the four passages.

**[Visual reference coverage]** — Pending references point to the wrong folder and format (§ DESIGN.md lines 742, 756, 771, 800; EXPERIENCE.md lines 58–65)
All nine pending references point to `mocks/*.png`, but the key-screens renderer writes `.working/key-{slug}.html` and Finalize promotes HTML keepers to `mockups/`. None will resolve once the mocks land.
Fix: Rename to `mockups/play-screen.html`, `mockups/capture-screen.html`, `mockups/build-view.html` and `mockups/completion-greeting.html`. If PNG exports are intended, log the deviation in the memlog and keep the HTML as the linked source.

**[Bloat & overspecification]** — EXPERIENCE.md restates architecture and repeats its own rules (§ EXPERIENCE.md lines 39–48, 296–304, 350, 384, 483–484, 605–649)
Event constructors, the `Meta` field list, AD-9 and AD-3 contents are restated. Order-buffer arming appears in three places, hint-request behavior in five, mode differences twice, the Build view four times and privacy copy twice. Every architecture change then needs edits in several places, and the spine was already amended on Oct 21.
Fix: Give each rule one home and cite it elsewhere. Replace AD restatements with the AD id plus the one UI consequence. Fold the Build View section into Component and State Patterns, and the Foundation mode table into Hosted Mode Differences.

**[Bloat & overspecification]** — DESIGN.md carries behavior EXPERIENCE.md owns (§ DESIGN.md lines 554–576, 788; Components rows)
Order click progress cites server acknowledgement; Access-code build, Stored Room row and Mode indicator cite routes; Brand & Style repeats the wizard-introduction placement and the register rule from Voice and Tone.
Fix: Keep visual anatomy and visual states in DESIGN.md, drop route and server references, and reduce the introduction placement to one pointer to EXPERIENCE.md Voice and Tone.

**[Inheritance discipline]** — Guide thinking state before an unrequested Rung has no signal (§ EXPERIENCE.md lines 438, 538)
UJ-2 step 1 shows the thinking state before a Rung arrives through the poll. AD-4 gives a `phrasing` flag only for the opening line, there is no phrase route, and the Polling row says nothing about phrasing, so the client cannot know a Rung is being phrased until it appears.
Fix: Limit the thinking state to an in-flight Hint request and correct UJ-2 step 1, or add a `[NOTE FOR ARCHITECTURE]` asking for a Rung phrasing flag in session state.

**[Judge's-eye demo]** — Fairness shown on one side only (§ EXPERIENCE Cards (labels); Accessibility Floor; DESIGN Trickster card)
"Accepted" does not say by whom, and "Rejected · {type}" has no Puzzle number or proposal. Under the "replayed from a recording" Disclosure a skeptical judge can read the reject as staged.
Fix: Labels "Validator passed · {type} · Puzzle {n}" and "Validator refused · {type} · Puzzle {n}"; add a structural "Proposed:" line on rejected Cards; mirror in the Card log.

**[Judge's-eye demo]** — UJ-6 maps only three demo beats to screens (§ EXPERIENCE UJ-6; Demo Mode and Disclosure)
The 0:00 beat would show unlabelled dashed outlines, the delivery plan's 0:15 beat still says "the puzzle JSON", and nothing puts the time-lapse disclaimer on screen (NFR-12).
Fix: Add a Main demo shot list table mapping each §11.3 beat to surface, state and what must be legible at 1080p, with the caption "Time-lapse · unedited capture proof linked" for 0:15.

**[Judge's-eye demo]** — Hosted Demo rooms hide the ladder and the Trickster (§ EXPERIENCE Hosted Mode Differences; Foundation › two-modes table)
At full timings the nudge waits 90 s, each Rung 90 s more, and the first Trickster window opens no sooner than 3 minutes in. In ten minutes Priya cannot see either mechanic.
Fix: Record a builder pick: hosted Demo rooms run at a Demo timescale (FR-24), already disclosed by FR-26.

**[Judge's-eye demo]** — Side column overflows in the 0:50 and 1:05 beats (§ DESIGN Layout & Spacing › side column)
Two Cards, the Rung line, field, toggle and open panel total about 580 px against a 320 px cap, so the filmed line scrolls out of frame. Rows are 13 px muted mono.
Fix: While Triggers is open, stack only the newest Card and let the Hint area grow to leave Wizard notes their 280 px minimum. Newest row in `text`, rows in `body-sm` with `mono-sm` numbers.

**[Judge's-eye demo]** — "Welcome to your own room" is untrue in a Demo room (§ EXPERIENCE First-room welcome; Hosted Mode Differences › Opening line)
Priya is standing in Luis's living room. The builder's condition protects "Find what doesn't belong", not "your own room".
Fix: Use one line that holds in every mode ("Welcome to the room. Find what doesn't belong.") or a server-picked Demo-room variant.

**[Judge's-eye demo]** — Build view integrity claims are never stated on screen (§ DESIGN Build view: BuildView JSON, Model table; EXPERIENCE Build View)
The solution-free JSON and the sentinel test are invisible; "cached" and "billed" are unexplained, so a Demo room full of "cached" can read as nothing ran live.
Fix: Caption the JSON toggle and the cached or billed column in plain `body-sm` `text-muted`.

**[Judge's-eye demo]** — "profile demo" beside the Greeting invites "it's canned" (§ EXPERIENCE Mode indicator; UJ-6 step 4; DESIGN Mode indicator)
The 1:20 beat runs on `?profile=demo`, though NFR-12 requires a real room-1 record played at 1×.
Fix: Show "profile demo · 1 room played" and caption the beat "Greeting read from the real room-1 run, played Mon Nov 2 at 1×".

**[Judge's-eye demo]** — Hosted Timer counts queue time (§ EXPERIENCE Timer; Build job statuses (`queued`); Hosted Mode Differences)
A judge can see 4:30 on their own build against "about two minutes" on video and read the video as faked.
Fix: Show "queued" in place of digits while queued, add "includes 1:10 in the queue", and add a plain line that the two-minute target is measured in Local mode.

**[Voice and copy]** — M1 · "A new clue has appeared" uses the wrong Glossary term (§ EXPERIENCE Voice and Tone › Cards, Accepted Decoy; UJ-3 step 2)
A Decoy adds an Evidence card, never a Clue. A first-time player looks for new Clue text in the Wizard notes and finds none. The judge's-eye review saw the same beat as a new clue with no visible change.
Fix: "A new evidence card has appeared. I do love a crowded desk."

**[Voice and copy]** — M2 · "This lock" points at nothing; Merge worded two ways (§ EXPERIENCE Voice and Tone › Cards, Accepted Merge; Merge-hidden entry placeholder)
The Card sits in the Hint area, away from any entry. The Card says "needs another opened first" and the placeholder says "now waits on another puzzle".
Fix: "One puzzle now waits on another. Patience builds character; I build locks."

**[Voice and copy]** — M3 · "Welcome to your own room" is false on a Demo room (§ EXPERIENCE First-room welcome; Hosted Mode Differences › Opening line; UJ-5 step 3)
Demo rooms are the first room most judges play. "Find what doesn't belong" stays verbatim, so condition (a) still holds.
Fix: Demo room variant: "Welcome to someone else's room. Find what doesn't belong."

**[Voice and copy]** — M4 · Two names for one thing: hint and Rung (§ EXPERIENCE Wizard introductions › Guide role line; Completion › Stat labels)
The field, button and two Disclosures say hint; the Guide's role line and "Rungs used" say Rung, a word the UI never teaches, read before the first Scene.
Fix: Role line: "Reads how you play; offers one hint at a time, never the answer." Stat label: "Hints used". Keep Rung in the spec.

**[Voice and copy]** — M5 · Mask preview template renders without articles (§ EXPERIENCE Capture screen, Architect line over the Mask preview; UJ-1 step 4)
It renders as "I see mug, lamp and books, and 9 things worth a closer look in all.", and "…and 9 things … in all" reads as 9 more.
Fix: "I see {n} things worth a closer look, starting with the {label 1}, the {label 2} and the {label 3}." plus a two-label case.

**[Voice and copy]** — M6 · First Trickster Card nearly fills the Hint area at 1024 px (§ EXPERIENCE Wizard introductions › Trickster; DESIGN Trickster card, Hint area (320 px max))
About 248 px of text width; the first Card runs roughly 300 px against a 320 px cap shared with the Rung line, field and toggle. The voice line repeats the role line.
Fix: Voice line: "I like to move things around. The Validator keeps me honest, sadly." Pin the hint field and Triggers toggle outside the Hint area's scroll.

### Low (29)

**[Token completeness]** — Two frontmatter keys sit outside the spec's token table (§ DESIGN.md lines 119, 185–190)
The top-level `elevation` group and `fontStyle: italic` on `typography.lore` are not spec token types.
Fix: Add one line under Elevation & Depth and Typography marking these as deliberate extensions, or fold the shadows into component tokens and state the italic in prose only.

**[Token completeness]** — Load-bearing pairs missing from the contrast table (§ DESIGN.md Colors › Contrast)
Pairs that pass but are not listed: `error-text` on `chrome-raised` (7.33), `success` on `chrome-raised` (7.80), `lamp` as secondary-button label inside error and warning banners (7.49, 6.55), and `lamp-strong` on `chrome` (10.86).
Fix: Add these rows so the table covers every pair the Components tables use.

**[Token completeness]** — Narrow-screen heading has two type tokens (§ DESIGN.md lines 680, 825)
Typography assigns `display-lg`; the Narrow-screen message row says `display-sm`.
Fix: Pick one and update the other line.

**[Component coverage]** — Cut 2 profile file controls have no visual spec (§ EXPERIENCE.md Closure, line 108)
The Cut 2 placeholder adds "Open profile file" and "Save profile file" controls, but no DESIGN.md row or placement covers them.
Fix: Name them as Secondary buttons in the Retention summary and Completion screen rows, or mark the placeholder as copy-only.

**[State coverage]** — Smaller state gaps (§ EXPERIENCE.md State Patterns)
No error state for `GET /rooms` and no empty state for zero Demo rooms; no initial focus on the Build view; no focus target after a Card is dismissed or after "Keep playing"; no open-but-empty Triggers panel state.
Fix: One row each in the relevant State Patterns tables.

**[State coverage]** — Hosted landing row omits "too many tries" (§ EXPERIENCE.md lines 384, 473)
The Access code state row leaves out the rate-limited state the Access-code build component row has.
Fix: Add it to the row.

**[Bloat & overspecification]** — Pixel values beside tokens; Clue card slot specified twice (§ DESIGN.md lines 692–697, 780–781)
Parentheticals like "`{spacing.side-column}` (400 px)" duplicate the token; the Clue card slot appears in the Wizard notes row and its own row.
Fix: Drop the parenthetical values and keep the slot spec only in its own row, with Wizard notes pointing to it.

**[Inheritance discipline]** — Source lists differ between spines (§ DESIGN.md lines 8–11)
DESIGN.md `sources` leave out the memlog and `schema-v1.md`, though DESIGN.md cites memlog decisions.
Fix: Add `./.memlog.md` to DESIGN.md `sources`.

**[Inheritance discipline]** — Access-code surface has three names (§ DESIGN.md lines 709, 822; EXPERIENCE.md line 203)
"Access-code panel", "Access code panel" and the component name "Access-code build".
Fix: Use "Access-code build" for the component and "panel" only as a plain noun, or rename the component everywhere.

**[Inheritance discipline]** — Input requirement placement unclear (§ DESIGN.md lines 703, 760; EXPERIENCE.md lines 178, 396)
Layout puts it in the right column, the dropzone row puts a line inside the dropzone, and cold load lists both. A consumer cannot tell whether the verbatim string shows once or twice.
Fix: State that the right column carries the verbatim term and the dropzone carries the picker sentence, or keep only one.

**[Inheritance discipline]** — Armed order sequence drifts from PRD FR-12 (§ PRD FR-12, §8)
The spine follows AD-4 and Schema v1, but FR-12 still reads "the most recent clicks are judged" and the control is missing from the PRD §8 Play screen list.
Fix: Keep the spine and log the PRD wording correction for `bmad-correct-course`.

**[Judge's-eye demo]** — Privacy line can read as contradicting Modal storage (§ EXPERIENCE Privacy and Retention; Retention summary (Hosted ending))
"stays on your machine" sits right after "your photos … are stored on Modal".
Fix: Give the Privacy line a plain `label` lead-in, "Your play history"; the string stays unchanged.

**[Judge's-eye demo]** — No path to the Build view mid-play (§ EXPERIENCE Open Items; Navigation rules)
Cross-checking masks and verdicts mid-play means leaving the Session.
Fix: Add "How this room was built" to the Play screen top bar, opening in a new tab.

**[Voice and copy]** — L1 · Skipped Card speaks of the Trickster in the third person (§ EXPERIENCE Cards, Skipped; UJ-3 Failure)
The live region reads "The Trickster: The Trickster is quiet this time."
Fix: "I'm keeping quiet this time. Enjoy it while it lasts."

**[Voice and copy]** — L2 · Loosen Card is not a literal effect clause (§ EXPERIENCE Cards, Accepted Loosen)
"The Guide is feeling generous." does not state the effect FR-19 asks for.
Fix: "The Guide is feeling generous: a hint just opened early. Don't tell anyone I allowed it."

**[Voice and copy]** — L3 · Positive persistence Greeting says the player asked (§ EXPERIENCE Greeting template, `persistence` ≥ 0.34)
Positive persistence comes from Puzzles solved after the nudge with no Hint request. "Last time" is exact only while `sessions` is 1.
Fix: "Welcome back. Last time you kept going long past my first nudge; let's see what this room makes of you."

**[Voice and copy]** — L4 · "first draft" is wrong on attempt 2 (§ EXPERIENCE Capture › Regeneration)
Attempt 2 of 2 follows the second draft.
Fix: "The Riddler's draft didn't pass. Another go."

**[Voice and copy]** — L5 · Capitalized gerund mid-sentence in `failed` (§ EXPERIENCE Capture `failed`; Build job statuses)
"The build stopped at Writing puzzles."
Fix: "The build stopped while {stage label, lowercased}."

**[Voice and copy]** — L6 · Riddler role line uses jargon and misattributes the Dry run (§ EXPERIENCE Wizard introductions › Riddler role line)
"A blind test" is jargon and reads as if the Riddler runs it.
Fix: "Reads the objects; writes the puzzles, then a test run that never sees the answers checks each one can be solved."

**[Voice and copy]** — L7 · Riddler voice line describes instead of teasing (§ EXPERIENCE Wizard introductions › Riddler voice line)
PRD §7 has the Riddler tease.
Fix: "I taught your things to talk. Pity they only speak in riddles."

**[Voice and copy]** — L8 · Guide voice line holds help back (§ EXPERIENCE Guide voice line; Greeting card; UJ-1 step 5)
It repeats "never the answer" in the only encouraging slot; PRD §7 has the Guide encourage.
Fix: "Get stuck as often as you like. I'll help, a little at a time."

**[Voice and copy]** — L9 · Card log empty says "session" and capitalizes Cards (§ EXPERIENCE Play screen › Card log empty)
The UI elsewhere says "play-through"; sentence case is broken.
Fix: "No cards yet in this play-through."

**[Voice and copy]** — L10 · "3 Wrong attempts" capitalizes a Glossary term on screen (§ EXPERIENCE Triggers rows; UJ-2 step 3)
Glossary capitals belong in the spec, not in on-screen running text.
Fix: "Puzzle {n} · Direction · 3 wrong attempts"

**[Voice and copy]** — L11 · Three labels for the Build view link (§ EXPERIENCE Navigation rules › Stored Rooms; Stored Room row; DESIGN Stored Room row)
"How this room was built", "How it was built" and "How a room is built"; the generic title-block label can stay.
Fix: Stored Room row: "How this room was built"

**[Voice and copy]** — L12 · "Yours is next." can be false (§ EXPERIENCE Capture `queued`; Build job statuses)
Untrue when more than one Judge room Build waits for the single runner.
Fix: "Another room is being built. Yours is in line and will start on its own."

**[Voice and copy]** — L13 · `needs_more_photos` body cannot be followed at 10 photos (§ EXPERIENCE Capture `needs_more_photos`)
"Add photos" has nothing to add when 10 are already uploaded.
Fix: "You already have 10 photos. Start over with closer shots of shelves and tables."

**[Voice and copy]** — L14 · Narrow-screen message gives no action (§ EXPERIENCE Responsive › Below 1024 px; DESIGN Narrow-screen message; Typography)
A judge on a phone needs to know to open the link on a laptop. At `display-lg` the heading breaks into three lines in a 328 px card.
Fix: "Open this page on a laptop or desktop browser to play." Use `display-sm` for the heading.

**[Voice and copy]** — L15 · Reconnecting line is ambiguous (§ EXPERIENCE Play screen › Reconnecting)
"Nothing is counted until it's back." can read as lost progress or a paused Timer.
Fix: "Reconnecting to Keyframe. Your progress is safe; play resumes when it's back."

**[Voice and copy]** — L16 · Wizard notes rule overstates the Shortcut (§ EXPERIENCE Component Patterns › Wizard notes)
"An accepted Shortcut reveals one." is untrue when another prerequisite is unmet. Spec text, not a player string.
Fix: "An accepted Shortcut reveals the entry only when the Puzzle has no other unmet prerequisite."

## Mechanical notes

- Frontmatter: DESIGN.md has `name`, `description`, `status: draft`, `created`, `updated`, `sources` and all token groups, plus the non-spec `elevation` group. EXPERIENCE.md has `name`, `status: draft`, `created`, `updated` and `sources`. Every source path resolves.
- Token references: 148 in DESIGN.md and 19 in EXPERIENCE.md, 0 unresolved. Spacing steps `'2'`, `'6'`, `'7'` are defined but never cited, which is harmless for a scale.
- Contrast: all 33 rows match to 0.01; `lamp` on `parchment` (1.49) is correctly listed as a fail and banned.
- Name consistency: 53 component rows match exactly; drift is limited to the Access-code panel names and the narrow-screen heading token.
- Cross-references: internal anchors resolve, and citations of PRD §7, §8, §9, §11.1, §11.3, §13 and AD-2 to AD-16 are correct.
- Pending visual references use `mocks/*.png` instead of `mockups/*.html`.
- Mermaid: neither spine has a diagram.

## Reviewer files

- `review-rubric.md`
- `review-judge-demo.md`
- `review-voice-copy.md`
