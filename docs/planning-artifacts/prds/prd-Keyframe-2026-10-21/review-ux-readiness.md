# UX Readiness Review — Keyframe PRD

Reviewer lens: downstream readiness for `bmad-ux`, which writes `DESIGN.md` (how Keyframe looks) and `EXPERIENCE.md` (how it behaves: IA, Voice and Tone, Component Patterns, State Patterns, Interaction Primitives, Accessibility Floor, Key Flows). Read against `prd.md` as of 2026-10-21, with `addendum.md`, the PRD and UX decision logs, and the four `reconcile-*.md` files for cross-checks. Neither `prd.md` nor `addendum.md` was edited.

## Overall verdict

**Not ready for `bmad-ux` as written. About a page of edits fixes it.** The journeys are the strongest part. All seven have a named protagonist, an entry state, numbered steps, a climax and a Capability → FR line, and UJ-2 and UJ-3 are good enough to become Key Flows almost as they stand. The PRD falls short on the rest of what EXPERIENCE.md needs:

- **IA (§8):** it lists surfaces by noun but never says where a lock is operated, where Evidence lives, how a player moves between surfaces, or what each wizard does on screen.
- **Aesthetic (§7):** it contradicts the visual and voice decisions the builder already recorded (Lamplit study, dark only, wry and playful, candlelit portraits).
- **States:** of the seven required states, two are fully specified (HEIC rejection, Ollama timeout fallback), three are named with no copy and no recovery (`needs_more_photos`, `needs_recapture`, build quota), and two are only partly covered (spend-cap refusal, skipped Card). Interaction feedback (Wrong attempt, order reset, lock pending, stuck after the near-answer) is not specified at all.

| Area | Verdict |
|---|---|
| User journeys (concreteness for Key Flows) | adequate |
| Information Architecture (surface closure per FR) | thin |
| Aesthetic, tone and wizard voice | broken (contradicts recorded decision) |
| Empty, loading, error and refusal states | thin |
| Accessibility and platform floor | thin (absent) |

Finding counts: 0 critical, 6 high, 11 medium, 8 low.

Several findings overlap with points already raised in `reconcile-decisions.md` (H1 on §7, L5), `reconcile-spine-schema.md` (H2 on Evidence cards, H3 on `loosen`, M3 on the Card types, M4 on the Greeting fallback, M5 on the input requirement, M6 on Build states, L7 on the no-hint line) and `review-rubric.md` (failed Builds, lock feedback, accessibility). They are restated here only where the UX contract needs something more, mainly placement, copy, transitions and recovery, and the fix text below is written so that one edit closes both reviews.

---

## 1. User journeys — adequate

**Checked:** each UJ for named protagonist, entry state, numbered path, climax, resolution, edge case, and whether screens, states and transitions can be derived from it.

| UJ | Protagonist | Entry | Path | Climax | Resolution | Edge case | Derivable screens / gaps |
|---|---|---|---|---|---|---|---|
| UJ-1 | Ana | yes | 4 steps | yes, but the wording risks a solution leak | yes, but play itself is a black box | HEIC, `needs_more_photos` | Capture screen yes. Missing: the Capture → Play transition, the mask preview surface (step 3), and the first Hotspot interaction that stops the timer. No `needs_recapture` or `failed` path |
| UJ-2 | Ana | yes | 4 steps | strong | yes | Ollama past 5 s | Hint area derivable. Missing: where the nudge appears and whether it interrupts, Wrong-attempt feedback, Rung history (step "rereads the direction Rung" implies Rungs persist), and what happens after the near-answer if still stuck |
| UJ-3 | Ana | yes | 4 steps | strong | yes | skipped Card | Card derivable in outline. Missing: the visible change an accepted `decoy` makes (no Evidence surface exists), the Card's placement and lifetime, how it is sequenced against the lock-open feedback, and copy for the other three edit types |
| UJ-4 | Ana | yes | 3 steps | emotional only | yes | **none** | Greeting derivable only if A-13 is confirmed. Missing: the path from Completion to Capture for room 2, the Greeting form when phrasing is unavailable, and the first-room (no profile) case |
| UJ-5 | Priya | yes | 4 steps | strong | yes | 21st Build | Hosted landing outlined. Missing: invalid Access code, queued Build (one container), closing the tab during a long Build and returning, the deletion notice, and the hosted Retention summary |
| UJ-6 | Luis | contradictory (fresh profiles vs room-2 Greeting; see rubric) | 4 steps | yes | yes | retake | Disclosure overlay derivable in content. Missing: placement and persistence while recording |
| UJ-7 | Ana | yes | 3 steps | yes | yes | **none** | Too thin to design against: no controls, no "look" rule (dwell time or crosshair), no loading state, no WebGL fallback, and no way to operate `code`, `order` or `use_on` in 3D |

