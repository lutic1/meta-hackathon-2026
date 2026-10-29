import './filmstrip.css'
import type { PlayView } from '../../types'
import { photoUrl } from '../api/index.ts'
import { hotspotPath } from '../scene/geometry.ts'
import { strings } from '../strings.ts'

const SVG = 'http://www.w3.org/2000/svg'

function path(className: string, d: string): SVGPathElement {
  const element = document.createElementNS(SVG, 'path')
  element.setAttribute('class', className)
  element.setAttribute('d', d)
  return element
}

/** One photo: the picture, and the lit outline of each solved Interactable on it, in the photo's own pixel space. */
function frame(roomId: string, view: PlayView, index: number, solved: ReadonlySet<string>): HTMLElement {
  const tile = document.createElement('div')
  tile.className = 'filmstrip-frame'
  const image = document.createElement('img')
  image.className = 'filmstrip-photo'
  image.alt = ''
  image.src = photoUrl(roomId, index)
  const overlay = document.createElementNS(SVG, 'svg')
  overlay.setAttribute('class', 'filmstrip-svg')
  overlay.setAttribute('preserveAspectRatio', 'none')
  const lit = view.interactables
    .filter((interactable) => interactable.photo === index && solved.has(interactable.id))
    .map((interactable) => hotspotPath(interactable.polygons ?? []))
    .filter((d) => d !== '')
  overlay.append(...lit.map((d) => path('filmstrip-halo', d)), ...lit.map((d) => path('filmstrip-outline', d)))
  image.addEventListener('load', () => {
    overlay.setAttribute('viewBox', `0 0 ${image.naturalWidth} ${image.naturalHeight}`)
  })
  tile.append(image, overlay)
  return tile
}

/**
 * The Completion sheet's filmstrip (owner decision, Oct 29): every photo of the Room in order, one row across the
 * sheet, each solved object's outline lit in lamp over a dark halo. It draws outlines only, never a label, so it
 * names nothing the player has not already found; the photos are decoration under the strip's one accessible name.
 */
export function filmstrip(view: PlayView, solved: ReadonlySet<string>): HTMLElement {
  const strip = document.createElement('div')
  strip.className = 'filmstrip'
  strip.setAttribute('role', 'img')
  strip.setAttribute('aria-label', strings.filmstripLabel)
  strip.style.setProperty('--filmstrip-count', String(Math.max(1, view.photos.length)))
  strip.append(...view.photos.map((_, index) => frame(view.id, view, index, solved)))
  return strip
}
