import './timer.css'
import { fill, strings } from '../strings.ts'

/**
 * The Timer's three faces: counting from T0 (Hosted: shown as "queued" while the Build waits in line), frozen at
 * T1 − T0 (Hosted: with the time it spent in the queue, when it waited), or frozen beside an end status.
 */
export type TimerFace =
  | { kind: 'running'; elapsedMs: number; queued?: boolean }
  | { kind: 'playable'; elapsedMs: number; queueMs?: number | null }
  | { kind: 'ended'; elapsedMs: number; status: string }

export interface Timer {
  element: HTMLElement
  render: (face: TimerFace) => void
}

/** `elapsedMs` as m:ss, whole seconds. */
export function formatElapsed(elapsedMs: number): string {
  const seconds = Math.floor(Math.max(0, elapsedMs) / 1000)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}

/** "includes m:ss in the queue", the queue time in the same m:ss as the digits. */
function queueNote(queueMs: number): string {
  const [m, ss] = formatElapsed(queueMs).split(':')
  return fill(strings.queueNote, { m, ss })
}

/**
 * `{components.timer}` (UX-DR17): a plain `label` in `text-muted`, then `mono-timer` m:ss digits. Running: "Photos
 * to play", a static 6 px lamp dot and `text` digits. At T1: "Playable in" and the frozen digits in `success`, no
 * dot. At an end status: the frozen digits and the status in `text-muted`, no dot. Hosted: while the Build is
 * `queued` the word "queued" in `label` stands in place of the digits; after a queue the frozen digits carry the note
 * "includes m:ss in the queue" in `label` `text-muted`. The label and the digits are text in one `timer` element, so
 * a screen reader reads them together; the dot is decoration.
 */
export function timer(): Timer {
  const element = document.createElement('div')
  element.className = 'timer'
  element.setAttribute('role', 'timer')
  const label = document.createElement('span')
  label.className = 'timer-label label'
  const dot = document.createElement('span')
  dot.className = 'timer-dot'
  dot.setAttribute('aria-hidden', 'true')
  const digits = document.createElement('span')
  digits.className = 'timer-digits mono-timer'
  const status = document.createElement('span')
  status.className = 'timer-status label'
  element.append(label, dot, digits, status)

  function render(face: TimerFace): void {
    const queued = face.kind === 'running' && face.queued === true
    const queueMs = face.kind === 'playable' ? (face.queueMs ?? null) : null
    element.dataset.state = queued ? 'queued' : face.kind
    label.textContent = face.kind === 'playable' ? strings.playableIn : strings.photosToPlay
    dot.hidden = face.kind !== 'running'
    digits.className = `timer-digits ${queued ? 'label' : 'mono-timer'}`
    digits.textContent = queued ? strings.timerQueued : formatElapsed(face.elapsedMs)
    status.hidden = face.kind !== 'ended' && queueMs === null
    if (face.kind === 'ended') status.textContent = face.status
    else if (queueMs !== null) status.textContent = queueNote(queueMs)
    else status.textContent = ''
  }

  return { element, render }
}
