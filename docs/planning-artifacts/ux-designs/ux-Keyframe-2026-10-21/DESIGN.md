---
title: "Keyframe Design"
name: Keyframe
description: Lamplit study. A warm, dark, desktop-web frame of quiet chrome, parchment cards and candlelit wizard portraits around the player's own room photos. Dark theme only; vanilla TypeScript and three.js, no UI system.
status: final
created: 2026-10-21
updated: 2026-10-21
sources:
  - ./.memlog.md
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
  scrim-soft: '#0A080680'
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
  pending: '#B8A98E' # = text-muted
  pending-ink: '#5A4630' # = ink-muted
  # Plain-register messages
  warning-surface: '#3A2D12'
  warning-text: '#F2D488'
  warning-edge: '#C9A04A'
  error-surface: '#3D1B16'
  error-text: '#F29A88'
  error-edge: '#B8503E'
  disclosure-surface: '#1E1812' # = chrome
  disclosure-text: '#F0E6D2' # = text
  disclosure-edge: '#B08A4E' # = gilt
  # Role tokens below repeat a base token's hex (named in the comment) so every
  # color value stays a hex string; change the base and its role tokens together.
  # Trickster Cards
  card-accepted-surface: '#E8DBBE' # = parchment
  card-accepted-edge: '#275A2C' # = success-ink
  card-rejected-surface: '#E8DBBE' # = parchment
  card-rejected-edge: '#87321B' # = wrong-ink
  card-skipped-surface: '#2A2119' # = chrome-raised
  card-skipped-text: '#B8A98E' # = text-muted
  card-skipped-edge: '#4A3C2C' # = hairline
  # Clue card slot (Tier 1.5, FR-37)
  clue-card-placeholder: '#D8C7A2' # = parchment-shade
  clue-card-placeholder-edge: '#5A463040' # = parchment-rule
  clue-card-blank: '#D8C7A2' # = parchment-shade
  # Build view (graph-edge is the only one with its own hex)
  graph-node: '#E8DBBE' # = parchment
  graph-node-ink: '#2A1D11' # = ink
  graph-node-exit: '#E9A94B' # = lamp
  graph-edge: '#9C8766'
  graph-pass: '#8CC48A' # = success
  graph-fail: '#E58A6C' # = wrong
  graph-skipped: '#B8A98E' # = text-muted
  mask-overlay-fill: '#E9A94B40'
  mask-overlay-stroke: '#E9A94B'
typography:
  # Self-hosted from web/dist (no third-party font request): EB Garamond
  # (headings and in-character lines), Source Sans 3 (plain body),
  # IBM Plex Mono (numbers). Families confirmed by the builder Oct 21;
  # sizes are [ASSUMPTION].
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
    # fontStyle is a deliberate extension past the spec's typography keys;
    # Lore is the only italic style (Typography rules).
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
  # Deliberate extension: the spec's token table has no elevation group. Kept
  # as one group so components reference shadows by name instead of repeating
  # them. [ASSUMPTION] values; the meaning of each level is in Elevation & Depth
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
    pressedFill: '{colors.lamp-hover-fill}'
    pressedBorder: '2px solid {colors.lamp}'
    height: 40px
    radius: '{rounded.md}'
  button-quiet:
    # The top bar's Play screen controls only (owner decision Oct 29): a
    # secondary button that stays out of the lamp until it is used.
    background: transparent
    border: '1px solid {colors.hairline}'
    foreground: '{colors.text}'
    hoverForeground: '{colors.lamp-strong}'
    hoverBorder: '1px solid {colors.lamp}'
    hoverFill: '{colors.lamp-hover-fill}'
    pressedFill: '{colors.lamp-hover-fill}'
    pressedBorder: '2px solid {colors.lamp}'
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
    compactWidth: 96px
    compactHeight: 72px
    removeControl: 32px
    removeControlFill: '{colors.scrim}'
  timer:
    typography: '{typography.mono-timer}'
    label: '{typography.label}'
    labelColor: '{colors.text-muted}'
    running: '{colors.text}'
    runningMark: '{colors.lamp}'
    stopped: '{colors.success}'
    endStatus: '{colors.text-muted}'
  mode-indicator:
    foreground: '{colors.text-muted}'
    typography: '{typography.body-sm}'
  stage-list-item:
    background: '{colors.chrome-raised}'
    radius: '{rounded.lg}'
    introRule: '1px solid {colors.hairline}'
    typography: '{typography.label}'
    architectLine: '{typography.wizard-line}'
    pending: '{colors.text-muted}'
    running: '{colors.lamp}'
    done: '{colors.success}'
    failed: '{colors.error-text}'
    duration: '{typography.mono-sm}'
    model: '{typography.mono-sm}'
    result: '{typography.body-sm}'
    resultColor: '{colors.text}'
    sentBack: '{typography.body-sm}'
    introPortrait: 48px
    introName: '{typography.label}'
    introRole: '{typography.body-sm}'
    introRoleColor: '{colors.text-muted}'
    introVoiceLine: '{typography.wizard-line}'
    introVoiceColor: '{colors.text}'
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
    privacyLabel: '{typography.label}'
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
    openRule: '1px solid {colors.lamp}'
    openGlow: '{elevation.lamp-glow}'
  hotspot:
    rest: none
    hoverStroke: '3px {colors.hotspot-outline}'
    hoverHalo: '1px {colors.hotspot-halo}'
    hoverFill: '{colors.hotspot-glow}'
    hoverGlow: 'drop-shadow(0 0 4px {colors.hotspot-outline}) drop-shadow(0 0 12px {colors.hotspot-outline}) drop-shadow({elevation.lamp-glow})'
    pressedFill: '{colors.hotspot-outline}'
    focusStroke: '{components.focus-ring.outer}'
    showAllStroke: '2px dashed {colors.hotspot-show-all}'
    transition: '150ms ease-out'
    labelDwell: 400ms
    bloomFill: '{colors.hotspot-outline}'
    bloomGlow: 'drop-shadow(0 0 12px {colors.hotspot-outline}) drop-shadow({elevation.lamp-glow})'
    bloom: 300ms
  hotspot-label-chip:
    background: '{colors.parchment}'
    foreground: '{colors.ink}'
    typography: '{typography.label}'
    radius: '{rounded.sm}'
  feedback-line:
    background: '{colors.parchment}'
    foreground: '{colors.ink}'
    typography: '{typography.wizard-line}'
    portrait: 30px
    radius: '{rounded.md}'
    shadow: '{elevation.paper}'
    inset: 22px
    hold: 2500ms
  coach-pill:
    background: '{colors.chrome}'
    foreground: '{colors.text}'
    edge: '1px solid {colors.hairline}'
    typography: '{typography.body-sm}'
    hold: 15000ms
  walk-map:
    width: 184px
    background: '{colors.canvas}'
    edge: '1px solid {colors.hairline}'
    radius: '{rounded.lg}'
    currentDot: '{colors.lamp}'
    cone: '{colors.lamp}'
  turn-disc:
    size: 52px
    background: '{colors.chrome}'
    edge: '1px solid {colors.hairline}'
    hover: '1px solid {colors.lamp}'
  doorway-sign:
    background: 'linear-gradient(#C9A464, #9C7A43)'
    foreground: '{colors.on-lamp}'
    typography: '{typography.wizard-line}'
  inventory:
    item: 76px x 60px
    itemEdge: '1px solid {colors.gilt}'
    emptySlot: '1px dashed {colors.hairline}'
    selected: '2px solid {colors.lamp}'
    name: '{colors.text-muted}'
    caption: '{colors.text-muted}'
    radius: '{rounded.md}'
  riddle-note:
    background: '{colors.parchment}'
    foreground: '{colors.ink}'
    secondary: '{colors.ink-muted}'
    width: 300px to 400px
    clue: '{typography.wizard-line}'
    placeTag: '{colors.lamp-ink}'
    hint: '{colors.parchment-shade}'
    solved: '{colors.success-ink}'
    seal: '#9E3324'
    padding: '{spacing.4}'
    radius: '{rounded.lg}'
    shadow: '{elevation.paper}'
  wizard-portrait:
    sizes: '24px · 26px · 30px · 32px · 36px · 40px · 48px · 96px'
    ring: '2px solid {colors.gilt}'
    thinkingRing: '2px solid {colors.lamp}'
    thinkingLabelOnPaper: '{colors.pending-ink}'
    placeholder: '{colors.chrome-raised}'
    radius: '{rounded.full}'
  treasure-chest:
    gem: '{colors.lamp-strong}'
    spentGem: '1px solid {colors.hairline}'
    name: '{colors.text}'
    count: '{colors.text-muted}'
    dialog: '{colors.parchment}'
    dialogWidth: 340px
    dialogShadow: '{elevation.overlay}'
    bubble: '{colors.parchment}'
    button: '{colors.lamp-ink}'
  story-stage:
    scrim: 'linear-gradient(to top, #0A0806F0, #0A080610)'
    lightScrim: 'linear-gradient(to top, #0A0806D8, transparent 52%)'
    portrait: 'min(66vh, 600px), 3:4, gilt arch'
    box: '{colors.parchment}'
    boxWidth: 700px
    line: 25px serif
    namePlate: 'linear-gradient(#C9A464, #9C7A43)'
    button: '{colors.lamp-ink}'
  clue-card-slot:
    width: 112px
    height: 84px
    placeholder: '{colors.clue-card-placeholder}'
    placeholderEdge: '1px dashed {colors.clue-card-placeholder-edge}'
    blank: '{colors.clue-card-blank}'
    radius: '{rounded.sm}'
  triggers-panel:
    toggle: '{typography.body-sm}'
    toggleColor: '{colors.text-muted}'
    background: '{colors.chrome}'
    foreground: '{colors.text-muted}'
    newestRow: '{colors.text}'
    rows: '{typography.body-sm}'
    header: '{typography.body-sm}'
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
    selectedFill: '{colors.lamp-ink-hover-fill}'
    selectedEdge: '1px solid {colors.lamp-ink}'
  order-progress:
    pip: 10px
    empty: '1.5px solid {colors.text-muted}'
    filled: '{colors.lamp}'
    reset: '{colors.wrong}'
    startControl: '{components.button-secondary}'
  use-on-selected:
    itemRing: '2px solid {colors.lamp}'
    chipBackground: '{colors.parchment}'
    chipForeground: '{colors.ink}'
  chip-not-this:
    foreground: '{colors.wrong}'
    border: '1px solid {colors.wrong}'
    typography: '{typography.label}'
    radius: '{rounded.sm}'
  chip-pending:
    foreground: '{colors.pending}'
    border: '1px dashed {colors.pending}'
    typography: '{typography.label}'
    radius: '{rounded.sm}'
  chip-open:
    foreground: '{colors.success}'
    border: '1px solid {colors.success}'
    typography: '{typography.label}'
    radius: '{rounded.sm}'
    openLift: '{elevation.paper}'
  evidence-card:
    background: '{colors.parchment-shade}'
    thumb: 64px
    label: '{typography.label}'
    attribute: '{typography.body-sm}'
    note: '{typography.wizard-line}'
    foreground: '{colors.ink}'
    backgroundInNotes: '{colors.canvas}'
    foregroundInNotes: '{colors.text}'
    attributeInNotes: '{colors.text-muted}'
    radius: '{rounded.md}'
  trickster-card-accepted:
    background: '{colors.card-accepted-surface}'
    edge: '4px solid {colors.card-accepted-edge}'
    foreground: '{colors.ink}'
    typography: '{typography.wizard-line}'
    introName: '{typography.label}'
    introRole: '{typography.body-sm}'
    introRoleColor: '{colors.ink-muted}'
    radius: '{rounded.md}'
  trickster-card-rejected:
    background: '{colors.card-rejected-surface}'
    edge: '4px solid {colors.card-rejected-edge}'
    foreground: '{colors.ink}'
    proposed: '{typography.body-sm}'
    reason: '{typography.body-sm}'
    introName: '{typography.label}'
    introRole: '{typography.body-sm}'
    introRoleColor: '{colors.ink-muted}'
    radius: '{rounded.md}'
  trickster-card-skipped:
    background: '{colors.card-skipped-surface}'
    border: '1px dashed {colors.card-skipped-edge}'
    foreground: '{colors.card-skipped-text}'
    introName: '{typography.label}'
    introRole: '{typography.body-sm}'
    introRoleColor: '{colors.card-skipped-text}'
    radius: '{rounded.md}'
  card-log:
    scrim: '{colors.scrim}'
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
    width: 860px
    heading: 36px serif
    portrait: 40px
    line: '{typography.wizard-line}'
    stats: '{typography.mono-timer}'
    statLabel: '{typography.label}'
    statLabelColor: '{colors.ink-muted}'
    padding: 22px 26px
    radius: '{rounded.lg}'
    shadow: '{elevation.overlay}'
    scrim: '{colors.scrim-soft}'
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
    introName: '{typography.display-sm}'
    introRole: '{typography.body-sm}'
    introRoleColor: '{colors.ink-muted}'
    introVoiceLine: '{typography.wizard-line}'
    steps: '{typography.body-md}'
    stepsColor: '{colors.ink}'
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
    caption: '{typography.body-sm}'
    captionColor: '{colors.text-muted}'
    maxHeight: 360px
    radius: '{rounded.md}'
  in-play-block:
    background: '{colors.chrome}'
    modelId: '{typography.mono-sm}'
    foreground: '{colors.text}'
    secondary: '{colors.text-muted}'
    portrait: 32px
    roleLine: '{typography.body-sm}'
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
    exitLabel: '{colors.lamp-ink}'
    marker: 8px
    markerPass: '{colors.success-ink}'
    markerFail: '{colors.wrong-ink}'
    markerSkipped: '{colors.ink-muted}'
    radius: '{rounded.md}'
  graph-edge:
    stroke: '1.5px {colors.graph-edge}'
    arrowhead: 8px
  verdict-table:
    background: '{colors.chrome}'
    rowRule: '1px solid {colors.hairline}'
    foreground: '{colors.text}'
    numbers: '{typography.mono-sm}'
    caption: '{typography.body-sm}'
    captionColor: '{colors.text-muted}'
    pass: '{colors.graph-pass}'
    fail: '{colors.graph-fail}'
    skipped: '{colors.graph-skipped}'
  model-table:
    background: '{colors.chrome}'
    modelId: '{typography.mono-sm}'
    foreground: '{colors.text}'
    secondary: '{colors.text-muted}'
    whatItDid: '{typography.body-sm}'
    caption: '{typography.body-sm}'
    portrait: 24px
    roleLine: '{typography.body-sm}'
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
    portraits: 24px
    title: '{typography.display-sm}'
    meta: '{typography.body-sm}'
    hoverShadow: '{elevation.lamp-glow}'
    radius: '{rounded.lg}'
  chooser:
    background: '{colors.canvas}'
    face: '{colors.chrome}'
    frame: '{colors.gilt}'
    eyebrow: '{colors.lamp-strong}'
    title: '{colors.text}'
    line: '{colors.parchment}'
    prompt: '{colors.lamp-strong}'
    leadTag: '{colors.lamp-strong}'
    panelShadow: '{elevation.overlay}'
    radius: '{rounded.lg}'
    cardRatio: '0.64'
    minText: 14px
    minLine: 16px
    perspective: 1500px
    liftEase: 'cubic-bezier(.2,.8,.2,1)'
    lift: 520ms
    spin: 1150ms
    deal: 1500ms
    reducedFade: 160ms
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

