---
title: "Keyframe Design"
name: Keyframe
description: Lamplit study. A warm, dark, desktop-web frame of parchment notes and candlelit wizard portraits around the player's own room photos. Dark theme only; vanilla TypeScript and three.js, no UI system.
status: draft
created: 2026-10-21
updated: 2026-10-21
sources:
  - ../../prds/prd-Keyframe-2026-10-21/prd.md
  - ../../../specs/spec-keyframe/SPEC.md
  - ../../architecture/architecture-Keyframe-2026-10-21/ARCHITECTURE-SPINE.md
colors:
  # Dark theme only. Every value below is [ASSUMPTION] in its exact hex, chosen
  # to carry the Lamplit study direction; contrast ratios are in the Colors section.
  # Study: walls, desk, frames
  canvas: '#14100C'
  chrome: '#1E1812'
  chrome-raised: '#2A2119'
  hairline: '#4A3C2C'
  gilt: '#B08A4E'
  scrim: '#0A0806CC'
  # Paper: cards and notes
  parchment: '#E8DBBE'
  parchment-shade: '#D8C7A2'
  parchment-rule: '#5A463040'
  ink: '#2A1D11'
  ink-muted: '#5A4630'
  # Text on dark
  text: '#F0E6D2'
  text-muted: '#B8A98E'
  # Lamplight
  lamp: '#E9A94B'
  lamp-strong: '#F4C470'
  lamp-ink: '#6E400C'
  on-lamp: '#1A1208'
  lamp-hover-fill: '#E9A94B1F'
  lamp-ink-hover-fill: '#6E400C1F'
  # Focus and hotspots
  focus-ring: '#FFD27A'
  focus-ring-inner: '#14100C'
  hotspot-outline: '#E9A94B'
  hotspot-halo: '#14100C'
  hotspot-glow: '#E9A94B59'
  hotspot-show-all: '#F4C470'
  # Lock and state feedback
  success: '#8CC48A'
  success-ink: '#275A2C'
  wrong: '#E58A6C'
  wrong-ink: '#87321B'
  pending: '{colors.text-muted}'
  pending-ink: '{colors.ink-muted}'
  # Plain-register messages
  warning-surface: '#3A2D12'
  warning-text: '#F2D488'
  warning-edge: '#C9A04A'
  error-surface: '#3D1B16'
  error-text: '#F29A88'
  error-edge: '#B8503E'
  disclosure-surface: '#23272C'
  disclosure-text: '#E4E8EC'
  disclosure-edge: '#3A4048'
  # Trickster Cards (aliases of the base tokens, named for their role)
  card-accepted-surface: '{colors.parchment}'
  card-accepted-edge: '{colors.success-ink}'
  card-rejected-surface: '{colors.parchment}'
  card-rejected-edge: '{colors.wrong-ink}'
  card-skipped-surface: '{colors.chrome-raised}'
  card-skipped-text: '{colors.text-muted}'
  card-skipped-edge: '{colors.hairline}'
  # Clue card slot (Tier 1.5, FR-37)
  clue-card-placeholder: '{colors.parchment-shade}'
  clue-card-placeholder-edge: '{colors.parchment-rule}'
  clue-card-blank: '{colors.parchment-shade}'
  # Build view (aliases except graph-edge)
  graph-node: '{colors.parchment}'
  graph-node-ink: '{colors.ink}'
  graph-node-exit: '{colors.lamp}'
  graph-edge: '#9C8766'
  graph-pass: '{colors.success}'
  graph-fail: '{colors.wrong}'
  graph-skipped: '{colors.text-muted}'
  mask-overlay-fill: '#E9A94B40'
  mask-overlay-stroke: '#E9A94B'
typography:
  # Self-hosted from web/dist (no third-party font request): EB Garamond
  # (headings and in-character lines), Source Sans 3 (plain body),
  # IBM Plex Mono (numbers). Families and sizes are [ASSUMPTION].
  display-lg:
    fontFamily: EB Garamond
    fontSize: 40px
    fontWeight: '500'
    lineHeight: '1.15'
    letterSpacing: -0.01em
  display-md:
    fontFamily: EB Garamond
    fontSize: 30px
    fontWeight: '500'
    lineHeight: '1.2'
  display-sm:
    fontFamily: EB Garamond
    fontSize: 22px
    fontWeight: '500'
    lineHeight: '1.3'
  wizard-line-lg:
    fontFamily: EB Garamond
    fontSize: 24px
    fontWeight: '400'
    lineHeight: '1.4'
  wizard-line:
    fontFamily: EB Garamond
    fontSize: 19px
    fontWeight: '400'
    lineHeight: '1.5'
  lore:
    fontFamily: EB Garamond
    fontSize: 17px
    fontWeight: '400'
    fontStyle: italic
    lineHeight: '1.5'
  body-md:
    fontFamily: Source Sans 3
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.5'
  body-sm:
    fontFamily: Source Sans 3
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.45'
  label:
    fontFamily: Source Sans 3
    fontSize: 13px
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: 0.02em
  caption:
    fontFamily: Source Sans 3
    fontSize: 12px
    fontWeight: '400'
    lineHeight: '1.4'
  mono-timer:
    fontFamily: IBM Plex Mono
    fontSize: 28px
    fontWeight: '500'
    lineHeight: '1'
  mono-code:
    fontFamily: IBM Plex Mono
    fontSize: 20px
    fontWeight: '500'
    lineHeight: '1'
    letterSpacing: 0.2em
  mono-sm:
    fontFamily: IBM Plex Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: '1.4'
rounded:
  none: 0px
  sm: 4px
  md: 8px
  lg: 12px
  full: 9999px
spacing:
  # 4 px base [ASSUMPTION]
  '1': 4px
  '2': 8px
  '3': 12px
  '4': 16px
  '5': 24px
  '6': 32px
  '7': 48px
  '8': 64px
  frame-margin: 24px
  column-gap: 24px
  side-column: 400px
  top-bar: 48px
  disclosure-min: 32px
  thumbnail-strip: 88px
  narrow-gutter: 16px
  hint-area-max: 320px
  triggers-panel-max: 160px
  notes-min: 280px
  status-strip: 32px
elevation:
  # [ASSUMPTION] values; the meaning of each level is in Elevation & Depth
  paper: '0 1px 0 #00000040, 0 6px 16px #00000059'
  overlay: '0 24px 64px #000000A6'
  lamp-glow: '0 0 16px #E9A94B40'
  vignette: 'inset 0 0 80px #000000A6'
