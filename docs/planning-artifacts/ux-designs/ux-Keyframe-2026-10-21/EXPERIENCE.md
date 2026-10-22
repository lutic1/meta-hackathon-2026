---
title: "Keyframe Experience"
name: Keyframe
status: final
created: 2026-10-21
updated: 2026-10-22
sources:
  - ./.memlog.md
  - ./DESIGN.md
  - ../../prds/prd-Keyframe-2026-10-21/prd.md
  - ../../architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md
  - ../../briefs/brief-Keyframe-2026-10-20/schema-v1.md
  - ../../../specs/spec-keyframe/SPEC.md
  - ../../../specs/spec-keyframe/player-profile.md
  - ../../../specs/spec-keyframe/delivery-plan.md
---

# Keyframe: Experience Spine

Luis Ticas · 2026-10-21

This spine covers how Keyframe behaves: its surfaces, copy, states, interactions, accessibility floor and journeys. `DESIGN.md` covers how it looks, and this file refers to its tokens by name (`{components.hotspot}`, `{colors.lamp}`). Requirements are cited by id (FR-n, NFR-n, UJ-n from the PRD; AD-n from the architecture spine) and are not restated. Where this spine had to infer something (timings, labels, client routes, draft copy), the item is tagged `[ASSUMPTION]`. Gaps it found in upstream documents are tagged `[NOTE FOR ARCHITECTURE]` or `[NOTE FOR UX]` and gathered in Open Items. If this spine conflicts with a mock or wireframe, the spine wins.

## Foundation

- **Form factor.** Desktop web, one surface. Local mode runs in Chrome on Luis's M1 Mac. Hosted mode runs in any current desktop Chrome, Safari or Firefox at 1280 px or wider (NFR-10, A-15). The layout is designed at 1440 x 900, scales down to 1024 px, and below 1024 px shows the Narrow-screen message (see Responsive & Platform). Photos come from the phone's camera roll as JPEG files. There is no native mobile client and no live phone capture (§9).
- **No UI system.** The client is vanilla TypeScript. Scenes and Hotspots are three.js textured planes with polygon Hotspots (AD-11). Client types are generated from `GET /schema` (AD-2). Because nothing is inherited, this spine specifies all behavior and `DESIGN.md` specifies every token and component.
- **Visual reference.** `DESIGN.md` defines the Lamplit study direction: warm dark chrome, parchment for cards and notes, serif headings, and the player's own photos framed like pictures in a wizard's study. Every component named below is a `DESIGN.md.Components` row with the same name. The four key-screen mocks the builder chose are linked from the surface map rows they illustrate (Capture screen, Greeting / First-room welcome, Play screen, Completion screen, Build view). They show this spine and `DESIGN.md` at work and add nothing to them; the `DESIGN.md` tables stay the visual spec.
- **Theme and senses.** Dark theme only. No sound in v1. Motion is slow and warm, with no transition over 300 ms and no looping animation, and reduced-motion settings are honored (NFR-14). Input is mouse and keyboard. English only `[ASSUMPTION]`. No browser notifications and no offline mode: losing the network shows the reconnecting state only, on the Capture and Play screens alike (State Patterns).
- **Lead with what the room knows, never with photorealism (PRD §7).** The UI shows off what the Architect read, not how pretty the photo is:
  - The Mask preview labels every found object on a parchment chip in `{typography.label}`, and the Architect's line names two or three of them before giving the count.
  - The Capture screen's `done` state and the Build view lead with the found objects and their outlines; every Build view overlay carries its label.
  - In the Wizard notes, the Evidence cards, with the attributes the Architect read, sit directly under the Clue they support.
  - The Scene photo is never enhanced, relit, retouched or upscaled. It is framed, never improved.
- **Helps without telling (UJ-2).** The Guide's help is always visible, always tied to a Puzzle, and never an answer. Every Rung line names its Puzzle ("Puzzle {n} · Nudge"). The Active puzzle is marked in the Wizard notes. Every reply to a Hint request visibly arrives and is announced, even when it repeats a Rung already on screen. A Rung that arrives unasked gets one lamplight glow on the Guide. Rung copy follows the scaffold ladder in Voice and Tone.
- **The client renders server state.** The client renders state and posts events. It never decides whether a lock is open, which Rung is current, or whether a Trickster edit applies (AD-4). It never holds a solution or an edit payload: play routes return `PlayView`, the Build view reads `BuildView`, and Cards reach it as `cards` in session state, the `TricksterCard` projection (AD-3).
- **Two modes, one product.** The HTTP surface is the same in both modes (AD-9). This spine describes Local mode by default; Hosted Mode Differences is the one home for everything that changes in Hosted mode.

## Information Architecture

The surfaces come from PRD §8 (A-17). Navigation is mostly automatic. The player rarely chooses where to go: the Build carries them into play, and the Exit puzzle carries them to the Completion screen.

### Surface map

| Surface | Mode | Reached from | Leaves to | Purpose | FRs | Key Flow |
|---|---|---|---|---|---|---|
| Capture screen (mock [mockups/capture-screen.html](mockups/capture-screen.html): a live Build with the Architect's and Riddler's introductions, the Mask preview and the compact tray; the Empty state; the HEIC refusal) | Both | Local app open; "Build another room" (Local); accepted Access code (Hosted); a build URL | Play screen (automatic when the first Scene is ready); Build view link on `done`; stored Room replay (Local) | Choose photos, watch the Build, meet the Architect and the Riddler, read where photos go | FR-1 to FR-6, FR-10, FR-28, FR-36 | UJ-1, UJ-4, UJ-5, UJ-6 |
| Greeting / First-room welcome (mock [mockups/completion-greeting.html](mockups/completion-greeting.html): the First-room welcome with its tip, the room 2 Greeting, and the Guide thinking while it is phrased) | Both | Session start, over the first Scene | Play screen ("Begin") | Meet the Guide; the Guide's opening line | FR-20, FR-21, FR-31 | UJ-4, UJ-1, UJ-5 |
| Play screen (mock [mockups/play-screen.html](mockups/play-screen.html): mid-Session with Hotspot hover and focus, the Active puzzle, an unrequested Rung; then the first Trickster card and a Wrong attempt on the Code field) | Both | Capture screen (automatic); stored Room row (Local); Demo room card (Hosted); reload of a session URL | Completion screen (automatic on the Exit puzzle); "Leave room" | Play the Session | FR-11 to FR-19, FR-23, FR-37 (Tier 1.5) | UJ-1, UJ-2, UJ-3 |
| Card log | Both | Top-bar "Card log" button on the Play screen | Back to the Play screen | Reopen this Session's Cards | FR-19 | UJ-3 |
| Triggers panel | Both | Always-visible toggle in the Hint area; opens automatically while a Disclosure is active | Collapses in place (a second window under cut 5) | Show why each Rung changed | FR-16 | UJ-2, UJ-6 |
| Leave room confirmation | Both | Top-bar "Leave room" | Capture screen (Local) or Hosted landing (Hosted); or back to play | Leave without recording a Room result | §8 Navigation | none (guard state) |
| Completion screen (mock [mockups/completion-greeting.html](mockups/completion-greeting.html): the room 1 sheet over the dimmed last Scene, top bar inert) | Both | Exit puzzle opens | Capture screen (Local) or Hosted landing (Hosted) via "Build another room"; Build view | Show the result and record the Room result | FR-13, FR-33, FR-38 | UJ-1, UJ-5 |
| Build view (mock [mockups/build-view.html](mockups/build-view.html): opened from the Completion screen with two Disclosure lines and one Regeneration, every panel, the pinned banner below the fold, and the cut 4 Dry run rows) | Both | Capture screen on `done`; Completion screen; stored Room row (Local) `[ASSUMPTION]`; each Demo room card and the Hosted landing's "How a room is built" link (Hosted), so a judge reaches it without finishing a 15 to 25 minute Demo room (PRD §7 "Lead with the work"); route `#/build/<job_id>/view`, open in both modes with no Access code (AD-3); Demo rooms have a seeded job record, so every entry point works for them (AD-7) | "Back" to where it was opened from | Show how the Room was built and verified | FR-38, FR-30, FR-27 (cached or billed) | UJ-6, UJ-1, UJ-5 |
| Hosted landing | Hosted | Hosted URL; "Build another room" (Hosted); "Leave room" (Hosted) | Play screen (Demo room card); Build view (Demo room card link, "How a room is built"); Capture screen (accepted Access code) | Play a Demo room or see how it was built (where the wizards are introduced); unlock a Judge room Build | FR-31, FR-32, FR-38 | UJ-5 |
| Disclosure banner | Both | Shown on the Capture, Play and Completion screens, the Build view and the Hosted landing whenever a Disclosure applies | Not navigable | Name each demo shortcut or mode in effect | FR-24 to FR-26 | UJ-5, UJ-6 |
| Deleted Judge room notice | Hosted | A Judge room URL opened after Tue Nov 10 (the server answers `room_deleted`, AD-9) | Hosted landing | State that the deletion happened as promised | FR-33 | UJ-5 (resolution) |
| Narrow-screen message | Both | Any surface below 1024 px wide | Not navigable | Say that Keyframe plays on a laptop or desktop browser | A-15 | none (guard state) |

### Navigation rules

- Modals are one level deep. The Greeting, the Leave room confirmation and the Card log are all modal (scrim below the top bar, focus trapped, Scene, Hotspots and top bar inert) and never open on top of each other.
- **Client routes** `[ASSUMPTION]`: hash routes, because FastAPI serves `web/dist` statically at `/` (AD-9) and this avoids a server-side fallback. The routes are `#/` (Local: Capture screen; Hosted: Hosted landing), `#/build/<job_id>` (Capture screen for that Build; resumes polling, FR-32), `#/build/<job_id>/view` (Build view), `#/play/<session_id>` (Play screen; reload resumes, FR-11), and `#/done/<session_id>` (Completion screen). The `?profile=` query parameter (AD-14) is carried on every route.
- **Stored Rooms (Local).** The list comes from `GET /rooms` (AD-9); the browser keeps no list of its own. Row behavior is in Component Patterns (Stored Room row). Replaying a stored Room never shows the Timer.
- **Leave room** opens a confirmation. Confirming records no Room result (§8).
- The browser Back button moves between routes. On the Play screen it acts like "Leave room" and asks for the same confirmation `[ASSUMPTION]`.

### Closure

**Every FR that has a UI lands on a surface:**

| FR | Surface |
|---|---|
| FR-1, FR-4, FR-5, FR-6 | Capture screen |
| FR-2, FR-3 | Capture screen (Stage list, Mask preview); Play screen (Hotspots); Build view (mask overlays) |
| FR-7 | Play screen (Clue, Lore and Rungs in the Wizard notes and Hint area) |
| FR-8, FR-9 | Build view (Validator verdict table, Dry run rows) |
| FR-10 | Capture screen (Regeneration stage rows, `needs_recapture`); Build view (Regeneration count) |
| FR-11, FR-12, FR-14 to FR-16 | Play screen |
| FR-13 | Completion screen |
| FR-17 | Play screen (Rung line, Guide thinking state) |
| FR-18, FR-19 | Play screen (Trickster cards in the Hint area, Evidence cards); Card log |
| FR-21 | Greeting / First-room welcome (which also introduces the Guide) |
| FR-23 | Every Wizard portrait: Stage list (Architect and Riddler introductions), Wizard notes, Hint area, Cards (Trickster introduction on the first), Greeting, Demo room cards, Build view Model table and In play block |
| FR-24, FR-25, FR-26 | Disclosure banner (FR-25 also through Trickster cards) |
| FR-27, FR-30 | Build view (Model table) |
| FR-28 | Capture screen (Spend cap message); Play screen (skipped Card) |
| FR-31 | Hosted landing; Play screen; First-room welcome |
| FR-32 | Hosted landing (Access-code build); Capture screen (`queued`, quota) |
| FR-33 | Completion screen ("Deleted Tue Nov 10"); Deleted Judge room notice |
| FR-36 | Capture screen (Retention summary, Privacy line); typed hint text never sent |
| FR-37 (Tier 1.5) | Play screen (Clue card slot in the Wizard notes) |
| FR-38 | Build view |

**FRs with no UI surface:** FR-20 and FR-22 (the Player profile and the demo flag live in IndexedDB, with no viewer in v1), and FR-29 (Ledger export). FR-34 (Tier 2, UJ-7) and FR-35 (voice) stay out of this contract until they are scheduled; both share the one-line UJ-7 placeholder.

**Cut 2 placeholder (Player profile as a local JSON file).** Under cut 2 the Retention summary gains an "Open profile file" Secondary button below the Privacy line (browser file picker) and the Completion screen gains a "Save profile file" Secondary button (browser download), with one plain line, "Your player profile is a file on this computer; Keyframe reads it only when you open it." The Privacy line holds unchanged `[ASSUMPTION for the control and copy]`.

**Every surface has a Key Flow**, except the Leave room confirmation and the Narrow-screen message. Both are guard states the PRD defines without a journey; Component Patterns and State Patterns specify them fully, so neither gets an invented one.

## Voice and Tone

Microcopy only. Brand voice and how the two registers look live in `DESIGN.md` (Brand & Style).

### Register rule (PRD §7)

| Register | Lines | Treatment |
|---|---|---|
| **In character** | Rungs, the No-hint line, the Greeting, the First-room welcome, Cards (the Trickster's sentence), Clues, Lore, Build stages (the Architect's stage lines), each wizard's introduction voice line, the Guide's Completion sign-off | `{typography.wizard-line}` (or `{typography.wizard-line-lg}`, `{typography.lore}`), signed with the speaker's Wizard portrait, usually on parchment. Wry and playful, never condescending, one or two sentences. The Architect observes, the Riddler teases, the Guide encourages, and the Trickster has the most fun. |
| **Plain messages** | Format and count errors, upload failure, `failed`, `needs_more_photos`, `needs_recapture`, `queued`, Spend cap, Build quota, Access code, session start refused, deletion messages, the Retention summary, the Privacy line, the hint field's helper line, the reconnecting state, the mode indicator, the Hosted pipeline line, every caption in the Build view, every Disclosure | `{typography.body-md}` or `{typography.body-sm}`. No portrait, never on parchment, no jokes. Says what happened and what to do next. |
| **Plain labels and chips** | Build stage names and done-row results, Rung names and "Puzzle {n}" labels, evidence counts, Card outcome labels, the "Proposed: …" line and the Validator's reason on a rejected Card, the Timer label, the "Checking", "Not this" and "Open" chips, stat labels, Hotspot and mask label chips, each wizard's name and role line where it is introduced | `{typography.label}` or `{typography.body-sm}`, sans. May sit on parchment. |

Headings are set in the serif everywhere, on plain surfaces too (`DESIGN.md` Brand & Style); the register is carried by the body face and the portrait, never by the heading.

General rules: sentence case everywhere. No exclamation marks. No emoji. No "Oops". No "successfully". A line never names a solution token, and wizard lines never name an object unless they are a Clue, an Evidence card, a Rung pointing where to look, or the Architect's line naming what it found. Numbers are digits. A state never relies on color or an icon alone: each one carries a word.

### Helps without telling: Rung and Guide line rules (PRD §7, §3 Rung)

