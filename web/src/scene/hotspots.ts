import type { PlayInteractable } from '../../types'
import { glowOnce } from '../fade.ts'
import { fill, strings } from '../strings.ts'
import { hotspotPath, readingOrder, type Size, topLeft } from './geometry.ts'

const SVG = 'http://www.w3.org/2000/svg'

/** DESIGN.md `{components.hotspot-label-chip}`: anchored 8 px above the polygon's top edge. */
export const CHIP_OFFSET_PX = 8
/** UX-DR24: after a non-target click the label chip fades after 2 s, or sooner on pointer leave. */
export const CHIP_MS = 2000
/** DESIGN.md `{components.hotspot}` `labelDwell`: the pointer rests this long on a Hotspot before its label shows. */
export const DWELL_MS = 400

/**
 * What ends a label chip: a `click` chip after 2 s or on pointer leave (or on blur, when keyboard focus showed it), a
 * `dwell` chip when the pointer leaves, a `pending` chip only when its reply releases it.
 */
type ChipHold = 'click' | 'dwell' | 'pending'

export interface HotspotHandlers {
  /** A click inside any of the Hotspot's polygons, or Enter on it. */
  onActivate: (interactable: PlayInteractable) => void
  /** The pointer reached the Hotspot: its hover reveal shows. */
  onPointerEnter: () => void
  /** Whether an Inventory item is being dragged, so the Hotspot takes the drop. */
  canDrop: () => boolean
  /** An Inventory item dropped on the Hotspot. */
  onDrop: (interactable: PlayInteractable) => void
}

export interface HotspotLayer {
  /** The overlay over the photo: the Hotspots' SVG and the label chip. */
  elements: [SVGSVGElement, HTMLElement]
  /**
   * Shows the Interactable's label on the chip after a click: until 2 s pass or the pointer leaves its Hotspot, or
   * for as long as its Hotspot keeps keyboard focus. "{label} · in hand" for an Interactable the Inventory holds.
   */
  showLabel: (interactable: PlayInteractable) => void
  /** Marks the Hotspots of the Interactables `inventory` holds: a collected one's glow fades out and stays out. */
  setCollected: (inventory: readonly string[]) => void
  /**
   * Shows the Interactable's label on the chip with the "Checking" chip beside it, held (no dwell, timeout, pointer
   * leave or blur replaces it) until the returned function clears it: a `click` or `use_on` waiting for its reply.
   */
  showPending: (interactable: PlayInteractable) => () => void
  /** The unlock moment: the Interactable's Hotspot blooms once, its class held `hold` ms between the two fades. */
  bloom: (interactableId: string, hold: number) => void
}

/** A drag over the Hotspot: while it carries an Inventory item, the drop is allowed and the hover reveal shows. */
function dragOver(event: DragEvent, hotspot: SVGGElement, handlers: HotspotHandlers): void {
  if (!handlers.canDrop()) return
  event.preventDefault()
  if (event.dataTransfer !== null) event.dataTransfer.dropEffect = 'move'
  hotspot.classList.add('is-drop-target')
}

function path(className: string, d: string): SVGPathElement {
  const element = document.createElementNS(SVG, 'path')
  element.setAttribute('class', className)
  element.setAttribute('d', d)
  return element
}

/**
 * The Hotspots of one photo (`{components.hotspot}`, UX-DR23): one per Interactable on it, the union of its
 * `polygons` in the photo's own pixel space (the SVG `viewBox`), so the browser scales them to the rendered size.
 * Each is a focusable button named by the Interactable label whose id is the Interactable id, in Tab order by
 * polygon centroid from top to bottom, then left to right (UX-DR23); only its hit path takes the pointer, so a click
 * outside every polygon reaches no Hotspot. Invisible at rest; the reveal (outline, halo, glow fill and lamp shadow)
 * shows on hover, with the label chip once the pointer has dwelt 400 ms and until it leaves, and keyboard focus
 * traces the focus ring along it with the label chip shown at once, for as long as it keeps focus (UX-DR69). A
 * collected `find` target stays in the Scene, still a Hotspot, but its glow fill fades out over 200 ms and no longer
 * shows (FR-12). An Inventory item dragged over a Hotspot shows the same reveal as hover, and dropped there it is
 * handed to `onDrop`; a drop anywhere else reaches no Hotspot (UX-DR36). `bloom` plays the unlock moment on a
 * solved target: its bloom path, the polygon filled solid lamp under the lamp drop shadow, fades in and out whatever
 * hover, focus, "Show all objects" or the collected state show on the Hotspot.
 */
