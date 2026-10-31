import './riddle-note.css'
import type { PlayPuzzle, PlayView, RungChangeEvent, SessionState } from '../../types'
import { cue } from '../audio.ts'
import { glowOnce } from '../fade.ts'
import type { PlaySession } from '../play.ts'
import { hintLabel, placeTag, riddleHeading, riddleNumber, seals } from '../riddles.ts'
import { strings } from '../strings.ts'
import { speakerPrefix, wizardPortrait } from '../wizards/portrait.ts'
import { type CodeField, codeField } from './code-field.ts'
import { type OrderProgress, orderProgress } from './order-progress.ts'
import { waxSeal } from './wax-seal.ts'

const CHEVRON =
  '<svg width="11" height="11" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M2 4l4 4 4-4"/></svg>'
const PIN =
  '<svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 2a7 7 0 0 0-7 7c0 5 7 13 7 13s7-8 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>'

/** A bought hint's arrival ring (spec 5.4): 900 ms, held 2 s with no animation under reduced motion. */
export const HINT_ARRIVAL_MS = 900
export const HINT_ARRIVAL_REDUCED_MS = 2000

export interface RiddleNote {
  element: HTMLElement
  /** Draws `state`: the riddle shown (the active one, unless held), its seals, its bought hints and its lock input. */
  render: (state: SessionState) => void
  /** Shows the active riddle again: the moment the player sets off for it. */
  release: () => void
  /** Moves focus to the heading, "Riddle n of N", at every riddle start (spec 6.2). */
  focus: () => void
  /** Where a bought hint lands: the gem from the chest flies here (spec 5.4). */
  hintSlot: () => HTMLElement
  /** The newest bought hint glows once as it lands. */
  hintArrived: () => void
  /** Redraws over the refetched Effective room (AD-12): its numbering, clue, lore and lock inputs. */
  reshape: (view: PlayView) => void
}

function paragraph(className: string, ...children: (Node | string)[]): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = className
  element.append(...children)
  return element
}

/** The lore disclosure, "The Riddler's aside": a button with an expanded state over the lore, closed by default. */
function loreDisclosure(): { element: HTMLElement; show: (lore: string) => void } {
  const element = document.createElement('div')
  element.className = 'riddle-lore'
  const toggle = document.createElement('button')
  toggle.type = 'button'
  toggle.className = 'riddle-lore-toggle'
  toggle.textContent = strings.riddlersAside
  toggle.insertAdjacentHTML('beforeend', CHEVRON)
  toggle.setAttribute('aria-expanded', 'false')
  toggle.setAttribute('aria-controls', 'riddle-lore-text')
  const lore = paragraph('riddle-lore-text lore')
  lore.id = 'riddle-lore-text'
  lore.hidden = true
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true'
    toggle.setAttribute('aria-expanded', String(open))
    lore.hidden = !open
  })
  element.append(toggle, lore)
  return {
    element,
    show: (text) => {
      lore.replaceChildren(speakerPrefix('riddler'), text)
      toggle.setAttribute('aria-expanded', 'false')
      lore.hidden = true
    },
  }
}

/**
 * The Riddle note (story mode, owner decision Oct 29; build spec 1.3): ONE riddle, the active one, pinned to the wall
 * at the top left of the Scene. A `section` labelled by its heading, "Riddle {n} of {N}" (n its place among the
 * available Puzzles, N every Puzzle; "The way out · riddle {n} of {N}" on the Exit), which takes focus at each riddle
 * start and is no control; a row of N wax seals (a dashed slot, the current one ringed, a solved one red wax with its
 * number); the place tag "Waits in the {area}" (its start photo's area); the Riddler's 40 px portrait beside the clue;
 * "The Riddler's aside", a disclosure closed by default over the lore; the hints bought from the chest, each "The
 * Guide's hint · Nudge|Direction" and its line beside the Guide's 26 px portrait; the lock input of a `code` or
 * `order` riddle; and, once its lock is open, the "Solved" stamp. No later riddle is drawn and no evidence either:
 * the session's room serves none before a lock opens. Which riddle is current comes only from `active_puzzle_id` (AD-4).
 * When the riddle shown opens, the note holds it (the solve beat): its stamp shows and its seal is stamped in, once,
 * until `release` shows the active riddle, the moment the player sets off for it (spec 3.3); a reload holds nothing.
 */
