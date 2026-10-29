import { fill, strings } from './strings.ts'

/** What the shared line says: the Room's title, its lock count, the m:ss time, the Rungs used and the Wrong attempts. */
export interface ShareResult {
  room: string
  locks: number
  time: string
  hints: number
  wrong: number
  url: string
}

/**
 * "Copy your result"'s one line, as "Keyframe - The front hall and the lounge - 4 locks - 3:28 - 2 hints - 0 wrong -
 * <url>": the stats the sheet shows and where to play, never a clue, an object or an answer. Pure: Node runs it as it
 * ships.
 */
export function shareLine({ room, locks, time, hints, wrong, url }: ShareResult): string {
  return fill(strings.shareLine, {
    room,
    locks: locks === 1 ? strings.oneLock : fill(strings.locksCount, { n: locks }),
    time,
    hints: hints === 1 ? strings.oneHint : fill(strings.hintsCount, { n: hints }),
    wrong: fill(strings.wrongCount, { n: wrong }),
    url,
  })
}

/** A stat counting up to `final` at `t` (0 to 1) of the way, easing out: 0 at the start, `final` exactly at the end. */
export function countedAt(final: number, t: number): number {
  if (t >= 1) return final
  return Math.round(final * (1 - (1 - Math.max(0, t)) ** 3))
}
