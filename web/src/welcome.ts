import type { Meta, OpeningLine, SessionState } from '../types'
import { greetingOverlay } from './components/greeting-overlay.ts'
import { announce } from './live-region.ts'
import { fill, strings } from './strings.ts'

const BEGUN_KEY = 'keyframe-begun:'

function begunHere(sessionId: string): boolean {
  try {
    return sessionStorage.getItem(BEGUN_KEY + sessionId) !== null
  } catch {
    return false
  }
}

function markBegun(sessionId: string): void {
  try {
    sessionStorage.setItem(BEGUN_KEY + sessionId, '1')
  } catch {
    // Storage refused: the session state alone tells a reload whether play has begun.
  }
}

/**
 * Whether play has begun in this session, so a reload never shows the First-room welcome again: "Begin" was pressed
 * in this tab, or the state already carries play (an open lock, a held item, a Wrong attempt, an armed order, a
 * hint asked, a Rung or a Card).
 */
export function playHasBegun(state: SessionState): boolean {
  return (
    begunHere(state.id) ||
    state.locks_open.length > 0 ||
    state.inventory.length > 0 ||
    Object.values(state.wrong_attempts).some((count) => count > 0) ||
    (state.order_buffer.puzzle_id ?? null) !== null ||
    state.rungs_used > 0 ||
    state.rung_changes.length > 0 ||
    state.cards.length > 0
  )
}

/**
 * The Guide's role line for the mode and the `guide` setting (UX-DR74): Local with Ollama names Llama 3.2 3B on this
 * Mac; Hosted, and Local shown as written, end "shown as written".
 */
export function guideRoleLine(mode: Meta['mode'], guide: Meta['guide']): string {
  return mode === 'local' && guide === 'ollama' ? strings.guideRoleLocal : strings.guideRoleWritten
}

export interface Welcome {
  /** Brings the served line to a card still thinking: it shows, "Begin" takes focus, and it is announced once. */
  arrive: (line: string) => void
  /** Removes the card without "Begin" (the teardown). */
  close: () => void
}

/**
 * The Greeting or First-room welcome over the first Scene (FR-21, UX-DR45, UX-DR64): `body` takes the scrim, every
 * element in `held` (the top bar, the Scene column, the side column) is inert while it shows, and focus is trapped in
 * the card: on "Begin", its only control and the only way to dismiss it, or while a Local Greeting is still being
 * phrased (`opening.text` null), on its heading, with no "Begin" yet and the Guide's static thinking state where the
 * line will go. Escape and clicks anywhere do nothing, and Tab stays put. Once the line is in the card (served at once,
 * or brought by `arrive` from a later state the Play screen's poll reads), "Begin" appears and takes focus, and the
 * Guide's introduction, the line and the voice line are written to the live region once. A First-room welcome also
 * shows the plain tip naming "Show all objects" on the scrim under the card; a Greeting has none. "Begin" records
 * that play has begun, closes the card and calls `onBegin` with the line.
 */
export function mountWelcome(
  sessionId: string,
  mode: Meta['mode'],
  guide: Meta['guide'],
  opening: OpeningLine,
  body: HTMLElement,
  held: readonly HTMLElement[],
  onBegin: (line: string) => void,
): Welcome {
  const role = guideRoleLine(mode, guide)
  const overlay = greetingOverlay(role)
  const { begin, heading } = overlay
  if (opening.kind === 'welcome') {
    const tip = document.createElement('p')
    tip.className = 'greeting-tip body-sm'
    tip.textContent = strings.showAllTip
    overlay.element.append(tip)
  }

  let open = true
  let line: string | null = null
  /** Where focus stays: the heading until the line and "Begin" arrive. */
  const target = (): HTMLElement => (line === null ? heading : begin)
  /** No pointer press anywhere moves focus off the card's target; a click on "Begin" still fires. */
  const keepFocus = (event: MouseEvent): void => event.preventDefault()
  const trap = (event: KeyboardEvent): void => {
    if (event.key !== 'Tab') return
    event.preventDefault()
    target().focus()
  }

  function arrive(served: string): void {
    if (!open || line !== null) return
    line = served
    overlay.arrive(served)
    begin.focus()
    announce(fill(strings.guideIntroduction, { 'role line': role, 'opening line': served, 'voice line': strings.guideVoice }))
  }

  for (const element of held) element.inert = true
  body.append(overlay.element)
  document.addEventListener('mousedown', keepFocus, true)
  document.addEventListener('keydown', trap, true)
  if (opening.text !== null) arrive(opening.text) // served at once, before the card is drawn: no thinking state
  overlay.show()
  if (line === null) heading.focus()

  function close(): void {
    if (!open) return
    open = false
    document.removeEventListener('mousedown', keepFocus, true)
    document.removeEventListener('keydown', trap, true)
    overlay.element.remove()
    for (const element of held) element.inert = false
  }

  begin.addEventListener('click', () => {
    if (line === null) return
    markBegun(sessionId)
    close()
    onBegin(line)
  })
  return { arrive, close }
}