export function riddleNote(room: PlayView, play: PlaySession): RiddleNote {
  const element = document.createElement('section')
  element.className = 'riddle-note'
  element.setAttribute('aria-labelledby', 'riddle-note-heading')
  const pin = document.createElement('span')
  pin.className = 'riddle-note-pin'
  pin.setAttribute('aria-hidden', 'true')
  const head = document.createElement('div')
  head.className = 'riddle-note-head'
  const heading = document.createElement('h2')
  heading.id = 'riddle-note-heading'
  heading.className = 'riddle-note-heading'
  heading.tabIndex = -1 // focus lands here at each riddle start
  const sealRow = document.createElement('span')
  sealRow.className = 'riddle-seals'
  sealRow.setAttribute('aria-hidden', 'true')
  head.append(heading, sealRow)
  const place = paragraph('riddle-place label')
  const body = document.createElement('div')
  body.className = 'riddle-body'
  const clue = paragraph('riddle-clue wizard-line')
  const words = document.createElement('div')
  words.className = 'riddle-words'
  const lore = loreDisclosure()
  const hints = document.createElement('div')
  hints.className = 'riddle-hints'
  const lock = document.createElement('div')
  lock.className = 'riddle-lock'
  const stamp = paragraph('riddle-stamp label')
  stamp.hidden = true
  words.append(clue, lore.element, hints, lock, stamp)
  body.append(wizardPortrait('riddler', 40), words)
  element.append(pin, head, place, body)

  let latest = play.state()
  let held = false
  /** The Puzzle the note shows, and what it was last drawn from. */
  let shown: string | null = null
  let drawn = ''
  const inputs = new Map<string, { element: HTMLElement; update: (state: SessionState) => void }>()

  /** The lock input of `puzzle`, built once and kept so a typed code survives a redraw. */
  function input(puzzle: PlayPuzzle): { element: HTMLElement; update: (state: SessionState) => void } | null {
    if (puzzle.lock_type !== 'code' && puzzle.lock_type !== 'order') return null
    let made = inputs.get(puzzle.id)
    if (made === undefined) {
      const place = room.puzzles.indexOf(puzzle) + 1
      const built: CodeField | OrderProgress = puzzle.lock_type === 'code' ? codeField(puzzle, place, play) : orderProgress(puzzle, play)
      made = { element: built.element, update: built.update }
      inputs.set(puzzle.id, made)
    }
    return made
  }

  function hint(line: RungChangeEvent): HTMLElement {
    const made = document.createElement('div')
    made.className = 'riddle-hint'
    const said = document.createElement('div')
    said.append(paragraph('riddle-hint-label label', hintLabel(line.rung)), paragraph('riddle-hint-text wizard-line', speakerPrefix('guide'), line.text))
    made.append(wizardPortrait('guide', 26), said)
    return made
  }

  function draw(state: SessionState): void {
    const id = held ? shown : (state.active_puzzle_id ?? shown)
    const puzzle = room.puzzles.find((candidate) => candidate.id === id)
    if (puzzle === undefined) return
    const open = state.locks_open.includes(puzzle.id)
    const mine = state.rung_changes.filter((change) => change.puzzle_id === puzzle.id)
    const states = seals(room.puzzles, state.locks_open, held ? puzzle.id : state.active_puzzle_id)
    const key = JSON.stringify([puzzle, open, mine.map((change) => [change.rung, change.text]), states])
    const fresh = puzzle.id !== shown
    shown = puzzle.id
    inputs.get(puzzle.id)?.update(state)
    if (key === drawn) return
    drawn = key
    const n = riddleNumber(room.puzzles, state.locks_open, puzzle.id)
    heading.textContent = riddleHeading(room.puzzles, state.locks_open, puzzle.id)
    sealRow.replaceChildren(
      ...states.map((seal, k) => {
        const slot = document.createElement('span')
        slot.className = `riddle-seal is-${seal}`
        slot.append(waxSeal(k + 1))
        return slot
      }),
    )
    place.innerHTML = PIN
    place.append(placeTag(room, puzzle.id))
    if (fresh) {
      clue.replaceChildren(speakerPrefix('riddler'), puzzle.clue)
      lore.show(puzzle.lore)
    }
    hints.replaceChildren(...mine.map(hint))
    const lockInput = open ? null : input(puzzle)
    lock.replaceChildren(...(lockInput === null ? [] : [lockInput.element]))
    stamp.hidden = !open
    element.classList.toggle('is-solved', open)
    if (open) {
      const seal = document.createElement('span')
      seal.className = 'riddle-seal is-solved'
      seal.append(waxSeal(n))
      stamp.replaceChildren(seal, strings.solved)
    }
  }

  /** Draws `state`; the riddle shown opening in it is held with its stamp, its seal stamped in once (never on reload). */
  function render(state: SessionState): void {
    const opened = shown !== null && state.locks_open.includes(shown) && !latest.locks_open.includes(shown)
    latest = state
    if (opened) held = true
    draw(state)
    if (!opened || shown === null) return
    const n = riddleNumber(room.puzzles, state.locks_open, shown)
    for (const seal of [sealRow.children[n - 1], stamp.firstElementChild]) seal?.classList.add('is-stamping')
  }

  render(latest)

  return {
    element,
    render,
    release: () => {
      held = false
      drawn = ''
      draw(latest)
    },
    focus: () => heading.focus({ preventScroll: true }),
    hintSlot: () => hints,
    hintArrived: () => {
      cue('hintPinned')
      const newest = hints.lastElementChild
      const hold = matchMedia('(prefers-reduced-motion: reduce)').matches ? HINT_ARRIVAL_REDUCED_MS : HINT_ARRIVAL_MS
      if (newest !== null) glowOnce(newest, 'is-arriving-hint', hold)
    },
    reshape: (view) => {
      room = view
      inputs.clear()
      drawn = ''
      shown = null
      draw(latest)
    },
  }
}
