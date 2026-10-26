import type { PlayInteractable } from '../../types'
import { hotspotPath, type Size, topLeft } from './geometry.ts'

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
  /** Shows the Interactable's label on the chip until 2 s pass or the pointer leaves its Hotspot. */
  showLabel: (interactable: PlayInteractable) => void
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
 * Each is a focusable button named by the Interactable label whose id is the Interactable id; only its hit path
 * takes the pointer, so a click outside every polygon reaches no Hotspot. Invisible at rest; the reveal (outline,
 * halo and glow fill) shows on hover and on keyboard focus, never with a label.
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

  for (const interactable of interactables) {
    const d = hotspotPath(interactable.polygons ?? [])
    if (d === '') continue
    const hotspot = document.createElementNS(SVG, 'g')
    hotspot.setAttribute('class', 'hotspot')
    hotspot.id = interactable.id
    hotspot.setAttribute('role', 'button')
    hotspot.setAttribute('aria-label', interactable.label)
    hotspot.setAttribute('tabindex', '0')
    const reveal = document.createElementNS(SVG, 'g')
    reveal.setAttribute('class', 'hotspot-reveal')
    reveal.append(path('hotspot-halo', d), path('hotspot-outline', d))
    hotspot.append(reveal, path('hotspot-hit', d))
    hotspot.addEventListener('pointerenter', handlers.onPointerEnter)
    hotspot.addEventListener('click', () => handlers.onActivate(interactable))
    hotspot.addEventListener('keydown', (event) => {
      if (event.key === 'Enter') handlers.onActivate(interactable)
    })
    hotspots.set(interactable.id, hotspot)
    svg.append(hotspot)
  }

  let hide: (() => void) | undefined

  function showLabel(interactable: PlayInteractable): void {
    const hotspot = hotspots.get(interactable.id)
    if (hotspot === undefined) return
    hide?.()
    const rendered = svg.getBoundingClientRect()
    const scale = rendered.width / photo.width
    const [left, top] = topLeft(interactable.polygons ?? [])
    chip.textContent = interactable.label
    chip.style.left = `${left * scale}px`
    // 8 px above the polygon, kept inside the photo when the polygon touches its top edge.
    const bottom = Math.min(rendered.height - top * scale + CHIP_OFFSET_PX, rendered.height - chip.offsetHeight)
    chip.style.bottom = `${bottom}px`
    chip.classList.add('is-shown')
    const timer = setTimeout(() => hide?.(), CHIP_MS)
    const done = (): void => {
      clearTimeout(timer)
      hotspot.removeEventListener('pointerleave', done)
      chip.classList.remove('is-shown')
      hide = undefined
    }
    hotspot.addEventListener('pointerleave', done)
    hide = done
  }

  return { elements: [svg, chip], showLabel }
}
