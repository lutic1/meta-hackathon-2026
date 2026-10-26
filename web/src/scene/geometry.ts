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
