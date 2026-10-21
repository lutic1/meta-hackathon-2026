---
title: "Keyframe Experience"
name: Keyframe
status: draft
created: 2026-10-21
updated: 2026-10-21
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
- **Visual reference.** `DESIGN.md` defines the Lamplit study direction: warm dark chrome, parchment for cards and notes, serif headings, and the player's own photos framed like pictures in a wizard's study. Every component named below is a `DESIGN.md.Components` row with the same name. The four key-screen mocks the builder chose (Play screen, Capture screen, Build view, Completion and greeting) are pending; the surface map names each one, and until they exist the `DESIGN.md` tables are the only visual spec.
- **Theme and senses.** Dark theme only. No sound in v1. Motion is slow and warm, with no transition over 300 ms and no looping animation, and reduced-motion settings are honored (NFR-14). Input is mouse and keyboard. English only `[ASSUMPTION]`. No browser notifications and no offline mode: losing the network shows the reconnecting state only.
- **Lead with what the room knows, never with photorealism (PRD §7).** The UI shows off what the Architect read, not how pretty the photo is:
  - The Mask preview labels every found object on a parchment chip in `{typography.label}`, and the Architect's line names two or three of them before giving the count.
  - The Capture screen's `done` state and the Build view lead with the found objects and their outlines; every Build view overlay carries its label.
  - In the Wizard notes, the Evidence cards, with the attributes the Architect read, sit directly under the Clue they support.
  - The Scene photo is never enhanced, relit, retouched or upscaled. It is framed, never improved.
- **Helps without telling (UJ-2).** The Guide's help is always visible, always tied to a Puzzle, and never an answer. Every Rung line names its Puzzle ("Puzzle {n} · Nudge"). The Active puzzle is marked in the Wizard notes. Every reply to a Hint request visibly arrives and is announced, even when it repeats a Rung already on screen. A Rung that arrives unasked gets one lamplight glow on the Guide. Rung copy follows the scaffold ladder in Voice and Tone.
- **The client renders server state.** The client renders state and posts events. It never decides whether a lock is open, which Rung is current, or whether a Trickster edit applies (AD-4). It never holds a solution: play routes return `PlayView`, and the Build view reads `BuildView` (AD-3).
- **Two modes, one product.** The HTTP surface is the same in both modes (AD-9). What players see differs as follows. Hosted Mode Differences has the full table.

| Concern | Local mode | Hosted mode |
|---|---|---|
| Opens on | Capture screen, with stored Rooms listed below | Hosted landing |
| Rungs | Phrased by the Guide model on the Mac, or verbatim after the 5 s fallback | Always verbatim; the Guide thinking state never shows (FR-17) |
| Session start | Sends the Player profile's Derived block | Always sends a fresh Derived block (AD-8) |
| Opening line | Greeting when `sessions` ≥ 1; otherwise First-room welcome | Always the First-room welcome, never a Greeting (FR-21, FR-31) |
| Building | Open to anyone at the Mac | Access code first; at most 20 Builds; may wait `queued` (FR-32, FR-5) |
| Disclosure | Only when the Demo timescale, the Trickster source, the Cache or an earlier-built Room calls for one | Always includes the Hosted-mode line (FR-26) |
| Mode indicator (top bar, plain) | "Local mode · Cache {on or off} · profile {name}" from `GET /meta` | "Hosted mode" |

## Information Architecture

The surfaces come from PRD §8 (A-17). Navigation is mostly automatic. The player rarely chooses where to go: the Build carries them into play, and the Exit puzzle carries them to the Completion screen.

### Surface map

| Surface | Mode | Reached from | Leaves to | Purpose | FRs | Key Flow |
|---|---|---|---|---|---|---|
| Capture screen (mock `mocks/capture-screen.png`, pending) | Both | Local app open; "Build another room" (Local); accepted Access code (Hosted); a build URL | Play screen (automatic when the first Scene is ready); Build view link on `done`; stored Room replay (Local) | Choose photos, watch the Build, meet the Council, read where photos go | FR-1 to FR-6, FR-10, FR-28, FR-36 | UJ-1, UJ-4, UJ-5, UJ-6 |
| Greeting / First-room welcome (mock `mocks/completion-greeting.png`, pending) | Both | Session start, over the first Scene | Play screen ("Begin") | The Guide's opening line | FR-20, FR-21, FR-31 | UJ-4, UJ-1, UJ-5 |
| Play screen (mock `mocks/play-screen.png`, pending) | Both | Capture screen (automatic); stored Room row (Local); Demo room card (Hosted); reload of a session URL | Completion screen (automatic on the Exit puzzle); "Leave room" | Play the Session | FR-11 to FR-19, FR-23, FR-37 (Tier 1.5) | UJ-1, UJ-2, UJ-3 |
| Card log | Both | Top-bar "Card log" button on the Play screen | Back to the Play screen | Reopen this Session's Cards | FR-19 | UJ-3 |
| Triggers panel | Both | Always-visible toggle in the Hint area; opens automatically while a Disclosure is active | Collapses in place (a second window under cut 5) | Show why each Rung changed | FR-16 | UJ-2, UJ-6 |
| Leave room confirmation | Both | Top-bar "Leave room" | Capture screen (Local) or Hosted landing (Hosted); or back to play | Leave without recording a Room result | §8 Navigation | none (see Open Items) |
| Completion screen (mock `mocks/completion-greeting.png`, pending) | Both | Exit puzzle opens | Capture screen (Local) or Hosted landing (Hosted) via "Build another room"; Build view | Show the result and record the Room result | FR-13, FR-33, FR-38 | UJ-1, UJ-5 |
| Build view (mock `mocks/build-view.png`, pending) | Both | Capture screen on `done`; Completion screen; stored Room row (Local) `[ASSUMPTION]`; each Demo room card and the Hosted landing's "How a room is built" link (Hosted) | "Back" to where it was opened from | Show how the Room was built and verified | FR-38, FR-30, FR-27 (cached or billed) | UJ-6, UJ-1, UJ-5 |
| Hosted landing | Hosted | Hosted URL; "Build another room" (Hosted); "Leave room" (Hosted) | Play screen (Demo room card); Build view (Demo room card link, "How a room is built"); Capture screen (accepted Access code) | Meet the Council; play a Demo room or see how it was built; unlock a Judge room Build | FR-31, FR-32, FR-38 | UJ-5 |
| Disclosure banner | Both | Shown on the Capture, Play and Completion screens, the Build view and the Hosted landing whenever a Disclosure applies | Not navigable | Name each demo shortcut or mode in effect | FR-24 to FR-26 | UJ-5, UJ-6 |
| Deleted Judge room notice | Hosted | A Judge room URL opened after Tue Nov 10 | Hosted landing | State that the deletion happened as promised | FR-33 | UJ-5 (resolution) |
| Narrow-screen message | Both | Any surface below 1024 px wide | Not navigable | Say that Keyframe plays on a laptop or desktop browser | A-15 | none (see Open Items) |

### Navigation rules

- Modals stack one level deep. The Greeting, the Leave room confirmation and the Card log never open on top of each other.
- **Client routes** `[ASSUMPTION]`: hash routes, because FastAPI serves `web/dist` statically at `/` (AD-9) and this avoids a server-side fallback. The routes are `#/` (Local: Capture screen; Hosted: Hosted landing), `#/build/<job_id>` (Capture screen for that Build; resumes polling, FR-32), `#/build/<job_id>/view` (Build view), `#/play/<session_id>` (Play screen; reload resumes, FR-11), and `#/done/<session_id>` (Completion screen). The `?profile=` query parameter (AD-14) is carried on every route.
- **Stored Rooms (Local).** Each row shows a cover thumbnail, the Build's date and time, the Puzzle count, "Play" (starts a new Session) and "How it was built" (Build view). The list comes from the browser's own record of the Builds it started, kept beside the Player profile `[ASSUMPTION]`. Replaying a stored Room never shows the Timer.
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
| FR-21 | Greeting / First-room welcome |
| FR-23 | Every Wizard portrait: Stage list, Wizard notes, Hint area, Cards, Greeting, Hosted landing |
| FR-24, FR-25, FR-26 | Disclosure banner (FR-25 also through Trickster cards) |
| FR-27, FR-30 | Build view (Model table) |
| FR-28 | Capture screen (Spend cap message); Play screen (skipped Card) |
| FR-31 | Hosted landing; Play screen; First-room welcome |
| FR-32 | Hosted landing (Access-code build); Capture screen (`queued`, quota) |
| FR-33 | Completion screen ("Deleted Tue Nov 10"); Deleted Judge room notice |
| FR-36 | Capture screen (Retention summary, Privacy line); typed hint text never sent |
| FR-37 (Tier 1.5) | Play screen (Clue card slot in the Wizard notes) |
| FR-38 | Build view |

**FRs with no UI surface:** FR-20 and FR-22 (the Player profile and the demo flag live in IndexedDB, with no viewer in v1), and FR-29 (Ledger export). FR-34 (Tier 2, UJ-7) and FR-35 (voice) stay out of this contract until they are scheduled. Each gets a one-line placeholder only.

**Cut 2 placeholder (Player profile as a local JSON file).** Under cut 2 the Capture screen's right column gains a plain file control below the Retention summary: "Open profile file" (browser file picker) and, on the Completion screen, "Save profile file" (browser download), with one plain line, "Your player profile is a file on this computer; Keyframe reads it only when you open it." The Privacy line holds unchanged `[ASSUMPTION for the control and copy]`.

**Every surface has a Key Flow**, except the Leave room confirmation and the Narrow-screen message. Both are guard states that the PRD defines without a journey, and both are listed in Open Items rather than given an invented journey.

## Voice and Tone

Microcopy only. Brand voice and how the two registers look live in `DESIGN.md` (Brand & Style).

### Register rule (PRD §7)

| Register | Lines | Treatment |
|---|---|---|
| **In character** | Rungs, the No-hint line, the Greeting, the First-room welcome, Cards (the Trickster's sentence), Clues, Lore, Build stages (the Architect's stage lines), the Council strip's voice lines, the Guide's Completion sign-off | `{typography.wizard-line}` (or `{typography.wizard-line-lg}`, `{typography.lore}`), signed with the speaker's Wizard portrait, usually on parchment. Wry and playful, never condescending, one or two sentences. The Architect observes, the Riddler teases, the Guide encourages, and the Trickster has the most fun. |
| **Plain messages** | Format and count errors, `failed`, `needs_more_photos`, `needs_recapture`, `queued`, Spend cap, Build quota, Access code, deletion messages, the Retention summary, the Privacy line, the reconnecting state, the mode indicator, every Disclosure | `{typography.body-md}` or `{typography.body-sm}`. No portrait, never on parchment, no jokes. Says what happened and what to do next. |
| **Plain labels and chips** | Build stage names, Rung names and "Puzzle {n}" labels, Card outcome labels, the Validator's reason on a rejected Card, the "Checking", "Not this" and "Open" chips, stat labels, Hotspot and mask label chips | `{typography.label}` or `{typography.body-sm}`, sans. May sit on parchment. |

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
- **No-hint line criteria (PRD §7):** in-world and encouraging; never a refusal and never "no hint available"; it acknowledges the ask, says the Guide is watching and help is coming, invites one more look, and holds nothing about any Puzzle. The PRD sample, "Look around a little longer; I'll speak up if you stay stuck.", invites a look and promises help but does not clearly acknowledge the ask, so the fixed line adds a short acknowledgement: "A fair ask. Look around a little longer; I'll speak up if you stay stuck." `[ASSUMPTION]`. It says nothing about what was typed, because nothing typed is read.

