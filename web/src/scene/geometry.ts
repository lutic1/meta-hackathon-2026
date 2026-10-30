// Hotspot geometry (AD-11): an Interactable's `polygons`, one per instance, in the pixel space of the stored
// downscaled 1280 px JPEG. The client never reads `box` and never branches on how a polygon was made.

export type Polygon = [number, number][]

export interface Size {
  width: number
  height: number
}

/** Twice the signed area of `polygon` (shoelace); its sign is the winding. */
function signedArea(polygon: Polygon): number {
  return polygon.reduce((sum, [x, y], i) => {
    const [nx, ny] = polygon[(i + 1) % polygon.length]
    return sum + x * ny - nx * y
  }, 0)
}

/**
 * One SVG path for the union of `polygons`: one closed subpath per polygon, all wound the same way, so the nonzero
 * fill rule paints and hit-tests their union once, overlaps included.
 */
export function hotspotPath(polygons: readonly Polygon[]): string {
  return polygons
    .filter((polygon) => polygon.length >= 3)
    .map((polygon) => (signedArea(polygon) < 0 ? [...polygon].reverse() : polygon))
    .map((polygon) => `M${polygon.map(([x, y]) => `${x} ${y}`).join(' L')} Z`)
    .join(' ')
}

/**
 * The area-weighted centroid of every polygon together, in photo pixels: where a Hotspot falls in the Tab order. A
 * shape with no area (every polygon degenerate) falls back to the mean of its points.
 */
export function centroid(polygons: readonly Polygon[]): [number, number] {
  let area = 0
  let cx = 0
  let cy = 0
  for (const polygon of polygons) {
    // Each polygon's moments taken with one winding, so instances wound either way add up.
    const sign = signedArea(polygon) < 0 ? -1 : 1
    polygon.forEach(([x, y], i) => {
      const [nx, ny] = polygon[(i + 1) % polygon.length]
      const cross = sign * (x * ny - nx * y)
      area += cross
      cx += (x + nx) * cross
      cy += (y + ny) * cross
    })
  }
  if (area !== 0) return [cx / (3 * area), cy / (3 * area)]
  const points = polygons.flat()
  return [points.reduce((sum, [x]) => sum + x, 0) / points.length, points.reduce((sum, [, y]) => sum + y, 0) / points.length]
}

/** Tab order over Hotspots: by centroid from top to bottom, then left to right. */
export function readingOrder(a: readonly Polygon[], b: readonly Polygon[]): number {
  const [ax, ay] = centroid(a)
  const [bx, by] = centroid(b)
  return ay - by || ax - bx
}

/** The top-left corner of the box around every polygon, in photo pixels: where the label chip is anchored. */
export function topLeft(polygons: readonly Polygon[]): [number, number] {
  const points = polygons.flat()
  return [Math.min(...points.map(([x]) => x)), Math.min(...points.map(([, y]) => y))]
}

/** `photo` scaled to fit inside `frame` whole: contained, never cropped, letterboxed on the other axis. */
export function contain(photo: Size, frame: Size): Size {
  const scale = Math.min(frame.width / photo.width, frame.height / photo.height)
  return { width: Math.floor(photo.width * scale), height: Math.floor(photo.height * scale) }
}

export interface Rect {
  x: number
  y: number
  width: number
  height: number
}

/** The bounds of every polygon, in photo pixels: what an Inventory item or Evidence card crop is cut from. */
export function bounds(polygons: readonly Polygon[]): Rect {
  const [x, y] = topLeft(polygons)
  const points = polygons.flat()
  return { x, y, width: Math.max(...points.map(([px]) => px)) - x, height: Math.max(...points.map(([, py]) => py)) - y }
}

/** The polygon covering the most area: the one instance a crop is cut from (spec 1.8, the two-polygon pillows). */
export function largest(polygons: readonly Polygon[]): Polygon | undefined {
  return polygons.reduce<Polygon | undefined>(
    (best, polygon) => (best === undefined || Math.abs(signedArea(polygon)) > Math.abs(signedArea(best)) ? polygon : best),
    undefined,
  )
}

/** The crop `aspect` (width over height) wide around `rect`: just big enough for it, centered on it and kept inside the photo. */
export function cropAround(rect: Rect, photo: Size, aspect: number): Rect {
  const width = Math.min(Math.max(rect.width, rect.height * aspect), photo.width, photo.height * aspect)
  const height = width / aspect
  const clamp = (start: number, side: number, limit: number): number => Math.min(Math.max(start, 0), limit - side)
  return {
    x: clamp(rect.x + (rect.width - width) / 2, width, photo.width),
    y: clamp(rect.y + (rect.height - height) / 2, height, photo.height),
    width,
    height,
  }
}

/** The square crop around `rect`: its longer side, centered on it and kept inside the photo. */
export function squareAround(rect: Rect, photo: Size): Rect {
  return cropAround(rect, photo, 1)
}
