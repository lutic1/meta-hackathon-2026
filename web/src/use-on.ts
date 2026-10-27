import './use-on.css'
import type { PlayInteractable } from '../types'
import { secondaryButton } from './components/button.ts'
import { fill, strings } from './strings.ts'

/** The drag image is a 64 px copy of the item's crop (UX-DR26). */
const DRAG_PX = 64
/** Room around the drag image so its `paper` shadow is drawn with it. */
const DRAG_MARGIN_PX = 16

/** The item a drag from the Inventory carries; one drag at a time in the page. */
let dragged: string | null = null

/**
 * The Inventory item a `use_on` is being given with (UX-DR36, UX-DR37): the one selected for select-then-click, and
 * the one being dragged. Client state only; the lock state stays the server's.
 */
export interface UseOnSelection {
  selected: () => string | null
  /** Selects an item, or clears the selection with null; every listener hears the change. */
  select: (item: string | null) => void
  dragging: () => string | null
  onChange: (listener: (item: string | null) => void) => void
  /** Removes the Escape listener. */
  dispose: () => void
}

/** A selection with nothing selected; Escape anywhere on the page clears it once something is. */
export function useOnSelection(): UseOnSelection {
  let selected: string | null = null
  const listeners: ((item: string | null) => void)[] = []
  function select(item: string | null): void {
    if (item === selected) return
    selected = item
    for (const listener of listeners) listener(item)
  }
  function escape(event: KeyboardEvent): void {
    if (event.key === 'Escape' && selected !== null) select(null)
  }
  document.addEventListener('keydown', escape)
  return {
    selected: () => selected,
    select,
    dragging: () => dragged,
    onChange: (listener) => {
      listeners.push(listener)
    },
    dispose: () => document.removeEventListener('keydown', escape),
  }
}

/** The Inventory item button for `item`, so focus can return to it. */
function itemButton(item: string): HTMLElement | null {
  return document.querySelector<HTMLElement>(`.inventory-item[data-item="${item}"]`)
}

/** A 64 px copy of the item's drawn crop on a `paper` shadow, placed off screen for `setDragImage`. */
function dragImage(source: HTMLCanvasElement | null): HTMLElement {
  const wrap = document.createElement('div')
  wrap.className = 'use-on-drag-image'
  const canvas = document.createElement('canvas')
  canvas.width = canvas.height = Math.round(DRAG_PX * window.devicePixelRatio)
  canvas.style.width = canvas.style.height = `${DRAG_PX}px`
  if (source !== null) canvas.getContext('2d')?.drawImage(source, 0, 0, canvas.width, canvas.height)
  wrap.append(canvas)
  document.body.append(wrap)
  return wrap
}

/**
 * Makes `button`, an Inventory item, a `use_on` source: click or Enter selects it for select-then-click and a second
 * activation clears the selection (the Inventory marks the selected item pressed, with its 2 px lamp ring). Dragged, it
 * stays in place at 60% while a 64 px drag image with the `paper` shadow follows the pointer.
 */
export function useOnItem(button: HTMLButtonElement, interactable: PlayInteractable, selection: UseOnSelection): void {
  button.dataset.item = interactable.id
  button.draggable = true
  button.addEventListener('click', () => {
    selection.select(selection.selected() === interactable.id ? null : interactable.id)
  })
  button.addEventListener('dragstart', (event) => {
    dragged = interactable.id
    button.classList.add('is-dragging')
    if (event.dataTransfer === null) return
    event.dataTransfer.effectAllowed = 'move'
    const image = dragImage(button.querySelector('canvas'))
    event.dataTransfer.setDragImage(image, DRAG_MARGIN_PX + DRAG_PX / 2, DRAG_MARGIN_PX + DRAG_PX / 2)
    setTimeout(() => image.remove()) // the browser has taken its picture once dragstart returns
  })
  button.addEventListener('dragend', () => {
    dragged = null
    button.classList.remove('is-dragging')
  })
}

/**
 * `{components.use-on-selected}` (UX-DR37): the parchment chip pinned to the top-left of the Scene frame while an item
 * is selected, "Using {item label}" with "Cancel". It fades in and out (200 ms) and is inert while hidden; Cancel
 * clears the selection, and focus inside the chip then returns to the item.
 */
export function useOnChip(labels: ReadonlyMap<string, string>, selection: UseOnSelection): HTMLElement {
  const element = document.createElement('div')
  element.className = 'use-on-chip'
  element.inert = true
  const text = document.createElement('span')
  text.className = 'label'
  const cancel = secondaryButton({ label: strings.cancel, onActivate: () => selection.select(null), onParchment: true })
  element.append(text, cancel)
  let shown: string | null = null
  selection.onChange((item) => {
    const label = item === null ? undefined : labels.get(item)
    if (item !== null && label !== undefined) text.textContent = fill(strings.usingItem, { 'item label': label })
    const focused = element.contains(document.activeElement)
    element.classList.toggle('is-shown', item !== null)
    element.inert = item === null
    if (item === null && focused && shown !== null) itemButton(shown)?.focus()
    shown = item
  })
  return element
}