| Level | Says | Length | Sample `[ASSUMPTION]` |
|---|---|---|---|
| Nudge | Where to look | Shortest: one short sentence | "The shelf has been very quiet. Suspiciously quiet." (PRD §7 sample) |
| Direction | What to notice there | Longer than the nudge | "Those spines aren't all facing the same way, and I doubt that's an accident." |
| Near-answer | How to use what was noticed | Longest, still at most two sentences | "Read the spines that face out, left to right, and let them tell you the order." |

- **Scaffold, never answer.** No Rung says "the answer is", "the code is" or anything like it, and none names a solution token beyond the Rule 5 allowance. Each Rung is enough on its own to move the player one step forward.
- **Rungs increase in length** from nudge to near-answer.
- **After the near-answer**, a further Hint request repeats the near-answer (A-21). There is no reveal or skip.
- **No-hint line criteria (PRD §7):** in-world and encouraging; never a refusal and never "no hint available"; it acknowledges the ask, says the Guide is watching and help is coming, invites one more look, and holds nothing about any Puzzle. The PRD sample, "Look around a little longer; I'll speak up if you stay stuck.", invites a look and promises help but does not clearly acknowledge the ask, so the fixed line adds a short acknowledgement: "A fair ask. Look around a little longer; I'll speak up if you stay stuck." The builder accepted this on two conditions, which the line meets:
  - **No clue.** The acknowledgement names no object, place, attribute or Puzzle content, and neither does the rest of the line. It says nothing about what was typed, because nothing typed is read.
  - **No interruption.** It arrives as an ordinary Rung line in the Hint area and is announced through the polite live region. No modal, no focus move, no scrim, and no input is blocked or delayed: the Scene, the Wizard notes and the lock inputs stay usable while it shows.

### Voice for generated lines

Most of the wry voice lives in lines the models write: Clues, Lore and Rungs (authored by the Riddler at Build time) and the Greeting and phrased Rungs (phrased locally by the Guide model). Hosted mode and every fallback show the authored lines verbatim, so they must already be in voice. The prompts carry these rules (AD-5): the Riddler author prompt carries the generated-line rules (Clue and Lore in the Riddler's voice, Rungs in the Guide's voice on the scaffold ladder, no solution tokens), and the `phrase` and `greet` fixed prefixes carry "reword, never add content" and the Greeting brief.

| Line | Written by | Voice | Length | Sample `[ASSUMPTION]` |
|---|---|---|---|---|
| Clue | Riddler prompt | The Riddler's: teasing, points at the Evidence without quoting it | One or two sentences | "Someone in this room is very proud of the year they were made. Ask the mug." For an order Puzzle: "Some books on this shelf are better dressed than the rest." |
| Lore | Riddler prompt | The Riddler's, in-world flavor; no help, no tokens | At most 60 words | "The mug has outlived three kettles and one diet. It remembers everything and says nothing, unless you look closely." |
| Rungs (nudge, direction, near-answer) | Riddler prompt, written in the Guide's voice because the Guide signs them | The Guide's: encouraging, warm; the scaffold ladder above | As the ladder | See the ladder above |
| Phrased Rung | Guide model (Local) | The Guide's | No longer than the Rung it rewords | Rewords; never adds content |
| Greeting | Guide model (Local) or the template | Wry, warm and specific about play style (PRD §7) | One or two sentences | See the template below |

- **Per-wizard attitude.** The Architect observes (plain facts with a dry aside), the Riddler teases (never mocks), the Guide encourages (never scolds, never sighs), the Trickster has the most fun (mischief aimed at the room, never at the player). Never condescending.
- **Phrasing may reword but never add content.** A phrased Rung or Greeting carries no fact that is not in its source (the Rung text or the Derived block numbers): no new object, no new hint, no solution, no play history beyond the Derived block.
- **Never name a token.** No Clue, Lore line or Rung names a solution token beyond the Rule 5 allowance, and no Evidence card displays one. Validator rule 5 enforces this on the Rungs, the Clue and `evidence.visible_attribute` with the same matching rules: every displayed attribute says where to look and never holds a solution token (Schema v1, AD-3).

### Exact strings

`[ASSUMPTION]` marks wording this spine drafted. Strings marked "verbatim" come from the PRD Glossary, a requirement or the memlog and must not be paraphrased (the Input requirement, the Privacy line, the FR-1 and Spend cap errors, "n of 20 builds left", "Deleted Tue Nov 10", the Disclosure lines). The PRD §7 sample lines (sample nudge, No-hint line, Greeting template, First-room welcome, Card sentences) are illustrative: the UX contract may reword any of them if the rewrite keeps the line's functional intent (PRD §7). This spine adopts them as defaults and edits them where noted. Every line here is checked for consistency, clarity, personality and readability at small widths (the 340 px side column at 1024 px).

**Wizard introductions (PRD §7: what each wizard consumes and produces, then its voice).** Each wizard is introduced in place where it first works, with its name, its role line (plain label) and one voice line (in character). Each role line names the Meta model (or the local model) behind the wizard, so the model stack stays visible on every surface even under cut 0, when the Build view is gone. There is no separate band of wizards on any surface. This table is the one home for where each introduction sits; `DESIGN.md` Components draws them. `[ASSUMPTION for every line]`

| Wizard | Introduced on | Role line (plain) | Voice line (in character) |
|---|---|---|---|
| Architect | The Architect's row at the top of the Stage list, from Upload, on the Capture screen in both modes | "Reads your photos with muse-spark-1.3, names the objects, and draws their outlines with sam-3.1." | "I notice everything. Mostly mugs." |
| Riddler | The "Writing puzzles" row of the Stage list, when that stage starts, in both modes | "Reads the objects; writes the puzzles with muse-spark-1.3, then a test run that never sees the answers checks each one can be solved." | "I taught your things to talk. Pity they only speak in riddles." |
| Guide | The Greeting or First-room welcome card, under the heading "The Guide" | Local: "Reads how you play; offers one hint at a time, never the answer, worded by Llama 3.2 3B on this Mac." Hosted (and whenever the `guide` setting is verbatim): "Reads how you play; offers one hint at a time, never the answer, shown as written." | "Get stuck as often as you like. I'll help, a little at a time." |
| Trickster | Its first Card of the Session, the role line under its name, once | "Reads the game state; proposes changes between puzzles with muse-spark-1.3, and the Validator checks each one." | "I like to move things around. The Validator keeps me honest, sadly." |

The role lines name the default model for each role; when a backup provider runs the Riddler or the Trickster, the Build view Model table shows the model that actually ran. On the Hosted landing the wizards appear through the Demo room cards (four portraits on each), the pipeline line in the title block, and, behind "How a room is built", through the Build view: the Model table shows the Architect's and Riddler's role lines on their rows, and the In play block shows the Guide's and Trickster's `[ASSUMPTION, for the builder]`. Their voice lines appear where each first works in play or in a Judge room Build.

**Capture screen (plain)**

