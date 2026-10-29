import './triggers-panel.css'
import type { PlayView, RungChangeEvent, SessionState, Thresholds } from '../../types'
import { CUT_5, placeHref } from '../router.ts'
import { fill, strings } from '../strings.ts'
import { secondaryButton, toggleButton } from './button.ts'

const LIST_ID = 'triggers-list'

/** `text` with every number in a `mono-sm` span, the rest plain (DESIGN.md: `body-sm` rows, `mono-sm` numbers). */
function withNumbers(text: string): Node[] {
  return text.split(/(\d+(?:\.\d+)?)/).map((part, i) => {
    if (i % 2 === 0) return document.createTextNode(part)
    const number = document.createElement('span')
    number.className = 'mono-sm'
    number.textContent = part
    return number
  })
}

/**
 * The panel's opening lines in player words: when the Guide offers a hint, then, for a returning player (the
 * threshold came from the Derived block), that the wait was set by how they played last time. Nothing here computes
 * a threshold or a spacing.
 */
export function hintsIntro(thresholds: Thresholds | null): string[] {
  return thresholds === null || thresholds.source === 'fresh' ? [strings.hintsExplained] : [strings.hintsExplained, strings.thresholdDerived]
}

/**
 * Why a Rung arrived, from the logged events its `triggered_by` names (`trigger_events`, their type and `t_ms`), read
 * off the shapes the Rung selector writes: three or more name the wrong attempts, "after three wrong tries"; a lone
 * Trickster Card is the Loosen card that opened it early; a lone Hint request is an ask, "when you asked"; else it was
 * a quiet stretch, its seconds being the triggering event's `t_ms` minus the `t_ms` of the other event named (the one
 * Idle counts from), or minus 0 when none is. Every `t_ms` is the server's session clock, never scaled and never read
 * from the browser.
 */
export function triggerCause(change: RungChangeEvent, events: SessionState['trigger_events'] = {}): string {
  const named = change.triggered_by.map((position) => events[position])
  const tick = named.at(-1)
  if (named.length >= 3 || tick === undefined) return strings.afterThreeWrongTries
  if (named.length === 1 && tick.type === 'trickster_card') return strings.openedByTrickster
  if (named.length === 1 && tick.type === 'hint_request') return strings.whenYouAsked
  const from = named.length === 2 ? (named[0]?.t_ms ?? 0) : 0
  return fill(strings.afterQuietSeconds, { s: Math.round((tick.t_ms - from) / 1000) })
}

/** One row: "Puzzle {n}, hint {k}, {cause}", then ", worded on this Mac" when the Guide model worded it; never Rung text. */
export function triggersRow(room: PlayView, change: RungChangeEvent, events: SessionState['trigger_events']): string {
  const n = room.puzzles.findIndex((puzzle) => puzzle.id === change.puzzle_id) + 1
  const row = fill(strings.hintRow, { n, k: change.rung, cause: triggerCause(change, events) })
  return change.phrased ? `${row}, ${strings.wordedOnThisMac}` : row
}

export interface TriggersList {
  /** The opening lines and the rows on `chrome`; the rows scroll past `{spacing.triggers-panel-max}`. */
  element: HTMLElement
  /** Draws `state`: the opening lines, one row per `rung_changes[]` entry, newest last and in view. */
  render: (state: SessionState) => void
  /** Scrolls the newest row into view (the list has no height while it is hidden). */
  reveal: () => void
}

/**
 * The content of "How hints work" (`{components.triggers-panel}`, FR-16, UX-DR33; player words, owner decision Oct 29),
 * the same in place and, under cut 5, in the second window: the plain `body-sm` opening lines, then the hint history,
 * one `body-sm` row per Rung change with `mono-sm` numbers, the newest last in `text`, older rows `text-muted`, or
 * "No hints yet." with none. The rows are never written to the live region; the Rung line already announced each one.
 */
export function triggersList(room: PlayView): TriggersList {
  const element = document.createElement('div')
  element.id = LIST_ID
  element.className = 'triggers-panel'
  const header = document.createElement('p')
  header.className = 'triggers-header body-sm'
  const rows = document.createElement('ol')
  rows.className = 'triggers-rows'
  const empty = document.createElement('p')
  empty.className = 'triggers-empty body-sm'
  empty.textContent = strings.noHintsYet
  element.append(header, empty, rows)
  let drawn = -1

  function reveal(): void {
    rows.scrollTop = rows.scrollHeight
    element.scrollTop = element.scrollHeight // the panel scrolls only on a Hint area short even of one row
  }

  function render(state: SessionState): void {
    header.replaceChildren(
      ...hintsIntro(state.thresholds ?? null).map((line) => {
        const span = document.createElement('span')
        span.className = 'triggers-line'
        span.textContent = line
        return span
      }),
    )
    if (state.rung_changes.length === drawn) return
    drawn = state.rung_changes.length
    empty.hidden = drawn > 0
    rows.hidden = drawn === 0
    rows.replaceChildren(
      ...state.rung_changes.map((change) => {
        const row = document.createElement('li')
        row.className = 'triggers-row body-sm'
        row.append(...withNumbers(triggersRow(room, change, state.trigger_events)))
        return row
      }),
    )
    reveal()
  }

  return { element, render, reveal }
}

export interface TriggersPanel {
  element: HTMLElement
  render: (state: SessionState) => void
  /** Scrolls the newest row into view; called once the panel is in the document, since a detached list cannot scroll. */
  reveal: () => void
}

/**
 * "How hints work" under the hint button: a quiet text button with an expanded state, collapsed until the player
 * opens it (owner decision Oct 29: it replaced the "Triggers ({n})" toggle, and it no longer opens by itself under a
 * Disclosure). `onOpen` tells the Hint area, which may grow past its cap while the panel is open.
 * Under cut 5 the same button opens `#/triggers/<session_id>` in a second window instead, and nothing opens in place;
 * the window is 1024 px wide, since below that the Narrow-screen message replaces every route.
 */
export function triggersPanel(
  room: PlayView,
  session: SessionState,
  profile: string,
  onOpen: (open: boolean) => void,
): TriggersPanel {
  const element = document.createElement('div')
  element.className = 'triggers'
  const list = triggersList(room)
  const href = placeHref({ route: { name: 'triggers', sessionId: session.id }, profile })
  const label = strings.howHintsWork
  const toggle = CUT_5
    ? secondaryButton({ label, onActivate: () => window.open(href, `triggers-${session.id}`, 'popup,width=1024,height=480') })
    : toggleButton({ label, state: 'expanded', controls: LIST_ID, onToggle: show })
  toggle.className = 'triggers-toggle body-sm' // a quiet text button, not the secondary one
  list.element.hidden = true
  element.append(toggle, ...(CUT_5 ? [] : [list.element]))

  function show(on: boolean): void {
    toggle.setAttribute('aria-expanded', String(on))
    list.element.hidden = !on
    onOpen(on)
    if (on) list.reveal()
  }

  onOpen(false)
  list.render(session)
  return { element, render: list.render, reveal: list.reveal }
}
