import './chooser.css'
import type { RoomSummary } from '../types'
import { photoUrl } from './api/index.ts'
import { cue } from './audio.ts'
import { buildViewLink } from './build-view.ts'
import { CLIP_CARD, DEMO_VIDEO, DEMO_VIDEO_ASPECT, TUTORIAL, type VideoSources } from './clip.ts'
import { ACCESS_CODE_FIELD, accessCodeBuild } from './components/access-code-build.ts'
import { primaryButton, secondaryButton } from './components/button.ts'
import { roomTitle } from './components/stored-room-row.ts'
import { type Intro, introDue, openIntro } from './intro.ts'
import { announce } from './live-region.ts'
import { buildViewHref, CUT_0 } from './router.ts'
import { fill, strings } from './strings.ts'
import { portraitUrl, speakerPrefix, type Wizard, wizardPortrait } from './wizards/portrait.ts'

// Motion, as DESIGN.md's owner exception for this screen gives it (Oct 29).
/** The deal: each card spins in over 1500 ms, the centre first, then the left, then the right, 160 ms apart. */
const T_ARRIVE = 1500
const ARRIVE_STAGGER = 160
/** One full turn on choosing: the card to 270 degrees (edge-on), then the panel from -90 to 0. */
const T_CHOOSE = 1150
/** The way home: the panel to 90 degrees, then the card from 270 to 360. */
const T_RETURN_PANEL = 380
const T_RETURN_CARD = 560
/** How far toward the viewer the turning card and the panel stand at the edge-on hand-over. */
const LIFT_Z = 140
const P_ROW = 1500
const P_PANEL = 2600
/** Under reduced motion every change is this crossfade, out then in. */
const FADE_MS = 160
/** How long the Play card holds each photo. */
const HOLD_CARD_MS = 3600
/** The polite announcement waits this long after the pointer settles on a card. */
const ANNOUNCE_MS = 500
const MOTES = 26
/** Each card's hover swish is panned toward its side of the arc. */
const PAN = [-0.6, 0, 0.6]

const WIZARDS: readonly Wizard[] = ['architect', 'riddler', 'guide', 'trickster']
const NAMES: Record<Wizard, string> = {
  architect: strings.architect,
  riddler: strings.riddler,
  guide: strings.guide,
  trickster: strings.trickster,
}
const HEROES: Record<Wizard, string> = {
  architect: strings.heroArchitect,
  riddler: strings.heroRiddler,
  guide: strings.heroGuide,
  trickster: strings.heroTrickster,
}
const ROLES: Record<Wizard, string> = {
  architect: strings.architectCastRole,
  riddler: strings.riddlerCastRole,
  guide: strings.guideCastRole,
  trickster: strings.tricksterCastRole,
}

const MEDAL_PLAY = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M7 4.5v11l9-5.5z" fill="currentColor"/></svg>'
const MEDAL_KEY =
  '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="6.5" cy="10" r="3.6" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M10 10h8M15 10v3M17.5 10v2.4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/></svg>'
const MEDAL_CAMERA =
  '<svg viewBox="0 0 20 20" aria-hidden="true"><rect x="2.5" y="6" width="15" height="10.5" rx="2" fill="none" stroke="currentColor" stroke-width="1.7"/><path d="M7 6l1.4-2.4h3.2L13 6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/><circle cx="10" cy="11.2" r="2.8" fill="none" stroke="currentColor" stroke-width="1.7"/></svg>'
const CORNER =
  '<svg class="chooser-corner" viewBox="0 0 22 22" fill="none" aria-hidden="true"><path d="M1 21V7Q1 1 7 1h14" stroke="currentColor" stroke-width="1.2"/><path d="M5 21V10q0-5 5-5h11" stroke="currentColor" stroke-opacity=".45"/><circle cx="4" cy="4" r="1.6" fill="currentColor"/></svg>'
const BACK_ICON =
  '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M9 2 4 7l5 5" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'
const CLIP_PAUSE_ICON =
  '<svg viewBox="0 0 14 14" aria-hidden="true"><rect x="2.5" y="2" width="3" height="10" rx="1" fill="currentColor"/><rect x="8.5" y="2" width="3" height="10" rx="1" fill="currentColor"/></svg>'
const CLIP_PLAY_ICON = '<svg viewBox="0 0 14 14" aria-hidden="true"><path d="M3.5 2v10l8.5-5z" fill="currentColor"/></svg>'
const STILL_ICONS =
  '<svg class="is-pause" viewBox="0 0 12 12" aria-hidden="true"><rect x="2" y="1.5" width="2.6" height="9" rx=".8" fill="currentColor"/><rect x="7.4" y="1.5" width="2.6" height="9" rx=".8" fill="currentColor"/></svg><svg class="is-play" viewBox="0 0 12 12" aria-hidden="true"><path d="M3 1.5v9l7.5-4.5z" fill="currentColor"/></svg>'

/** The card's back: a keyhole on a lattice over the wordmark; `id` keeps each lattice pattern's id its own. */
function keyholeArt(id: string): string {
  return `<svg viewBox="0 0 200 300" fill="none" aria-hidden="true"><defs><pattern id="${id}" width="20" height="20" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><path d="M0 0h20v20" stroke="currentColor" stroke-opacity=".16" stroke-width="1"/></pattern></defs><rect x="0" y="0" width="200" height="300" rx="6" fill="url(#${id})"/><rect x="6" y="6" width="188" height="288" rx="5" stroke="currentColor" stroke-opacity=".5"/><circle cx="100" cy="140" r="54" stroke="currentColor" stroke-width="1.6"/><circle cx="100" cy="140" r="46" stroke="currentColor" stroke-opacity=".5"/><circle cx="100" cy="128" r="12" fill="currentColor"/><path d="M93 136l-6 26h26l-6-26z" fill="currentColor"/><path d="M100 60v20M100 200v20M30 140h16M154 140h16" stroke="currentColor" stroke-opacity=".6"/><text x="100" y="250" text-anchor="middle" fill="currentColor" font-family="EB Garamond, serif" font-size="19" letter-spacing="3">${strings.wordmark}</text></svg>`
}

/** Pause motion holds for the page: a re-render of the landing keeps it. */
let still = false

/** A cubic-bezier easing as a function of progress, the curve CSS would draw for the same four numbers. */
function bezier(x1: number, y1: number, x2: number, y2: number): (x: number) => number {
  const at = (a: number, b: number, t: number): number => 3 * a * t * (1 - t) * (1 - t) + 3 * b * t * t * (1 - t) + t * t * t
  return (x) => {
    let lo = 0
    let hi = 1
    let t = x
    for (let k = 0; k < 30; k++) {
      const v = at(x1, x2, t)
      if (Math.abs(v - x) < 1e-6) break
      if (v < x) lo = t
      else hi = t
      t = (lo + hi) / 2
    }
    return at(y1, y2, t)
  }
}

/** The one curve over the whole 360-degree turn, so the card and the panel share it across the hand-over. */
const SPIN_CURVE = bezier(0.5, 0, 0.2, 1)
const easeOut = (q: number): number => 1 - (1 - q) ** 3
const easeIn = (q: number): number => q ** 3
/** `n + 1` keyframes of `frame(q)` for q from 0 to 1. */
const sampled = (frame: (q: number) => { transform: string }, n: number): { transform: string }[] =>
  Array.from({ length: n + 1 }, (_, k) => frame(k / n))

/** Where the turn reaches 270 degrees (edge-on): the card hands over to the panel there. */
const P_SWAP = ((): number => {
  let lo = 0
  let hi = 1
  for (let k = 0; k < 30; k++) {
    const mid = (lo + hi) / 2
    if (SPIN_CURVE(mid) < 0.75) lo = mid
    else hi = mid
  }
  return (lo + hi) / 2
})()

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className = '',
  ...children: (Node | string)[]
): HTMLElementTagNameMap[K] {
  const made = document.createElement(tag)
  if (className !== '') made.className = className
  made.append(...children)
  return made
}

/** Decorative markup (icons, the keyhole, corners), parsed once per use. */
function art(markup: string): Element {
  const template = document.createElement('template')
  template.innerHTML = markup
  const first = template.content.firstElementChild
  if (first === null) throw new Error('empty art')
  return first
}

function hidden<T extends HTMLElement>(node: T): T {
  node.setAttribute('aria-hidden', 'true')
  return node
}

/** The four gilt corner flourishes of a card face or the panel. */
function corners(): Element[] {
  return ['is-tl', 'is-tr', 'is-bl', 'is-br'].map((corner) => {
    const flourish = art(CORNER)
    flourish.classList.add(corner)
    return flourish
  })
}

