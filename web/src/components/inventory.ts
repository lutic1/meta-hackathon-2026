import './inventory.css'
import type { PlayView, SessionState } from '../../types'
import { fadeIn, glowOnce } from '../fade.ts'
import { capitalized } from '../feedback.ts'
import { fill, strings } from '../strings.ts'
import { type UseOnSelection, useOnItem } from '../use-on.ts'
import { crop } from './crop.ts'

/** Each item is a 76 x 60 px crop (spec 1.8). */
const ITEM_WIDTH = 76
const ITEM_HEIGHT = 60
/** A new item's well lights once like the arrival glow: 300 ms in all, held 2 s with no animation under reduced motion. */
export const GLOW_MS = 150
export const GLOW_REDUCED_MS = 2000

export interface InventoryTray {
  element: HTMLElement
  /** Draws what `state.inventory` holds; the client never adds an item on its own. */
  render: (state: SessionState) => void
}

/**
 * "Your pack" (`{components.inventory}`, FR-11, UX-DR26; story mode, build spec 1.8): it stands on the floor left of
 * the photo, 22 px from its edge and 26 px up, its name over a row of 76 x 60 crops (each cut around its largest
 * polygon) and a caption: "Empty for now." before any riddle is solved, "Empty again." after, "Click an item to hold
 * it." while it holds something, "In hand. Click where it goes." while an item is held. It holds the Interactables
 * `state.inventory` lists, redrawn only when that list changes; an item collected after the first draw fades in and
 * its well glows once. Each item is a button named by its label and a `use_on` source (select-then-click, drag,
 * Escape); holding or putting one away says so in the feedback line through `say`: "{Label} in hand. Click where
 * they belong.", "You put the {label} away." or, on Escape, "Hands empty.".
 */
export function inventory(room: PlayView, selection: UseOnSelection, say: (line: string) => void): InventoryTray {
  const element = document.createElement('div')
  element.className = 'inventory'
  const name = document.createElement('span')
  name.id = 'inventory-name'
  name.className = 'inventory-name'
  name.textContent = strings.yourPack
  const slots = document.createElement('div')
  slots.className = 'inventory-slots'
  slots.setAttribute('role', 'group')
  slots.setAttribute('aria-labelledby', name.id)
  const caption = document.createElement('span')
  caption.className = 'inventory-caption'
  element.append(name, slots, caption)
  const interactables = new Map(room.interactables.map((interactable) => [interactable.id, interactable]))
  let drawn: string | undefined
  let buttons: HTMLButtonElement[] = []
  let latest: SessionState | undefined

  function describe(): void {
    if (buttons.length === 0) caption.textContent = (latest?.locks_open.length ?? 0) > 0 ? strings.packEmptyAgain : strings.packEmpty
    else caption.textContent = selection.selected() === null ? strings.packHold : strings.packInHand
  }

  function markSelected(item: string | null): void {
    for (const button of buttons) button.setAttribute('aria-pressed', String(button.dataset.item === item))
    describe()
  }
  /** The item in hand before the latest change, so putting it away can name it. */
  let holding: string | null = null
  selection.onChange((item, cause) => {
    const was = holding
    holding = item
    markSelected(item)
    const label = (id: string | null): string => interactables.get(id ?? '')?.label ?? ''
    if (cause === 'pack' && item !== null) say(fill(strings.inHandWhere, { Label: capitalized(label(item)) }))
    else if (cause === 'pack' && was !== null) say(fill(strings.putAway, { label: label(was) }))
    else if (cause === 'escape') say(strings.handsEmpty)
  })

  function render(state: SessionState): void {
    latest = state
    const held = state.inventory.flatMap((id) => interactables.get(id) ?? [])
    const key = held.map((interactable) => interactable.id).join(' ')
    if (key === drawn) return describe()
    const before = drawn === undefined ? undefined : new Set(drawn.split(' '))
    drawn = key
    if (held.length === 0) {
      const empty = document.createElement('span')
      empty.className = 'inventory-slot is-empty'
      empty.setAttribute('aria-hidden', 'true')
      buttons = []
      slots.replaceChildren(empty)
      return describe()
    }
    const arrived: HTMLElement[] = []
    buttons = held.map((interactable) => {
      const button = document.createElement('button')
      button.type = 'button'
      button.className = 'inventory-slot inventory-item'
      button.setAttribute('aria-label', capitalized(interactable.label))
      button.append(crop(room.id, interactable, ITEM_WIDTH, ITEM_HEIGHT))
      useOnItem(button, interactable, selection)
      if (before !== undefined && !before.has(interactable.id)) arrived.push(button)
      return button
    })
    slots.replaceChildren(...buttons)
    markSelected(selection.selected())
    const hold = matchMedia('(prefers-reduced-motion: reduce)').matches ? GLOW_REDUCED_MS : GLOW_MS
    for (const item of arrived) {
      fadeIn(item)
      glowOnce(item, 'is-glowing', hold)
    }
  }

  return { element, render }
}