### Findings
- **medium** UJ-4 and UJ-7 have no edge case, and UJ-1 and UJ-5 miss the edge cases that most change the screens (§2.3). *Fix:* add to UJ-4: "**Edge case:** Ana opens room 2 in a different browser; there is no Player profile, so no Greeting appears, the first-room welcome line shows instead, and the nudge threshold is 90 s." Add to UJ-5: "**Edge case:** a wrong Access code is refused inline with 'That code didn't work' and no upload starts; a Build queued behind another shows 'Waiting for the workshop' with its position." Add to UJ-1 edge cases: "after two failed Regenerations the Build ends `needs_recapture` and the Capture screen explains what to photograph differently." For UJ-7, either add "Mouse-look and WASD; a centred reticle; resting the reticle on an Interactable for 1 s counts as a `find` click; other Lock types open the same Wizard-notes input as Tier 1; if WebGL fails, the Tier 1 Scenes load" or mark UJ-7 "out of the UX contract until the Mon Nov 2 gate passes".
- **low** The UJ-1 climax "the first Clue names Ana's mug and a word printed on it" reads as the Clue quoting the code (§2.3 UJ-1). *Fix:* "the first Clue points at Ana's mug and what is printed on it, without quoting it."
- **low** UJ-1's resolution ("plays 4 to 6 Puzzles") collapses the whole play loop, so the Key Flow for core play must come from FR-11 and FR-12 alone, and neither one says where inputs live (see §2). *Fix:* add a step to UJ-1 between steps (4) and Climax: "(5) Ana hovers the mug, opens its Wizard-notes entry, types a code, sees 'not this' once, then opens it; the next Puzzle appears in the notes."

---

## 2. Information Architecture — thin

**Checked:** every FR that has a UI surface, mapped to a surface in §8 and to the states that surface needs. A surface "closes" when its contents, entry and exit, and states can be derived without inventing product decisions.

| FR / surface | In §8? | Closes? | What is missing |
|---|---|---|---|
| FR-1 photo picker | yes | partly | The input requirement is stated only on rejection (it should also show before upload); no preview grid, per-photo remove, or count; mixed sets (7 JPEG + 1 HEIC) undefined |
| FR-2/3 mask preview | **no** | no | UJ-1 step 3 shows "Masks appear over Ana's mug, lamp, and books", but §8 has no such element |
| FR-4 `needs_more_photos` | yes (name only) | no | No copy; unclear whether the photos are kept and the player can add more (at 10 photos they can only replace); timer behavior unstated |
| FR-5 timer and stage | yes | no | The timer stops at T1, "first Hotspot responding", which happens on the Play screen, yet §8 places the timer on the Capture screen only. Stage labels are deferred to A-11 although NFR-1 already lists the stages; no Regeneration label |
| FR-6 Retention summary | yes | partly | No Hosted-mode variant (Modal storage until Tue Nov 10); placement relative to the Upload button unstated |
| FR-10 `needs_recapture` | yes (name only) | no | No copy, no guidance on what to reshoot, and no difference from `needs_more_photos` as the player sees it |
| Build `failed`, `queued`, Spend cap | **no** | no | See §4 |
| FR-11 Scene, Thumbnail strip, Inventory | yes | partly | No empty Inventory; no Puzzle progress (n of N, Exit marked); hover-only Hotspots with no alternative |
| FR-11 Evidence | **no** | no | Schema v1 shows Evidence in play and a `decoy` adds a card, but no surface exists |
| FR-12 lock inputs | yes ("per Lock type") | **no** | Where a lock is operated is undefined: a Wizard-notes entry, a Hotspot popover, or a modal. Also undefined: how a cross-Scene `order` sequence shows progress, how a `use_on` drag crosses Scenes, the 3 to 6 character code length, and the 3 to 5 click order length |
| FR-13 Completion screen | yes | partly | Contents are time and Rungs only (Wrong attempts and per-Puzzle stats are recorded but not stated as shown); the label and destination of "entry to the next Room" are undefined; Hosted judges have no destination |
| FR-14 hint-request field | yes | partly | No "Ask for help" button besides the free-text field; no-hint line copy missing; active Puzzle undefined |
| FR-15/16 Hint area, Triggers panel | yes | partly | No Rung history per Puzzle; no phrasing wait state; Triggers panel default visibility (always on or toggle) undefined |
| FR-19 Cards | yes | no | Placement, lifetime (toast, inline or log), per-type copy, player-language reject reasons |
| FR-21 Greeting | yes (A-13) | partly | Form (interstitial or portrait line) undefined; verbatim template missing; first-room welcome missing |
| FR-23 portraits | via Wizard notes | partly | Which wizard appears where is undefined (only the Guide and Trickster have obvious surfaces) |
| FR-26 Disclosure overlay | yes | partly | Variants, placement and dismissibility undefined |
| FR-31/32 Hosted landing | yes | partly | Demo-room card contents, Access-code states, resumable Build URL, deletion notice |
| FR-33 deletion | no | no | No expired-Judge-room state |
| FR-35 voice | no | n/a | No mic control or permission states (unscheduled) |
| FR-37 Clue cards | yes | partly | Image may arrive after T1, so a loading or absent state is needed |
| FR-34 Tier 2 | no | n/a | No 3D view entry or photo/3D toggle |
| Navigation | **no** | no | No Local-mode home, no way to replay a stored Room, no resume after reload, no way to abandon a Room |

