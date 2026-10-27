import './hint-area.css'
import type { HintReply, Meta, PlayView, RungChangeEvent, SessionState, TricksterCard } from '../../types'
import { fadeIn, stateFadeMs } from '../fade.ts'
import { announce } from '../live-region.ts'
import type { PlaySession } from '../play.ts'
import { fill, strings } from '../strings.ts'
import { speakerPrefix, wizardPortrait } from '../wizards/portrait.ts'
import { primaryButton } from './button.ts'
import { cardAnnouncement, cardText, tricksterCard } from './trickster-card.ts'
import { OPEN_HOLD_MS } from './wizard-notes.ts'

/** The arrival glow lights for this long and fades by `--motion-hover` each way: 300 ms in all (DESIGN.md Motion). */
export const GLOW_MS = 150
/** Under reduced motion the lit ring is held this long, with no animation (NFR-14). */
export const GLOW_REDUCED_MS = 2000

/** At most this many Cards stack in the Hint area; only the newest while the Triggers panel is open (UX-DR30). */
export const CARDS_STACKED = 2

/** The label of each Rung, by its number: 0 is the No-hint line, labelled with its Puzzle alone. */
const RUNG_LABELS = [strings.puzzleHeading, strings.rungNudge, strings.rungDirection, strings.rungNearAnswer]

/** The Rung a line shows, by its Puzzle and number. */
interface Shown {
  puzzle_id: string
  rung: number
}

/** One Guide line: its label (none for the opening line), its words and the Rung it shows (none for a non-Rung). */
interface Line {
  label: string | null
  text: string
  shown: Shown | null
}

/** "Puzzle {n} · Nudge", "· Direction" or "· Near-answer", or "Puzzle {n}" alone for the No-hint line (rung 0). */
export function rungLabel(n: number, rung: number): string {
  return fill(RUNG_LABELS[rung] ?? strings.puzzleHeading, { n })
}

/** A Rung a Loosen card opened: its one triggering log event is the `trickster_card`, as the Triggers panel reads it. */
function byLoosen(change: RungChangeEvent, events: SessionState['trigger_events']): boolean {
  const [only, ...rest] = change.triggered_by
  return only !== undefined && rest.length === 0 && events?.[only]?.type === 'trickster_card'
}

/**
 * The opened Rungs the Wizard notes keep: every Rung change but the one on the Rung line, unless a Loosen card opened
 * that one, which shows in its Puzzle's entry as well (FR-19).
 */
export function openedRungs(
  changes: readonly RungChangeEvent[],
  shown: Shown | null,
  events: SessionState['trigger_events'] = {},
): RungChangeEvent[] {
  return changes.filter(
    (change) =>
      shown === null || change.puzzle_id !== shown.puzzle_id || change.rung !== shown.rung || byLoosen(change, events),
  )
}

export interface HintArea {
  element: HTMLElement
  /** Draws `state`: the field's label from the Active puzzle, and each newly arrived `rung_change` as the Rung line. */
  render: (state: SessionState) => void
  /** After "Begin": the opening line as the first Guide line, never announced, unless a Rung line already shows. */
  opening: (line: string) => void
  /** The slot under the helper line that holds the Triggers toggle and its panel. */
  triggers: HTMLElement
  /** The Triggers panel opened or closed: the tray may grow past its cap, and only the newest Card stacks. */
  triggersOpen: (open: boolean) => void
}

function paragraph(className: string): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = className
  return element
}

