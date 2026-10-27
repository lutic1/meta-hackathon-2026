import type { PlayInteractable } from '../../types'
import { fill, strings } from '../strings.ts'
import { hotspotPath, readingOrder, type Size, topLeft } from './geometry.ts'

const SVG = 'http://www.w3.org/2000/svg'

/** DESIGN.md `{components.hotspot-label-chip}`: anchored 8 px above the polygon's top edge. */
export const CHIP_OFFSET_PX = 8
/** UX-DR24: after a non-target click the label chip fades after 2 s, or sooner on pointer leave. */
export const CHIP_MS = 2000

export interface HotspotHandlers {
  /** A click inside any of the Hotspot's polygons, or Enter on it. */
  onActivate: (interactable: PlayInteractable) => void
  /** The pointer reached the Hotspot: its hover reveal shows. */
  onPointerEnter: () => void
}

export interface HotspotLayer {
  /** The overlay over the photo: the Hotspots' SVG and the label chip. */
  elements: [SVGSVGElement, HTMLElement]
  /**
   * Shows the Interactable's label on the chip until 2 s pass or the pointer leaves its Hotspot, or for as long as
   * its Hotspot keeps keyboard focus: "{label} · in hand" for an Interactable the Inventory holds.
   */
  showLabel: (interactable: PlayInteractable) => void
  /** Marks the Hotspots of the Interactables `inventory` holds: a collected one's glow fades out and stays out. */
  setCollected: (inventory: readonly string[]) => void
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
 * outside every polygon reaches no Hotspot. Invisible at rest; the reveal (outline, halo and glow fill) shows on
 * hover, never with a label, and keyboard focus traces the focus ring along it with the label chip shown for as long
 * as it keeps focus (UX-DR69). A collected `find` target stays in the Scene, still a Hotspot, but its glow fill fades
 * out over 200 ms and no longer shows (FR-12).
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
    hotspot.append(reveal, path('hotspot-hit', d))
    hotspot.addEventListener('pointerenter', handlers.onPointerEnter)
    hotspot.addEventListener('click', () => handlers.onActivate(interactable))
    hotspot.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') handlers.onActivate(interactable)
    })
    hotspot.addEventListener('focus', () => {
      if (hotspot.matches(':focus-visible')) showChip(interactable, interactable.label)
    })
    hotspot.addEventListener('blur', () => hide?.())
    hotspots.set(interactable.id, hotspot)
    svg.append(hotspot)
  }

  let hide: (() => void) | undefined
  let collected: readonly string[] = []

  /**
   * Shows `text` on the chip over the Interactable's Hotspot: for as long as the Hotspot keeps keyboard focus, else
   * until 2 s pass or the pointer leaves it.
   */
  function showChip(interactable: PlayInteractable, text: string): void {
    const hotspot = hotspots.get(interactable.id)
    if (hotspot === undefined) return
    hide?.()
    const rendered = svg.getBoundingClientRect()
    const scale = rendered.width / photo.width
    const [left, top] = topLeft(interactable.polygons ?? [])
    chip.textContent = text
    chip.style.left = `${left * scale}px`
    // 8 px above the polygon, kept inside the photo when the polygon touches its top edge.
    const bottom = Math.min(rendered.height - top * scale + CHIP_OFFSET_PX, rendered.height - chip.offsetHeight)
    chip.style.bottom = `${bottom}px`
    chip.classList.add('is-shown')
    let timer: ReturnType<typeof setTimeout> | undefined
    const done = (): void => {
      clearTimeout(timer)
      hotspot.removeEventListener('pointerleave', done)
      chip.classList.remove('is-shown')
      hide = undefined
    }
    hide = done
    // Keyboard focus holds the chip until blur; otherwise it fades after 2 s, or sooner on pointer leave.
    if (document.activeElement === hotspot && hotspot.matches(':focus-visible')) return
    timer = setTimeout(() => hide?.(), CHIP_MS)
    hotspot.addEventListener('pointerleave', done)
  }

  function setCollected(inventory: readonly string[]): void {
    collected = inventory
    for (const [id, hotspot] of hotspots) hotspot.classList.toggle('is-collected', inventory.includes(id))
  }

  function showLabel(interactable: PlayInteractable): void {
    const held = collected.includes(interactable.id)
    showChip(interactable, held ? fill(strings.inHand, { label: interactable.label }) : interactable.label)
  }

  return { elements: [svg, chip], showLabel, setCollected }
}