| Moment | String |
|---|---|
| Input requirement (verbatim term) | "6 to 10 JPEG photos", standing alone once, as the first line of the right column. The dropzone carries the picker sentence, which uses the term inside a sentence: "Choose 6 to 10 JPEG photos of one room." `[ASSUMPTION for the sentence around the term]` |
| iPhone tip | "On iPhone, set Settings > Camera > Formats to Most Compatible so photos save as JPEG." `[ASSUMPTION]` |
| Faces, documents, belongings reminder | "Leave out faces, documents and other people's belongings." `[ASSUMPTION]` |
| Picker button / Upload | "Choose photos" / "Upload" `[ASSUMPTION for "Choose photos"]` |
| Photo tray remove control (accessible name) | "Remove photo {n}" (n = its place in upload order) `[ASSUMPTION]` |
| HEIC, PNG, other format, or wrong count (set rejected whole) | Banner: "Keyframe needs 6 to 10 JPEG photos." (verbatim, FR-1) as the banner heading, with no body sentence, and the action "Choose photos again". Label on each offending file: "Not a JPEG". When the count is the problem, the count line reads "{n} photos chosen" `[ASSUMPTION for the labels and the action]` |
| Downscaled file refused by ingest (422) | "Keyframe couldn't read these photos. Choose them again." `[ASSUMPTION]` |
| Upload failed (any other failure of the upload: network, 5xx) | Heading "Your photos didn't reach Keyframe." Body "Nothing was built. Check the connection and try again." Action "Try again" (sends the same set) `[ASSUMPTION]` |
| Reconnecting during a Build (status strip) | "Reconnecting to Keyframe. Your build keeps going; this page catches up when it's back." `[ASSUMPTION]` |
| Session start refused (after `done`, a stored Room "Play" or a Demo room card) | Heading "Keyframe couldn't start this room." Body "Your room is safe. Try again." Action "Try again" `[ASSUMPTION]` |
| Timer label | Running: "Photos to play". Frozen at T1: "Playable in". Hosted, while `queued`: "queued" in place of the digits; after a queue: "includes m:ss in the queue" after the digits `[ASSUMPTION]` |
| Stage names (A-11; plain labels in the Stage list) | "Reading your photos" (ingest) · "Finding objects" (architect, segment) · "Writing puzzles" (author) · "Testing the room" (validate, dry run) · "Setting the scene" (scene). Regeneration: "Rewriting puzzles, attempt n of {max}" ({max} is the configured `REGEN_MAX`: 2, or 1 under cut 7), with "Sent back: {fixed messages of the failed attempt}" under it |
| Done-row results (plain, beside each done stage; the model id sits beside the duration, which reads like "4.2 s") `[ASSUMPTION]` | Reading your photos: "8 photos" · Finding objects: "9 objects" (muse-spark-1.3 · sam-3.1) · Writing puzzles: "5 puzzles" (muse-spark-1.3) · Testing the room, two lines: "Rules: 8 of 8 passed" (code, no model) and "Test run: reached 5 of 5 answers" (muse-spark-1.3) · Setting the scene: "8 scenes ready" |
| Architect stage lines (in character, one per stage, in the running stage row under the Architect's introduction row) `[ASSUMPTION]` | Reading your photos: "{n} photos of one room. Let me find my loupe." · Finding objects: the Architect line below · Writing puzzles: "I've handed my notes to the Riddler. Brace yourself." · Testing the room: "Now we make sure every lock can actually be opened. Fair is fair." · Setting the scene: "Hanging your room on the wall. Mind the frame." · Regeneration: "The Riddler's draft didn't pass. Another go." |
| Architect line for the Mask preview (in character; the "Finding objects" stage line) | "I see {n} things worth a closer look, starting with the {label 1}, the {label 2} and the {label 3}." Two-label case: "I see {n} things worth a closer look, starting with the {label 1} and the {label 2}." (the labels come from the found Interactables in segment order) `[ASSUMPTION]`. It sits in the running "Finding objects" row and moves on like every stage line when "Writing puzzles" starts; the Mask preview has no line or heading of its own |
| Retention summary heading | "Where your photos go." (the served text follows it) `[ASSUMPTION]` |
| `queued` (Hosted, warning) | "Another room is being built. Yours is in line and will start on its own." `[ASSUMPTION]` |
| Hosted lines under the Stage list (plain) | "This build has its own link; close this tab or play a demo room meanwhile." · "The two-minute build target is measured in Local mode on the Mac; here the timer also counts any time in the queue." `[ASSUMPTION]` |
| `needs_more_photos` (error) | Heading "Keyframe found too few objects to build a room." Body "Add a few more photos of this room, closer to shelves and tables, up to 10 in all." When 10 photos are already in the set: "You already have 10 photos. Start over with closer shots of shelves and tables." Actions: "Add photos" (absent in the 10-photo case), "Start over" `[ASSUMPTION for heading and body]` |
| `needs_recapture` (error) | Heading "Keyframe couldn't build a fair room from these photos." Body "Try brighter, closer shots where labels and printed text are readable." Action: "Start over" `[ASSUMPTION for heading]` |
| `failed` (error) | Heading "The build stopped while {stage label, lowercased}." (for example "The build stopped while writing puzzles.") Body: one cause class, either "A model service didn't answer." or "The build stopped unexpectedly." Action: "Try again" (new Build, same photos). In Hosted mode the body adds "Trying again uses one of the remaining judge builds." `[ASSUMPTION for cause and consequence wording]` |
| Spend cap refusal (warning; `failed` with `spend_cap_exceeded`) | "Keyframe has reached its spending limit, so this room can't be built right now." (verbatim, PRD §7), then "Trying again won't help until the limit is raised; your photos are still here." `[ASSUMPTION]`. No "Try again" action; "Start over" only |
| Build quota exceeded (Hosted, warning) | "All 20 judge builds have been used. The demo rooms are still open." `[ASSUMPTION]` |
| Done | Build view link: "How this room was built" `[ASSUMPTION]`. On a reopened build URL that is already `done`: "Play this room" (primary) `[ASSUMPTION]` |

**Hosted landing (plain unless noted)**

| Moment | String |
|---|---|
| Title / subtitle | "Keyframe" / "An escape room built from your own photos." `[ASSUMPTION]` |
| Pipeline line (under the subtitle) | "muse-spark-1.3 reads your photos and writes the puzzles, sam-3.1 outlines every object, a test run that never sees the answers checks each puzzle can be solved, and the Guide hands out hints one at a time." `[ASSUMPTION]` |
| Title-block lead-in and link | "Short on time? See how a room is built and checked." then the link "How a room is built" (opens the first Demo room's Build view) `[ASSUMPTION]` |
| Demo room card title / meta / link | The Room's name (`Room.name`; the build time when absent) / "{n} puzzles · 15 to 25 min" / "How this room was built" `[ASSUMPTION for the link]` |
| Demo room card portraits (accessible name of the row) | "The Architect, the Riddler, the Guide and the Trickster" `[ASSUMPTION]` |
| Access-code build | Heading "Build your own room". Field label "Access code". Button "Check code" `[ASSUMPTION]` |
| Access code empty submit | "Enter the access code from the submission." `[ASSUMPTION]` |
| Access code refused | "That access code isn't right. No photos were sent." `[ASSUMPTION]` |
| Access code checks rate-limited | "Too many tries. Wait a moment, then check the code again." `[ASSUMPTION]` |
| Access code accepted | "{n} of 20 builds left" (verbatim, §8) |
| Quota reached | As the Build quota string above |
| Demo rooms failed to load | "Keyframe couldn't load the demo rooms." with "Try again" `[ASSUMPTION]` |
| No Demo rooms | "No demo rooms are open right now. You can still build your own room with the access code." `[ASSUMPTION]` |

**Play screen**

| Moment | Register | String |
|---|---|---|
| Hint field placeholder / button | plain | "Stuck? Ask the Guide for a hint" `[ASSUMPTION]` / "Ask the Guide" (verbatim) |
| Hint field accessible label | plain | "Ask the Guide for a hint on Puzzle {n}" (n = the Active puzzle) `[ASSUMPTION]` |
| Code field accessible label | plain | "Code for Puzzle {n}"; the field has no visible label or placeholder `[ASSUMPTION]` |
| Hint field helper (permanent, under the field) | plain | "Your words stay in this browser. The Guide only hears that you asked." `[ASSUMPTION]` |
| Button while sending | plain | "Asking" `[ASSUMPTION]` |
| Guide thinking label (Local only) | plain label | "thinking on this Mac" `[ASSUMPTION]` |
| Puzzle heading (Wizard notes) | plain label | "Puzzle {n}" (n = the Puzzle's order number in the Room, the same number the Rung lines, Triggers rows, Card labels and Build view graph use, so it never changes when a Merge or Shortcut reorders availability), with "Current" beside the Active puzzle's heading `[ASSUMPTION]` |
| Evidence count (right end of the Puzzle heading row) | plain label | "{k} evidence cards" ("1 evidence card" for one) `[ASSUMPTION]` |
| Rung label | plain label | "Puzzle {n} · Nudge", "Puzzle {n} · Direction", "Puzzle {n} · Near-answer"; the No-hint line is labelled "Puzzle {n}" |
| Sample nudge (PRD §7; Rungs themselves come from the Room) | in character | "The shelf has been very quiet. Suspiciously quiet." |
| No-hint line (fixed) | in character | "A fair ask. Look around a little longer; I'll speak up if you stay stuck." (PRD §7 sample plus an acknowledgement that gives no clue and interrupts nothing; see the No-hint criteria) |
| Ollama fallback | none | **Silent on the Rung line.** The verbatim Rung appears with the same anatomy as a phrased one: no notice, no badge, no "verbatim" label (FR-17; `DESIGN.md` Do's and Don'ts). Where each Rung was worded shows only in its Triggers row ("worded on this Mac · 1.6 s" or "as written"), so a verbatim Rung can never pass for local wording on video |
| Pending chip | plain | "Checking" with a static ellipsis (no animation) `[ASSUMPTION]` |
| Merge-hidden entry placeholder | plain label | "Puzzle {n} now waits on another puzzle." `[ASSUMPTION]` |
| Order click progress description | plain | "{filled} of {length}" (visually hidden) `[ASSUMPTION]` |
| Order puzzle start control | plain | "Start the sequence"; while armed, "Stop the sequence"; back to "Start the sequence" when another Puzzle becomes Active (AD-4) `[ASSUMPTION for the wording]` |
| Collected item, clicked again in the Scene | plain | "{label} · in hand" on the Hotspot label chip `[ASSUMPTION]` |
| Cards beyond two | plain | "{n} more in the Card log" `[ASSUMPTION]` |
| Wrong attempt chip | plain | "Not this · {n}" (n = Wrong attempts at this lock) |
| Open chip | plain | "Open" |
| Clicked non-target Hotspot | plain | The Interactable's label only, on the Hotspot label chip |
| Empty Inventory | plain | "Nothing in hand yet." `[ASSUMPTION]` |
| `use_on` selected chip | plain | "Using {item label}" plus "Cancel" `[ASSUMPTION]` |
| Triggers toggle / header / rows | plain | Toggle: "Triggers ({n})". Header line: "Nudge after {threshold} s idle or 3 wrong attempts · next hint no sooner than {spacing} s"; at a Demo timescale n > 1 each number carries its 1× value ("Nudge after 15 s idle (90 s at 1×) …"); then the source: "Set by how you played last time (kept in this browser)" or, on a fresh Player profile and in Hosted mode, "Default for a first room". Rows: "Puzzle {n} · Nudge · Idle 92 s · worded on this Mac · 1.6 s", "Puzzle {n} · Direction · 3 wrong attempts · as written", "Puzzle {n} · Near-answer · Loosen card · as written". Open with no rows: "No hint changes yet." `[ASSUMPTION for row layout and wording]` |
| Top bar | plain | "Show all objects", "Card log", "Leave room" (on the Play screen, and inert on the Completion screen; the Capture screen, Build view and Hosted landing show none of them); mode indicator "Local mode · Cache off · profile {name} · {k} rooms played" ("0 rooms played" on a fresh profile, "1 room played"; "Cache on" when on) or "Hosted mode" `[ASSUMPTION for the indicator wording]` |
| Leave room confirmation | plain | "Leave this room? This play-through won't be recorded." Buttons "Leave room" / "Keep playing" `[ASSUMPTION]` |
| Reconnecting | plain | "Reconnecting to Keyframe. Your progress is safe; play resumes when it's back." `[ASSUMPTION]` |
| Session gone (Hosted log expired) | plain | "This play-through has ended. Start the room again." Button "Start again" `[ASSUMPTION]` |
| Server unreachable (cold load) | plain | "Keyframe can't reach its server. Retrying." `[ASSUMPTION]` |
| Session start refused | plain | See the Capture screen table; the same banner serves the Capture screen, the stored Room row and the Hosted landing |
| Unknown room (`room_not_found`, distinct from a deleted Judge room, AD-9) | plain | Heading "Keyframe can't find this room". Body "Check the link, or start from the beginning." Button "Go to the demo rooms" (Hosted) or "Build a room" (Local) `[ASSUMPTION]` |
| Card log empty | plain | "No cards yet in this play-through." `[ASSUMPTION]` |

**Greeting and First-room welcome (Guide, in character)**

- **Greeting brief (PRD §7).** Wry, warm and specific about play style; never about objects; never surveillance-flavored; one or two sentences. It should make a returning player feel recognized by the game, not tracked by a service.
- **Greeting template.** Used when phrasing is unavailable: cut 3, Ollama past 5 s, or Ollama unreachable. AD-5's "template filled with the numbers" is realized as one template whose phrase is chosen by the Derived block's numbers `[ASSUMPTION]`, checked in this order:
  - `time_to_first_hint_s` is null (the player never asked): "Welcome back. Last time you never asked me once; let's see what this room makes of you."
  - `persistence` ≥ 0.34: "Welcome back. Last time you kept going long past my first nudge; let's see what this room makes of you."
  - `persistence` −0.33 to 0.33: "Welcome back. Last time you held out a good while before asking; let's see what this room makes of you."
  - `persistence` ≤ −0.34: "Welcome back. Last time you held out just long enough to get your bearings before asking; let's see what this room makes of you."
  With Ollama, `greet(derived)` phrases the line freely under the Greeting brief and the generated-line rules: no object, no solution, nothing that sounds like surveillance, nothing beyond the Derived block.
- **First-room welcome.** "Welcome to your own room. Find what doesn't belong." This keeps the PRD §7 line word for word: the builder's copy condition asks that the welcome clearly convey "Find what doesn't belong", and keeping the phrase is the safest way to meet it. It is two short sentences, so it wraps cleanly on the 560 px card. **Demo room variant**, chosen by the server for a Session on a Demo room (which is not the player's room): "Welcome to someone else's room. Find what doesn't belong." It keeps the phrase word for word `[ASSUMPTION]` (see Open Items). Under the card, once per Player profile, a plain tip: "Tip: 'Show all objects' in the top bar outlines everything you can click." `[ASSUMPTION for the tip]`
- **The Guide's introduction on the card.** On both the Greeting and the First-room welcome, the heading "The Guide" with the Guide's role line under it, and the Guide's voice line, "Get stuck as often as you like. I'll help, a little at a time.", under the opening line (see Wizard introductions).
- **Begin** is the only button.

**Cards (Trickster, in character, then a plain outcome label)**

Each sentence is a literal effect clause followed by one Trickster flourish; the sentence comes first and the outcome label after it. Every label names the Validator, so fairness shows on both sides: "Validator passed" on an accepted Card, "Validator refused" on a rejected one. The PRD §7 samples are kept as the effect clauses, except Shortcut, whose draft "A door just opened early." misstated the mechanic. A Shortcut removes one prerequisite, so one Puzzle may become available early; it never opens a lock and never skips a Puzzle. The Shortcut sentence says exactly that much and promises nothing more: the Puzzle may turn up sooner, and the player still solves it. Every flourish is `[ASSUMPTION]`. The first Card of the Session also carries the Trickster's introduction (name, role line, voice line; see Wizard introductions), once.

| Outcome | Sentence | Label (`{typography.label}`, after the sentence) |
|---|---|---|
| Accepted Decoy | "A new evidence card has appeared. I do love a crowded desk." | "Validator passed · Decoy · Puzzle {n}" (n = the Puzzle whose evidence grew; its evidence count ticks up by one, and nothing says which card is new) |
| Accepted Merge | "One puzzle now waits on another. Patience builds character; I build locks." | "Validator passed · Merge · Puzzle {n}" (n = the Puzzle that now waits) |
| Accepted Loosen | "The Guide is feeling generous: a hint just opened early. Don't tell anyone I allowed it." The Rung also appears as a Rung line. | "Validator passed · Loosen · Puzzle {n}" |
| Accepted Shortcut | "One puzzle no longer waits on another, so it may turn up sooner. Solving it is still on you." | "Validator passed · Shortcut · Puzzle {n}" (n = the Puzzle that lost a prerequisite) |
| Rejected (any type) | "The Validator says that wouldn't be fair. Spoilsport." | "Validator refused · {type} · Puzzle {n}", then two plain lines: "Proposed: {structural summary}" (Decoy: "a false evidence card for Puzzle {n}"; Merge: "Puzzle {n} waits on Puzzle {m}"; Loosen: "open the next hint on Puzzle {n} early"; Shortcut: "Puzzle {n} stops waiting on Puzzle {m}"; ids and numbers only, never content) and "That change was refused. {fixed message}" |
| Skipped (provider error or Spend cap; same text for both causes) | "I'm keeping quiet this time. Enjoy it while it lasts." | "Skipped" |

A Decoy Card never says which Evidence card is false (FR-19), and no flourish hints at it. **Fixed reason messages** belong to the Validator (AD-3) and serve four places: a fail row in the Build view's verdict table, the regeneration prompt, the "Sent back" lines (Capture Regeneration row and Build view header) and the rejected Card. Each is one neutral, plain sentence that never contains a token; the rejected Card adds its own "That change was refused." framing in the UI. A pass row never prints the fixed message: it shows the rule's check-phrased name instead. Proposed wording `[ASSUMPTION]`:

| Rule | Check name (pass) | Fixed message (fail) |
|---|---|---|
| 1 | "No two locks wait on each other" | "Two locks would wait on each other forever." |
| 2 | "Every lock can be reached" | "A lock could never be reached." |
| 3 | "Every puzzle names something in this room" | "A puzzle names something that isn't in this room." |
| 4 | "Every puzzle cites something the Architect saw" | "A puzzle cites something the Architect never saw." |
| 5 | "No hint, clue or evidence gives an answer away" | "A hint gives part of an answer away." |
| 6 | "Lore and hints keep to the length rules" | "Lore or a hint breaks the length rules." |
| 7 | "Every lock has a valid shape" | "A lock doesn't have a valid shape." |
| 8 | "Every needed item can be picked up first" | "A puzzle needs an item that can't be picked up yet." |
| 9 (after the decoy pick) | "False evidence follows the decoy rules" | "A false clue breaks the decoy rules." |
| `validate_edit` bounds | none (no pass row) | "The change is outside the Trickster's limits." |

**Build view captions (plain, one per table)** `[ASSUMPTION]`:

- Verdict table: "The Validator is code, not a model. It checks these 8 rules on every draft; a failed rule sends the draft back to the Riddler."
- Dry run rows: "A separate muse-spark-1.3 call saw only the clues, hints and object names, never the answers, and tried every puzzle."
- Model table, under it: "Cached means an identical earlier call was served from the cache, unbilled; billed means it ran live and was paid for."
- BuildView JSON pane: "Everything this page receives. It holds no answers; a sentinel test checks every build for them."
- Dry run rows under cut 4, in place of the Dry run caption: "The test run was switched off for this build, so no puzzle was tried blind."

**Build view labels (plain)** `[ASSUMPTION]`: the panels carry no headings, only their captions and table header cells. Model table header: "Role", "Model", "Where it ran", "What it did", "Cached or billed". Verdict table: "Rule", "Check", "Verdict". Dry run rows: "Puzzle", "Lock type", "Verdict". Hosts: "Meta Model API", "this Mac" (the Validator), "Ollama on the Mac" (the Guide in the In play block). Trickster source in the In play block: "Source: live", "Source: scripted" or "Source: written in advance" (cut 1). A Room with no name is titled by its build time, as "Tue Nov 3, 10:42".

**Completion screen**

| Element | Register | String |
|---|---|---|
| Heading | plain heading (serif, like every heading) | "The room is open." `[ASSUMPTION]` |
| Guide sign-off (48 px Guide portrait) | in character | Chosen from the Session's stats only, never objects `[ASSUMPTION]`: no Rungs used: "Not a single hint. I'm almost offended." · 1 to 3 Rungs: "You let me help a little. I enjoyed every word." · 4 or more: "We solved it together, and I'd do it again." |
| Stat labels | plain label | "Time", "Hints used", "Wrong attempts", "Time per puzzle" `[ASSUMPTION]` (Rung stays the term in this spec) |
| Actions | plain | "Build another room" (verbatim); "How this room was built" `[ASSUMPTION]` |
| Judge room | plain, below the sheet | "Deleted Tue Nov 10" (verbatim, FR-33) |
| Deleted Judge room notice | plain | Heading "This room is gone". Body "This room was deleted on Tue Nov 10, as promised." Button "Go to the demo rooms" `[ASSUMPTION for exact phrasing of FR-33]` |

**Disclosure copy (plain, out of character, literal; PRD §7)**

The server composes every line (AD-15); the client renders them as served.

| Condition | Line |
|---|---|
| `demo_timescale` > 1 | "Hint and Trickster timings run at n× speed; the build timer is real time." (n = the timescale; PRD §7, AD-15) |
| `trickster: scripted` | "Trickster proposals replayed from a recording; the Validator ran live." |
| `trickster: cut1` | "Trickster proposals were written in advance; the Validator ran live on each." |
| `mode: hosted` | "Hosted mode: hints are shown as written; no hint model runs here." |
| An earlier-built Room is in play or on view: a Demo room, a Room with an earlier session (a stored Room replay), or a Build with any call served from the Cache (PRD UJ-6 step 4) | "This room was built earlier, on {date}." (date from the Room's build time). Per-Room: carried in the session state's and `BuildView`'s `disclosure` list, never in `GET /meta` (AD-15) |

The global lines (the first four) come from `GET /meta` `disclosure`; the per-Room `disclosure` list in session state and in `BuildView` holds the applicable global lines plus the earlier-builds line for that Room (AD-15). A Build in progress with `CACHE=on` shows "Cache on" in the mode indicator; once its Room exists, a cached call puts the earlier-builds line in that Room's list.

**Privacy and retention (plain)**

- **Privacy line**, verbatim: "the player profile stays on your machine." It holds under every Cut, including cut 3. A plain label, "Your play history" `[ASSUMPTION]`, sits directly above it, so in Hosted mode it reads as a separate topic and is not skimmed as a contradiction of the Modal storage sentence just before it.
- **Retention summary.** Shows the one text served by `GET /meta` (`retention`), as served. The server serves one text per mode: the Hosted text replaces the Local storage sentence, never appends to it (AD-8, AD-15). Its final wording depends on §13 Q3. The texts this spine expects `[ASSUMPTION; Q3 owns the final words]`:
  - **Heading (client, both modes):** "Where your photos go.", above the served text.
  - **Shared opening (both modes):** "Your photos and the puzzle text go to the Meta Model API (standard tier) to find objects, write puzzles and test them; {Meta retention terms}. If a backup model is switched on for the Riddler or the Trickster, that role's prompt goes to Baseten or Fireworks, never with an answer or anything from your player profile; {terms}."
  - **Local ending:** "A copy of your photos is also kept on this computer."
  - **Hosted ending (FR-6):** "In Hosted mode, your photos, the originals, your room and its play-throughs are stored on Modal and deleted Tue Nov 10. Play-through logs are deleted 24 hours after their last event. No player profile data leaves your browser."
  - The repository claim (photos under `rooms/`, never committed, FR-36) belongs in the README, not in the player-facing text. The fal.ai line appears only when Tier 2 ships. The voice line appears only when voice ships.

## Component Patterns

Behavior only. Visual specs live in `DESIGN.md.Components`, under the same names.

### Shared controls

| Component | Behavioral rules |
|---|---|
| Primary button | One per surface region at most. Enter and Space activate it. While its request is in flight it shows a pending label and ignores repeat activation. Disabled buttons stay focusable only when a reason is shown next to them `[ASSUMPTION]`. |
| Secondary button | Same keyboard behavior. Used for every banner action ("Add photos", "Start over", "Try again"), Submit on the Code field, the top-bar controls and three toggles: "Show all objects" (pressed state, announced as pressed or not pressed), the Triggers toggle and "Show the build JSON" (expanded state, announced as expanded or collapsed); each toggle shows its state with the pressed look in `DESIGN.md` `[ASSUMPTION: top-bar controls use Secondary button]`. |
| Focus ring | Drawn by `{components.focus-ring}` on every focusable element, Hotspots and graph nodes included. Shown for keyboard focus (`:focus-visible`). Never suppressed. |
| Mode indicator | Plain text in the top bar on every surface, built from `GET /meta` (AD-15) plus, in Local mode, the number of Room results in the local Player profile ("1 room played"), so the finals mode, the active profile and the play history behind any Greeting are declared on screen (NFR-12). Not focusable, not a control, not a Disclosure. Shows "Cache off" during the Capture proof. The count changes as soon as a Room result is recorded, so the Completion screen already shows the new count ("1 room played" after room 1); a fresh profile reads "0 rooms played". The Cache clear itself happens outside the app (a command Luis runs on camera); the app has no Cache-clear control and no demo-only path `[ASSUMPTION]`. |
| Status strip | Plain; takes no focus. Reconnecting: at the top of the Scene column on the Play screen, or at the top of the left area on the Capture screen, written once to the live region. Server unreachable: centered, alone. |

### Capture screen

| Component | Behavioral rules |
|---|---|
| Capture dropzone | Accepts drag-and-drop or the "Choose photos" picker. Validation is client-side and all-or-nothing: if any file is not a JPEG (checked by its bytes, not just its extension `[ASSUMPTION]`), or the count is under 6 or over 10, the whole set is rejected, nothing is uploaded, and the offending files are marked (FR-1). A valid set enables Upload. Upload produces the downscaled JPEGs (AD-7) and posts one multipart `POST /builds`. An upload that fails for any reason other than the 422 shows the upload-failed banner; "Try again" re-sends the same set and nothing else changes. Disabled while a Build runs. |
| Photo tray | Shows the chosen photos in upload order with a count line. Before Upload the player can remove any photo, including a file marked "Not a JPEG" `[ASSUMPTION]`; each removal re-validates the whole set, so removing the offending files (or adding valid ones) clears the FR-1 banner and enables Upload. Stays visible in every end state (PRD §8). Each remove control is a button named "Remove photo {n}". After `needs_more_photos`, "Add photos" reopens the picker and appends up to 10 in all. The next Upload is a new Build. |
| Mask preview | Appears once the segment stage completes and job status carries the solution-free mask preview (AD-3, AD-7). The client draws each Interactable's outline over its own downscaled copy of the clearest photo `[ASSUMPTION]`, with the Interactable's label on a parchment chip. Tiles are not interactive. The preview has no heading or line of its own: the Architect's line naming the objects belongs to the "Finding objects" row and moves on when "Writing puzzles" starts. |
| Timer | Starts on the Upload click (T0). Counts up in m:ss under the label "Photos to play"; once frozen at T1 the label reads "Playable in", so the frozen digits say what they measured. Stays in the same top-bar position from the Capture screen into the Play screen. Stops at T1 (the first Hotspot that responds to the pointer on the Play screen, exactly as the PRD Glossary defines it; keyboard focus does not stop it, see Open Items) and then shows the frozen T1 − T0 for the rest of the Session. On `failed`, `needs_more_photos` or `needs_recapture` it stops and shows the end status. The Demo timescale never scales it. It keeps running, undimmed, under the First-room welcome or Greeting overlay, because scrims start below the top bar. Hidden when replaying a stored Room or a Demo room. After a reload during a Build, it resumes from the Build's recorded start `[ASSUMPTION]`. In Hosted mode, while the Build is `queued`, the word "queued" replaces the digits (the clock still runs from T0); once the Build runs, the digits return and, after T1, the note "includes m:ss in the queue" follows them, the queue time measured by the client from T0 to the first non-queued poll `[ASSUMPTION]`. While reconnecting, it keeps counting from T0. |
| Stage list | Introduces the Architect and the Riddler in place, in both modes (PRD §7). The Architect's row at the top appears at Upload with its portrait, name, role line and voice line, and signs the list. Under it, one row per A-11 stage name, in order: pending → running → done (with duration) or failed. The running row shows the Architect's line for that stage; as each stage starts, the line moves to the new row. When "Writing puzzles" starts, the Riddler's introduction (portrait, name, role line, voice line) appears in that row and stays for the rest of the Build. Each done row shows its plain result and the model behind it (Voice and Tone, Done-row results), so the Capture screen shows outcomes even under cut 0; "Testing the room" shows its two checks (the rules, then the test run) as two lines once done. A Regeneration adds "Rewriting puzzles, attempt n of {max}" ({max} = `REGEN_MAX`) with "Sent back: …" naming the failed attempt's fixed messages, and re-runs the author, validate and dry-run rows. In Hosted mode the two plain Hosted lines (the build's own link, where the two-minute target is measured) sit under the list from Upload on. The introductions are static once shown, not interactive and not announced (the Stage list is not a live region); each carries the visually hidden speaker prefix. |
| Retention summary | Renders `GET /meta` `retention` as served, then the Privacy line. Always fully expanded and visible before any photo is chosen. Never collapsed or truncated (FR-6). |
| Error banner | Appears at the top of the left area, above the photos it refers to. One banner at a time; a newer state replaces an older one. Holds the plain heading, one sentence and its actions. Gets focus when it appears, so its text is read out and Tab reaches its actions next `[ASSUMPTION]`. The FR-1 refusal offers "Choose photos again", which reopens the picker and replaces the whole set. The warning variant (`{components.warning-banner}`) is used for Spend cap (no retry action, because a retry cannot succeed until the cap is raised), `queued` and Build quota. The session-start-refused banner (a failed `POST /sessions`) offers "Try again", which re-posts the session start. |
| Stored Room row (Local) | One row per stored Room (`RoomSummary`, AD-9), newest build first `[ASSUMPTION]`: "Play" starts a new Session (no Timer; a refused start shows the session-start-refused banner at the top of the left area); "How this room was built" opens the Build view for the summary's job id. The list says "No rooms yet." when empty. |

### Play screen

| Component | Behavioral rules |
|---|---|
| Scene frame | Shows one photo from `GET /rooms/<room_id>/photos/<i>`, contained and never cropped, never enhanced. While loading, the frame shows a plain loading line. While reconnecting, the status strip takes 32 px at the top of the Scene column and the frame shrinks to fit, so no Hotspot is covered; the photo dims and every input disables (FR-11). |
| Hotspot | One per Interactable on that photo: the union of its polygons, with the Hotspot id equal to the Interactable id (AD-11). Invisible at rest. Hover or focus reveals it (plus the label chip on focus). Click or Enter posts `click` (unless a `use_on` item is selected, in which case it posts only the `use_on` lock input, AD-4; see Interaction Primitives). Tab order runs top to bottom, then left to right, by polygon centroid `[ASSUMPTION]`. Accessible name: the Interactable label, with the role of a button. When a `find` Puzzle is solved, its target's Hotspot stays in the Scene (the photo cannot change) but is no longer a target: its hover glow fades out over 200 ms in step with the Inventory item fading in, so the object reads as moving into the hand without anything sliding (FR-12); clicking it again shows "{label} · in hand" on the label chip `[ASSUMPTION]`. |
| Hotspot label chip | Shows the Interactable label on keyboard focus and stays for as long as the Hotspot has focus (WCAG 1.4.13). After a click on a Hotspot that is not a target (FR-12), it shows and fades after 2 s or when the pointer leaves. Never shows on hover alone, so hover stays a reveal and not a giveaway `[ASSUMPTION]`. |
| Thumbnail strip | One thumbnail per photo, in upload order (A-12). Click or Enter switches the Scene. The current photo is marked and announced as current. Stays usable while a `use_on` item is selected. |
| Inventory | Holds Interactables collected by solved `find` Puzzles for the whole Session (FR-11). A new item fades in over 200 ms, paired with its Hotspot's glow fading out (see Hotspot), with no flight animation. An item is a drag source for `use_on`. Click or Enter selects it for select-then-click, and a second activation or Escape deselects it. Shows the empty-state line when empty. |
| Wizard notes | One entry per available Puzzle, in availability order, each headed "Puzzle {n}" with its plain evidence count at the end of the heading row. The count is the number of Evidence cards in that entry; it changes in place when an accepted Decoy adds a card, with no highlight, badge, animation or announcement, so the Trickster's edit is visible without pointing at the new card (FR-11, FR-19). Each entry has its Clue (Riddler), the Evidence cards directly under the Clue, Lore, opened Rungs, its lock input (Code field, or Order click progress with its "Start the sequence" control; `find` and `use_on` happen in the Scene) and, in Tier 1.5, the Clue card slot. The Active puzzle's entry carries the `{components.active-puzzle-marker}` (a left rule plus the word "Current", never color alone); "Current" follows `active_puzzle_id` from session state, which is never null while a Puzzle is available: it is the last Puzzle targeted by a lock input or a named Hint request, else the earliest available unsolved Puzzle, and it moves on its own when its Puzzle opens or a Merge hides it (AD-4). Puzzles with unmet prerequisites are not drawn. A newly available entry fades in. An open entry collapses to one line with the Open chip. An accepted Merge hides the entry it now gates (fade out) and leaves the plain placeholder "Puzzle {n} now waits on another puzzle." in its place until the gating Puzzle opens; if focus was inside the hidden entry, focus moves to that placeholder. An accepted Shortcut reveals the entry only when the Puzzle has no other unmet prerequisite. Scrolls on its own, inside the side column, never shorter than `{spacing.notes-min}`. |
| Clue card slot (Tier 1.5) | Drawn only when the Room has Clue cards (FR-37); otherwise the entry has no slot at all. Sits beside the Clue (FR-37), at `{components.clue-card-slot}` size. Placeholder until ready, blank on failure; the size never changes, so the layout never shifts. Alt text: when the image is shown, its alt is the Clue (FR-37) and the visible Clue text beside it is hidden from assistive technology, so the Clue is read once; while the slot is a placeholder or blank, the slot is hidden from assistive technology and the visible Clue is read `[ASSUMPTION for the no-double-readout method]`. |
| Wizard portrait | Decorative next to text that names the speaker (alt is empty). Every in-character line carries a visually hidden speaker prefix for screen readers: "The Architect:", "The Riddler:", "The Guide:" or "The Trickster:" `[ASSUMPTION]`. The Guide's portrait shows the thinking state (static lamp ring plus "thinking on this Mac", no animation) only while something is known to be in flight in Local mode: a Hint request awaiting its reply, or a Greeting while `phrasing` is true. A Rung that arrives through the poll unrequested appears directly, with no thinking state before it, because nothing signals that it is being phrased; instead, the Guide portrait ring and the Hint area show one lamplight arrival glow, 300 ms in all (under reduced motion, the lit ring held 2 s with no animation). Falls back to the placeholder art when the image is missing (FR-23). |
| Hint area | Holds the latest Rung line or No-hint line, at most two stacked Cards (newest on top; older ones behind a "{n} more in the Card log" link that opens the Card log; only the newest while the Triggers panel is open) and the hint controls. Cards are read from `cards` in session state, the `TricksterCard` projection (AD-3), so the UI never holds an edit payload. Grows upward to `{spacing.hint-area-max}`, then its upper part scrolls inside itself, so the Wizard notes keep their minimum height; while the Triggers panel is open it may grow until the Wizard notes reach `{spacing.notes-min}`. The hint field, "Ask the Guide", the helper line and the Triggers toggle stay pinned outside the scroll. Its in-character lines are the ones the live region announces. After "Begin", it holds the Greeting or First-room welcome as its first Guide line until the first Rung replaces it (not announced again). |
| Rung line | **The one home for Hint replies.** Shows one Rung or the No-hint line, labelled with its Puzzle ("Puzzle {n} · Direction"). A new Rung replaces the previous Rung line, and the replaced Rung stays in its Puzzle's notes entry under "opened Rungs". **Every reply to a Hint request visibly arrives:** if the reply is the Rung already shown, the Rung line fades out and in again (200 ms each way, instant under reduced motion) and is announced again. In Local mode the Guide model may re-phrase a repeat so it does not read as a wall, rewording only; in Hosted mode and under any fallback the repeat is the same verbatim text. After the near-answer, a further Hint request repeats the near-answer; there is no reveal or skip (A-21). |
| Hint field + Ask the Guide | **The one home for Hint requests.** Enter in the field, or the button, sends one Hint request with `puzzle_id` always omitted; the server resolves it to `active_puzzle_id`, which is never null while a Puzzle is available, so the reply matches the entry marked "Current" (AD-4). The field's accessible label names the Puzzle ("Ask the Guide for a hint on Puzzle {n}"). The typed text never leaves the browser; only the Hint request is sent (FR-14). While sending, the typed text stays visible in the read-only field and the button says "Asking", so the player sees that the words stayed here; when the reply lands, the field clears `[ASSUMPTION]`. A permanent plain helper line under the field says the words stay here ("Your words stay in this browser. The Guide only hears that you asked."). An empty field still sends. One request in flight at a time. The reply is handled by the Rung line. |
| Triggers panel | Collapsed by default behind the always-visible toggle. Opens automatically when the page loads with a Disclosure active, and the player can still collapse it `[ASSUMPTION]`. A header line states when help comes: the nudge threshold and the Rung spacing in effect, their 1× values at a Demo timescale, and where the threshold came from (the last play-through, kept in this browser, or the first-room default). Rows appear as `rung_change` events arrive, newest last, each naming its Puzzle, Rung, cause and where it was worded ("worded on this Mac · {latency}" or "as written"). Capped at `{spacing.triggers-panel-max}` and scrolls inside, newest row kept in view and set apart from older rows. Open with no rows, it shows the header and "No hint changes yet.". Under cut 5 it opens in a second window instead, with the same content. |
| Code field | Accepts up to 6 characters. No visible label or placeholder; its accessible name is "Code for Puzzle {n}". Submit is disabled below 3 `[ASSUMPTION]`. Enter or Submit posts the code lock input (AD-4); the lock shows open only on the server's confirmation (FR-12). While pending, the field is read-only and the Pending chip shows. A wrong code shows "Not this · n", keeps the field value and selects it for retyping. Open shows the Open chip and removes the field. The server compares the input trimmed and case-folded (A-20). |
| Order click progress | **The one home for the order sequence rules.** For each available `order` Puzzle: a "Start the sequence" control and one pip per position, with a visually hidden description "{filled} of {length}". The sequence is armed only by that control, which posts the order start lock input naming the Puzzle (AD-4); the control then reads "Stop the sequence". **Unarmed**, the pips stay empty and never flash, and Hotspot clicks are exploration that never count. **Armed**, every Hotspot click fills the next pip whichever object it hits, so progress reveals nothing about which objects belong; a pip fills when the server acknowledges the click into the buffer, never optimistically, so the pips always match the buffer being judged. At full length a match opens the lock; a mismatch is one Wrong attempt: the pips turn `{colors.wrong-ink}` for 300 ms, then empty, "Not this · n" shows, and the sequence stays armed. "Stop the sequence" posts the order stop lock input: the pips empty and no Wrong attempt is counted. **The sequence is armed only while its Puzzle is the Active puzzle** (AD-4): "Start the sequence" is a lock input, so it makes its Puzzle Current and arms it; when another Puzzle becomes Active (a lock input on another Puzzle, among them "Start the sequence" on another order Puzzle, a Hint request naming another available Puzzle, a Merge hiding this Puzzle, or this Puzzle opening), the sequence is disarmed with no Wrong attempt: the pips reset to empty with no wrong flash and no "Not this", the control returns to "Start the sequence", and the player re-arms with it; the client renders the armed Puzzle from session state and never decides the disarm itself. The armed state survives Scene switches and reloads (it is session state). |
| `use_on` drag | Drag an Inventory item over the Scene. The Hotspot under the pointer shows its hover state. Dropping on a Hotspot posts `lock_input` with UseOnInput {item, target} and no `puzzle_id`; the server resolves the Puzzle from the pair (AD-4). Dropping anywhere else cancels and posts nothing. Until the verdict, the target's label chip shows with the "Checking" chip beside it; the verdict ("Not this · n" or "Open") then shows in the resolved Puzzle's entry, which becomes the Active puzzle while it stays unsolved (AD-4). A pair that resolves to no Puzzle counts nothing and only clears the Checking chip. |
| `use_on` select-then-click | Selecting an item pins the "Using {item}" chip with Cancel. The next Hotspot click or Enter posts the same UseOnInput as a drop and no `click`, exactly like a drop (AD-4, AD-11), then clears the selection; feedback is the same as for a drop. Switching thumbnails keeps the selection. Escape or Cancel clears it. |
| Feedback chips | "Checking" from submit until the server's verdict. "Not this · n" until the next input on that lock. "Open" held for 1200 ms `[ASSUMPTION]`, then the entry collapses and the next Puzzle appears. The chip text is the lock input's accessible description `[ASSUMPTION]`. "Not this · n" and "Open" are also written to the polite live region (see Accessibility Floor). |
| Evidence card | Static, directly under its Clue. Shows the Interactable label, thumbnail crop and the read attribute as a description of where to look ("a year printed on the side", "gold lettering on a few spines"), never a solution token: validator rule 5 checks `evidence.visible_attribute` and the Clue like the nudge and direction, so a stored Room never carries a displayed attribute with a solution token (Schema v1, AD-3). Real and Decoy cards behave identically and keep the stable order `PlayView` gives them. A new card gets no highlight and no announcement (FR-11, FR-19). |
| Trickster card, accepted | Read from `cards` in session state, the `TricksterCard` projection (ids, type, outcome, reason and fixed message), so the UI never holds an edit payload (AD-3). Enters after the lock-open state. Stays until dismissed (Dismiss control, accessible name "Dismiss card"); on dismiss, focus moves to the next Card in the Hint area, else to the hint field `[ASSUMPTION]`. Copied into the Card log. Announced once in the live region. Every Card names the Validator and its Puzzle (the Card's `puzzle_id`) in the label ("Validator passed · Merge · Puzzle 3"), so a Merge that hides an entry still points at it and a Decoy points at the entry whose evidence count rose, never at the card. **The first Card of the Session**, whatever its outcome, introduces the Trickster in place (PRD §7): "The Trickster" with its role line under the name, then its voice line before the Card's sentence. The introduction appears once per Session, is never repeated on later Cards or in the Card log, and is not re-shown after a reload that replays the first Card. |
| Trickster card, rejected | Same as accepted, including the first-Card introduction. Shown only for a Validator failure on a proposal (AD-12, AD-13). Under the label, two plain lines: the structural "Proposed: …" summary (type and Puzzle numbers only, from the Card's `edit_type`, `puzzle_id` and `related_puzzle_id`) and the Validator's reason, framed "That change was refused. {fixed message}" (the Card's `message`), so the refusal reads as a real proposal stopped by a rule, not as staged. The Effective room is unchanged. |
| Trickster card, skipped | Same as accepted, including the first-Card introduction. Play continues. Shown for `reason: provider_unavailable` (AD-4): a Trickster call error (`ProviderError` or `SpendCapExceeded`) is always a skipped Card, never a rejected one (AD-13), which covers both causes FR-19 and FR-28 name. No Card at all once the Session's seventh call would be needed (FR-19). |
| Card log | A modal dialog: opens from the top-bar button, or from the Hint area's "{n} more in the Card log" link. While open, the scrim covers the body below the top bar, focus is trapped in the dialog (first on its close control), and the Scene, Hotspots and top bar are inert. Built from `cards` in session state (AD-3), it lists every Card this play-through, oldest first, with its session time; each row leads with the Trickster's sentence in `{typography.wizard-line}`, then the same label as the Card, and on a rejected Card the "Proposed: …" line and reason. Escape or the close control closes it and focus returns to the control that opened it. Dismissing a Card in the Hint area never removes it from the Card log. |

### Completion, Greeting, Build view

| Component | Behavioral rules |
|---|---|
| Completion screen | Appears automatically after the Exit puzzle's open state. Reads `GET /sessions/<id>/result` and `web/profile` records the Room result (demo-flagged when the Demo timescale > 1, FR-22). Focus goes to the heading. The Guide's sign-off line is chosen from the stats only and written to the live region once. "Build another room" goes to the Capture screen (Local) or the Hosted landing (Hosted). Under cut 2, "Save profile file" downloads the profile. "How this room was built" opens the Build view. Active Disclosures stay in the banner, which the scrim never dims. The top bar keeps "Show all objects", "Card log" and "Leave room" in place, inert, and the Timer frozen at T1 − T0. On a Judge room, shows "Deleted Tue Nov 10" in a plain strip below the sheet, off the parchment. A reload of `#/done/<session_id>` shows it again and does not record the result twice `[ASSUMPTION]`. |
| Greeting / First-room welcome | Shown over the first Scene after the Session starts and before play. It also introduces the Guide in place (PRD §7): the heading "The Guide", the role line under it, and the Guide's voice line under the opening line. The line comes from the `POST /sessions` response, `opening_line {kind: greeting | welcome, text}` with the `phrasing` flag (AD-4, AD-5): the server picks the kind from the Derived block sent (Greeting when `sessions` ≥ 1 in Local mode; First-room welcome otherwise, and always in Hosted mode, which never phrases) and, for a welcome, its text (the Demo room variant on a Demo room). Focus is trapped and placed on "Begin". While a Local Greeting is being phrased there is no "Begin" yet: focus sits on the card's heading and moves to "Begin" when the line arrives `[ASSUMPTION]`. "Begin" is the only way to dismiss it (FR-21). The heading, the opening line and the voice line are written to the live region once, as "The Guide. {role line} {opening line} {voice line}" (NFR-14); the dialog is labelled by its heading only and does not also use the line as its description, so nothing is read twice. Not shown again on reload once play has events `[ASSUMPTION]`. In Local mode, while `phrasing` is true (`text` is null), the card shows the Guide's thinking state; the client polls `GET /sessions/<id>` every 2000 ms and shows the line once `opening_line.text` arrives, phrased or, after the 5 s fallback, the template. After "Begin", the opening line stays as the first Guide line in the Hint area, not announced again. The First-room welcome shows its one-time plain tip under the card. |
| Leave room confirmation | A plain card on `chrome-raised` (`{components.leave-room-confirmation}`), never parchment, because its copy is a plain message. Opened by "Leave room" or the browser Back button on the Play screen. Focus is trapped and placed on "Keep playing". Escape means "Keep playing"; on "Keep playing" focus returns to the control that opened it ("Leave room"), or to the Scene's first Hotspot after the Back button `[ASSUMPTION]`. Confirming records no Room result (§8) and goes to the Capture screen (Local) or the Hosted landing (Hosted). |
| Deleted Judge room notice | Replaces the Play or Completion screen for a Judge room URL opened after Tue Nov 10, when a room-keyed route answers 410 `room_deleted`. The server keeps an ids-only deletion record for each purged Judge room, so a deleted room is told apart from an unknown one, which answers 404 `room_not_found` (AD-9, AD-13) and shows the unknown-room copy in the same card. Focus on the heading. "Go to the demo rooms" opens the Hosted landing. |
| Build view: header | Shows the Room's name as its title when it has one (AD-2, AD-7), else the build time; "Regenerations: n of {max}" ({max} = the Build's `REGEN_MAX`, AD-3); after a Regeneration, one "Attempt {k} sent back: {fixed messages}" line per failed attempt, so the verification shows what it caught; and "Back". The Disclosure banner sits above it, from `BuildView`'s per-Room list (AD-15). Not ready and error states replace the panels below it (see State Patterns). |
| Build view: mask overlays | Static per-photo grid, drawn from `BuildView`'s mask polygons with each Interactable's label (AD-3). Each label chip is focusable and carries the Interactable label `[ASSUMPTION]`. |
| Build view: puzzle graph | Each node is focusable and Tab moves through nodes in Puzzle order. Accessible name: "Puzzle {n}, {lock type}, requires {list or none}, Dry run {pass, fail or skipped}", plus "Exit" on the Exit puzzle `[ASSUMPTION]`. Nodes are not interactive beyond focus. |
| Build view: Validator verdict table | One row per rule (AD-3), under its plain caption. A pass row shows the rule's check-phrased name and the word "pass"; a fail row shows the word "fail" and the rule's fixed message. Verdicts are words. |
| Build view: Dry run row | One row per Puzzle, under its plain caption, which says the test run never saw the answers. Under cut 4 every row says "skipped" (FR-38, AD-3), and the cut 4 caption replaces the usual one, which would no longer be true. |
| Build view: Model table | First in the right column, so it is above the fold at 900 px. One row per role and model (AD-3, AD-16) with a "what it did" column built from provenance counts ("found 9 objects", "outlined 9 objects", "wrote 5 puzzles", "tried 5 puzzles blind", "proposed 2 changes") (FR-38), plus three fixed rows: the Validator ("code, no model", "checked 8 rules"), the Dry run (its model and host from the call rows) and Muse Image ("muse-image-1.0", "painted the four portraits, once", FR-23). Each wizard row leads with the wizard's portrait and name; the Architect and Riddler rows carry their role lines, introducing them on the Hosted landing's path `[ASSUMPTION, for the builder]`. "cached" or "billed" spelled out; a role with both shows both counts, for example "3 billed · 9 cached" (FR-27, FR-30) `[ASSUMPTION for the grouping]`; the caption under the table says what cached means. It lists Build-time calls only, so it has no Guide or Trickster row; the In play block carries both. The Validator's cached-or-billed cell stays empty, because it makes no call. Under cut 4 the fixed Dry run row stays and reads "skipped", with no model or host. |
| Build view: In play block | Fixed, from `GET /meta` (AD-15), not from the Build's provenance: the Guide row (portrait, name, role line, then the Guide model and host: in Local mode Llama 3.2 3B on Ollama on the Mac; in Hosted mode the plain line "Hints are shown as written here. In Local mode, Llama 3.2 3B rewords them on the Mac." `[ASSUMPTION]`), and the Trickster row (portrait, name, role line, then the source: live, scripted or cut 1). Static. |
| Build view: BuildView JSON | Collapsed by default behind "Show the build JSON". Opening it shows its plain caption, then the build data exactly as served, which is solution-free by construction and checked by the sentinel test (AD-3, FR-38). Keyboard: the toggle is a button with an expanded state; the JSON pane is a focusable, scrollable region. No answer, Clue-to-answer pairing or Dry run answer is shown or fetched anywhere on the Build view, and Clues are not repeated here `[ASSUMPTION]`. |

### Modes, disclosure, platform

| Component | Behavioral rules |
|---|---|
| Disclosure banner | One line per applicable Disclosure, rendered as served: on the Play and Completion screens from the session state's per-Room `disclosure` list, on the Build view from `BuildView`'s `disclosure` list, and on the Capture screen and Hosted landing from `GET /meta` `disclosure` (the global lines; AD-15). Cannot be dismissed. Takes no focus and contains no controls. Read as page content at the top of each surface, the Build view included. No scrim ever covers or dims it. See Demo Mode and Disclosure. |
| Hosted landing | Shows the Demo room cards and the Access-code build side by side (UJ-5), with no separate band of wizards (Voice and Tone, Wizard introductions). The title block carries the subtitle, the plain pipeline line naming the models and the test run, and the lead-in "Short on time? See how a room is built and checked." with the "How a room is built" link, which opens the first Demo room's Build view, so a judge can lead with the work in about a minute (PRD §7 "Lead with the work"). The cards come from `GET /rooms`, which in Hosted mode returns Demo rooms only, never Judge rooms (AD-9). |
| Demo room card | One per `RoomSummary`: the Room's name (`Room.name`, set when the Demo room is seeded; the build time when absent), cover photo, Puzzle count, and the four Wizard portraits (decorative, with one accessible name for the row). Click or Enter on the card starts a Session on that Demo room with a fresh Derived block, then the First-room welcome (Demo room variant); a refused start shows the session-start-refused banner at the top of the landing's left area. Its separate "How this room was built" link opens that Demo room's Build view (open in both modes, AD-3; seeding writes a job record for each Demo room, AD-7), with "Back" returning to the landing. The mask-and-graph thumbnail is decorative. |
| Access-code build | The code is checked before photo selection (FR-32) with `POST /access/check {code}`, which returns `{ok, builds_left}` without starting a Build and is rate-limited (AD-9). Submit gives checking → accepted (status line "{n} of 20 builds left" from `builds_left`, then the Capture screen with the code held for `POST /builds` as `X-Access-Code`), refused (compact error, no upload), too many tries (compact warning with the rate-limit line) or quota reached (`builds_left` is 0: warning; Demo room cards stay active). `POST /builds` re-checks the code and the quota, so a quota reached between the check and the upload shows the Build quota warning on the Capture screen. The code is kept for the tab's lifetime only and never written to storage `[ASSUMPTION]`. |
| Narrow-screen message | Replaces the whole app below 1024 px. Above 1024 px the app returns with its state intact (nothing is torn down in between `[ASSUMPTION]`). |
| Server unreachable (cold load) | Replaces the surface while `GET /meta` fails, retrying every 2000 ms; no Disclosure, Retention summary or Scene is guessed (see Capture cold load). |

## State Patterns

### Capture screen

| State | Treatment |
|---|---|
| Cold load | Waits for `GET /meta` (Disclosure, Retention summary), then shows the before-upload layout: Input requirement, iPhone tip, reminder, dropzone, Retention summary with the Privacy line. Stored Rooms below (Local). If `GET /meta` fails, a plain "Keyframe can't reach its server. Retrying." replaces the screen and retries every 2000 ms, because the Disclosure and Retention summary must not be guessed `[ASSUMPTION]`. |
| Empty | Dropzone at rest; Upload disabled; stored Rooms list says "No rooms yet." (Local) `[ASSUMPTION]`. |
| Photos chosen | Photo tray with count; Upload enabled. |
| Refused (picker) | Error banner "Keyframe needs 6 to 10 JPEG photos." with "Choose photos again"; offending files marked and removable from the tray; each removal or addition re-validates the set, and a valid set clears the banner and enables Upload; nothing sent until then. |
| Pending (uploading) | Upload shows its pending label; the Timer is running from T0; the dropzone is disabled. |
| Upload failed | `POST /builds` fails for any reason other than the 422 (network, 5xx): the upload-failed error banner at the top of the left area, with "Try again" (same set); the photos stay; the Timer stops with its end status and restarts at the next Upload (a new T0); the banner takes focus `[ASSUMPTION]`. |
| Reconnecting (Build) | Two consecutive missed Build polls `[ASSUMPTION]`: the status strip at the top of the left area, above any banner, with the reconnecting-during-a-Build line; the Stage list and Mask preview stay as last seen; the Timer keeps counting from T0, because the Build keeps running on the server; recovery re-renders from job status and removes the strip. |
| Loading (Build) | Job status drives the screen. See Build job statuses below. |
| Success (`done`) | Every stage done, each with its result and model; the "How this room was built" link appears; `POST /sessions` starts and the Play screen opens when the first Scene is ready. |
| Session start refused | `POST /sessions` fails after `done` (or after a stored Room's "Play"): the session-start-refused error banner at the top of the left area, with "Try again"; the banner takes focus; the Timer keeps running toward T1 `[ASSUMPTION]`. |
| Error | Error or warning banner per status; photos stay visible; the Timer is stopped with its end status. |
| Disabled | Everything except the Retention summary and banners is disabled during a Build. Under the Narrow-screen message nothing is shown. |
| Focus | Initial focus on "Choose photos" `[ASSUMPTION]`. A new banner takes focus; the status strip never does. On `done`, focus moves with the screen to the Play screen. |

### Build job statuses (`GET /builds/<job_id>`, polled every 2000 ms `[ASSUMPTION: same cadence as sessions]`)

| Status | Stage list | Banner | Timer | Actions |
|---|---|---|---|---|
| `queued` (Hosted) | All pending | Warning: "Another room is being built. Yours is in line and will start on its own." | Running, shown as "queued" | none |
| `running` + `stage` | That stage running, earlier ones done with durations; the Mask preview once the segment stage has completed (AD-3, AD-7); Regeneration rows when the attempt count rises | none | Running | none |
| `done` | All done, with results and models | none | Running until T1 on the Play screen | Build view link; automatic Play |
| `failed` + `stage` | That stage failed | Error: "The build stopped while {stage label, lowercased}." plus the cause class (and, in Hosted mode, that a retry uses a judge build). For `spend_cap_exceeded`, the warning variant with the Spend cap string and its consequence line | Stopped, end status | "Try again"; for `spend_cap_exceeded`, "Start over" only |
| `needs_more_photos` | Stopped at "Finding objects" | Error (FR-4 copy; the 10-photo body when the set is full) | Stopped, end status | "Add photos" (not with 10 photos), "Start over" |
| `needs_recapture` | Stopped at "Testing the room" after the last attempt | Error (FR-10 copy) | Stopped, end status | "Start over" |

The UI keys on job status (AD-13): `needs_more_photos` asks for more photos and `needs_recapture` asks for a re-capture; there is no error class for exhausted Regenerations. Envelope codes map onto these states: `too_few_interactables` → `needs_more_photos`; `spend_cap_exceeded` → Spend cap; `provider_error` → "A model service didn't answer."; `unsupported_image` → the FR-1 banner; `build_quota_exceeded` → quota warning; on room-keyed routes, `room_deleted` → the Deleted Judge room notice and `room_not_found` → the unknown-room card (AD-9). Opening `#/build/<job_id>` on a Build that is already `done` shows the done state with "Play this room" and the Build view link instead of auto-starting `[ASSUMPTION]`.

### Greeting / First-room welcome

| State | Treatment |
|---|---|
| Loading | Local Greeting only: while `phrasing` is true and `opening_line.text` is null (AD-4, AD-5), the card shows the Guide's introduction, its voice line and the static thinking state, for up to 5 s plus one poll. No "Begin" yet; focus sits on the card's heading. A welcome, and every Hosted session, arrives with its text in the `POST /sessions` response and skips this state. |
| Success | Line shown; "Begin" focused; the introduction and the line announced once through the live region. |
| Fallback | Phrasing over 5 s or unreachable: the template line appears in the same card, silently. |
| Focus | Trapped on the card; "Begin" is the only control. |
| After "Begin" | The line stays as the first Guide line in the Hint area, not announced again. |

### Play screen

| State | Treatment |
|---|---|
| Cold load | `GET /sessions/<id>` (state with `active_puzzle_id`, `cards`, `opening_line`, `phrasing` and the per-Room `disclosure` list) and `GET /sessions/<id>/room`. The Scene frame shows its loading line until the first photo is drawn and its Hotspots are live. |
| Reload | Resumes from the Event log: same Scene index (the first Scene `[ASSUMPTION]`), Inventory, open locks, current Rungs, Cards (from `cards` in session state, all in the Card log, none re-stacked in the Hint area `[ASSUMPTION]`) and the frozen Timer if it was set. No Greeting if play has events. |
| Empty | Inventory empty line; Card log empty line; Hint area with no Rung line (controls only). |
| Pending | Per lock: the "Checking" chip until the server's verdict; Hint request: "Asking", the typed text held read-only, plus the Guide thinking state (Local). |
| Polling | `GET /sessions/<id>` every 2000 ms while the Play screen is open (AD-4); this read also drives idle ticks. New `rung_change` gives a Rung line (with no thinking state before it) plus a Triggers row plus an announcement, and, because nobody asked for it, one arrival glow on the Guide portrait ring and the Hint area (300 ms in all; static lit ring under reduced motion) so a player looking at the Scene notices the Guide speaking up. A new entry in `cards` gives a Card plus an announcement. A changed `room_revision` triggers a refetch of `GET /sessions/<id>/room` and a re-render of the Wizard notes. Polling continues while the tab is hidden `[ASSUMPTION]`. |
| Hint reply | As in Component Patterns (Rung line); the field clears as it lands. No arrival glow, because the player asked. |
| Ollama timeout fallback | After 5 s the verbatim Rung replaces the thinking state. No message on the Rung line; its Triggers row says "as written". Unreachable Ollama gives the verbatim Rung at once (FR-17). |
| Triggers panel open, no rows | The header line (threshold, spacing, source) and "No hint changes yet." |
| Success (lock open) | "Open" chip for 1200 ms, then the entry collapses, the next Puzzle fades in, a solved `find` target's Hotspot glow fades out while its item fades into the Inventory (both 200 ms), and then any Card. |
| Merge hides the entry in use | The hidden entry is replaced by its plain placeholder line; focus inside it moves to the placeholder; the Card names the Puzzle. |
| Wrong attempt | "Not this · n"; no shake, no sound; the Rung may advance on a later poll (FR-15). |
| Skipped card | Shown like any Card; play never pauses. |
| Refused | An input for a Puzzle whose prerequisites are not open, or a `use_on` with an item not held, is not a Wrong attempt; it shows nothing beyond clearing its Pending chip `[ASSUMPTION]`. |
| Error (reconnecting) | When a request fails or the poll misses `[ASSUMPTION: two consecutive misses]`: the Scene dims, every input is disabled, and the reconnecting line shows in the status strip at the top of the Scene column; the Scene frame shrinks by the strip's height, so the strip never covers a Hotspot. An input that never reached the server is dropped; the Code field keeps its value. Recovery re-renders from server state and removes the strip. |
| Error (Session gone) | Hosted log expired: the play-through-ended state, the photo dimmed under the plain Session-gone line with "Start again". A deleted Judge room (`room_deleted`) shows the Deleted Judge room notice instead; an unknown room (`room_not_found`) shows the unknown-room card (AD-9). |
| Disabled | During reconnecting; Hotspots and the top bar are inert under the Greeting, Card log and Leave room overlays. |
| Focus | After the Greeting, focus goes to the first Hotspot of the first Scene `[ASSUMPTION]`. After a lock opens, focus moves to the next Puzzle's entry heading `[ASSUMPTION]`. After a Card is dismissed, focus moves to the next Card, else the hint field `[ASSUMPTION]`. After "Keep playing", focus returns to "Leave room" (or the first Hotspot after the Back button) `[ASSUMPTION]`. After the Card log closes, focus returns to the control that opened it. |

### Completion screen

| State | Treatment |
|---|---|
| Loading | Sheet shown with stats pending until `GET /sessions/<id>/result` returns. |
| Success | Stats, actions, Disclosures; the Room result is written once. |
| Error | Plain "Keyframe couldn't load the result. Retrying." and a retry every 2000 ms; "Build another room" stays available `[ASSUMPTION]`. |

### Build view

| State | Treatment |
|---|---|
| Cold load | Disclosure banner (when one applies) and header with "Back", then panels fill from `GET /builds/<job_id>/view`; the In play block fills from `GET /meta`. |
| Not ready | Build not `done`: the header, then "This room is still being built." with a link to its Capture screen, and no panels `[ASSUMPTION]`. |
| Error | Plain "Keyframe couldn't load how this room was built." with "Try again" `[ASSUMPTION]`. |
| Focus | Initial focus on the header title `[ASSUMPTION]`. |
| Scrolled | The right column runs past 900 px, so the page scrolls; the Disclosure banner and the top bar stay pinned and only the body scrolls. |
| Cut 0 | The surface and every link to it are absent; the Stage list's done results and the role lines still show what each model did. |

### Hosted landing

| State | Treatment |
|---|---|
| Cold load | `GET /meta` (Disclosure with the Hosted line), then the Demo room cards from `GET /rooms` (Demo rooms only, AD-9). |
| Demo rooms failed to load | `GET /rooms` fails: in place of the cards, the plain "Keyframe couldn't load the demo rooms." with "Try again"; the title block and the Access-code build stay usable `[ASSUMPTION]`. |
| No Demo rooms | `GET /rooms` returns none: the plain no-demo-rooms line in place of the cards; the "How a room is built" link and its lead-in are hidden, because they open a Demo room's Build view `[ASSUMPTION]`. |
| Session start refused | A Demo room card's `POST /sessions` fails: the session-start-refused error banner at the top of the left area, with "Try again"; the banner takes focus. |
| Access code empty / checking / refused / too many tries / accepted / quota reached | As in Component Patterns. Refused uses the compact error banner inside the Access-code build; too many tries and quota use the compact warning banner. |
| Focus | Initial focus on the first Demo room card `[ASSUMPTION]`. |

## Interaction Primitives

- **Click** to act everywhere. A Hotspot click always posts `click` (AD-4), with one exception: the target click of a select-then-click, which posts only the `use_on` lock input. A click is never by itself a Wrong attempt; the only click-driven Wrong attempt is a full-length, non-matching armed order sequence (Component Patterns, Order click progress).
- **Hover** reveals a Hotspot (`{components.hotspot}` hover state, 150 ms). Hover is never the only path: Tab focus and "Show all objects" reveal the same Hotspots (NFR-14).
- **Keyboard.** Tab and Shift+Tab move in reading order: top bar → Scene Hotspots → Thumbnail strip → Inventory → Wizard notes → Hint area. Enter acts as a click on Hotspots, thumbnails, Inventory items, Demo room cards and graph nodes. Enter submits the Code field, the hint field and the Access code field. Escape closes the Card log, cancels a `use_on` selection, and means "Keep playing" on the Leave room confirmation. Escape never dismisses the Greeting. No single-key shortcuts in v1 `[ASSUMPTION]`.
- **Drag** (`use_on`): pointer drag from the Inventory onto a Hotspot. **Select-then-click** is the equivalent for keyboard and pointer: select the item, optionally switch Scenes, then click or Enter on a Hotspot. The two paths are identical to the server (AD-4, AD-11); Component Patterns (`use_on` drag, `use_on` select-then-click) holds their rules.
- **Active puzzle.** AD-4 defines it as the most recently targeted available unsolved Puzzle (targeted by a lock input, or by a Hint request naming a Puzzle), else the earliest available unsolved Puzzle; it moves on its own when its Puzzle opens (a `find` Puzzle opened by a click included) or a Merge hides it, it is null only once the Exit has opened, and clicks never set it (an exploration click leaves it unchanged). Session state exposes it as `active_puzzle_id`; the client reads it and never computes it, and always omits `puzzle_id` from a Hint request. The Wizard notes mark it ("Current"), the hint field's accessible label names it, and every Rung line names its Puzzle.
- **Order sequence, code submit, Hint request.** Each has one home in Component Patterns: Order click progress, Code field, and Hint field + Ask the Guide (the reply in Rung line). The order sequence is armed only while its Puzzle is the Active puzzle (AD-4): when another Puzzle becomes Active, the pips reset and the control returns to "Start the sequence"; the player re-arms with it.
- **Polling.** Session every 2000 ms (AD-4); Build every 2000 ms `[ASSUMPTION]`. The client never stamps time: `t_ms` comes from the API.
- **Refetch on `room_revision`.** When the polled `room_revision` changes, the client fetches `GET /sessions/<id>/room` and re-renders the Wizard notes and Hotspot set from the new `PlayView` (AD-12).
- **Trickster request.** When polled state shows an open Trickster window, the client posts `POST /sessions/<id>/trickster` once, with no visible pending state `[ASSUMPTION]`, and never again while the state shows the window `pending`; the server makes one source call per window and answers a repeat with the unchanged state (AD-4). The Card arrives in the reply and through the poll, as a new entry in `cards`.
- **Banned:** sliding, bouncing or shaking (a Wrong attempt is play, not failure); looping animation of any kind; sound; browser notifications; an offline mode; free conversation with any wizard; a reveal or skip after the near-answer (A-21); highlighting a new Evidence card; dismissing a Disclosure; modals more than one level deep; text over a photo except on a label chip; any image generation in play (FR-23).

## Accessibility Floor

Behavioral; contrast lives in `DESIGN.md` (Colors, contrast table). The floor is NFR-14 and AD-11, exactly:

1. Every Hotspot is reachable by Tab and shows a visible focus ring; Enter acts as a click.
2. A "Show all objects" toggle outlines every Hotspot.
3. A `use_on` input can be given by select-then-click and posts the same `UseOnInput` as a drop.
4. Text meets WCAG AA contrast on the dark theme.
5. Rungs, Cards and the Greeting are announced through one polite live region.
6. Motion respects reduced-motion settings.

How the floor is realized (behavior, not new requirements):

- **Focus.** Each Hotspot is a focusable element in the three.js scene's accessible overlay (DOM-only fallback: the same ids, AD-11). The focus ring is traced along the polygon, and the label chip gives the visual name for as long as the Hotspot has focus.
- **Show all objects.** The toggle is in the top bar, pressed state announced. It persists across Scene changes within the Session `[ASSUMPTION]`. It draws outlines only, with no labels and no fill (`{colors.hotspot-show-all}`).
- **Live region.** There is one region (`aria-live="polite"`), and only Rung lines (including the No-hint line), Cards, the Greeting or First-room welcome, the Guide's Completion sign-off, the reconnecting line and lock outcomes are written to it. Every in-character line is prefixed with its speaker ("The Guide:", "The Trickster:"). Cards read "The Trickster: {sentence} {outcome label}." (the label names the Validator); a rejected Card appends its "Proposed: …" line and plain reason ("That change was refused. {fixed message}"), so the UJ-3 climax is not lost. The first Card of the Session reads "The Trickster. {role line} {voice line} {sentence} {outcome label}.", so the introduction is heard once. Announcement rules:
  - **Lock outcomes** `[ASSUMPTION: an addition above the floor]`: "Not this · n" and "Open" are announced once each, as "Puzzle {n}: not this, {count}." and "Puzzle {n}: open.", so a screen-reader player hears the verdict without moving focus. "Checking" is not announced.
  - **Replies to explicit Hint requests are always announced** (Component Patterns, Rung line).
  - **Rungs and Cards that arrive through the poll** are announced once each.
  - **Nothing is re-announced on reload.**
  - **The Greeting or First-room welcome** goes to the live region once, with the Guide's introduction ("The Guide. {role line} {opening line} {voice line}"); the dialog is labelled by its heading only, so the line is not also read as the dialog's description while focus sits on "Begin". After "Begin" it stays in the Hint area without being announced again.
- **Build view keyboard.** Initial focus on the header title. Tab then moves through "Back", the Model table, the In play block, the verdict table and Dry run rows, the graph nodes, the mask label chips and the JSON toggle (the right column first, matching its place above the fold, then the left) `[ASSUMPTION]`. Tables are real `<table>` elements with header cells `[ASSUMPTION]`.
- **Card log.** A modal dialog: focus trapped, the Scene, Hotspots and top bar inert, Escape closes it and focus returns to its opener (Component Patterns).
- **Order click progress** carries a visually hidden "{filled} of {length}" description; the "Start the sequence" control is a plain button whose label changes to "Stop the sequence" while armed (a label change, not a pressed state), and keeps focus across the change.
- **Reduced motion** (`prefers-reduced-motion: reduce`): every fade becomes instant (a repeated Hint reply is still announced); the arrival glow becomes the lit ring held for 2 s with no animation; the 300 ms wrong flash on the order pips becomes an instant reset. The Guide thinking state, the Pending chip's ellipsis and the Timer's lamp dot are static in every setting.
- **Contrast.** Every text and state pair used here is listed in the `DESIGN.md` contrast table. No state depends on color alone.

## Key Flows

### UJ-1. Ana turns their living room into a game.

Ana has never played an escape room and wants a 20-minute game on a weeknight. Ana's iPhone is set to Most Compatible, and eight JPEG photos are on Ana's Mac. Local mode, Chrome.

1. Ana opens Keyframe. The Capture screen states "6 to 10 JPEG photos", the iPhone tip, the reminder about faces, documents and belongings, and the Retention summary ending in "the player profile stays on your machine."
2. Ana drags in the eight photos. The Photo tray shows them in order with "8 photos chosen", and Upload enables.
3. Ana clicks Upload (T0). The Timer starts in the top bar, and the Stage list starts at "Reading your photos" under the Architect's row, which introduces the Architect: "Reads your photos with muse-spark-1.3, names the objects, and draws their outlines with sam-3.1." and "I notice everything. Mostly mugs."
4. During "Finding objects", the Mask preview fills in: labelled outlines over Ana's mug, lamp and books, and the Architect's line names them: "I see 9 things worth a closer look, starting with the mug, the lamp and the books." The done row reads "9 objects", with muse-spark-1.3 and sam-3.1 beside its duration.
5. The stages finish ("Writing puzzles", whose row introduces the Riddler with its role line and "I taught your things to talk. Pity they only speak in riddles.", then reads "5 puzzles"; "Testing the room", done as "Rules: 8 of 8 passed" and "Test run: reached 5 of 5 answers"; "Setting the scene"). The Build is `done`, the Session starts, and the First-room welcome appears over the first Scene: the Guide introduces itself with its role line, says "Welcome to your own room. Find what doesn't belong.", then "Get stuck as often as you like. I'll help, a little at a time.", with the "Show all objects" tip underneath. Above the scrim, the Timer still runs under "Photos to play". Ana clicks "Begin".
6. Ana moves the pointer over the mug. It glows (T1), and the Timer freezes at T1 − T0 under "Playable in".
7. **Climax:** in the Wizard notes, under "Puzzle 1", the Riddler's first Clue points at Ana's mug, and the Evidence card directly under it shows the mug with "a year printed on the side": it says where to look and never shows the year itself. Ana recognizes their own mug in a puzzle.
8. Ana types a code: "Checking", then "Not this · 1". Ana retypes: "Open", and the next Puzzle fades into the notes.
9. Ana plays 4 to 6 Puzzles. The Exit puzzle opens and the Completion screen shows the time, hints used, wrong attempts and time per puzzle.

Failure: a HEIC file in the set → the whole set is refused with "Keyframe needs 6 to 10 JPEG photos.", the file is marked "Not a JPEG", and nothing is sent. Fewer than 5 objects → `needs_more_photos` with "Add photos" and "Start over". The last Regeneration fails → `needs_recapture` with guidance to reshoot. In every case the photos stay visible and the Timer shows the end status.

### UJ-2. Ana gets stuck and the Guide helps without telling.

Ana is mid-Room on a fresh Player profile (nudge threshold 90 s) and cannot find the second code.

1. Ana scans the Scene for 90 s without acting. The next poll brings a `rung_change`: "Puzzle 2 · Nudge" fades into the Hint area with no thinking state before it, the Guide's ring and the Hint area glow once so Ana looks up from the Scene, and the line is announced.
2. Ana submits three wrong codes ("Not this · 3"). No sooner than 90 s after the nudge, "Puzzle 2 · Direction" arrives the same way.
3. Ana opens the Triggers panel. Its header reads "Nudge after 90 s idle or 3 wrong attempts · next hint no sooner than 90 s" and "Default for a first room"; the rows read "Puzzle 2 · Nudge · Idle 90 s · worded on this Mac · 1.6 s" and "Puzzle 2 · Direction · 3 wrong attempts · worded on this Mac · 1.4 s".
4. Ana types "just tell me the answer" into the field labelled for Puzzle 2 and presses Enter. The words stay visible in the read-only field while the button says "Asking", under the helper line "Your words stay in this browser. The Guide only hears that you asked."; only a Hint request leaves the browser.
5. **Climax:** the Guide answers with the direction Rung again, and the field clears. The Rung line visibly fades out and back in (in Local mode, possibly reworded, never with more in it), and it is announced again as "The Guide: …". Nothing beyond the direction appears, and the Code field is still waiting.
6. Ana rereads the direction Rung in Puzzle 2's notes entry, marked "Current", looks at the bookshelf thumbnail, and opens the lock.

Failure: local phrasing takes more than 5 s → the verbatim Rung appears silently, and play continues. Ana asks before any Rung is open → the No-hint line, "A fair ask. Look around a little longer; I'll speak up if you stay stuck.", visibly arrives, is announced, and is logged as an Early ask.

### UJ-3. The Trickster changes the room between puzzles.

Ana has just opened a lock, at least 3 minutes of session time after the last Trickster window (30 s at Demo timescale 6, as on the Main demo).

1. The "Open" chip holds, and the next Puzzle appears. The polled state shows the Trickster window open, and the client posts the proposal request.
2. A Card arrives, the first of the Session, so it introduces the Trickster: "The Trickster" with "Reads the game state; proposes changes between puzzles with muse-spark-1.3, and the Validator checks each one." under the name, then "I like to move things around. The Validator keeps me honest, sadly." Then the Card itself: "A new evidence card has appeared. I do love a crowded desk.", then "Validator passed · Decoy · Puzzle 3". It is announced, introduction included. `room_revision` changes, the client refetches the Effective room, Puzzle 3's heading row now reads "3 evidence cards" instead of "2 evidence cards", and the new Evidence card sits among the real ones with no highlight.
3. At least one Trickster window later, Ana opens another lock. A second proposal arrives, with no introduction this time: "The Validator says that wouldn't be fair. Spoilsport.", then "Validator refused · Merge · Puzzle 4", then, in plain text, "Proposed: Puzzle 4 waits on Puzzle 2" and "That change was refused." with the rule's fixed message. The announcement includes both.
4. **Climax:** Ana sees the room fight back, and sees the rules bind the Trickster too. Both Cards stay in the Hint area until dismissed and are kept in the Card log.
5. The Effective room changed only for the accepted Card. The rejected one left the notes untouched.

Failure: a provider error or the Spend cap during the window → "I'm keeping quiet this time. Enjoy it while it lasts.", "Skipped"; play continues. An accepted Merge that hides the entry Ana is working on → the entry is replaced by "Puzzle {n} now waits on another puzzle.", focus moves there, and the Card's label names the same Puzzle.

### UJ-4. Ana comes back for a second room.

Ana finished room 1 by persisting past nudges, and now uploads photos of the study in the same browser and Player profile.

1. Ana uploads the study photos; the Build runs as in UJ-1 steps 2 to 5.
2. The Session starts with Ana's Derived block (`sessions` 1, positive persistence). The `POST /sessions` response says a greeting is being phrased, so the Greeting card appears with the Guide's introduction and the thinking state, then the phrased line, or the template: "Welcome back. Last time you kept going long past my first nudge; let's see what this room makes of you."
3. **Climax:** Ana feels recognized by the game, not tracked by a service. The line is about how Ana plays, never about Ana's objects.
4. Ana clicks "Begin". Room 2's Clues name things from the study, and the nudge now waits longer (toward 135 s); the Triggers header says so, with "Set by how you played last time (kept in this browser)".
5. At completion, the Room result is written into Ana's browser only.

Failure: Ana opens room 2 in a different browser → no Player profile, so the First-room welcome appears and the nudge threshold is 90 s.

### UJ-5. Priya, a judge, plays the hosted demo and builds their own room.

Priya has ten minutes, the hosted URL in a desktop browser, and the Access code from the submission.

1. The Hosted landing opens with the Disclosure "Hosted mode: hints are shown as written; no hint model runs here.", the mode indicator "Hosted mode", the title block with the pipeline line naming muse-spark-1.3, sam-3.1, the test run and the Guide, the lead-in "Short on time? See how a room is built and checked.", the Demo room cards (each named, with the four Wizard portraits) and the Access-code build.
2. With ten minutes, Priya can lead with the work (PRD §7) and follow "How a room is built": the Build view, headed with the Demo room's name, opens on the Model table (what each model did, cached or billed, the Validator as code, the test run, Muse Image), then the In play block (which explains that Llama 3.2 3B rewords hints on the Mac in Local mode), the verdicts with their captions, the masks and the puzzle graph, under the same Disclosure banner, which now also says "This room was built earlier, on {date}.". "Back" returns to the landing.
3. Priya picks a Demo room. The First-room welcome introduces the Guide and says "Welcome to someone else's room. Find what doesn't belong.", then "Begin". When Priya asks the Guide, Rungs appear verbatim with no thinking state, and their Triggers rows say "as written".
4. Priya returns to the landing, enters the Access code, and clicks "Check code". The code is checked without starting a Build, the status line says "{n} of 20 builds left", and the Capture screen opens with the Hosted Retention summary (deletion Tue Nov 10).
5. Priya uploads 6 JPEG photos of their office. The Build shows `queued` (the Timer reads "queued"), then runs; under the Stage list, "This build has its own link; close this tab or play a demo room meanwhile." The Stage list introduces the Architect and then the Riddler, and one Regeneration adds "Rewriting puzzles, attempt 1 of 2" with "Sent back:" and the failed rule's fixed message.
6. The Build outlasts the host's 150 s web timeout. Polling of `#/build/<job_id>` carries on, even across a closed and reopened tab. Once playable, the frozen Timer carries "includes m:ss in the queue", and the line under the Stage list says the two-minute target is measured in Local mode.
7. **Climax:** the Build completes, and Priya's Clues name Priya's own objects.
8. Priya plays the Judge room to the Completion screen, which shows "Deleted Tue Nov 10" below the sheet. Priya opens the Build view.

Failure: a wrong Access code → "That access code isn't right. No photos were sent.", inline, and no upload starts. The 21st Build → "All 20 judge builds have been used. The demo rooms are still open." After Tue Nov 10 → the Deleted Judge room notice.

### UJ-6. Luis records the Capture proof and the Main demo.

Tue Nov 3, Local mode on the M1, `CACHE=off`, a fresh Photo set shot that day, and fresh Player profiles for the Capture proof. `PROFILE=demo` holds only the real Mon Nov 2 room-1 run, played at Demo timescale 1 (§11.1), so it is not demo-flagged and counts toward the Derived block.

1. Luis clears the Cache on camera (outside the app), opens the Capture screen, and clicks Upload. The mode indicator reads "Local mode · Cache off · profile {name}", and the Timer runs on screen from T0. The Architect's and the Riddler's introductions in the Stage list, and the Architect's stage lines, carry the wait.
2. The First-room welcome appears, with the Timer still running above the scrim under "Photos to play", and Luis clicks "Begin" at once. The first Hotspot glows (T1), and the frozen T1 − T0 stays in the top bar under "Playable in". The take is kept only under 200 s.
3. For the Main demo's 0:15 and 1:35 beats, Luis opens the Build view from the Completion screen or the stored Room row (shot list in Demo Mode and Disclosure). Any active Disclosure stays in the banner at the top of the Build view.
4. For the 1:20 beat, Luis opens room 2 on `?profile=demo`. The mode indicator reads "profile demo · 1 room played", the Session sends the Derived block from the real room-1 run, and the Greeting (not the First-room welcome) appears, read from that record.
5. On the Play screen, with `DEMO_TIMESCALE=6` and the Scripted Trickster, the Disclosure banner reads "Hint and Trickster timings run at 6× speed; the build timer is real time." and "Trickster proposals replayed from a recording; the Validator ran live.", plus "This room was built earlier, on {date}." whenever the Room on screen was built before the take (the per-Room list in session state, AD-15). The Triggers panel is open automatically.
6. **Climax:** a 2:00 Main demo (cap 2:30) and an unedited Capture proof, honest about every shortcut. The banner never left the screen: it sits on every surface the beats are filmed on, the Build view included, and no scrim ever dims it.

Failure: a take over 200 s, or with a second visible retry → discarded and re-shot from step 1.

### UJ-7 (placeholder)

Tier 2, gated: controls, look rule and loading state stay out of this contract until the Mon Nov 2 gate passes (FR-34). Voice help (FR-35) likewise stays out until scheduled.

## Demo Mode and Disclosure

- **Source of truth.** Global Disclosure lines come from `GET /meta`, read once per page load; every Room-bound surface (Play, Completion, Build view) renders its Room's own list instead (AD-15). Each list is rendered as served, one line per entry, and an empty list means no banner. The client never composes or edits a Disclosure line itself. The Voice and Tone table lists the lines and their conditions; the Disclosure banner row in Component Patterns says which list each surface reads.
- **Placement.** The Disclosure banner sits at the top edge of the Capture, Play and Completion screens, the Build view and the Hosted landing (FR-26). The Build view carries it because two Main demo beats (0:15 and 1:35) are filmed there. It is part of the layout grid and pushes everything below it down (`{spacing.disclosure-min}` per line). It never covers the Scene or a Hotspot, and it has no close control. On the Build view, the one surface that scrolls past 900 px, the banner stays pinned at the top with the top bar while the body scrolls.
- **Scrims start below the top bar.** The Greeting, the Completion sheet, the Card log and the Leave room confirmation dim the body only, never the banner or the top bar (which stays visible but inert), so a Disclosure and the running Timer stay legible under every overlay.
- **Coupled behavior.** While any Disclosure is active, the Triggers panel opens automatically (FR-16). The Completion screen keeps the banner.
- **Mode declared (NFR-12).** The top bar's mode indicator (Component Patterns, Mode indicator) states the mode, the Cache setting, the active profile and the play history on every surface, so the finals fallbacks are visible on camera.
- **Earlier builds (PRD UJ-6 step 4).** The earlier-builds line comes from the Room's per-Room `disclosure` list under the conditions in the Disclosure copy table (AD-15).
- **Honesty (NFR-12).** Demo settings change only timing and the Trickster source. The UI has no demo-only path that injects events, Rungs, Greetings, Cards or Build output. The Timer and Event log timestamps are never scaled (FR-24). The Scripted Trickster's Cards render exactly like live ones, and the Validator decides them (AD-15).
- **If `GET /meta` fails,** no surface renders (see Capture cold load). A missing Disclosure must never look like "no shortcuts in effect".

### Main demo shot list

The §11.3 beats mapped to surfaces and states, with what must be legible at 1080p. Captions are added in the edit, not drawn by the app `[ASSUMPTION for every caption and shot]`.

| Beat | Surface and state | Legible at 1080p |
|---|---|---|
| 0:00 to 0:15 | A phone photo of the real room, then the Capture screen's Mask preview (or the Build view mask overlays): the same objects outlined, each with its label chip. Not "Show all objects", which draws outlines without labels | The object labels on their chips |
| 0:15 to 0:35 | The Capture screen as a time-lapse, Timer running under "Photos to play", the Stage list filling with done results and models; then the Build view: puzzle graph and verdict table with its caption. The BuildView JSON pane appears as a short cutaway (it stands in for the "puzzle JSON" the delivery plan names) | Edit caption "Time-lapse · unedited capture proof linked"; "Rules: 8 of 8 passed" and "Test run: reached 5 of 5 answers"; the verdict caption |
| 0:35 to 0:50 | The Play screen: "just tell me the answer" held in the read-only field while "Asking", the helper line, then the current Rung arriving again | The typed words, the helper line, the Rung label |
| 0:50 to 1:05 | The Play screen at 6×, the Triggers panel open (automatic under the Disclosure), only the newest Card stacked, the Hint area grown | The Triggers header with its 1× values, the newest row in full text color, the Rung line, all in frame together |
| 1:05 to 1:20 | Two Trickster Cards in the Hint area. For the recorded accepted proposal, prefer a Merge or a Loosen, whose effect shows on screen (a placeholder entry, or a Rung line), over a Decoy | "Validator passed · Merge · Puzzle {n}"; "Validator refused · {type} · Puzzle {n}", the "Proposed: …" line and the reason |
| 1:20 to 1:35 | Room 2 on `?profile=demo`: the Greeting card | The mode indicator "profile demo · 1 room played"; edit caption naming the real Mon Nov 2 run at Demo timescale 1 |
| 1:35 to 1:50 | The Build view: Model table (what each model did, cached or billed, its caption), In play block; optionally a Triggers row saying "worded on this Mac" | Model ids, the "What it did" column, the cached caption |
| 1:50 to 2:00 | The Disclosure banner on the Play screen | Every Disclosure line |

## Hosted Mode Differences

The one home for what changes between the modes; every other section describes Local mode unless it says otherwise.

| Area | Local mode | Hosted mode |
|---|---|---|
| Entry | The Capture screen, with stored Rooms listed below | The Hosted landing; "Build another room" and "Leave room" return to it. The landing shows the wizards through the Demo room cards and the pipeline line, and links each Demo room's Build view, whose Model table and In play block introduce them `[ASSUMPTION, for the builder]` |
| Disclosure | Only when the Demo timescale, the Trickster source or an earlier-built Room calls for one (Demo Mode and Disclosure) | Always shows "Hosted mode: hints are shown as written; no hint model runs here.", plus the Trickster-source line when it is scripted or cut 1 (§13 Q11), plus the earlier-builds line on Demo rooms (FR-26) |
| Mode indicator | "Local mode · Cache {on or off} · profile {name} · {k} rooms played" | "Hosted mode" |
| Guide | Rungs phrased by Llama 3.2 3B on the Mac, or verbatim after the 5 s fallback; the thinking state shows while a Hint request or the Greeting is in flight; Triggers rows say "worded on this Mac · {latency}" or "as written" | Rungs verbatim with the same anatomy; no thinking state (FR-17); the No-hint line is unchanged; every Triggers row says "as written"; the Guide's role line ends "shown as written", and the In play block explains that Llama 3.2 3B rewords hints in Local mode |
| Session start | Sends the Player profile's Derived block | Always sends a fresh Derived block (AD-8) |
| Opening line | Greeting when `sessions` ≥ 1; otherwise the First-room welcome | The First-room welcome for every Session, never a Greeting (FR-21, FR-31); on a Demo room, the Demo room variant |
| Player profile | Recorded locally; the Derived block is sent at session start | The browser may still record Room results locally (FR-20 is mode-agnostic), but nothing from it is sent `[ASSUMPTION]`; the Privacy line holds literally |
| Building | Open to anyone at the Mac | Access code checked before photo selection (rate-limited, starts no Build); the code goes with the upload, which re-checks it; 20-Build quota; `queued` state; a Build URL that resumes after the tab closes, said on screen under the Stage list (AD-9, FR-32) |
| Timer | Counts from T0 to T1 | Shows "queued" while queued; after T1 the frozen digits carry "includes m:ss in the queue"; a plain line under the Stage list says the two-minute target is measured in Local mode |
| Retention summary | The Local text served by `GET /meta` | The Hosted text: the Modal storage, Tue Nov 10 deletion and 24 h log lines replace the Local storage sentence, never appended (AD-15) |
| Failed Build retry | "Try again" | "Try again" states that it uses one of the remaining judge builds |
| Completion | No deletion line | A Judge room shows "Deleted Tue Nov 10"; a Demo room shows no deletion line |
| After deletion | Not applicable | The Judge room URL shows the Deleted Judge room notice (AD-9) |
| Stored Rooms list | Every stored Room (AD-9) | Absent; Demo room cards take its place, Demo rooms only, never Judge rooms (AD-9) |
| Browsers | Chrome on the Mac | Any current desktop Chrome, Safari or Firefox at 1280 px or wider; the Narrow-screen message below 1024 px |

## Privacy and Retention

- **Retention summary and Privacy line** sit in the right column of the Capture screen, visible before any photo is chosen, in both modes (FR-6). They are never collapsed or truncated. The Privacy line is verbatim and survives cut 3.
- **Raw room photos** go only to the services the Retention summary names. The client sends them in exactly one place, `POST /builds`, and never anywhere else. Play renders photos only from `GET /rooms/<room_id>/photos/<i>` (AD-11).
- **Typed hint text** never leaves the browser (Component Patterns, Hint field + Ask the Guide; FR-14). No copy implies the Guide "read" what was typed; the helper line says the opposite.
- **The Player profile** (Room results and the Derived block) lives in IndexedDB under the `?profile=` name. A Session start carries only the Derived block (FR-20). There is no profile viewer, export or delete control in v1 `[ASSUMPTION]`.
- **The reminder about faces, documents and other people's belongings** sits in the right column of the Capture screen, after the Input requirement and the iPhone tip and before the Retention summary, visible before upload (FR-6, PRD §8 order; `DESIGN.md` Layout).
- **No third-party requests beyond the named services.** The client calls only its own server, so the Capture screen makes no request to a service the Retention summary does not name; fonts are self-hosted in `web/dist` (`DESIGN.md` Typography).
- **Deletion copy** is plain: "Deleted Tue Nov 10" on a Judge room's Completion screen, and the Deleted Judge room notice afterwards (FR-33).

## Responsive & Platform

| Width | Behavior |
|---|---|
| 1440 px and up | Designed layout (`DESIGN.md` Layout & Spacing). |
| 1280 to 1439 px | Same layout; side column 360 px. |
| 1024 to 1279 px | Same layout; side column 340 px `[ASSUMPTION]`. Hosted support starts at 1280 px (A-15), so this band is best-effort. |
| Below 1024 px | The Narrow-screen message: heading "Keyframe needs a bigger screen" (`display-sm`, so it holds two lines on a phone), body "Open this page on a laptop or desktop browser to play." `[ASSUMPTION for the heading and body]`. No horizontal scroll at any width. |

Pointer and keyboard only. Touch is not designed for: a touch device at 1024 px or wider gets the desktop layout as-is `[ASSUMPTION]`.

## Open Items

The architecture amendments of Oct 21 settled every earlier `[NOTE FOR ARCHITECTURE]` (room listing, Access code check, mask preview, `needs_recapture`, server-resolved `use_on` and hint Puzzle, seeded Demo job records, `Room.name`, rule 5 on the Clue and Evidence, the armed order sequence, `active_puzzle_id`, the opening line and phrasing flag, the per-Room Disclosure list, per-mode Retention text, the extra `BuildView` fields, deletion records), and the builder's picks settled the earlier-builds, timescale and dry-run notes and the confirmation list. The body above follows the new contract and cites its AD ids. The review round of Oct 21 raised the new architecture notes below; the Oct 22 readiness review settled the rejected proposal summary through the `TricksterCard` projection (AD-3) and redefined the Active puzzle (AD-4), and the body follows both. What stays open:

- `[NOTE FOR ARCHITECTURE]` **Per-attempt fixed messages.** Job status and `BuildView` should carry, per failed attempt, the fixed messages that sent it back, so the Capture Regeneration row and the Build view header can show "Sent back: …".
- `[NOTE FOR ARCHITECTURE]` **Done-stage results.** Job status should expose per stage the counts the Stage list shows (photos, objects, puzzles, rules passed of 8, test-run answers reached) and the model id per stage, and `BuildView` should carry the provenance counts behind the Model table's "what it did" column.
- `[NOTE FOR ARCHITECTURE]` **Rung provenance.** `rung_change` should carry whether the Rung was phrased and the phrasing latency, so a Triggers row can say "worded on this Mac · 1.6 s" or "as written".
- `[NOTE FOR ARCHITECTURE]` **Help timing in session state.** Session state should expose the effective nudge threshold and Rung spacing (after the Demo timescale), their 1× values, and whether the threshold came from the Derived block or `Derived.fresh()`, for the Triggers header.
- **Closed (Oct 22): rejected proposal summary.** `TricksterCard` carries `edit_type`, `puzzle_id` and `related_puzzle_id` (AD-3), which the "Proposed: …" line and every Card label read.
- **Card time.** Closed (Oct 22): `TricksterCard` (AD-3) carries the event's `t_ms`, which the Card log row shows as the Card's session time.
- `[NOTE FOR ARCHITECTURE]` **Demo room welcome.** The opening line on a Demo room should be the Demo room variant ("Welcome to someone else's room. Find what doesn't belong."), chosen by the server; AD-5 names one fixed welcome today.
- `[NOTE FOR UX]` **Hosted Demo rooms at a Demo timescale (builder pick pending).** At full timings, a judge with ten minutes sees no Guide ladder and no Trickster in a Demo room. Running hosted Demo rooms at a Demo timescale, which FR-26 already discloses, would show both. This sits beside §13 Q11 and needs the builder's pick; the spine assumes full timings until then.
- `[NOTE FOR UX]` **PRD correction for bmad-correct-course.** The spine keeps the armed sequence controls ("Start the sequence", "Stop the sequence") of AD-4 and Schema v1. PRD FR-12 still says "the most recent clicks are judged against the sequence", and the PRD §8 Play screen list does not name the control; both are logged for bmad-correct-course.
- `[NOTE FOR UX]` **T1 and keyboard players.** T1 stays pointer-only, as the PRD Glossary defines it and as the Capture target and Capture proof measure it. A keyboard-only player's Timer therefore never freezes on focus. Whether T1 should also count the first keyboard focus on a Hotspot is a PRD question.
- `[NOTE FOR UX]` **Lock outcomes in the live region.** The floor's letter (NFR-14, AD-11) announces Rungs, Cards and the Greeting only. This spine adopts announcing "Not this" and "Open" in the same polite live region as an addition above the floor (Accessibility Floor) `[ASSUMPTION]`; the PRD floor itself is unchanged until the builder widens it.
- `[NOTE FOR UX]` **Capture → Play brevity.** Capture → Play is automatic (§8), so the "How this room was built" link on the Capture screen's `done` state is visible only briefly in a live Build. The lasting paths are the Completion screen, the stored Room row and a reopened build URL.
- `[NOTE FOR UX]` **"Begin" inside T1.** The First-room welcome (and the Greeting) sits inside the T0-to-T1 window, so "Begin" is one click inside the Capture target and the Capture proof. The Timer stays visible above the scrim, and in UJ-6 Luis clicks "Begin" at once.
- `[NOTE FOR UX]` **Hint area cap and the first Card** ([mockups/play-screen.html](mockups/play-screen.html), second section). At the 400 px column, the first Card with the Trickster's introduction is about 290 px tall, so inside the 320 px Hint area only about 130 px of it shows above the pinned controls, and the introduction, sentence and outcome label need scrolling. The spine lets the Hint area grow past its cap only while the Triggers panel is open. Letting it grow the same way while a first Card is present is the likely fix; it needs the builder's pick.
- `[NOTE FOR UX]` **Hint field placeholder at 340 px.** "Stuck? Ask the Guide for a hint" fits beside "Ask the Guide" only at `body-sm` in the 400 px column ([mockups/play-screen.html](mockups/play-screen.html)); in the 340 px column (1024 to 1279 px) it cuts off. The accessible label carries the full meaning, but a shorter placeholder may be needed in that band.
- `[NOTE FOR UX]` **Muse Image row, cached or billed** ([mockups/build-view.html](mockups/build-view.html)). The portraits are painted once, not per Build, so it is open whether that row's cell reads "1 billed" (the mock), stays empty like the Validator's, or says the portraits came from an earlier run.
- §13 Q3 owns the final Retention summary wording. §13 Q11 decides whether the hosted Trickster Disclosure line appears.
- **Closed: key-screen mocks.** The four mocks in `mockups/` ([mockups/capture-screen.html](mockups/capture-screen.html), [mockups/play-screen.html](mockups/play-screen.html), [mockups/completion-greeting.html](mockups/completion-greeting.html), [mockups/build-view.html](mockups/build-view.html)) are linked from the surface map and from `DESIGN.md` Layout & Spacing and Components. Their decisions are folded into both spines, and each mock was corrected where it disagreed.
