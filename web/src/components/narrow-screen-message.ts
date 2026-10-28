import './narrow-screen-message.css'
import { announce } from '../live-region.ts'
import { strings } from '../strings.ts'
import { wizardPortrait } from '../wizards/portrait.ts'
import { secondaryButton } from './button.ts'

const HEADING_ID = 'narrow-screen-heading'

/**
 * `{components.narrow-screen-message}` (UX-DR60): the canvas with a centered plain `chrome-raised` card, at most 480 px
 * wide inside 16 px side gutters, holding the wordmark, the Guide's 96 px portrait (its placeholder until the painting
 * loads), the heading in `display-sm`, one `body-md` sentence and "Copy link for your laptop", the card's one control:
 * it copies this page's address with the clipboard and confirms under itself and in the live region, "Link copied.
 * The room will wait.", or, with no clipboard or a refused write, that the address bar still has it. Nothing on the
 * card leaves the page. Its stylesheet draws it only below 1024 px, where the shell's stylesheet hides `#app` instead
 * of tearing it down, so widening past 1024 px returns the app with its state intact.
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
  const portrait = wizardPortrait('guide', 96)
  portrait.classList.add('narrow-screen-portrait')
  const heading = document.createElement('h1')
  heading.id = HEADING_ID
  heading.className = 'narrow-screen-heading display-sm'
  heading.textContent = strings.narrowHeading
  const body = document.createElement('p')
  body.className = 'narrow-screen-sentence body-md'
  body.textContent = strings.narrowBody
  const copy = secondaryButton({ label: strings.copyLinkForLaptop, onActivate: () => void copyLink() })
  copy.classList.add('narrow-screen-copy')
  const status = document.createElement('p')
  status.className = 'narrow-screen-status body-sm'

  async function copyLink(): Promise<void> {
    let line: string = strings.linkCopied
    try {
      await navigator.clipboard.writeText(location.href)
    } catch {
      line = strings.linkNotCopied
    }
    status.textContent = line
    announce(line)
  }

  card.append(wordmark, portrait, heading, body, copy, status)
  element.append(card)
  return element
}
