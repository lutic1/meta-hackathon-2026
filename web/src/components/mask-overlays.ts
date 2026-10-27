import './mask-overlays.css'
import type { BuildView, MaskOverlay, PhotoMasks } from '../../types'
import { photoUrl } from '../api/index.ts'
import { bounds, hotspotPath, type Size } from '../scene/geometry.ts'
import { fill, strings } from '../strings.ts'
import { placeChips } from './chip-layout.ts'

const SVG = 'http://www.w3.org/2000/svg'

/** The stored downscale's size until the photo has loaded: its 1280 px long edge at 4:3. */
const DEFAULT_SIZE: Size = { width: 1280, height: 960 }

function path(className: string, d: string): SVGPathElement {
  const element = document.createElementNS(SVG, 'path')
  element.setAttribute('class', className)
  element.setAttribute('d', d)
  return element
}

/**
 * One photo of the grid: the photo, every Interactable's mask on it as `{components.build-view-mask}` (the union of its
 * polygons, filled and stroked over a dark halo; a box fallback is a polygon like any other, so it draws the same),
 * and each label on a focusable parchment chip just above the mask's top edge, placed by `placeChips` so no two chips
 * overlap. The SVG takes the photo's own pixel space once the photo has loaded, so the masks line up with it at any
 * tile size; the chips are placed again whenever the tile or a chip changes size.
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
  let photoSize = DEFAULT_SIZE
  const place = (): void => {
    overlay.setAttribute('viewBox', `0 0 ${photoSize.width} ${photoSize.height}`)
    const tileSize = { width: tile.clientWidth, height: tile.clientHeight }
    if (tileSize.width === 0) return
    const sizes = chips.map((chip) => ({ width: chip.offsetWidth, height: chip.offsetHeight }))
    const boxes = placeChips(drawn.map(([mask]) => bounds(mask.polygons)), sizes, photoSize, tileSize)
    boxes.forEach(({ x, y }, index) => {
      chips[index].style.left = `${x}px`
      chips[index].style.top = `${y}px`
    })
  }
  place()
  image.addEventListener('load', () => {
    photoSize = { width: image.naturalWidth, height: image.naturalHeight }
    place()
  })
  // Placing a chip moves it but never resizes it or the tile, so this never re-enters itself.
  const observer = new ResizeObserver(() => place())
  for (const element of [tile, ...chips]) observer.observe(element)
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
