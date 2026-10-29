import type { PlayInteractable, PlayPuzzle, PostedEvent, SessionState } from '../types'
import { fill, strings } from './strings.ts'

/** What the line reads from the Effective room: each Puzzle's place, lock type and Exit flag, each Interactable's label. */
export interface FeedbackRoom {
  puzzles: readonly Pick<PlayPuzzle, 'id' | 'lock_type' | 'is_exit'>[]
  interactables: readonly Pick<PlayInteractable, 'id' | 'label'>[]
}

/** The parts of a session state the line compares across one reply. */
export type FeedbackState = Pick<SessionState, 'locks_open' | 'inventory' | 'wrong_attempts' | 'order_buffer'>

/** The Interactable a `click` or a `use_on` names, null for any other input. */
function named(input: PostedEvent): string | null {
  if (input.type === 'click') return input.interactable_id
  if (input.type === 'lock_input' && input.input.type === 'use_on') return input.input.target
  return null
}

/**
 * The target the server's reply `after` to `input` found (owner decision Oct 29): a `click` that opened a `find` lock
 * and put nothing in the Inventory, because no `use_on` needs it; null for any other reply. Pure.
 */
export function foundBy(room: FeedbackRoom, input: PostedEvent, before: FeedbackState, after: FeedbackState): string | null {
  if (input.type !== 'click' || after.inventory.includes(input.interactable_id)) return null
  const opened = room.puzzles.some(
    (puzzle) => puzzle.lock_type === 'find' && after.locks_open.includes(puzzle.id) && !before.locks_open.includes(puzzle.id),
  )
  return opened ? input.interactable_id : null
}

/**
 * The feedback line for the server's reply `after` to `input`, posted against `before` (n = the Puzzle's fixed place
 * in the Room): a newly open lock reads "Puzzle {n} solved.", after "You pick up the {label}." when it put an item in
 * the Inventory, and the Exit reads "The way out is open." alone; a Wrong attempt reads the lock outcome "Puzzle {n}:
 * not this, {count}."; a `click` or `use_on` that changed nothing reads "{label}. Not this one.", "{label} · in hand"
 * for a click on an item the Inventory holds, or "{label} · found" for a click on a target `found` holds (a solved
 * `find` target no `use_on` needs). A click that only fills an armed order sequence (its Order click progress
 * answers), the order controls and a Hint request read nothing. Pure: Node runs it as it ships.
 */
export function feedbackFor(
  room: FeedbackRoom,
  input: PostedEvent,
  before: FeedbackState,
  after: FeedbackState,
  found: readonly string[],
): string | null {
  const label = (id: string): string | undefined => room.interactables.find((interactable) => interactable.id === id)?.label
  const place = (id: string): number => room.puzzles.findIndex((puzzle) => puzzle.id === id) + 1
  const opened = room.puzzles.findLast((puzzle) => after.locks_open.includes(puzzle.id) && !before.locks_open.includes(puzzle.id))
  if (opened !== undefined) {
    if (opened.is_exit) return strings.wayOut
    const solved = fill(strings.lockSolved, { n: place(opened.id) })
    const picked = after.inventory.find((id) => !before.inventory.includes(id))
    const item = picked === undefined ? undefined : label(picked)
    return item === undefined ? solved : `${fill(strings.pickUp, { label: item })} ${solved}`
  }
  const wrong = room.puzzles.find((puzzle) => (after.wrong_attempts[puzzle.id] ?? 0) > (before.wrong_attempts[puzzle.id] ?? 0))
  if (wrong !== undefined) return fill(strings.lockNotThis, { n: place(wrong.id), count: after.wrong_attempts[wrong.id] })
  const target = named(input)
  const name = target === null ? undefined : label(target)
  if (target === null || name === undefined) return null
  if ((after.order_buffer.clicks ?? []).length > (before.order_buffer.clicks ?? []).length) return null
  if (input.type === 'click' && after.inventory.includes(target)) return fill(strings.inHand, { label: name })
  if (input.type === 'click' && found.includes(target)) return fill(strings.found, { label: name })
  return fill(strings.notThisOne, { label: name })
}
