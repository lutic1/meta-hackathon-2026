import './timer.css'
import { strings } from '../strings.ts'

/** The Timer's three faces: counting from T0, frozen at T1 − T0, or frozen beside an end status. */
export type TimerFace =
  | { kind: 'running'; elapsedMs: number }
  | { kind: 'playable'; elapsedMs: number }
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

/**
 * `{components.timer}` (UX-DR17): a plain `label` in `text-muted`, then `mono-timer` m:ss digits. Running: "Photos
 * to play", a static 6 px lamp dot and `text` digits. At T1: "Playable in" and the frozen digits in `success`, no
 * dot. At an end status: the frozen digits and the status in `text-muted`, no dot. The label and the digits are text
 * in one `timer` element, so a screen reader reads them together; the dot is decoration.
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
    element.dataset.state = face.kind
    label.textContent = face.kind === 'playable' ? strings.playableIn : strings.photosToPlay
    dot.hidden = face.kind !== 'running'
    digits.textContent = formatElapsed(face.elapsedMs)
    status.hidden = face.kind !== 'ended'
    status.textContent = face.kind === 'ended' ? face.status : ''
  }

  return { element, render }
}