Keyframe is a wizard's study lit by one lamp, and the player's own room hangs on its wall. The interface is the study: warm dark chrome for the walls and desk, parchment for the cards and pages a wizard hands over, and one gilt frame around the thing worth framing: on the Play screen, the Scene alone (reviewer feedback, Oct 29: the room image, the current riddle and the next action come first, so the trays around them are quiet). The player's photos are the most valuable thing in the room, so the UI frames them and never paints over them. Lead with what the room knows, never with photorealism (PRD §7): the design gives the most room and the clearest type to what the Architect read (object names, outlines, read attributes), and never enhances, relights or retouches a photo. The behavior rules for this principle are in EXPERIENCE.md Foundation.

**Two registers, one rule for headings.** The PRD §7 register rule splits every line into *in character* or *plain*; which lines fall on each side is listed in EXPERIENCE.md Voice and Tone (Register rule). The design makes that split visible and enforceable:

- **Headings are serif everywhere** (the builder's "serif headings"), on plain and in-character surfaces alike. A heading never signals the register on its own.
- **The register is carried by the body face plus the portrait.** In-character lines are set in the serif body (`wizard-line`, `wizard-line-lg`, `lore`) and signed with the speaker's Wizard portrait. Plain lines are set in the sans (`body-md`, `body-sm`) and carry no portrait.
- **Plain messages never sit on parchment**; they sit on chrome, a banner or the Disclosure strip. **Plain labels and chips may sit on paper** in the sans (the list is in EXPERIENCE.md Voice and Tone).

A reader can tell at a glance whether a wizard or the product is speaking.

**The wizards' visual register.** The voice is wry and playful, never condescending, one or two sentences (PRD §7). The design supports it with restraint: short lines, generous leading, no exclamation styling, no emoji, no comic-book bubbles. Each wizard owns one surface (PRD §8 Wizard placement) and its portrait sits beside every line it speaks, so the joke is in the words and the face, not in the chrome:

- **Architect**, who observes: Build stages and the mask preview on the Capture screen.
- **Riddler**, who teases: signs each Clue and Lore in the Wizard notes.
- **Guide**, who encourages: Rungs, the No-hint line, the Greeting and the First-room welcome, in the Hint area, and the sign-off line on the Completion sheet.
- **Trickster**, who has the most fun with the player: every Card.

Each wizard is introduced in place where it first works, never in a separate band, with one exception: the Hosted landing's cast, the four together at 96 px with a name and a four-word role each, the voice line fading in on hover and focus. Visually, every introduction has the same anatomy: a portrait, the wizard's name and role line (plain, in the sans; the role line names the model behind the wizard) and one voice line (in character, in the serif), warm and in the Lamplit register. Where each introduction sits, and its lines, are in EXPERIENCE.md Voice and Tone (Wizard introductions); the per-surface anatomy is in Components.

**Portrait art direction (Muse Image prompts).** The four Wizard portraits are generated once with `muse-image-1.0` (FR-23) and share one painted, candlelit oil-portrait style. Every prompt carries the same style block; only the subject line changes. [ASSUMPTION] for everything past the shared style:

- *Shared style block:* oil painting on canvas, visible brushwork, chiaroscuro lit by a single candle from camera left, warm umber, ochre and lamp-amber palette, near-black background close to `{colors.canvas}`, head and shoulders in three-quarter view, square 1:1 at 1024 px, no text, no lettering, no painted frame (the UI supplies the gilt ring), no resemblance to any real person.
- *Architect:* calm and attentive, a brass loupe raised to one eye.
- *Riddler:* a half-smile, a sealed folded note held between two fingers.
- *Guide:* kind and patient, a small lantern held low.
- *Trickster:* a sly grin, one eyebrow up, a playing card turned toward the viewer.
- Portraits are cropped to a circle in the UI, so faces sit in the center 70% of the frame. The placeholder art FR-23 allows is a `{colors.chrome-raised}` circle with the wizard's initial in `display-sm`, `{colors.gilt}`.

**Mood words:** lamplit, warm, quiet, wry. **Not:** neon, glassy, gamer HUD, horror, parchment-texture kitsch (paper is a flat tone, not a scanned texture).

Dark theme only (memlog decision). Desktop web, designed at 1440 x 900 (PRD §7). No sound in v1, except the intro's music, which starts only when the player turns it on (owner exception, Oct 29; Motion). Voice help (FR-35) and the walkable 3D room (FR-34, UJ-7) are out of this contract until scheduled; no tokens are reserved for them.

## Colors

The palette is three materials and one light. Contrast ratios are WCAG 2.x relative-luminance ratios, computed from the frontmatter hex values; AA needs 4.5:1 for body text and 3:1 for large text and non-text UI.

**The study (dark chrome).**

- **Canvas (`#14100C`)** is the wall behind everything: page background, the Scene frame's letterbox, overlay scrims (`{colors.scrim}` at 80%; the Completion sheet's `{colors.scrim-soft}` at 50%, so the exit photo shows brighter behind it).
- **Chrome (`#1E1812`)** is the desk: top bar, side column ground, tables in the Build view, the "How hints work" panel in the Card log.
- **Chrome raised (`#2A2119`)** is a tray on the desk: the Wizard notes, the Hint area, Inventory, capture dropzone, Retention summary, Demo room cards, skipped Cards. On the Play screen the three trays (Wizard notes, Hint area, Inventory) are flat, with a 1 px `hairline` edge and no shadow (reviewer feedback, Oct 29).
- **Hairline (`#4A3C2C`)** separates rows (the Puzzle entries in the Wizard notes among them), edges the Play screen's trays and outlines empty slots. Decorative only (1.65:1 on chrome); never the only cue for a state.
- **Gilt (`#B08A4E`)** is reserved for frames: the Scene frame rule, portrait rings and, in story mode, the doorway sign, the Story stage's arch and the pack's item edges. Never text, never a state.

**Paper (parchment).** The cards and pages a wizard hands over: Trickster Cards, the Greeting, the Completion sheet, the landing's Riddler sample page with its Evidence cards, Build view graph nodes, the feedback line and the chips over the Scene. The Wizard notes left paper on Oct 29 (reviewer feedback: a bright sheet beside the photo competed with it); they are a dark tray, their Evidence cards `canvas` insets, their text the light forms. Plain-message surfaces (the narrow-screen message, the Leave room confirmation, the deletion line) are on `chrome-raised`, never on paper.

- **Parchment (`#E8DBBE`)** is the sheet; **parchment shade (`#D8C7A2`)** is a card or field inset (the sample page's Evidence cards, the code field, which keeps its inset on the dark notes).
- **Ink (`#2A1D11`)** is text on paper; **ink muted (`#5A4630`)** is Lore, read attributes and secondary labels on paper.
- **Parchment rule (`#5A463040`)** divides rows on paper (the Completion sheet, the sample page) and is the dashed edge of a Clue card placeholder.

**Text on dark.** **Text (`#F0E6D2`)** for everything readable on chrome; **text muted (`#B8A98E`)** for secondary lines, pending states and "How hints work".

**Lamplight.** **Lamp (`#E9A94B`)** is the single accent: the primary button, the Hotspot hover outline and glow, the current thumbnail, the running Timer mark, the current Rung label, the Guide's thinking ring, the Exit puzzle ring in the graph. **Lamp strong (`#F4C470`)** is lamp on hover and the "Show all objects" outline. **Lamp ink (`#6E400C`)** is the accent when it must sit on parchment (secondary button label and border, the code field's selected edge). On the dark notes the Active puzzle marker and the filled order pips are `lamp`. **Lamp hover fill (`#E9A94B1F`, 12%)** and **lamp-ink hover fill (`#6E400C1F`, 12%)** are the secondary button's hover fill on dark and on paper. Lamp is light, not decoration: it never fills a large area and never colors a plain-register message.

**Focus.** **Focus ring (`#FFD27A`)** with **focus ring inner (`#14100C`)** form a two-tone ring, so focus is visible on dark chrome, on parchment and on any photo.

**Hotspots.** **Hotspot outline (`#E9A94B`)** carries a 1 px **hotspot halo (`#14100C`)** outside it, so the outline holds at least 3:1 against one of its neighbors on any photo, light or dark; under the pointer the whole reveal casts a lamp drop shadow (4 px and 12 px blurs of the outline color over `{elevation.lamp-glow}`), so the object is lit, not only traced, on a busy photo. **Hotspot glow (`#E9A94B59`)** is the 35% fill under the pointer, solid outline color while the Hotspot is pressed. **Hotspot show-all (`#F4C470`)** is the dashed outline the "Show all objects" toggle draws (NFR-14).

**State.** Each state has a light form for dark surfaces and an ink form for parchment:

