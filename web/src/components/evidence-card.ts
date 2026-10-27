import './evidence-card.css'
import type { Evidence, PlayInteractable } from '../../types'
import { crop } from './crop.ts'

/** The Evidence card's thumbnail crop (`{components.evidence-card.thumb}`). */
const THUMB_PX = 64

/**
 * An Evidence card (`{components.evidence-card}`, UX-DR39): an inset `parchment-shade` row with a 64 px crop of the
 * Interactable cut from its photo, its label and the read attribute, which says where to look. One state only: real
 * and Decoy cards are drawn alike, and a new card gets no highlight, badge, animation or announcement.
 */
export function evidenceCard(roomId: string, interactable: PlayInteractable, evidence: Evidence): HTMLLIElement {
  const element = document.createElement('li')
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
