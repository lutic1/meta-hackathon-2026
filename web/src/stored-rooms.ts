import type { RoomSummary } from '../types'
import { freshDerived, startSession } from './api/index.ts'
import { showBanner } from './components/error-banner.ts'
import { storedRoomRow } from './components/stored-room-row.ts'
import { placeHref } from './router.ts'
import { strings } from './strings.ts'

/**
 * The Stored Rooms list (Local, UX-DR19): one row per `RoomSummary` exactly as `GET /rooms` served it, newest build
 * first, or "No rooms yet." when there are none. "Play" posts the session start with `Derived.fresh()` (until 5.1)
 * and routes to `#/play/<session_id>`; a refused start shows the session-start-refused banner in `banners`, the
 * slot at the top of the left area, whose "Try again" posts the same start again. One start runs at a time.
 */
export function storedRooms(rooms: readonly RoomSummary[], profile: string, banners: HTMLElement): HTMLElement {
  if (rooms.length === 0) {
    const empty = document.createElement('p')
    empty.className = 'stored-room-empty body-sm'
    empty.textContent = strings.noRooms
    return empty
  }
  let starting = false

  async function start(room: RoomSummary): Promise<void> {
    if (starting) return
    starting = true
    try {
      const session = await startSession({ room_id: room.room_id, derived: freshDerived() })
      showBanner(banners, null)
      location.hash = placeHref({ route: { name: 'play', sessionId: session.id }, profile })
    } catch {
      showBanner(banners, {
        variant: 'error',
        heading: strings.sessionStartRefused,
        sentence: strings.sessionStartRefusedBody,
        actions: [{ label: strings.tryAgain, onActivate: () => void start(room) }],
      })
    } finally {
      starting = false
    }
  }

  const list = document.createElement('ul')
  list.className = 'stored-room-list'
  list.append(...rooms.map((room) => storedRoomRow(room, profile, () => void start(room))))
  return list
}