function kbd(key: string): HTMLElement {
  return element('kbd', 'chooser-kbd', key)
}

function sourced(video: HTMLVideoElement, sources: VideoSources): void {
  video.poster = sources.poster
  for (const [src, type] of [
    [sources.webm, 'video/webm'],
    [sources.mp4, 'video/mp4'],
  ] as const) {
    const source = document.createElement('source')
    source.src = src
    source.type = type
    video.append(source)
  }
}

/** Plays a muted video, quietly doing nothing if the browser refuses. */
function play(video: HTMLVideoElement): void {
  void video.play().catch(() => undefined)
}

/** A wizard's line in character: the portrait, the name shown (a screen reader hears the hidden prefix), the line. */
function voice(wizard: Wizard, line: string): HTMLElement {
  const words = element('p', 'wizard-line', speakerPrefix(wizard), hidden(element('span', 'chooser-voice-name label', NAMES[wizard])), line)
  return element('div', 'chooser-voice', wizardPortrait(wizard, 48), words)
}

/** "{n} puzzles"-style chip: the number in mono, the words after it. */
function fact(template: string, n: number | string): HTMLElement {
  const [before, after] = template.split('{n}')
  return element('span', 'chooser-fact body-md', before, element('b', '', String(n)), after)
}

interface Cycler {
  /** Shows these photos in turn, the first at once. */
  set: (urls: readonly string[]) => void
  start: () => void
  stop: () => void
}

export interface ChooserOptions {
  /** The first Demo room; undefined with none listed, or when `GET /rooms` failed (`failed`). */
  first: RoomSummary | undefined
  failed: boolean
  profile: string
  /** Starts a Session on the room through the landing's guarded `roomStarter`; its refusal shows in `banners`. */
  start: (room: RoomSummary) => Promise<void>
  /** The session-start-refused banner slot, at the top of the Play back's details. */
  banners: HTMLElement
  /** "Try again" after a failed listing. */
  onRetry: () => void
  /** The Access-code build's accepted code: opens the Capture screen. */
  onAccepted: (buildsLeft: number) => void
}

export interface Chooser {
  element: HTMLElement
  /** The first Demo room's photo count, once its `PlayView` has answered: the Play card then cycles every photo. */
  showPhotos: (count: number) => void
  /** Runs once the chooser is in the page: lays it out, deals the cards in and starts the loops; returns the teardown. */
  mount: () => () => void
}

type State = 'arriving' | 'rest' | 'choosing' | 'chosen' | 'returning'

/**
 * The Hosted landing's first screen, the hero-select chooser (DESIGN.md Hosted landing and Motion, EXPERIENCE.md
 * Hosted landing): the pitch over three tall gilt cards in a shallow arc on a gilt floor ring under the lamp, Watch
 * the demo, Play the sample room and Build your own, each a real button named by its title and described by its line.
 * They are dealt in with a 540-degree spin and breathe at rest, Play leading while a Demo room is listed (a little
 * forward, lit, its prompt shown, the other two a step back), so the first move is plain; its tag says no upload is
 * needed and Build's that an access code is. Hover or focus brings a card forward into the light
 * (it lifts, squares up, tilts toward the pointer and shows its prompt) while the other two step back and dim. Choosing
 * one (click, Enter or Space) gives it one full turn, handing over at the edge-on moment to one shared back panel, a
 * modal dialog that finishes the turn: Watch plays the captioned tutorial larger with controls, the real play-through a
 * tab away; Play plays the same tutorial on its left over a strip of the first Demo room's photos, beside the room, its
 * hosts, how to play and "Play this room" (the guarded start, "Opening the room…" while pending); Build holds
 * the three steps and the Access-code build. Escape, Back or a click on the bare stage turns it home, focus returning
 * to the card. The cards are one Tab stop, Play first; arrows, Home and End move between them; Tab is trapped in the
 * dialog and everything outside it is inert, but for "Play intro", which the chooser puts at the top bar's right end on
 * mount and which reopens the full-screen intro (`intro.ts`) from the landing and from every back. The footer holds the
 * key hints and Pause motion, which holds every loop still. On the first visit the intro shows by itself on mount and
 * the cards are dealt in once it is gone. Under reduced motion nothing
 * deals, spins or loops and every change is a 160 ms crossfade. With no Demo room listed, or a failed listing, Watch and
 * Build stay whole and the Play back holds the no-room line or the failed line with "Try again".
 */