### Findings
- **high** Where a lock is operated is undefined, so the core Interaction Primitives and Component Patterns cannot be derived (§8 "lock inputs per Lock type", §4.3 FR-12). *Fix:* add to FR-12 (tag as an assumption if not yet decided): "Each available Puzzle has an entry in the Wizard notes holding its Clue, Lore, Evidence cards and lock input. `code`: a 3 to 6 character field with Submit. `order`: the entry shows 3 to 5 empty slots that fill as Hotspots are clicked in any Scene; a full non-matching sequence counts one Wrong attempt and clears the slots. `find`: a click on the target Hotspot while the Puzzle is available. `use_on`: drag an Inventory item onto a Hotspot, or select the item and then click the Hotspot (the Thumbnail strip stays usable while an item is selected, so the target may be in another Scene). A lock shows open only after the server confirms it."
- **high** Evidence has no surface, so an accepted `decoy` changes nothing the player can see (§8 Play screen, §4.3 FR-11, §3 Decoy; same root as `reconcile-spine-schema.md` H2). *Fix:* in §8 Play screen change "Wizard notes with portraits, Clues, Lore" to "Wizard notes with portraits, and per available Puzzle its Clue, Lore, Evidence cards (Interactable label, thumbnail crop, read attribute) and lock input". Add to FR-11: "After an accepted `decoy`, the new Evidence card is visually identical to the real one and appears in a stable order."
- **medium** The timer spans two surfaces, T1 is ambiguous, and the mask preview has no home (§8 Capture screen, §4.1 FR-5, §3 T1, §2.3 UJ-1 step 3). *Fix:* in §3 change T1 to "The first Hotspot on the Play screen showing its hover highlight". Add to §8: "The timer and the final stage stay pinned from the Capture screen into the Play screen until T1, then show the frozen T1 − T0." Replace A-11 in FR-5 with: "Stage labels follow NFR-1 in order: Reading your photos (Architect) · Finding objects (segmentation) · Writing puzzles (Riddler) · Testing the room (Dry run) · Setting the scene (Scene); a Regeneration shows 'Rewriting puzzles, attempt n of 2'." Add to §8 Capture screen: "A mask preview: as segmentation completes, each Interactable's clearest photo appears with its Hotspot outline and label."
- **medium** There is no navigation model between surfaces (§8). *Fix:* add a §8 entry "**Navigation:** Local mode opens on the Capture screen with a list of stored Rooms below it (replay starts a new Session). Capture → Play is automatic once the first Scene is ready. Play → Completion is automatic when the Exit puzzle opens. Completion → 'Build another room' returns to the Capture screen (Local) or the Hosted landing (Hosted). Reloading the Play screen restores the Session from the Event log. 'Leave room' on the Play screen asks for confirmation and records no Room result."
- **medium** Each wizard's on-screen role is unmapped, so DESIGN.md cannot place the four portraits (§3 Council, §8, §7 voices, A-10). *Fix:* add to §8: "**Wizard placement:** the Architect speaks the Build stages and the mask preview on the Capture screen; the Riddler signs each Puzzle's Clue and Lore in the Wizard notes; the Guide speaks Rungs, the no-hint line and the Greeting in the Hint area; the Trickster speaks every Card. Each line shows its wizard's portrait." Confirm and remove A-10.
- **medium** The Hosted landing and judge path are not specified enough to design (§8 Hosted landing, §4.10 FR-31 to FR-33). *Fix:* add to §8 Hosted landing: "Each Demo room card shows a cover photo, room name, Puzzle count and an expected 15 to 25 minutes. Access-code entry has these states: empty, checking, refused ('That code didn't work'), accepted (shows the Capture screen with 'n of 20 builds left'), and quota reached ('All 20 judge builds are used; the Demo rooms are still open'). An accepted Build has its own URL that survives closing the tab and resumes polling. A Judge room shows 'Deleted Tue Nov 10' on its Completion screen, and its URL afterwards shows 'This room was deleted on Tue Nov 10 as promised.'"
- **low** The Completion screen's contents and exits are thin (§8, §4.3 FR-13). *Fix:* add to FR-13: "The Completion screen shows elapsed time, Rungs used, Wrong attempts, and per-Puzzle time; active Disclosures stay visible; its one action is 'Build another room' (see Navigation)."

