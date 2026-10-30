import './triggers-panel.css'
import type { PlayView, RungChangeEvent, SessionState } from '../../types'
import { CUT_5, placeHref } from '../router.ts'
import { fill, strings } from '../strings.ts'
import { secondaryButton } from './button.ts'

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
 * The content of "How hints work" (`{components.triggers-panel}`, FR-16, UX-DR33; story mode, owner decision Oct 29),
 * in the Card log and, under cut 5, in the second window: the one plain `body-sm` line, "The chest holds 2 hints for
 * the whole game. Each one opens the next hint for the riddle you're on. Nothing opens on its own.", then the hint
 * history, one `body-sm` row per Rung change with `mono-sm` numbers, the newest last in `text`, older rows
 * `text-muted`. The rows are never written to the live region; the chest already announced each hint.
 */
export function triggersList(room: PlayView): TriggersList {
  const element = document.createElement('div')
  element.className = 'triggers-panel'
  const header = document.createElement('p')
  header.className = 'triggers-header body-sm'
  header.textContent = strings.hintsExplained
  const rows = document.createElement('ol')
  rows.className = 'triggers-rows'
  element.append(header, rows)
  let drawn = -1

  /** Scrolls the rows only, so the plain line above them stays in view. */
  function reveal(): void {
    rows.scrollTop = rows.scrollHeight
  }

  function render(state: SessionState): void {
    if (state.rung_changes.length === drawn) return
    drawn = state.rung_changes.length
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

/**
 * "How hints work" in the Card log (story mode): the list in place, or under cut 5 a button that opens it in the second
 * window, `#/triggers/<session_id>`, 1024 px wide, since below that the Narrow-screen message replaces every route.
 */
export function howHintsWork(room: PlayView, sessionId: string, profile: string): TriggersList {
  const list = triggersList(room)
  if (!CUT_5) return list
  const href = placeHref({ route: { name: 'triggers', sessionId }, profile })
  const element = secondaryButton({
    label: strings.howHintsWork,
    onActivate: () => window.open(href, `triggers-${sessionId}`, 'popup,width=1024,height=480'),
  })
  return { element, render: () => undefined, reveal: () => undefined }
}
