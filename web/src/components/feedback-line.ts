import './feedback-line.css'
import { fadeIn } from '../fade.ts'
import { strings } from '../strings.ts'
import { wizardPortrait } from '../wizards/portrait.ts'

/** The line is held this long after it arrives, then fades out (owner decision, Oct 29). */
export const FEEDBACK_HOLD_MS = 2500

/** The coach pill steps aside on its own after this long (spec 3.2). */
export const COACH_MS = 15000

export interface FeedbackLine {
  element: HTMLElement
  /** The coach pill, in the same slot: hidden while a line shows. */
  coachPill: HTMLElement
  /** Shows `text` beside the Guide, fading in over the shown line, held `FEEDBACK_HOLD_MS`, then fading out. */
  say: (text: string) => void
  /** Shows the coach pill for at most `COACH_MS`, or takes it away. */
  coach: (on: boolean) => void
}

/**
 * The feedback line (`{components.feedback-line}`): a parchment strip centred at the photo's bottom, 22 px up, the
 * Guide's 30 px portrait beside one line in `wizard-line` type, the same place for every reply. It takes no pointer, so
 * a Hotspot under it still answers, and it is hidden from assistive technology: the Play screen writes the same line
 * to the live region once. The coach pill (story mode, spec 3.2), "Click things in the photo · Turn with ← → or the
 * edges" in plain words, shares its slot and steps aside while a line shows.
 */
export function feedbackLine(): FeedbackLine {
  const element = document.createElement('div')
  element.className = 'feedback-line'
  element.setAttribute('aria-hidden', 'true')
  const words = document.createElement('p')
  words.className = 'wizard-line'
  element.append(wizardPortrait('guide', 30), words)
  const coachPill = document.createElement('p')
  coachPill.className = 'coach-pill body-sm'
  // The arrows read as keys: each one in a key cap; the words stay one line for a screen reader.
  coachPill.append(
    ...strings.coachPill.split(new RegExp(`(${strings.keyLeft}|${strings.keyRight})`)).map((part) => {
      if (part !== strings.keyLeft && part !== strings.keyRight) return part
      const key = document.createElement('kbd')
      key.textContent = part
      return key
    }),
  )
  coachPill.hidden = true
  let timer: ReturnType<typeof setTimeout> | undefined
  let coaching: ReturnType<typeof setTimeout> | undefined

  function coach(on: boolean): void {
    clearTimeout(coaching)
    coachPill.hidden = !on
    if (on) coaching = setTimeout(() => coach(false), COACH_MS)
  }

  function say(text: string): void {
    words.textContent = text
    element.classList.add('is-shown')
    fadeIn(element)
    clearTimeout(timer)
    timer = setTimeout(() => element.classList.remove('is-shown'), FEEDBACK_HOLD_MS)
  }

  return { element, coachPill, say, coach }
}
