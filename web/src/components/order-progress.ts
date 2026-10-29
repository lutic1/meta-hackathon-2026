import './order-progress.css'
import type { PlayPuzzle, SessionState } from '../../types'
import type { PlaySession } from '../play.ts'
import { fill, strings } from '../strings.ts'
import { secondaryButton } from './button.ts'

/** A full-length mismatch holds the pips in `wrong` this long before they empty (UX-DR35). */
export const WRONG_FLASH_MS = 300

export interface OrderProgress {
  element: HTMLElement
  /** Draws the control, the pips and "Not this · n" from the server's order buffer and Wrong attempts. */
  update: (state: SessionState) => void
}

function reducedMotion(): boolean {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/**
 * An `order` Puzzle's lock input (`{components.order-progress}`, FR-12, UX-DR35): a secondary "Start the sequence"
 * control on the notes tray, one 10 px pip per position of the sequence (`sequence_length`) with the visually hidden
 * description "{filled} of {length}", and the Not this chip. The control posts the order start lock input, or the
 * order stop one while the sequence is armed; it is the same button either way, so it keeps focus as its label turns
 * to "Stop the sequence" and back. The sequence is armed exactly while `order_buffer.puzzle_id` names this Puzzle, and
 * each pip fills in `lamp` only for a click the server holds in the buffer, never optimistically and never showing
 * which clicks were right; the client never decides the disarm. A rise in this Puzzle's Wrong attempts while armed is
 * a full-length mismatch: the pips turn `wrong` for 300 ms (an instant reset under reduced motion), then empty,
 * and "Not this · n" shows until the sequence is disarmed. A disarm (stopped, or another Puzzle Active) only empties
 * the pips: no flash and no Not this. A reload draws the armed state and filled pips from the first state.
 */
export function orderProgress(puzzle: PlayPuzzle, play: PlaySession): OrderProgress {
  const length = puzzle.sequence_length ?? 0
  const element = document.createElement('div')
  element.className = 'order-lock'

  const description = document.createElement('span')
  description.id = `order-progress-${puzzle.id}`
  description.className = 'visually-hidden'

  let pending = false
  let armed = false
  async function toggle(): Promise<void> {
    if (pending) return
    pending = true
    const input = { type: armed ? ('order_stop' as const) : ('order_start' as const), puzzle_id: puzzle.id }
    try {
      await play.post({ type: 'lock_input', input })
    } catch {
      // nothing reached the server; the control keeps its label (the reconnecting state lands in 1.24)
    } finally {
      pending = false
    }
  }
  const control = secondaryButton({ label: strings.startSequence, onActivate: () => void toggle() })
  control.setAttribute('aria-describedby', description.id)

  const pips = document.createElement('span')
  pips.className = 'order-pips'
  pips.setAttribute('aria-hidden', 'true')
  const pip = Array.from({ length }, () => {
    const one = document.createElement('i')
    one.className = 'order-pip'
    return one
  })
  pips.append(...pip)

  const chip = document.createElement('span')
  chip.className = 'chip chip-not-this label'
  chip.hidden = true

  element.append(control, pips, description, chip)

  let filled = 0
  /** Wrong attempts as the last drawn state counted them; undefined before the first draw, which flashes nothing. */
  let counted: number | undefined
  let flashing: ReturnType<typeof setTimeout> | undefined

  function drawPips(count: number, wrong: boolean): void {
    pips.classList.toggle('is-wrong', wrong)
    pip.forEach((one, index) => one.classList.toggle('is-filled', index < count))
  }

  function update(state: SessionState): void {
    armed = state.order_buffer.puzzle_id === puzzle.id
    filled = armed ? (state.order_buffer.clicks ?? []).length : 0
    const attempts = state.wrong_attempts[puzzle.id] ?? 0
    const mismatch = armed && counted !== undefined && attempts > counted
    counted = attempts
    control.textContent = armed ? strings.stopSequence : strings.startSequence
    description.textContent = fill(strings.sequenceProgress, { filled, length })
    if (mismatch) {
      chip.textContent = fill(strings.notThis, { n: attempts })
      chip.hidden = false
    } else if (!armed) chip.hidden = true
    // A flash in progress holds until it ends, unless the server already holds a new click.
    if (flashing !== undefined && armed && filled === 0 && !mismatch) return
    clearTimeout(flashing)
    flashing = undefined
    if (!mismatch || filled > 0 || reducedMotion()) {
      drawPips(filled, false)
      return
    }
    drawPips(length, true)
    flashing = setTimeout(() => {
      flashing = undefined
      drawPips(filled, false)
    }, WRONG_FLASH_MS)
  }

  return { element, update }
}
