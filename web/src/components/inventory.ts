import './inventory.css'
import type { PlayView, SessionState } from '../../types'
import { fadeIn, glowOnce } from '../fade.ts'
import { strings } from '../strings.ts'
import { type UseOnSelection, useOnItem } from '../use-on.ts'
import { crop } from './crop.ts'
import { GLOW_MS, GLOW_REDUCED_MS } from './hint-area.ts'

/** Three 64 px slots across the tray (UX-DR26). */
const ACROSS = 3
/** Each held item is a 56 px crop inside its 64 px slot. */
const ITEM_PX = 56

export interface InventoryTray {
  element: HTMLElement
  /** Draws what `state.inventory` holds; the client never adds an item on its own. */
  render: (state: SessionState) => void
}

function slot(well: HTMLElement = document.createElement('span')): HTMLLIElement {
  const element = document.createElement('li')
  element.className = 'inventory-slot'
  well.classList.add('inventory-well')
  element.append(well)
  return element
}

/**
 * The Inventory (`{components.inventory}`, FR-11, UX-DR26): a `chrome-raised` tray of 64 px slots, three across,
 * holding the Interactables `state.inventory` lists for the whole Session, each a 56 px crop with its label in
 * `caption` type, then dashed empty slots to the end of the row. Holding nothing, it shows one dashed slot and
 * "Nothing in hand yet." It redraws only when the held list changes; an item collected after the first draw fades in
 * over 200 ms, in step with its Hotspot's glow fading out (FR-12), and its well glows once with the lamp glow (in and
 * out by `--motion-hover`; held 2 s with no animation under reduced motion), so the pickup is seen where it lands. Each item's well is a button named by its label and
 * a `use_on` source (UX-DR26): pressed, with the 2 px lamp ring, while `selection` holds it.
 */
export function inventory(room: PlayView, selection: UseOnSelection): InventoryTray {
  const element = document.createElement('ul')
  element.className = 'inventory'
  element.setAttribute('aria-label', strings.inventory)
  element.tabIndex = 0 // its place in the Play screen's Tab order, after the Thumbnail strip (UX-DR71)
  const interactables = new Map(room.interactables.map((interactable) => [interactable.id, interactable]))
  let drawn: string | undefined
  let buttons: HTMLButtonElement[] = []

  function markSelected(item: string | null): void {
    for (const button of buttons) button.setAttribute('aria-pressed', String(button.dataset.item === item))
  }
  selection.onChange(markSelected)

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
      buttons = []
      element.replaceChildren(empty, line)
      return
    }
    const arrived: HTMLElement[] = []
    buttons = []
    const items = held.map((interactable) => {
      const button = document.createElement('button')
      button.type = 'button'
      button.className = 'inventory-item'
      button.setAttribute('aria-label', interactable.label)
      button.append(crop(room.id, interactable, ITEM_PX))
      useOnItem(button, interactable, selection)
      buttons.push(button)
      const item = slot(button)
      if (before !== undefined && !before.has(interactable.id)) arrived.push(item)
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
    markSelected(selection.selected())
    const hold = matchMedia('(prefers-reduced-motion: reduce)').matches ? GLOW_REDUCED_MS : GLOW_MS
    for (const item of arrived) {
      fadeIn(item)
      glowOnce(item, 'is-glowing', hold)
    }
  }

  return { element, render }
}
