import './wizard-notes.css'
import type { PlayPuzzle, PlayView, RungChangeEvent, SessionState } from '../../types'
import { fadeIn } from '../fade.ts'
import type { PlaySession } from '../play.ts'
import { fill, strings } from '../strings.ts'
import { speakerPrefix, wizardPortrait } from '../wizards/portrait.ts'
import { type CodeField, codeField } from './code-field.ts'
import { evidenceCard } from './evidence-card.ts'
import { rungLabel } from './hint-area.ts'

/** UX-DR38: a lock the server opened shows "Open" this long before its entry collapses and the next one appears. */
export const OPEN_HOLD_MS = 1200

export interface WizardNotes {
  element: HTMLElement
  /** Draws the notes for `state`: which entries show, their order, the Current marker, open locks, Wrong attempts. */
  render: (state: SessionState) => void
  /** Draws each Puzzle's opened Rungs: the `rung_changes` the Hint area's Rung line no longer shows (3.4). */
  openedRungs: (lines: readonly RungChangeEvent[]) => void
}

interface Entry {
  element: HTMLElement
  heading: HTMLHeadingElement
  update: (state: SessionState) => void
  /** The lock just opened: the lock input gives way to the Open chip while the entry stays expanded. */
  opening: () => void
  /** Draws the entry's opened Rungs from all the opened Rungs of the Room. */
  rungs: (lines: readonly RungChangeEvent[]) => void
}

/**
 * The Puzzles whose prerequisites are all open, in the order they became available: each when the last Puzzle it
 * `requires` opened (`locks_open` keeps the order locks opened in), those with none from the start, ties in Room order.
 * Open Puzzles stay in it; Puzzles with an unmet prerequisite are left out.
 */
export function availableInOrder(puzzles: readonly PlayPuzzle[], locksOpen: readonly string[]): PlayPuzzle[] {
  return puzzles
    .map((puzzle, place) => ({ puzzle, place, since: Math.max(-1, ...puzzle.requires.map((id) => locksOpen.indexOf(id))) }))
    .filter(({ puzzle }) => puzzle.requires.every((id) => locksOpen.includes(id)))
    .sort((a, b) => a.since - b.since || a.place - b.place)
    .map(({ puzzle }) => puzzle)
}

function paragraph(className: string, ...children: (Node | string)[]): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = className
  element.append(...children)
  return element
}

/** One Puzzle's entry, built once; `update` changes only what session state moves. */
function entry(room: PlayView, puzzle: PlayPuzzle, n: number, play: PlaySession): Entry {
  const element = document.createElement('article')
  element.className = 'notes-entry'

  const head = document.createElement('div')
  head.className = 'notes-entry-head'
  const title = document.createElement('div')
  title.className = 'notes-entry-title'
  const heading = document.createElement('h3')
  heading.className = 'notes-entry-heading display-sm'
  heading.textContent = fill(strings.puzzleHeading, { n })
  heading.tabIndex = -1 // focus moves here when the lock before it opens
  const current = document.createElement('span')
  current.className = 'notes-current label'
  current.textContent = strings.current
  title.append(heading, current)

  const interactables = new Map(room.interactables.map((interactable) => [interactable.id, interactable]))
  const cards = puzzle.evidence_cards.flatMap((evidence) => {
    const interactable = interactables.get(evidence.interactable)
    return interactable === undefined ? [] : [evidenceCard(room.id, interactable, evidence)]
  })
  const count = document.createElement('span')
  count.className = 'notes-count label'
  count.textContent = cards.length === 1 ? strings.evidenceCard : fill(strings.evidenceCards, { k: cards.length })
  const opened = document.createElement('span')
  opened.className = 'chip chip-open label'
  opened.textContent = strings.open
  head.append(title, count, opened)

  const body = document.createElement('div')
  body.className = 'notes-entry-body'
  const clue = document.createElement('div')
  clue.className = 'notes-clue'
  clue.append(wizardPortrait('riddler', 32), paragraph('wizard-line', speakerPrefix('riddler'), puzzle.clue))
  const evidence = document.createElement('ul')
  evidence.className = 'notes-evidence'
  evidence.append(...cards)
  const lore = paragraph('notes-lore lore', speakerPrefix('riddler'), puzzle.lore)
  const rungs = document.createElement('div')
  rungs.className = 'notes-rungs' // the opened Rungs
  const lock = document.createElement('div')
  lock.className = 'notes-lock' // the lock input (1.21, 1.26) and its feedback
  const wrong = document.createElement('span')
  wrong.className = 'chip chip-not-this label'
  const code: CodeField | undefined = puzzle.lock_type === 'code' ? codeField(puzzle, n, play) : undefined
  if (code !== undefined) lock.append(code.element)
  body.append(clue, evidence, lore, rungs, lock)
  element.append(head, body)

  function update(state: SessionState): void {
    const open = state.locks_open.includes(puzzle.id)
    const isCurrent = state.active_puzzle_id === puzzle.id
    element.classList.toggle('is-open', open)
    element.classList.toggle('is-current', isCurrent)
    current.hidden = !isCurrent
    count.hidden = open
    opened.hidden = !open
    body.hidden = open
    if (code !== undefined) {
      code.update(state)
      return
    }
    const attempts = state.wrong_attempts[puzzle.id] ?? 0
    wrong.textContent = fill(strings.notThis, { n: attempts })
    if (attempts === 0) wrong.remove()
    else if (wrong.parentNode !== lock) lock.append(wrong)
  }

  function opening(): void {
    const chip = opened.cloneNode(true) as HTMLElement
    chip.hidden = false
    lock.replaceChildren(chip)
  }

  let drawnRungs = ''
  function drawRungs(lines: readonly RungChangeEvent[]): void {
    const mine = lines.filter((line) => line.puzzle_id === puzzle.id)
    const key = JSON.stringify(mine.map((line) => [line.rung, line.text]))
    if (key === drawnRungs) return
    drawnRungs = key
    rungs.replaceChildren(
      ...mine.map((line) => {
        const opened = document.createElement('div')
        opened.className = 'notes-rung'
        const words = document.createElement('div')
        words.append(
          paragraph('notes-rung-label label', rungLabel(n, line.rung)),
          paragraph('wizard-line', speakerPrefix('guide'), line.text),
        )
        opened.append(wizardPortrait('guide', 32), words)
        return opened
      }),
    )
  }

  return { element, heading, update, opening, rungs: drawRungs }
}

