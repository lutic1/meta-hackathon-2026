import './evidence-card.css'
import type { Evidence, PlayInteractable } from '../../types'
import { fill, strings } from '../strings.ts'
import { crop } from './crop.ts'

/** The Evidence card's thumbnail crop (`{components.evidence-card.thumb}`). */
const THUMB_PX = 64

/**
 * An Evidence card (`{components.evidence-card}`, UX-DR39): an inset `parchment-shade` row. While its Puzzle is
 * unsolved it is the Riddler's note alone, the read attribute quoted in `wizard-line` ("The Riddler's note: “on
 * sofa”"), with no label and no crop, so a find lock's card never names its own answer; once `solved`, the whole card,
 * a 64 px crop of the Interactable cut from its photo beside its label and the attribute, is the reward. Real and
 * Decoy cards are drawn alike, and a new card gets no highlight, badge, animation or announcement.
 */
export function evidenceCard(
  roomId: string,
  interactable: PlayInteractable,
  evidence: Evidence,
  solved: boolean,
): HTMLLIElement {
  const element = document.createElement('li')
  if (!solved) {
    element.className = 'evidence-card evidence-card-note'
    const note = document.createElement('p')
    note.className = 'evidence-card-note-text wizard-line'
    note.textContent = fill(strings.riddlerNote, { attribute: evidence.visible_attribute })
    element.append(note)
    return element
  }
  element.className = 'evidence-card'
  const text = document.createElement('div')
  const label = document.createElement('p')
  label.className = 'evidence-card-label label'
  label.textContent = interactable.label
  const attribute = document.createElement('p')
  attribute.className = 'evidence-card-attribute body-sm'
  attribute.textContent = evidence.visible_attribute
  text.append(label, attribute)
  element.append(crop(roomId, interactable, THUMB_PX), text)
  return element
}
