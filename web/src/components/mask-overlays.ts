import './mask-overlays.css'
import type { BuildView, MaskOverlay, PhotoMasks } from '../../types'
import { photoUrl } from '../api/index.ts'
import { bounds, hotspotPath, type Size } from '../scene/geometry.ts'
import { fill, strings } from '../strings.ts'

const SVG = 'http://www.w3.org/2000/svg'

/** Each tile is 4:3; the photo sits in it whole (contained), as in the Scene. */
const TILE_RATIO = 4 / 3
/** The stored downscale's size until the photo has loaded: its 1280 px long edge at 4:3. */
const DEFAULT_SIZE: Size = { width: 1280, height: 960 }
/** How far a chip's top sits above the mask: its 21 px height (label type, 2 px padding) and a 4 px gap. */
const CHIP_LIFT_PX = 25

function path(className: string, d: string): SVGPathElement {
  const element = document.createElementNS(SVG, 'path')
  element.setAttribute('class', className)
  element.setAttribute('d', d)
  return element
}

/** Where `point` (photo pixels) falls in the 4:3 tile, in percent of the tile, with the photo contained in it. */
export function tilePoint([x, y]: [number, number], photo: Size): [number, number] {
  const ratio = photo.width / photo.height
  const width = ratio >= TILE_RATIO ? 1 : ratio / TILE_RATIO
  const height = ratio >= TILE_RATIO ? TILE_RATIO / ratio : 1
  return [((1 - width) / 2 + (width * x) / photo.width) * 100, ((1 - height) / 2 + (height * y) / photo.height) * 100]
}

/**
 * One photo of the grid: the photo, every Interactable's mask on it as `{components.build-view-mask}` (the union of its
 * polygons, filled and stroked over a dark halo; a box fallback is a polygon like any other, so it draws the same),
 * and each label on a focusable parchment chip just above the mask's top edge, centred on it and kept inside the tile
 * (at the tile's top edge when the mask reaches it, slid inward near a side edge). The SVG takes the photo's own pixel
 * space once the photo has loaded, so the masks line up with it at any tile size.
 */
function maskTile(roomId: string, { photo, masks }: PhotoMasks): HTMLElement {
  const drawn = masks.flatMap((mask): [MaskOverlay, string][] => {
    const d = hotspotPath(mask.polygons)
    return d === '' ? [] : [[mask, d]]
  })
  const tile = document.createElement('div')
  tile.className = 'mask-tile'
  tile.setAttribute('role', 'group')
  tile.setAttribute('aria-label', fill(strings.photoThumbnail, { n: photo + 1 }))
  const image = document.createElement('img')
  image.className = 'mask-tile-photo'
  image.alt = ''
  image.src = photoUrl(roomId, photo)
  const overlay = document.createElementNS(SVG, 'svg')
  overlay.setAttribute('class', 'mask-tile-overlay')
  overlay.setAttribute('aria-hidden', 'true')
  overlay.setAttribute('preserveAspectRatio', 'xMidYMid meet')
  // Every halo under every mask, so no halo crosses a neighbouring mask's lamp line.
  overlay.append(...drawn.map(([, d]) => path('build-view-mask-halo', d)), ...drawn.map(([, d]) => path('build-view-mask', d)))
  const chips = drawn.map(([mask]) => {
    const chip = document.createElement('span')
    chip.className = 'mask-chip label'
    chip.tabIndex = 0
    chip.textContent = mask.label
    return chip
  })
  const size = (photoSize: Size): void => {
    overlay.setAttribute('viewBox', `0 0 ${photoSize.width} ${photoSize.height}`)
    drawn.forEach(([mask], index) => {
      const box = bounds(mask.polygons)
      const [left, top] = tilePoint([box.x + box.width / 2, box.y], photoSize)
      chips[index].style.left = `${left}%`
      chips[index].style.top = `max(0px, calc(${top}% - ${CHIP_LIFT_PX}px))`
      chips[index].style.transform = `translateX(-${left}%)`
    })
  }
  size(DEFAULT_SIZE)
  image.addEventListener('load', () => size({ width: image.naturalWidth, height: image.naturalHeight }))
  tile.append(image, overlay, ...chips)
  return tile
}

/**
 * The mask overlays grid (UX-DR49): the Room's photos three across at 4:3, from `BuildView.photos`, each with its
 * Interactables' masks and label chips. The chips are Tab stops in photo order; the grid reads no Room.
 */
export function maskOverlays(view: BuildView): HTMLElement {
  const grid = document.createElement('div')
  grid.className = 'mask-overlays'
  grid.append(...view.photos.map((photo) => maskTile(view.room_id, photo)))
  return grid
}
