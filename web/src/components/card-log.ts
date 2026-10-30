import './card-log.css'
import type { PlayView, SessionState, TricksterCard } from '../../types'
import { fadeIn } from '../fade.ts'
import { strings } from '../strings.ts'
import { speakerPrefix, wizardPortrait } from '../wizards/portrait.ts'
import { formatElapsed } from './timer.ts'
import { cardText } from './trickster-card.ts'
import type { TriggersList } from './triggers-panel.ts'

export interface CardLogDialog {
  /** The scrim, holding the dialog; it covers whatever positioned box it is appended to. */
  element: HTMLElement
  /** The dialog itself, the box that scrolls. */
  dialog: HTMLElement
  /** The close control, focused when the dialog opens. */
  close: HTMLButtonElement
  /** Adds one row per Card, in the order given, after the rows already listed. */
  add: (cards: readonly TricksterCard[]) => void
  /** Draws "How hints work" from `state`: its plain line and one row per hint. */
  hints: (state: SessionState) => void
  /** Fades the dialog in over 300 ms (instant under reduced motion); call once the element is in the page. */
  show: () => void
}

function paragraph(className: string, ...content: (Node | string)[]): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = className
  element.append(...content)
  return element
}

/**
 * One Card log row, read from the `TricksterCard` fields alone: the Trickster portrait (24 px), the sentence in
 * `wizard-line`, the outcome label, a rejected Card's "Proposed: …" line and reason, and the card's `t_ms` as the
 * session time in `mono-sm`. The Trickster's introduction is never repeated here.
 */
function row(room: PlayView, card: TricksterCard): HTMLLIElement {
  const text = cardText(room, card)
  const element = document.createElement('li')
  element.className = `card-log-row is-${text.outcome}`
  const words = document.createElement('div')
  words.className = 'card-log-words'
  words.append(
    paragraph('card-log-sentence wizard-line', speakerPrefix('trickster'), text.sentence),
    paragraph('card-log-outcome label', text.label),
  )
  if (text.refusal !== null) {
    words.append(
      paragraph('card-log-refusal body-sm', text.refusal.proposed),
      paragraph('card-log-refusal body-sm', text.refusal.reason),
    )
  }
  words.append(paragraph('card-log-time mono-sm', formatElapsed(card.t_ms)))
  element.append(wizardPortrait('trickster', 24), words)
  return element
}

/**
 * `{components.card-log}` (UX-DR43): the scrim and on it the 360 px `chrome` modal dialog, at most 480 px high and
 * scrolling, named "Card log": the close control, then one row per Card, oldest first, or with no Cards the one
 * `text-muted` line "No cards yet in this play-through."; then "How hints work" (story mode: it left the play screen
 * with the hint button), `hints`: its one plain line and the hint history.
 */
export function cardLogDialog(room: PlayView, hints: TriggersList): CardLogDialog {
  const element = document.createElement('div')
  element.className = 'card-log-scrim'
  const dialog = document.createElement('section')
  dialog.className = 'card-log'
  dialog.setAttribute('role', 'dialog')
  dialog.setAttribute('aria-modal', 'true')
  dialog.setAttribute('aria-label', strings.cardLog)
  dialog.tabIndex = -1 // a click on a row keeps focus in the dialog
  const head = document.createElement('div')
  head.className = 'card-log-head'
  const close = document.createElement('button')
  close.type = 'button'
  close.className = 'card-log-close'
  close.setAttribute('aria-label', strings.closeCardLog)
  close.textContent = '×'
  head.append(close)
  const list = document.createElement('ol')
  list.className = 'card-log-list'
  list.hidden = true
  const empty = paragraph('card-log-empty body-sm', strings.cardLogEmpty)
  const hintsHeading = document.createElement('h3')
  hintsHeading.className = 'card-log-hints label'
  hintsHeading.textContent = strings.howHintsWork
  dialog.append(head, list, empty, hintsHeading, hints.element)
  element.append(dialog)

  function add(cards: readonly TricksterCard[]): void {
    list.append(...cards.map((card) => row(room, card)))
    list.hidden = list.children.length === 0
    empty.hidden = !list.hidden
  }

  return { element, dialog, close, add, hints: hints.render, show: () => fadeIn(dialog) }
}
