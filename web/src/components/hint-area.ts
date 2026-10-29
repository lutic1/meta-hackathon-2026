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

/** At most this many Cards stack in the Hint area; only the newest while "How hints work" is open (UX-DR30). */
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

/** "Next hint in m:ss" counts whole seconds: 90 reads "1:30". */
export function countdown(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

/** "Puzzle {n} · Nudge", "· Direction" or "· Near-answer", or "Puzzle {n}" alone for the No-hint line (rung 0). */
export function rungLabel(n: number, rung: number): string {
  return fill(RUNG_LABELS[rung] ?? strings.puzzleHeading, { n })
}

/** A Rung a Loosen card opened: its one triggering log event is the `trickster_card`, as "How hints work" reads it. */
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
  /** Draws `state`: the button's label from the Active puzzle, and each newly arrived `rung_change` as the Rung line. */
  render: (state: SessionState) => void
  /** After "Begin": the opening line as the first Guide line, never announced, unless a Rung line already shows. */
  opening: (line: string) => void
  /** The slot under the hint button that holds "How hints work" and its panel. */
  triggers: HTMLElement
  /** "How hints work" opened or closed: the tray may grow past its cap, and only the newest Card stacks. */
  triggersOpen: (open: boolean) => void
  /** The Guide's unlock aside (lock-opened.ts): a Guide line in the Rung line's place, no label, no glow. */
  aside: (line: string) => void
}

function paragraph(className: string): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = className
  return element
}

/**
 * The Hint area (`{components.hint-area}`, FR-14, UX-DR30 to UX-DR32): a `chrome-raised` tray pinned under the Wizard
 * notes, up to `{spacing.hint-area-max}`, its upper part scrolling (the Cards, then the Rung line) over a lower part
 * that never scrolls: the primary "Get a hint for Puzzle {n}" and the slot of "How hints work". While that panel is
 * open (`is-triggers-open`) or a Card is stacked, the tray may grow past its cap until the Wizard notes reach
 * `{spacing.notes-min}`; short of room the open panel gives way first, to its newest row, and then the upper part
 * scrolls to its end: the line that arrives, or the Card that enters over it (its sentence, its outcome and the Rung
 * line in one frame, the introduction a scroll above). Each time a Card enters or is dismissed the bands are
 * restacked, so `onStacked` is called for the panel to scroll its newest row back into view; its button reveals the
 * row itself.
 *
 * The button posts exactly one `hint_request` with no `puzzle_id`: the server answers for the Active puzzle, the
 * entry marked "Current" and the Puzzle the button names (owner decision Oct 29: the ask opens that Puzzle's next
 * Rung when it is due). While one request is in flight the button reads "The Guide is thinking" and the Guide's ring
 * glows (the Guide pulse, a static lit ring with no animation); with `guide` `ollama` the Rung line also shows
 * "thinking on this Mac" until the reply lands. A reply whose `next_hint_ms` says the next Rung is not due yet turns
 * the label into "Next hint in m:ss", counting down by the second from the server's value (never a clock reading),
 * until it is due or another Puzzle is active; a press meanwhile repeats the current Rung.
 *
 * The Rung line (`{components.rung-line}`) is the Guide portrait, the label "Puzzle {n} · {Rung name}" ("Puzzle {n}"
 * alone on the No-hint line) and the line. Every new line fades the shown one out and itself in (200 ms each way,
 * instant under reduced motion), so a reply that repeats the shown line still visibly arrives, and is announced in
 * the one live region as "The Guide: …". A `rung_change` in a state the server sent (never computed here, and its
 * words taken from `rung_changes[]`) shows the same way with one arrival glow on the portrait ring and the tray edge;
 * a reply the player asked for never glows. The line the Rung line no longer shows moves into its Puzzle's opened
 * Rungs, through `onOpened`; a Rung a Loosen card opened shows there at once as well. The first state is only read:
 * the latest `rung_change`, else the opening line, is drawn without a fade, a glow or an announcement, so a reload
 * rebuilds the Rungs and re-announces nothing. The Guide's asides of the unlock moment (lock-opened.ts) show the same
 * way as the opening line, with no label, no glow (the Scene frame carries that light) and no announcement (the
 * feedback line already is one); the Rung line it replaces keeps its place in its Puzzle's opened Rungs, and the next
 * Rung line replaces it.
 *
 * Trickster cards (FR-19, UX-DR40 to UX-DR42) stack above the Rung line, newest on top: at most `CARDS_STACKED`, only
 * the newest while "How hints work" is open, the rest behind the link "{n} more in the Card log", which opens the
 * Card log through `openCardLog` (focus returns to it when the log closes). Each new entry of the
 * state's `cards[]` (the `TricksterCard` projection) enters with a 200 ms fade once the lock-open state has played out
 * (the Solved chip's `OPEN_HOLD_MS`, then the entry collapse and the next Puzzle's fade-in; a collected item's fade-in
 * starts with the state and ends sooner), and is written once to the live region. A Card stays until dismissed;
 * dismissing it moves focus to the Card now in its place, else the one above, else the hint button. The Session's
 * first Card carries the Trickster's introduction. Cards already in the first state are never stacked, so after a
 * reload none is re-stacked or announced and the introduction never shows again.
 */
