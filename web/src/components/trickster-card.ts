import type { PlayView, TricksterCard } from '../../types'
import { fill, strings } from '../strings.ts'

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