/**
 * The Wizard notes (`{components.wizard-notes}`, FR-11, UX-DR27): a parchment sheet scrolling inside the side
 * column with one entry per Puzzle whose prerequisites are open, in availability order, each headed "Puzzle {n}"
 * (n = its fixed place in the Room) with its evidence count at the right end, then the Riddler's portrait beside the
 * Clue, the Evidence cards in `PlayView` order, the Lore, the opened Rungs (each a Rung the Hint area's Rung line
 * showed and gave up, with the Guide's 32 px portrait, its "Puzzle {n} · {Rung name}" label and its line, as
 * `rung_changes[]` carries it) and the lock-input slot (the Code field of a `code` Puzzle). The Active puzzle's
 * entry carries the `{components.active-puzzle-marker}`, read from `active_puzzle_id` and never guessed; an open entry
 * collapses to its heading with the Open chip. When a state shows a lock newly open, "Open" takes the lock input's
 * place for 1200 ms (UX-DR38), then the notes draw the latest state: the entry collapses, newly available entries
 * fade in, and focus moves to the heading of the first of them, else of the Active puzzle. Everything follows session
 * state; nothing follows a click.
 */
export function wizardNotes(room: PlayView, play: PlaySession): WizardNotes {
  const element = document.createElement('section')
  element.className = 'wizard-notes'
  element.setAttribute('aria-label', strings.wizardNotes)
  element.tabIndex = 0 // its place in the Tab order, after the Inventory, and scrolled by the keyboard (UX-DR71)
  const entries = new Map<string, Entry>()
  let drawn: string | undefined
  /** `locks_open` as last drawn; undefined before the first draw, which shows open locks collapsed at once. */
  let drawnOpen: readonly string[] | undefined
  let latest: SessionState | undefined
  let holding = false
  let opened: readonly RungChangeEvent[] = []

  function built(puzzle: PlayPuzzle): Entry {
    let made = entries.get(puzzle.id)
    if (made === undefined) {
      made = entry(room, puzzle, room.puzzles.indexOf(puzzle) + 1, play)
      made.rungs(opened)
      entries.set(puzzle.id, made)
    }
    return made
  }

  function draw(state: SessionState, afterOpening: boolean): void {
    drawn = JSON.stringify([state.locks_open, state.active_puzzle_id, state.wrong_attempts])
    drawnOpen = state.locks_open
    const before = new Set(element.children)
    const shown = availableInOrder(room.puzzles, state.locks_open).map((puzzle) => {
      const made = built(puzzle)
      made.update(state)
      return made
    })
    const children = [...element.children]
    if (shown.length !== children.length || shown.some(({ element: child }, index) => child !== children[index])) {
      element.replaceChildren(...shown.map((made) => made.element))
    }
    const arrived = shown.filter((made) => !before.has(made.element))
    if (before.size > 0) for (const made of arrived) fadeIn(made.element)
    if (!afterOpening) return
    const active = state.active_puzzle_id === null ? undefined : entries.get(state.active_puzzle_id)
    const next = arrived[0] ?? (active !== undefined && active.element.isConnected ? active : undefined)
    next?.heading.focus()
  }

  function render(state: SessionState): void {
    latest = state
    if (holding) return
    const key = JSON.stringify([state.locks_open, state.active_puzzle_id, state.wrong_attempts])
    if (key === drawn) return
    const previous = drawnOpen
    const opened =
      previous === undefined
        ? []
        : state.locks_open.flatMap((id) => {
            const made = entries.get(id)
            return !previous.includes(id) && made?.element.isConnected ? [made] : []
          })
    if (opened.length === 0) {
      draw(state, false)
      return
    }
    holding = true
    for (const made of opened) made.opening()
    setTimeout(() => {
      holding = false
      if (latest !== undefined && element.isConnected) draw(latest, true)
    }, OPEN_HOLD_MS)
  }

  function openedRungs(lines: readonly RungChangeEvent[]): void {
    opened = lines
    for (const made of entries.values()) made.rungs(lines)
  }

  return { element, render, openedRungs }
}
