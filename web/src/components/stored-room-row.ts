import './stored-room-row.css'
import type { RoomSummary } from '../../types'
import { photoUrl } from '../api/index.ts'
import { fill, strings } from '../strings.ts'
import { secondaryButton } from './button.ts'

const BUILT_AT = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' })

/** The row's title: the Room's name when it has one, else its build date and time. */
export function roomTitle(room: RoomSummary): string {
  return room.name || BUILT_AT.format(new Date(room.built_at))
}

/**
 * `{components.stored-room-row}` (UX-DR19): a `chrome` row with the 96 x 72 cover thumbnail, the title, the Puzzle
 * count in `body-sm` and "Play" (secondary). The thumbnail is decorative beside the title, so its alt is empty.
 * "How this room was built" joins in 2.31.
 */
export function storedRoomRow(room: RoomSummary, onPlay: () => void): HTMLLIElement {
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
  count.textContent = fill(strings.puzzleCount, { n: room.puzzle_count })
  text.append(title, count)
  row.append(cover, text, secondaryButton({ label: strings.play, onActivate: onPlay }))
  return row
}
