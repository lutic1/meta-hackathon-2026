import './feedback-line.css'
import { fadeIn } from '../fade.ts'
import { wizardPortrait } from '../wizards/portrait.ts'

/** The line is held this long after it arrives, then fades out (owner decision, Oct 29). */
export const FEEDBACK_HOLD_MS = 2500

export interface FeedbackLine {
  element: HTMLElement
  /** Shows `text` beside the Guide, fading in over the shown line, held `FEEDBACK_HOLD_MS`, then fading out. */
  say: (text: string) => void
}

/**
 * The feedback line (`{components.feedback-line}`): a parchment strip over the bottom edge of the Scene frame, the
 * Guide's 32 px portrait beside one line in `wizard-line` type, the same place for every reply. It takes no pointer, so
 * a Hotspot under it still answers, and it is hidden from assistive technology: the Play screen writes the same line
 * to the live region once.
 */
export function feedbackLine(): FeedbackLine {
  const element = document.createElement('div')
  element.className = 'feedback-line'
  element.setAttribute('aria-hidden', 'true')
  const words = document.createElement('p')
  words.className = 'wizard-line'
  element.append(wizardPortrait('guide', 32), words)
  let timer: ReturnType<typeof setTimeout> | undefined

  function say(text: string): void {
    words.textContent = text
    element.classList.add('is-shown')
    fadeIn(element)
    clearTimeout(timer)
    timer = setTimeout(() => element.classList.remove('is-shown'), FEEDBACK_HOLD_MS)
  }

  return { element, say }
}
