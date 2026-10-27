// Where the mask overlays' label chips sit in a tile. Pure, no DOM or CSS, so the tests run it as it ships.
import type { Rect, Size } from '../scene/geometry.ts'

/** Each tile is 4:3; the photo sits in it whole (contained), as in the Scene. */
const TILE_RATIO = 4 / 3
/** The gap between a chip and the mask under it, and between two stacked chips. */
const CHIP_GAP = 4

/** Where `point` (photo pixels) falls in the 4:3 tile, in percent of the tile, with the photo contained in it. */
export function tilePoint([x, y]: [number, number], photo: Size): [number, number] {
  const ratio = photo.width / photo.height
  const width = ratio >= TILE_RATIO ? 1 : ratio / TILE_RATIO
  const height = ratio >= TILE_RATIO ? TILE_RATIO / ratio : 1
  return [((1 - width) / 2 + (width * x) / photo.width) * 100, ((1 - height) / 2 + (height * y) / photo.height) * 100]
}

function overlaps(a: Rect, b: Rect): boolean {
  return a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height
}

/**
 * Each chip's box in the tile (px): just above its mask's top edge (`masks` in photo pixels), centred on it and kept
 * inside the tile, at the tile's top edge when the mask reaches it. Chips are placed in order; one that would cover a
 * chip already placed moves down a chip's height and the gap at a time, then up, until it is clear, still inside the
 * tile.
 */
export function placeChips(masks: readonly Rect[], chips: readonly Size[], photo: Size, tile: Size): Rect[] {
  const placed: Rect[] = []
  masks.forEach((mask, index) => {
    const { width, height } = chips[index]
    const [left, top] = tilePoint([mask.x + mask.width / 2, mask.y], photo)
    const x = Math.max(0, Math.min((left / 100) * tile.width - width / 2, tile.width - width))
    const base = Math.max(0, Math.min((top / 100) * tile.height - height - CHIP_GAP, tile.height - height))
    const pitch = height + CHIP_GAP
    const tops = [base]
    for (let y = base + pitch; y <= tile.height - height; y += pitch) tops.push(y)
    for (let y = base - pitch; y >= 0; y -= pitch) tops.push(y)
    const y = tops.find((t) => !placed.some((other) => overlaps({ x, y: t, width, height }, other))) ?? base
    placed.push({ x, y, width, height })
  })
  return placed
}
