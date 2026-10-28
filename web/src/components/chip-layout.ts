// Where the mask overlays' label chips sit in a tile. Pure, no DOM or CSS, so the tests run it as it ships.
import type { Rect, Size } from '../scene/geometry.ts'

/** Each tile is 4:3; the photo sits in it whole (contained), as in the Scene. */
const TILE_RATIO = 4 / 3
/** The gap between a chip and the mask under it, and between two chips, stacked or side by side. */
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
 * inside the tile, at the tile's top edge when the mask reaches it. Chips are placed from the top down; one that
 * would cover a chip already placed moves to the nearest clear place, over or under the chips in its way (the gap
 * between) or beside them, still inside the tile. Any clear place slides toward the chip's own place until it meets
 * one of those chips or the tile's edge, so one is found whenever the tile has room; in a tile with none the chip
 * keeps its own place.
 */
export function placeChips(masks: readonly Rect[], chips: readonly Size[], photo: Size, tile: Size): Rect[] {
  const owns = masks.map((mask, index) => {
    const { width, height } = chips[index]
    const [left, top] = tilePoint([mask.x + mask.width / 2, mask.y], photo)
    return {
      x: Math.max(0, Math.min((left / 100) * tile.width - width / 2, tile.width - width)),
      y: Math.max(0, Math.min((top / 100) * tile.height - height - CHIP_GAP, tile.height - height)),
    }
  })
  const boxes: Rect[] = []
  const placed: Rect[] = []
  for (const index of owns.map((_, index) => index).sort((a, b) => owns[a].y - owns[b].y)) {
    const own = owns[index]
    const { width, height } = chips[index]
    const inside = (values: number[], limit: number): number[] => values.filter((v) => v >= 0 && v <= limit)
    const xs = inside([own.x, ...placed.flatMap((o) => [o.x + o.width + CHIP_GAP, o.x - width - CHIP_GAP])], tile.width - width)
    const ys = inside([own.y, ...placed.flatMap((o) => [o.y + o.height + CHIP_GAP, o.y - height - CHIP_GAP])], tile.height - height)
    const places = ys.flatMap((y) => xs.map((x) => ({ x, y, width, height })))
    places.sort((a, b) => Math.abs(a.x - own.x) + Math.abs(a.y - own.y) - Math.abs(b.x - own.x) - Math.abs(b.y - own.y))
    const box = places.find((place) => !placed.some((other) => overlaps(place, other))) ?? { ...own, width, height }
    placed.push(box)
    boxes[index] = box
  }
  return boxes
}
