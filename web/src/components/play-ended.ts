import './button.css'
import './play-ended.css'
import { strings } from '../strings.ts'
import { secondaryButton } from './button.ts'

/**
 * The Scene frame's play-through-ended state (UX-DR22): over the dimmed photo, the plain Session-gone line on a
 * centered `chrome-raised` box with "Start again" (secondary), which calls `onStartAgain`.
 */
export function playEnded(onStartAgain: () => void): HTMLElement {
  const element = document.createElement('div')
  element.className = 'play-ended'
  const box = document.createElement('div')
  box.className = 'play-ended-box'
  const line = document.createElement('p')
  line.className = 'play-ended-line body-md'
  line.textContent = strings.sessionGone
  box.append(line, secondaryButton({ label: strings.startAgain, onActivate: onStartAgain }))
  element.append(box)
  return element
}
