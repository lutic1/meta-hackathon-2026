import './wizard-notes.css'
import type { PlayPuzzle, PlayView, SessionState } from '../../types'
import { fill, strings } from '../strings.ts'
import { speakerPrefix, wizardPortrait } from '../wizards/portrait.ts'
import { evidenceCard } from './evidence-card.ts'

export interface WizardNotes {
  element: HTMLElement
  /** Draws the notes for `state`: which entries show, their order, the Current marker, open locks, Wrong attempts. */
  render: (state: SessionState) => void
}

interface Entry {
  element: HTMLElement
  update: (state: SessionState) => void
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
function entry(room: PlayView, puzzle: PlayPuzzle, n: number): Entry {
  const element = document.createElement('article')
  element.className = 'notes-entry'

  const head = document.createElement('div')
  head.className = 'notes-entry-head'
  const title = document.createElement('div')
  title.className = 'notes-entry-title'
  const heading = document.createElement('h3')
  heading.className = 'notes-entry-heading display-sm'
  heading.textContent = fill(strings.puzzleHeading, { n })
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
  rungs.className = 'notes-rungs' // the opened Rungs (3.4)
  const lock = document.createElement('div')
  lock.className = 'notes-lock' // the lock input (1.21, 1.26) and its feedback
  const wrong = document.createElement('span')
  wrong.className = 'chip chip-not-this label'
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
    const attempts = state.wrong_attempts[puzzle.id] ?? 0
    wrong.textContent = fill(strings.notThis, { n: attempts })
    if (attempts === 0) wrong.remove()
    else if (wrong.parentNode !== lock) lock.append(wrong)
  }

  return { element, update }
}

/**
 * The Wizard notes (`{components.wizard-notes}`, FR-11, UX-DR27): a parchment sheet scrolling inside the side
 * column with one entry per Puzzle whose prerequisites are open, in availability order, each headed "Puzzle {n}"
 * (n = its fixed place in the Room) with its evidence count at the right end, then the Riddler's portrait beside the
 * Clue, the Evidence cards in `PlayView` order, the Lore, the opened-Rungs slot and the lock-input slot. The Active
 * puzzle's entry carries the `{components.active-puzzle-marker}`, read from `active_puzzle_id` and never guessed; an
 * open entry collapses to its heading with the Open chip. Everything follows session state; nothing follows a click.
 */
export function wizardNotes(room: PlayView): WizardNotes {
  const element = document.createElement('section')
  element.className = 'wizard-notes'
  element.setAttribute('aria-label', strings.wizardNotes)
  const entries = new Map<string, Entry>()
  let drawn: string | undefined

  function render(state: SessionState): void {
    const key = JSON.stringify([state.locks_open, state.active_puzzle_id, state.wrong_attempts])
    if (key === drawn) return
    drawn = key
    const shown = availableInOrder(room.puzzles, state.locks_open).map((puzzle) => {
      let built = entries.get(puzzle.id)
      if (built === undefined) {
        built = entry(room, puzzle, room.puzzles.indexOf(puzzle) + 1)
        entries.set(puzzle.id, built)
      }
      built.update(state)
      return built.element
    })
    const children = [...element.children]
    if (shown.length !== children.length || shown.some((child, index) => child !== children[index])) {
      element.replaceChildren(...shown)
    }
  }

  return { element, render }
}
