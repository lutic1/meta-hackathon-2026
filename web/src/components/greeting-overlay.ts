import './button.css'
import './greeting-overlay.css'
import { fadeIn } from '../fade.ts'
import { strings } from '../strings.ts'
import { speakerPrefix, wizardPortrait } from '../wizards/portrait.ts'

export interface GreetingOverlay {
  /** The scrim, holding the card; it covers whatever positioned box it is appended to. */
  element: HTMLElement
  /** The heading "The Guide", which holds focus while the line is being phrased. */
  heading: HTMLHeadingElement
  /** "Begin", the card's only control; in the card only once the line has arrived. */
  begin: HTMLButtonElement
  /** Fades the card in over 300 ms (instant under reduced motion); call once the element is in the page. */
  show: () => void
  /** Puts `line` where the thinking label was and "Begin" under the voice line; the thinking state ends. */
  arrive: (line: string) => void
}

const HEADING_ID = 'greeting-overlay-heading'

function paragraph(className: string, ...children: (Node | string)[]): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = className
  element.append(...children)
  return element
}

/** The First-room welcome's three-step how-to-play, numbered, in `body-md` `ink`. */
function steps(): HTMLOListElement {
  const list = document.createElement('ol')
  list.className = 'greeting-steps body-md'
  for (const step of [strings.howToPlay1, strings.howToPlay2, strings.howToPlay3]) {
    const item = document.createElement('li')
    item.textContent = step
    list.append(item)
  }
  return list
}

/**
 * `{components.greeting-overlay}` (UX-DR45) for the Greeting and the First-room welcome: the scrim and, centered on
 * it, the 560 px parchment card. The Guide's introduction at the top (the 96 px portrait beside the heading "The
 * Guide" in `display-sm` with `role` under it in `body-sm` `ink-muted`), then the Guide's voice line in
 * `wizard-line`; with `howToPlay` (the First-room welcome), the three-step how-to-play sits between the line and the
 * voice line. Until `arrive` brings the opening line, the card shows the Guide's static thinking state: the `lamp`
 * ring on the portrait and "thinking on this Mac" in `pending-ink` where the line will go, with no "Begin". `arrive`
 * puts the line there exactly as served in `wizard-line-lg`, the same whatever worded it, and "Begin" (primary)
 * left-aligned under the voice line; a line served at once is brought before the card is first drawn, so it never
 * shows the thinking state. The dialog is labelled by its heading only, with no description, so nothing is read
 * twice; each in-character line starts with the visually hidden speaker prefix.
 */
export function greetingOverlay(role: string, howToPlay: boolean): GreetingOverlay {
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
  heading.tabIndex = -1 // focusable by script only, while there is no "Begin" yet
  heading.textContent = strings.guide
  name.append(heading, paragraph('greeting-role body-sm', role))
  const portrait = wizardPortrait('guide', 96)
  intro.append(portrait, name)

  const begin = document.createElement('button')
  begin.type = 'button'
  begin.className = 'button-primary'
  begin.textContent = strings.begin
  const actions = document.createElement('div')
  actions.className = 'greeting-actions'
  actions.append(begin)

  const thinking = paragraph('greeting-thinking label', strings.thinkingOnThisMac)
  const voice = paragraph('greeting-voice wizard-line', speakerPrefix('guide'), strings.guideVoice)

  portrait.classList.add('is-thinking')
  card.append(intro, thinking, ...(howToPlay ? [steps()] : []), voice)
  element.append(card)

  function arrive(line: string): void {
    portrait.classList.remove('is-thinking')
    thinking.replaceWith(paragraph('greeting-line wizard-line-lg', speakerPrefix('guide'), line))
    card.append(actions)
  }

  return { element, heading, begin, show: () => fadeIn(card), arrive }
}