/**
 * The Hint area (`{components.hint-area}`, FR-14, UX-DR30 to UX-DR32): a `chrome-raised` tray pinned under the Wizard
 * notes, up to `{spacing.hint-area-max}`, its upper part scrolling (the Rung line) over a lower part that never
 * scrolls: the hint field and "Ask the Guide", the permanent helper line, and the slot of the Triggers toggle. While
 * the Triggers panel is open (`is-triggers-open`) the tray may grow past its cap until the Wizard notes reach
 * `{spacing.notes-min}`.
 *
 * Enter or the button posts exactly one `hint_request` with no `puzzle_id`: the server answers for the Active puzzle,
 * the entry marked "Current". The typed text is never read, so it leaves the browser in no body, query or header; it
 * stays visible in the read-only field while the button reads "Asking" and one request is in flight, and clears when
 * the reply lands. With `guide` `ollama` the Guide portrait shows the static `lamp` ring and "thinking on this Mac"
 * until then; with `verbatim` no thinking state ever shows.
 *
 * The Rung line (`{components.rung-line}`) is the Guide portrait, the label "Puzzle {n} · {Rung name}" ("Puzzle {n}"
 * alone on the No-hint line) and the line. Every new line fades the shown one out and itself in (200 ms each way,
 * instant under reduced motion), so a reply that repeats the shown line still visibly arrives, and is announced in
 * the one live region as "The Guide: …". A `rung_change` in a state the server sent (never computed here, and its
 * words taken from `rung_changes[]`) shows the same way with one arrival glow on the portrait ring and the tray edge;
 * a reply the player asked for never glows. The line the Rung line no longer shows moves into its Puzzle's opened
 * Rungs, through `onOpened`; a Rung a Loosen card opened shows there at once as well. The first state is only read:
 * the latest `rung_change`, else the opening line, is drawn without a fade, a glow or an announcement, so a reload
 * rebuilds the Rungs and re-announces nothing.
 *
 * Trickster cards (FR-19, UX-DR40 to UX-DR42) stack above the Rung line, newest on top: at most `CARDS_STACKED`, only
 * the newest while the Triggers panel is open, the rest behind the link "{n} more in the Card log", which opens the
 * Card log through `openCardLog` (focus returns to it when the log closes). Each new entry of the
 * state's `cards[]` (the `TricksterCard` projection) enters with a 200 ms fade once the lock-open state has played out
 * (the Open chip's `OPEN_HOLD_MS`, then the entry collapse and the next Puzzle's fade-in; a collected item's fade-in
 * starts with the state and ends sooner), and is written once to the live region. A Card stays until dismissed;
 * dismissing it moves focus to the Card now in its place, else the one above, else the hint field. The Session's
 * first Card carries the Trickster's introduction. Cards already in the first state are never stacked, so after a
 * reload none is re-stacked or announced and the introduction never shows again.
 */