### Voice for generated lines

Most of the wry voice lives in lines the models write: Clues, Lore and Rungs (authored by the Riddler at Build time) and the Greeting and phrased Rungs (phrased locally by the Guide model). Hosted mode and every fallback show the authored lines verbatim, so they must already be in voice. These rules go into the author and phrase prompts `[NOTE FOR ARCHITECTURE]`:

| Line | Written by | Voice | Length | Sample `[ASSUMPTION]` |
|---|---|---|---|---|
| Clue | Riddler prompt | The Riddler's: teasing, points at the Evidence without quoting it | One or two sentences | "Someone in this room is very proud of the year they were made. Ask the mug." |
| Lore | Riddler prompt | The Riddler's, in-world flavor; no help, no tokens | At most 60 words | "The mug has outlived three kettles and one diet. It remembers everything and says nothing, unless you look closely." |
| Rungs (nudge, direction, near-answer) | Riddler prompt, written in the Guide's voice because the Guide signs them | The Guide's: encouraging, warm; the scaffold ladder above | As the ladder | See the ladder above |
| Phrased Rung | Guide model (Local) | The Guide's | No longer than the Rung it rewords | Rewords; never adds content |
| Greeting | Guide model (Local) or the template | Wry, warm and specific about play style (PRD §7) | One or two sentences | See the template below |

- **Per-wizard attitude.** The Architect observes (plain facts with a dry aside), the Riddler teases (never mocks), the Guide encourages (never scolds, never sighs), the Trickster has the most fun (mischief aimed at the room, never at the player). Never condescending.
- **Phrasing may reword but never add content.** A phrased Rung or Greeting carries no fact that is not in its source (the Rung text or the Derived block numbers): no new object, no new hint, no solution, no play history beyond the Derived block.
- **Never name a token.** No Clue, Lore line or Rung names a solution token beyond the Rule 5 allowance, and no Evidence card displays one (see Open Items).

### Exact strings

`[ASSUMPTION]` marks wording this spine drafted. Strings marked "verbatim" come from the PRD Glossary, a requirement or the memlog and must not be paraphrased (the Input requirement, the Privacy line, the FR-1 and Spend cap errors, "n of 20 builds left", "Deleted Tue Nov 10", the Disclosure lines). The PRD §7 sample lines (sample nudge, No-hint line, Greeting template, First-room welcome, Card sentences) are drafts the UX contract owns (PRD §7); this spine adopts them as defaults and edits them where noted.

**Capture screen (plain)**

