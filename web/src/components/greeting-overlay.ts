import './button.css'
import './greeting-overlay.css'
import { fadeIn } from '../fade.ts'
import { strings } from '../strings.ts'
import { speakerPrefix, wizardPortrait } from '../wizards/portrait.ts'

export interface GreetingOverlay {
  /** The scrim, holding the card; it covers whatever positioned box it is appended to. */
  element: HTMLElement
  /** "Begin", the card's only control. */
  begin: HTMLButtonElement
  /** Fades the card in over 300 ms (instant under reduced motion); call once the element is in the page. */
  show: () => void
}

const HEADING_ID = 'greeting-overlay-heading'

function paragraph(className: string, ...children: (Node | string)[]): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = className
  element.append(...children)
  return element
}

/**
 * `{components.greeting-overlay}` (UX-DR45) for the First-room welcome: the scrim and, centered on it, the 560 px
 * parchment card. The Guide's introduction at the top (the 96 px portrait beside the heading "The Guide" in
 * `display-sm` with `role` under it in `body-sm` `ink-muted`), then `line` exactly as served in `wizard-line-lg`, the
 * Guide's voice line in `wizard-line`, and "Begin" (primary) left-aligned under it. The dialog is labelled by its
 * heading only, with no description, so nothing is read twice; each in-character line starts with the visually
 * hidden speaker prefix.
 */
export function greetingOverlay(role: string, line: string): GreetingOverlay {
  const element = document.createElement('div')
  element.className = 'greeting-scrim'
  const card = document.createElement('section')
  card.className = 'greeting-overlay'
  card.setAttribute('role', 'dialog')
  card.setAttribute('aria-modal', 'true')
  card.setAttribute('aria-labelledby', HEADING_ID)

  const intro = document.createElement('div')
  intro.className = 'greeting-intro'
  const name = document.createElement('div')
  const heading = document.createElement('h2')
  heading.id = HEADING_ID
  heading.className = 'greeting-heading display-sm'
  heading.textContent = strings.guide
  name.append(heading, paragraph('greeting-role body-sm', role))
  intro.append(wizardPortrait('guide', 96), name)

  const begin = document.createElement('button')
  begin.type = 'button'
  begin.className = 'button-primary'
  begin.textContent = strings.begin
  const actions = document.createElement('div')
  actions.className = 'greeting-actions'
  actions.append(begin)

  card.append(
    intro,
    paragraph('greeting-line wizard-line-lg', speakerPrefix('guide'), line),
    paragraph('greeting-voice wizard-line', speakerPrefix('guide'), strings.guideVoice),
    actions,
  )
  element.append(card)

  return { element, begin, show: () => fadeIn(card) }
}
