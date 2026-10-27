import type { Meta, SessionState } from '../types'
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

/** The Guide's role line for the `guide` setting (UX-DR74): Local with Ollama, or shown as written. */
export function guideRoleLine(guide: Meta['guide']): string {
  return guide === 'ollama' ? strings.guideRoleLocal : strings.guideRoleWritten
}

/**
 * The First-room welcome over the first Scene (FR-21, UX-DR45, UX-DR64): `body` takes the scrim, every element in
 * `held` (the top bar, the Scene column, the side column) is inert while it shows, and focus is trapped on "Begin",
 * its only control and the only way to dismiss it: Escape and clicks anywhere do nothing, and Tab stays put. The
 * Guide's introduction, `line` and the voice line are written to the live region once. The plain tip naming "Show all
 * objects" sits on the scrim under the card. "Begin" records that play has begun, closes the card and calls
 * `onBegin`. Returns the teardown.
 */
export function mountWelcome(
  sessionId: string,
  guide: Meta['guide'],
  line: string,
  body: HTMLElement,
  held: readonly HTMLElement[],
  onBegin: () => void,
): () => void {
  const role = guideRoleLine(guide)
  const overlay = greetingOverlay(role, line)
  const { begin } = overlay
  const tip = document.createElement('p')
  tip.className = 'greeting-tip body-sm'
  tip.textContent = strings.showAllTip
  overlay.element.append(tip)

  /** No pointer press anywhere moves focus off "Begin"; a click on it still fires. */
  const keepFocus = (event: MouseEvent): void => event.preventDefault()
  const trap = (event: KeyboardEvent): void => {
    if (event.key !== 'Tab') return
    event.preventDefault()
    begin.focus()
  }

  for (const element of held) element.inert = true
  body.append(overlay.element)
  document.addEventListener('mousedown', keepFocus, true)
  document.addEventListener('keydown', trap, true)
  overlay.show()
  begin.focus()
  announce(fill(strings.guideIntroduction, { 'role line': role, 'opening line': line, 'voice line': strings.guideVoice }))

  let open = true
  function close(): void {
    if (!open) return
    open = false
    document.removeEventListener('mousedown', keepFocus, true)
    document.removeEventListener('keydown', trap, true)
    overlay.element.remove()
    for (const element of held) element.inert = false
  }

  begin.addEventListener('click', () => {
    markBegun(sessionId)
    close()
    onBegin()
  })
  return close
}
