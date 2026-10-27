import './trickster-card.css'
import type { PlayView, TricksterCard } from '../../types'
import { fill, strings } from '../strings.ts'
import { speakerPrefix, wizardPortrait } from '../wizards/portrait.ts'

type EditType = NonNullable<TricksterCard['edit_type']>

/** Each accepted edit type's sentence: a literal effect clause, then one Trickster flourish (EXPERIENCE.md Cards). */
const SENTENCES: Record<EditType, string> = {
  decoy: strings.cardDecoy,
  merge: strings.cardMerge,
  loosen: strings.cardLoosen,
  shortcut: strings.cardShortcut,
}

/** The type as a Card label names it. */
const TYPE_NAMES: Record<EditType, string> = {
  decoy: strings.decoy,
  merge: strings.merge,
  loosen: strings.loosen,
  shortcut: strings.shortcut,
}

/** A rejected proposal's structural summary: Puzzle numbers only, never content. */
const SUMMARIES: Record<EditType, string> = {
  decoy: strings.proposedDecoy,
  merge: strings.proposedMerge,
  loosen: strings.proposedLoosen,
  shortcut: strings.proposedShortcut,
}

/** What one Card says, read from the `TricksterCard` projection alone (AD-3). */
export interface CardText {
  outcome: 'accepted' | 'rejected' | 'skipped'
  sentence: string
  label: string
  /** A rejected Card's two plain lines: "Proposed: …" and "That change was refused. {fixed message}". */
  refusal: { proposed: string; reason: string } | null
}

/**
 * The words of `card`: a skipped Card (`reason` `provider_unavailable`, no `edit_type`) is the same for a provider
 * error and the Spend cap; an accepted one is its type's sentence and "Validator passed · {type} · Puzzle {n}"; a
 * rejected one is "Validator refused · {type} · Puzzle {n}" with its structural "Proposed:" line and its `message`.
 * n and m are the fixed order numbers of `puzzle_id` and `related_puzzle_id` in the Room. A Decoy names only the
 * Puzzle whose evidence grew; the projection carries nothing that could name the card. The `reason` (a rule number)
 * is never shown.
 */
export function cardText(room: PlayView, card: TricksterCard): CardText {
  const type = card.edit_type
  if (type === null || card.reason === 'provider_unavailable') {
    return { outcome: 'skipped', sentence: strings.cardSkipped, label: strings.skipped, refusal: null }
  }
  const number = (id: string | null): number => room.puzzles.findIndex((puzzle) => puzzle.id === id) + 1
  const n = number(card.puzzle_id)
  if (card.accepted) {
    return { outcome: 'accepted', sentence: SENTENCES[type], label: fill(strings.validatorPassed, { type: TYPE_NAMES[type], n }), refusal: null }
  }
  return {
    outcome: 'rejected',
    sentence: strings.cardRejected,
    label: fill(strings.validatorRefused, { type: TYPE_NAMES[type], n }),
    refusal: {
      proposed: fill(strings.proposed, { summary: fill(SUMMARIES[type], { n, m: number(card.related_puzzle_id) }) }),
      reason: fill(strings.changeRefused, { message: card.message ?? '' }),
    },
  }
}

/**
 * The Card's one live-region line: "The Trickster: {sentence} {outcome label}.", or on the first Card of the Session
 * "The Trickster. {role line} {voice line} {sentence} {outcome label}."; a rejected Card appends its "Proposed:" line
 * and its reason.
 */
export function cardAnnouncement(text: CardText, first: boolean): string {
  const line = fill(first ? strings.firstCardAnnouncement : strings.cardAnnouncement, {
    'role line': strings.tricksterRole,
    'voice line': strings.tricksterVoice,
    sentence: text.sentence,
    'outcome label': text.label,
  })
  return text.refusal === null ? line : `${line} ${text.refusal.proposed}. ${text.refusal.reason}`
}

function paragraph(className: string, ...content: (Node | string)[]): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = className
  element.append(...content)
  return element
}

/**
 * A Trickster card (`{components.trickster-card-accepted}`, `-rejected` or `-skipped`; UX-DR40 to UX-DR42): the
 * Trickster portrait (48 px) beside the sentence in `wizard-line`, then the outcome label, a rejected Card's two plain
 * `body-sm` lines, and the dismiss control "Dismiss card" (32 px hit area). Accepted and rejected Cards are parchment
 * with a 4 px `success-ink` or `wrong-ink` left edge; a skipped one drops off the paper onto `chrome-raised` with a
 * dashed `hairline` edge and its portrait at 60% opacity. The outcome is always named in words, never by the edge
 * alone. `first` (the Session's first Card, whatever its outcome) puts the Trickster's introduction above the
 * sentence: "The Trickster", its role line and its voice line. The Card is focusable from script only, so dismissing
 * the one above it can move focus here.
 */
export function tricksterCard(text: CardText, first: boolean, onDismiss: () => void): HTMLElement {
  const element = document.createElement('article')
  element.className = `trickster-card is-${text.outcome}`
  element.tabIndex = -1
  const words = document.createElement('div')
  words.className = 'trickster-card-words'
  if (first) {
    words.append(
      paragraph('trickster-card-name label', strings.trickster),
      paragraph('trickster-card-role body-sm', strings.tricksterRole),
      paragraph('trickster-card-voice wizard-line', speakerPrefix('trickster'), strings.tricksterVoice),
      paragraph('trickster-card-sentence wizard-line', text.sentence),
    )
  } else {
    words.append(paragraph('trickster-card-sentence wizard-line', speakerPrefix('trickster'), text.sentence))
  }
  words.append(paragraph('trickster-card-outcome label', text.label))
  if (text.refusal !== null) {
    words.append(
      paragraph('trickster-card-refusal body-sm', text.refusal.proposed),
      paragraph('trickster-card-refusal body-sm', text.refusal.reason),
    )
  }
  const dismiss = document.createElement('button')
  dismiss.type = 'button'
  dismiss.className = 'trickster-card-dismiss'
  dismiss.setAttribute('aria-label', strings.dismissCard)
  dismiss.textContent = '×'
  dismiss.addEventListener('click', onDismiss)
  element.append(wizardPortrait('trickster', 48), words, dismiss)
  return element
}
