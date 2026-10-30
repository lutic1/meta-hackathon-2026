import './story-stage.css'
import type { PlayInteractable } from '../../types'
import { announce } from '../live-region.ts'
import { fill, strings } from '../strings.ts'
import { portraitUrl, type Wizard } from '../wizards/portrait.ts'
import { crop } from './crop.ts'
import { waxSeal } from './wax-seal.ts'

const NAMES: Record<Wizard, string> = {
  architect: strings.architect,
  riddler: strings.riddler,
  guide: strings.guide,
  trickster: strings.trickster,
}

/** Where each painting is framed in its tall arch (spec 1.2). */
const CROPS: Record<Wizard, string> = {
  architect: '28% 40%',
  trickster: '86% 40%',
  riddler: '58% 40%',
  guide: '52% 40%',
}

const PIN =
  '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a7 7 0 0 0-7 ' +
  '7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>'

type Side = 'left' | 'right'

/** One beat: who speaks, who stands on the stage, their role line, the line, and the button that moves on. */
export interface StoryBeat {
  speaker: Wizard
  role: string
  line: string
  button: string
  /** Who stands at either side; the speaker alone at the left when absent. The one who does not speak is dimmed. */
  cast?: Partial<Record<Side, Wizard>>
  /** An intro beat: its place among the intro's beats (page dots, and "Skip intro" shown). */
  page?: { at: number; of: number }
  /** The first riddle under the line: "Riddle 1 of {N}", its place tag and its Clue. */
  riddle?: { heading: string; place: string; clue: string }
  /** A part of the play screen lit through the scrim while the beat shows (the Guide's chest). */
  spot?: HTMLElement
  /** A part of the play screen the speech box stays clear of (the chest's box, on every intro beat; see `fit`). */
  clear?: HTMLElement
  /** A solve beat: the light stage, the shorter portrait and the row "Riddle {n} solved" with its wax seal. */
  solved?: number
  /** The item the solve put in the pack, shown as a crop beside "In your pack now: {label}. …". */
  item?: { roomId: string; interactable: PlayInteractable }
}

/** How a beat ended: its button (or Enter), or "Skip intro". */
export type BeatEnd = 'next' | 'skip'

export interface StoryStage {
  element: HTMLElement
  /** Shows `beat` and resolves once Next or "Skip intro" is pressed. Focus moves to the button. */
  play: (beat: StoryBeat) => Promise<BeatEnd>
  /** Keeps the box as tall as the tallest of `beats` and the button as wide as the widest, until `close`. */
  hold: (beats: StoryBeat[]) => void
  /** Where the box begins, its name plate included (px from the viewport's top): held in one place through the intro. */
  top: () => number
  /** Takes the stage away. */
  close: () => void
}

/** A tall painted portrait in its gilt arch, at one side of the stage. */
function portrait(side: Side): { figure: HTMLElement; painting: HTMLImageElement; wizard: Wizard | null } {
  const figure = document.createElement('figure')
  figure.className = `story-portrait is-${side}`
  const frame = document.createElement('div')
  frame.className = 'story-portrait-frame'
  const painting = document.createElement('img')
  painting.alt = '' // the name plate says who speaks
  frame.append(painting)
  figure.append(frame)
  return { figure, painting, wizard: null }
}

/**
 * The Story stage (story mode, owner decision Oct 29; build spec 1.2): a stage over the Scene, below the top bar, on a
 * scrim rising from the bottom ("light" for a solve beat, so the room stays in view), with up to two tall painted
 * portraits in their gilt arches, one at either side, sliding in from off-screen (the speaker lit, the other dimmed),
 * and the parchment speech box, its tail toward the speaker: a brass name plate with the name and role line, the
 * optional "Riddle {n} solved" row with its wax seal, the line (whole, at once: no typing effect), the optional first
 * riddle inset and pack row, and the footer with an intro beat's page dots and the button with its Enter key cap. An
 * intro beat also shows "Skip intro" at the top right; a beat with a `spot` lights that part through the scrim, and a
 * beat with a `clear` keeps the box off that part, in one place from beat to beat; beats held together (the intro)
 * keep the tallest one's box and the widest one's button, so neither the box's top nor Next moves. Each beat's spoken
 * line goes to the live region once, as "{name}: {line}" (the first riddle's Clue after it); focus moves to the button,
 * and Enter on the page or the stage presses it. The portraits' slide, the box's swap and the seal's stamp belong to
 * DESIGN.md Motion's walk and story exception and are off under reduced motion.
 */
