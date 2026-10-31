import type { PlayInteractable, PlayPuzzle, PostedEvent, SessionState } from '../types'
import type { Cue } from './audio.ts'
import { riddleNumber } from './riddles.ts'
import { fill, strings } from './strings.ts'

/**
 * What the line reads from the Effective room: each Puzzle's place, prerequisites (its riddle number), lock type and
 * Exit flag, each Interactable's label.
 */
export interface FeedbackRoom {
  puzzles: readonly Pick<PlayPuzzle, 'id' | 'requires' | 'lock_type' | 'is_exit'>[]
  interactables: readonly Pick<PlayInteractable, 'id' | 'label'>[]
}

/** The parts of a session state the line compares across one reply. */
export type FeedbackState = Pick<SessionState, 'locks_open' | 'inventory' | 'wrong_attempts' | 'order_buffer' | 'needs_item'>

/** `label` with a capital first letter, as a line starts: "Throw pillows. Not this one." */
export function capitalized(label: string): string {
  return label.charAt(0).toUpperCase() + label.slice(1)
}

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
 * The feedback line for the server's reply `after` to `input`, posted against `before` (story mode, owner decision
 * Oct 29): a newly open lock reads "Riddle {n} solved." (n = its riddle number, as the note numbers it), after "You pick
 * up the {label}." when it put an item in the pack, and the Exit reads "The way out is open." alone; a `use_on` that
 * opened nothing, a Wrong attempt or not, reads "That doesn't go there."; a code or order Wrong attempt reads the lock
 * outcome "Puzzle {n}: not this, {count}." (n = the Puzzle's fixed place in the Room); a `click` that changed nothing
 * reads "{Label}. Not this one.", "{Label}. Already in your pack." on an item the pack holds, "{label} · found" on
 * a target `found` holds (a solved `find` target no `use_on` needs), or "{Label}. It needs something from your pack."
 * when the reply says `needs_item`: the target of an open `use_on` lock reached with an empty hand (owner report,
 * Oct 30). A click that only fills an armed order sequence
 * (its Order click progress answers), the order controls and a Hint request read nothing. Pure: Node runs it as it
 * ships.
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
    const solved = fill(strings.riddleSolvedLine, { n: riddleNumber(room.puzzles, after.locks_open, opened.id) })
    const picked = after.inventory.find((id) => !before.inventory.includes(id))
    const item = picked === undefined ? undefined : label(picked)
    return item === undefined ? solved : `${fill(strings.pickUp, { label: item })} ${solved}`
  }
  if (input.type === 'lock_input' && input.input.type === 'use_on') return strings.doesntGoThere
  const wrong = room.puzzles.find((puzzle) => (after.wrong_attempts[puzzle.id] ?? 0) > (before.wrong_attempts[puzzle.id] ?? 0))
  if (wrong !== undefined) return fill(strings.lockNotThis, { n: place(wrong.id), count: after.wrong_attempts[wrong.id] })
  const target = named(input)
  const name = target === null ? undefined : label(target)
  if (target === null || name === undefined) return null
  if ((after.order_buffer.clicks ?? []).length > (before.order_buffer.clicks ?? []).length) return null
  if (after.inventory.includes(target)) return fill(strings.alreadyInPack, { Label: capitalized(name) })
  if (found.includes(target)) return fill(strings.found, { label: name })
  if (after.needs_item === true) return fill(strings.needsItem, { Label: capitalized(name) })
  return fill(strings.notThisOne, { Label: capitalized(name) })
}

/**
 * The sounds the server's reply `after` to `input` plays (owner request Oct 30, DESIGN.md Sound): a newly open lock
 * chimes, after the pop of an item it put in the pack, and the Exit plays nothing here (its fanfare plays on the way
 * out); an item picked up without a lock pops; a `use_on` that opened nothing, a Wrong attempt or a `click` that
 * changed nothing knocks. An order click mid-sequence, the order controls, a Hint request, an item already in the pack
 * and a found target play nothing. Pure, like the line.
 */
export function soundFor(
  room: FeedbackRoom,
  input: PostedEvent,
  before: FeedbackState,
  after: FeedbackState,
  found: readonly string[],
): Cue[] {
  const picked = after.inventory.some((id) => !before.inventory.includes(id)) ? (['pickUp'] as const) : []
  const opened = room.puzzles.findLast((puzzle) => after.locks_open.includes(puzzle.id) && !before.locks_open.includes(puzzle.id))
  if (opened !== undefined) return opened.is_exit ? [] : [...picked, 'solve']
  if (picked.length > 0) return [...picked]
  if (input.type === 'lock_input' && input.input.type === 'use_on') return ['knock']
  if (room.puzzles.some((puzzle) => (after.wrong_attempts[puzzle.id] ?? 0) > (before.wrong_attempts[puzzle.id] ?? 0))) return ['knock']
  const target = named(input)
  if (target === null || !room.interactables.some((interactable) => interactable.id === target)) return []
  if ((after.order_buffer.clicks ?? []).length > (before.order_buffer.clicks ?? []).length) return []
  return after.inventory.includes(target) || found.includes(target) ? [] : ['knock']
}
