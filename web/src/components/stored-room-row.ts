import './stored-room-row.css'
import type { RoomSummary } from '../../types'
import { photoUrl } from '../api/index.ts'
import { buildViewLink } from '../build-view.ts'
import { fill, strings } from '../strings.ts'
import { buildTime } from './build-view-header.ts'
import { secondaryButton } from './button.ts'

/** The row's title: the Room's name when it has one, else its build time as the Build view header reads it. */
export function roomTitle(room: RoomSummary): string {
  return room.name || buildTime(room.built_at)
}

/**
 * `{components.stored-room-row}` (UX-DR19): a `chrome` row with the 96 x 72 cover thumbnail, the title, the Puzzle
 * count in `body-sm`, "Play" (secondary) and "How this room was built" (secondary, the Build view of the summary's
 * job; absent under cut 0). The thumbnail is decorative beside the title, so its alt is empty.
 */
export function storedRoomRow(room: RoomSummary, profile: string, onPlay: () => void): HTMLLIElement {
  const row = document.createElement('li')
  row.className = 'stored-room-row'
  const cover = document.createElement('img')
  cover.className = 'stored-room-cover'
  cover.src = photoUrl(room.room_id, room.cover_photo)
  cover.alt = ''
  cover.width = 96
  cover.height = 72
  const text = document.createElement('div')
  text.className = 'stored-room-text'
  const title = document.createElement('p')
  title.className = 'stored-room-title body-sm'
  title.textContent = roomTitle(room)
  const count = document.createElement('p')
  count.className = 'stored-room-meta body-sm'
  count.textContent = room.puzzle_count === 1 ? strings.onePuzzle : fill(strings.puzzleCount, { n: room.puzzle_count })
  text.append(title, count)
  row.append(cover, text, secondaryButton({ label: strings.play, onActivate: onPlay }))
  const link = buildViewLink(room.job_id, profile)
  if (link !== null) row.append(link)
  return row
}