components:
  button-primary:
    background: '{colors.lamp}'
    foreground: '{colors.on-lamp}'
    typography: '{typography.label}'
    height: 44px
    paddingX: '{spacing.5}'
    radius: '{rounded.md}'
    hoverShadow: '{elevation.lamp-glow}'
  button-secondary:
    background: transparent
    border: '1px solid {colors.lamp}'
    foreground: '{colors.lamp}'
    hoverFill: '{colors.lamp-hover-fill}'
    foregroundOnParchment: '{colors.lamp-ink}'
    borderOnParchment: '1px solid {colors.lamp-ink}'
    hoverFillOnParchment: '{colors.lamp-ink-hover-fill}'
    height: 40px
    radius: '{rounded.md}'
  focus-ring:
    outer: '2px solid {colors.focus-ring}'
    inner: '2px solid {colors.focus-ring-inner}'
    offset: 2px
  capture-dropzone:
    background: '{colors.chrome-raised}'
    border: '2px dashed {colors.hairline}'
    borderActive: '2px dashed {colors.lamp}'
    radius: '{rounded.lg}'
    minHeight: 320px
  photo-tray-thumb:
    width: 120px
    height: 90px
    radius: '{rounded.sm}'
    rejectedBorder: '2px solid {colors.wrong}'
  timer:
    typography: '{typography.mono-timer}'
    running: '{colors.text}'
    runningMark: '{colors.lamp}'
    stopped: '{colors.success}'
    endStatus: '{colors.text-muted}'
  mode-indicator:
    foreground: '{colors.text-muted}'
    typography: '{typography.body-sm}'
  stage-list-item:
    typography: '{typography.label}'
    architectLine: '{typography.wizard-line}'
    pending: '{colors.text-muted}'
    running: '{colors.lamp}'
    done: '{colors.success}'
    failed: '{colors.error-text}'
    duration: '{typography.mono-sm}'
  council-strip:
    portrait: 48px
    portraitLanding: 160px
    role: '{typography.body-sm}'
    voiceLine: '{typography.wizard-line}'
    foreground: '{colors.text}'
    secondary: '{colors.text-muted}'
  stored-room-row:
    background: '{colors.chrome}'
    thumb: 96px
    meta: '{typography.body-sm}'
    rowRule: '1px solid {colors.hairline}'
    radius: '{rounded.md}'
  status-strip:
    background: '{colors.warning-surface}'
    foreground: '{colors.text}'
    typography: '{typography.body-sm}'
    height: '{spacing.status-strip}'
  retention-summary:
    background: '{colors.chrome-raised}'
    foreground: '{colors.text-muted}'
    privacyLine: '{colors.text}'
    privacyLineType: '{typography.body-md}'
    radius: '{rounded.md}'
  error-banner:
    background: '{colors.error-surface}'
    edge: '4px solid {colors.error-edge}'
    heading: '{colors.error-text}'
    foreground: '{colors.text}'
    radius: '{rounded.md}'
  warning-banner:
    background: '{colors.warning-surface}'
    edge: '4px solid {colors.warning-edge}'
    heading: '{colors.warning-text}'
    foreground: '{colors.text}'
    radius: '{rounded.md}'
  scene-frame:
    background: '{colors.canvas}'
    rule: '1px solid {colors.gilt}'
    mat: '{spacing.3}'
    vignette: '{elevation.vignette}'
    photoRadius: '{rounded.sm}'
  hotspot:
    rest: none
    hoverStroke: '2px {colors.hotspot-outline}'
    hoverHalo: '1px {colors.hotspot-halo}'
    hoverFill: '{colors.hotspot-glow}'
    focusStroke: '{components.focus-ring.outer}'
    showAllStroke: '2px dashed {colors.hotspot-show-all}'
    transition: '150ms ease-out'
  hotspot-label-chip:
    background: '{colors.parchment}'
    foreground: '{colors.ink}'
    typography: '{typography.label}'
    radius: '{rounded.sm}'
  thumbnail:
    width: 96px
    height: 72px
    radius: '{rounded.sm}'
    current: '2px solid {colors.lamp}'
    hover: '2px solid {colors.lamp-strong}'
  inventory:
    background: '{colors.chrome-raised}'
    slot: 64px
    emptySlot: '1px dashed {colors.hairline}'
    selected: '2px solid {colors.lamp}'
    radius: '{rounded.md}'
  wizard-notes:
    background: '{colors.parchment}'
    foreground: '{colors.ink}'
    divider: '1px solid {colors.parchment-rule}'
    puzzleHeading: '{typography.display-sm}'
    padding: '{spacing.5}'
    minHeight: '{spacing.notes-min}'
    radius: '{rounded.lg}'
    shadow: '{elevation.paper}'
  wizard-portrait:
    sizes: '24px · 32px · 48px · 96px · 160px'
    ring: '2px solid {colors.gilt}'
    thinkingRing: '2px solid {colors.lamp}'
    arrivalGlow: '{elevation.lamp-glow}'
    placeholder: '{colors.chrome-raised}'
    radius: '{rounded.full}'
  hint-area:
    background: '{colors.chrome-raised}'
    foreground: '{colors.text}'
    radius: '{rounded.lg}'
    padding: '{spacing.4}'
    maxHeight: '{spacing.hint-area-max}'
    arrivalGlow: '{elevation.lamp-glow}'
  rung-line:
    typography: '{typography.wizard-line}'
    foreground: '{colors.text}'
    rungLabel: '{typography.label}'
    rungLabelColor: '{colors.lamp}'
  active-puzzle-marker:
    rule: '3px solid {colors.lamp-ink}'
    label: '{typography.label}'
    labelColor: '{colors.lamp-ink}'
  clue-card-slot:
    width: 112px
    height: 84px
    placeholder: '{colors.clue-card-placeholder}'
    placeholderEdge: '1px dashed {colors.clue-card-placeholder-edge}'
    blank: '{colors.clue-card-blank}'
    radius: '{rounded.sm}'
  hint-field:
    background: '{colors.chrome}'
    border: '1px solid {colors.hairline}'
    foreground: '{colors.text}'
    placeholder: '{colors.text-muted}'
    height: 44px
    radius: '{rounded.md}'
  triggers-panel:
    background: '{colors.chrome}'
    foreground: '{colors.text-muted}'
    numbers: '{typography.mono-sm}'
    maxHeight: '{spacing.triggers-panel-max}'
    radius: '{rounded.md}'
  code-field:
    background: '{colors.parchment-shade}'
    foreground: '{colors.ink}'
    typography: '{typography.mono-code}'
    width: 168px
    height: 44px
    radius: '{rounded.sm}'
  order-progress:
    pip: 10px
    empty: '1.5px solid {colors.ink-muted}'
    filled: '{colors.lamp-ink}'
    reset: '{colors.wrong-ink}'
  use-on-selected:
    itemRing: '2px solid {colors.lamp}'
    chipBackground: '{colors.parchment}'
    chipForeground: '{colors.ink}'
  chip-not-this:
    foreground: '{colors.wrong-ink}'
    border: '1px solid {colors.wrong-ink}'
    typography: '{typography.label}'
    radius: '{rounded.sm}'
  chip-pending:
    foreground: '{colors.pending-ink}'
    border: '1px dashed {colors.pending-ink}'
    typography: '{typography.label}'
    radius: '{rounded.sm}'
  chip-open:
    foreground: '{colors.success-ink}'
    border: '1px solid {colors.success-ink}'
    typography: '{typography.label}'
    radius: '{rounded.sm}'
  evidence-card:
    background: '{colors.parchment-shade}'
    thumb: 64px
    label: '{typography.label}'
    attribute: '{typography.body-sm}'
    foreground: '{colors.ink}'
    radius: '{rounded.md}'
  trickster-card-accepted:
    background: '{colors.card-accepted-surface}'
    edge: '4px solid {colors.card-accepted-edge}'
    foreground: '{colors.ink}'
    typography: '{typography.wizard-line}'
    radius: '{rounded.md}'
  trickster-card-rejected:
    background: '{colors.card-rejected-surface}'
    edge: '4px solid {colors.card-rejected-edge}'
    foreground: '{colors.ink}'
    reason: '{typography.body-sm}'
    radius: '{rounded.md}'
  trickster-card-skipped:
    background: '{colors.card-skipped-surface}'
    border: '1px dashed {colors.card-skipped-edge}'
    foreground: '{colors.card-skipped-text}'
    radius: '{rounded.md}'
  card-log:
    background: '{colors.chrome}'
    sentence: '{typography.wizard-line}'
    outcome: '{typography.label}'
    time: '{typography.mono-sm}'
    portrait: 24px
    width: 360px
    radius: '{rounded.lg}'
    shadow: '{elevation.overlay}'
  completion-sheet:
    background: '{colors.parchment}'
    foreground: '{colors.ink}'
    width: 720px
    heading: '{typography.display-lg}'
    guidePortrait: 48px
    guideLine: '{typography.wizard-line}'
    stats: '{typography.mono-timer}'
    statLabel: '{typography.label}'
    radius: '{rounded.lg}'
    shadow: '{elevation.overlay}'
  deletion-line:
    background: '{colors.chrome-raised}'
    foreground: '{colors.text}'
    typography: '{typography.body-sm}'
    radius: '{rounded.md}'
  greeting-overlay:
    scrim: '{colors.scrim}'
    background: '{colors.parchment}'
    line: '{typography.wizard-line-lg}'
    width: 560px
    portrait: 96px
    tip: '{typography.body-sm}'
    tipColor: '{colors.text-muted}'
    radius: '{rounded.lg}'
    shadow: '{elevation.overlay}'
  leave-room-confirmation:
    scrim: '{colors.scrim}'
    background: '{colors.chrome-raised}'
    foreground: '{colors.text}'
    heading: '{typography.display-sm}'
    body: '{typography.body-md}'
    width: 480px
    radius: '{rounded.lg}'
    shadow: '{elevation.overlay}'
  build-view-header:
    background: '{colors.chrome}'
    title: '{typography.display-md}'
    meta: '{typography.body-sm}'
    numbers: '{typography.mono-sm}'
  build-view-json:
    background: '{colors.chrome}'
    foreground: '{colors.text}'
    typography: '{typography.mono-sm}'
    maxHeight: 360px
    radius: '{rounded.md}'
  in-play-block:
    background: '{colors.chrome}'
    modelId: '{typography.mono-sm}'
    foreground: '{colors.text}'
    secondary: '{colors.text-muted}'
    portrait: 32px
  build-view-mask:
    fill: '{colors.mask-overlay-fill}'
    stroke: '2px {colors.mask-overlay-stroke}'
    halo: '1px {colors.hotspot-halo}'
  graph-node:
    background: '{colors.graph-node}'
    foreground: '{colors.graph-node-ink}'
    width: 168px
    height: 64px
    exitRing: '3px double {colors.graph-node-exit}'
    radius: '{rounded.md}'
  graph-edge:
    stroke: '1.5px {colors.graph-edge}'
    arrowhead: 8px
  verdict-table:
    background: '{colors.chrome}'
    rowRule: '1px solid {colors.hairline}'
    foreground: '{colors.text}'
    numbers: '{typography.mono-sm}'
    pass: '{colors.graph-pass}'
    fail: '{colors.graph-fail}'
    skipped: '{colors.graph-skipped}'
  model-table:
    background: '{colors.chrome}'
    modelId: '{typography.mono-sm}'
    foreground: '{colors.text}'
    secondary: '{colors.text-muted}'
  disclosure-banner:
    background: '{colors.disclosure-surface}'
    border: '1px solid {colors.disclosure-edge}'
    foreground: '{colors.disclosure-text}'
    typography: '{typography.body-sm}'
    minHeight: '{spacing.disclosure-min}'
    radius: '{rounded.none}'
  demo-room-card:
    background: '{colors.chrome-raised}'
    cover: '4:3'
    buildThumb: 96px
    title: '{typography.display-sm}'
    meta: '{typography.body-sm}'
    hoverShadow: '{elevation.lamp-glow}'
    radius: '{rounded.lg}'
  access-code-field:
    background: '{colors.chrome}'
    foreground: '{colors.text}'
    typography: '{typography.mono-code}'
    height: 44px
    radius: '{rounded.md}'
  narrow-screen-message:
    background: '{colors.chrome-raised}'
    foreground: '{colors.text}'
    maxWidth: 480px
    gutter: '{spacing.narrow-gutter}'
    radius: '{rounded.lg}'