---

## 3. Aesthetic, tone and wizard voice — broken

**Checked:** whether §7 gives DESIGN.md (Brand & Style, Colors, Typography, Components) and EXPERIENCE.md (Voice and Tone) enough to design against, and whether it agrees with the decisions already recorded.

The PRD log records a user decision: "Lamplit study visual direction, dark only, wry and playful wizard voice, painted candlelit portraits; PRD section 7 follows these." The UX log records user decisions: "Lamplit study: warm dark chrome, parchment-toned cards and notes, serif headings; the UI frames the room photos like a wizard study", "dark only", "wry and playful across hints, greetings and cards; the Trickster especially has fun with the player", and "painted, candlelit oil-portrait style". §7 is still tagged A-16 "no visual references supplied". It says "Myst-style", "terse", and "the Trickster taunts". It never mentions dark only, parchment, serif headings or candlelit portraits. `bmad-ux` will read the PRD as a source, find the conflict with its own log, and have to stop and ask.

Beyond the conflict, the voice is described by adjective only. There are no sample lines per wizard and no rule for which messages are in character and which are plain, even though §7 already mixes both (in-world wizards, out-of-character Disclosure, plain Errors).

### Findings
- **high** §7 contradicts the recorded aesthetic and voice decisions (§7, §14 A-16; same as `reconcile-decisions.md` H1). *Fix:* replace §7's Scenes and wizards bullets with: "**Visual direction:** Lamplit study: warm dark chrome, parchment-toned cards and notes, serif headings; the UI frames the player's own photos like a wizard's study. Dark mode only. **Scenes:** the player's photos, full-bleed inside the study frame, Hotspots revealed on hover `[ASSUMPTION A-16b]`. **Wizard voice:** wry and playful in Rungs, Greetings and Cards, never condescending, one or two sentences. The Architect observes, the Riddler teases, the Guide encourages, the Trickster has the most fun with the player. **Portraits:** painted, candlelit oil-portrait style, one shared style for all four." Change Greeting to "wry, warm and specific about play style". Delete A-16 from §7 and §14. Add to FR-23: "Portraits share the §7 portrait style."
- **medium** The voice has no sample lines and no in-character versus plain rule (§7). *Fix:* add to §7: "**Register rule:** wizard lines (Rungs, no-hint line, Greeting, Cards, Build stages) are in character. System messages (format and count errors, `failed`, Spend cap, quota, Access code, deletion) are plain and out of character, with one optional in-character lead-in from the Architect. Disclosures are always plain. **Samples:** Architect: 'Eight photos. I count a lamp with opinions.' Riddler (Clue): 'The mug remembers a year it would rather forget.' Guide (nudge): 'The shelf has been very quiet. Suspiciously quiet.' Trickster (accepted): 'I've added a little something. Good luck telling which.' Trickster (rejected): 'The Validator says that wouldn't be fair. Spoilsport.' Greeting: 'Back again. Last time you held out long past my first nudge, so I'll wait a little longer this time.' No-hint line: 'Look around a little longer; I'll speak up if you stay stuck.'" Add to FR-7: "Clues, Lore and Rungs are written in the §7 voice, so a verbatim Rung reads in character."
- **low** Motion, sound and density are not stated, so DESIGN.md will either invent them or leave them out (§7). *Fix:* add to §7: "**Motion:** slow and warm (fades, a lamplight glow on Hotspot hover); none longer than 300 ms; respects reduced motion. **Sound:** none in v1. **Density:** designed for a 1440 × 900 MacBook viewport; the Scene takes most of the width, with the notes and Hint area in one side column."