| Moment | String |
|---|---|
| Input requirement (verbatim term) | "6 to 10 JPEG photos". Shown in the dropzone as "Choose 6 to 10 JPEG photos of one room." `[ASSUMPTION for the sentence around the term]` |
| iPhone tip | "On iPhone, set Settings > Camera > Formats to Most Compatible so photos save as JPEG." `[ASSUMPTION]` |
| Faces, documents, belongings reminder | "Leave out faces, documents and other people's belongings." `[ASSUMPTION]` |
| Picker button / Upload | "Choose photos" / "Upload" `[ASSUMPTION for "Choose photos"]` |
| HEIC, PNG, other format, or wrong count (set rejected whole) | Banner: "Keyframe needs 6 to 10 JPEG photos." (verbatim, FR-1), with the action "Choose photos again". Label on each offending file: "Not a JPEG". When the count is the problem, the count line reads "{n} photos chosen" `[ASSUMPTION for the labels and the action]` |
| Downscaled file refused by ingest (422) | "Keyframe couldn't read these photos. Choose them again." `[ASSUMPTION]` |
| Stage names (A-11; plain labels in the Stage list) | "Reading your photos" (ingest) · "Finding objects" (architect, segment) · "Writing puzzles" (author) · "Testing the room" (validate, dry run) · "Setting the scene" (scene). Regeneration: "Rewriting puzzles, attempt n of {max}" ({max} is 2, or 1 under cut 7, read from the Build's configured maximum) |
| Architect stage lines (in character, one per stage, beside the Architect portrait) `[ASSUMPTION]` | Reading your photos: "{n} photos of one room. Let me find my loupe." · Finding objects: the Architect line below · Writing puzzles: "I've handed my notes to the Riddler. Brace yourself." · Testing the room: "Now we make sure every lock can actually be opened. Fair is fair." · Setting the scene: "Hanging your room on the wall. Mind the frame." · Regeneration: "The Riddler's first draft didn't pass. Another go." |
| Architect line over the Mask preview (in character) | "I see {label 1}, {label 2} and {label 3}, and {n} things worth a closer look in all." (two labels when only two are found; the labels come from the found Interactables in segment order) `[ASSUMPTION]` |
| `queued` (Hosted, warning) | "Another room is being built. Yours is next." `[ASSUMPTION]` |
| `needs_more_photos` (error) | Heading "Keyframe found too few objects to build a room." Body "Add a few more photos of this room, closer to shelves and tables, up to 10 in all." Actions: "Add photos", "Start over" `[ASSUMPTION for heading and body]` |
| `needs_recapture` (error) | Heading "Keyframe couldn't build a fair room from these photos." Body "Try brighter, closer shots where labels and printed text are readable." Action: "Start over" `[ASSUMPTION for heading]` |
| `failed` (error) | Heading "The build stopped at {stage label}." Body: one cause class, either "A model service didn't answer." or "The build stopped unexpectedly." Action: "Try again" (new Build, same photos). In Hosted mode the body adds "Trying again uses one of the remaining judge builds." `[ASSUMPTION for cause and consequence wording]` |
| Spend cap refusal (warning; `failed` with `spend_cap_exceeded`) | "Keyframe has reached its spending limit, so this room can't be built right now." (verbatim, PRD §7), then "Trying again won't help until the limit is raised; your photos are still here." `[ASSUMPTION]`. No "Try again" action; "Start over" only |
| Build quota exceeded (Hosted, warning) | "All 20 judge builds have been used. The demo rooms are still open." `[ASSUMPTION]` |
| Done | Build view link: "How this room was built" `[ASSUMPTION]`. On a reopened build URL that is already `done`: "Play this room" (primary) `[ASSUMPTION]` |

**Hosted landing (plain unless noted)**

| Moment | String |
|---|---|
| Title / subtitle | "Keyframe" / "An escape room built from your own photos." `[ASSUMPTION]` |
| Title-block link | "How a room is built" (opens the first Demo room's Build view) `[ASSUMPTION]` |
| Council strip (required in both modes; PRD §7: what each wizard consumes and produces, then its voice) | Role lines (plain): Architect "Reads your photos; names the objects and draws their outlines." · Riddler "Reads the objects; writes the puzzle chain, then a blind test proves it solvable." · Guide "Reads how you play; offers one Rung at a time, never the answer." · Trickster "Reads the game state; changes the room between puzzles, if the Validator agrees." Voice lines (in character): Architect "I notice everything. Mostly mugs." · Riddler "I make your things talk, in riddles, naturally." · Guide "I'll help when you're stuck, and not one word more." · Trickster "I rearrange the room between puzzles. The Validator keeps me honest, sadly." `[ASSUMPTION for every line]`. Shown on the Hosted landing, and on the Capture screen during a Local Build as each wizard's stage starts |
| Demo room card meta / link | "{n} puzzles · 15 to 25 min" / "How this room was built" `[ASSUMPTION for the link]` |
| Access code panel | Heading "Build your own room". Field label "Access code". Button "Check code" `[ASSUMPTION]` |
| Access code empty submit | "Enter the access code from the submission." `[ASSUMPTION]` |
| Access code refused | "That access code isn't right. No photos were sent." `[ASSUMPTION]` |
| Access code accepted | "{n} of 20 builds left" (verbatim, §8) |
| Quota reached | As the Build quota string above |

**Play screen**

| Moment | Register | String |
|---|---|---|
| Hint field placeholder / button | plain | "Stuck? Ask the Guide for a hint" `[ASSUMPTION]` / "Ask the Guide" (verbatim) |
| Hint field accessible label | plain | "Ask the Guide for a hint on Puzzle {n}" (n = the Active puzzle) `[ASSUMPTION]` |
| Button while sending | plain | "Asking" `[ASSUMPTION]` |
| Puzzle heading (Wizard notes) | plain label | "Puzzle {n}" (n = the Puzzle's order number in the Room, the same number the Rung lines, Triggers rows, Card labels and Build view graph use, so it never changes when a Merge or Shortcut reorders availability), with "Current" beside the Active puzzle's heading `[ASSUMPTION]` |
| Rung label | plain label | "Puzzle {n} · Nudge", "Puzzle {n} · Direction", "Puzzle {n} · Near-answer"; the No-hint line is labelled "Puzzle {n}" |
| Sample nudge (PRD §7; Rungs themselves come from the Room) | in character | "The shelf has been very quiet. Suspiciously quiet." |
| No-hint line (fixed) | in character | "A fair ask. Look around a little longer; I'll speak up if you stay stuck." `[ASSUMPTION: PRD §7 sample plus an acknowledgement, per the No-hint criteria]` |
| Ollama fallback | none | **Silent.** The verbatim Rung appears with the same anatomy as a phrased one. No notice, no badge, no "verbatim" label (FR-17; `DESIGN.md` Do's and Don'ts) |
| Pending chip | plain | "Checking" with a static ellipsis (no animation) `[ASSUMPTION]` |
| Merge-hidden entry placeholder | plain label | "Puzzle {n} now waits on another puzzle." `[ASSUMPTION]` |
| Order click progress description | plain | "{filled} of {length}" (visually hidden) `[ASSUMPTION]` |
| Order puzzle start control | plain | "Start the sequence" (pending the NOTE FOR ARCHITECTURE in Interaction Primitives) `[ASSUMPTION]` |
| Collected item, clicked again in the Scene | plain | "{label} · in hand" on the Hotspot label chip `[ASSUMPTION]` |
| Cards beyond two | plain | "{n} more in the Card log" `[ASSUMPTION]` |
| Wrong attempt chip | plain | "Not this · {n}" (n = Wrong attempts at this lock) |
| Open chip | plain | "Open" |
| Clicked non-target Hotspot | plain | The Interactable's label only, on the Hotspot label chip |
| Empty Inventory | plain | "Nothing in hand yet." `[ASSUMPTION]` |
| `use_on` selected chip | plain | "Using {item label}" plus "Cancel" `[ASSUMPTION]` |
| Triggers toggle / rows | plain | "Triggers ({n})". Rows: "Puzzle {n} · Nudge · Idle 92 s", "Puzzle {n} · Direction · 3 Wrong attempts", "Puzzle {n} · Near-answer · Loosen Card" `[ASSUMPTION for row layout]` |
| Top bar | plain | "Show all objects", "Card log", "Leave room"; mode indicator "Local mode · Cache off · profile {name}" (or "Cache on") or "Hosted mode" `[ASSUMPTION for the indicator wording]` |
| Leave room confirmation | plain | "Leave this room? This play-through won't be recorded." Buttons "Leave room" / "Keep playing" `[ASSUMPTION]` |
| Reconnecting | plain | "Reconnecting to Keyframe. Nothing is counted until it's back." `[ASSUMPTION]` |
| Session gone (Hosted log expired) | plain | "This play-through has ended. Start the room again." Button "Start again" `[ASSUMPTION]` |
| Server unreachable (cold load) | plain | "Keyframe can't reach its server. Retrying." `[ASSUMPTION]` |
| Session start refused | plain | "Keyframe couldn't start this room. Try again." `[ASSUMPTION]` |
| Card log empty | plain | "No Cards yet this session." `[ASSUMPTION]` |

**Greeting and First-room welcome (Guide, in character)**

- **Greeting brief (PRD §7).** Wry, warm and specific about play style; never about objects; never surveillance-flavored; one or two sentences. It should make a returning player feel recognized by the game, not tracked by a service.
- **Greeting template.** Used when phrasing is unavailable: cut 3, Ollama past 5 s, or Ollama unreachable. AD-5's "template filled with the numbers" is realized as one template whose phrase is chosen by the Derived block's numbers `[ASSUMPTION]`, checked in this order:
  - `time_to_first_hint_s` is null (the player never asked): "Welcome back. Last time you never asked me once; let's see what this room makes of you."
  - `persistence` ≥ 0.34: "Welcome back. Last time you held out long past the first nudge before asking; let's see what this room makes of you."
  - `persistence` −0.33 to 0.33: "Welcome back. Last time you held out a good while before asking; let's see what this room makes of you."
  - `persistence` ≤ −0.34: "Welcome back. Last time you held out just long enough to get your bearings before asking; let's see what this room makes of you."
  With Ollama, `greet(derived)` phrases the line freely under the Greeting brief and the generated-line rules: no object, no solution, nothing that sounds like surveillance, nothing beyond the Derived block.
- **First-room welcome.** "Welcome to your own room. Run the pointer over things to see what stirs, and keep an eye on the notes." `[ASSUMPTION: replaces the PRD §7 draft "Find what doesn't belong.", which implied an odd-one-out mechanic Keyframe does not have; never mentions false clues]`. Under the card, once per Player profile, a plain tip: "Tip: 'Show all objects' in the top bar outlines everything you can click." `[ASSUMPTION]`
- **Begin** is the only button.

**Cards (Trickster, in character, then a plain outcome label)**

Each sentence is a literal effect clause followed by one Trickster flourish; the sentence comes first and the outcome label after it. The PRD §7 samples are kept as the effect clauses, except Shortcut, whose draft "A door just opened early." was inaccurate (a Shortcut removes a prerequisite; it opens no lock). Every flourish is `[ASSUMPTION]`.

| Outcome | Sentence | Label (`{typography.label}`, after the sentence) |
|---|---|---|
| Accepted Decoy | "A new clue has appeared. I do love a crowded desk." | "Accepted · Decoy" (no Puzzle number, so the Card never points at the false card) |
| Accepted Merge | "This lock now needs another opened first. Patience builds character; I build locks." | "Accepted · Merge · Puzzle {n}" (n = the Puzzle that now waits) |
| Accepted Loosen | "The Guide is feeling generous. Don't tell anyone I allowed it." The Rung also appears as a Rung line. | "Accepted · Loosen · Puzzle {n}" |
| Accepted Shortcut | "One puzzle no longer waits on another. Consider it a corner I cut for you." | "Accepted · Shortcut · Puzzle {n}" |
| Rejected (any type) | "The Validator says that wouldn't be fair. Spoilsport." | "Rejected · {type}", then, plain: "That change was refused. {fixed message}" |
| Skipped (provider error or Spend cap; same text for both causes) | "The Trickster is quiet this time. Enjoy it while it lasts." | "Skipped" |

A Decoy Card never says which Evidence card is false (FR-19), and no flourish hints at it. **Fixed reason messages** belong to `domain/validator.py` (AD-3) and serve three places: the Build view's verdict table, the regeneration prompt and the rejected Card. Each is one neutral, plain sentence that never contains a token; the rejected Card adds its own "That change was refused." framing in the UI. Proposed wording `[ASSUMPTION]`: rule 1 "Two locks would wait on each other forever."; rule 2 "A lock could never be reached."; rule 3 "A puzzle names something that isn't in this room."; rule 4 "A puzzle cites something the Architect never saw."; rule 5 "A hint gives part of an answer away."; rule 6 "Lore or a hint breaks the length rules."; rule 7 "A lock doesn't have a valid shape."; rule 8 "A puzzle needs an item that can't be picked up yet."; rule 9 (after the decoy pick) "A false clue breaks the decoy rules."; `validate_edit` bounds "The change is outside the Trickster's limits."

**Completion screen**

| Element | Register | String |
|---|---|---|
| Heading | plain heading (serif, like every heading) | "The room is open." `[ASSUMPTION]` |
| Guide sign-off (48 px Guide portrait) | in character | Chosen from the Session's stats only, never objects `[ASSUMPTION]`: no Rungs used: "Not a single hint. I'm almost offended." · 1 to 3 Rungs: "You let me help a little. I enjoyed every word." · 4 or more: "We solved it together, and I'd do it again." |
| Stat labels | plain label | "Time", "Rungs used", "Wrong attempts", "Time per puzzle" `[ASSUMPTION]` |
| Actions | plain | "Build another room" (verbatim); "How this room was built" `[ASSUMPTION]` |
| Judge room | plain, below the sheet | "Deleted Tue Nov 10" (verbatim, FR-33) |
| Deleted Judge room notice | plain | Heading "This room is gone". Body "This room was deleted on Tue Nov 10, as promised." Button "Go to the demo rooms" `[ASSUMPTION for exact phrasing of FR-33]` |

**Disclosure copy (plain, out of character, literal; PRD §7)**

| Condition (from `GET /meta`) | Line |
|---|---|
| `demo_timescale` > 1 | "Timings shown at n× speed." (n = the timescale). Proposed replacement through `bmad-correct-course`, because the line sits above the real-time Timer and reads as if the build time were sped up: "Hint and Trickster timings run at n× speed; the build timer is real time." (see Open Items) |
| `trickster: scripted` | "Trickster proposals replayed from a recording; the Validator ran live." |
| `trickster: cut1` | "Trickster proposals were written in advance; the Validator ran live on each." |
| `mode: hosted` | "Hosted mode: hints are shown as written; no hint model runs here." |
| `cache: on` while the Timer is visible (a Build in progress or a just-finished one) | "Cache on: some model responses in this build are replayed from earlier runs." `[ASSUMPTION; NOTE FOR ARCHITECTURE: the server emits it]` |
| An earlier-built Room is in play or on view: a stored Room replay, a Demo room, a Build served from the Cache (UJ-6 step 4) | "This room was built earlier, on {date}." (date from the Room's provenance) `[ASSUMPTION for the wording; NOTE FOR ARCHITECTURE: the line depends on the Room, so the server must emit it per Room]` |

**Privacy and retention (plain)**

- **Privacy line**, verbatim: "the player profile stays on your machine." It holds under every Cut, including cut 3.
- **Retention summary.** Shows the one text served by `GET /meta` (`retention`), as served. The server serves a mode-specific text: the Hosted text replaces the Local storage sentence rather than appending to it `[NOTE FOR ARCHITECTURE]`. Its final wording depends on §13 Q3. The texts this spine expects `[ASSUMPTION; Q3 owns the final words]`:
  - **Shared opening (both modes):** "Where your photos go. Your photos and the puzzle text go to the Meta Model API (standard tier) to find objects, write puzzles and test them; {Meta retention terms}. If a backup model is switched on for the Riddler or the Trickster, that role's prompt goes to Baseten or Fireworks, never with an answer or anything from your player profile; {terms}."
  - **Local ending:** "A copy of your photos is also kept on this computer."
  - **Hosted ending (FR-6):** "In Hosted mode, your photos, the originals, your room and its play-throughs are stored on Modal and deleted Tue Nov 10. Play-through logs are deleted 24 hours after their last event. No player profile data leaves your browser."
  - The repository claim (photos under `rooms/`, never committed, FR-36) belongs in the README, not in the player-facing text. The fal.ai line appears only when Tier 2 ships. The voice line appears only when voice ships.
- **Fonts and other requests.** The Capture screen makes no request to a service the Retention summary does not name: fonts are self-hosted in `web/dist` (`DESIGN.md` Typography).

## Component Patterns

Behavior only. Visual specs live in `DESIGN.md.Components`, under the same names.

### Shared controls

| Component | Behavioral rules |
|---|---|
| Primary button | One per surface region at most. Enter and Space activate it. While its request is in flight it shows a pending label and ignores repeat activation. Disabled buttons stay focusable only when a reason is shown next to them `[ASSUMPTION]`. |
| Secondary button | Same keyboard behavior. Used for every banner action ("Add photos", "Start over", "Try again"), Submit on the Code field, and the top-bar toggles. "Show all objects" is a toggle with a pressed state announced as pressed or not pressed `[ASSUMPTION: top-bar controls use Secondary button]`. |
| Focus ring | Drawn by `{components.focus-ring}` on every focusable element, Hotspots and graph nodes included. Shown for keyboard focus (`:focus-visible`). Never suppressed. |
| Mode indicator | Plain text in the top bar on every surface, built from `GET /meta` (`mode`, `cache`, `profile`) so the finals mode and the active profile are declared on screen (NFR-12). Not focusable, not a control, not a Disclosure. Shows "Cache off" during the Capture proof. The Cache clear itself happens outside the app (a command Luis runs on camera); the app has no Cache-clear control and no demo-only path `[ASSUMPTION]`. |
| Status strip | Plain; takes no focus. Reconnecting: at the top of the Scene column, written once to the live region. Server unreachable: centered, alone. |

### Capture screen

| Component | Behavioral rules |
|---|---|
| Capture dropzone | Accepts drag-and-drop or the "Choose photos" picker. Validation is client-side and all-or-nothing: if any file is not a JPEG (checked by its bytes, not just its extension `[ASSUMPTION]`), or the count is under 6 or over 10, the whole set is rejected, nothing is uploaded, and the offending files are marked (FR-1). A valid set enables Upload. Upload produces the downscaled JPEGs (AD-7) and posts one multipart `POST /builds`. Disabled while a Build runs. |
| Photo tray | Shows the chosen photos in upload order with a count line. Before Upload the player can remove any photo, including a file marked "Not a JPEG" `[ASSUMPTION]`; each removal re-validates the whole set, so removing the offending files (or adding valid ones) clears the FR-1 banner and enables Upload. Stays visible in every end state (PRD §8). After `needs_more_photos`, "Add photos" reopens the picker and appends up to 10 in all. The next Upload is a new Build. |
| Mask preview | Fills in as segment results arrive in job state. The client draws each Interactable's outline over its own downscaled copy of the clearest photo `[ASSUMPTION]`, with the Interactable's label on a parchment chip. Tiles are not interactive. |
| Timer | Starts on the Upload click (T0). Counts up in m:ss. Stays in the same top-bar position from the Capture screen into the Play screen. Stops at T1, the first Hotspot that responds to the pointer on the Play screen, exactly as the PRD Glossary defines it; keyboard focus does not stop it (see Open Items), and then shows the frozen T1 − T0 for the rest of the Session. On `failed`, `needs_more_photos` or `needs_recapture` it stops and shows the end status. The Demo timescale never scales it. It keeps running under the First-room welcome or Greeting overlay. Hidden when replaying a stored Room or a Demo room. After a reload during a Build, it resumes from the Build's recorded start `[ASSUMPTION]`. |
| Stage list | One row per A-11 stage name, in order: pending → running → done (with duration) or failed. As each stage starts, the Architect's line beside the portrait changes to that stage's line. A Regeneration adds "Rewriting puzzles, attempt n of {max}" and re-runs the author, validate and dry-run rows. The Architect portrait signs the list. |
| Council strip (Capture, Local mode) | Required in Local mode, which has no Hosted landing. Under the Stage list, each wizard appears with its role line and voice line as its stage starts: the Architect with "Reading your photos", the Riddler with "Writing puzzles", the Guide and the Trickster with "Setting the scene". Static once shown; not interactive; not announced (the Stage list is not a live region). |
| Retention summary | Renders `GET /meta` `retention` as served, then the Privacy line. Always fully expanded and visible before any photo is chosen. Never collapsed or truncated (FR-6). |
| Error banner | Appears at the top of the left area, above the photos it refers to. One banner at a time; a newer state replaces an older one. Holds the plain heading, one sentence and its actions. Gets focus when it appears, so its text is read out and Tab reaches its actions next `[ASSUMPTION]`. The FR-1 refusal offers "Choose photos again", which reopens the picker and replaces the whole set. The warning variant (`{components.warning-banner}`) is used for Spend cap (no retry action, because a retry cannot succeed until the cap is raised), `queued` and Build quota. |
| Stored Room row (Local) | One row per Build this browser started: "Play" starts a new Session (no Timer); "How it was built" opens the Build view. The list says "No rooms yet." when empty. |

### Play screen

| Component | Behavioral rules |
|---|---|
| Scene frame | Shows one photo from `GET /rooms/<room_id>/photos/<i>`, contained and never cropped, never enhanced. While loading, the frame shows a plain loading line. While reconnecting, the status strip takes 32 px at the top of the Scene column and the frame shrinks to fit, so no Hotspot is covered; the photo dims and every input disables (FR-11). |
| Hotspot | One per Interactable on that photo: the union of its polygons, with the Hotspot id equal to the Interactable id (AD-11). Invisible at rest. Hover or focus reveals it (plus the label chip on focus). Click or Enter posts `click` (unless a `use_on` item is selected, in which case it posts only the `use_on` lock input; see Interaction Primitives). Tab order runs top to bottom, then left to right, by polygon centroid `[ASSUMPTION]`. Accessible name: the Interactable label, with the role of a button. When a `find` Puzzle is solved, its target's Hotspot stays in the Scene (the photo cannot change) but is no longer a target: its hover glow fades out over 200 ms in step with the Inventory item fading in, so the object reads as moving into the hand without anything sliding (FR-12); clicking it again shows "{label} · in hand" on the label chip `[ASSUMPTION]`. |
| Hotspot label chip | Shows the Interactable label on keyboard focus and stays for as long as the Hotspot has focus (WCAG 1.4.13). After a click on a Hotspot that is not a target (FR-12), it shows and fades after 2 s or when the pointer leaves. Never shows on hover alone, so hover stays a reveal and not a giveaway `[ASSUMPTION]`. |
| Thumbnail strip | One thumbnail per photo, in upload order (A-12). Click or Enter switches the Scene. The current photo is marked and announced as current. Stays usable while a `use_on` item is selected. |
| Inventory | Holds Interactables collected by solved `find` Puzzles for the whole Session (FR-11). A new item fades in over 200 ms, paired with its Hotspot's glow fading out (see Hotspot), with no flight animation. An item is a drag source for `use_on`. Click or Enter selects it for select-then-click, and a second activation or Escape deselects it. Shows the empty-state line when empty. |
| Wizard notes | One entry per available Puzzle, in availability order, each headed "Puzzle {n}". Each entry has its Clue (Riddler), the Evidence cards directly under the Clue, Lore, opened Rungs, its lock input (Code field or Order click progress; `find` and `use_on` happen in the Scene) and, in Tier 1.5, the Clue card slot. The Active puzzle's entry carries the `{components.active-puzzle-marker}` (a left rule plus the word "Current", never color alone), driven by `active_puzzle_id` from session state `[NOTE FOR ARCHITECTURE]`. Puzzles with unmet prerequisites are not drawn. A newly available entry fades in. An open entry collapses to one line with the Open chip. An accepted Merge hides the entry it now gates (fade out) and leaves the plain placeholder "Puzzle {n} now waits on another puzzle." in its place until the gating Puzzle opens; if focus was inside the hidden entry, focus moves to that placeholder. An accepted Shortcut reveals one. Scrolls on its own, inside the side column, never shorter than `{spacing.notes-min}`. |
| Clue card slot (Tier 1.5) | Drawn only when the Room has Clue cards (FR-37); otherwise the entry has no slot at all. Sits beside the Clue (FR-37), at `{components.clue-card-slot}` size. Placeholder until ready, blank on failure; the size never changes, so the layout never shifts. Alt text: when the image is shown, its alt is the Clue (FR-37) and the visible Clue text beside it is hidden from assistive technology, so the Clue is read once; while the slot is a placeholder or blank, the slot is hidden from assistive technology and the visible Clue is read `[ASSUMPTION for the no-double-readout method]`. |
| Wizard portrait | Decorative next to text that names the speaker (alt is empty). Every in-character line carries a visually hidden speaker prefix for screen readers: "The Architect:", "The Riddler:", "The Guide:" or "The Trickster:" `[ASSUMPTION]`. The Guide's portrait shows the thinking state (static lamp ring plus "thinking", no animation) while phrased text is awaited (Local only). When a Rung arrives through the poll without a Hint request, the Guide portrait ring and the Hint area show one lamplight arrival glow, 300 ms in all (under reduced motion, the lit ring held 2 s with no animation). Falls back to the placeholder art when the image is missing (FR-23). |
| Hint area | Holds the latest Rung line or No-hint line, at most two stacked Cards (newest on top; older ones behind a "{n} more in the Card log" link that opens the Card log) and the hint controls. Grows upward to `{spacing.hint-area-max}`, then scrolls inside itself, so the Wizard notes keep their minimum height. Its in-character lines are the ones the live region announces. After "Begin", it holds the Greeting or First-room welcome as its first Guide line until the first Rung replaces it (not announced again). |
| Rung line | Shows one Rung or the No-hint line, labelled with its Puzzle ("Puzzle {n} · Direction"). A new Rung replaces the previous Rung line, and the replaced Rung stays in its Puzzle's notes entry under "opened Rungs". **Every reply to a Hint request visibly arrives:** if the reply is the Rung already shown, the Rung line fades out and in again (200 ms each way, instant under reduced motion) and is announced again. In Local mode the Guide model may re-phrase a repeat so it does not read as a wall, rewording only; in Hosted mode and under any fallback the repeat is the same verbatim text. After the near-answer, a further Hint request repeats the near-answer; there is no reveal or skip (A-21). |
| Hint field + Ask the Guide | Enter in the field, or the button, sends one Hint request for the Active puzzle; the field's accessible label names it ("Ask the Guide for a hint on Puzzle {n}"). The typed text is discarded in the browser and the field clears (FR-14) `[ASSUMPTION: clears]`. An empty field still sends. While sending, the field is read-only and the button says "Asking". One request in flight at a time. |
| Triggers panel | Collapsed by default behind the always-visible toggle. Opens automatically when the page loads with a Disclosure active, and the player can still collapse it `[ASSUMPTION]`. Rows appear as `rung_change` events arrive, newest last. Capped at `{spacing.triggers-panel-max}` and scrolls inside, newest row kept in view. Under cut 5 it opens in a second window instead, with the same content. |
| Code field | Accepts up to 6 characters. Submit is disabled below 3 `[ASSUMPTION]`. Enter or Submit posts `lock_input` (CodeInput). While pending, the field is read-only and the Pending chip shows. A wrong code shows "Not this · n", keeps the field value and selects it for retyping. Open shows the Open chip and removes the field. The server compares the input trimmed and case-folded (A-20). |
| Order click progress | Shows one pip per position in the sequence, for each available `order` Puzzle, with a visually hidden description "{filled} of {length}". The pips stay empty and never flash until the player engages that order Puzzle ("Start the sequence" in its entry), so looking around the Scene is never shown as a failed sequence `[ASSUMPTION; NOTE FOR ARCHITECTURE in Interaction Primitives]`. Once engaged, a pip fills when the server acknowledges a click into the trailing buffer, never optimistically, so the pips always match the buffer being judged `[ASSUMPTION]`. A completed non-matching sequence turns the pips `{colors.wrong-ink}` for 300 ms, then empties them and shows "Not this · n". The pips never reveal which clicks were right. |
| `use_on` drag | Drag an Inventory item over the Scene. The Hotspot under the pointer shows its hover state. Dropping on a Hotspot posts `lock_input` (UseOnInput: item, target). Dropping anywhere else cancels and posts nothing. The Pending chip shows in the Puzzle's entry until the verdict. |
| `use_on` select-then-click | Selecting an item pins the "Using {item}" chip with Cancel. The next Hotspot click or Enter posts the same UseOnInput as a drop (AD-11) and clears the selection. Switching thumbnails keeps the selection. Escape or Cancel clears it. |
| Feedback chips | "Checking" from submit until the server's verdict. "Not this · n" until the next input on that lock. "Open" held for 1200 ms `[ASSUMPTION]`, then the entry collapses and the next Puzzle appears. The chip text is the lock input's accessible description `[ASSUMPTION]`. |
| Evidence card | Static, directly under its Clue. Shows the Interactable label, thumbnail crop and the read attribute as a description of where to look ("a year printed on the side"), never a solution token; an attribute that contains a solution token is never displayed (see the rule 5 note in Open Items). Real and Decoy cards behave identically and keep the stable order `PlayView` gives them. A new card gets no highlight and no announcement (FR-11, FR-19). |
| Trickster card, accepted | Enters after the lock-open state. Stays until dismissed (Dismiss control, accessible name "Dismiss card"). Copied into the Card log. Announced once in the live region. A Merge, Loosen or Shortcut Card names its Puzzle in the label ("Accepted · Merge · Puzzle 3"), so a Merge that hides an entry still points at it. |
| Trickster card, rejected | Same as accepted. The Validator's reason sits below the Trickster's sentence, in the plain register, framed "That change was refused. {fixed message}". The Effective room is unchanged. |
| Trickster card, skipped | Same as accepted. Play continues. Shown for `reason: provider_unavailable` (AD-4), which covers both causes FR-19 and FR-28 name: a provider error and the Spend cap reached during a Trickster window. No Card at all once the Session's seventh call would be needed (FR-19). |
| Card log | Opens from the top-bar button, or from the Hint area's "{n} more in the Card log" link, as a popover. Lists every Card this Session, oldest first, with its session time; each row leads with the Trickster's sentence in `{typography.wizard-line}`. Escape or the button closes it and focus returns to the control that opened it. Dismissing a Card in the Hint area never removes it from the Card log. |

### Completion, Greeting, Build view

| Component | Behavioral rules |
|---|---|
| Completion screen | Appears automatically after the Exit puzzle's open state. Reads `GET /sessions/<id>/result` and `web/profile` records the Room result (demo-flagged when the Demo timescale > 1, FR-22). Focus goes to the heading. The Guide's sign-off line is chosen from the stats only and written to the live region once. "Build another room" goes to the Capture screen (Local) or the Hosted landing (Hosted). "How this room was built" opens the Build view. Active Disclosures stay in the banner, which the scrim never dims. On a Judge room, shows "Deleted Tue Nov 10" in a plain strip below the sheet, off the parchment. A reload of `#/done/<session_id>` shows it again and does not record the result twice `[ASSUMPTION]`. |
| Greeting / First-room welcome | Shown over the first Scene after the Session starts and before play. Which line appears is decided by the Derived block sent (Greeting when `sessions` ≥ 1 in Local mode; First-room welcome otherwise, and always in Hosted mode). Focus is trapped and placed on "Begin". "Begin" is the only way to dismiss it (FR-21). The line is written to the live region (NFR-14); the dialog is labelled by its heading only and does not also use the line as its description, so the line is read once. Not shown again on reload once play has events `[ASSUMPTION]`. In Local mode, while the Greeting is being phrased, the Guide thinking state shows on the card for up to 5 s, then the template appears; the client learns the line and the phrasing state from the Session start `[NOTE FOR ARCHITECTURE]`. After "Begin", the line stays as the first Guide line in the Hint area, not announced again. The First-room welcome shows its one-time plain tip under the card. |
| Leave room confirmation | Opened by "Leave room" or the browser Back button on the Play screen. Focus is trapped and placed on "Keep playing". Escape means "Keep playing". Confirming records no Room result (§8) and goes to the Capture screen (Local) or the Hosted landing (Hosted). |
| Deleted Judge room notice | Replaces the Play or Completion screen for a Judge room URL opened after Tue Nov 10. Focus on the heading. "Go to the demo rooms" opens the Hosted landing. Requires the server to tell a deleted Judge room from an unknown one `[NOTE FOR ARCHITECTURE]`; until then an unknown room shows the Session-gone line. |
| Build view: header | Shows the Room's build time as its title (Schema v1 has no Room name), "Regenerations: n of {max}" with {max} read from the Build's configured maximum (2, or 1 under cut 7), and "Back". Not ready and error states replace the panels below it (see State Patterns). |
| Build view: mask overlays | Static per-photo grid. Each label chip is focusable and carries the Interactable label `[ASSUMPTION]`. |
| Build view: puzzle graph | Each node is focusable and Tab moves through nodes in Puzzle order. Accessible name: "Puzzle {n}, {lock type}, requires {list or none}, Dry run {pass, fail or skipped}", plus "Exit" on the Exit puzzle `[ASSUMPTION]`. Nodes are not interactive beyond focus. |
| Build view: Validator verdict table | One row per rule, from `BuildView`. Verdicts are words. |
| Build view: Dry run row | One row per Puzzle. Under cut 4 every row says "skipped" (PRD FR-38; SPEC CAP-14 says "absent", see Open Items). |
| Build view: Model table | One row per model used in this Build, from provenance. "cached" or "billed" spelled out (FR-27, FR-30). |
| Build view: In play block | Fixed, from `GET /meta`, not from the Build's provenance: the Guide (in Local mode the Guide model, Llama 3.2 3B on Ollama on the Mac; in Hosted mode "verbatim, no hint model"), the Trickster source (live, scripted or cut 1), and the four Wizard portraits "generated once with muse-image-1.0" (FR-23). It carries the Main demo's 1:35 beat ("the local Guide"). Static. |
| Build view: BuildView JSON | Collapsed by default behind "Show the build JSON". Opening it shows the `GET /builds/<job_id>/view` response exactly as served, which is solution-free by construction (AD-3). It stands in for the "puzzle JSON" of the Main demo's 0:15 beat and the README screenshot. Keyboard: the toggle is a button with an expanded state; the JSON pane is a focusable, scrollable region. |

### Modes, disclosure, platform

| Component | Behavioral rules |
|---|---|
| Disclosure banner | Rendered from `GET /meta` on every app load, one line per applicable Disclosure. Cannot be dismissed. Takes no focus and contains no controls. Read as page content at the top of each surface, the Build view included. No scrim ever covers or dims it. See Demo Mode and Disclosure. |
| Hosted landing | Shows the required Council strip, then the Demo room cards and the Access-code build side by side (UJ-5). The Council strip is static. The title block's "How a room is built" link opens the first Demo room's Build view, so a judge can lead with the work without first finishing a 15 to 25 minute room (PRD §7 "Lead with the work"). |
| Demo room card | Click or Enter on the card starts a Session on that Demo room with a fresh Derived block, then the First-room welcome. Its separate "How this room was built" link opens that Demo room's Build view (open in both modes, AD-3), with "Back" returning to the landing. The mask-and-graph thumbnail is decorative. |
| Access-code build | The code is checked before photo selection (FR-32). Submit gives checking → accepted (status line, then the Capture screen with the code held for `POST /builds` as `X-Access-Code`) or refused (compact error, no upload) or quota reached (warning; Demo room cards stay active). The code is kept for the tab's lifetime only and never written to storage `[ASSUMPTION]`. |
| Narrow-screen message | Replaces the whole app below 1024 px. Above 1024 px the app returns with its state intact (nothing is torn down in between `[ASSUMPTION]`). |
| Server unreachable (cold load) | Replaces the surface while `GET /meta` fails, retrying every 2000 ms; no Disclosure, Retention summary or Scene is guessed (see Capture cold load). |

The **Leave room confirmation** is a plain card on `chrome-raised` (`{components.leave-room-confirmation}`), never parchment, because its copy is a plain message.

## State Patterns

### Capture screen

| State | Treatment |
|---|---|
| Cold load | Waits for `GET /meta` (Disclosure, Retention summary), then shows the before-upload layout: Input requirement, iPhone tip, reminder, dropzone, Retention summary with the Privacy line. Stored Rooms below (Local). If `GET /meta` fails, a plain "Keyframe can't reach its server. Retrying." replaces the screen and retries every 2000 ms, because the Disclosure and Retention summary must not be guessed `[ASSUMPTION]`. |
| Empty | Dropzone at rest; Upload disabled; stored Rooms list says "No rooms yet." (Local) `[ASSUMPTION]`. |
| Photos chosen | Photo tray with count; Upload enabled. |
| Refused (picker) | Error banner "Keyframe needs 6 to 10 JPEG photos." with "Choose photos again"; offending files marked and removable from the tray; each removal or addition re-validates the set, and a valid set clears the banner and enables Upload; nothing sent until then. |
| Pending (uploading) | Upload shows its pending label; the Timer is running from T0; the dropzone is disabled. |
| Loading (Build) | Job status drives the screen. See Build job statuses below. |
| Success (`done`) | Every stage done; the "How this room was built" link appears; `POST /sessions` starts and the Play screen opens when the first Scene is ready. |
| Error | Error or warning banner per status; photos stay visible; the Timer is stopped with its end status. |
| Disabled | Everything except the Retention summary and banners is disabled during a Build. Under the Narrow-screen message nothing is shown. |
| Focus | Initial focus on "Choose photos" `[ASSUMPTION]`. A new banner takes focus. On `done`, focus moves with the screen to the Play screen. |

### Build job statuses (`GET /builds/<job_id>`, polled every 2000 ms `[ASSUMPTION: same cadence as sessions]`)

| Status | Stage list | Banner | Timer | Actions |
|---|---|---|---|---|
| `queued` (Hosted) | All pending | Warning: "Another room is being built. Yours is next." | Running | none |
| `running` + `stage` | That stage running, earlier ones done with durations; Regeneration rows when the attempt count rises | none | Running | none |
| `done` | All done | none | Running until T1 on the Play screen | Build view link; automatic Play |
| `failed` + `stage` | That stage failed | Error: "The build stopped at {stage label}." plus the cause class (and, in Hosted mode, that a retry uses a judge build). For `spend_cap_exceeded`, the warning variant with the Spend cap string and its consequence line | Stopped, end status | "Try again"; for `spend_cap_exceeded`, "Start over" only |
| `needs_more_photos` | Stopped at "Finding objects" | Error (FR-4 copy) | Stopped, end status | "Add photos", "Start over" |
| `needs_recapture` | Stopped at "Testing the room" after the last attempt | Error (FR-10 copy) | Stopped, end status | "Start over" |

Envelope codes map onto these states (AD-13): `too_few_interactables` → `needs_more_photos`; `regen_exhausted` → `needs_recapture` `[NOTE FOR ARCHITECTURE: not a typed error class name]`; `spend_cap_exceeded` → Spend cap; `provider_error` → "A model service didn't answer."; `unsupported_image` → the FR-1 banner; `build_quota_exceeded` → quota warning. Opening `#/build/<job_id>` on a Build that is already `done` shows the done state with "Play this room" and the Build view link instead of auto-starting `[ASSUMPTION]`.

### Greeting / First-room welcome

| State | Treatment |
|---|---|
| Loading | Local Greeting only: card shown with the Guide thinking state (static) for up to 5 s, driven by the phrasing flag in session state `[NOTE FOR ARCHITECTURE]`. |
| Success | Line shown; "Begin" focused; the line announced once through the live region. |
| Fallback | Phrasing over 5 s or unreachable: the template line appears in the same card, silently. |
| Focus | Trapped on the card; "Begin" is the only control. |
| After "Begin" | The line stays as the first Guide line in the Hint area, not announced again. |

### Play screen

| State | Treatment |
|---|---|
| Cold load | `GET /sessions/<id>` and `GET /sessions/<id>/room`. The Scene frame shows its loading line until the first photo is drawn and its Hotspots are live. |
| Reload | Resumes from the Event log: same Scene index (the first Scene `[ASSUMPTION]`), Inventory, open locks, current Rungs, Cards (from the log, all in the Card log, none re-stacked in the Hint area `[ASSUMPTION]`) and the frozen Timer if it was set. No Greeting if play has events. |
| Empty | Inventory empty line; Card log empty line; Hint area with no Rung line (controls only). |
| Pending | Per lock: the "Checking" chip until the server's verdict; Hint request: "Asking" plus the Guide thinking state (Local). |
| Polling | `GET /sessions/<id>` every 2000 ms while the Play screen is open (AD-4); this read also drives idle ticks. New `rung_change` gives a Rung line plus a Triggers row plus an announcement, and, because nobody asked for it, one arrival glow on the Guide portrait ring and the Hint area (300 ms in all; static lit ring under reduced motion) so a player looking at the Scene notices the Guide speaking up. New `trickster_card` gives a Card plus an announcement. A changed `room_revision` triggers a refetch of `GET /sessions/<id>/room` and a re-render of the Wizard notes. Polling continues while the tab is hidden `[ASSUMPTION]`. |
| Hint reply | The reply to an explicit Hint request always fades in (again, if it repeats the Rung on screen) and is always announced, prefixed "The Guide:". No arrival glow, because the player asked. |
| Ollama timeout fallback | After 5 s the verbatim Rung replaces the thinking state. No message. Unreachable Ollama gives the verbatim Rung at once (FR-17). |
| Success (lock open) | "Open" chip for 1200 ms, then the entry collapses, the next Puzzle fades in, a solved `find` target's Hotspot glow fades out while its item fades into the Inventory (both 200 ms), and then any Card. |
| Merge hides the entry in use | The hidden entry is replaced by its plain placeholder line; focus inside it moves to the placeholder; the Card names the Puzzle. |
| Wrong attempt | "Not this · n"; no shake, no sound; the Rung may advance on a later poll (FR-15). |
| Skipped card | Shown like any Card; play never pauses. |
| Refused | An input for a Puzzle whose prerequisites are not open, or a `use_on` with an item not held, is not a Wrong attempt; it shows nothing beyond clearing its Pending chip `[ASSUMPTION]`. |
| Error (reconnecting) | When a request fails or the poll misses `[ASSUMPTION: two consecutive misses]`: the Scene dims, every input is disabled, and the reconnecting line shows in the status strip at the top of the Scene column; the Scene frame shrinks by the strip's height, so the strip never covers a Hotspot. An input that never reached the server is dropped; the Code field keeps its value. Recovery re-renders from server state and removes the strip. |
| Error (Session gone) | Hosted log expired or Room deleted: the play-through-ended state, the photo dimmed under the plain Session-gone line with "Start again" (or the Deleted Judge room notice). |
| Disabled | During reconnecting; Hotspots are inert under the Greeting and Leave room overlays. |
| Focus | After the Greeting, focus goes to the first Hotspot of the first Scene `[ASSUMPTION]`. After a lock opens, focus moves to the next Puzzle's entry heading `[ASSUMPTION]`. |

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
| Cut 0 | The surface and every link to it are absent. |

### Hosted landing

| State | Treatment |
|---|---|
| Cold load | `GET /meta` (Disclosure with the Hosted line), then the Demo room cards `[NOTE FOR ARCHITECTURE: listing route]`. |
| Access code empty / checking / refused / accepted / quota reached | As in Component Patterns. Refused and quota use the compact error and warning banners inside the panel. |
| Focus | Initial focus on the first Demo room card `[ASSUMPTION]`. |

## Interaction Primitives

- **Click** to act everywhere. A Hotspot click always posts `click` (`ClickEvent(interactable_id)`), except when a `use_on` item is selected. A click is never by itself a Wrong attempt; the only click-driven Wrong attempt is a completed, non-matching `order` buffer (AD-4, PRD §3 Wrong attempt).
- **Hover** reveals a Hotspot (`{components.hotspot}` hover state, 150 ms). Hover is never the only path: Tab focus and "Show all objects" reveal the same Hotspots (NFR-14).
- **Keyboard.** Tab and Shift+Tab move in reading order: top bar → Scene Hotspots → Thumbnail strip → Inventory → Wizard notes → Hint area. Enter acts as a click on Hotspots, thumbnails, Inventory items, Demo room cards and graph nodes. Enter submits the Code field, the hint field and the Access code field. Escape closes the Card log, cancels a `use_on` selection, and means "Keep playing" on the Leave room confirmation. Escape never dismisses the Greeting. No single-key shortcuts in v1 `[ASSUMPTION]`.
- **Drag** (`use_on`): pointer drag from the Inventory onto a Hotspot. **Select-then-click** is the equivalent for keyboard and pointer: select the item, optionally switch Scenes, then click or Enter on a Hotspot. Both post one `lock_input` with UseOnInput (AD-11) and nothing else: the target click of a select-then-click posts no `click`, exactly as a drop posts none, so the two paths are identical to the server (no `find` match, no order-buffer entry). This spine decides it that way; AD-4's "a click for every hotspot click" needs to confirm the exception `[NOTE FOR ARCHITECTURE]`. The `puzzle_id` is the available `use_on` Puzzle; when several are available, it is the Active puzzle if that is a `use_on` Puzzle, else the first in the Wizard notes, unless the server resolves it from the target `[ASSUMPTION; NOTE FOR ARCHITECTURE]`.
- **Active puzzle.** AD-4 defines it as the Puzzle of the most recent `lock_input` or attempted click. The client cannot compute that for a click without knowing solutions, so it reads `active_puzzle_id` from session state, or the server resolves the `puzzle_id` of a Hint request itself `[NOTE FOR ARCHITECTURE]`. Before any attempt it is the first available Puzzle `[ASSUMPTION]`. The Wizard notes mark it ("Current"), the hint field's accessible label names it, and every Rung line names its Puzzle.
- **Order click buffer.** Per AD-4, every Hotspot click feeds the server's trailing buffer, and when the buffer reaches the sequence length the server judges it: a match opens the lock; a mismatch is one Wrong attempt, resets the buffer and empties the pips. With an `order` Puzzle available, that rule turns ordinary exploring into failed sequences, "Not this" flashes and nudges after three mismatches, which punishes looking around. `[NOTE FOR ARCHITECTURE]`: arm the order buffer only after an explicit start in the Puzzle's entry ("Start the sequence"), or judge only clicks on that Puzzle's candidate Hotspots. Until that is decided, the Order click progress pips stay empty and never flash for clicks made before the player engages the order Puzzle.
- **Code submit.** Enter or Submit posts `LockInputEvent(puzzle_id, CodeInput)`. The lock shows open only on the server's confirmation (FR-12).
- **Hint request.** Enter in the hint field or "Ask the Guide" posts `HintRequestEvent(puzzle_id)` for the Active puzzle (before any attempt: the first available Puzzle `[ASSUMPTION]`). The player's text never leaves the browser (AD-4). The reply is the current Rung or the No-hint line, labelled with its Puzzle. The reply always visibly arrives (a repeat fades in again) and is always announced, prefixed "The Guide:".
- **Polling.** Session every 2000 ms (AD-4); Build every 2000 ms `[ASSUMPTION]`. The client never stamps time: `t_ms` comes from the API.
- **Refetch on `room_revision`.** When the polled `room_revision` changes, the client fetches `GET /sessions/<id>/room` and re-renders the Wizard notes and Hotspot set from the new `PlayView` (AD-12).
- **Trickster request.** When polled state shows an open Trickster window, the client posts `POST /sessions/<id>/trickster` once, with no visible pending state `[ASSUMPTION]`. The Card arrives through the poll.
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
- **Live region.** There is one region (`aria-live="polite"`), and only Rung lines (including the No-hint line), Cards, the Greeting or First-room welcome, the Guide's Completion sign-off and the reconnecting line are written to it. Every in-character line is prefixed with its speaker ("The Guide:", "The Trickster:"). Cards read "The Trickster: {sentence} {outcome label}."; a rejected Card appends its plain reason ("That change was refused. {fixed message}"), so the UJ-3 climax is not lost. Announcement rules:
  - **Replies to explicit Hint requests are always announced**, prefixed "The Guide:", even when the reply repeats a Rung already on screen or is the No-hint line.
  - **Rungs and Cards that arrive through the poll** are announced once each.
  - **Nothing is re-announced on reload.**
  - **The Greeting or First-room welcome** goes to the live region once; the dialog is labelled by its heading only, so the line is not also read as the dialog's description while focus sits on "Begin". After "Begin" it stays in the Hint area without being announced again.
- **Order click progress** carries a visually hidden "{filled} of {length}" description.
- **Reduced motion** (`prefers-reduced-motion: reduce`): every fade becomes instant (a repeated Hint reply is still announced); the arrival glow becomes the lit ring held for 2 s with no animation; the 300 ms wrong flash on the order pips becomes an instant reset. The Guide thinking state, the Pending chip's ellipsis and the Timer's lamp dot are static in every setting.
- **Contrast.** Every text and state pair used here is listed in the `DESIGN.md` contrast table. No state depends on color alone.

## Key Flows

### UJ-1. Ana turns their living room into a game.

Ana has never played an escape room and wants a 20-minute game on a weeknight. Ana's iPhone is set to Most Compatible, and eight JPEG photos are on Ana's Mac. Local mode, Chrome.

1. Ana opens Keyframe. The Capture screen states "6 to 10 JPEG photos", the iPhone tip, the reminder about faces, documents and belongings, and the Retention summary ending in "the player profile stays on your machine."
2. Ana drags in the eight photos. The Photo tray shows them in order with "8 photos chosen", and Upload enables.
3. Ana clicks Upload (T0). The Timer starts in the top bar, the Stage list starts at "Reading your photos", and the Architect appears in the Council strip with its role and voice lines.
4. During "Finding objects", the Mask preview fills in: labelled outlines over Ana's mug, lamp and books, and the Architect's line names them: "I see a mug, a lamp and a row of books, and 9 things worth a closer look in all."
5. The stages finish ("Writing puzzles", where the Riddler joins the Council strip; "Testing the room"; "Setting the scene", where the Guide and the Trickster join). The Build is `done`, the Session starts, and the First-room welcome appears over the first Scene, telling Ana to run the pointer over things and watch the notes, with the "Show all objects" tip underneath. Ana clicks "Begin".
6. Ana moves the pointer over the mug. It glows (T1), and the Timer freezes at T1 − T0.
7. **Climax:** in the Wizard notes, under "Puzzle 1", the Riddler's first Clue points at Ana's mug, and the Evidence card directly under it shows the mug with "a year printed on the side": it says where to look and never shows the year itself. Ana recognizes their own mug in a puzzle.
8. Ana types a code: "Checking", then "Not this · 1". Ana retypes: "Open", and the next Puzzle fades into the notes.
9. Ana plays 4 to 6 Puzzles. The Exit puzzle opens and the Completion screen shows the time, Rungs used, Wrong attempts and time per puzzle.

Failure: a HEIC file in the set → the whole set is refused with "Keyframe needs 6 to 10 JPEG photos.", the file is marked "Not a JPEG", and nothing is sent. Fewer than 5 objects → `needs_more_photos` with "Add photos" and "Start over". The last Regeneration fails → `needs_recapture` with guidance to reshoot. In every case the photos stay visible and the Timer shows the end status.

### UJ-2. Ana gets stuck and the Guide helps without telling.

Ana is mid-Room on a fresh Player profile (nudge threshold 90 s) and cannot find the second code.

1. Ana scans the Scene for 90 s without acting. The next poll brings a `rung_change`. The Guide's portrait shows its thinking state, then "Puzzle 2 · Nudge" fades into the Hint area, the Guide's ring and the Hint area glow once so Ana looks up from the Scene, and the line is announced.
2. Ana submits three wrong codes ("Not this · 3"). No sooner than 90 s after the nudge, "Puzzle 2 · Direction" arrives the same way.
3. Ana opens the Triggers panel: "Puzzle 2 · Nudge · Idle 90 s", "Puzzle 2 · Direction · 3 Wrong attempts".
4. Ana types "just tell me the answer" into the field labelled for Puzzle 2 and presses Enter. The field clears, and only a Hint request leaves the browser.
5. **Climax:** the Guide answers with the direction Rung again. The Rung line visibly fades out and back in (in Local mode, possibly reworded, never with more in it), and it is announced again as "The Guide: …". Nothing beyond the direction appears, and the Code field is still waiting.
6. Ana rereads the direction Rung in Puzzle 2's notes entry, marked "Current", looks at the bookshelf thumbnail, and opens the lock.

Failure: local phrasing takes more than 5 s → the verbatim Rung appears silently, and play continues. Ana asks before any Rung is open → the No-hint line, "A fair ask. Look around a little longer; I'll speak up if you stay stuck.", visibly arrives, is announced, and is logged as an Early ask.

### UJ-3. The Trickster changes the room between puzzles.

Ana has just opened a lock, at least 3 minutes of session time after the last Trickster window (30 s at Demo timescale 6, as on the Main demo).

1. The "Open" chip holds, and the next Puzzle appears. The polled state shows the Trickster window open, and the client posts the proposal request.
2. A Card arrives: "A new clue has appeared. I do love a crowded desk.", then "Accepted · Decoy". It is announced. `room_revision` changes, the client refetches the Effective room, and a new Evidence card sits among the real ones in the notes with no highlight.
3. At least one Trickster window later, Ana opens another lock. A second proposal arrives: "The Validator says that wouldn't be fair. Spoilsport.", then "Rejected · Merge", then, in plain text, "That change was refused." and the rule's fixed message. The announcement includes the reason.
4. **Climax:** Ana sees the room fight back, and sees the rules bind the Trickster too. Both Cards stay in the Hint area until dismissed and are kept in the Card log.
5. The Effective room changed only for the accepted Card. The rejected one left the notes untouched.

Failure: a provider error or the Spend cap during the window → "The Trickster is quiet this time. Enjoy it while it lasts.", "Skipped"; play continues. An accepted Merge that hides the entry Ana is working on → the entry is replaced by "Puzzle {n} now waits on another puzzle.", focus moves there, and the Card's label names the same Puzzle.

### UJ-4. Ana comes back for a second room.

Ana finished room 1 by persisting past nudges, and now uploads photos of the study in the same browser and Player profile.

1. Ana uploads the study photos; the Build runs as in UJ-1 steps 2 to 5.
2. The Session starts with Ana's Derived block (`sessions` 1, positive persistence). The Greeting card appears with the Guide thinking state, then the phrased line, or the template: "Welcome back. Last time you held out long past the first nudge before asking; let's see what this room makes of you."
3. **Climax:** Ana feels recognized by the game, not tracked by a service. The line is about how Ana plays, never about Ana's objects.
4. Ana clicks "Begin". Room 2's Clues name things from the study, and the nudge now waits longer (toward 135 s).
5. At completion, the Room result is written into Ana's browser only.

Failure: Ana opens room 2 in a different browser → no Player profile, so the First-room welcome appears and the nudge threshold is 90 s.

### UJ-5. Priya, a judge, plays the hosted demo and builds their own room.

Priya has ten minutes, the hosted URL in a desktop browser, and the Access code from the submission.

1. The Hosted landing opens with the Disclosure "Hosted mode: hints are shown as written; no hint model runs here.", the mode indicator "Hosted mode", the Council strip introducing the four wizards, the Demo room cards and the Access-code panel.
2. With ten minutes, Priya can lead with the work (PRD §7) and open "How this room was built" on a Demo room card first: the Build view shows the masks, the puzzle graph and the verdicts, under the same Disclosure banner. "Back" returns to the landing.
3. Priya picks a Demo room. The First-room welcome appears, then "Begin". When Priya asks the Guide, Rungs appear verbatim with no thinking state.
4. Priya returns to the landing, enters the Access code, and clicks "Check code". The status line says "{n} of 20 builds left", and the Capture screen opens with the Hosted Retention summary (deletion Tue Nov 10).
5. Priya uploads 6 JPEG photos of their office. The Build shows `queued`, then runs, and one Regeneration adds "Rewriting puzzles, attempt 1 of 2".
6. The Build outlasts the host's 150 s web timeout. Polling of `#/build/<job_id>` carries on, even across a closed and reopened tab.
7. **Climax:** the Build completes, and Priya's Clues name Priya's own objects.
8. Priya plays the Judge room to the Completion screen, which shows "Deleted Tue Nov 10" below the sheet. Priya opens the Build view.

Failure: a wrong Access code → "That access code isn't right. No photos were sent.", inline, and no upload starts. The 21st Build → "All 20 judge builds have been used. The demo rooms are still open." After Tue Nov 10 → the Deleted Judge room notice.

### UJ-6. Luis records the Capture proof and the Main demo.

Tue Nov 3, Local mode on the M1, `CACHE=off`, a fresh Photo set shot that day, and fresh Player profiles for the Capture proof. `PROFILE=demo` holds only the real Mon Nov 2 room-1 run, played at Demo timescale 1 (§11.1), so it is not demo-flagged and counts toward the Derived block.

1. Luis clears the Cache on camera (outside the app), opens the Capture screen, and clicks Upload. The mode indicator reads "Local mode · Cache off · profile {name}", and the Timer runs on screen from T0. The Architect's stage lines and the Council strip carry the wait.
2. The First-room welcome appears and Luis clicks "Begin". The first Hotspot glows (T1), and the frozen T1 − T0 stays in the top bar. The take is kept only under 200 s.
3. For the Main demo's 0:15 and 1:35 beats, Luis opens the Build view from the Completion screen or the stored Room row: mask overlays, puzzle graph, verdicts, Dry run rows, the BuildView JSON pane (the "puzzle JSON"), a Model table showing "cached" and "billed", and the In play block naming the local Guide (Llama 3.2 3B on Ollama on the Mac), the Trickster source and the portraits generated once with muse-image-1.0. Any active Disclosure stays in the banner at the top of the Build view.
4. For the 1:20 beat, Luis opens room 2 on `?profile=demo`. The Session sends the Derived block from the real room-1 run, so the Greeting (not the First-room welcome) appears, read from that record.
5. On the Play screen, with `DEMO_TIMESCALE=6` and the Scripted Trickster, the Disclosure banner reads "Timings shown at 6× speed." and "Trickster proposals replayed from a recording; the Validator ran live.", plus "This room was built earlier, on {date}." whenever the Room on screen was built before the take. The Triggers panel is open automatically.
6. **Climax:** a 2:00 Main demo (cap 2:30) and an unedited Capture proof, honest about every shortcut. The banner never left the screen: it sits on every surface the beats are filmed on, the Build view included, and no scrim ever dims it.

Failure: a take over 200 s, or with a second visible retry → discarded and re-shot from step 1.

### UJ-7 (placeholder)

Tier 2, gated: controls, look rule and loading state stay out of this contract until the Mon Nov 2 gate passes (FR-34). Voice help (FR-35) likewise stays out until scheduled.

## Demo Mode and Disclosure

- **Source of truth.** The client reads `GET /meta` once per page load (`{mode, guide, trickster, demo_timescale, cache, profile, disclosure, retention}`, AD-15). It renders `disclosure` as served, one line per Disclosure `[ASSUMPTION: the field carries the joined lines]`, and an empty `disclosure` means no banner. The client never composes or edits a Disclosure line itself. The Voice and Tone table lists which lines the server must emit for which settings.
- **Placement.** The Disclosure banner sits at the top edge of the Capture, Play and Completion screens, the Build view and the Hosted landing (FR-26). The Build view carries it because two Main demo beats (0:15 and 1:35) are filmed there. It is part of the layout grid and pushes everything below it down (`{spacing.disclosure-min}` per line). It never covers the Scene or a Hotspot, and it has no close control.
- **Scrims start below the banner.** The Greeting, the Completion sheet, the Card log and the Leave room confirmation dim the top bar and the body, never the banner, so a Disclosure stays legible under every overlay.
- **Coupled behavior.** While any Disclosure is active, the Triggers panel opens automatically (FR-16). The Completion screen keeps the banner.
- **Mode declared (NFR-12).** The top bar's plain mode indicator states the mode on every surface ("Local mode · Cache off · profile {name}" or "Hosted mode"), from `GET /meta`, so the finals fallbacks and the active profile are visible on camera. The Cache clear in the Capture proof happens outside the app, on camera; the indicator then shows "Cache off". When `cache` is on while the Timer is visible, the server adds the Cache Disclosure line.
- **Earlier builds (PRD UJ-6 step 4).** A stored Room replay, a Demo room or a Build served from the Cache shows "This room was built earlier, on {date}." in the banner. The architecture spine moves this statement to the Main demo and README only; this spine keeps it on screen as the PRD asks and raises the conflict in Open Items.
- **Honesty (NFR-12).** Demo settings change only timing and the Trickster source. The UI has no demo-only path that injects events, Rungs, Greetings, Cards or Build output. The Timer and Event log timestamps are never scaled (FR-24). The Scripted Trickster's Cards render exactly like live ones, and the Validator decides them (AD-15).
- **If `GET /meta` fails,** no surface renders (see Capture cold load). A missing Disclosure must never look like "no shortcuts in effect".

## Build View

- **Entry points:** the Capture screen once the Build is `done`, the Completion screen, the stored Room row (Local) `[ASSUMPTION for the row]`, and, in Hosted mode, each Demo room card's "How this room was built" and the Hosted landing's "How a room is built" (PRD §7 "Lead with the work": a judge reaches it without finishing a 15 to 25 minute Demo room). "Back" returns to the surface it was opened from. Reached at `#/build/<job_id>/view`. Open in both modes, with no Access code (AD-3).
- **Disclosure banner:** shown here like on every other surface, above the header.
- **Content** (FR-38), read from `GET /builds/<job_id>/view` unless noted: the header (Room built time `[ASSUMPTION: Schema v1 has no Room name]`, "Regenerations: n of {max}", {max} read from the Build's configured maximum: 2, or 1 under cut 7), the puzzle graph (Exit puzzle rightmost), mask overlays per photo with their labels, the BuildView JSON pane (collapsed), the Validator verdict table, Dry run rows ("skipped" under cut 4) and the Model table (per Build, from provenance). Below them, the fixed **In play** block, read from `GET /meta`: the Guide model and where it runs (Llama 3.2 3B on Ollama on the Mac in Local mode; "verbatim, no hint model" in Hosted mode), the Trickster source, and the four Wizard portraits generated once with muse-image-1.0. Several of these fields are not in AD-3's BuildView list `[NOTE FOR ARCHITECTURE, Open Items]`.
- **No solution reaches this surface.** No answer, no Clue-to-answer pairing and no Dry run answer is shown or fetched. Clues are not repeated here `[ASSUMPTION]`. The JSON pane shows only the solution-free BuildView as served.
- **Keyboard:** Tab moves through "Back", the graph nodes, the mask label chips, the JSON toggle, then the tables and the In play block. Tables are real `<table>` elements with header cells `[ASSUMPTION]`.
- **Main demo use:** the 0:15 beat (Capture time-lapse, masks, the puzzle graph and verification, and the JSON pane as the "puzzle JSON") and the 1:35 beat (Model table and In play block: which Meta model did what, the local Guide, what is cached) (§11.3) are filmed here. It fits at 1280 px with no horizontal scroll (`DESIGN.md` Layout).

## Hosted Mode Differences

| Area | Hosted behavior |
|---|---|
| Entry | The Hosted landing instead of the Capture screen; "Build another room" and "Leave room" return to it. The landing introduces the Council and links each Demo room's Build view |
| Disclosure | Always shows "Hosted mode: hints are shown as written; no hint model runs here.", plus the Trickster-source line when it is scripted or cut 1 (§13 Q11), plus the earlier-builds line on Demo rooms |
| Mode indicator | "Hosted mode" |
| Guide | Rungs verbatim with the same anatomy; no thinking state; the No-hint line is unchanged |
| Opening line | First-room welcome for every Session, because the client always sends a fresh Derived block; never a Greeting |
| Player profile | The browser may still record Room results locally (FR-20 is mode-agnostic), but nothing from it is sent `[ASSUMPTION]`; the Privacy line holds literally |
| Building | Access code checked before photo selection; `X-Access-Code` on `POST /builds`; 20-Build quota; `queued` state; a Build URL that resumes after the tab closes |
| Retention summary | The Hosted text: the Modal storage, Tue Nov 10 deletion and 24 h log lines replace the Local storage sentence |
| Failed Build retry | "Try again" states that it uses one of the remaining judge builds |
| Completion | A Judge room shows "Deleted Tue Nov 10"; a Demo room shows no deletion line |
| After deletion | The Judge room URL shows the Deleted Judge room notice |
| Stored Rooms list | Absent; Demo room cards take its place |
| Browsers | Any current desktop Chrome, Safari or Firefox at 1280 px or wider; the Narrow-screen message below 1024 px |

## Privacy and Retention

- **Retention summary and Privacy line** sit in the right column of the Capture screen, visible before any photo is chosen, in both modes (FR-6). They are never collapsed or truncated. The Privacy line is verbatim and survives cut 3.
- **Raw room photos** go only to the services the Retention summary names. The client sends them in exactly one place, `POST /builds`, and never anywhere else. Play renders photos only from `GET /rooms/<room_id>/photos/<i>` (AD-11).
- **Typed hint text** is discarded in the browser. Only a Hint request is sent (FR-14). No copy implies the Guide "read" what was typed.
- **The Player profile** (Room results and the Derived block) lives in IndexedDB under the `?profile=` name. A Session start carries only the Derived block (FR-20). There is no profile viewer, export or delete control in v1 `[ASSUMPTION]`.
- **The reminder about faces, documents and other people's belongings** sits in the right column of the Capture screen, after the Input requirement and the iPhone tip and before the Retention summary, visible before upload (FR-6, PRD §8 order; `DESIGN.md` Layout).
- **No third-party requests beyond the named services.** Fonts are self-hosted; the client calls only its own server.
- **Deletion copy** is plain: "Deleted Tue Nov 10" on a Judge room's Completion screen, and the Deleted Judge room notice afterwards (FR-33).

## Responsive & Platform

| Width | Behavior |
|---|---|
| 1440 px and up | Designed layout (`DESIGN.md` Layout & Spacing). |
| 1280 to 1439 px | Same layout; side column 360 px. |
| 1024 to 1279 px | Same layout; side column 340 px `[ASSUMPTION]`. Hosted support starts at 1280 px (A-15), so this band is best-effort. |
| Below 1024 px | The Narrow-screen message: heading "Keyframe needs a bigger screen", body "Keyframe plays on a laptop or desktop browser." `[ASSUMPTION for the heading]`. No horizontal scroll at any width. |

Pointer and keyboard only. Touch is not designed for: a touch device at 1024 px or wider gets the desktop layout as-is `[ASSUMPTION]`.

## Open Items

- `[NOTE FOR ARCHITECTURE]` The spine's HTTP surface has no listing route for stored Rooms (Local) or Demo room cards (Hosted). This spine assumes the browser records its own Builds locally; Demo rooms still need a route, or a list in `GET /meta`.
- `[NOTE FOR ARCHITECTURE]` FR-32 checks the Access code before photo selection and shows "n of 20 builds left", but no route checks a code or reports the remaining count without a `POST /builds`.
- `[NOTE FOR ARCHITECTURE]` The Mask preview needs per-Interactable polygons in `GET /builds/<job_id>` job state before the `room` artifact exists.
- `[NOTE FOR ARCHITECTURE]` AD-13 names `regen_exhausted`, which is not a typed error class. The UI keys on job status `needs_recapture`.
- `[NOTE FOR ARCHITECTURE]` `use_on` lock input needs a `puzzle_id`; when more than one `use_on` Puzzle is available, the client's choice is an assumption, or the server could resolve it from the target.
- `[NOTE FOR ARCHITECTURE]` The Build view link from a Demo room's Completion screen needs a seeded job record per Demo room.
- `[NOTE FOR UX]` Schema v1 has no Room name. Demo room cards need a name source (a seeding field or `GET /meta`); the Build view header and Local rows use the build time.
- `[NOTE FOR UX]` Capture → Play is automatic (§8), so the "How this room was built" link on the Capture screen's `done` state is visible only briefly in a live Build. The lasting paths are the Completion screen, the stored Room row and a reopened build URL.
- `[NOTE FOR UX]` The First-room welcome (and the Greeting) sits inside the T0-to-T1 window, so "Begin" is one click inside the Capture target and the Capture proof.
- `[NOTE FOR UX]` The Leave room confirmation and the Narrow-screen message have no journey. Confirm that guard states need none. (Both now have `DESIGN.md` component rows.)
- `[NOTE FOR UX]` Lock outcomes ("Not this", "Open") are not in the live region by the floor's letter. Decide whether the accessibility floor should widen.
- `[NOTE FOR ARCHITECTURE]` **Evidence and rule 5, before the Mon Oct 26 freeze.** The Evidence card shows `evidence.visible_attribute` verbatim, and rule 5 never checks evidence, so a `code` Puzzle's card could show the code itself (UJ-1 says the Clue points at the mug "without quoting the year"). Rule 9 bars tokens only in decoys, so a card that shows a token would always be the real one, breaking decoy secrecy (FR-19). Extend rule 5 to `evidence.visible_attribute`, so every displayed attribute says where to look and never holds a solution token. Until then, this spine's rule stands: an attribute that contains a solution token is never displayed.
- `[NOTE FOR ARCHITECTURE]` **Order buffer vs exploring.** AD-4 feeds every Hotspot click into the trailing order buffer, so with an `order` Puzzle available, looking around produces failed sequences and Wrong attempts, against the PRD's "never a click alone". Arm the buffer only after an explicit start in the Puzzle's entry, or judge only clicks on that Puzzle's candidate Hotspots. The UI already keeps the pips empty until the player engages.
- `[NOTE FOR ARCHITECTURE]` **Active puzzle.** The client cannot compute AD-4's Active puzzle (most recent lock input or attempted click) without solutions, yet `HintRequestEvent` needs a `puzzle_id` and the UI marks the Active puzzle. Expose `active_puzzle_id` in session state, or let the server resolve the `puzzle_id` of a Hint request.
- `[NOTE FOR ARCHITECTURE]` **Select-then-click posts no `click`.** This spine decides that the target click of a select-then-click posts only the `use_on` lock input, like a drop. AD-4 says "a click for every hotspot click"; confirm the exception.
- `[NOTE FOR ARCHITECTURE]` **Opening line.** No route returns the Greeting or First-room welcome, and no state says phrasing is under way, so the thinking state before a phrased Greeting cannot be driven. The `POST /sessions` response should carry the opening line, and session state a phrasing flag. AD-5's "template filled with the numbers" is realized by the persistence and never-asked branches in Voice and Tone.
- `[NOTE FOR ARCHITECTURE]` **Prompts carry the voice rules.** The Riddler author prompt carries the generated-line rules (Clue and Lore in the Riddler's voice; Rungs in the Guide's voice on the scaffold ladder; no tokens), and the `phrase` and `greet` prompts carry "reword, never add content" and the Greeting brief.
- `[NOTE FOR ARCHITECTURE]` **Disclosure lines the server must emit.** The earlier-builds line ("This room was built earlier, on {date}.") depends on the Room, but `GET /meta` is read once per page load; the server needs a per-Room Disclosure (for example `GET /meta?room_id=` or a `disclosure` field on the session and BuildView responses). The `cache: on` line applies while the Timer is visible.
- `[NOTE FOR ARCHITECTURE]` **Mode-specific Retention text.** `GET /meta` `retention` must be served per mode, the Hosted text replacing the Local storage sentence rather than appending to it.
- `[NOTE FOR ARCHITECTURE]` **BuildView fields beyond AD-3.** The UX shows mask labels, "where it ran" and cached or billed per model, the Build's configured regeneration maximum (`REGEN_MAX`; 1 under cut 7) and the build time; AD-3's BuildView lists none of these explicitly. The In play block reads `GET /meta` (`guide`, `trickster`) and needs the Guide model id and host there.
- `[NOTE FOR ARCHITECTURE]` **Deletion record.** The Deleted Judge room notice cannot be told apart from an unknown room unless the server keeps a record of deleted Judge rooms (ids only, no content).
- `[NOTE FOR UX]` **PRD conflict: earlier builds.** PRD UJ-6 step 4 has the Disclosure banner state earlier builds of the Room; the architecture spine moves that to the Main demo and README only. This spine keeps the banner line (PRD wins) and asks the spine to align through `bmad-correct-course`.
- `[NOTE FOR UX]` **Proposed Disclosure change (correct-course).** "Timings shown at n× speed." sits above the real-time Timer and implies the build time is faked (against CAP-8 and AD-10). Proposed: "Hint and Trickster timings run at n× speed; the build timer is real time." Until accepted, the PRD line stands.
- `[NOTE FOR UX]` **T1 and keyboard players.** T1 stays pointer-only, as the PRD Glossary defines it and as the Capture target and Capture proof measure it. A keyboard-only player's Timer therefore never freezes on focus. Whether T1 should also count the first keyboard focus on a Hotspot is a PRD question.
- `[NOTE FOR UX]` **Dry run under cut 4.** PRD FR-38 says the rows show "skipped"; SPEC CAP-14 says "absent". This spine follows the PRD ("skipped") and logs the conflict for `bmad-correct-course`.
- `[NOTE FOR UX]` **For the builder's confirmation** (choices made beyond the memlog decisions): the cool grey Disclosure strip, which departs from Lamplit warmth on purpose; the third type family (IBM Plex Mono) for numbers; the Council strip, now required in both modes (Hosted landing; Local Capture screen during the Build); the "full-bleed" Scene read as contained inside a mat and gilt frame with letterboxing, never cropped; the First-room welcome rewritten away from "Find what doesn't belong."; the Shortcut Card wording; and the No-hint line's added acknowledgement.
- `[NOTE FOR UX]` **Key-screen mocks pending.** The four mocks the builder chose (Play screen, Capture screen, Build view, Completion and greeting) are not rendered yet. They are named in the surface map and in `DESIGN.md` Components, and should be logged as pending in the memlog until they exist.
- §13 Q3 owns the final Retention summary wording. §13 Q11 decides whether the hosted Trickster Disclosure line appears.