---

## Brand & Style

Keyframe is a wizard's study lit by one lamp, and the player's own room hangs on its wall. The interface is the study: warm dark chrome for the walls and desk, parchment for anything a wizard has written down, gilt hairlines around anything worth framing. The player's photos are the most valuable thing in the room, so the UI frames them and never paints over them. Lead with what the room knows, never with photorealism (PRD §7): the design gives the most room and the clearest type to what the Architect read (object names, outlines, read attributes), and never enhances, relights or retouches a photo. The behavior rules for this principle are in EXPERIENCE.md Foundation.

**Two registers, one rule for headings.** The PRD §7 register rule splits every line into *in character* (Rungs, the No-hint line, the Greeting, the First-room welcome, Cards, Clues, Lore, Build stages as the Architect speaks them) or *plain* (format and count errors, `failed`, Spend cap, quota, Access code, deletion messages, every Disclosure). The design makes that split visible and enforceable:

- **Headings are serif everywhere** (the builder's "serif headings"), on plain and in-character surfaces alike. A heading never signals the register on its own.
- **The register is carried by the body face plus the portrait.** In-character lines are set in the serif body (`wizard-line`, `wizard-line-lg`, `lore`) and signed with the speaker's Wizard portrait. Plain lines are set in the sans (`body-md`, `body-sm`) and carry no portrait.
- **Plain messages never sit on parchment.** Errors, warnings, quota, Spend cap, Access code, deletion and privacy messages and every Disclosure sit on chrome, a banner or the Disclosure strip. **Plain labels and chips may sit on paper** in the sans: Rung names, Card outcome labels, the rejected Card's reason, the "Checking", "Not this" and "Open" chips, Puzzle headings' numbers, stat labels on the Completion sheet, and Hotspot and mask label chips.

A reader can tell at a glance whether a wizard or the product is speaking.

**The wizards' visual register.** The voice is wry and playful, never condescending, one or two sentences (PRD §7). The design supports it with restraint: short lines, generous leading, no exclamation styling, no emoji, no comic-book bubbles. Each wizard owns one surface (PRD §8 Wizard placement) and its portrait sits beside every line it speaks, so the joke is in the words and the face, not in the chrome:

- **Architect**, who observes: Build stages and the mask preview on the Capture screen.
- **Riddler**, who teases: signs each Clue and Lore in the Wizard notes.
- **Guide**, who encourages: Rungs, the No-hint line, the Greeting and the First-room welcome, in the Hint area, and the sign-off line on the Completion sheet.
- **Trickster**, who has the most fun with the player: every Card.

Each wizard is introduced by what it consumes and produces, then its voice (PRD §7), in the Council strip: on the Hosted landing, and on the Capture screen during a Local Build as each wizard's stage starts (EXPERIENCE.md Voice and Tone has the lines).

**Portrait art direction (Muse Image prompts).** The four Wizard portraits are generated once with `muse-image-1.0` (FR-23) and share one painted, candlelit oil-portrait style. Every prompt carries the same style block; only the subject line changes. [ASSUMPTION] for everything past the shared style:

- *Shared style block:* oil painting on canvas, visible brushwork, chiaroscuro lit by a single candle from camera left, warm umber, ochre and lamp-amber palette, near-black background close to `{colors.canvas}`, head and shoulders in three-quarter view, square 1:1 at 1024 px, no text, no lettering, no painted frame (the UI supplies the gilt ring), no resemblance to any real person.
- *Architect:* calm and attentive, a brass loupe raised to one eye.
- *Riddler:* a half-smile, a sealed folded note held between two fingers.
- *Guide:* kind and patient, a small lantern held low.
- *Trickster:* a sly grin, one eyebrow up, a playing card turned toward the viewer.
- Portraits are cropped to a circle in the UI, so faces sit in the center 70% of the frame. The placeholder art FR-23 allows is a `{colors.chrome-raised}` circle with the wizard's initial in `display-sm`, `{colors.gilt}`.

**Mood words:** lamplit, warm, quiet, wry. **Not:** neon, glassy, gamer HUD, horror, parchment-texture kitsch (paper is a flat tone, not a scanned texture).

Dark theme only (memlog decision). Desktop web, designed at 1440 x 900 (PRD §7). No sound in v1. Voice help (FR-35) and the walkable 3D room (FR-34, UJ-7) are out of this contract until scheduled; no tokens are reserved for them.

## Colors

The palette is three materials and one light. Contrast ratios are WCAG 2.x relative-luminance ratios, computed from the frontmatter hex values; AA needs 4.5:1 for body text and 3:1 for large text and non-text UI.

**The study (dark chrome).**

- **Canvas (`#14100C`)** is the wall behind everything: page background, the Scene frame's letterbox, overlay scrims (`{colors.scrim}` at 80%).
- **Chrome (`#1E1812`)** is the desk: top bar, side column ground, tables in the Build view, the hint field.
- **Chrome raised (`#2A2119`)** is a tray on the desk: the Hint area, Inventory, capture dropzone, Retention summary, Demo room cards, skipped Cards.
- **Hairline (`#4A3C2C`)** separates rows and outlines empty slots. Decorative only (1.65:1 on chrome); never the only cue for a state.
- **Gilt (`#B08A4E`)** is reserved for frames: the Scene frame rule and portrait rings. Never text, never a state.

**Paper (parchment).** Anything a wizard has written down: the Wizard notes, Evidence cards, Trickster Cards, the Greeting, the Completion sheet, Build view graph nodes. Plain-message surfaces (the narrow-screen message, the Leave room confirmation, the deletion line) are on `chrome-raised`, never on paper.

- **Parchment (`#E8DBBE`)** is the sheet; **parchment shade (`#D8C7A2`)** is a card or field inset on the sheet (Evidence cards, code field).
- **Ink (`#2A1D11`)** is text on paper; **ink muted (`#5A4630`)** is Lore, read attributes and secondary labels on paper.
- **Parchment rule (`#5A463040`)** divides Puzzle entries inside the notes.

**Text on dark.** **Text (`#F0E6D2`)** for everything readable on chrome; **text muted (`#B8A98E`)** for secondary lines, pending states and the Triggers panel.

**Lamplight.** **Lamp (`#E9A94B`)** is the single accent: the primary button, the Hotspot hover outline and glow, the current thumbnail, the running Timer mark, the current Rung label, the Guide's thinking ring, the Exit puzzle ring in the graph. **Lamp strong (`#F4C470`)** is lamp on hover and the "Show all objects" outline. **Lamp ink (`#6E400C`)** is the accent when it must sit on parchment (secondary button label and border, filled order pips, the Active puzzle marker). **Lamp hover fill (`#E9A94B1F`, 12%)** and **lamp-ink hover fill (`#6E400C1F`, 12%)** are the secondary button's hover fill on dark and on paper. Lamp is light, not decoration: it never fills a large area and never colors a plain-register message.

**Focus.** **Focus ring (`#FFD27A`)** with **focus ring inner (`#14100C`)** form a two-tone ring, so focus is visible on dark chrome, on parchment and on any photo.

**Hotspots.** **Hotspot outline (`#E9A94B`)** plus a 1 px **hotspot halo (`#14100C`)** outside it, so the outline holds at least 3:1 against one of its neighbors on any photo, light or dark. **Hotspot glow (`#E9A94B59`)** is the 35% fill under the pointer. **Hotspot show-all (`#F4C470`)** is the dashed outline the "Show all objects" toggle draws (NFR-14).

**State.** Each state has a light form for dark surfaces and an ink form for parchment:

- **Success / open:** `success` `#8CC48A` on dark, `success-ink` `#275A2C` on paper. Verdigris, not neon green.
- **Wrong attempt:** `wrong` `#E58A6C` on dark, `wrong-ink` `#87321B` on paper. Rust, deliberately softer than error: a Wrong attempt is play, not failure.
- **Pending:** `pending` (alias of `text-muted`) on dark, `pending-ink` (alias of `ink-muted`) on paper.
- **Warning (Spend cap, quota, queued):** `warning-surface` `#3A2D12`, `warning-text` `#F2D488`, `warning-edge` `#C9A04A`.
- **Error (format and count, `failed`, `needs_more_photos`, `needs_recapture`, refused Access code):** `error-surface` `#3D1B16`, `error-text` `#F29A88`, `error-edge` `#B8503E`.

**Disclosure.** **Disclosure surface (`#23272C`)**, **disclosure text (`#E4E8EC`)**, **disclosure edge (`#3A4048`)**: the only cool, grey surface in the product. It reads as outside the study on purpose, because Disclosures are always plain and out of character (PRD §7, FR-26) [ASSUMPTION: a departure from Lamplit warmth, listed for the builder's confirmation in EXPERIENCE.md Open Items].

**Cards.** Accepted and rejected Cards are parchment (`card-*-surface`, aliases of `parchment`) with a 4 px left edge in `success-ink` or `wrong-ink`; the edge is never the only cue, the Card also names its outcome in words. Skipped Cards drop off the paper entirely: `card-skipped-surface` (`chrome-raised`), `card-skipped-text` (`text-muted`), dashed `card-skipped-edge` (`hairline`).

**Clue card slot (Tier 1.5).** The placeholder is `clue-card-placeholder` (`parchment-shade`) with a dashed `clue-card-placeholder-edge`; a failed card is a flat `clue-card-blank` with no edge, so the two read differently and the layout never shifts (FR-37).

**Build view.** Graph nodes are parchment (`graph-node`, `graph-node-ink`); the Exit puzzle gets a lamp double ring (`graph-node-exit`); `requires` edges are `graph-edge` `#9C8766` on dark (the only Build view color that is not an alias); verdicts use `graph-pass` (`success`), `graph-fail` (`wrong`), `graph-skipped` (`text-muted`). Mask overlays use `mask-overlay-fill` (lamp at 25%) with a lamp stroke and the dark halo.

### Contrast (load-bearing pairs)

| Foreground | Background | Ratio | Use | AA |
|---|---|---|---|---|
| `text` #F0E6D2 | `canvas` #14100C | 15.29 | Text on the page | pass |
| `text` | `chrome` #1E1812 | 14.19 | Top bar, tables, hint field | pass |
| `text` | `chrome-raised` #2A2119 | 12.75 | Hint area, Rung line, Inventory | pass |
| `text-muted` #B8A98E | `canvas` | 8.21 | Secondary lines | pass |
| `text-muted` | `chrome` | 7.62 | Triggers panel, table secondary | pass |
| `text-muted` / `card-skipped-text` | `chrome-raised` / `card-skipped-surface` | 6.84 | Skipped Card, Retention summary body | pass |
| `ink` #2A1D11 | `parchment` #E8DBBE | 11.94 | Wizard notes, Cards, Greeting | pass |
| `ink` | `parchment-shade` #D8C7A2 | 9.83 | Evidence card, code field | pass |
| `ink-muted` #5A4630 | `parchment` | 6.50 | Lore, read attributes | pass |
| `ink-muted` | `parchment-shade` | 5.36 | Attribute inside an Evidence card | pass |
| `lamp` #E9A94B | `chrome` | 8.57 | Rung label, Timer mark, links on dark | pass |
| `lamp` | `chrome-raised` | 7.70 | Rung label in the Hint area | pass |
| `on-lamp` #1A1208 | `lamp` | 9.03 | Primary button label | pass |
| `lamp-ink` #6E400C | `parchment` | 6.37 | Secondary button on paper | pass |
| `lamp-ink` | `parchment-shade` | 5.25 | Filled order pips, Submit | pass |
| `lamp-ink` (1 px border) | `parchment` | 6.37 | Secondary button border on paper (non-text, 3:1) | pass |
| `lamp-ink` | `parchment` + `lamp-ink-hover-fill` (≈ #D9C8A9) | 5.32 | Secondary button label on paper, hovered | pass |
| `success` #8CC48A | `chrome` | 8.69 | Stopped Timer, stage done | pass |
| `success-ink` #275A2C | `parchment` | 5.92 | Open chip, accepted Card edge | pass |
| `success-ink` | `parchment-shade` | 4.88 | Open chip inside an inset | pass |
| `wrong` #E58A6C | `chrome-raised` | 6.15 | Rejected photo marker in the tray | pass |
| `wrong-ink` #87321B | `parchment` | 6.12 | "Not this" chip, rejected Card edge | pass |
| `wrong-ink` | `parchment-shade` | 5.04 | "Not this" next to the code field | pass |
| `pending-ink` #5A4630 | `parchment` | 6.50 | Pending chip | pass |
| `error-text` #F29A88 | `error-surface` #3D1B16 | 7.14 | Error banner heading | pass |
| `text` | `error-surface` | 12.40 | Error banner body | pass |
| `warning-text` #F2D488 | `warning-surface` #3A2D12 | 9.30 | Spend cap / quota heading | pass |
| `text` | `warning-surface` | 10.84 | Warning banner body | pass |
| `disclosure-text` #E4E8EC | `disclosure-surface` #23272C | 12.20 | Disclosure banner | pass |
| `graph-node-ink` | `graph-node` | 11.94 | Graph node labels | pass |
| `graph-fail` (= `wrong` #E58A6C) | `chrome` | 6.85 | Fail verdicts | pass |
| `text-muted` | `scrim` over the Scene (≈ #0A0806) | 8.67 | Tip under the First-room welcome card | pass |
| `graph-edge` #9C8766 | `chrome` | 5.08 | `requires` edges (non-text, 3:1) | pass |
| `focus-ring` #FFD27A | `chrome` | 12.35 | Focus on dark (non-text, 3:1) | pass |
| `focus-ring-inner` #14100C | `parchment` | 13.80 | Focus on paper (non-text, 3:1) | pass |
| `hotspot-outline` #E9A94B | `hotspot-halo` #14100C | 9.23 | Hotspot outline on any photo (non-text, 3:1) | pass |

Avoid: lamp on parchment (1.49:1, fails, for text and for borders; use `lamp-ink`), any state color as the only signal, gradients other than the Scene vignette, and any color drawn from the player's photos into the chrome.

## Typography

Three families, self-hosted as WOFF2 files in `web/dist` and served by the app itself, so the Capture screen makes no third-party request its Retention summary does not name, and the fonts load on a venue network with no internet [ASSUMPTION for the family choices; the third family, IBM Plex Mono, is listed for the builder's confirmation in EXPERIENCE.md Open Items]. The register rule shows in the body face; headings are serif everywhere (Brand & Style):

- **EB Garamond (serif): headings and the wizards.** `display-lg` (40 px) for the Completion heading, the Hosted landing title and the narrow-screen heading; `display-md` (30 px) for screen titles and the Build view header; `display-sm` (22 px) for panel headings, "Puzzle {n}" headings in the Wizard notes and Demo room names. `wizard-line` (19 px, line height 1.5) for every in-character line: Rungs, the No-hint line, Clues, Card sentences (in the Hint area and in the Card log), the Architect's stage lines, the Council strip's voice lines, the Guide's sign-off on the Completion sheet. `wizard-line-lg` (24 px) for the Greeting and First-room welcome. `lore` (17 px, italic in its token) for Lore only. Garamond's small x-height is why wizard lines never go below 17 px.
- **Source Sans 3 (sans): the product.** `body-md` (16 px) for plain copy: errors, the Retention summary, the Privacy line, Disclosures in long form, the Input requirement. `body-sm` (14 px) for the Disclosure banner, the mode indicator, table cells, Evidence card attributes, rejected-Card reasons and the Council strip's role lines. `label` (13 px, 600) for buttons, chips, Build stage names, Rung names ("Nudge", "Direction", "Near-answer"), Card outcome labels, mask-preview labels and stat labels. `caption` (12 px) is the floor, used only for thumbnail and Inventory captions.
- **IBM Plex Mono: numbers that matter.** `mono-timer` (28 px, tabular figures) for the Timer and the Completion stats; `mono-code` (20 px, tracked 0.2em) for the code field and the Access code field; `mono-sm` (13 px, tabular) for the Triggers panel seconds and counts, stage durations, Build view ids, Lock types, verdict numbers and the Model table's model ids.

Rules: sentence case everywhere; no all-caps labels; no italic outside Lore; numbers that change in place (Timer, counts) are always tabular so nothing jitters. Text never sits directly on a photo; labels over the Scene sit on a parchment chip.

## Layout & Spacing

The spacing scale is 4 px based: 4, 8, 12, 16, 24, 32, 48, 64 (`{spacing.1}` to `{spacing.8}`), plus named layout tokens. Tight pairs (portrait to its line, label to field) use 8; elements inside a panel use 12 to 16; panels sit 24 apart; screen sections 48 apart.

**The frame, 1440 x 900** [ASSUMPTION for every dimension; the split follows PRD §7]. From the top:

1. **Disclosure banner**, full width, `{spacing.disclosure-min}` (32 px) per line, present only when a Disclosure applies (FR-26). It is part of the grid and pushes everything down; it never overlays the Scene.
2. **Top bar**, `{spacing.top-bar}` (48 px), `{colors.chrome}`: the Keyframe wordmark (`display-sm`) left, followed by the mode indicator (`{components.mode-indicator}`, plain, for example "Local mode · Cache off · profile demo"); the Timer centered, in the same position on the Capture and Play screens so it reads as pinned across them (FR-5); the "Show all objects" toggle, the Card log button and "Leave room" right.
3. **Body**, inside `{spacing.frame-margin}` (24 px) page margins:
   - **Scene column**, everything left of the side column (about 968 px): the Scene frame filling the height, then a `{spacing.thumbnail-strip}` (88 px) row holding the Thumbnail strip (flexible width, left) and the Inventory (about 288 px, right). Inventory sits next to the Scene because `use_on` drags from it onto a Hotspot.
   - **Side column**, `{spacing.side-column}` (400 px), `{spacing.column-gap}` (24 px) from the Scene: the Wizard notes on top, filling and scrolling, never shorter than `{spacing.notes-min}` (280 px); the Hint area pinned below (about 280 px, growing upward when a Card or the open Triggers panel needs room, up to `{spacing.hint-area-max}` (320 px), past which it scrolls inside itself). The open Triggers panel is capped at `{spacing.triggers-panel-max}` (160 px) and scrolls. At most two Cards stack in the Hint area; older ones collapse into a "{n} more in the Card log" link. With two Disclosure lines at 900 px high, the Wizard notes still keep their minimum height [ASSUMPTION for every cap].
   - **Reconnecting strip:** while reconnecting, a `{components.status-strip}` (32 px) sits at the top of the Scene column and the Scene frame shrinks by the same height, so the strip never covers the photo or a Hotspot.

The Scene is "full-bleed" in the PRD §7 sense inside its frame: the photo fills the frame edge to edge on its limiting axis and is never cropped, so no Hotspot is ever off-screen [ASSUMPTION for the contain-not-crop reading, with the mat, gilt rule and letterboxing; listed for confirmation in EXPERIENCE.md Open Items]. A 4:3 landscape photo renders at about 900 x 676 with a Disclosure line present; a portrait photo letterboxes into the canvas with the vignette.

**1280 to 1439 px:** the side column narrows to 360 px; everything else scales. **1024 to 1279 px:** the same layout with the side column at 340 px [ASSUMPTION]. **Below 1024 px:** the narrow-screen message replaces the app (A-15).

**Capture screen.** Same top bar (Timer appears on Upload). Body: left, the capture dropzone and photo tray (about 880 px); right, a 400 px column with the Input requirement, the iPhone Most Compatible tip, the faces, documents and belongings reminder, and the Retention summary with the Privacy line, in that order top to bottom (PRD §8). During the Build the dropzone area becomes the Stage list (top, with the Architect portrait and the Architect's current stage line), then the Council strip (Local mode: each wizard appears as its stage starts), over the mask preview grid; the photos stay visible in a compact tray. Error and warning banners sit at the top of the left area, above the photos they refer to. Stored Rooms (Local mode) list below the fold as `{components.stored-room-row}` rows.

**Play screen.** The frame above.

**Build view.** Disclosure banner (when a Disclosure applies) and top bar as on every surface, then full width inside the page margins, no side column. Top: the `{components.build-view-header}` row with the Room's build time (Schema v1 has no Room name), "Regenerations: n of {max}" and a "Back" control. Then two columns: left two-thirds, the puzzle graph (laid out left to right, Exit puzzle rightmost) over the mask overlays grid (three photos across, 4:3), then the collapsed BuildView JSON pane; right third, stacked tables: Validator verdicts, Dry run rows, Model table, then the In play block. Every table fits without horizontal scroll at 1280 px.

**Hosted landing.** Disclosure banner, top bar without the Timer, then a 48 px title block with the "How a room is built" link. Below: the Council strip (four 160 px portraits across), then Demo room cards three across (left, about 968 px) and the Access-code panel in the 400 px right column, so Priya sees both paths at once (UJ-5).

**Completion screen, Greeting / First-room welcome:** centered parchment sheets over the dimmed Scene (see Components). **Every scrim starts below the Disclosure banner**: overlays dim the top bar and the body, never the banner, so a Disclosure stays legible under the Greeting, the Completion sheet, the Card log and the Leave room confirmation.

## Elevation & Depth

Depth is a desk under one lamp: paper lies on the desk, the desk sits against the wall, and the lamp makes things glow, never float.

- **Level 0, wall:** `{colors.canvas}`. No shadow.
- **Level 1, desk and trays:** `{colors.chrome}` and `{colors.chrome-raised}`, separated by tone, not shadow.
- **Level 2, paper:** parchment surfaces carry `{elevation.paper}`, so the sheet lifts a few millimeters off the desk. Cards on the notes add only its 1 px line.
- **Level 3, overlays:** the Greeting, Completion sheet, Card log and Leave room confirmation carry `{elevation.overlay}` over `{colors.scrim}`. The scrim starts below the Disclosure banner and never dims it.
- **Lamplight glow** (`{elevation.lamp-glow}`) is the only light effect and it means "this responds" or "this just spoke": the Hotspot hover glow, the primary button and Demo room card hover, and a single arrival glow on the Guide portrait ring and the Hint area when a Rung arrives without being asked for (one fade in and out, 300 ms in all). Waiting is never shown by glow or by a loop: the Guide's thinking state is a static lamp ring plus a "thinking" label. Plain-register surfaces (banners, Disclosures, errors) never glow.
- **Scene vignette:** `{elevation.vignette}` on the frame's mat only; the photo itself is never darkened, tinted, enhanced or filtered.

**Motion.** Slow and warm: fades and glows only, 150 ms for hover, 200 ms for state fades, 300 ms maximum for overlays entering and for the arrival glow; `ease-out` throughout; nothing slides, bounces, shakes or scales more than 2%. **Nothing loops:** the Guide's thinking state, the "Checking" chip and the running Timer's lamp dot are static. With reduced motion set, every transition becomes an instant change and the arrival glow becomes the lit ring held for 2 s with no animation (NFR-14).

## Shapes

Softened paper corners, framed pictures.

- `{rounded.sm}` (4 px): photos inside frames, thumbnails, the code field, chips, Hotspot label chips.
- `{rounded.md}` (8 px): buttons, fields, Evidence cards, Trickster Cards, banners, graph nodes.
- `{rounded.lg}` (12 px): sheets and trays: the Wizard notes, Hint area, Completion sheet, Greeting card, Demo room cards, the dropzone.
- `{rounded.full}`: Wizard portraits (circle with a gilt ring) and order pips only. No pill buttons.
- `{rounded.none}`: the Disclosure banner, which runs edge to edge.

Hotspots take the shape of their polygon; they are never rounded, boxed or simplified for looks (AD-11).

## Components

No UI system: each component below is built in vanilla TypeScript (Scenes and Hotspots in three.js, AD-11) from the tokens above. Behavior, copy and states in full live in EXPERIENCE.md; this section is the visual spec. Dimensions and placements not traced to the PRD are [ASSUMPTION].

**Key-screen mocks (pending).** The builder chose four mocks, rendered from these tokens: Play screen (`mocks/play-screen.png`), Capture screen (`mocks/capture-screen.png`), Build view (`mocks/build-view.png`), Completion and greeting (`mocks/completion-greeting.png`). None is rendered yet; each is linked from its subsection below once it exists. Until then these tables are the only visual spec, and where a mock and this file disagree, this file wins.

### Shared controls

| Component | Anatomy and size | Tokens | States |
|---|---|---|---|
| Primary button | Label only, 44 px high, 24 px side padding | `{components.button-primary}` | Rest lamp fill; hover `lamp-strong` + glow; focus two-tone ring; disabled 40% opacity, no glow |
| Secondary button | 40 px, 1 px lamp border | `{components.button-secondary}` | Hover fills `lamp-hover-fill`; on parchment the label and border are `lamp-ink` and hover fills `lamp-ink-hover-fill` (Code field Submit) |
| Focus ring | 2 px `focus-ring` outside 2 px `focus-ring-inner`, 2 px offset | `{components.focus-ring}` | On every focusable element, Hotspots included; never removed |
| Mode indicator | One plain line in the top bar after the wordmark, `body-sm` `text-muted`, built from `GET /meta` `mode`, `cache` and `profile` | `{components.mode-indicator}` | Local ("Local mode · Cache off · profile demo"); Hosted ("Hosted mode"); never hidden, never styled as a Disclosure |
| Status strip | 32 px plain strip, `body-sm`, no portrait, no glow | `{components.status-strip}` | Reconnecting (top of the Scene column, Scene frame shrinks to fit); server unreachable on cold load (centered in the page body, alone) |

### Capture screen

Mock: `mocks/capture-screen.png` (pending).

| Component | Anatomy and size | Tokens | States |
|---|---|---|---|
| Capture dropzone | Tray, at least 320 px high, centered picker button and the Input requirement line in `body-md` | `{components.capture-dropzone}` | Rest dashed hairline; drag-over dashed lamp; disabled during a Build |
| Photo tray | Grid of 120 x 90 thumbnails, 12 px gaps, in upload order, count line in `label`; before Upload each thumbnail has a 32 px remove control | `{components.photo-tray-thumb}` | Accepted; rejected file marked with a 2 px `wrong` border and a `label` naming why (FR-1), and still removable; kept visible on every end state (PRD §8) |
| Mask preview | Same grid, each tile an Interactable's clearest photo with its outline drawn as `build-view-mask`; its label on a parchment chip in `label` type (`{components.hotspot-label-chip}`), never at the caption floor | `{components.build-view-mask}`, `{components.hotspot-label-chip}` | Tiles fade in (200 ms) as segmentation completes |
| Timer | `mono-timer` digits in the top bar center, m:ss, with a 6 px lamp dot | `{components.timer}` | Running: `text` digits, static lamp dot (no blink); stopped at T1: frozen T1 − T0 in `success`; end status (`failed`, `needs_more_photos`, `needs_recapture`): frozen digits plus status in `text-muted` |
| Stage list | Architect portrait (48 px) with the Architect's current stage line beside it in `wizard-line` `text`; under it a vertical list of the five stage names (A-11) in `label`, each with a 12 px marker and a `mono-sm` duration | `{components.stage-list-item}` | Pending hollow `text-muted`; running filled `lamp`; done `success` with duration; failed `error-text`; the Architect's line changes as each stage starts (200 ms fade); Regeneration repeats the author, validate and dry run rows with "attempt n of {max}" in `label` |
| Council strip (Capture, Local mode) | Row of four 48 px portraits under the Stage list; under each, the role line (what it consumes and produces) in `body-sm` `text-muted` and one voice line in `wizard-line` | `{components.council-strip}`, `{components.wizard-portrait}` | Each wizard is drawn as its stage starts (200 ms fade): Architect with "Reading your photos", Riddler with "Writing puzzles", Guide and Trickster with "Setting the scene"; not drawn before a wizard's stage |
| Stored Room row (Local) | Row on chrome: 96 x 72 cover thumbnail, build date and time and Puzzle count in `body-sm`, "Play" (secondary) and "How it was built" (secondary) | `{components.stored-room-row}` | Rest; hover row ring `lamp`; focus ring; empty list: one `text-muted` line |
| Retention summary | Tray in the right column, on `chrome-raised` (never parchment): heading `display-sm`, the mode-specific text served by `GET /meta` in `body-sm`, naming every service photos and puzzle text go to (FR-6; raw room photos go nowhere else), then the Privacy line, "the player profile stays on your machine.", in `body-md` 600 `text` | `{components.retention-summary}` | Always fully expanded; never truncated, collapsed or set below `body-sm` |
| Error banner | Full width of the left area: heading (serif, like every heading), one plain sentence in `body-md`, actions (Choose photos again, Add photos, Start over, Try again) as secondary buttons | `{components.error-banner}` | Error variant for format and count (action "Choose photos again"), `failed` (with stage), `needs_more_photos`, `needs_recapture`; warning variant (`{components.warning-banner}`) for Spend cap (no retry action), `queued` and Build quota; no portrait |

### Play screen

Mock: `mocks/play-screen.png` (pending).

| Component | Anatomy and size | Tokens | States |
|---|---|---|---|
| Scene frame | Canvas ground, 12 px chrome mat, 1 px gilt rule, inner vignette; the photo contained inside at `rounded.sm` | `{components.scene-frame}` | Loading: mat only with a `text-muted` line; reconnecting: the status strip appears above the frame (the frame shrinks, nothing overlays the photo), the photo dims to 60% and inputs disable; play-through ended: the photo dims to 60% under a centered plain line on `chrome-raised` with "Start again" (secondary) |
| Hotspot | The Interactable's polygon(s) over the photo | `{components.hotspot}` | **Rest:** invisible, pointer cursor only. **Hover:** 2 px lamp outline, 1 px dark halo, 35% glow fill, 150 ms fade. **Focus:** the two-tone focus ring traced along the polygon plus the label chip. **Show all objects:** every Hotspot gets the 2 px dashed `hotspot-show-all` outline with halo, no fill, no labels. **Clicked non-target:** label chip only (FR-12). **Collected (`find` solved):** the hover glow shows, then fades out over 200 ms while the Inventory item fades in over the same 200 ms |
| Hotspot label chip | Parchment chip, `label` type, anchored above the polygon's top edge, 8 px offset | `{components.hotspot-label-chip}` | On keyboard focus: shown for as long as the Hotspot has focus; after a non-target click: fades out after 2 s or on pointer leave [ASSUMPTION] |
| Thumbnail strip | Row of 96 x 72 thumbnails, 8 px gaps, in upload order (A-12), horizontally scrollable inside its row only | `{components.thumbnail}` | Current 2 px lamp border; hover `lamp-strong`; others at 80% opacity; usable while a `use_on` item is selected |
| Inventory | Tray of 64 px slots; each item a 56 px crop with a `caption` label | `{components.inventory}` | Empty: one dashed slot and a `body-sm` `text-muted` line; item arriving fades in (200 ms) in step with its Hotspot's glow fading out; selected for `use_on`: 2 px lamp ring; dragging: item at 60% in place, a 64 px drag image with `{elevation.paper}` |
| Wizard notes | Parchment sheet, 24 px padding, one entry per available Puzzle separated by `parchment-rule`; each entry: a "Puzzle {n}" heading in `display-sm`; the Riddler portrait (32 px) beside the Clue (`wizard-line`); the Evidence cards directly under the Clue; Lore (`lore`, `ink-muted`); opened Rungs; lock input. Clue card slot (Tier 1.5, FR-37): a 112 x 84 px card beside the Clue, right-aligned, the Clue wrapping to its left [ASSUMPTION for the size], drawn only when the Room has Clue cards | `{components.wizard-notes}`, `{components.clue-card-slot}`, `{components.active-puzzle-marker}` | Newly available entry fades in; the Active puzzle's entry carries a 3 px `lamp-ink` left rule plus the word "Current" in `label` `lamp-ink` beside its heading (never color alone); open entry collapses to one line with the Open chip; hidden Puzzles are not drawn at all, except an entry an accepted Merge just hid, which leaves a one-line plain `label` placeholder in `ink-muted`. Clue card slot: placeholder (dashed edge) until ready; blank (flat, no edge) on failure; same size in every state |
| Clue card slot (Tier 1.5) | 112 x 84 px, `rounded.sm`, beside the Clue in its Puzzle entry (FR-37); drawn only when the Room has Clue cards | `{components.clue-card-slot}` | Placeholder: `clue-card-placeholder` fill with a 1 px dashed `clue-card-placeholder-edge`; ready: the image; blank (failed): flat `clue-card-blank`, no edge; same size in every state |
| Wizard portrait | Circle with a 2 px gilt ring at 24 (Card log), 32 (signature, In play block), 48 (Hint area, Cards, Stage list, Council strip on the Capture screen, Completion sign-off), 96 (Greeting) or 160 px (Hosted landing Council strip) | `{components.wizard-portrait}` | Normal; Guide thinking: static `lamp` ring plus a "thinking" `label` (no pulse, no loop); arrival: one `{elevation.lamp-glow}` fade in and out on the ring, 300 ms in all, when a Rung arrives unrequested (under reduced motion, the lit ring held 2 s, no animation); placeholder: initial on `chrome-raised` |
| Hint area | Tray pinned at the bottom of the side column, at most 320 px high, scrolling inside past that: the latest Rung line, then the hint field and "Ask the Guide" side by side, then the Triggers toggle | `{components.hint-area}` | Idle (after "Begin", the Greeting or First-room welcome sits here as the first Guide line until the first Rung); Guide thinking; Card present (at most two Cards stack above the Rung line, newest on top, older ones behind a "{n} more in the Card log" link); arrival glow on the tray edge with the portrait's, same timing |
| Rung line | Guide portrait (48 px) left; the label "Puzzle {n} · {Rung name}" in `label` `lamp`; the line in `wizard-line` `text`. The No-hint line uses the same anatomy with the label "Puzzle {n}" alone | `{components.rung-line}` | Arrives with a 200 ms fade; a repeated reply to a Hint request fades in again (200 ms) even when its words are unchanged; a phrased and a verbatim Rung look identical, and in Hosted mode the thinking state never shows (FR-17) |
| Hint field + Ask the Guide | 44 px field (flexible width) and a primary button | `{components.hint-field}`, `{components.button-primary}` | Rest; focus ring; sending: button shows `pending` label, field read-only |
| Triggers panel | Toggle row ("Triggers" with a `mono-sm` count); open: a list on chrome, at most 160 px high and scrolling, one row per Rung change, Rung name in `label`, causes in `mono-sm` ("Idle 92 s", "3 Wrong attempts", or the Card that loosened it) | `{components.triggers-panel}` | Collapsed by default; open (also automatic while a Disclosure is active, FR-16); under cut 5 the same list fills a second window |
| Code field | Inset on the Puzzle entry: `mono-code` field sized for 6 characters (168 x 44 px) and a secondary Submit | `{components.code-field}` | Rest; focus ring; pending (field read-only, Pending chip); wrong (Not this chip and count beside it, field keeps its value); open (Open chip, field removed) |
| Order click progress | A row of 3 to 5 pips (10 px) in the Puzzle entry, one per position in the sequence, with a visually hidden "{filled} of {length}" description | `{components.order-progress}` | Inactive until the player engages this order Puzzle (EXPERIENCE.md Interaction Primitives): pips stay empty and never flash; engaged: each acknowledged Hotspot click fills the next pip in `lamp-ink`; a completed non-matching sequence turns the pips `wrong-ink` for 300 ms, then empties them, with the Not this chip; pips never show which clicks were right |
| `use_on` drag | Inventory item dragged onto the Scene; the Hotspot under the pointer shows the hover state | `{components.inventory}`, `{components.hotspot}` | Dragging; over a Hotspot; dropped (Pending chip in the Puzzle entry) |
| `use_on` select-then-click | Selected item ringed in lamp; a parchment chip pinned to the top-left of the Scene frame names the item and offers Cancel | `{components.use-on-selected}` | Selected; Hotspot hover while selected; cleared (chip fades out) |
| Feedback chips | Outlined chip, `label` type, word first, never icon-only: "Not this" (with the per-lock count), pending (wording in EXPERIENCE.md), open ("Open") | `{components.chip-not-this}`, `{components.chip-pending}`, `{components.chip-open}` | Not this persists until the next input; pending shows a static ellipsis (no animation); open holds for its short open state, then the next Puzzle appears |
| Evidence card | Inset row directly under the Clue: 64 px thumbnail crop (`rounded.sm`), Interactable label (`label`, `ink`), read attribute (`body-sm`, `ink-muted`) describing where to look, never a solution token | `{components.evidence-card}` | One state only. Real and Decoy cards are pixel-identical and keep a stable order; a new card gets no highlight, badge or animation beyond the entry's ordinary fade (FR-11, FR-19) |
| Trickster card, accepted | Parchment card in the Hint area: Trickster portrait (48 px) beside the sentence in `wizard-line` (first), then the outcome label in `label` after it ("Accepted · Merge · Puzzle 3"), dismiss control (32 px hit area) | `{components.trickster-card-accepted}` | Enters after the lock-open state with a 200 ms fade; stays until dismissed; a Loosen Card's Rung also appears as a Rung line |
| Trickster card, rejected | Same anatomy, `wrong-ink` edge; the Trickster's sentence in `wizard-line`, then the outcome label, then the plain reason ("That change was refused. {fixed message}") in `body-sm` `ink` | `{components.trickster-card-rejected}` | As accepted; the reason is never styled in character |
| Trickster card, skipped | Off the paper: `chrome-raised`, dashed edge, portrait at 60% opacity, one `wizard-line` sentence in `card-skipped-text`, then the label "Skipped" | `{components.trickster-card-skipped}` | As accepted; same look for a provider error and the Spend cap |
| Card log | Popover from the top bar, 360 px wide, max 480 px high, scrolling: one row per Card with portrait (24 px), the sentence in `wizard-line`, then outcome label (`label`) and session time (`mono-sm`) | `{components.card-log}` | Empty: one `text-muted` line; open; closed |

### Completion, Greeting, Build view

Mocks: `mocks/completion-greeting.png` and `mocks/build-view.png` (pending).

| Component | Anatomy and size | Tokens | States |
|---|---|---|---|
| Completion screen | The last Scene dimmed under the scrim; a centered 720 px parchment sheet: heading `display-lg` ("The room is open."); the Guide's sign-off, a 48 px Guide portrait beside one `wizard-line` line; elapsed time, Rungs used and Wrong attempts in `mono-timer` with `label` stat labels; a per-Puzzle time table (`body-sm`, `mono-sm` numbers); "Build another room" (primary), a link to the Build view (secondary) | `{components.completion-sheet}` | Local; Hosted Judge room adds "Deleted Tue Nov 10" as a `{components.deletion-line}` strip on `chrome-raised` directly below the sheet, off the paper, plain; active Disclosures stay in the banner above, which the scrim never dims |
| Greeting / First-room welcome | Over the first Scene: scrim (below the Disclosure banner), a 560 px parchment card, Guide portrait (96 px), the line in `wizard-line-lg`, "Begin" (primary); First-room welcome only: a one-time plain tip under the card, on the scrim, in `body-sm` `text-muted` | `{components.greeting-overlay}` | Greeting (returning player, Local mode); First-room welcome (fresh Player profile; and always in Hosted mode, which sends a fresh Derived block, FR-20, FR-21, FR-31); same anatomy for both; enters with a 300 ms fade; Local Greeting being phrased: the card shows the Guide's static thinking ring and "thinking" label |
| Leave room confirmation | Over the Play screen: scrim (below the Disclosure banner), a 480 px `chrome-raised` card (plain, never parchment): heading `display-sm`, one `body-md` sentence, "Keep playing" (primary, focused) and "Leave room" (secondary) | `{components.leave-room-confirmation}` | Open; closed (Escape means "Keep playing"); enters with a 300 ms fade |
| Deleted Judge room notice | The page body with a centered 480 px `chrome-raised` card: heading `display-sm`, one plain `body-md` sentence, "Go to the demo rooms" (primary) | `{components.leave-room-confirmation}` (same card, no scrim) | Single state |
| Build view: header | Row on chrome: build time as the title (`display-md`), "Regenerations: n of {max}" with `mono-sm` numbers, "Back" (secondary) | `{components.build-view-header}` | Ready; not ready (header, then one plain `body-md` line and a secondary link to the Build's Capture screen, no panels); error (one plain line and "Try again") |
| Build view: mask overlays | Grid of the Room's photos, three across, each with every Interactable's mask filled and stroked and its label on a parchment chip in `label` type | `{components.build-view-mask}`, `{components.hotspot-label-chip}` | Box-rectangle Hotspots draw the same way as masks (AD-11) |
| Build view: puzzle graph | Nodes 168 x 64 px: Puzzle order number [ASSUMPTION] (`mono-sm`) and Lock type (`mono-sm`) on parchment; `requires` edges with 8 px arrowheads; Exit puzzle with the lamp double ring and an "Exit" `label`; a Dry run marker (pass, fail, skipped) in the node's corner | `{components.graph-node}`, `{components.graph-edge}` | Static; focusable nodes show the focus ring |
| Build view: Validator verdict table | One row per rule: rule number (`mono-sm`), rule name, verdict word with an 8 px marker in `graph-pass` or `graph-fail`, fixed message in `body-sm` | `{components.verdict-table}` | Pass; fail |
| Build view: Dry run row | One row per Puzzle: order number, Lock type, verdict word; the Regeneration count in the header row | `{components.verdict-table}` | Pass; fail; skipped (cut 4) in `graph-skipped` with "skipped" spelled out |
| Build view: Model table | Columns model id (`mono-sm`), where it ran, what it did, cached or billed; one row per model used in this Build | `{components.model-table}` | Cached and billed are words, never color alone |
| Build view: In play block | Fixed panel under the Model table, from `GET /meta`: the Guide (model id or "verbatim", where it runs), the Trickster source (live, scripted or cut 1), and the four Wizard portraits at 32 px with "generated once with muse-image-1.0" | `{components.in-play-block}` | Local; Hosted (Guide reads "verbatim, no hint model") |
| Build view: BuildView JSON | Collapsed pane under the mask overlays: a "Show the build JSON" toggle (secondary), then the `GET /builds/<job_id>/view` response as served, pretty-printed in `mono-sm`, max 360 px high, scrolling | `{components.build-view-json}` | Collapsed (default); open; it holds only the solution-free BuildView (AD-3) |

### Modes, disclosure, platform

| Component | Anatomy and size | Tokens | States |
|---|---|---|---|
| Disclosure banner | Full-width strip above the top bar, `body-sm` lines, each Disclosure on its own line; no icon, no close control | `{components.disclosure-banner}` | Absent when nothing applies; one or more lines (FR-26); identical on the Capture, Play and Completion screens, the Build view and the Hosted landing; never dimmed by a scrim |
| Hosted landing | Title block (`display-lg`) with a "How a room is built" link (secondary); the required Council strip of the four portraits at 160 px, each with its role line and one voice line [ASSUMPTION for the strip's layout]; Demo room cards; the Access-code panel | `{components.council-strip}`, `{components.demo-room-card}`, `{components.access-code-field}` | See the two rows below |
| Demo room card | 4:3 cover photo on top (`rounded.lg` top corners), name in `display-sm`, Puzzle count and "15 to 25 min" in `body-sm` `text-muted`; a footer row with a 96 px mask-and-graph thumbnail (the cover's mask overlay with the puzzle graph inset) and "How this room was built" (secondary) | `{components.demo-room-card}` | Rest; hover lamp ring and `{elevation.lamp-glow}`; focus ring on the card and, separately, on the Build view link |
| Access-code build | Panel in the right column: heading `display-sm`, a 44 px `mono-code` field and a primary button, a status line below in `body-sm` | `{components.access-code-field}` | Empty; checking (button `pending`); refused (error banner, compact); accepted (status line in `success`, "n of 20 builds left", then the Capture screen); quota reached (warning banner; Demo room cards stay active) |
| Narrow-screen message | Below 1024 px: the canvas with a centered `chrome-raised` card (plain, never parchment), max 480 px wide, 16 px side gutters, wordmark, heading `display-sm`, one plain sentence in `body-md` | `{components.narrow-screen-message}` | Single state; no horizontal scroll at any width |
| Server unreachable (cold load) | The page body empty except a centered `{components.status-strip}` line; no Disclosure banner, no Retention summary, no Scene | `{components.status-strip}` | Retrying; replaced by the surface once `GET /meta` answers |

## Do's and Don'ts

| Do | Don't |
|---|---|
| Frame the player's photos: gilt rule, mat, vignette on the mat | Tint, filter, crop or paint over a photo |
| Keep Hotspots invisible at rest; reveal them on hover, focus and "Show all objects" | Outline Hotspots at rest or simplify their polygons |
| Set in-character lines in the EB Garamond body styles, signed with the speaker's portrait; set every heading in the serif | Put a portrait or a serif body line on an error, a Disclosure, a quota or a deletion message |
| Keep plain messages on chrome, banners or the Disclosure strip; let plain labels and chips sit on paper in the sans | Put an error, warning, deletion, privacy or Disclosure message on parchment |
| Make Disclosures the one cool grey strip, always visible, never covering the Scene | Style a Disclosure in the study palette, give it a close control or overlay it on Hotspots |
| Keep real and Decoy Evidence cards pixel-identical in a stable order | Highlight, badge or animate a newly added Evidence card |
| Use lamp for the one thing that responds or is current | Fill large areas with lamp or use it on plain messages |
| Use `lamp-ink`, `success-ink` and `wrong-ink` on parchment | Put `lamp`, `success` or `wrong` on parchment (they fail AA there) |
| Pair every state color with a word ("Not this", "Open", "skipped") | Signal any state by color or icon alone |
| Show the two-tone focus ring on every focusable element | Remove focus outlines or rely on the hover glow for focus |
| Keep motion to fades and glows, 300 ms at most, instant under reduced motion; show waiting with a static lit ring and a word | Slide, bounce, shake on a Wrong attempt, or loop any animation (pulses, blinking dots, animated ellipses) |
| Let the Disclosure banner sit above every scrim, on every surface including the Build view | Dim, cover or hide the Disclosure banner under an overlay |
| Keep the Privacy line verbatim, full size, always visible on the Capture screen | Collapse the Retention summary or shorten the Privacy line |
| Make Hosted mode look like Local mode, with the First-room welcome and verbatim Rungs | Add a "verbatim" badge to Rungs or show a Greeting in Hosted mode |
| Keep Garamond at 17 px or larger | Set wizard lines small or in all caps |