- **Success / open:** `success` `#8CC48A` on dark, `success-ink` `#275A2C` on paper. Verdigris, not neon green.
- **Wrong attempt:** `wrong` `#E58A6C` on dark, `wrong-ink` `#87321B` on paper. Rust, deliberately softer than error: a Wrong attempt is play, not failure.
- **Pending:** `pending` (same hex as `text-muted`) on dark, `pending-ink` (same hex as `ink-muted`) on paper.
- **Warning (Spend cap, quota, queued):** `warning-surface` `#3A2D12`, `warning-text` `#F2D488`, `warning-edge` `#C9A04A`.
- **Error (format and count, `failed`, `needs_more_photos`, `needs_recapture`, refused Access code):** `error-surface` `#3D1B16`, `error-text` `#F29A88`, `error-edge` `#B8503E`.

**Disclosure.** **Disclosure surface (`#1E1812`, the same hex as `chrome`)**, **disclosure text (`#F0E6D2`, the same hex as `text`)**, **disclosure edge (`#B08A4E`, the same hex as `gilt`)**: the strip belongs to the study, a chrome band under a gilt hairline like the top bar's ground, with its lines in full `text` (14.19:1). Disclosures stay plain and out of character in their words and their sans type, never in a separate palette (PRD §7, FR-26). Owner decision Oct 29 retired the grey strip of Oct 21, which read as a break in the room.

**Cards.** Accepted and rejected Cards are parchment (`card-*-surface`, the same hex as `parchment`) with a 4 px left edge in `success-ink` or `wrong-ink`; the edge is never the only cue, the Card also names its outcome in words. Skipped Cards drop off the paper entirely: `card-skipped-surface` (`chrome-raised`), `card-skipped-text` (`text-muted`), dashed `card-skipped-edge` (`hairline`).

**Clue card slot (Tier 1.5).** The placeholder is `clue-card-placeholder` (`parchment-shade`) with a dashed `clue-card-placeholder-edge`; a failed card is a flat `clue-card-blank` with no edge, so the two read differently and the layout never shifts (FR-37).