export function storyStage(): StoryStage {
  const element = document.createElement('section')
  element.className = 'story-stage'
  element.hidden = true
  const scrim = document.createElement('div')
  scrim.className = 'story-scrim'
  const slots: Record<Side, ReturnType<typeof portrait>> = { left: portrait('left'), right: portrait('right') }
  const box = document.createElement('div')
  box.className = 'story-box'
  const plate = document.createElement('div')
  plate.className = 'story-plate'
  const name = document.createElement('b')
  const role = document.createElement('small')
  plate.append(name, role)
  const solved = document.createElement('p')
  solved.className = 'story-solved label'
  const line = document.createElement('p')
  line.className = 'story-line'
  const riddle = document.createElement('div')
  riddle.className = 'story-riddle'
  const riddleHead = document.createElement('p')
  riddleHead.className = 'story-riddle-head label'
  const clue = document.createElement('p')
  clue.className = 'story-riddle-clue'
  riddle.append(riddleHead, clue)
  const item = document.createElement('p')
  item.className = 'story-item'
  const foot = document.createElement('div')
  foot.className = 'story-foot'
  const pips = document.createElement('div')
  pips.className = 'story-pips'
  pips.setAttribute('aria-hidden', 'true')
  const next = document.createElement('button')
  next.type = 'button'
  next.className = 'story-next'
  foot.append(pips, next)
  box.append(plate, solved, line, riddle, item, foot)
  const skip = document.createElement('button')
  skip.type = 'button'
  skip.className = 'story-skip'
  skip.textContent = strings.introSkip
  element.append(scrim, slots.left.figure, slots.right.figure, box, skip)

  let settle: (end: BeatEnd) => void = () => undefined
  let waiting = false
  /** The part of the play screen the beats keep the speech box clear of, and the box's place beside it (see `fit`). */
  let clearing: HTMLElement | undefined
  let fitted: { marginLeft: string; width: string } | null = null
  /** The beats held together, the one on the stage, and whether the box and its button fit them (see `reserve`). */
  let held: StoryBeat[] = []
  let shown: StoryBeat | undefined
  let reserved = false
  // The chest's box spans from the chest to the frame's edge, so it resizes when the chest moves (its photo loading).
  const refit = new ResizeObserver(() => {
    fitted = null
    fit(clearing)
    reserve()
  })
  next.addEventListener('click', () => settle('next'))
  skip.addEventListener('click', () => settle('skip'))
  function onKey(event: KeyboardEvent): void {
    if (event.key !== 'Enter' || !waiting || event.target === next || event.target === skip) return
    if (event.target !== document.body && !(event.target instanceof Node && element.contains(event.target))) return
    event.preventDefault()
    settle('next')
  }

  /** Puts `beat`'s cast on the stage: a new face slides in, one who stays only changes from lit to dimmed. */
  function takeStage(beat: StoryBeat): void {
    const cast = beat.cast ?? { left: beat.speaker }
    for (const side of ['left', 'right'] as const) {
      const slot = slots[side]
      const wizard = cast[side]
      if (wizard === undefined) {
        slot.figure.classList.remove('is-in', 'is-quiet')
        slot.wizard = null
        continue
      }
      if (slot.wizard !== wizard) {
        slot.figure.classList.remove('is-in')
        slot.painting.src = portraitUrl(wizard)
        slot.painting.style.objectPosition = CROPS[wizard]
        slot.wizard = wizard
      }
      requestAnimationFrame(() => slot.figure.classList.add('is-in'))
      slot.figure.classList.toggle('is-quiet', wizard !== beat.speaker)
    }
    box.classList.toggle('is-right', beat.cast?.right === beat.speaker && beat.cast.left === undefined)
  }

  /** Opens the scrim round `spot`. */
  function light(spot: HTMLElement): void {
    const stage = element.getBoundingClientRect()
    const lit = spot.getBoundingClientRect()
    element.style.setProperty('--spot-x', `${lit.left + lit.width / 2 - stage.left}px`)
    element.style.setProperty('--spot-y', `${lit.top + lit.height / 2 - stage.top}px`)
  }

  /**
   * Keeps the speech box clear of `clear`: where the box would cover it, the box keeps its left edge and ends 12 px
   * short of it (the chest stands right of the photo's middle, so the box keeps at least half its width). Measured at
   * the first beat that carries it and held from beat to beat, so the box and its button keep one place through the
   * intro; measured again only when `clear` itself moves (a resize of the Scene).
   */
  function fit(clear: HTMLElement | undefined): void {
    if (clear !== clearing) {
      refit.disconnect()
      clearing = clear
      fitted = null
      if (clear !== undefined) refit.observe(clear)
    }
    if (clear !== undefined && fitted === null) {
      box.style.marginLeft = ''
      box.style.width = ''
      const stage = element.getBoundingClientRect()
      const lit = clear.getBoundingClientRect()
      const said = box.getBoundingClientRect()
      const covers = said.right > lit.left && said.left < lit.right
      fitted = covers
        ? { marginLeft: `${said.left - stage.left}px`, width: `${lit.left - 12 - said.left}px` }
        : { marginLeft: '', width: '' }
      reserved = false
    }
    box.style.marginLeft = fitted?.marginLeft ?? ''
    box.style.width = fitted?.width ?? ''
  }

  /**
   * Sizes the box and its button for the held beats: each is laid out once, at the box's width as it stands, and the box
   * keeps the tallest one's height and the button the widest one's width (the footer sits on the box's bottom edge, so
   * Next keeps its place too). Done at the first beat and again when the box refits; the beat on the stage goes back.
   */
  function reserve(): void {
    if (reserved || held.length === 0) return
    reserved = true
    box.style.minHeight = ''
    next.style.minWidth = ''
    let tall = 0
    let wide = 0
    for (const beat of held) {
      show(beat)
      tall = Math.max(tall, box.getBoundingClientRect().height)
      wide = Math.max(wide, next.getBoundingClientRect().width)
    }
    box.style.minHeight = `${tall}px`
    next.style.minWidth = `${wide}px`
    if (shown !== undefined) show(shown)
  }

  /** Fills the speech box with `beat`: the name plate, the rows, the line, the riddle inset, the dots and the button. */
  function show(beat: StoryBeat): void {
    name.textContent = NAMES[beat.speaker]
    role.textContent = beat.role
    solved.hidden = beat.solved === undefined
    if (beat.solved !== undefined) solved.replaceChildren(waxSeal(beat.solved), fill(strings.riddleSolved, { n: beat.solved }))
    line.textContent = beat.line
    riddle.hidden = beat.riddle === undefined
    if (beat.riddle !== undefined) {
      const place = document.createElement('span')
      place.className = 'story-riddle-place'
      place.innerHTML = PIN
      place.append(beat.riddle.place)
      riddleHead.replaceChildren(beat.riddle.heading, place)
      clue.textContent = beat.riddle.clue
    }
    item.hidden = beat.item === undefined
    if (beat.item !== undefined) {
      const words = document.createElement('span')
      words.textContent = fill(strings.inYourPack, { label: beat.item.interactable.label })
      item.replaceChildren(crop(beat.item.roomId, beat.item.interactable, 44, 34), words)
    }
    pips.hidden = beat.page === undefined
    const page = beat.page
    if (page !== undefined) {
      pips.replaceChildren(...Array.from({ length: page.of }, (_, k) => {
        const pip = document.createElement('i')
        pip.className = k < page.at ? 'is-done' : k === page.at ? 'is-now' : ''
        return pip
      }))
    }
    const key = document.createElement('kbd')
    key.setAttribute('aria-hidden', 'true')
    key.textContent = strings.keyEnter
    next.replaceChildren(beat.button, key)
    next.classList.toggle('is-go', beat.button !== strings.next)
  }

  function hold(beats: StoryBeat[]): void {
    held = beats
    reserved = false
  }

  function play(beat: StoryBeat): Promise<BeatEnd> {
    element.classList.toggle('is-light', beat.solved !== undefined)
    element.classList.toggle('is-spotlit', beat.spot !== undefined)
    element.setAttribute('aria-label', NAMES[beat.speaker])
    takeStage(beat)
    shown = beat
    show(beat)
    skip.hidden = beat.page === undefined
    box.classList.remove('is-swapping')
    void box.offsetWidth
    box.classList.add('is-swapping')
    element.hidden = false
    fit(beat.clear)
    reserve()
    if (beat.spot !== undefined) light(beat.spot)
    window.addEventListener('keydown', onKey)
    announce(`${NAMES[beat.speaker]}: ${beat.line}${beat.riddle === undefined ? '' : ` ${beat.riddle.heading}: ${beat.riddle.clue}`}`)
    next.focus({ preventScroll: true })
    waiting = true
    return new Promise((resolve) => {
      settle = (end) => {
        if (!waiting) return
        waiting = false
        resolve(end)
      }
    })
  }

  function close(): void {
    waiting = false
    refit.disconnect()
    clearing = undefined
    fitted = null
    held = []
    shown = undefined
    box.style.minHeight = next.style.minWidth = ''
    element.hidden = true
    for (const slot of Object.values(slots)) {
      slot.figure.classList.remove('is-in', 'is-quiet')
      slot.wizard = null
    }
    window.removeEventListener('keydown', onKey)
  }

  return { element, play, hold, top: () => plate.getBoundingClientRect().top, close }
}
