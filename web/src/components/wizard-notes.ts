import './wizard-notes.css'
import type { PlayPuzzle, PlayView, RungChangeEvent, SessionState } from '../../types'
import { fadeIn, stateFadeMs } from '../fade.ts'
import type { PlaySession } from '../play.ts'
import { fill, strings } from '../strings.ts'
import { speakerPrefix, wizardPortrait } from '../wizards/portrait.ts'
import { type CodeField, codeField } from './code-field.ts'
import { evidenceCard } from './evidence-card.ts'
import { rungLabel } from './hint-area.ts'
import { type OrderProgress, orderProgress } from './order-progress.ts'

/** UX-DR38: a lock the server opened shows "Open" this long before its entry collapses and the next one appears. */
export const OPEN_HOLD_MS = 1200

export interface WizardNotes {
  element: HTMLElement
  /** Draws the notes for `state`: which entries show, their order, the Current marker, open locks, Wrong attempts. */
  render: (state: SessionState) => void
  /** Draws each Puzzle's opened Rungs: the `rung_changes` the Hint area's Rung line no longer shows (3.4). */
  openedRungs: (lines: readonly RungChangeEvent[]) => void
  /** Redraws the notes over the refetched Effective room: its Evidence cards and which Puzzles wait (AD-12). */
  reshape: (view: PlayView) => void
}

