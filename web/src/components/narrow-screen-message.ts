import './narrow-screen-message.css'
import { strings } from '../strings.ts'

const HEADING_ID = 'narrow-screen-heading'

/**
 * `{components.narrow-screen-message}` (UX-DR60): the canvas with a centered plain `chrome-raised` card, at most 480 px
 * wide inside 16 px side gutters, holding the wordmark, the heading in `display-sm` and one `body-md` sentence. Its
 * stylesheet draws it only below 1024 px, where the shell's stylesheet hides `#app` instead of tearing it down, so
 * widening past 1024 px returns the app with its state intact. A single state with no controls.
 */
export function narrowScreenMessage(): HTMLElement {
  const element = document.createElement('div')
  element.className = 'narrow-screen'
  const card = document.createElement('section')
  card.className = 'narrow-screen-message'
  card.setAttribute('aria-labelledby', HEADING_ID)
  const wordmark = document.createElement('p')
  wordmark.className = 'narrow-screen-wordmark display-sm'
  wordmark.textContent = strings.wordmark
  const heading = document.createElement('h1')
  heading.id = HEADING_ID
  heading.className = 'narrow-screen-heading display-sm'
  heading.textContent = strings.narrowHeading
  const body = document.createElement('p')
  body.className = 'narrow-screen-sentence body-md'
  body.textContent = strings.narrowBody
  card.append(wordmark, heading, body)
  element.append(card)
  return element
}