---

## 4. Empty, loading, error and refusal states — thin

**Checked:** each named state for copy (or a tone rule plus intent), where it appears, what the player can do next, and what happens to the data. Then a sweep for states the FRs imply but never name.

| State | Named in | Copy | Placement | Recovery | Verdict |
|---|---|---|---|---|---|
| HEIC / format rejection | FR-1, UJ-1, §7, §8 | yes, but two strings ("6 to 10 JPEG photos" in FR-1; "Keyframe needs 6 to 10 JPEG photos" in §7) | implied at the picker | implied (choose again); mixed set undefined | adequate |
| Count out of range (<6, >10) | FR-1 | no | no | no | thin |
| `needs_more_photos` | FR-4, UJ-1, §8 | no | Capture screen | unclear (add or replace; the 10-photo cap) | thin |
| `needs_recapture` | FR-10, §8 | no | Capture screen | no guidance on what to reshoot | thin |
| `failed` (provider, timeout) | §3 only | no | no | no | missing |
| `queued` (Hosted, one container) | none (spine AD-9) | no | no | no | missing |
| Spend-cap refusal, in a Build | FR-28 ("player or Luis") | no | no | no | missing |
| Spend-cap refusal, in play | FR-19 (skipped Card) | no | Card | play continues | thin |
| Ollama timeout fallback | FR-17, UJ-2 | n/a (verbatim Rung) | Hint area | automatic | adequate, but no wait state for the 0 to 5 s |
| Skipped Trickster Card | FR-19, UJ-3 | no | Card | play continues | thin |
| Build quota exceeded | FR-32, UJ-5 | "quota message" only | no (after upload, or at code entry?) | no | thin |
| Invalid Access code | FR-32 ("refused") | no | no | no | thin |
| Wrong attempt / `order` reset | FR-12 (counted) | no | no | n/a | missing |
| Lock pending (server-confirmed) | none (spine AD-4) | no | no | n/a | missing |
| Stuck after the near-answer | none | no | no | no | missing (decision; see rubric) |
| No-hint line | FR-14 ("fixed no-hint line") | no | Hint area | n/a | thin |
| Empty Inventory | none | no | Inventory | n/a | missing |
| Portrait missing | FR-23 (placeholder art) | n/a | portraits | automatic | adequate |
| Clue card failed or not yet ready | FR-37 (no image) | n/a | beside Clue | automatic | thin (no loading state) |
| Mid-Session reload / network loss | §3 Event log only | no | no | no | missing |
| First room, no Player profile | none | no | Greeting slot | n/a | missing |
| Expired Judge room | FR-33 (deleted) | no | no | no | missing |
| Voice: mic denied, listening | none (FR-35 unscheduled) | no | no | no | missing (deferred) |
| Non-desktop or narrow viewport | none | no | no | no | missing |