interface Entry {
  element: HTMLElement
  heading: HTMLHeadingElement
  update: (state: SessionState) => void
  /** The lock just opened: the lock input gives way to the Open chip while the entry stays expanded. */
  opening: () => void
  /** Draws the entry's opened Rungs from all the opened Rungs of the Room. */
  rungs: (lines: readonly RungChangeEvent[]) => void
  /** Draws the Puzzle's Evidence cards and their count as `view` gives them; the same cards redraw nothing. */
  evidence: (view: PlayView, shown: PlayPuzzle) => void
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

/** What the notes draw from a state: a state with the same key redraws nothing. */
function drawKey(state: SessionState): string {
  return JSON.stringify([state.locks_open, state.active_puzzle_id, state.wrong_attempts, state.order_buffer])
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

  const count = document.createElement('span')
  count.className = 'notes-count label'
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
  const lore = paragraph('notes-lore lore', speakerPrefix('riddler'), puzzle.lore)
  const rungs = document.createElement('div')
  rungs.className = 'notes-rungs' // the opened Rungs
  const lock = document.createElement('div')
  lock.className = 'notes-lock' // the lock input (the Code field or Order click progress) and its feedback
  const wrong = document.createElement('span')
  wrong.className = 'chip chip-not-this label'
  const code: CodeField | undefined = puzzle.lock_type === 'code' ? codeField(puzzle, n, play) : undefined
  if (code !== undefined) lock.append(code.element)
  const order: OrderProgress | undefined = puzzle.lock_type === 'order' ? orderProgress(puzzle, play) : undefined
  if (order !== undefined) lock.append(order.element)
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
    if (order !== undefined) {
      order.update(state)
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

  let drawnEvidence = ''
  function drawEvidence(view: PlayView, shown: PlayPuzzle): void {
    const key = JSON.stringify(shown.evidence_cards)
    if (key === drawnEvidence) return
    drawnEvidence = key
    const interactables = new Map(view.interactables.map((interactable) => [interactable.id, interactable]))
    const cards = shown.evidence_cards.flatMap((card) => {
      const interactable = interactables.get(card.interactable)
      return interactable === undefined ? [] : [evidenceCard(view.id, interactable, card)]
    })
    count.textContent = cards.length === 1 ? strings.evidenceCard : fill(strings.evidenceCards, { k: cards.length })
    evidence.replaceChildren(...cards)
  }
  drawEvidence(room, puzzle)

  return { element, heading, update, opening, rungs: drawRungs, evidence: drawEvidence }
}

/** The plain line an accepted Merge leaves where the entry it gated stood; focus can land on it (UX-DR27). */
function waitingLine(n: number): HTMLParagraphElement {
  const element = paragraph('notes-entry notes-waiting label', fill(strings.puzzleWaits, { n }))
  element.tabIndex = -1
  return element
}

/**
 * The Wizard notes (`{components.wizard-notes}`, FR-11, UX-DR27): a parchment sheet scrolling inside the side
 * column with one entry per Puzzle whose prerequisites are open, in availability order, each headed "Puzzle {n}"
 * (n = its fixed place in the Room) with its evidence count at the right end, then the Riddler's portrait beside the
 * Clue, the Evidence cards in `PlayView` order, the Lore, the opened Rungs (each a Rung the Hint area's Rung line
 * showed and gave up, with the Guide's 32 px portrait, its "Puzzle {n} · {Rung name}" label and its line, as
 * `rung_changes[]` carries it) and the lock-input slot (the Code field of a `code` Puzzle, the Order click progress
 * of an `order` one, else the Not this chip a `use_on` verdict shows). The Active puzzle's entry carries the
 * `{components.active-puzzle-marker}`, read from `active_puzzle_id` and never guessed; an open entry collapses to its
 * heading with the Open chip. When a state shows a lock newly open, "Open" takes the lock input's place for 1200 ms
 * (UX-DR38), then the notes draw the latest state: the entry collapses, newly available entries fade in, and focus
 * moves to the heading of the first of them, else of the Active puzzle. Everything follows session state; nothing
 * follows a click.
 *
 * `reshape` takes the Effective room refetched after an accepted edit (FR-19, AD-12) and keeps every entry, so the
 * Code field's value and keyboard focus stay: an entry's Evidence cards and count change in place, a card the Room
 * gained drawn like the others, with no highlight or announcement. An entry whose Puzzle now waits on an unopened one
 * (a Merge) fades out and leaves "Puzzle {n} now waits on another puzzle." in its place, taking focus if it held it,
 * until the Puzzle is available again; a Puzzle whose last unmet prerequisite went (a Shortcut) fades in as any newly
 * available entry does. The placeholder is never written to the live region.
 */
export function wizardNotes(room: PlayView, play: PlaySession): WizardNotes {
  const element = document.createElement('section')
  element.className = 'wizard-notes'
  element.setAttribute('aria-label', strings.wizardNotes)
  element.tabIndex = 0 // its place in the Tab order, after the Inventory, and scrolled by the keyboard (UX-DR71)
  const entries = new Map<string, Entry>()
  /** The Puzzles a Merge hid from view, each as it was drawn (its prerequisites open) and the line in its place. */
  const waiting = new Map<string, { puzzle: PlayPuzzle; line: HTMLElement }>()
  let drawn: string | undefined
  /** `locks_open` as last drawn; undefined before the first draw, which shows open locks collapsed at once. */
  let drawnOpen: readonly string[] | undefined
  let latest: SessionState | undefined
  let holding = false
  let opened: readonly RungChangeEvent[] = []

  const place = (id: string): number => room.puzzles.findIndex((puzzle) => puzzle.id === id) + 1

  function built(puzzle: PlayPuzzle): Entry {
    let made = entries.get(puzzle.id)
    if (made === undefined) {
      made = entry(room, puzzle, place(puzzle.id), play)
      made.rungs(opened)
      entries.set(puzzle.id, made)
    }
    return made
  }

  /**
   * Puts focus back after the rows were swapped, which detaches every kept entry for a moment: on the element that
   * held it when that is still drawn, else on the line that took the place of the gated entry that held it. Returns
   * that line, if any.
   */
  function keepFocus(focused: Element | null): HTMLElement | undefined {
    if (!(focused instanceof HTMLElement) || document.activeElement === focused) return undefined
    if (focused.isConnected) {
      focused.focus({ preventScroll: true })
      return undefined
    }
    const line = [...waiting].find(([id]) => entries.get(id)?.element.contains(focused))?.[1].line
    if (!line?.isConnected) return undefined
    line.focus()
    return line
  }

  function draw(state: SessionState, afterOpening: boolean): void {
    drawn = drawKey(state)
    drawnOpen = state.locks_open
    for (const puzzle of room.puzzles) {
      if (waiting.has(puzzle.id) && puzzle.requires.every((id) => state.locks_open.includes(id))) waiting.delete(puzzle.id)
    }
    const before = new Set(element.children)
    // A waiting Puzzle keeps the place it was drawn in, as its line.
    const listed = availableInOrder(room.puzzles.map((puzzle) => waiting.get(puzzle.id)?.puzzle ?? puzzle), state.locks_open)
    const shown = listed.flatMap((puzzle) => {
      if (waiting.has(puzzle.id)) return []
      const made = built(puzzle)
      made.update(state)
      made.element.classList.remove('is-leaving') // an entry a Merge gated is drawn again once its Puzzle is available
      return [made]
    })
    const rows = listed.map((puzzle) => waiting.get(puzzle.id)?.line ?? built(puzzle).element)
    const children = [...element.children]
    const arrived = shown.filter((made) => !before.has(made.element))
    let line: HTMLElement | undefined
    if (rows.length !== children.length || rows.some((child, index) => child !== children[index])) {
      const focused = document.activeElement
      element.replaceChildren(...rows)
      // The arriving entries start transparent before focus moves: its style pass would otherwise skip their fade.
      if (before.size > 0) for (const made of arrived) fadeIn(made.element)
      line = keepFocus(focused)
    }
    if (!afterOpening || line !== undefined) return
    const active = state.active_puzzle_id === null ? undefined : entries.get(state.active_puzzle_id)
    const next = arrived[0] ?? (active !== undefined && active.element.isConnected ? active : undefined)
    next?.heading.focus()
  }

  function render(state: SessionState): void {
    latest = state
    if (holding) return
    if (drawKey(state) === drawn) return
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

  function reshape(view: PlayView): void {
    // The latest state, not the drawn one: during the Open hold a lock it shows open gates nothing.
    const open = latest?.locks_open ?? []
    // The drawn entries of unopened Puzzles that the new Room makes wait on an unopened one.
    const gated = room.puzzles.filter((puzzle) => {
      const now = view.puzzles.find(({ id }) => id === puzzle.id)
      const shown = entries.get(puzzle.id)?.element.isConnected === true && !open.includes(puzzle.id)
      return shown && now !== undefined && !now.requires.every((id) => open.includes(id))
    })
    room = view
    for (const puzzle of view.puzzles) entries.get(puzzle.id)?.evidence(view, puzzle)
    for (const puzzle of gated) waiting.set(puzzle.id, { puzzle, line: waitingLine(place(puzzle.id)) })
    const leaving = gated.flatMap((puzzle) => entries.get(puzzle.id) ?? [])
    for (const made of leaving) made.element.classList.add('is-leaving')
    const redraw = (): void => {
      drawn = undefined
      // During the Open hold the entries stay faded out, and the hold's own draw puts their lines in.
      if (!holding && latest !== undefined && element.isConnected) draw(latest, false)
    }
    // The gated entries fade out (instant under reduced motion) before their lines take their places, and focus
    // inside one moves to its line.
    if (leaving.length === 0) redraw()
    else setTimeout(redraw, stateFadeMs())
  }

  return { element, render, openedRungs, reshape }
}