export function hintArea(
  room: PlayView,
  play: PlaySession,
  guide: Meta['guide'],
  onOpened: (lines: readonly RungChangeEvent[]) => void,
  openCardLog: (opener: HTMLElement) => void,
  onStacked: () => void,
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
  /** The Puzzle the last reply answered and the whole seconds until an ask opens its next Rung; 0 once it is due. */
  let wait: { puzzleId: string | null; seconds: number } = { puzzleId: null, seconds: 0 }
  let ticking: ReturnType<typeof setInterval> | undefined

  const lower = document.createElement('div')
  lower.className = 'hint-lower'
  const ask = document.createElement('div')
  ask.className = 'hint-ask'
  const button = primaryButton({ label: askLabel, pendingLabel: strings.guideThinking, onActivate: request })
  ask.append(button)
  const triggers = document.createElement('div')
  triggers.className = 'hint-triggers' // "How hints work" and its panel
  lower.append(ask, triggers)
  element.append(upper, lower)

  /** "Get a hint for Puzzle {n}" for the Active puzzle, or "Next hint in m:ss" while its next Rung is not due. */
  function askLabel(): string {
    const n = place(latest.active_puzzle_id)
    if (n === null) return strings.askTheGuide
    if (wait.seconds > 0 && wait.puzzleId === latest.active_puzzle_id) {
      return fill(strings.nextHintIn, { time: countdown(wait.seconds) })
    }
    return fill(strings.getHint, { n })
  }

  /** Relabels the button, unless a request is in flight (it reads "The Guide is thinking" until it settles). */
  function relabel(): void {
    if (!button.hasAttribute('aria-busy')) button.textContent = askLabel()
  }

  /** Counts the reply's wait down by the second, from the server's value. */
  function countDown(reply: HintReply): void {
    clearInterval(ticking)
    wait = { puzzleId: reply.puzzle_id, seconds: Math.ceil((reply.next_hint_ms ?? 0) / 1000) }
    if (wait.seconds === 0) return
    ticking = setInterval(() => {
      wait.seconds -= 1
      if (wait.seconds <= 0 || !element.isConnected) clearInterval(ticking)
      relabel()
    }, 1000)
  }

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
    upper.scrollTop = upper.scrollHeight // the Rung line is last, under any Card
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
    element.classList.add('is-asking')
    if (guide === 'ollama') think(true)
    try {
      const reply = (await play.post({ type: 'hint_request' })).hint_reply ?? null
      if (reply === null) {
        think(false)
        return
      }
      countDown(reply)
      announce(`${strings.speakerGuide} ${reply.text}`)
      present(replyLine(reply), false)
    } catch {
      think(false) // nothing reached the server (the reconnecting state lands in 1.24)
    } finally {
      element.classList.remove('is-asking')
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
    onStacked()
    const next = stack.children[at] ?? stack.lastElementChild
    if (next instanceof HTMLElement) next.focus()
    else button.focus()
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
    upper.scrollTop = upper.scrollHeight // the newest Card's sentence and outcome sit over the Rung line
    for (const { made } of arrived) if (made.isConnected) fadeIn(made)
    announce(arrived.map(({ line }) => line).join(' '))
    onStacked()
  }

  /** Holds new Cards for the lock-open state: the Solved chip, then the entry collapse and the next Puzzle's fade-in. */
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
    relabel()
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

  return {
    element,
    render,
    opening,
    triggers,
    triggersOpen,
    aside: (line) => present({ label: null, text: line, shown: null }, false),
  }
}
