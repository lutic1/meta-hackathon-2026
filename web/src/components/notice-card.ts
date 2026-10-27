import './button.css'
import './notice-card.css'
import { primaryButton } from './button.ts'

export interface NoticeCardOptions {
  heading: string
  /** One plain sentence. */
  sentence: string
  /** The card's one action, a primary button. */
  action: { label: string; onActivate: () => void }
}

export interface NoticeCard {
  element: HTMLElement
  /** Takes focus when the card shows. */
  heading: HTMLHeadingElement
}

const HEADING_ID = 'notice-card-heading'

/**
 * The page body's centered 480 px `chrome-raised` card (`{components.leave-room-confirmation}` with no scrim, as the
 * Deleted Judge room notice and the unknown-room card use it, UX-DR47): heading in `display-sm`, one plain `body-md`
 * sentence, then one primary button, left-aligned.
 */
export function noticeCard({ heading: title, sentence, action }: NoticeCardOptions): NoticeCard {
  const element = document.createElement('section')
  element.className = 'notice-card'
  element.setAttribute('aria-labelledby', HEADING_ID)
  const heading = document.createElement('h1')
  heading.id = HEADING_ID
  heading.className = 'notice-card-heading display-sm'
  heading.tabIndex = -1
  heading.textContent = title
  const body = document.createElement('p')
  body.className = 'notice-card-sentence body-md'
  body.textContent = sentence
  const actions = document.createElement('div')
  actions.className = 'notice-card-actions'
  actions.append(
    primaryButton({
      label: action.label,
      pendingLabel: action.label,
      onActivate: async () => action.onActivate(),
    }),
  )
  element.append(heading, body, actions)
  return { element, heading }
}