export function hintArea(
  room: PlayView,
  play: PlaySession,
  guide: Meta['guide'],
  onOpened: (lines: readonly RungChangeEvent[]) => void,
  openCardLog: (opener: HTMLElement) => void,
): HintArea {
  const element = document.createElement('section')
  element.className = 'hint-area'
  element.setAttribute('aria-label', strings.hintArea)

  const upper = document.createElement('div')
  upper.className = 'hint-upper'
  const rungLine = document.createElement('div')
  rungLine.className = 'rung-line'
  rungLine.hidden = true
  const portrait = wizardPortrait('guide', 48)
  const words = document.createElement('div')
  words.className = 'rung-line-words'
  const label = paragraph('rung-label label')
  const thinking = paragraph('rung-thinking label')
  thinking.textContent = strings.thinkingOnThisMac
  const said = paragraph('rung-text wizard-line')
  words.append(label, thinking, said)
  rungLine.append(portrait, words)
  const stack = document.createElement('div')
  stack.className = 'hint-cards'
  stack.hidden = true
  const more = document.createElement('button')
  more.type = 'button'
  more.className = 'hint-more body-sm'
  more.hidden = true
  more.setAttribute('aria-haspopup', 'dialog')
  more.addEventListener('click', () => openCardLog(more))
  upper.append(stack, more, rungLine)

  const lower = document.createElement('div')
  lower.className = 'hint-lower'
  const ask = document.createElement('div')
  ask.className = 'hint-ask'
  const field = document.createElement('input')
  field.type = 'text'
  field.className = 'hint-field body-sm'
  field.placeholder = strings.hintPlaceholder
  field.autocomplete = 'off'
  const helper = paragraph('hint-helper body-sm')
  helper.id = 'hint-helper'
  helper.textContent = strings.hintHelper
  field.setAttribute('aria-describedby', helper.id)
  const button = primaryButton({ label: strings.askTheGuide, pendingLabel: strings.asking, onActivate: request })
  field.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return
    event.preventDefault()
    button.click() // the button ignores it while a request is in flight
  })
  ask.append(field, button)
  const triggers = document.createElement('div')
  triggers.className = 'hint-triggers' // the Triggers toggle and its panel
  lower.append(ask, helper, triggers)
  element.append(upper, lower)

  const place = (puzzleId: string | null): number | null => {
    const index = room.puzzles.findIndex((puzzle) => puzzle.id === puzzleId)
    return index < 0 ? null : index + 1
  }
  let latest = play.state()
  /** How many `rung_changes` have been drawn; only those after it arrive. */
  let heard = latest.rung_changes.length
  let version = 0
  let glowing: ReturnType<typeof setTimeout> | undefined
  /** How many `cards` have arrived; only those after it are new, so the first state stacks none. */
  let cardsHeard = latest.cards.length
  /** How many locks were open; a newly open lock holds new Cards until its lock-open state has played out. */
  let locksSeen = latest.locks_open.length
  let holding: ReturnType<typeof setTimeout> | undefined
  /** Cards that arrived while a lock-open state plays out, oldest first, each marked when it is the Session's first. */
  const waiting: { card: TricksterCard; first: boolean }[] = []
  /** The Cards in the Hint area, oldest first, each until it is dismissed. */
  const held: HTMLElement[] = []
  let triggersShown = false

  function changeLine(change: RungChangeEvent): Line {
    const n = place(change.puzzle_id)
    return { label: n === null ? null : rungLabel(n, change.rung), text: change.text, shown: change }
  }

  function replyLine(reply: HintReply): Line {
    const { puzzle_id, rung, text } = reply
    const n = place(puzzle_id)
    const shown = puzzle_id !== null && rung > 0 ? { puzzle_id, rung } : null // the No-hint line is no Rung
    return { label: n === null ? null : rungLabel(n, rung), text, shown }
  }

  function think(on: boolean): void {
    rungLine.classList.toggle('is-thinking', on)
    thinking.hidden = !on
    label.hidden = on || label.textContent === ''
    said.hidden = on
    rungLine.hidden = !on && said.textContent === ''
  }

  function draw(line: Line): void {
    label.textContent = line.label ?? ''
    said.replaceChildren(speakerPrefix('guide'), line.text)
    words.classList.remove('is-leaving')
    think(false)
    onOpened(openedRungs(latest.rung_changes, line.shown, latest.trigger_events))
  }

  function glow(): void {
    const hold = matchMedia('(prefers-reduced-motion: reduce)').matches ? GLOW_REDUCED_MS : GLOW_MS
    clearTimeout(glowing)
    element.classList.add('is-glowing')
    glowing = setTimeout(() => element.classList.remove('is-glowing'), hold)
  }

  /** Fades the shown line out, then `line` in; `arrived` glows once. The latest call wins a fade still running. */
  function present(line: Line, arrived: boolean): void {
    const mine = ++version
    const swap = (): void => {
      if (mine !== version || !element.isConnected) return
      draw(line)
      fadeIn(words)
      if (arrived) glow()
    }
    const fade = rungLine.hidden ? 0 : stateFadeMs()
    if (fade === 0) {
      swap()
      return
    }
    words.classList.add('is-leaving')
    setTimeout(swap, fade)
  }

  async function request(): Promise<void> {
    field.readOnly = true
    if (guide === 'ollama') think(true)
    try {
      const reply = (await play.post({ type: 'hint_request' })).hint_reply ?? null
      field.value = ''
      if (reply === null) {
        think(false)
        return
      }
      announce(`${strings.speakerGuide} ${reply.text}`)
      present(replyLine(reply), false)
    } catch {
      think(false) // nothing reached the server; the field keeps its words (the reconnecting state lands in 1.24)
    } finally {
      field.readOnly = false
    }
  }

  /**
   * Shows the newest held Cards, newest on top, and counts the rest behind "{n} more in the Card log". Only Cards
   * that change place are inserted or removed, so a Card that keeps its place keeps focus.
   */
  function restack(): void {
    const shown = held.slice(-(triggersShown ? 1 : CARDS_STACKED)).reverse()
    shown.forEach((card, index) => {
      if (stack.children[index] !== card) stack.insertBefore(card, stack.children[index] ?? null)
    })
    while (stack.children.length > shown.length) stack.lastElementChild?.remove()
    stack.hidden = shown.length === 0
    const rest = held.length - shown.length
    more.textContent = fill(strings.moreInCardLog, { n: rest })
    more.hidden = rest === 0
  }

  function dismiss(card: HTMLElement): void {
    const at = [...stack.children].indexOf(card)
    held.splice(held.indexOf(card), 1)
    card.remove()
    restack()
    const next = stack.children[at] ?? stack.lastElementChild
    if (next instanceof HTMLElement) next.focus()
    else field.focus()
  }

  /** Stacks every waiting Card, each fading in and written once to the live region; nothing while a lock-open plays. */
  function enter(): void {
    if (holding !== undefined || waiting.length === 0) return
    const arrived = waiting.splice(0).map(({ card, first }) => {
      const text = cardText(room, card)
      const made = tricksterCard(text, first, () => dismiss(made))
      held.push(made)
      return { made, line: cardAnnouncement(text, first) }
    })
    restack()
    upper.scrollTop = 0 // the newest Card is on top
    for (const { made } of arrived) if (made.isConnected) fadeIn(made)
    announce(arrived.map(({ line }) => line).join(' '))
  }

  /** Holds new Cards for the lock-open state: the Open chip, then the entry collapse and the next Puzzle's fade-in. */
  function hold(): void {
    clearTimeout(holding)
    holding = setTimeout(() => {
      holding = undefined
      if (element.isConnected) enter()
    }, OPEN_HOLD_MS + stateFadeMs())
  }

  function receiveCards(state: SessionState): void {
    if (state.locks_open.length > locksSeen) hold()
    locksSeen = state.locks_open.length
    state.cards.slice(cardsHeard).forEach((card, index) => waiting.push({ card, first: cardsHeard + index === 0 }))
    cardsHeard = state.cards.length
    enter()
  }

  function triggersOpen(open: boolean): void {
    triggersShown = open
    element.classList.toggle('is-triggers-open', open)
    restack()
  }

  function render(state: SessionState): void {
    latest = state
    receiveCards(state)
    const n = place(state.active_puzzle_id)
    field.setAttribute('aria-label', n === null ? strings.askTheGuide : fill(strings.hintFieldLabel, { n }))
    const arrived = state.rung_changes.slice(heard)
    heard = state.rung_changes.length
    const newest = arrived.at(-1)
    if (newest === undefined) return
    announce(arrived.map((change) => `${strings.speakerGuide} ${change.text}`).join(' '))
    present(changeLine(newest), true)
  }

  function opening(line: string): void {
    if (rungLine.hidden) present({ label: null, text: line, shown: null }, false)
  }

  render(latest)
  const last = latest.rung_changes.at(-1)
  if (last !== undefined) draw(changeLine(last))
  else if (play.openingLine !== null) draw({ label: null, text: play.openingLine, shown: null })
  else think(false)

  return { element, render, opening, triggers, triggersOpen }
}