export function chooser({ first, failed, profile, start, banners, onRetry, onAccepted }: ChooserOptions): Chooser {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches
  const section = element('section', 'chooser')
  if (!reduced) section.classList.add('is-arriving', 'is-pre')
  section.classList.toggle('is-still', still)

  // ---- atmosphere: the lamp cone and the dust in it ----
  const motes = element('div', 'chooser-motes')
  for (let k = 0; k < MOTES; k++) {
    const mote = element('i', 'chooser-mote')
    const spread = Math.random() * 2 - 1
    const x = 50 + spread * Math.abs(spread) * 24
    mote.style.cssText =
      `left:${x.toFixed(1)}%;--s:${(2 + Math.random() * 3.5).toFixed(1)}px;--d:${(10 + Math.random() * 9).toFixed(1)}s;` +
      `--delay:${(-Math.random() * 18).toFixed(1)}s;--dx:${((Math.random() * 2 - 1) * 60).toFixed(0)}px;` +
      `--a:${(0.25 + Math.random() * 0.5).toFixed(2)};--p:${Math.random().toFixed(2)}`
    motes.append(mote)
  }
  const atmos = hidden(element('div', 'chooser-atmos', element('div', 'chooser-beam'), motes))

  // ---- the pitch ----
  const heading = element('h1', 'chooser-heading display-lg', strings.landingSubtitle)
  const pitch = element('header', 'chooser-pitch', heading, element('p', 'chooser-subline wizard-line', strings.chooserSubline))

  // ---- the three cards ----
  const titles = [strings.watchCardTitle, strings.playSampleRoom, strings.buildCardTitle]
  const order: number[] = first === undefined ? [] : [first.cover_photo]
  /** The card that leads at rest, forward and lit with its prompt shown: Play, while a Demo room is listed. */
  const lead = first === undefined ? -1 : 1

  /**
   * A card's slot in the arc with its nested planes, its front (art over plate) and its keyhole back; `named` holds the
   * ids of the tags its button's name reads after the title.
   */
  function card(
    i: number,
    medal: string,
    artwork: HTMLElement,
    eyebrow: string,
    tags: HTMLElement[],
    line: (Node | string)[],
    prompt: string,
    named: string[] = [],
  ) {
    const title = element('h2', 'chooser-title', titles[i])
    title.id = `chooser-title-${i}`
    const description = element('p', 'chooser-line', ...line)
    description.id = `chooser-line-${i}`
    const plate = element(
      'div',
      'chooser-plate',
      element('div', 'chooser-plate-top', hidden(element('span', 'chooser-eyebrow', eyebrow)), ...tags),
      title,
      description,
      hidden(element('span', 'chooser-prompt', kbd(strings.keyEnter), prompt)),
    )
    const glint = element('div', 'chooser-glint')
    const choose = element('button', 'chooser-choose')
    choose.type = 'button'
    choose.setAttribute('aria-labelledby', [title.id, ...named].join(' '))
    choose.setAttribute('aria-describedby', description.id)
    choose.setAttribute('aria-haspopup', 'dialog')
    choose.setAttribute('aria-expanded', 'false')
    choose.setAttribute('aria-controls', 'chooser-panel')
    const front = element(
      'div',
      'chooser-face chooser-front',
      artwork,
      plate,
      element('div', 'chooser-dim'),
      element('div', 'chooser-clip', glint),
      element('div', 'chooser-shine'),
      hidden(element('div', 'chooser-medal')),
      ...corners(),
      choose,
    )
    front.querySelector('.chooser-medal')?.append(art(medal))
    const reverse = hidden(element('div', 'chooser-face chooser-reverse'))
    reverse.append(art(keyholeArt(`chooser-lattice-${i}`)))
    const turning = element('div', 'chooser-card', hidden(element('div', 'chooser-glow')), front, reverse)
    const tilt = element('div', 'chooser-tilt', turning)
    const deal = element('div', 'chooser-deal', element('div', 'chooser-breath', tilt))
    const slot = element('div', 'chooser-slot', deal)
    slot.dataset.i = String(i)
    return { slot, deal, card: turning, tilt, glint, reverse, choose, front }
  }

  function tagChip(text: string, variant = ''): HTMLElement {
    return hidden(element('span', `chooser-tag ${variant}`.trim(), element('i'), text))
  }

  // Watch: the card's own loop of the clip, muted, with its own pause toggle (WCAG 2.2.2).
  const frontVideo = element('video')
  frontVideo.className = 'chooser-front-video'
  frontVideo.defaultMuted = true
  frontVideo.muted = true
  frontVideo.loop = true
  frontVideo.playsInline = true
  frontVideo.preload = 'auto'
  frontVideo.tabIndex = -1
  hidden(frontVideo)
  sourced(frontVideo, CLIP_CARD)
  const watch = card(
    0,
    MEDAL_PLAY,
    element('div', 'chooser-art', element('div', 'chooser-vwin', frontVideo)),
    strings.watchCardEyebrow,
    [tagChip(strings.watchCardTag)],
    [strings.watchCardLine],
    strings.watchCardPrompt,
  )
  const clipToggle = element('button', 'chooser-clip-toggle')
  clipToggle.type = 'button'
  clipToggle.hidden = reduced
  watch.front.append(clipToggle)

  // Play: the first Demo room's photos crossfading, or the keyhole when no room is listed.
  const frontPhotos = element('div', 'chooser-art')
  const playTag = tagChip(first === undefined ? '' : first.puzzle_count === 1 ? strings.onePuzzle : fill(strings.puzzleCount, { n: first.puzzle_count }))
  playTag.hidden = first === undefined
  let playLine: (Node | string)[]
  if (first !== undefined) {
    const puzzles = first.puzzle_count === 1 ? strings.onePuzzle : fill(strings.puzzleCount, { n: first.puzzle_count })
    playLine = [`${roomTitle(first)}.`, ' ', element('span', 'chooser-meta', fill(strings.demoRoomMeta, { puzzles }))]
  } else {
    playLine = [failed ? strings.demoRoomsFailed : strings.sampleRoomSoon]
    frontPhotos.append(element('div', 'chooser-placeholder'))
    frontPhotos.firstElementChild?.append(art(keyholeArt('chooser-lattice-none')))
  }
  const playTags = [playTag, ...(first === undefined ? [] : [tagChip(strings.noUploadNeeded, 'is-lamp')])]
  const playCard = card(1, MEDAL_KEY, frontPhotos, strings.playCardEyebrow, playTags, playLine, strings.playCardPrompt)

  // Build: a hand of the room's photos (none with no room listed) over the four wizards, lit in turn.
  const fan = element('div', 'chooser-fan')
  const heroes = element(
    'div',
    'chooser-heroes',
    ...WIZARDS.map((wizard, k) => {
      const image = element('img')
      image.src = portraitUrl(wizard)
      image.alt = ''
      image.addEventListener('error', () => image.remove())
      const hero = element(
        'div',
        'chooser-hero',
        element('div', 'chooser-hero-win', image, element('i', 'chooser-hero-ring')),
        element('span', 'chooser-hero-name', HEROES[wizard]),
      )
      hero.style.setProperty('--k', String(k))
      return hero
    }),
  )
  const buildArt = hidden(element('div', 'chooser-art chooser-build-art', ...(first === undefined ? [] : [fan]), heroes))
  buildArt.classList.toggle('is-portraits-only', first === undefined)
  // The code is asked for before the card is chosen: its tag sits beside the time and its button's name reads it.
  const codeTag = tagChip(strings.accessCodeRequired)
  codeTag.id = 'chooser-code-tag'
  const build = card(
    2,
    MEDAL_CAMERA,
    buildArt,
    strings.buildCardEyebrow,
    [tagChip(strings.buildCardTag), codeTag],
    [strings.buildCardLine],
    strings.buildCardPrompt,
    [codeTag.id],
  )

  const cards = [watch, playCard, build]
  /**
   * The group's one Tab stop is the card last focused, Play to begin with; the Watch card's clip toggle is a stop only
   * after the Watch card (Pause motion in the footer pauses the clip from anywhere).
   */
  function rove(i: number): void {
    cards.forEach(({ choose: button }, k) => {
      button.tabIndex = k === i ? 0 : -1
    })
    clipToggle.tabIndex = i === 0 ? 0 : -1
  }
  rove(Math.max(lead, 0))
  const slots = cards.map(({ slot }) => slot)
  const row = element('div', 'chooser-row', ...slots)
  row.setAttribute('role', 'group')
  row.setAttribute('aria-label', strings.chooserGroup)

  // ---- the floor: the ring, a shadow and a pool of light under each card ----
  const track = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  track.setAttribute('class', 'chooser-track')
  track.setAttribute('aria-hidden', 'true')
  const shadows = slots.map(() => hidden(element('div', 'chooser-shadow')))
  const pools = slots.map(() => hidden(element('div', 'chooser-pool')))

  // ---- the back panel ----
  const flash = hidden(element('div', 'chooser-flash'))
  const panel = element('section', 'chooser-panel')
  panel.id = 'chooser-panel'
  panel.setAttribute('role', 'dialog')
  panel.setAttribute('aria-modal', 'true')
  panel.hidden = true
  const layer = element('div', 'chooser-panel-layer', panel)

  function backButton(): HTMLButtonElement {
    const back = element('button', 'chooser-back label', art(BACK_ICON), strings.back, kbd(strings.keyEsc))
    back.type = 'button'
    back.setAttribute('aria-label', strings.backToCards)
    back.addEventListener('click', () => goHome())
    return back
  }
  function head(title: string, ...end: HTMLElement[]): HTMLElement {
    return element('div', 'chooser-panel-head', backButton(), element('h2', 'chooser-panel-title display-md', title), element('span', 'chooser-grow'), ...end)
  }
  /** Turns the panel home, then opens the card `target`. */
  function goto(target: number): Promise<void> {
    goHome(() => choose(target))
    return Promise.resolve()
  }

  // Watch back: two tabs, the captioned tutorial first and the real play-through, each video larger with native controls.
  function watchVideo(sources: VideoSources, label: string): HTMLVideoElement {
    const video = element('video')
    video.controls = true
    video.defaultMuted = true
    video.muted = true
    video.loop = true
    video.playsInline = true
    video.preload = 'metadata'
    video.tabIndex = 0
    video.setAttribute('aria-label', label)
    sourced(video, sources)
    return video
  }
  const tutorialVideo = watchVideo(TUTORIAL, strings.tutorialLabel)
  const panelVideo = watchVideo(DEMO_VIDEO, strings.clipLabel)
  const watchVideos = [tutorialVideo, panelVideo]
  // The tutorial's accessible description is its five captions, which are burned into the video.
  const tutorialLines = [strings.tutorialLine1, strings.tutorialLine2, strings.tutorialLine3, strings.tutorialLine4, strings.tutorialLine5]
  const described = element('p', '', tutorialLines.join(' '))
  described.id = 'chooser-tutorial-lines'
  described.hidden = true
  tutorialVideo.setAttribute('aria-describedby', described.id)
  const watchBoxes = watchVideos.map((video, k) => element('div', 'chooser-watch-video', video, ...(k === 0 ? [described] : [])))
  const watchTabs = [strings.watchTabTutorial, strings.watchTabPlayThrough].map((label, k) => {
    const tab = element('button', 'chooser-tab label', label)
    tab.type = 'button'
    tab.id = `chooser-watch-tab-${k}`
    const box = watchBoxes[k]
    box.id = `chooser-watch-panel-${k}`
    tab.setAttribute('role', 'tab')
    tab.setAttribute('aria-controls', box.id)
    box.setAttribute('role', 'tabpanel')
    box.setAttribute('aria-labelledby', tab.id)
    return tab
  })
  const tablist = element('div', 'chooser-tabs', ...watchTabs)
  tablist.setAttribute('role', 'tablist')
  tablist.setAttribute('aria-label', strings.watchTabs)
  const watchTags = [tagChip(strings.tutorialTag), tagChip(strings.watchBackTag)]
  const watchHead = head(strings.tutorialCaption, tablist, ...watchTags)
  const watchTitle = watchHead.querySelector('h2')
  let watchTab = 0
  /** Shows tab `k`'s video, heading and tag, pausing the other video. */
  function showTab(k: number): void {
    watchTab = k
    watchTabs.forEach((tab, n) => {
      tab.setAttribute('aria-selected', String(n === k))
      tab.tabIndex = n === k ? 0 : -1
      watchBoxes[n].hidden = n !== k
      watchTags[n].hidden = n !== k
      if (n !== k) watchVideos[n].pause()
    })
    if (watchTitle !== null) watchTitle.textContent = k === 0 ? strings.tutorialCaption : strings.clipCaption
  }
  showTab(watchTab)
  /** Selects tab `k` by the player's hand: its video plays from the start (never under reduced motion or Pause motion). */
  function selectTab(k: number, focus: boolean): void {
    if (k !== watchTab) {
      showTab(k)
      if (!reduced && !still) {
        watchVideos[k].currentTime = 0
        play(watchVideos[k])
      }
    }
    if (focus) watchTabs[k].focus()
  }
  watchTabs.forEach((tab, i) => {
    tab.addEventListener('click', () => selectTab(i, false))
    tab.addEventListener('keydown', (event) => {
      const next: Record<string, number> = { ArrowRight: (i + 1) % 2, ArrowLeft: (i + 1) % 2, Home: 0, End: 1 }
      if (!(event.key in next)) return
      event.preventDefault()
      selectTab(next[event.key], true)
    })
  })
  const watchActions = element('div', 'chooser-actions', secondaryButton({ label: strings.buildCardTitle, onActivate: () => void goto(2) }))
  if (first !== undefined) {
    watchActions.append(primaryButton({ label: strings.playSampleRoom, pendingLabel: strings.playSampleRoom, onActivate: () => goto(1) }))
  }
  const watchView = element(
    'div',
    'chooser-view',
    watchHead,
    ...watchBoxes,
    element('div', 'chooser-watch-foot', voice('trickster', strings.tricksterVoice), watchActions),
  )

  // Play back: the tutorial over a strip of the room's photos (owner request Oct 30), beside the room, its facts, its
  // hosts, how to play and the guarded start; or the no-room or failed line.
  const playVideo = watchVideo(TUTORIAL, strings.tutorialLabel)
  playVideo.setAttribute('aria-describedby', described.id)
  const count = element('span', 'chooser-count mono-sm')
  const strip = hidden(element('div', 'chooser-play-strip'))
  const photoFact = element('span')
  const thumbs = hidden(element('div', 'chooser-vis is-thumbs'))
  let playView: HTMLElement
  let playFocus: HTMLElement
  if (first !== undefined) {
    const playButton = primaryButton({ label: strings.playThisRoom, pendingLabel: strings.openingRoom, onActivate: () => start(first) })
    playFocus = playButton
    const actions = element('div', 'chooser-play-actions', playButton)
    const link = buildViewLink(first.job_id, profile)
    if (link !== null) actions.append(link)
    const howto = element(
      'ol',
      'chooser-howto',
      ...[strings.howToPlay1, strings.howToPlay2, strings.howToPlay3].map((step, k) =>
        element('li', 'body-md', hidden(element('span', 'chooser-howto-n wizard-line', String(k + 1))), element('span', '', step)),
      ),
    )
    howto.setAttribute('aria-label', strings.howToPlay)
    const hosts = element(
      'ul',
      'chooser-hosts chooser-hosts-block',
      ...WIZARDS.map((wizard) =>
        element('li', '', wizardPortrait(wizard, 48), element('div', '', element('b', 'label', NAMES[wizard]), element('span', 'body-md', ROLES[wizard]))),
      ),
    )
    hosts.setAttribute('aria-label', strings.theWizards)
    const puzzles = fact(strings.puzzleCount, first.puzzle_count)
    const facts = element('div', 'chooser-facts', puzzles, fact(strings.minutesRange, '15–25'), photoFact)
    playView = element(
      'div',
      'chooser-view',
      head(roomTitle(first), hidden(element('span', 'chooser-eyebrow', strings.playCardEyebrow))),
      element(
        'div',
        'chooser-play-body',
        element('div', 'chooser-play-media', element('div', 'chooser-watch-video chooser-play-video', playVideo), strip),
        element(
          'div',
          'chooser-play-info',
          banners,
          facts,
          voice('riddler', strings.riddlerVoice),
          element('p', 'chooser-sub chooser-hosts-block label', strings.yourHosts),
          hosts,
          hidden(element('p', 'chooser-sub label', strings.howToPlay)),
          howto,
          actions,
        ),
      ),
    )
  } else {
    playFocus = failed
      ? secondaryButton({ label: strings.tryAgain, onActivate: onRetry })
      : secondaryButton({ label: strings.buildCardTitle, onActivate: () => void goto(2) })
    playView = element(
      'div',
      'chooser-view',
      head(strings.playSampleRoom),
      element('div', 'chooser-play-state', element('p', 'body-md', failed ? strings.demoRoomsFailed : strings.sampleRoomSoon), playFocus),
    )
  }

  // Build back: the three steps and the Access-code build, unchanged in behaviour.
  const step = (n: number, picture: HTMLElement, title: string, body: string): HTMLElement =>
    element(
      'li',
      '',
      hidden(element('span', 'chooser-step-num', String(n))),
      picture,
      element('span', 'chooser-step-title', title),
      element('span', 'chooser-step-body body-md', body),
    )
  const solvedChips = hidden(
    element(
      'div',
      'chooser-vis is-solved',
      element('span', 'chooser-step-chip label', fill(strings.puzzleHeading, { n: 1 })),
      element('span', 'chooser-step-chip is-ok label', strings.solved),
    ),
  )
  const steps = element(
    'ol',
    'chooser-steps',
    step(1, thumbs, strings.buildStep1, strings.buildStep1Body),
    step(2, hidden(element('div', 'chooser-vis is-mini', ...WIZARDS.map((wizard) => wizardPortrait(wizard, 48)))), strings.buildStep2, strings.buildStep2Body),
    step(3, solvedChips, strings.buildStep3, strings.buildStep3Body),
  )
  const intro = element(
    'div',
    'chooser-code-intro',
    element('h3', 'chooser-code-ask display-sm', strings.accessCodeAsk),
    element('p', 'chooser-code-note body-md', strings.accessCodeNote),
  )
  if (first !== undefined && !CUT_0) {
    const link = element('a', 'chooser-link', strings.howARoomIsBuilt)
    link.href = buildViewHref(first.job_id, profile)
    intro.append(link)
  }
  // Under the field, where a judge looks for it: the code is in the submission.
  const judges = element('p', 'chooser-code-judges body-md', strings.accessCodeJudges)
  judges.id = 'chooser-code-judges'
  const buildView = element(
    'div',
    'chooser-view',
    head(strings.buildYourOwnRoom, voice('architect', strings.architectVoice)),
    steps,
    element('div', 'chooser-code-box', intro, element('div', 'chooser-code-form', accessCodeBuild(onAccepted, { heading: false }), judges)),
  )
  // The field is described by that line too, after its own status line.
  const field = buildView.querySelector(`#${ACCESS_CODE_FIELD}`)
  field?.setAttribute('aria-describedby', `${field.getAttribute('aria-describedby') ?? ''} ${judges.id}`.trim())
  const views = [watchView, playView, buildView]
  for (const view of views) view.hidden = true
  panel.append(...views, ...corners())

  const stage = element('div', 'chooser-stage', track, ...shadows, ...pools, row, flash, layer)

  // ---- the footer: key hints and Pause motion ----
  const hint = (only: string, ...parts: (Node | string)[]): HTMLElement => element('span', `chooser-hint ${only}`, ...parts)
  const hints = hidden(
    element(
      'div',
      'chooser-hints',
      hint('is-rest-only', kbd(strings.keyLeft), kbd(strings.keyRight), ` ${strings.keysLook}`),
      hint('is-rest-only', kbd(strings.keyEnter), ` ${strings.keysChoose}`),
      hint('is-chosen-only', kbd(strings.keyTab), ` ${strings.keysMove}`),
      hint('is-chosen-only', kbd(strings.keyEsc), ` ${strings.keysBack}`),
    ),
  )
  const stillToggle = element('button', 'chooser-still-toggle label')
  stillToggle.type = 'button'
  stillToggle.setAttribute('aria-pressed', String(still))
  stillToggle.append(...Array.from(art(`<span>${STILL_ICONS}</span>`).childNodes), strings.pauseMotion)
  // "Play intro", the play screen's quiet top-bar button, goes to the top bar's right end on mount (owner request Oct 30).
  const introButton = secondaryButton({ label: strings.playIntro, onActivate: () => reopenIntro() })
  const keys = element('footer', 'chooser-keys body-sm', hints, element('div', 'chooser-keys-end', stillToggle))

  section.append(atmos, pitch, stage, keys)

  // ---- state ----
  let state: State = reduced ? 'rest' : 'arriving'
  let active = -1
  let chosen = -1
  let pointerInside = false
  let queuedHome = false
  let clipPausedByUser = false
  let mounted = false
  let introShown: Intro | null = null
  /** The intro reopened by hand is showing: the chooser's own keys wait for it. */
  let introOpen = false
  let raf = 0
  let announceTimer: ReturnType<typeof setTimeout> | undefined
  let lastAnnounced = ''
  const timers = new Set<ReturnType<typeof setTimeout>>()
  function later(run: () => void, ms: number): void {
    const timer = setTimeout(() => {
      timers.delete(timer)
      run()
    }, ms)
    timers.add(timer)
  }

  // ---- the clip and the photo cyclers ----
  function startFrontVideo(): void {
    if (!mounted || reduced || still || clipPausedByUser || document.hidden || chosen !== -1) return
    play(frontVideo)
  }
  function showClipState(): void {
    const playing = !frontVideo.paused
    clipToggle.replaceChildren(art(playing ? CLIP_PAUSE_ICON : CLIP_PLAY_ICON))
    clipToggle.setAttribute('aria-label', playing ? strings.clipPauseName : strings.clipPlayName)
  }
  showClipState()
  frontVideo.addEventListener('play', showClipState)
  frontVideo.addEventListener('pause', showClipState)
  clipToggle.addEventListener('click', () => {
    clipPausedByUser = !frontVideo.paused
    if (clipPausedByUser) frontVideo.pause()
    else play(frontVideo)
  })

  function cycler(container: HTMLElement, hold: number): Cycler {
    let images: HTMLImageElement[] = []
    let shown = 0
    let timer: ReturnType<typeof setInterval> | undefined
    function show(next: number): void {
      const previous = images[shown]
      shown = next % images.length
      const image = images[shown]
      image.style.zIndex = '1'
      previous.style.zIndex = '0'
      image.classList.remove('is-on')
      void image.offsetWidth // restarts the drift: one read per hold, never per frame
      image.classList.add('is-on')
      setTimeout(() => {
        if (images[shown] !== previous) previous.classList.remove('is-on')
      }, 1300)
    }
    const cycle: Cycler = {
      set(urls) {
        const running = timer !== undefined
        cycle.stop()
        for (const image of images) image.remove()
        images = urls.map((url) => {
          const image = element('img', 'chooser-photo')
          image.src = url
          image.alt = ''
          image.decoding = 'async'
          return image
        })
        container.prepend(...images)
        shown = 0
        images[0]?.classList.add('is-on')
        if (running) cycle.start()
      },
      start() {
        if (timer !== undefined || reduced || still || images.length < 2) return
        timer = setInterval(() => {
          if (!document.hidden) show(shown + 1)
        }, hold)
      },
      stop() {
        clearInterval(timer)
        timer = undefined
      },
    }
    return cycle
  }
  const frontCycler = cycler(frontPhotos, HOLD_CARD_MS)

  /** Fills every place the first Demo room's photos show, `order` its photo indices, the cover first. */
  function showOrder(): void {
    if (first === undefined) return
    const urls = order.map((n) => photoUrl(first.room_id, n))
    const at = (k: number): string => urls[k % urls.length]
    frontCycler.set(urls)
    const known = urls.length > 1
    const figures = (known && urls.length >= 3 ? [[2, -1], [4, 1], [0, 0]] : [[0, 0]]).map(([k, i]) => {
      const image = element('img')
      image.src = at(k)
      image.alt = ''
      const figure = element('figure', '', image)
      figure.style.setProperty('--i', String(i))
      return figure
    })
    fan.replaceChildren(...figures)
    // Three photos spread through the room, the cover first.
    strip.replaceChildren(
      ...urls.filter((_, k) => k % Math.ceil(urls.length / 3) === 0).map((url) => {
        const image = element('img', 'chooser-still')
        image.src = url
        image.alt = ''
        return element('div', '', image)
      }),
      count,
    )
    thumbs.replaceChildren(
      ...urls.slice(0, 5).map((url, k, shown) => {
        const image = element('img')
        image.src = url
        image.alt = ''
        image.style.setProperty('--r', `${(k - (shown.length - 1) / 2) * 7}deg`)
        return image
      }),
    )
    count.textContent = known ? fill(strings.photoCount, { n: urls.length }) : ''
    photoFact.replaceChildren(...(known ? [fact(strings.photoCount, urls.length)] : []))
  }
  showOrder()

  // ---- layout: on mount and resize only; everything per frame reads this cache ----
  const geo = {
    W: 320,
    H: 500,
    gap: 52,
    dx: [0, 0, 0],
    row: { left: 0, top: 0, width: 0, height: 0 },
    panel: [] as { w: number; h: number | null }[],
  }
  function readRow(): void {
    const box = row.getBoundingClientRect()
    geo.row = { left: box.left, top: box.top, width: box.width, height: box.height }
  }
  /**
   * Sizes the cards from the stage, its height first and then its width, so the trio fills it at every desktop size:
   * H = the stage height less 80 px for the medals and the floor (at least 360), W = 0.64 H, and no card wider than a
   * 3.3th of the width less 96 px, which keeps the arc clear of the edges (owner fix over the prototype, Oct 29: its
   * cards stopped growing at 740 px and left a 1920 x 1080 stage half empty).
   */
  function layout(): void {
    readRow()
    const vw = geo.row.width
    const sh = geo.row.height
    let H = Math.round(Math.max(360, sh - 80))
    let W = Math.round(H * 0.64)
    const maxW = Math.floor((vw - 96) / 3.3)
    if (W > maxW) {
      W = maxW
      H = Math.min(H, Math.round(W / 0.6))
    }
    const gap = Math.round(W * 0.17)
    Object.assign(geo, { W, H, gap })
    section.style.setProperty('--card-w', `${W}px`)
    section.style.setProperty('--card-h', `${H}px`)
    section.style.setProperty('--gap', `${gap}px`)
    geo.dx = slots.map((_, i) => (1 - i) * (W + gap))
    const ph = Math.min(sh - 20, 780)
    const maxPw = Math.min(vw - 72, 1300)
    const chrome = 26 * 2 + 44 + 16 + 16 + 48 // padding, head, two gaps, foot
    let videoHeight = ph - chrome
    let watchWidth = Math.round(videoHeight * DEMO_VIDEO_ASPECT) + 60
    if (watchWidth > maxPw) {
      watchWidth = maxPw
      videoHeight = Math.round((watchWidth - 60) / DEMO_VIDEO_ASPECT)
    }
    geo.panel = [
      { w: watchWidth, h: videoHeight + chrome },
      first === undefined ? { w: Math.min(maxPw, 720), h: null } : { w: Math.min(maxPw, 1180), h: ph },
      { w: Math.min(maxPw, 1000), h: null },
    ]
    drawFloor()
    if (chosen !== -1) sizePanel(chosen)
    applyAll()
  }

  /** The gilt ring through the three cards' feet, projected as the row's perspective draws them, and a plate each. */
  function drawFloor(): void {
    const { W, H, gap } = geo
    const cx = geo.row.width / 2
    const cy = geo.row.height / 2
    const oy = geo.row.height * 0.42
    const project = (x: number, y: number, z: number): [number, number] => [
      cx + ((x - cx) * P_ROW) / (P_ROW - z),
      oy + ((y - oy) * P_ROW) / (P_ROW - z),
    ]
    const feetY = cy + H / 2
    const feet = slots.map((_, i) => {
      const a = Math.abs(i - 1)
      return project(cx + (i - 1) * (W + gap), feetY + a * 10, -a * 120)
    })
    const [lx, ly] = feet[0]
    const fy = feet[1][1]
    const rx = (cx - lx) * 1.42
    const k = Math.sqrt(1 - 1 / (1.42 * 1.42))
    const ry = Math.max(28, (fy - ly) / (1 - k))
    const ecy = fy - ry + 6
    const plates = feet
      .map(
        ([x, y], i) =>
          `<ellipse cx="${x.toFixed(1)}" cy="${(y + 4).toFixed(1)}" rx="${(W * 0.62).toFixed(1)}" ry="${(ry * 0.34).toFixed(1)}" fill="url(#chooser-plate)" opacity=".55"/>` +
          `<ellipse class="chooser-plate-lit" data-i="${i}" cx="${x.toFixed(1)}" cy="${(y + 4).toFixed(1)}" rx="${(W * 0.66).toFixed(1)}" ry="${(ry * 0.38).toFixed(1)}" fill="url(#chooser-plate-lit)"/>`,
      )
      .join('')
    const ticks = Array.from({ length: 23 }, (_, n) => {
      const t = Math.PI * (0.06 + (0.88 * n) / 22)
      const x = cx + rx * Math.cos(t)
      const y = ecy + ry * Math.sin(t)
      const x2 = cx + (rx + 9) * Math.cos(t)
      const y2 = ecy + (ry + 4) * Math.sin(t)
      return `<path d="M${x.toFixed(1)} ${y.toFixed(1)}L${x2.toFixed(1)} ${y2.toFixed(1)}"/>`
    }).join('')
    track.innerHTML =
      '<defs><linearGradient id="chooser-ring" x1="0" x2="1"><stop offset="0" stop-color="#B08A4E" stop-opacity="0"/><stop offset=".25" stop-color="#B08A4E" stop-opacity=".55"/><stop offset=".5" stop-color="#F4C470" stop-opacity=".8"/><stop offset=".75" stop-color="#B08A4E" stop-opacity=".55"/><stop offset="1" stop-color="#B08A4E" stop-opacity="0"/></linearGradient>' +
      '<radialGradient id="chooser-plate"><stop offset="0" stop-color="#E9A94B" stop-opacity=".32"/><stop offset=".6" stop-color="#E9A94B" stop-opacity=".08"/><stop offset="1" stop-color="#E9A94B" stop-opacity="0"/></radialGradient>' +
      '<radialGradient id="chooser-plate-lit"><stop offset="0" stop-color="#F4C470" stop-opacity=".55"/><stop offset=".55" stop-color="#E9A94B" stop-opacity=".16"/><stop offset="1" stop-color="#E9A94B" stop-opacity="0"/></radialGradient>' +
      `<mask id="chooser-front-half"><rect x="0" y="${ecy.toFixed(1)}" width="100%" height="100%" fill="#fff"/></mask></defs>` +
      `<ellipse cx="${cx}" cy="${ecy.toFixed(1)}" rx="${(rx + 26).toFixed(1)}" ry="${(ry + 10).toFixed(1)}" fill="none" stroke="url(#chooser-ring)" stroke-opacity=".35" stroke-width="1"/>` +
      `<ellipse cx="${cx}" cy="${ecy.toFixed(1)}" rx="${rx.toFixed(1)}" ry="${ry.toFixed(1)}" fill="none" stroke="url(#chooser-ring)" stroke-width="1.5"/>` +
      `<g stroke="#B08A4E" stroke-opacity=".5" stroke-width="1" mask="url(#chooser-front-half)">${ticks}</g>${plates}`
    shadows.forEach((shadow, i) => {
      shadow.style.left = `${feet[i][0]}px`
      shadow.style.top = `${feet[i][1] - 6}px`
    })
    pools.forEach((pool, i) => {
      pool.style.left = `${feet[i][0]}px`
      pool.style.top = `${feet[i][1] - 30}px`
    })
  }

  // ---- the arc: each card's place for the state ----
  function transformFor(i: number): string {
    const p = i - 1
    const a = Math.abs(p)
    if (chosen !== -1) {
      if (i === chosen) return `translate3d(${geo.dx[i]}px, 0, 0)`
      const side = Math.sign(i - chosen)
      return `translate3d(${side * (window.innerWidth * 0.75 + geo.W)}px, 30px, -420px) rotateY(${-side * 55}deg)`
    }
    if (active === -1 && i === lead) return 'translate3d(0, -6px, 50px)'
    if (active === -1 && lead !== -1) return `translate3d(0, ${a * 10 + 4}px, ${-a * 120 - 50}px) rotateY(${-p * 10}deg)`
    if (active === -1) return `translate3d(0, ${a * 10}px, ${-a * 120}px) rotateY(${-p * 9}deg)`
    if (i === active) return `translate3d(0, -10px, 80px) rotateY(${-p * 3}deg) scale(1.03)`
    return `translate3d(0, ${a * 10 + 8}px, ${-120 * a - 110}px) rotateY(${-p * 12}deg)`
  }
  function applyAll(): void {
    slots.forEach((slot, i) => {
      slot.style.transform = transformFor(i)
      const lit = chosen === -1 && active === i && state === 'rest'
      const leading = chosen === -1 && active === -1 && i === lead && (state === 'rest' || state === 'arriving')
      slot.classList.toggle('is-active', lit)
      slot.classList.toggle('is-lead', leading)
      slot.classList.toggle('is-back', chosen === -1 && active === -1 && lead !== -1 && i !== lead)
      slot.classList.toggle('is-dimmed', chosen === -1 && active !== -1 && active !== i)
      slot.classList.toggle('is-away', chosen !== -1 && chosen !== i)
      slot.classList.toggle('is-chosen', chosen === i)
      shadows[i].classList.toggle('is-lit', lit)
      shadows[i].classList.toggle('is-gone', chosen !== -1)
      pools[i].classList.toggle('is-lit', lit || leading)
      track.querySelector(`.chooser-plate-lit[data-i="${i}"]`)?.classList.toggle('is-on', lit || leading)
    })
  }

  // ---- the pointer tilt: lerped per frame, transform only, from cached geometry ----
  const tilts = cards.map(({ tilt, glint }) => ({ tilt, glint, tx: 0, ty: 0, x: 0, y: 0, gx: 50, gy: 50, cgx: 50, cgy: 50 }))
  function tick(): void {
    raf = 0
    let moving = false
    for (const t of tilts) {
      t.x += (t.tx - t.x) * 0.12
      t.y += (t.ty - t.y) * 0.12
      t.cgx += (t.gx - t.cgx) * 0.15
      t.cgy += (t.gy - t.cgy) * 0.15
      if (Math.abs(t.tx - t.x) > 0.01 || Math.abs(t.ty - t.y) > 0.01 || Math.abs(t.gx - t.cgx) > 0.1 || Math.abs(t.gy - t.cgy) > 0.1) moving = true
      t.tilt.style.transform = `rotateX(${t.y.toFixed(3)}deg) rotateY(${t.x.toFixed(3)}deg)`
      t.glint.style.transform = `translate3d(${t.cgx.toFixed(2)}%, ${t.cgy.toFixed(2)}%, 0)`
    }
    if (moving && mounted) raf = requestAnimationFrame(tick)
  }
  function kick(): void {
    if (raf === 0 && mounted) raf = requestAnimationFrame(tick)
  }
  function setActive(i: number): void {
    if (active === i) return
    active = i
    tilts.forEach((t, k) => {
      if (k !== i) {
        t.tx = 0
        t.ty = 0
      }
    })
    kick()
    applyAll()
  }
  function announceSoon(i: number): void {
    clearTimeout(announceTimer)
    announceTimer = setTimeout(() => {
      if (state !== 'rest' || active !== i || slots[i].contains(document.activeElement)) return
      const line = fill(strings.cardAnnounce, { title: titles[i], n: i + 1 })
      if (line === lastAnnounced) return
      lastAnnounced = line
      announce(line)
    }, ANNOUNCE_MS)
  }
  slots.forEach((slot, i) => {
    slot.addEventListener('pointermove', (event) => {
      if (state !== 'rest' || reduced) return
      const cx = geo.row.left + geo.row.width / 2 - geo.dx[i]
      const cy = geo.row.top + geo.row.height / 2
      const nx = Math.min(1, Math.max(0, (event.clientX - cx) / geo.W + 0.5))
      const ny = Math.min(1, Math.max(0, (event.clientY - cy) / geo.H + 0.5))
      tilts[i].tx = (nx - 0.5) * 16
      tilts[i].ty = (0.5 - ny) * 16
      tilts[i].gx = nx * 100
      tilts[i].gy = ny * 100
      kick()
    })
    slot.addEventListener('pointerenter', () => {
      if (state !== 'rest') return
      cue('cardHover', PAN[i])
      setActive(i)
      announceSoon(i)
    })
    slot.addEventListener('pointerleave', () => {
      tilts[i].tx = 0
      tilts[i].ty = 0
      kick()
    })
  })
  row.addEventListener('pointerenter', () => {
    pointerInside = true
    readRow() // one read per entry, so a scrolled page still tilts true
  })
  row.addEventListener('pointerleave', () => {
    pointerInside = false
    clearTimeout(announceTimer)
    if (state === 'rest') setActive(slots.findIndex((slot) => slot.contains(document.activeElement)))
  })

  // ---- the keyboard: arrows, Home and End move between the cards; Enter and Space choose (native) ----
  cards.forEach(({ choose: button }, i) => {
    button.addEventListener('focus', () => {
      lastAnnounced = ''
      rove(i)
      if (state === 'rest') setActive(i)
    })
    button.addEventListener('click', () => choose(i))
    button.addEventListener('keydown', (event) => {
      if (state !== 'rest') return
      const next: Record<string, number> = {
        ArrowRight: (i + 1) % 3,
        ArrowDown: (i + 1) % 3,
        ArrowLeft: (i + 2) % 3,
        ArrowUp: (i + 2) % 3,
        Home: 0,
        End: 2,
      }
      if (!(event.key in next)) return
      event.preventDefault()
      cards[next[event.key]].choose.focus()
    })
  })
  row.addEventListener('focusout', () => {
    setTimeout(() => {
      if (state === 'rest' && !row.contains(document.activeElement) && !pointerInside) setActive(-1)
    }, 0)
  })
  // A click on the bare stage around the open panel turns it home.
  stage.addEventListener('click', (event) => {
    if (state === 'chosen' && event.target instanceof Node && !panel.contains(event.target)) goHome()
  })
  function onKey(event: KeyboardEvent): void {
    if (introOpen) return
    if (event.key === 'Escape' && state === 'chosen') {
      event.preventDefault()
      goHome()
    } else if (event.key === 'Escape' && state === 'choosing') {
      event.preventDefault()
      queuedHome = true
    } else if (event.key === 'Tab' && state === 'chosen') {
      trapTab(event)
    }
  }
  /**
   * The dialog keeps Tab inside it, cycling its visible controls and then "Play intro" and the sound toggle in the top
   * bar: the browser steps within the panel, and the ring takes over at its ends, into and out of the bar's buttons and
   * from anywhere outside.
   */
  function trapTab(event: KeyboardEvent): void {
    const view = views[chosen]
    const controls = [...view.querySelectorAll<HTMLElement>('button, a[href], input, video[tabindex]')].filter(
      (control) => !(control instanceof HTMLButtonElement && control.disabled) && control.offsetParent !== null,
    )
    if (controls.length === 0) return
    const sound = document.querySelector<HTMLElement>('.top-bar-sound')
    const bar = [introButton, sound].filter((button): button is HTMLElement => button !== null && button.isConnected)
    const ring = [...controls, ...bar]
    const at = document.activeElement
    const k = ring.findIndex((control) => control === at)
    let next: HTMLElement | undefined
    if (k === -1) next = at instanceof Node && panel.contains(at) ? undefined : ring[0]
    else if (event.shiftKey) next = k === 0 || bar.includes(ring[k]) ? ring.at(k - 1) : undefined
    else next = k === ring.length - 1 || bar.includes(ring[k + 1]) ? ring[(k + 1) % ring.length] : undefined
    if (next === undefined) return
    event.preventDefault()
    next.focus()
  }

  // ---- choosing and going home ----
  /**
   * Everything outside the dialog: the top bar but its right end, where "Play intro" and the sound toggle stay live over
   * a card back (WCAG 1.4.2), the row, the footer and the page below the fold.
   */
  function outside(): HTMLElement[] {
    const bar = [...(document.querySelector<HTMLElement>('.top-bar')?.children ?? [])].filter(
      (node): node is HTMLElement => node instanceof HTMLElement && !node.contains(introButton),
    )
    const below = [...(section.parentElement?.children ?? [])].filter(
      (node): node is HTMLElement => node instanceof HTMLElement && node !== section,
    )
    return [...bar, row, keys, ...below]
  }
  function setModal(on: boolean): void {
    for (const node of outside()) node.inert = on
    const scroller = section.parentElement
    if (scroller !== null) {
      if (on) scroller.scrollTop = 0
      scroller.classList.toggle('is-locked', on)
    }
  }
  function sizePanel(i: number): void {
    const size = geo.panel[i]
    panel.style.setProperty('--pw', `${size.w}px`)
    panel.style.setProperty('--ph', size.h === null ? 'auto' : `${size.h}px`)
  }
  function showView(i: number): void {
    views.forEach((view, k) => {
      view.hidden = k !== i
    })
    panel.setAttribute('aria-labelledby', `chooser-title-${i}`)
    sizePanel(i)
  }
  /** The panel's apparent height at the edge-on moment equals the lifted card's: one read per choose and per return. */
  function startScale(): number {
    return ((geo.H * P_ROW) / (P_ROW - LIFT_Z)) / ((panel.offsetHeight * P_PANEL) / (P_PANEL - LIFT_Z))
  }
  function focusPanel(i: number): void {
    const target = i === 0 ? watchVideos[watchTab] : i === 1 ? playFocus : panel.querySelector<HTMLElement>(`#${ACCESS_CODE_FIELD}`)
    target?.focus({ preventScroll: true })
  }
  /** Fades the stage out, makes the change, and fades it back in: every change under reduced motion. */
  function crossfade(swap: () => void): void {
    const out = stage.animate([{ opacity: 1 }, { opacity: 0 }], { duration: FADE_MS, easing: 'ease', fill: 'forwards' })
    out.finished.then(
      () => {
        swap()
        out.cancel()
        stage.animate([{ opacity: 0 }, { opacity: 1 }], { duration: FADE_MS, easing: 'ease' })
      },
      () => undefined, // cancelled by the teardown
    )
  }

  /**
   * The fills a turn leaves on the card, its back, its deal and the panel, held here until the next turn cancels them.
   * Chromium may garbage-collect a finished, filling animation that no script holds: getAnimations() stops listing it,
   * yet its fill stays on the element for good (a back left edge-on and blank), so each is settled by reference.
   */
  let fills: Animation[] = []
  function settle(): void {
    for (const animation of fills) animation.cancel()
    fills = []
  }

  function choose(i: number): void {
    if (state !== 'rest' || !mounted) return
    chosen = i
    active = -1
    queuedHome = false
    clearTimeout(announceTimer)
    for (const t of tilts) Object.assign(t, { tx: 0, ty: 0, gx: 50, gy: 50 })
    kick()
    const { slot, card: turning, deal, reverse, choose: button } = cards[i]
    cue('cardChoose')
    button.setAttribute('aria-expanded', 'true')
    setModal(true)
    section.classList.add('is-chosen')
    frontVideo.pause()
    frontCycler.stop()
    showView(i)
    panel.hidden = false
    panel.style.visibility = 'hidden'
    const s0 = startScale()
    state = 'choosing'
    let opening: Animation | undefined

    const finish = (): void => {
      state = 'chosen'
      opening?.finish() // settle exactly at rest, whatever the frames
      panel.style.visibility = ''
      focusPanel(i)
      if (i === 0 && !reduced && !still) {
        watchVideos[watchTab].currentTime = 0
        play(watchVideos[watchTab])
      }
      if (i === 1 && !reduced && !still) {
        playVideo.currentTime = 0
        play(playVideo)
      }
      if (queuedHome) goHome()
    }

    if (reduced) {
      crossfade(() => {
        slots.forEach((other) => other.classList.add('is-instant'))
        applyAll()
        turning.classList.add('is-gone')
        requestAnimationFrame(() => slots.forEach((other) => other.classList.remove('is-instant')))
        finish()
      })
      return
    }

    const dir = i === 2 ? -1 : 1
    const swapMs = Math.round(T_CHOOSE * P_SWAP)
    slots.forEach((other) => other.classList.remove('is-home'))
    // The slot transition and every animation start in this same task, so they share a start time.
    slot.style.transition = `transform ${swapMs}ms cubic-bezier(0.45, 0, 0.35, 1)`
    applyAll()
    fills = [
      turning.animate(
        sampled((q) => ({ transform: `rotateY(${(dir * 360 * SPIN_CURVE(q * P_SWAP)).toFixed(2)}deg)` }), 14),
        { duration: swapMs, easing: 'linear', fill: 'forwards' },
      ),
      // The back, the face in view near 270 degrees, fades out exactly at edge-on, so the hand-over needs no timer.
      // Opacity goes on the leaf face, never on the preserve-3d card, which would flatten it.
      reverse.animate([{ opacity: 1 }, { opacity: 1, offset: 0.96 }, { opacity: 0 }], { duration: swapMs, fill: 'forwards' }),
      deal.animate([{ transform: 'translate3d(0, 0, 0)' }, { transform: `translate3d(0, 0, ${LIFT_Z}px)` }], {
        duration: swapMs,
        easing: 'cubic-bezier(0.3, 0, 0.4, 1)',
        fill: 'forwards',
      }),
    ]
    panel.style.visibility = ''
    opening = panel.animate(
      sampled((q) => {
        const p = P_SWAP + q * (1 - P_SWAP)
        const e = easeOut(q)
        return {
          transform: `translate3d(0, 0, ${(LIFT_Z * (1 - e)).toFixed(2)}px) rotateY(${(dir * (360 * SPIN_CURVE(p) - 360)).toFixed(2)}deg) scale(${(s0 + (1 - s0) * e).toFixed(4)})`,
        }
      }, 14),
      { duration: T_CHOOSE - swapMs, delay: swapMs, easing: 'linear', fill: 'backwards' },
    )
    flash.animate([{ opacity: 0 }, { opacity: 0.9, offset: 0.35 }, { opacity: 0 }], { duration: 560, delay: swapMs - 180, easing: 'ease-out' })
    later(() => {
      slot.style.transition = ''
      finish()
    }, T_CHOOSE)
  }

  function goHome(then?: () => void): void {
    if (state !== 'chosen') return
    cue('cardClose')
    const i = chosen
    const { slot, card: turning, deal, choose: button } = cards[i]
    tutorialVideo.pause()
    panelVideo.pause()
    playVideo.pause()
    playVideo.currentTime = 0
    state = 'returning'
    section.classList.remove('is-chosen')
    const s0 = startScale()
    const dir = i === 2 ? -1 : 1

    const done = (): void => {
      settle()
      turning.classList.remove('is-gone')
      panel.hidden = true
      panel.style.visibility = ''
      slots.forEach((other) => {
        other.classList.remove('is-home')
        other.style.transition = ''
      })
      setModal(false)
      button.setAttribute('aria-expanded', 'false')
      state = 'rest'
      if (then !== undefined) {
        then()
        return
      }
      button.focus({ preventScroll: true })
      applyAll()
      startFrontVideo()
      frontCycler.start()
    }

    if (reduced) {
      crossfade(() => {
        slots.forEach((other) => other.classList.add('is-instant'))
        chosen = -1
        active = i
        applyAll()
        requestAnimationFrame(() => slots.forEach((other) => other.classList.remove('is-instant')))
        done()
      })
      return
    }
    // The panel turns on to edge-on, then the card finishes the turn from behind and steps back into the line: each a
    // delayed animation or transition started now, so the hand-over is frame-exact and needs no timer midway.
    settle()
    fills = [
      panel.animate(
        sampled((q) => {
          const e = easeIn(q)
          return { transform: `translate3d(0, 0, ${(LIFT_Z * e).toFixed(2)}px) rotateY(${(dir * 90 * e).toFixed(2)}deg) scale(${(1 + (s0 - 1) * e).toFixed(4)})` }
        }, 10),
        { duration: T_RETURN_PANEL, easing: 'linear', fill: 'forwards' },
      ),
      turning.animate(
        sampled((q) => ({ transform: `rotateY(${(dir * (270 + 90 * easeOut(q))).toFixed(2)}deg)` }), 10),
        { duration: T_RETURN_CARD, delay: T_RETURN_PANEL, easing: 'linear', fill: 'both' },
      ),
      deal.animate([{ transform: `translate3d(0, 0, ${LIFT_Z}px)` }, { transform: 'translate3d(0, 0, 0)' }], {
        duration: T_RETURN_CARD,
        delay: T_RETURN_PANEL,
        easing: 'cubic-bezier(0.2, 0.7, 0.3, 1)',
        fill: 'both',
      }),
    ]
    flash.animate([{ opacity: 0 }, { opacity: 0.6, offset: 0.4 }, { opacity: 0 }], { duration: 420, delay: T_RETURN_PANEL - 160, easing: 'ease-out' })
    chosen = -1
    active = i
    slots.forEach((other, k) => {
      if (k !== i) other.classList.add('is-home')
    })
    slot.style.transition = `transform ${T_RETURN_CARD + 140}ms var(--ease-lift) ${T_RETURN_PANEL}ms`
    applyAll()
    later(done, T_RETURN_PANEL + T_RETURN_CARD + 40)
  }

  // ---- Pause motion ----
  stillToggle.addEventListener('click', () => {
    still = !still
    section.classList.toggle('is-still', still)
    stillToggle.setAttribute('aria-pressed', String(still))
    if (still) {
      frontVideo.pause()
      tutorialVideo.pause()
      panelVideo.pause()
      playVideo.pause()
      frontCycler.stop()
      return
    }
    startFrontVideo()
    if (state === 'rest') frontCycler.start()
  })

  // ---- the intro, reopened by hand: no countdown at its end ----
  /** Opens the intro over the landing or a back, the videos behind it paused, so no two play at once. */
  function reopenIntro(): void {
    cue('playIntro')
    introOpen = true
    for (const video of [frontVideo, tutorialVideo, panelVideo, playVideo]) video.pause()
    introShown = openIntro(false)
    void introShown.closed.then(() => {
      introOpen = false
      startFrontVideo()
    })
  }

  // ---- the arrival: dealt in from below with a 540-degree spin, the centre first ----
  function arrive(): void {
    layout()
    if (reduced) return
    cards.forEach(({ deal }, i) => {
      const at = [1, 0, 2][i] * ARRIVE_STAGGER
      deal.animate(
        [
          {
            transform: `translate3d(0, ${window.innerHeight * 0.8}px, -220px) rotateY(-540deg) rotateZ(${(i - 1) * 8}deg) scale(0.8)`,
            easing: 'cubic-bezier(0.25, 0.55, 0.3, 1)',
          },
          { transform: 'translate3d(0, -14px, 40px) rotateY(10deg) rotateZ(0deg) scale(1.01)', offset: 0.78, easing: 'cubic-bezier(0.45, 0, 0.4, 1)' },
          { transform: 'translate3d(0, 0, 0) rotateY(0deg) rotateZ(0deg) scale(1)' },
        ],
        { duration: T_ARRIVE, delay: at, easing: 'linear', fill: 'backwards' },
      )
      shadows[i].animate([{ opacity: 0, transform: 'scale(0.4)' }, { opacity: 1, transform: 'scale(1)' }], {
        duration: 600,
        delay: at + T_ARRIVE * 0.55,
        easing: 'ease-out',
        fill: 'backwards',
      })
    })
    section.classList.remove('is-pre')
    const total = 2 * ARRIVE_STAGGER + T_ARRIVE
    later(() => section.classList.remove('is-arriving'), total - 700)
    later(() => {
      state = 'rest'
      const hovered = slots.findIndex((slot) => slot.matches(':hover'))
      const focused = slots.findIndex((slot) => slot.contains(document.activeElement))
      if (hovered >= 0) setActive(hovered)
      else if (focused >= 0) setActive(focused)
      else applyAll()
    }, total)
  }

  function onVisibility(): void {
    if (document.hidden) frontVideo.pause()
    else startFrontVideo()
  }

  return {
    element: section,
    showPhotos(total) {
      if (first === undefined || total < 1) return
      order.splice(0, order.length, first.cover_photo, ...Array.from({ length: total }, (_, n) => n).filter((n) => n !== first.cover_photo))
      showOrder()
      if (state === 'rest' && chosen === -1) frontCycler.start()
    },
    mount() {
      mounted = true
      let resized = 0
      const observer = new ResizeObserver(() => {
        cancelAnimationFrame(resized)
        resized = requestAnimationFrame(layout)
      })
      document.addEventListener('keydown', onKey, true) // capture: the video's own controls keep Escape otherwise
      document.addEventListener('visibilitychange', onVisibility)
      document.querySelector<HTMLElement>('.top-bar-controls')?.append(introButton)
      if (introDue(reduced)) introShown = openIntro(true)
      // The cards are dealt in once the fonts are in and the intro that showed by itself is gone.
      Promise.all([document.fonts.ready, introShown?.closed]).then(
        () => {
          if (!mounted) return
          arrive()
          observer.observe(row)
          startFrontVideo()
          frontCycler.start()
        },
        () => undefined,
      )
      return () => {
        mounted = false
        observer.disconnect()
        cancelAnimationFrame(resized)
        cancelAnimationFrame(raf)
        clearTimeout(announceTimer)
        for (const timer of timers) clearTimeout(timer)
        for (const animation of section.getAnimations({ subtree: true })) animation.cancel()
        frontVideo.pause()
        tutorialVideo.pause()
        panelVideo.pause()
        playVideo.pause()
        frontCycler.stop()
        document.removeEventListener('keydown', onKey, true)
        document.removeEventListener('visibilitychange', onVisibility)
        if (chosen !== -1) setModal(false)
        introShown?.remove()
        introButton.remove()
      }
    },
  }
}