export function hotspotLayer(photo: Size, interactables: readonly PlayInteractable[], handlers: HotspotHandlers): HotspotLayer {
  const svg = document.createElementNS(SVG, 'svg')
  svg.setAttribute('class', 'scene-hotspots')
  svg.setAttribute('viewBox', `0 0 ${photo.width} ${photo.height}`)
  svg.setAttribute('preserveAspectRatio', 'none')
  const chip = document.createElement('div')
  chip.className = 'hotspot-label-chip label'
  chip.setAttribute('aria-hidden', 'true') // the label is already the Hotspot's accessible name
  const hotspots = new Map<string, SVGGElement>()

  const shown = interactables
    .map((interactable) => ({ interactable, d: hotspotPath(interactable.polygons ?? []) }))
    .filter(({ d }) => d !== '')
    .sort((a, b) => readingOrder(a.interactable.polygons ?? [], b.interactable.polygons ?? []))
  for (const { interactable, d } of shown) {
    const hotspot = document.createElementNS(SVG, 'g')
    hotspot.setAttribute('class', 'hotspot')
    hotspot.id = interactable.id
    hotspot.setAttribute('role', 'button')
    hotspot.setAttribute('aria-label', interactable.label)
    hotspot.setAttribute('tabindex', '0')
    const reveal = document.createElementNS(SVG, 'g')
    reveal.setAttribute('class', 'hotspot-reveal')
    reveal.append(path('hotspot-glow', d), path('hotspot-halo', d), path('hotspot-outline', d))
    hotspot.append(reveal, path('hotspot-bloom', d), path('hotspot-hit', d))
    let dwell: ReturnType<typeof setTimeout> | undefined
    hotspot.addEventListener('pointerenter', () => {
      handlers.onPointerEnter()
      dwell = setTimeout(() => showLabel(interactable, 'dwell'), DWELL_MS)
    })
    hotspot.addEventListener('pointerleave', () => clearTimeout(dwell))
    hotspot.addEventListener('click', () => handlers.onActivate(interactable))
    hotspot.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') handlers.onActivate(interactable)
    })
    hotspot.addEventListener('focus', () => {
      if (hotspot.matches(':focus-visible')) showChip(interactable, interactable.label)
    })
    hotspot.addEventListener('blur', () => hide?.())
    // A drag from the Inventory shows the hover reveal on the Hotspot under the pointer and drops onto it.
    hotspot.addEventListener('dragenter', (event) => dragOver(event, hotspot, handlers))
    hotspot.addEventListener('dragover', (event) => dragOver(event, hotspot, handlers))
    hotspot.addEventListener('dragleave', () => hotspot.classList.remove('is-drop-target'))
    hotspot.addEventListener('drop', (event) => {
      hotspot.classList.remove('is-drop-target')
      if (!handlers.canDrop()) return
      event.preventDefault()
      handlers.onDrop(interactable)
    })
    hotspots.set(interactable.id, hotspot)
    svg.append(hotspot)
  }

  /** Hides the chip shown on focus or after a click. */
  let hide: (() => void) | undefined
  /** Clears the chip held for a pending click or `use_on`, which no focus, dwell, timeout or pointer leave replaces. */
  let release: (() => void) | undefined
  let collected: readonly string[] = []

  /**
   * Shows `text` (a label, or a label and the Checking chip) on the chip over the Interactable's Hotspot: until the
   * returned function runs when `pending`, else for as long as the Hotspot keeps keyboard focus, else until the
   * pointer leaves it, after 2 s at most unless a `dwell` showed it.
   */
  function showChip(interactable: PlayInteractable, text: string | (string | Node)[], hold: ChipHold = 'click'): () => void {
    const hotspot = hotspots.get(interactable.id)
    if (hotspot === undefined || (release !== undefined && hold !== 'pending')) return () => undefined
    hide?.()
    release?.()
    const rendered = svg.getBoundingClientRect()
    const scale = rendered.width / photo.width
    const [left, top] = topLeft(interactable.polygons ?? [])
    if (typeof text === 'string') chip.textContent = text
    else chip.replaceChildren(...text)
    chip.style.left = `${left * scale}px`
    // 8 px above the polygon, kept inside the photo when the polygon touches its top edge.
    const bottom = Math.min(rendered.height - top * scale + CHIP_OFFSET_PX, rendered.height - chip.offsetHeight)
    chip.style.bottom = `${bottom}px`
    chip.classList.add('is-shown')
    let timer: ReturnType<typeof setTimeout> | undefined
    const done = (): void => {
      if (hide !== done && release !== done) return // a later chip took its place
      clearTimeout(timer)
      hotspot.removeEventListener('pointerleave', done)
      chip.classList.remove('is-shown')
      hide = release = undefined
    }
    if (hold === 'pending') {
      release = done
      return done
    }
    hide = done
    // Keyboard focus holds the chip until blur; otherwise it leaves with the pointer, after 2 s at most for a click.
    if (document.activeElement === hotspot && hotspot.matches(':focus-visible')) return done
    if (hold === 'click') timer = setTimeout(() => hide?.(), CHIP_MS)
    hotspot.addEventListener('pointerleave', done)
    return done
  }

  function setCollected(inventory: readonly string[]): void {
    collected = inventory
    for (const [id, hotspot] of hotspots) hotspot.classList.toggle('is-collected', inventory.includes(id))
  }

  function showLabel(interactable: PlayInteractable, hold: ChipHold = 'click'): void {
    const held = collected.includes(interactable.id)
    showChip(interactable, held ? fill(strings.inHand, { label: interactable.label }) : interactable.label, hold)
  }

  function showPending(interactable: PlayInteractable): () => void {
    const checking = document.createElement('span')
    checking.className = 'chip chip-pending label'
    checking.textContent = `${strings.checking}…`
    return showChip(interactable, [interactable.label, checking], 'pending')
  }

  function bloom(interactableId: string, hold: number): void {
    const hotspot = hotspots.get(interactableId)
    if (hotspot !== undefined) glowOnce(hotspot, 'is-blooming', hold)
  }

  return { elements: [svg, chip], showLabel, setCollected, showPending, bloom }
}
