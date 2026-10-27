import type { Meta } from '../types'
import { RequestFailed } from './api/index.ts'
import { noticeCard } from './components/notice-card.ts'
import { placeHref } from './router.ts'
import { strings } from './strings.ts'

/** A room-keyed refusal that leaves the route nothing to show: a deleted Judge room, or an id no Room has (AD-9). */
export type RoomGone = 'room_deleted' | 'room_not_found'

/** Which room-keyed refusal `error` is: 410 `room_deleted` or 404 `room_not_found`; null for anything else (AD-13). */
export function roomGone(error: unknown): RoomGone | null {
  if (!(error instanceof RequestFailed)) return null
  if (error.status === 410 && error.code === 'room_deleted') return 'room_deleted'
  if (error.status === 404 && error.code === 'room_not_found') return 'room_not_found'
  return null
}

/**
 * The Deleted Judge room notice, or the unknown-room card (FR-33, UX-DR47): `body` then holds only the centered
 * 480 px `chrome-raised` card, focused on its heading, with no scrim and no fade. A deleted room says it was deleted
 * on Tue Nov 10, as promised; an unknown one asks to check the link. Its one button goes to `#/`: "Go to the demo
 * rooms", the Hosted landing, for a deleted room and for an unknown one in Hosted mode; "Build a room", the Capture
 * screen, for an unknown one in Local mode.
 */
export function showRoomGone(body: HTMLElement, gone: RoomGone, mode: Meta['mode'], profile: string): void {
  const deleted = gone === 'room_deleted'
  const card = noticeCard({
    heading: deleted ? strings.roomDeleted : strings.roomNotFound,
    sentence: deleted ? strings.roomDeletedBody : strings.roomNotFoundBody,
    action: {
      label: deleted || mode === 'hosted' ? strings.goToDemoRooms : strings.buildARoom,
      onActivate: () => {
        location.hash = placeHref({ route: { name: 'home' }, profile })
      },
    },
  })
  body.className = 'shell-body notice-layout'
  body.replaceChildren(card.element)
  card.heading.focus()
}
