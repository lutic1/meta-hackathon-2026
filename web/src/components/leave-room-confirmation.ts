import './button.css'
import './leave-room-confirmation.css'
import { fadeIn } from '../fade.ts'
import { strings } from '../strings.ts'

export interface LeaveRoomConfirmation {
  /** The scrim, holding the card; it covers whatever positioned box it is appended to. */
  element: HTMLElement
  /** The primary button that stays ("Keep playing"), focused when the card opens. */
  stay: HTMLButtonElement
  /** The secondary button that confirms ("Leave room"). */
  leave: HTMLButtonElement
  /** Fades the card in over 300 ms (instant under reduced motion); call once the element is in the page. */
  show: () => void
}

/** The card's words: its question, its one sentence, the button that stays and the one that leaves. */
export interface ConfirmationCopy {
  question: string
  sentence: string
  stay: string
  leave: string
}

const LEAVE_ROOM: ConfirmationCopy = {
  question: strings.leaveRoomQuestion,
  sentence: strings.leaveRoomBody,
  stay: strings.keepPlaying,
  leave: strings.leaveRoom,
}

const HEADING_ID = 'leave-room-heading'
const SENTENCE_ID = 'leave-room-sentence'

function button(className: string, label: string): HTMLButtonElement {
  const element = document.createElement('button')
  element.type = 'button'
  element.className = className
  element.textContent = label
  return element
}

/**
 * `{components.leave-room-confirmation}` (UX-DR46): the scrim and, centered on it, the plain 480 px `chrome-raised`
 * card, never parchment: the question as its `display-sm` heading, the one `body-md` sentence, then "Keep playing"
 * (primary) and "Leave room" (secondary), left-aligned. The Build progress screen's "Back to the start" asks with the
 * same card in its own words (`copy`).
 */
export function leaveRoomConfirmation(copy: ConfirmationCopy = LEAVE_ROOM): LeaveRoomConfirmation {
  const element = document.createElement('div')
  element.className = 'leave-room-scrim'
  const card = document.createElement('section')
  card.className = 'leave-room-confirmation'
  card.setAttribute('role', 'dialog')
  card.setAttribute('aria-modal', 'true')
  card.setAttribute('aria-labelledby', HEADING_ID)
  card.setAttribute('aria-describedby', SENTENCE_ID)
  const heading = document.createElement('h2')
  heading.id = HEADING_ID
  heading.className = 'leave-room-heading display-sm'
  heading.textContent = copy.question
  const sentence = document.createElement('p')
  sentence.id = SENTENCE_ID
  sentence.className = 'leave-room-sentence body-md'
  sentence.textContent = copy.sentence
  const stay = button('button-primary', copy.stay)
  const leave = button('button-secondary', copy.leave)
  const actions = document.createElement('div')
  actions.className = 'leave-room-actions'
  actions.append(stay, leave)
  card.append(heading, sentence, actions)
  element.append(card)
  return { element, stay, leave, show: () => fadeIn(card) }
}