### Findings
- **high** Capture-screen end states have no copy or recovery, and three Build states have no presence in the PRD at all (§8 Capture screen, §4.1 FR-4, §4.2 FR-10, §4.9 FR-28, §3 Build; extends `reconcile-spine-schema.md` M6 and the rubric's failed-Build finding). *Fix:* add to §8 Capture screen: "End states keep the uploaded photos visible and stop the timer:
  - **`needs_more_photos`:** 'I only found n objects I can build puzzles around. Add a few photos of shelves, tables or walls (up to 10 in all) and try again.' The photos are kept; 'Add photos' and 'Start over' controls.
  - **`needs_recapture`:** 'I couldn't build a room I'm sure you can solve from these photos. Try brighter, closer shots where labels and printed text are readable.' 'Start over' control.
  - **`failed`:** names the stage and cause class ('The puzzle writer didn't answer' / 'This took too long'), with a 'Try again' control that resumes from the last completed stage.
  - **Spend cap:** 'Keyframe has reached today's spending limit. Try again tomorrow.' No retry.
  - **`queued` (Hosted):** 'Another room is being built; yours starts next.'
  - **Build quota (Hosted):** shown at Access-code entry, before photo selection (see §2)."

  Change FR-28's second consequence to "A refused call ends a Build `failed` with the Spend-cap message, or shows a skipped Card in play (FR-19)."
- **high** Play-feedback states are unnamed: Wrong attempt, `order` reset, lock pending, lock open, `find` → Inventory, non-target click, empty Inventory, and stuck after the near-answer (§4.3 FR-12, §4.4 FR-15). *Fix:* add to FR-12:
  - "A Wrong attempt shakes the lock input, shows 'Not this' and the per-lock count."
  - "A non-matching `order` clears its slots after the same feedback."
  - "A submitted input shows a pending state until the server answers; the lock never opens optimistically."
  - "An opened lock plays a short open state, then the next Puzzle appears in the Wizard notes."
  - "A solved `find` moves its item into the Inventory with a visible transfer."
  - "A click on a Hotspot that is no current target shows its label only, with no penalty."
  - "An empty Inventory shows 'Nothing in your pockets yet.'"

  Add to FR-15 the decision the rubric asks for, either a reveal control or "[NON-GOAL for MVP] no reveal; after the near-answer the Hint area repeats it on request." The UX contract needs either branch stated.
- **high** Card states are under-specified (§4.5 FR-19, §3 Card; extends `reconcile-spine-schema.md` H3 and M3). *Fix:* add to FR-19:
  - "A Card appears in the Hint area after the lock-open state finishes, stays until dismissed, and is kept in a Card log the player can reopen."
  - "An accepted Card names the edit type in player words and shows its effect at once: 'A new clue has appeared' (`decoy`, never saying which is false); 'This lock now needs another opened first' (`merge`); 'The Guide is feeling generous' plus the next Rung (`loosen`); 'A door just opened early' (`shortcut`)."
  - "A rejected Card shows a plain one-line reason derived from the Validator rule, never the rule number alone and never a token."
  - "A skipped Card reads 'The Trickster is quiet this time' for both a provider error and the Spend cap; the cause goes only to the log."

  Settle `loosen` against FR-15 as `reconcile-spine-schema.md` H3 proposes.
- **medium** The Hint area's interaction and wait states are not specified (§8 Hint area, §4.3 FR-14, §4.4 FR-16, FR-17). *Fix:* add to §8 Hint area:
  - "An 'Ask the Guide' button sits beside the free-text field; both send one Hint request for the active Puzzle (the one most recently clicked or attempted)."
  - "While local phrasing runs (up to 5 s), the Guide portrait shows a thinking state; past 5 s the verbatim Rung replaces it silently."
  - "Each Puzzle's opened Rungs stay listed in its Wizard-notes entry for rereading."
  - "The no-hint line uses the §7 sample."
  - "The Triggers panel is collapsed by default, with an always-visible toggle, and opens automatically when a Disclosure is active (Main demo, Hosted mode)."
- **medium** The Greeting has no form for verbatim mode and no first-room counterpart (§4.6 FR-21, A-13; extends `reconcile-spine-schema.md` M4). *Fix:* confirm A-13 as: "The Greeting is a Guide line with portrait, shown over the first Scene before play starts, dismissed by 'Begin'." Add: "Without phrasing (Hosted mode, cut 3, or past 5 s) the Greeting is a fixed template in the §7 voice, filled from the Derived block. A player with no Room result sees a fixed first-room welcome instead: 'Welcome to your own room. Find what doesn't belong.'"
- **medium** Format and count errors use inconsistent copy, and mixed sets and the pre-upload statement are undefined (§4.1 FR-1, §7 Errors, §8; extends `reconcile-spine-schema.md` M5). *Fix:* make FR-1 and §7 use one string: "Keyframe needs 6 to 10 JPEG photos." Add to FR-1: "The Capture screen shows the requirement, with the iPhone Most Compatible tip, before any photo is chosen. A set containing any non-JPEG, or a count outside 6 to 10, is rejected as a whole at the picker before upload, with the offending files marked."
- **medium** The Disclosure overlay has no variants, placement or persistence rule (§8, §4.8 FR-26, §7 Disclosure copy). *Fix:* add to FR-26: "The Disclosure is a persistent plain-text banner at the top edge of every surface (Capture, Play, Completion, Hosted landing) whenever a trigger is active. It cannot be dismissed and never covers the Scene or Hotspots. Variants, joined when several apply: 'Timings shown at n× speed.' / 'Trickster proposals replayed from a recording; the Validator ran live.' / 'Trickster proposals were written in advance; the Validator ran live on each.' (cut 1) / 'Hosted mode: hints are shown as written; no hint model runs here.'"
- **low** The Clue card has no loading or absent state (§4.7 FR-37). *Fix:* add to FR-37: "Until its image is ready the Clue card shows a parchment placeholder of the same size; on failure the placeholder stays blank, so the layout never shifts. The image's alt text is the Clue."
- **low** Expired rooms, mid-Session reload and network loss are not stated (§4.10 FR-33, §3 Event log, §4.3). *Fix:* add to FR-11: "Reloading restores the Session from the Event log. If the server cannot be reached, inputs are disabled with 'Reconnecting…' and nothing is counted until it returns." Add to FR-33: "A deleted Judge room's URL shows 'This room was deleted on Tue Nov 10 as promised.'"

---

## 5. Accessibility and platform floor — thin

**Checked:** whether EXPERIENCE.md's required Accessibility Floor and Foundation (form factor) can be filled from the PRD.

The PRD has no accessibility statement. §7's hover-only Hotspot reveal and FR-12's drag-only `use_on` are both mouse-only patterns, and a dark-only parchment palette makes contrast a live question. Form factor is implied (Chrome on a Mac; desktop) but not closed for the hosted URL. A-15 says judges use desktop Chrome, while the UX log says "any desktop browser for the hosted judge URL". Neither says what a phone visitor sees.

### Findings
- **medium** No Accessibility Floor (§5, §7, §4.3 FR-12; extends the rubric's accessibility finding). *Fix:* add NFR-14: "Every Hotspot is reachable by Tab in reading order with a visible focus ring; Enter acts as a click. A 'Show all objects' toggle outlines every Hotspot. `use_on` also works by select-then-click. Text and controls meet WCAG AA contrast on the dark theme. Rungs, Cards and the Greeting are announced in a polite live region. Motion respects reduced motion." Or state the opposite as a `[NON-GOAL for MVP]` in §9 so the UX run records it as a decision.
- **low** Form factor for the hosted URL is open (§6.5 A-15, §8 Hosted landing). *Fix:* replace A-15 with: "Hosted mode supports current desktop Chrome, Safari and Firefox at 1280 px wide or more. Below 1024 px wide the Hosted landing shows 'Keyframe plays on a laptop or desktop browser' and the Demo-room list stays readable. Local mode is Chrome only." Add the matching line to NFR-10.
- **low** Voice (FR-35) has no surface or permission states (§4.12). *Fix:* add to FR-35: "When voice ships, a mic control beside 'Ask the Guide' has idle, listening, transcribing and permission-denied states; denied falls back to the text field with 'Microphone blocked; type instead.'" Or add "voice UI out of the UX contract until scheduled" to §10.2.

---

## Mechanical notes

- **Glossary drift that UX will copy verbatim:**
  - "Demo disclosure overlay" (§8) vs **Disclosure** (§3).
  - "hint-request field" (§8) vs **Hint area** (§3).
  - "capture timer" (FR-24, §3 Demo timescale) vs **T0**/**T1** and "timer" (FR-5).
  - "lock" (throughout) vs **Puzzle** and **Lock type**.

  Pick one name per component. Component names must be identical across both spines.
- **Unconfirmed assumptions on the UX critical path:** A-1 to A-7 (journeys), A-10 (Wizard notes), A-11 (stage labels; NFR-1 already answers it), A-12 (thumbnail order), A-13 (Greeting placement), A-16 (aesthetic; contradicted by the log), and A-17 (IA). Clear them in one pass before the UX run. A-11 and A-16 can be closed from existing sources without asking Luis.
- **Surface closure check:** Evidence cards, the mask preview, navigation, and the Card log are needed by an FR or a journey but have no surface. The Triggers panel has a surface but no stated audience or default visibility. Every other §8 surface has at least one journey landing on it.
- **Copy inventory UX will need:** about 25 fixed strings (errors, end states, no-hint line, first-room welcome, Greeting template, four Card types plus reject and skip, Disclosure variants, Access-code and quota states, deletion notice). The PRD holds 3 today ("6 to 10 JPEG photos", the Privacy line, one Disclosure example). The fixes above propose the rest as starting copy for Luis to accept or rewrite.
