import './mask-preview.css'
import type { MaskPreview } from '../../types'
import { hotspotPath, type Polygon, type Size, topLeft } from '../scene/geometry.ts'
import { CHIP_OFFSET_PX } from '../scene/hotspots.ts'
import { fading } from './fade.ts'

const SVG = 'http://www.w3.org/2000/svg'
const TILE: Size = { width: 120, height: 90 }

/** A photo the tile draws under its outline: its URL and its pixel size, the space the polygons are in. */
export interface TilePhoto {
  url: string
  size: Size
}

function svg<K extends keyof SVGElementTagNameMap>(tag: K, attributes: Record<string, string>): SVGElementTagNameMap[K] {
  const element = document.createElementNS(SVG, tag)
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, value)
  return element
}

/** The box `polygons` span with a tenth of it as margin each side: the tile's frame when no photo is held. */
function around(polygons: readonly Polygon[]): [number, number, number, number] {
  const points = polygons.flat()
  const [left, top] = topLeft(polygons)
  const width = Math.max(...points.map(([x]) => x)) - left || 1
  const height = Math.max(...points.map(([, y]) => y)) - top || 1
  return [left - width / 10, top - height / 10, width * 1.2, height * 1.2]
}

function tile({ label, polygons }: MaskPreview, photo: TilePhoto | null): HTMLElement {
  const element = document.createElement('li')
  element.className = 'mask-tile'
  const [x, y, width, height] = photo === null ? around(polygons) : [0, 0, photo.size.width, photo.size.height]
  const drawing = svg('svg', { viewBox: `${x} ${y} ${width} ${height}`, preserveAspectRatio: 'xMidYMid meet' })
  drawing.setAttribute('aria-hidden', 'true')
  if (photo !== null) drawing.append(svg('image', { href: photo.url, width: `${width}`, height: `${height}` }))
  const d = hotspotPath(polygons)
  drawing.append(svg('path', { class: 'mask-tile-halo', d }), svg('path', { class: 'mask-tile-outline', d }))
  // The chip sits 8 px above the outline's top-left corner, in tile pixels, kept inside the tile.
  const scale = Math.min(TILE.width / width, TILE.height / height)
  const [left, top] = topLeft(polygons)
  const chip = document.createElement('span')
  chip.className = 'mask-tile-chip label'
  chip.textContent = label
  chip.dataset.left = `${Math.max(0, (TILE.width - width * scale) / 2 + (left - x) * scale)}`
  chip.style.bottom = `${TILE.height - ((TILE.height - height * scale) / 2 + (top - y) * scale) + CHIP_OFFSET_PX}px`
  element.append(drawing, chip)
  return element
}

/**
 * The Mask preview (UX-DR18): one 120 x 90 tile per Interactable, in segment order, each its clearest photo
 * contained, with the outline drawn in `{components.build-view-mask}` style and the label on a parchment chip in
 * `label` type. `photos` holds the photo of each index this page has, else a tile frames the outline alone. The
 * grid fades in whole (200 ms); it has no heading, and no tile is a control or takes focus.
 */
export function maskPreview(tiles: readonly MaskPreview[], photos: ReadonlyMap<number, TilePhoto>): HTMLElement {
  const grid = fading(document.createElement('ul'))
  grid.classList.add('mask-preview')
  grid.append(...tiles.map((preview) => tile(preview, photos.get(preview.photo) ?? null)))
  return grid
}

/**
 * Keeps every chip inside its tile once the grid is in the page: each is measured at the tile's left edge, where it
 * has the tile's full width, held at that width, then moved toward its anchor as far as the width allows.
 */
export function fitChips(grid: HTMLElement): void {
  for (const chip of grid.querySelectorAll<HTMLElement>('.mask-tile-chip')) {
    chip.style.left = '0px'
    const width = Math.ceil(chip.getBoundingClientRect().width)
    chip.style.width = `${width}px` // so moving it right never rewraps its label
    chip.style.left = `${Math.min(Number(chip.dataset.left), Math.max(0, TILE.width - width))}px`
    chip.style.bottom = `${Math.min(parseFloat(chip.style.bottom), TILE.height - chip.offsetHeight)}px`
  }
}
