import './triggers-panel.css'
import type { PlayView, RungChangeEvent, SessionState, Thresholds } from '../../types'
import { CUT_5, placeHref } from '../router.ts'
import { fill, strings } from '../strings.ts'
import { secondaryButton, toggleButton } from './button.ts'
import { rungLabel } from './hint-area.ts'

const LIST_ID = 'triggers-list'

/** Seconds from ms as the panel prints them: whole, or with one decimal when the server's value has one. */
function seconds(ms: number): string {
  return String(Math.round(ms / 100) / 10)
}

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
 * The header's two lines from the server's effective values: "Nudge after {threshold} s idle or 3 wrong attempts ·
 * next hint no sooner than {spacing} s", each number followed by its 1× value where the session clock scaled it (a
 * Demo timescale above 1), then where the threshold came from. Nothing here computes a threshold or a spacing.
 */
export function triggersHeader(thresholds: Thresholds): [string, string] {
  const oneX = (ms: number, base: number): string => (ms === base ? '' : ` ${fill(strings.atOneX, { s: seconds(base) })}`)
  const nudge = fill(strings.triggersNudge, { threshold: seconds(thresholds.nudge_threshold_ms) })
  const spacing = fill(strings.triggersSpacing, { spacing: seconds(thresholds.rung_spacing_ms) })
  const timing = `${nudge}${oneX(thresholds.nudge_threshold_ms, thresholds.nudge_threshold_base_ms)} ${spacing}${oneX(
    thresholds.rung_spacing_ms,
    thresholds.rung_spacing_base_ms,
  )}`
  return [timing, thresholds.source === 'derived' ? strings.thresholdDerived : strings.thresholdFresh]
}

/**
 * Why a Rung arrived, from the logged events its `triggered_by` names (`trigger_events`, their type and `t_ms`), read
 * off the shapes the Rung selector writes: three or more name the wrong attempts, so "3 wrong attempts"; a lone
 * Trickster Card is the Loosen card that opened the Rung; else it was Idle, "Idle {s} s" being the triggering event's
 * `t_ms` minus the `t_ms` of the other event named (the one Idle counts from), or minus 0 when none is. Every `t_ms`
 * is the server's session clock, never scaled and never read from the browser.
 */
export function triggerCause(change: RungChangeEvent, events: SessionState['trigger_events'] = {}): string {
  const named = change.triggered_by.map((position) => events[position])
  const tick = named.at(-1)
  if (named.length >= 3 || tick === undefined) return strings.threeWrongAttempts
  if (named.length === 1 && tick.type === 'trickster_card') return strings.loosenCard
  const from = named.length === 2 ? (named[0]?.t_ms ?? 0) : 0
  return fill(strings.idleSeconds, { s: Math.round((tick.t_ms - from) / 1000) })
}

/** One row: "Puzzle {n} · {Rung name} · {cause} · worded on this Mac · {s} s" or "… · as written"; never Rung text. */
export function triggersRow(room: PlayView, change: RungChangeEvent, events: SessionState['trigger_events']): string {
  const n = room.puzzles.findIndex((puzzle) => puzzle.id === change.puzzle_id) + 1
  const worded =
    change.phrased && change.phrasing_ms !== null
      ? fill(strings.wordedOnThisMac, { s: (change.phrasing_ms / 1000).toFixed(1) })
      : strings.asWritten
  return [rungLabel(n, change.rung), triggerCause(change, events), worded].join(strings.modeSeparator)
}

export interface TriggersList {
  /** The header and the rows on `chrome`; the rows scroll past `{spacing.triggers-panel-max}`. */
  element: HTMLElement
  /** Draws `state`: the header from its `thresholds`, one row per `rung_changes[]` entry, newest last and in view. */
  render: (state: SessionState) => void
  /** Scrolls the newest row into view (the list has no height while it is hidden). */
  reveal: () => void
}

/**
 * The Triggers panel's content (`{components.triggers-panel}`, FR-16, UX-DR33), the same in place and, under cut 5,
 * in the second window: one plain `body-sm` header, then one `body-sm` row per Rung change with `mono-sm` numbers,
 * the newest last in `text`, older rows `text-muted`, or "No hint changes yet." with none. The rows are never written
 * to the live region; the Rung line already announced each one.
 */
export function triggersList(room: PlayView): TriggersList {
  const element = document.createElement('div')
  element.id = LIST_ID
  element.className = 'triggers-panel'
  const header = document.createElement('p')
  header.className = 'triggers-header body-sm'
  const timing = document.createElement('span')
  const source = document.createElement('span')
  source.className = 'triggers-source'
  header.append(timing, source)
  const rows = document.createElement('ol')
  rows.className = 'triggers-rows'
  const empty = document.createElement('p')
  empty.className = 'triggers-empty body-sm'
  empty.textContent = strings.noHintChanges
  element.append(header, empty, rows)
  let drawn = -1

  function reveal(): void {
    rows.scrollTop = rows.scrollHeight
    element.scrollTop = element.scrollHeight // the panel scrolls only on a Hint area short even of one row
  }

  function render(state: SessionState): void {
    const thresholds = state.thresholds ?? null
    header.hidden = thresholds === null
    if (thresholds !== null) [timing.textContent, source.textContent] = triggersHeader(thresholds)
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
 * The Triggers toggle "Triggers ({n})" under the hint controls, n the number of Rung changes: a secondary button with
 * an expanded state, collapsed by default and opened at once when the session loads with a Disclosure active; the
 * player can still collapse it. `onOpen` tells the Hint area, which may grow past its cap while the panel is open.
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
  const open = !CUT_5 && session.disclosure.length > 0
  const toggle = CUT_5
    ? secondaryButton({ label: '', onActivate: () => window.open(href, `triggers-${session.id}`, 'popup,width=1024,height=480') })
    : toggleButton({
        label: '',
        state: 'expanded',
        on: open,
        controls: LIST_ID,
        onToggle: (on) => {
          list.element.hidden = !on
          onOpen(on)
          if (on) list.reveal()
        },
      })
  toggle.classList.add('triggers-toggle')
  list.element.hidden = !open
  element.append(toggle, ...(CUT_5 ? [] : [list.element]))

  function render(state: SessionState): void {
    const label = document.createElement('span') // one flex item, so the name reads "Triggers (2)" unbroken
    label.append(...withNumbers(fill(strings.triggers, { n: state.rung_changes.length })))
    toggle.replaceChildren(label)
    list.render(state)
  }

  render(session)
  onOpen(open)
  return { element, render, reveal: list.reveal }
}