**Build view.** Graph nodes are parchment (`graph-node`, `graph-node-ink`); the Exit puzzle gets a lamp double ring (`graph-node-exit`); `requires` edges are `graph-edge` `#9C8766` on dark (the only Build view color with its own hex; the others repeat a base token's hex); verdicts use `graph-pass` (`success`), `graph-fail` (`wrong`), `graph-skipped` (`text-muted`). Mask overlays use `mask-overlay-fill` (lamp at 25%) with a lamp stroke and the dark halo.

### Contrast (load-bearing pairs)

| Foreground | Background | Ratio | Use | AA |
|---|---|---|---|---|
| `text` #F0E6D2 | `canvas` #14100C | 15.29 | Text on the page; an Evidence card in the Wizard notes | pass |
| `text` | `chrome` #1E1812 | 14.19 | Top bar (the quiet buttons' labels at rest among it), tables, the newest "How hints work" row | pass |
| `text` | `chrome-raised` #2A2119 | 12.75 | Wizard notes, Hint area, Rung line, Inventory | pass |
| `text-muted` #B8A98E | `canvas` | 8.21 | Secondary lines; the read attribute of an Evidence card in the Wizard notes | pass |
| `text-muted` | `chrome` | 7.62 | "How hints work" panel, table secondary | pass |
| `text-muted` / `card-skipped-text` | `chrome-raised` / `card-skipped-surface` | 6.84 | Skipped Card, Retention summary body; Lore, evidence counts, the Pending chip and empty order pips in the Wizard notes | pass |
| `ink` #2A1D11 | `parchment` #E8DBBE | 11.94 | Cards, Greeting, the landing's sample page | pass |
| `ink` | `parchment-shade` #D8C7A2 | 9.83 | Evidence card on the sample page, code field | pass |
| `ink-muted` #5A4630 | `parchment` | 6.50 | Lore and read attributes on paper | pass |
| `ink-muted` | `parchment-shade` | 5.36 | Attribute inside an Evidence card on the sample page | pass |
| `lamp` #E9A94B | `chrome` | 8.57 | Rung label, Timer mark, links on dark | pass |
| `lamp` | `chrome-raised` | 7.70 | Rung label in the Hint area; the Active puzzle marker, filled order pips and the secondary buttons (Submit, the sequence control) in the Wizard notes | pass |
| `lamp` | `error-surface` | 7.49 | Secondary button actions in an error banner | pass |
| `lamp` | `warning-surface` | 6.55 | Secondary button actions in a warning banner | pass |
| `lamp-strong` #F4C470 | `chrome` | 10.86 | Hovered secondary button and thumbnail on dark | pass |
| `lamp-strong` #F4C470 | `chrome` + `lamp-hover-fill` (≈ #372A19) | 8.65 | Quiet button label hovered, focused or pressed (the top bar's controls) | pass |
| `on-lamp` #1A1208 | `lamp` | 9.03 | Primary button label | pass |
| `lamp-ink` #6E400C | `parchment` | 6.37 | Secondary button on paper | pass |
| `lamp-ink` | `parchment-shade` | 5.25 | Lamp ink on an inset (no Play screen use since the notes went dark, Oct 29) | pass |
| `lamp-ink` (1 px border) | `parchment` | 6.37 | Secondary button border on paper (non-text, 3:1) | pass |
| `lamp-ink` | `parchment` + `lamp-ink-hover-fill` (≈ #D9C8A9) | 5.32 | Secondary button label on paper, hovered | pass |
| `ink` | `parchment-shade` + `lamp-ink-hover-fill` (≈ #CBB790) | 8.36 | Code field value selected for retyping | pass |
| `lamp-ink` (1 px edge) | `parchment-shade` + `lamp-ink-hover-fill` | 4.46 | Edge of the selected code value (non-text, 3:1) | pass |
| `success` #8CC48A | `chrome` | 8.69 | Stopped Timer | pass |
| `success` | `chrome-raised` | 7.80 | Stage done marker, accepted Access code status line, Solved chip in the Wizard notes | pass |
| `success-ink` #275A2C | `parchment` | 5.92 | Accepted Card edge | pass |
| `success-ink` | `parchment-shade` | 4.88 | Success ink inside an inset | pass |
| `wrong` #E58A6C | `chrome-raised` | 6.15 | Rejected photo marker in the tray; "Not this" chip and reset order pips in the Wizard notes | pass |
| `wrong-ink` #87321B | `parchment` | 6.12 | Rejected Card edge | pass |
| `wrong-ink` | `parchment-shade` | 5.04 | Wrong ink inside an inset | pass |
| `pending-ink` #5A4630 | `parchment` | 6.50 | Pending label on paper (Guide thinking on the Greeting) | pass |
| `error-text` #F29A88 | `error-surface` #3D1B16 | 7.14 | Error banner heading | pass |
| `error-text` | `chrome-raised` | 7.33 | Failed stage row in the Stage list | pass |
| `text` | `error-surface` | 12.40 | Error banner body | pass |
| `warning-text` #F2D488 | `warning-surface` #3A2D12 | 9.30 | Spend cap / quota heading | pass |
| `text` | `warning-surface` | 10.84 | Warning banner body | pass |
| `disclosure-text` (= `text` #F0E6D2) | `disclosure-surface` (= `chrome` #1E1812) | 14.19 | Disclosure banner | pass |
| `graph-node-ink` | `graph-node` | 11.94 | Graph node labels | pass |
| `graph-fail` (= `wrong` #E58A6C) | `chrome` | 6.85 | Fail verdicts | pass |
| `text-muted` | `scrim` over the Scene (≈ #0A0806) | 8.67 | Tip under the First-room welcome card | pass |
| `graph-edge` #9C8766 | `chrome` | 5.08 | `requires` edges (non-text, 3:1) | pass |
| `focus-ring` #FFD27A | `chrome` | 12.35 | Focus on dark (non-text, 3:1) | pass |
| `focus-ring-inner` #14100C | `parchment` | 13.80 | Focus on paper (non-text, 3:1) | pass |
| `hotspot-outline` #E9A94B | `hotspot-halo` #14100C | 9.23 | Hotspot outline on any photo (non-text, 3:1) | pass |

Avoid: lamp on parchment (1.49:1, fails, for text and for borders; use `lamp-ink`), any state color as the only signal, gradients other than the Scene vignette (and the Hosted landing chooser's lamp light and gilt, the owner's exception in Motion), and any color drawn from the player's photos into the chrome.

## Typography

Three families, self-hosted as WOFF2 files in `web/dist` and served by the app itself, so the Capture screen makes no third-party request its Retention summary does not name, and the fonts load on a venue network with no internet. The builder confirmed the three families on Oct 21; sizes stay [ASSUMPTION]. The register shows in the body face; headings are serif everywhere (Brand & Style).

- **EB Garamond (serif): headings and the wizards.** `display-lg` (40 px) for the Completion heading and the Hosted landing title; `display-md` (30 px) for screen titles and the Build view header; `display-sm` (22 px) for panel headings, "Puzzle {n}" headings in the Wizard notes, Demo room names and the narrow-screen heading. `wizard-line` (19 px, line height 1.5) for every in-character line: Rungs, the No-hint line, Clues, Card sentences (in the Hint area and in the Card log), the Architect's stage lines, each wizard's introduction voice line, the Guide's sign-off on the Completion sheet. `wizard-line-lg` (24 px) for the Greeting and First-room welcome. `lore` (17 px, italic in its token) for Lore only. Garamond's small x-height is why wizard lines never go below 17 px.
- **Source Sans 3 (sans): the product.** `body-md` (16 px) for plain copy: errors, the Privacy line, Disclosures in long form, the Input requirement and the other plain lines in the Capture screen's right column. `body-sm` (14 px) for the Retention summary's served text, the Disclosure banner, the mode indicator, "How hints work" and its rows, table cells, Evidence card attributes, rejected-Card reasons and the wizards' role lines where they are introduced. `label` (13 px, 600) for buttons, chips, Build stage names, Rung names ("Nudge", "Direction", "Near-answer"), Card outcome labels, mask-preview labels and stat labels. `caption` (12 px) is the floor, used only for thumbnail and Inventory captions.
- **IBM Plex Mono: numbers that matter.** `mono-timer` (28 px, tabular figures) for the Timer and the Completion stats; `mono-code` (20 px, tracked 0.2em) for the code field and the Access code field (the Access code field tracks 0.1em, so a 10-character code fits the 168 px it has at 1024 px; replay Oct 29); `mono-sm` (13 px, tabular) for the numbers inside "How hints work" rows (the rows themselves are `body-sm`), stage durations and the model id on done Stage rows, Build view ids, Lock types, verdict numbers and the Model table's model ids.

Rules: sentence case everywhere; no all-caps labels; no italic outside Lore; numbers that change in place (Timer, counts) are always tabular so nothing jitters. Text never sits directly on a photo; labels over the Scene sit on a parchment chip.

## Layout & Spacing

The spacing scale is 4 px based: 4, 8, 12, 16, 24, 32, 48, 64 (`{spacing.1}` to `{spacing.8}`), plus named layout tokens. Tight pairs (portrait to its line, label to field) use 8; elements inside a panel use 12 to 16; panels sit 24 apart; screen sections 48 apart.

**The frame, 1440 x 900** [ASSUMPTION for every dimension; the split follows PRD §7]. 1440 x 900 is the app viewport, browser chrome excluded. [mockups/play-screen.html](mockups/play-screen.html) draws this frame mid-Session. From the top:

1. **Disclosure banner**, the full-width footer strip under the body, `{spacing.disclosure-min}` per line, present only when a Disclosure applies (FR-26). It is part of the grid, the last band of the frame (moved there from the top edge on Oct 28); the body keeps its full height above it, and it never overlays the Scene.
2. **Top bar**, `{spacing.top-bar}`, `{colors.chrome}`: the Keyframe wordmark (`display-sm`) left, a link to the start in `text`, never underlined at rest, underlined on hover, with the shared focus ring (owner report Oct 29), followed by the mode indicator (`{components.mode-indicator}`, plain, for example "Local mode · Cache off · profile demo · 1 room played"); the Timer with its plain label centered, in the same position on the Capture and Play screens so it reads as pinned across them (FR-5); the "Show all objects" toggle, the Card log button and "Leave room" right, as quiet buttons (`{components.button-quiet}`, owner decision Oct 29), so the hint button stays the one gold action. These three controls belong to the Play screen: they stay in place, inert, under its overlays and on the Completion screen; the Capture screen, the Build view and the Hosted landing leave the right side empty.
3. **Body**, inside `{spacing.frame-margin}` page margins:
   - **Scene column**, the whole width (story mode, owner decision Oct 29: the side column is gone): the Scene frame filling the height. Inside the frame: the photo you face at the frame's full height (less a 32 px gutter for its walls), its neighbouring views as walls either side, the doorway sign hanging from its top edge, the turn discs at the frame's edges 58% down, the walk map, "Where you are", 184 px at the top right (18 px down, 20 px in), the Riddle note pinned at the top left (18 px down, 20 px in, 300 to 400 px wide: wholly on the wall left of the photo at 1440 x 900, just over the photo's top-left corner at 1024 x 768), "Your pack" on the floor left of the photo and the Treasure chest on the floor right of it (each 22 px from the photo's edge, 26 px up, and never closer than 16 px to the frame's edge: where the side margin is narrower than the part, as beside a landscape photo, it stands over the photo's lower corner instead), and the feedback line or the coach pill at the photo's bottom. The Story stage covers the body below the top bar.
   - **Reconnecting strip:** while reconnecting, a `{components.status-strip}` sits at the top of the Scene column and the Scene frame shrinks by the same height, so the strip never covers the photo or a Hotspot. On the Capture screen the same strip sits at the top of the left area, above any banner.

The Scene is "full-bleed" in the PRD §7 sense inside its frame: the photo fills the frame edge to edge on its limiting axis and is never cropped, so no Hotspot is ever off-screen. The builder confirmed this contain-not-crop reading, with the mat, gilt rule and letterboxing, on Oct 21. A 4:3 landscape photo renders at about 900 x 676 with a Disclosure line present; a portrait photo letterboxes into the canvas with the vignette.

**1280 to 1439 px:** the side column (the Capture screen's) narrows to 360 px; everything else scales. **1024 to 1279 px:** the same layout with the side column at 340 px [ASSUMPTION]. The Play screen has no side column (story mode): its Riddle note narrows toward 300 px and overlaps the photo's top-left corner at 1024 px. **Below 1024 px:** the narrow-screen message replaces the app (A-15).

**Capture screen** (live Build, Empty and the HEIC refusal in [mockups/capture-screen.html](mockups/capture-screen.html)). Same top bar (Timer appears on Upload; no right-side controls). Body: left, the capture dropzone and photo tray (about 968 px, the width of the Play screen's Scene column); right, a 400 px column with the Input requirement (the verbatim term, the only place it stands alone), the iPhone Most Compatible tip, the faces, documents and belongings reminder, and the Retention summary with the Privacy line, in that order top to bottom (PRD §8). The first three are plain `body-md` `text` lines on the canvas, 16 px apart, with no tray; the Retention summary is the column's only tray. The dropzone carries the picker sentence, which uses the term inside a sentence. Upload (primary) sits left-aligned under the dropzone, or under the Photo tray once photos are chosen. During the Build the dropzone area becomes the Stage list, on its `chrome-raised` tray (top: the Architect's introduction row, then the stage rows, the "Writing puzzles" row carrying the Riddler's introduction once it starts), over the mask preview grid; the photos stay visible in a compact tray (96 x 72 thumbnails, count line kept). A done Build's actions ("Play this room" and "How this room was built") sit under the banner slot, above the Stage list, so the primary action is in view at 1024 x 768 without scrolling the stage history (changed Oct 29, decision record item 64). The layout is the same in both modes, except that Hosted mode adds two plain `body-sm` lines under the Stage list (the build's own link, and where the two-minute target is measured). Error and warning banners sit at the top of the left area, above the photos they refer to. Stored Rooms (Local) list below the fold as `{components.stored-room-row}` rows.

**Play screen.** The frame above; mock: [mockups/play-screen.html](mockups/play-screen.html) (contents listed under Components, Play screen).

**Build view** ([mockups/build-view.html](mockups/build-view.html)). The top bar (wordmark and mode indicator only) and, under the body, the Disclosure banner (when one applies) as on every surface; the body full width inside the page margins, with no side column. Top: the `{components.build-view-header}` row with the Room's name (`Room.name`, set on Demo rooms) or, when it has none, its build time; "Regenerations: n of {max}"; and a "Back" control. After a Regeneration the header carries one "sent back" line per failed attempt. Then two columns: left two-thirds, the puzzle graph (laid out left to right, Exit puzzle rightmost) over the mask overlays grid (three photos across, 4:3), then the collapsed BuildView JSON pane; right third, stacked: the Model table first, so it sits above the fold at 900 px, then the In play block, then the Validator verdict table and the Dry run rows. Every table fits without horizontal scroll from 1024 px: below 1280 px the Model table lays out fixed, its five columns at 19, 20, 17, 26 and 18 % of the width, and a word too long for its column breaks inside it. The right column runs past 900 px, so the page scrolls: the top bar stays pinned at the top of the viewport and the Disclosure footer at its foot, and only the body scrolls between them, so the banner never leaves the screen. The Build view is the only surface that scrolls this way.

**Hosted landing** (owner decision Oct 29: a hero-select chooser; the reference prototype and its build spec were judged before the build). Top bar without the Timer, the Disclosure banner as the footer, and between them the `{components.chooser}`, filling the scroll viewport exactly: the pitch (`display-lg` "An escape room built from your own photos." at `clamp(32px, 2.9vw, 52px)`, over the subline in `wizard-line` `parchment`), the stage, and a 48 px footer with the key hints (`body-sm` `parchment`, keys in 14 px mono chips) centred and "Watch the intro" then "Pause motion" (14 px) at the right end ("Watch the intro" added Oct 29 with the intro, Motion). On the stage three tall cards stand in a shallow arc on a static gilt floor ring with ticks on its front half, a lamp-lit plate under each card's foot, under the lamp cone with dust in the light; the static light (the lamp from above, the floor glow, the vignette) is painted once on the chooser's background. The cards are sized from the stage, height first: H = the stage height less 80 px (at least 360 px), W = 0.64 H, and no card wider than (width − 96 px) / 3.3, so the trio fills the stage from 1024 × 768 to 1920 × 1080 and still at 2560 × 1440 (about 281 × 468 px at 1024 × 768, 380 × 594 at 1440 × 900, 488 × 762 at 1920 × 1080); the card text scales with the card through `clamp()` and never drops below 14 px, the line and its meta never below 16 px (about 16 px at 1440 × 900, 21 px at 1920 × 1080). Every sentence on the chooser and its backs (the subline, the card lines, the voice lines, the fact chips, the hosts' roles, the step bodies, the code notes, the key hints) reads in `parchment` or `text` at 7:1 or better against its ground, a stepped-back card included; `text-muted` is left to true labels (reviewer feedback, owner decision Oct 29). The one shared back panel (a gilt-framed `chrome` sheet under `{elevation.overlay}`) is sized per card: Watch as wide as the demo video's aspect allows (at most 1300 px), Play 1180 px by up to 780 px, Build 1000 px by its content. Below the fold, in the same scroll and inside the 24 px page margins: the cast, the four Wizard portraits at 96 px four across (two across below 1440 px), each with its name in `label` and its four-word role in `body-sm` `text-muted`, the row lifting to `chrome` with the lamp glow on hover and focus while the voice line in `wizard-line` fades in where the name was; then a row two across: the Riddler's sample page on parchment ("Puzzle {n}", Evidence cards, the Clue beside the Riddler's 32 px portrait, the Lore) and "How a room is built" as three numbered steps in `body-sm`, the numbers in `mono-sm` lamp; then any further Demo room cards three across. The cast is the one band of large wizard portraits in the product; the Completion sheet's "Built by" row names the four again at 32 px. (Changed Oct 29 from the title screen with the attract frame, the clip under "How to play" and the right column.)

**Completion screen, Greeting / First-room welcome** ([mockups/completion-greeting.html](mockups/completion-greeting.html)): centered parchment sheets over the dimmed Scene (see Components). Their buttons ("Begin", the Completion actions) sit left-aligned under the content. **Every scrim starts below the top bar**: overlays dim the body only. The Disclosure banner and the top bar stay undimmed; the top bar is inert while an overlay is open (its controls take no input), so a Disclosure and the running Timer stay legible under the Greeting, the Completion sheet, the Card log and the Leave room confirmation.

## Elevation & Depth

Depth is a desk under one lamp: paper lies on the desk, the desk sits against the wall, and the lamp makes things glow, never float.

- **Level 0, wall:** `{colors.canvas}`. No shadow.
- **Level 1, desk and trays:** `{colors.chrome}` and `{colors.chrome-raised}`, separated by tone, not shadow.
- **Level 2, paper:** parchment surfaces carry `{elevation.paper}`, so the sheet lifts a few millimeters off the desk. Cards on the notes add only the 1 px line of `{elevation.paper}`.
- **Level 3, overlays:** the Greeting, Completion sheet, Card log and Leave room confirmation carry `{elevation.overlay}` over `{colors.scrim}`, which starts below the top bar (Layout & Spacing).
- **Lamplight glow** (`{elevation.lamp-glow}`) is the only light effect; it means "this responds" or "this just spoke": the Hotspot hover glow, the primary button and Demo room card hover, the Hosted landing chooser's lamp rim on the card brought forward, a single arrival glow on the Guide portrait ring and the Hint area when a Rung arrives without being asked for (one fade in and out, 300 ms in all), and the unlock moment: on a lock opening, the solved target's Hotspot blooms (its polygon filled solid lamp under the lamp drop shadow) while the Scene frame's gilt rule turns lamp under the glow, each one fade in and out, 300 ms in all, and the Solved chip enters lifted on `{elevation.paper}`; a newly collected Inventory item's well carries the same glow once as it fades in. Waiting never glows (Motion), with one exception: the Guide pulse, the Guide's ring lit (lamp border and lamp glow, held, no animation) while a Hint request is in flight (Tier 2, owner decision Oct 29). Plain-register surfaces (banners, Disclosures, errors) never glow.
- **Scene vignette:** `{elevation.vignette}` on the frame's mat only; the photo itself is never darkened, tinted, enhanced or filtered. In the walk (story mode, owner decision Oct 29) the vignette and a side shade may darken the walls, the neighbouring views either side, never the photo you face.

**Motion.** Slow and warm: fades and glows only, 150 ms for hover, 200 ms for state fades, 300 ms maximum for overlays entering and for the arrival glow; `ease-out` throughout; nothing slides, bounces, shakes or scales more than 2%. A lock open is a glow trigger: the solved Hotspot's bloom and the Scene frame's gilt rule light once (150 ms in, 150 ms held, 150 ms out) while the Solved chip fades in over 200 ms lifted on the paper shadow; a pickup is the other, the new Inventory slot's well lighting once the same way. Every reply's feedback line fades in over 200 ms, is held 2.5 s and fades out (owner decision, Oct 29). Nothing shakes on a Wrong attempt. **Nothing loops:** the Guide's thinking state (a static lamp ring plus a "thinking on this Mac" label), the Guide pulse (the same ring lit and held while a Hint request is in flight, beside "The Guide is thinking" on the button), the "Checking" chip and the running Timer's lamp dot are static. The exceptions are content, not chrome: the Hosted landing chooser's card clip and the sample room's photos loop (below). With reduced motion set, every transition becomes an instant change and the arrival glow becomes the lit ring held for 2 s with no animation (NFR-14). **Owner exception: the Hosted landing chooser only (Oct 29).** On that one screen the cards move, transform and opacity only, every value in `chooser.css` and `chooser.ts`: the **deal**, each card spun in from below through 540 degrees over 1500 ms, the centre first, then the left and the right 160 ms apart (`cubic-bezier(.25,.55,.3,1)` to a 10-degree overshoot at 78 %, then `cubic-bezier(.45,0,.4,1)`), its shadow growing in after it, the pitch and key hints fading in over 700 ms; the **breathing idle**, a 4 px float over 4.6 s, alternate, offset per card; the **lift**, hover or focus bringing a card forward (80 px toward the viewer, squared up, scale 1.03) and the other two back and dimmed, over 520 ms on `cubic-bezier(.2,.8,.2,1)`, with its lamp rim, its pool of light, its plate lit and its prompt rising over 260 ms; the **tilt**, up to 8 degrees toward the pointer, lerped each frame from cached geometry and stopping when settled, with a glint that follows it; the **spin**, one full turn on choosing over 1150 ms on one `cubic-bezier(.5,0,.2,1)` across the whole turn, the card to 270 degrees (its keyhole back passing in view) and the panel from edge-on to rest, handing over at the edge-on moment under a lamp-light flash (560 ms), the other cards swept off to the sides over 820 ms; the way home, the panel to edge-on over 380 ms and the card finishing its turn over 560 ms; the **dust**, 26 motes rising through the lamp cone over 10 to 19 s; the **candle flicker**, the lamp cone's opacity between .85 and 1 over 7 s, alternate; the **shimmer**, a gilt band crossing each card's frame once every 8 s; the four portraits on the Build card lit in turn every 5.6 s; and the sample room's photos crossfading over 1200 ms, each drifting (scale 1.02 to 1.1) over 7 s, held 3.6 s on the card and 2.8 s on the back. A **Pause motion** toggle in the chooser's footer holds every loop still (and pauses the clip and the photos), while the lift, the tilt and the spin still answer, being the player's own; the card clip keeps its own pause toggle (WCAG 2.2.2). With reduced motion set, nothing deals, breathes, tilts, spins, flickers, shimmers or drifts and the dust holds still: a choice and a return are a 160 ms crossfade of the stage, and the clip and the photos wait on their first frame. **Owner exception: the intro (Oct 29).** On the first visit to the Hosted landing the owner's ten-second teaser (`web/public/intro/`, re-encoded from the owner's own video) covers the whole page, top bar and Disclosure strip included, on black (`#000`), the video covering the viewport (`object-fit: cover`; `contain`, letterboxed, wider than 21:9 or narrower than 5:4), above everything else. It autoplays muted: its music is the one sound in the product and starts only when the player presses "Sound on" (browsers block audible autoplay). Its controls are quiet: "Sound on" top right and "Skip intro" bottom right, each 40 px on `canvas` with a 1 px lamp border and `text` in `label`; at its end, under the held title, the countdown line in `body-sm` `text` over "Replay" (secondary, on `canvas`) and "Enter Keyframe" (primary). Entering or skipping fades it out over 600 ms (`ease-out`); the chooser's deal starts only after. "Watch the intro" in the chooser's footer, a quiet underlined text button in 14 px `parchment` before "Pause motion", reopens it. With reduced motion set it never plays by itself and, reopened, shows the native controls with no fade, "Skip intro" moving to the top right, clear of their bar. **Owner decision: the tutorial (Oct 29).** The Watch back opens on the owner's own ten-second generated video, slowed to half speed (20 s, each frame held: motion interpolation warped this footage), its sound dropped, with five captions burned in (`web/public/tutorial/`; the lines, times and encoding in `clip.ts`): EB Garamond Medium in `parchment` on a soft `canvas`-dark band under a `gilt` hairline, just above the video's own inventory bar, each caption fading in and out over 250 ms, never two at once. It plays muted with native controls, only while its tab is shown on the open back, never by itself under reduced motion or Pause motion. Every other surface keeps the rule above. **Owner decision: the walk and story class (Oct 29, story mode).** On the Play screen the walk and the story move, each listed with its timing, and every one of them is off under reduced motion (a move is a cut, nothing drifts or pushes in, the seal simply appears, the daylight appears, fades are instant): the **turn swing**, every wall re-posed by its new offset (`wallPose`) over 780 ms on `cubic-bezier(.55,.05,.25,1)`, its opacity on `ease`, the side shade over 780 ms `ease`, a 2 px motion blur peaking at 45% (780 ms `ease-in-out`); the **push-in** through a doorway (the sign, ArrowUp, the walk map or "Take me there" across areas), the area you leave scaling 1 to 1.55 and fading through .85 at 50% to 0 with a 3 px blur over 720 ms on `cubic-bezier(.5,0,.75,.2)` around the sign's centre (18% lower) or 50% 45%, the next area from scale .92 and opacity 0 to rest over 640 ms on `cubic-bezier(.2,.7,.2,1)` starting 260 ms in (900 ms in all); the **slow push-in at rest**, the photo you face from scale 1 to 1.035 over 26 s on `cubic-bezier(.3,0,.4,1)`, once, around 50% 55%, restarting after every move; the **pointer drift**, the photo you face moving up to 7 x 4.5 px against the pointer and the walls 2.4 times as far, eased over 500 ms; the walk map's view cone turning with the swing; and, with the story, the **portrait slide** (600 ms on `cubic-bezier(.2,.7,.2,1)`, the dim 400 ms), the **seal slam** (500 ms on `cubic-bezier(.3,1.6,.5,1)`; the solve stamp 550 ms on `cubic-bezier(.3,1.5,.5,1)`), the **flicker** (700 ms, `steps(1)`), the **gem flight** (650 ms on `cubic-bezier(.5,0,.3,1)`) and the **exit push-in** (the area scaling 1 to 1.12 over 1400 ms on `cubic-bezier(.4,0,.2,1)`, the daylight over 1200 ms `ease-out`). All other motion on the Play screen stays fades and glows, 300 ms at most. The Completion stats count up once from 0 to their values when the result arrives, easing out over `--motion-count` (800 ms), a number change with no fade, slide or scale; with reduced motion set they show their final values at once (owner decision, Oct 29).

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

**Key-screen mocks.** The builder chose four mocks, rendered as HTML from these tokens: [mockups/play-screen.html](mockups/play-screen.html), [mockups/capture-screen.html](mockups/capture-screen.html), [mockups/build-view.html](mockups/build-view.html) and [mockups/completion-greeting.html](mockups/completion-greeting.html). They illustrate this file and EXPERIENCE.md and add nothing to them; where a mock and this file disagree, this file wins.

### Shared controls

| Component | Anatomy and size | Tokens | States |
|---|---|---|---|
| Primary button | Label only, 44 px high, 24 px side padding | `{components.button-primary}` | Rest lamp fill; hover `lamp-strong` + glow; focus two-tone ring; disabled 40% opacity, no glow |
| Secondary button | 40 px, 1 px lamp border | `{components.button-secondary}` | Hover fills `lamp-hover-fill`; on parchment the label and border are `lamp-ink` and hover fills `lamp-ink-hover-fill` (the Using chip's Cancel; Submit and the sequence control take the dark form on the notes tray since Oct 29). **Pressed or expanded** (toggles only: "Show all objects" pressed, "Show the build JSON" expanded; "How hints work" is a quiet text button whose expanded state shows as `text` in place of `text-muted`): `lamp-hover-fill` held as the fill and a 2 px `lamp` border (`pressedFill`, `pressedBorder`), so the state shows without hover; the effect itself (the outlines, the open panel) is the second cue, never color alone |
| Quiet button | The secondary button's 40 px, label and padding, its edge a 1 px `hairline` and its label `text` (14.19:1 on chrome); only "Show all objects", the Card log button and "Leave room" in the top bar (owner decision Oct 29: the hint button is the Play screen's one gold action) | `{components.button-quiet}` | **Rest:** no fill, `hairline` edge, `text` label. **Hover and focus:** lit, `lamp-strong` label (8.65:1 over the fill), 1 px `lamp` edge, `lamp-hover-fill`; focus also draws the two-tone ring. **Pressed** ("Show all objects"): the same lit look held, with the 2 px `lamp` edge, so the state shows without hover; the outlines are the second cue. Inert with the top bar under the Play screen's overlays and on the Completion screen |
| Focus ring | 2 px `focus-ring` outside 2 px `focus-ring-inner`, 2 px offset | `{components.focus-ring}` | On every focusable element, Hotspots included; never removed |
| Mode indicator | One plain line in the top bar after the wordmark, `body-sm` `text-muted` (content in EXPERIENCE.md) | `{components.mode-indicator}` | Local ("Local mode · Cache off · profile demo · 1 room played"); Hosted ("Hosted mode"); never hidden, never styled as a Disclosure |
| Status strip | `{spacing.status-strip}` plain strip, `body-sm`, no portrait, no glow | `{components.status-strip}` | Reconnecting on the Play screen (top of the Scene column, Scene frame shrinks to fit); reconnecting on the Capture screen (top of the left area, above any banner; the Stage list stays as last seen); server unreachable on cold load (centered in the page body, alone) |

### Capture screen

Mock: [mockups/capture-screen.html](mockups/capture-screen.html), a live Build in Local mode (the Architect's row, "Writing puzzles" with the Riddler's introduction, the Mask preview and the compact tray), then the Empty state and the HEIC refusal.

| Component | Anatomy and size | Tokens | States |
|---|---|---|---|
| Capture dropzone | Tray, at least 320 px high, centered picker button and the picker sentence in `body-md` (the verbatim Input requirement term stands alone only in the right column); in Hosted mode with a Demo room listed, a second secondary button under the picker button, "No photos handy? Play the sample room" | `{components.capture-dropzone}` | Rest dashed hairline; drag-over dashed lamp; disabled during a Build |
| Photo tray | Grid of 120 x 90 thumbnails, 12 px gaps, in upload order, count line in `label`; before Upload each thumbnail has a 32 px remove control at its top-right corner: a × in `text` on a `{colors.scrim}` square, `rounded.md`, 1 px `hairline` border. During a Build the tray turns compact: 96 x 72 thumbnails at the same radius and gaps, count line kept | `{components.photo-tray-thumb}` | Accepted; rejected file marked with a 2 px `wrong` border and a `label` in `wrong` under the thumbnail naming why (FR-1), and still removable; kept visible on every end state (PRD §8) |
| Mask preview | Same grid, each tile an Interactable's clearest photo with its outline drawn as `build-view-mask`; its label on a parchment chip in `label` type (`{components.hotspot-label-chip}`), never at the caption floor | `{components.build-view-mask}`, `{components.hotspot-label-chip}` | Tiles fade in together (200 ms) when the mask preview arrives (EXPERIENCE.md) |
| Timer | A plain `label` in `text-muted` before `mono-timer` digits in the top bar center, m:ss, with a 6 px lamp dot between the label and the digits while it runs | `{components.timer}` | Running: label "Photos to play", `text` digits, static lamp dot (no blink); stopped at T1: label "Playable in", frozen T1 − T0 in `success`, no dot; end status (`failed`, `needs_more_photos`, `needs_recapture`): frozen digits plus the status in player words ("Build stopped", "Add more photos", "Try clearer photos") in `text-muted`, no dot; Hosted queued: "Waiting to build" in `label` in place of the digits; Hosted after a queue: a `label` `text-muted` note after the digits ("includes m:ss in the queue") |
| Stage list | On a `chrome-raised` tray (`rounded.lg`, 16 px by 24 px padding). **Architect's row** at the top, drawn at Upload, with a 1 px `hairline` rule under it: Architect portrait (48 px); beside it "The Architect" in `label`, the role line in `body-sm` `text-muted`, the voice line in `wizard-line` `text`. Under it a vertical list of the six stage names (A-11, and "Writing the story" between "Testing the room" and "Setting the scene", amended 29 Oct 2026, story mode) in `label`, each with a 12 px marker and a `mono-sm` duration ("4.2 s"): `success` on a done row, `lamp` on the running row (elapsed so far); the running row shows the Architect's stage line under its name in `wizard-line`, and "Finding objects" keeps the Architect's line naming the objects ("I see {n} things worth a closer look, …") under its name in every state from the first poll that carries the Mask preview (changed Oct 29, decision record item 64). A done row adds its plain result in `body-sm` `text` under the name ("9 objects") and the model id in `mono-sm` `text-muted` beside the duration; the done "Testing the room" row carries two result lines, one per check (rules, then the test run). **Riddler's introduction** inside the "Writing puzzles" row: Riddler portrait (48 px), "The Riddler" in `label`, the role line in `body-sm` `text-muted`, the voice line in `wizard-line`. Same in both modes | `{components.stage-list-item}`, `{components.wizard-portrait}` | Pending hollow `text-muted`; running filled `lamp`; done `success` with duration; failed `error-text`; the stage line moves to the newly running row as each stage starts (200 ms fade); the Riddler's introduction fades in (200 ms) when "Writing puzzles" starts and stays for the rest of the Build, never drawn before; the Architect's row stays static once drawn; Regeneration repeats the author, validate and dry run rows with "attempt n of {max}" in `label`, and the Regeneration row carries a plain "Sent back: …" line in `body-sm` naming the failed attempt's fixed messages |
| Stored Room row (Local) | Row on chrome, one per stored Room: 96 x 72 cover thumbnail, the Room's name when it has one, else its build date and time, and the Puzzle count in `body-sm`, "Play" (secondary) and "How this room was built" (secondary) | `{components.stored-room-row}` | Rest; hover row ring `lamp`; focus ring; empty list: one `text-muted` line |
| Retention summary | Tray in the right column, on `chrome-raised` (never parchment): heading `display-sm`, the mode-specific text in `body-sm`, naming every service photos and puzzle text go to (FR-6; raw room photos go nowhere else), its provider-policy URLs as `lamp` links, then the plain label "Your play history" in `label` and under it the Privacy line, "the player profile stays on your machine.", in `body-md` 600 `text`. Under cut 2 only, an "Open profile file" secondary button and its one plain `body-sm` line sit below the Privacy line | `{components.retention-summary}`, `{components.button-secondary}` | Always fully expanded; never truncated, collapsed or set below `body-sm` |
| Error banner | Full width of the left area: heading (serif, like every heading) and one plain sentence in `body-md` on the left, actions (Choose photos again, Add photos, Start over, Try again) as secondary buttons at the right end of the row. The FR-1 refusal has no sentence: its verbatim string is the heading | `{components.error-banner}` | Error variant for format and count (action "Choose photos again"), upload failed ("Try again"), `failed` (with stage), `needs_more_photos`, `needs_recapture`, session start refused ("Try again"); warning variant (`{components.warning-banner}`) for Spend cap (no retry action), `queued` and Build quota; no portrait |

### Play screen

Mock: [mockups/play-screen.html](mockups/play-screen.html), room 1 mid-Session in Local mode: pointer hover on one Hotspot and keyboard focus with its label chip on another, "Current" on Puzzle 3, an unrequested Rung, the collapsed Triggers toggle (since Oct 29 the hint button and "How hints work" in its place); then the first Trickster card (accepted, with the introduction) and "Not this · 1" on the Code field.

| Component | Anatomy and size | Tokens | States |
|---|---|---|---|
| Scene frame | Canvas ground, 12 px chrome mat, 1 px gilt rule, inner vignette; the photo contained inside at `rounded.sm` | `{components.scene-frame}` | Lock opened: the gilt rule turns `lamp` under `{elevation.lamp-glow}` once, 300 ms in all (`openRule`, `openGlow`; under reduced motion the lit rule held 2 s); loading: mat only with a `text-muted` line; reconnecting: the status strip appears above the frame (the frame shrinks, nothing overlays the photo), the photo dims to 60% and inputs disable; play-through ended: the photo dims to 60% under a centered plain line on `chrome-raised` with "Start again" (secondary); cannot draw (WebGL fails to start): the mat holds the `{components.error-banner}` centered, at most 560 px wide, with "Reload" (secondary), in place of the photo (added Oct 29, decision record item 67) |
| Hotspot | The Interactable's polygon(s) over the photo | `{components.hotspot}` | **Rest:** invisible, pointer cursor only. **Hover:** 3 px lamp outline, 1 px dark halo, 35% glow fill and the lamp drop shadow (`hoverGlow`) around the reveal, 150 ms fade; the label chip after a 400 ms dwell. **Pressed:** the glow fill goes solid lamp while the button is held. **Focus:** the two-tone focus ring traced along the polygon plus the label chip at once, no shadow. **Show all objects:** every Hotspot gets the 2 px dashed `hotspot-show-all` outline with halo, no fill, no shadow, no labels. **Clicked:** the label chip with the Checking chip beside it until the reply; a non-target reply leaves the label chip alone (FR-12). **Collected (`find` solved):** the hover glow shows, then fades out over 200 ms while the Inventory item fades in over the same 200 ms. **Opened (the unlock moment):** the solved target's bloom path, the polygon filled `bloomFill` under `bloomGlow`, fades in and out once over `bloom` (300 ms in all; under reduced motion the lit fill held 2 s), above whatever hover, focus, show-all or the collected state draw |
| Hotspot label chip | Parchment chip, `label` type, anchored above the polygon's top edge, 8 px offset | `{components.hotspot-label-chip}` | On hover: after a 400 ms dwell, held until the pointer leaves; on keyboard focus: at once, for as long as the Hotspot has focus; while a click or `use_on` waits: with the Checking chip beside it until the reply; after a non-target click: fades out after 2 s or on pointer leave [ASSUMPTION] |
| Feedback line | Parchment strip centred at the photo's bottom, 22 px up (`inset`), `rounded.md`, `{elevation.paper}`; the Guide's 30 px portrait left of one `wizard-line` in ink. The coach pill (story mode, owner decision Oct 29) shares its place: plain `body-sm` `text` on `chrome` with a `hairline` edge, a `lamp` dot and the arrows in key caps | `{components.feedback-line}`, `{components.coach-pill}` | Hidden (opacity 0, takes no pointer); a reply's line fades in (200 ms), is held 2.5 s (`hold`) and fades out; a new line fades in over the shown one; the coach pill shows at play start on the first riddle for at most 15 s and is hidden while a line shows; instant under reduced motion [ASSUMPTION for the layout] |
| Walls (story mode, owner decision Oct 29; replaces the Thumbnail strip) | The photo you face at the frame's full height, its two neighbours in its ring as walls: plain images the size of that photo, 0.94 of its width out and 0.30 back, turned 52 degrees toward you, in a 1500 px perspective, each under a side shade from `canvas` at 55% (near edge) through 85% to `canvas` (far edge); views further round wait beyond them, turned 62 degrees and unseen | `{components.scene-frame}` | Only the photo you face carries Hotspots and takes input; the walls are inert and hidden from assistive technology. Under reduced motion every move is a cut |
| Turn zone | The outer fifth of the photo you face, either side, under the Hotspots; its cursor a 36 px lamp-ringed curved arrow; a 56 px `canvas` fade at its edge on hover | `{components.scene-frame}` | Hidden at the ring's end on that side |
| Turn disc | 52 px round `chrome` disc, 1 px `hairline` edge, a chevron in `lamp-strong`; its name in 13 px `text-muted` under it on hover and focus | `{components.turn-disc}` | Hover: `lamp` edge on `chrome-raised`; hidden at the ring's end on that side |
| Doorway sign | A gilt plaque hanging by two 14 px chains from the photo's top edge: an arch icon, "To the {area}" in 18 px serif `on-lamp`, an "↑" key cap; placed at the first of x 480, 640, 320, 760, 200 (photo px of a 960 px photo, scaled) whose 230 x 120 box overlaps no Hotspot; a second sign 30% further along | `{components.doorway-sign}` | Hover: lighter gilt with a lamp drop shadow; focus: the shared ring |
| Walk map | "Where you are", a 184 px card at the frame's top right: `canvas` at 80% under a 1 px `hairline` edge at 60%, `rounded.lg`; the heading in `label` `text-muted`; a plan with one `hairline` box per area, sized by its photo count, a dashed `text-muted` doorway tick between neighbours, one dot per photo in ring order along a shallow arc and a `lamp` view cone over the dot you stand on; one button per area under it in 13 px sans `text-muted` | `{components.walk-map}` | The dot you stand on lit `lamp` (4.5 px, `canvas` ring); the area you stand in in `text` 600; a button's hover `lamp`; the cone turns from -50 to 50 degrees across a ring with the turn |
| Your pack (story mode, owner decision Oct 29); the Inventory | On the floor left of the photo, 22 px from its edge and 26 px up, right-aligned (never past 16 px inside the frame's left edge; a narrower margin puts it over the photo's lower left corner): "Your pack" in 14 px sans `text-muted`, a row of 76 x 60 crops (`rounded.md`, a 1 px `gilt` edge, each cut around the Interactable's largest polygon), a free slot the dashed `hairline` well, and a 13 px `text-muted` caption | `{components.inventory}` | Empty: one dashed slot and the caption; item arriving fades in (200 ms) in step with its Hotspot's glow fading out, its well lit once with `{elevation.lamp-glow}` (150 ms in, held, 150 ms out; held 2 s under reduced motion); in hand for `use_on`: 2 px lamp ring; dragging: item at 60% in place, a 64 px drag image with `{elevation.paper}` |
| Riddle note (story mode, owner decision Oct 29); replaces the Wizard notes | A parchment note pinned to the wall at the Scene's top left (18 px down, 20 px in; 300 to 400 px wide, as the wall left of the photo allows; scrolling inside itself below 58% of the height), `rounded.lg`, the paper shadow, a red pin: the heading "Riddle {n} of {N}" in 21 px serif `ink`, then one 22 px wax seal per Puzzle (a dashed slot, the current one ringed in `lamp-ink`, a solved one red wax with its number); the place tag in `label` `lamp-ink` on a faint lamp-ink pill with a pin icon; the Riddler's 40 px portrait beside the clue (`wizard-line` at 21/1.36); "The Riddler's aside" in 13 px sans `ink-muted` with a chevron, over the lore (`lore`, `ink-muted`); each bought hint on a `parchment-shade` inset, the Guide's 26 px portrait beside "The Guide's hint · Nudge" in `label` `lamp-ink` and its line in 17 px serif; a `code` or `order` riddle's lock input; the "Solved" stamp in `label` `success-ink` beside its seal | `{components.riddle-note}` | One riddle at a time; the heading takes focus with no ring (it is no control); a solved riddle holds with its stamp, its seal stamped in (550 ms on `cubic-bezier(.3,1.5,.5,1)`, from 1.9x and -30 degrees), until "Take me there"; a bought hint lands with one arrival ring (900 ms ease-out; held 2 s with no animation under reduced motion) |
| Clue card slot (Tier 1.5) | `{components.clue-card-slot.width}` x `{components.clue-card-slot.height}`, `rounded.sm`, beside the Clue in its Puzzle entry, right-aligned, the Clue wrapping to its left (FR-37) [ASSUMPTION for the size]; drawn only when the Room has Clue cards | `{components.clue-card-slot}` | Placeholder: `clue-card-placeholder` fill with a 1 px dashed `clue-card-placeholder-edge`; ready: the image; blank (failed): flat `clue-card-blank`, no edge; same size in every state |
| Wizard portrait | Circle with a 2 px gilt ring at 24 (Card log, Demo room card, Build view Model table), 26 (a hint on the Riddle note), 30 (the feedback line), 32 (signature, In play block, the Completion sheet's "Built by" row, the Trickster's bubble), 36 (the empty chest), 40 (the Riddle note's Riddler, the closing sheet's lines), 48 (Cards, the Architect's and Riddler's introductions in the Stage list) or 96 px (Greeting and First-room welcome) | `{components.wizard-portrait}` | Normal; Guide thinking (Local only, while the Greeting is being phrased): static `lamp` ring plus a "thinking on this Mac" `label` (no pulse, no loop), in `pending-ink` on parchment, where lamp fails; placeholder: initial on `chrome-raised` |
| Treasure chest (story mode, owner decision Oct 29); replaces the Hint area | On the floor right of the photo, 22 px from its edge and 26 px up (never past 16 px inside the frame's right edge; a narrower margin puts it over the photo's lower right corner, and its dialog and bubble slide left to stay in the frame): two diamond gems in `lamp-strong` (a spent one a `hairline` outline) over a 96 x 72 illustrated chest whose lid swings open while its dialog is open and stays open once it is empty (desaturated), its name in 14 px sans `text` over its count in 13 px `text-muted`. The dialog: 340 px of parchment above it on `{elevation.overlay}`, a 22 px serif heading, a plain 15 px line or the Trickster's 36 px portrait and line, `lamp-ink` "Open it" and an outlined "Not yet". The Trickster's bubble: a 250 px parchment bubble above it with a tail, his 32 px portrait, his name in `label` `ink-muted` and his line in 17 px serif | `{components.treasure-chest}` | Rest; hover (lamp fill and glow); dialog open (lid open); spending (the gem flies to the note, 650 ms on `cubic-bezier(.5,0,.3,1)` through a point 80 px above the middle, turning 360 degrees, swelling to 1.6x; none under reduced motion); empty; bubble shown 7 s |
| Story stage (story mode, owner decision Oct 29) | Over the Scene, below the top bar: a scrim rising from the bottom (`#0A0806F0` to `#0A080610`; the light one for a solve beat, `#0A0806D8` to transparent at 52%), the speaker's painted portrait at the left in a 3:4 gilt arch (radius 50% 50% 6px 6px / 37.5% 37.5% 6px 6px; a 1 px `gilt`, 6 px dark and 1 px bronze ring), min(66vh, 600px) tall (a solve beat min(46vh, 420px)), fading to dark at its foot; the parchment speech box, min(700px, 100% - 48px) wide, 26 px up, in a gilt double ring with a tail toward the speaker, the brass name plate (name in 21 px serif, role line in 13 px sans) on its top edge, the "Riddle {n} solved" row with its 38 px seal, the line in 25/1.38 serif, the pack row (a 44 x 34 crop beside a plain 15 px line), and the `lamp-ink` button with its "Enter" key cap | `{components.story-stage}` | Portrait slides in (600 ms on `cubic-bezier(.2,.7,.2,1)`; none under reduced motion); lines appear whole, at once, with no typing effect |
| "How hints work" | In the Card log, under the Cards (story mode, owner decision Oct 29): a `label` heading, then a panel on chrome with its one plain `body-sm` line and the hint history, at most `{spacing.triggers-panel-max}` high and scrolling, one row per Rung change in `body-sm` with `mono-sm` numbers ("Puzzle 2, hint 1, after three wrong tries", ", worded on this Mac" when the Guide model worded it); the newest row in `text`, older rows in `text-muted` | `{components.triggers-panel}` | No rows: the line alone; under cut 5 the same content fills a second window |
| Code field | Inset on the Puzzle entry: `mono-code` field sized for 6 characters (`{components.code-field}` size; it keeps its `parchment-shade` inset on the dark notes) and a secondary Submit (the dark form, `lamp`); no visible label or placeholder | `{components.code-field}` | Rest; focus ring; pending (field read-only, Pending chip); wrong (Not this chip and count beside it, field keeps its value, selected for retyping: a `lamp-ink-hover-fill` tint with a 1 px `lamp-ink` edge); open (Solved chip, field removed) |
| Order click progress | In the order Puzzle's entry: a "Start the sequence" control (secondary button, `lamp` on the dark notes since Oct 29) and a row of 3 to 5 pips (10 px, a `text-muted` ring when empty), one per position in the sequence, with a visually hidden "{filled} of {length}" description | `{components.order-progress}`, `{components.button-secondary}` | **Unarmed** (default): pips empty, never flash; the control reads "Start the sequence". **Armed** (after "Start the sequence"): the control reads "Stop the sequence"; every acknowledged Hotspot click fills the next pip in `lamp`, whichever object it hit (behavior in EXPERIENCE.md); a full-length mismatch turns the pips `wrong` for 300 ms, then empties them, with the Not this chip, and the sequence stays armed. **Stopped:** pips empty, back to unarmed, no Not this chip. Pips never show which clicks were right |
| `use_on` drag | Inventory item dragged onto the Scene; the Hotspot under the pointer shows the hover state | `{components.inventory}`, `{components.hotspot}` | Dragging; over a Hotspot; dropped (the target's label chip shows with the Checking chip beside it until the verdict, which then shows in the resolved Puzzle's entry) |
| `use_on` select-then-click | Selected item ringed in lamp; a parchment chip pinned to the top-left of the Scene frame names the item and offers Cancel | `{components.use-on-selected}` | Selected; Hotspot hover while selected; cleared (chip fades out) |
| Feedback chips | Outlined chip in the state's colour, `label` type, word first, never icon-only: "Not this" (with the per-lock count) and pending (wording in EXPERIENCE.md); on the Riddle note's parchment in the ink forms (`wrong-ink`, `pending-ink`) | `{components.chip-not-this}`, `{components.chip-pending}` | Not this persists until the next input; pending shows a static ellipsis (no animation); a solved riddle is the note's "Solved" stamp |
| Evidence card | Inset row directly under the Clue, on the landing's sample page a `parchment-shade` inset in `ink` (story mode: the Play screen draws none). **Unsolved:** the Riddler's note alone, the read attribute quoted in `wizard-line`: no label, no crop. **Solved:** 64 px thumbnail crop (`rounded.sm`), Interactable label (`label`), read attribute (`body-sm`, `text-muted` in the notes, `ink-muted` on paper) describing where to look, never a solution token | `{components.evidence-card}` | Two states, following the Puzzle's lock: the note until it opens, then the whole card fading in (200 ms, `--motion-state`; instant under reduced motion) as the reward. Real and Decoy cards are pixel-identical in each state and keep a stable order; a new card gets no highlight, badge or animation beyond the entry's ordinary fade (FR-11, FR-19) |
| Trickster card, accepted | Story mode: in play its sentence shows in the Trickster's bubble above the chest (see Treasure chest), 7 s; the Card log keeps the Card. Parchment card: Trickster portrait (48 px) beside the sentence in `wizard-line` (first), then the outcome label in `label` after it ("Validator passed · Merge · Puzzle 3"), dismiss control (32 px hit area). **First Card of the Session only:** above the sentence, "The Trickster" in `label` with the role line under it in `body-sm` `ink-muted`, then the voice line in `wizard-line` | `{components.trickster-card-accepted}` | A Loosen Card's Rung is refused under the chest; the introduction appears once per Session, on whichever Card comes first, and never on a later Card or in the Card log |
| Trickster card, rejected | Same anatomy, `wrong-ink` edge; the Trickster's sentence in `wizard-line`, then the outcome label ("Validator refused · Merge · Puzzle 3"), then a plain structural "Proposed: …" line in `body-sm` `ink`, then the plain reason ("That change was refused. {fixed message}") in `body-sm` `ink`; the same first-Card introduction | `{components.trickster-card-rejected}` | As accepted; the reason is never styled in character |
| Trickster card, skipped | Off the paper: `chrome-raised`, dashed edge, portrait at 60% opacity, one `wizard-line` sentence in `card-skipped-text`, then the label "Skipped"; the same first-Card introduction, its role line in `card-skipped-text` | `{components.trickster-card-skipped}` | As accepted; same look for a provider error and the Spend cap |
| Card log | Modal dialog anchored under the top bar's Card log button, over `{colors.scrim}` (below the top bar, like every overlay), 360 px wide, max 480 px high, scrolling: a close control, then one row per Card with portrait (24 px), the sentence in `wizard-line`, then outcome label (`label`), a rejected Card's "Proposed: …" line and reason (`body-sm`), and session time (`mono-sm`) | `{components.card-log}` | Empty: one `text-muted` line; open (Scene, Hotspots and top bar inert); closed; enters with a 300 ms fade |

### Completion, Greeting, Build view

Mocks: [mockups/completion-greeting.html](mockups/completion-greeting.html), the room 1 Completion sheet, the First-room welcome with its tip, the room 2 Greeting and the Guide's thinking state; and [mockups/build-view.html](mockups/build-view.html), the Build view opened from the Completion screen with two Disclosure lines, one Regeneration and every panel, plus the cut 4 Dry run rows.

| Component | Anatomy and size | Tokens | States |
|---|---|---|---|
| Completion screen | Story mode, owner decision Oct 29: the exit photo with its door still in daylight, under the soft scrim (`scrim-soft`, 50%), and the closing sheet docked low over it (22 px up, min(860px, 100% - 40px) wide) so the door stays in view: parchment, `rounded.lg`, a 1 px `gilt` edge and `{elevation.overlay}`, 22 by 26 px padding, two columns. Left: "You escaped." in 36 px serif, the subline in `body-sm` `ink-muted`, then each wizard's closing line, a 40 px portrait beside the name in `label` `ink-muted` over the line in 18/1.35 serif. Right of a `parchment-rule`: Riddles, Time, Chest hints and Wrong tries two across, each value in `mono-timer` over its `label` in `ink-muted`, counting up once on arrival (Motion), over "Play again" (primary). Under both, "Details" (`label`, `ink-muted`) folds away the filmstrip (every photo of the Room in one row at its own aspect, `rounded.sm` on canvas, each solved object's outline a 2 px `lamp` line over a 4 px `hotspot-halo`, no fill, no label), the per-Puzzle time table (row header "Puzzle {n}" in `body-sm`, its time in `mono-sm`, right-aligned, no header row, with its plain caption in `body-sm` `ink-muted`), "Built by" over the four wizards (32 px portraits beside their names in `body-sm` `ink`), and "Build another room", "Copy your result" and "How this room was built" (secondary, on parchment), the copied confirmation under them in `body-sm` `ink`; under cut 2 only, "Save profile file". When the result is not safely kept, one plain `body-sm` `ink` line under the columns, with "Try again" for a profile file that failed to save. A Judge room's "Deleted Tue Nov 10" sits directly below the sheet, on the scrim | `{components.completion-sheet}` | Pending stats show a static ellipsis; the heading takes focus with no ring; Details closed |
| Greeting / First-room welcome | Over the first Scene: scrim (below the top bar), a 560 px parchment card. The Guide's introduction at the top: Guide portrait (96 px) beside the heading "The Guide" in `display-sm` with the role line under it in `body-sm` `ink-muted`. Then the opening line in `wizard-line-lg`, the Guide's voice line under it in `wizard-line`, and "Begin" (primary). First-room welcome only: the three-step how-to-play between the opening line and the voice line, a numbered list in `body-md` `ink` (added Oct 29), and a one-time plain tip under the card, on the scrim, in `body-sm` `text-muted` | `{components.greeting-overlay}`, `{components.wizard-portrait}` | Greeting (returning player, Local mode); First-room welcome (fresh Player profile; and always in Hosted mode, which sends a fresh Derived block, FR-20, FR-21, FR-31); same anatomy for both; enters with a 300 ms fade; Local Greeting being phrased: the introduction and voice line show, and in place of the opening line the portrait carries the Guide's static thinking ring and the "thinking on this Mac" label sits where the line will appear, in `pending-ink`; no "Begin" until the line arrives. "Begin" sits left-aligned under the voice line |
| Leave room confirmation | Over the Play screen: scrim (below the top bar), a 480 px `chrome-raised` card (plain, never parchment): heading `display-sm`, one `body-md` sentence, "Keep playing" (primary, focused) and "Leave room" (secondary) | `{components.leave-room-confirmation}` | Open; closed (Escape means "Keep playing"); enters with a 300 ms fade |
| Deleted Judge room notice | The page body with a centered 480 px `chrome-raised` card: heading `display-sm`, one plain `body-md` sentence, "Go to the demo rooms" (primary) | `{components.leave-room-confirmation}` (same card, no scrim) | Deleted; unknown room: the same card with the unknown-room copy |
| Build view: header | Row on chrome: the Room's name as the title (`display-md`), or its build time when it has no name; the build time in `body-sm` beside a named title; "Regenerations: n of {max}" with `mono-sm` numbers; after a Regeneration, one plain `body-sm` line per failed attempt ("Attempt 1 sent back: …" with its fixed messages); "Back" (secondary) | `{components.build-view-header}` | Ready; not ready (header, then one plain `body-md` line and a secondary link to the Build's Capture screen, no panels); error (one plain line and "Try again") |
| Build view: mask overlays | Grid of the Room's photos, three across, each with every Interactable's mask filled and stroked and its label on a parchment chip in `label` type | `{components.build-view-mask}`, `{components.hotspot-label-chip}` | Box-rectangle Hotspots draw the same way as masks (AD-11) |
| Build view: puzzle graph | Nodes 168 x 64 px: Puzzle order number [ASSUMPTION] (`mono-sm`) and Lock type (`mono-sm`) on parchment; `requires` edges with 8 px arrowheads; Exit puzzle with the lamp double ring and an "Exit" `label`; a Dry run marker in the node's top-right corner: an 8 px dot and the word ("pass", "fail", "skipped") in `label`, in `success-ink`, `wrong-ink` or `ink-muted`, because the node is parchment (the `graph-*` verdict colors are for the dark tables); the "Exit" label in `lamp-ink` | `{components.graph-node}`, `{components.graph-edge}` | Static; focusable nodes show the focus ring |
| Build view: Validator verdict table | Like every Build view panel, no heading: one plain caption line in `body-sm` `text-muted` above the table, then header cells in `label` `text-muted` over a `hairline` rule; one row per base check (rules 1 to 8): rule number (`mono-sm`), the rule's check-phrased name, verdict word with an 8 px marker in `graph-pass` or `graph-fail`; the fixed message in `body-sm` appears only on a fail row; then rule 9, the Decoy check, as its own row with the verdict word "not applicable" after the `graph-skipped` ring marker | `{components.verdict-table}` | Pass (check-phrased name, no message); fail (the fixed message under the name); not applicable (rule 9 on a build) |
| Build view: Dry run row | One plain caption line above the rows; one row per Puzzle: order number, Lock type, verdict word | `{components.verdict-table}` | Pass; fail; skipped (cut 4) in `graph-skipped` with "skipped" spelled out |
| Build view: Model table | First in the right column. Columns: role (24 px Wizard portrait and the wizard's name; on the Architect and Riddler rows the role line under the name in `body-sm` `text-muted`), model id (`mono-sm`), where it ran (host), what it did (`body-sm`, counts such as "found 9 objects"), cached or billed; one row per role and model, plus fixed rows for the Validator (no portrait, "deterministic code, no model", "checked 8 rules" when the Build recorded its verdicts), the Dry run, the Storyteller (no portrait; its model and host from the call rows, amended 29 Oct 2026, story mode), and Muse Image ("muse-image-1.0", "one-time generation of the four portraits, not part of this build", its cached-or-billed cell empty, since no Build paints portraits); one plain caption line under the table explaining cached. Header cells in `label` `text-muted`. A wizard with two models takes one row per model, portrait and name on the first; its role line runs as a full-width row of its own under them, because at the right-third width five columns leave the role cell no room. Build-time roles only: no Guide or Trickster row (the In play block carries both); the Validator's cached-or-billed cell stays empty | `{components.model-table}`, `{components.wizard-portrait}` | Cached and billed are words, never color alone; a role with both shows both counts |
| Build view: In play block | Fixed panel under the Model table: the Guide row (32 px portrait, "The Guide", its role line in `body-sm`, then the Guide model id and host; in Hosted mode a plain line saying the hints are shown as written here and that Llama 3.2 3B rewords them on the Mac in Local mode), the Trickster row (32 px portrait, "The Trickster", its role line, then the source: live, scripted or cut 1) | `{components.in-play-block}`, `{components.wizard-portrait}` | Local; Hosted |
| Build view: BuildView JSON | Collapsed pane under the mask overlays: a "Show the build JSON" toggle (secondary, with an expanded state), then one plain caption line in `body-sm` `text-muted`, then the build data exactly as served, pretty-printed in `mono-sm`, max 360 px high, scrolling | `{components.build-view-json}` | Collapsed (default); open; it holds only the solution-free build data |

### Modes, disclosure, platform

| Component | Anatomy and size | Tokens | States |
|---|---|---|---|
| Disclosure banner | Full-width footer strip under the body, `body-sm` lines, each Disclosure on its own line; no icon, no close control | `{components.disclosure-banner}` | Absent when nothing applies; one or more lines (FR-26); identical on the Capture, Play and Completion screens, the Build view and the Hosted landing; never dimmed by a scrim |
| Hosted landing | The `{components.chooser}` filling the first screen (the pitch, the three cards, the one back panel, the footer with the key hints and Pause motion); below the fold the cast: four `{components.wizard-portrait}` at 96 px with name (`label`), four-word role (`body-sm` `text-muted`) and voice line (`wizard-line`, on hover and focus); the row: the Riddler's sample page (parchment, paper elevation, an entry as the Wizard notes draw it) and the three steps of "How a room is built"; any further Demo room cards. The wizards also appear, behind "How a room is built", in the Build view Model table and In play block [ASSUMPTION, for the builder] | `{components.chooser}`, `{components.wizard-portrait}`, `{components.demo-room-card}`, `{components.evidence-card}`, `{components.access-code-field}` | See the chooser row; its motion is the owner exception in Motion |
| Chooser | A card: a `chrome` face (a 1 px `gilt` rule, a 6 px `chrome` mat, a 35 % `gilt` inner rule, `rounded.lg`, 12 px padding) with an arched window (radii from the card width) whose gilt rule fades out before the plate, a 46 px medallion on the top edge (play, key, camera), a gilt flourish in each corner, and the plate on solid `chrome`: the eyebrow (sans 600, `lamp-strong`), mono tag chips on `canvas`-dark with a `lamp` dot (Build's "~3 min" and "Access code required"; Play's puzzle count beside its one lamp tag "No upload needed", filled `lamp-strong` with sans 600 `on-lamp` words), the title (serif 500, `text`), the line (sans, `parchment`), the meta line (mono, `parchment`) and the prompt (sans 600, `lamp-strong`, an "Enter" key chip), each `clamp()`ed to the card width and never under 14 px, the line and meta never under 16 px; the back a keyhole on a lattice over the wordmark in `gilt`. The back panel: `chrome` under `{elevation.overlay}`, the same gilt frame and corners, a head with "Back" (a 38 px `gilt`-edged button with its "Esc" key), the `display-md` title and, at the right end, a tag, an eyebrow or a voice line (48 px portrait, the name in `label`, the line in `wizard-line`); Watch: two tabs in the head after the title, "Tutorial" and "Real play-through" (38 px, a 1 px `gilt` edge, `label` in `parchment`; the selected one lamp-edged on `lamp-hover-fill` with a 2 px `lamp` underline, in `text`), the title and the tag following the selected tab, then its video in a `gilt`-ruled box (the 16:9 tutorial held whole in the box sized to the play-through); Play: a three-photo mosaic with a mono count chip, `chrome-raised` fact chips in `body-md` `parchment` (the number in mono), "Your hosts" (48 px portraits, the roles in `body-md` `parchment`), "How to play" numbered in `lamp-strong` serif, then the 52 px primary "Play this room"; Build: three `chrome-raised` step cards (a `gilt`-ringed number, a picture, the title in serif 21 px, the body in `body-md` `parchment`), then a `chrome-raised` box holding "Have an access code?" (`display-sm`) over its note in `body-md` `parchment`, and the Access-code build with "Judges: the code is in the submission." under it in `body-md` `parchment` | `{components.chooser}` | Arriving; rest (Play leading while a Demo room is listed: 50 px forward and 6 px up, lamp rim, pool and plate lit, prompt shown; Watch and Build 50 px further back under a 25 % `canvas`-dark shade, their plate whole); a card forward (lifted, lamp rim, prompt shown; the others' faces shaded 50 % `canvas`-dark under a whole plate, their text still at least 7:1); choosing; chosen (the panel a modal dialog, the subline faded, the floor ring at 35 %); returning; paused (Pause motion pressed); reduced motion (crossfades only). Focus: the card's two-tone ring at 3 px, 4 px out, moving with the card; every other control the shared 2 px ring |
| Demo room card | One per Demo room: 4:3 cover photo on top (`rounded.lg` top corners), the Room's name (`Room.name`; build time when absent) in `display-sm`, Puzzle count and "15 to 25 min" in `body-sm` `text-muted`, the four Wizard portraits at 24 px in a row; a footer row with a 96 px mask-and-graph thumbnail (the cover's mask overlay with the puzzle graph inset) beside "Play this room" and "How this room was built" (both secondary, wrapping under each other in a narrow card) | `{components.demo-room-card}` | Rest; hover lamp ring and `{elevation.lamp-glow}`; focus ring on "Play this room" and, separately, on the Build view link |
| Access-code build | Panel in the right column: heading `display-sm`, a 44 px `mono-code` field and a primary button, a status line below in `body-sm` | `{components.access-code-field}` | Empty; checking (button reads "Checking code…"); refused (error banner, compact); check failed (error banner, compact, "We couldn't check the code. Try again.");  too many tries (warning banner, compact); accepted (status line in `success`, "n of 20 builds left", then the Capture screen); quota reached (warning banner; Demo room cards stay active) |
| Narrow-screen message | Below 1024 px: the canvas with a centered `chrome-raised` card (plain, never parchment), max 480 px wide, 16 px side gutters, wordmark, the Guide's 96 px portrait, heading `display-sm`, one plain sentence in `body-md`, then "Copy link for your laptop" (secondary) over its `body-sm` `text-muted` confirmation line | `{components.narrow-screen-message}` | Single state; the confirmation line fills when the link is copied; no horizontal scroll at any width |
| Server unreachable (cold load) | The page body empty except a centered `{components.status-strip}` line; no Disclosure banner, no Retention summary, no Scene | `{components.status-strip}` | Retrying; replaced by the surface once the server answers |
| Profile name refused (cold load) | The page body empty except the `{components.error-banner}`, centered, at most 640 px wide: heading, one plain sentence and "Use the dev profile" (secondary); no Disclosure banner, no Retention summary, no Scene (added Oct 29, decision record item 67) | `{components.error-banner}` | Not retried; "Use the dev profile" opens the same route on the default profile, deleting nothing |

## Do's and Don'ts

| Do | Don't |
|---|---|
| Frame the player's photos: gilt rule, mat, vignette on the mat | Tint, filter, crop or paint over a photo |
| Keep Hotspots invisible at rest; reveal them on hover, focus and "Show all objects" | Outline Hotspots at rest or simplify their polygons |
| Set in-character lines in the EB Garamond body styles, signed with the speaker's portrait; set every heading in the serif | Put a portrait or a serif body line on an error, a Disclosure, a quota or a deletion message |
| Keep plain messages on chrome, banners or the Disclosure strip; let plain labels and chips sit on paper in the sans | Put an error, warning, deletion, privacy or Disclosure message on parchment |
| Make Disclosures the plain chrome strip under a gilt rule, always visible, never covering the Scene | Set a Disclosure in a palette outside the study, give it a close control or overlay it on Hotspots |
| Keep real and Decoy Evidence cards pixel-identical in a stable order | Highlight, badge or animate a newly added Evidence card |
| Use lamp for the one thing that responds or is current | Fill large areas with lamp or use it on plain messages |
| Use `lamp-ink`, `success-ink` and `wrong-ink` on parchment | Put `lamp`, `success` or `wrong` on parchment (they fail AA there) |
| Pair every state color with a word ("Not this", "Solved", "skipped") | Signal any state by color or icon alone |
| Show the two-tone focus ring on every focusable element | Remove focus outlines or rely on the hover glow for focus |
| Keep motion to fades and glows, 300 ms at most, instant under reduced motion; show waiting with a static lit ring and a word | Slide, bounce, shake on a Wrong attempt, or loop any animation (pulses, blinking dots, animated ellipses; the Hosted landing chooser, the intro and the Play screen's walk and story class are the owner's exceptions, Motion) |
| Let the Disclosure banner sit above every scrim, on every surface including the Build view | Dim, cover or hide the Disclosure banner under an overlay (the intro alone covers the whole page, owner exception Oct 29, Motion) |
| Keep the Privacy line verbatim, full size, always visible on the Capture screen | Collapse the Retention summary or shorten the Privacy line |
| Make Hosted mode look like Local mode, with the First-room welcome and unbadged Rungs; show where a Rung was worded only in its "How hints work" row | Add a "verbatim" or "local" badge to the Rung line, or show a Greeting in Hosted mode |
| Keep Garamond at 17 px or larger | Set wizard lines small or in all caps |
