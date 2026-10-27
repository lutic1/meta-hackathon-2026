import './inventory.css'
import type { PlayView, SessionState } from '../../types'
import { fadeIn } from '../fade.ts'
import { strings } from '../strings.ts'
import { crop } from './crop.ts'

/** Three 64 px slots across the tray (UX-DR26). */
const ACROSS = 3
/** Each held item is a 56 px crop inside its 64 px slot. */
const ITEM_PX = 56

export interface InventoryTray {
  element: HTMLElement
  /** Draws what `state.inventory` holds; the client never adds an item on its own. */
  render: (state: SessionState) => void
}

function slot(): HTMLLIElement {
  const element = document.createElement('li')
  element.className = 'inventory-slot'
  const well = document.createElement('span')
  well.className = 'inventory-well'
  element.append(well)
  return element
}

/**
 * The Inventory (`{components.inventory}`, FR-11, UX-DR26): a `chrome-raised` tray of 64 px slots, three across,
 * holding the Interactables `state.inventory` lists for the whole Session, each a 56 px crop with its label in
 * `caption` type, then dashed empty slots to the end of the row. Holding nothing, it shows one dashed slot and
 * "Nothing in hand yet." It redraws only when the held list changes; an item collected after the first draw fades in
 * over 200 ms, in step with its Hotspot's glow fading out (FR-12).
 */
export function inventory(room: PlayView): InventoryTray {
  const element = document.createElement('ul')
  element.className = 'inventory'
  element.setAttribute('aria-label', strings.inventory)
  const interactables = new Map(room.interactables.map((interactable) => [interactable.id, interactable]))
  let drawn: string | undefined

  function render(state: SessionState): void {
    const held = state.inventory.flatMap((id) => interactables.get(id) ?? [])
    const key = held.map((interactable) => interactable.id).join(' ')
    if (key === drawn) return
    const before = drawn === undefined ? undefined : new Set(drawn.split(' '))
    drawn = key
    if (held.length === 0) {
      const empty = slot()
      empty.classList.add('is-empty')
      empty.setAttribute('aria-hidden', 'true')
      const line = document.createElement('li')
      line.className = 'inventory-nothing body-sm'
      line.textContent = strings.nothingInHand
      element.replaceChildren(empty, line)
      return
    }
    const arrived: HTMLElement[] = []
    const items = held.map((interactable) => {
      const item = slot()
      if (before !== undefined && !before.has(interactable.id)) arrived.push(item)
      item.firstElementChild?.append(crop(room.id, interactable, ITEM_PX))
      const caption = document.createElement('span')
      caption.className = 'inventory-caption caption'
      caption.textContent = interactable.label
      item.append(caption)
      return item
    })
    const free = Array.from({ length: (ACROSS - (held.length % ACROSS)) % ACROSS }, () => {
      const empty = slot()
      empty.classList.add('is-empty')
      empty.setAttribute('aria-hidden', 'true')
      return empty
    })
    element.replaceChildren(...items, ...free)
    for (const item of arrived) fadeIn(item)
  }

  return { element, render }
}
