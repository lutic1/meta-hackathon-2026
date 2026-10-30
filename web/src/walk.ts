// The walk (story mode, owner decision Oct 29): the Room's photos as areas you stand in and turn around, built from
// each photo's served `area` and `pan` alone. Pure, so the Scene, the map and the tests share it.
import type { PhotoView } from '../types'

/** One area of the Room: its label, its photos in turning order (its ring) and the view a walk into it lands on. */
export interface WalkArea {
  label: string
  ring: number[]
  /** The middle view of the ring, `ring[floor((length - 1) / 2)]`. */
  entry: number
}

/** The area a photo with no area at all belongs to: the server's own fallback for rooms built before areas. */
const NO_AREA = 'room'

/**
 * The walk graph: the distinct `area` labels in the order of each one's first photo, each ring holding the area's
 * photos sorted by `pan` (a null pan sorts as the photo's index). A Room without areas is one ring in upload order.
 */
export function walkGraph(photos: readonly Pick<PhotoView, 'area' | 'pan'>[]): WalkArea[] {
  const rings = new Map<string, number[]>()
  photos.forEach((photo, index) => {
    const label = photo.area || NO_AREA
    rings.set(label, [...(rings.get(label) ?? []), index])
  })
  const pan = (index: number): number => photos[index].pan ?? index
  return [...rings].map(([label, ring]) => {
    const sorted = [...ring].sort((a, b) => pan(a) - pan(b))
    return { label, ring: sorted, entry: sorted[Math.floor((sorted.length - 1) / 2)] }
  })
}

/** The index of the area `photo` stands in; -1 for a photo the graph does not hold. */
export function areaOf(areas: readonly WalkArea[], photo: number): number {
  return areas.findIndex((area) => area.ring.includes(photo))
}

/** The views either side of `photo` in its ring; null at the ring's ends, since rings do not wrap. */
export function neighbours(areas: readonly WalkArea[], photo: number): { left: number | null; right: number | null } {
  const ring = areas[areaOf(areas, photo)]?.ring ?? []
  const at = ring.indexOf(photo)
  return { left: at > 0 ? ring[at - 1] : null, right: at >= 0 && at < ring.length - 1 ? ring[at + 1] : null }
}

/** The areas a doorway of `photo` leads to: the previous area, then the next one (consecutive areas only). */
export function doorways(areas: readonly WalkArea[], photo: number): WalkArea[] {
  const at = areaOf(areas, photo)
  if (at < 0) return []
  return [areas[at - 1], areas[at + 1]].filter((area): area is WalkArea => area !== undefined)
}

/** A walk: a turn to either side, or through the (first) doorway. */
export type WalkMove = 'left' | 'right' | 'door'

/** The keyboard map of the walk (spec 6.1): no other key walks. */
const WALK_KEYS: Readonly<Partial<Record<string, WalkMove>>> = { ArrowLeft: 'left', ArrowRight: 'right', ArrowUp: 'door' }

/** The walk a key press asks for, or null for a key that does not walk. */
export function walkKey(key: string): WalkMove | null {
  return Object.hasOwn(WALK_KEYS, key) ? (WALK_KEYS[key] ?? null) : null
}

const px = (value: number): string => `${Math.round(value * 100) / 100 + 0}px`

/**
 * Where a view `offset` places away from the one you face stands, for photos `width` px wide in a 1500 px
 * perspective (spec 5.3): the next view either side is a dimmed wall angled 52 degrees; any further view waits beyond
 * it, angled 62 degrees and unseen, so a turn swings it in.
 */
export function wallPose(offset: number, width: number): { transform: string; opacity: number } {
  if (offset === 0) return { transform: 'translate3d(0px, 0px, 0px) rotateY(0deg)', opacity: 1 }
  const side = Math.sign(offset)
  const far = Math.abs(offset) - 1
  const [x, z, turn] = far === 0 ? [0.94, 0.3, 52] : [0.9 + 0.55 * far, 0.42 + 0.5 * far, 62]
  return {
    transform: `translate3d(${px(side * x * width)}, 0px, ${px(-z * width)}) rotateY(${-side * turn}deg)`,
    opacity: far === 0 ? 1 : 0,
  }
}

/** The map's view cone for the view at `index` of a ring of `count`: -50 degrees at its left end to 50 at its right. */
export function coneAngle(index: number, count: number): number {
  return count > 1 ? -50 + (100 * index) / (count - 1) : 0
}

/** A box in photo pixels: a Hotspot polygon's bounds. */
export interface Box {
  x: number
  y: number
  width: number
  height: number
}

/** The doorway sign's places, in photo pixels for a 960 px wide photo, tried in this order (spec 5.2). */
const SIGN_CENTRES = [480, 640, 320, 760, 200]
const SIGN_HALF = 115
const SIGN_BAND = 120

/**
 * The x centre of the doorway sign hanging from the top edge of a photo `width` px wide: the first place whose
 * 230 x 120 box overlaps none of `boxes` (the photo's Hotspot bounds), else the middle place. Photo pixels throughout.
 */
export function signCentre(boxes: readonly Box[], width: number): number {
  const scale = width / 960
  const clear = (centre: number): boolean =>
    !boxes.some(
      (box) =>
        box.y < SIGN_BAND * scale && box.x < (centre + SIGN_HALF) * scale && box.x + box.width > (centre - SIGN_HALF) * scale,
    )
  return (SIGN_CENTRES.find(clear) ?? SIGN_CENTRES[0]) * scale
}
