// One riddle at a time (story mode, owner decision Oct 29): the intro's lines, which riddle the note shows and its
// number, the seals, the place tag, the Riddler's solved line with the where-line for the next riddle, the chest's
// counts and the closing lines, all from served data (`PlayView`, `SessionState`) and never from a solution. Pure, so
// Node runs it.
import type { PlayPuzzle, PlayView } from '../types'
import { fill, strings } from './strings.ts'
import { areaOf, walkGraph } from './walk.ts'

/** The chest's hints for the whole Session; the server holds the count (`hints_left`), this only words it. */
export const CHEST_HINTS = 2

type Puzzles = readonly Pick<PlayPuzzle, 'id' | 'requires'>[]
type Room = Pick<PlayView, 'name' | 'photos' | 'puzzles' | 'story'>

/** A seal in the note's head row: a riddle solved, the one you are on, or one still to come. */
export type Seal = 'solved' | 'current' | 'waiting'

/**
 * The Puzzles whose prerequisites are all open, in Room order (`Room.puzzles[]`), the order the Active-puzzle fallback
 * follows (AD-4); open Puzzles keep their place, Puzzles with an unmet prerequisite are left out.
 */
export function availableInRoomOrder<P extends Pick<PlayPuzzle, 'requires'>>(puzzles: readonly P[], locksOpen: readonly string[]): P[] {
  return puzzles.filter((puzzle) => puzzle.requires.every((id) => locksOpen.includes(id)))
}

/** The n of "Riddle n of N": the Puzzle's place among the available ones; 0 for a Puzzle not available yet. */
export function riddleNumber(puzzles: Puzzles, locksOpen: readonly string[], id: string): number {
  return availableInRoomOrder(puzzles, locksOpen).findIndex((puzzle) => puzzle.id === id) + 1
}

/** "Riddle {n} of {N}", or "The way out · riddle {n} of {N}" on the Exit puzzle; N counts every Puzzle. */
export function riddleHeading(puzzles: readonly Pick<PlayPuzzle, 'id' | 'requires' | 'is_exit'>[], locksOpen: readonly string[], id: string): string {
  const values = { n: riddleNumber(puzzles, locksOpen, id), N: puzzles.length }
  return fill(puzzles.find((puzzle) => puzzle.id === id)?.is_exit === true ? strings.wayOutRiddle : strings.riddleOf, values)
}

/** One seal per Puzzle, by riddle number: solved once its lock is open, current for the active one, else waiting. */
export function seals(puzzles: Puzzles, locksOpen: readonly string[], active: string | null): Seal[] {
  const available = availableInRoomOrder(puzzles, locksOpen)
  return puzzles.map((_, k) => {
    const puzzle = available[k]
    if (puzzle !== undefined && locksOpen.includes(puzzle.id)) return 'solved'
    return puzzle !== undefined && puzzle.id === active ? 'current' : 'waiting'
  })
}

/** The area label of photo `photo`, "room" for a Room whose photos name none. */
export function areaLabel(room: Pick<PlayView, 'photos'>, photo: number): string {
  const areas = walkGraph(room.photos)
  return areas[areaOf(areas, photo)]?.label ?? areas[0]?.label ?? 'room'
}

function startArea(room: Room, id: string): string {
  return areaLabel(room, room.puzzles.find((puzzle) => puzzle.id === id)?.start_photo ?? 0)
}

/** "Waits in the {area}": the area of the riddle's start photo. */
export function placeTag(room: Room, id: string): string {
  return fill(strings.waitsIn, { area: startArea(room, id) })
}

/** The first riddle's where-line in the intro: "Start in the {area}." */
export function firstWhereLine(room: Room, id: string): string {
  return fill(strings.startIn, { area: startArea(room, id) })
}

/** The Room's area labels in the order of each one's first photo, joined "a, b and c"; "room" when none is named. */
export function joinedAreas(room: Pick<PlayView, 'photos'>): string {
  const labels = walkGraph(room.photos).map((area) => area.label)
  return labels.length > 1 ? `${labels.slice(0, -1).join(', ')} and ${labels.at(-1)}` : (labels[0] ?? 'room')
}

/** The five lines of the story intro (spec 3.1), one per beat. */
export interface IntroLines {
  welcome: string
  trap: string
  entrance: string
  guide: string
  /** The Riddler's last beat: where the first riddle waits, then its opening. */
  first: string
}

/**
 * The intro's lines for a Room whose first riddle is `first`: the Room's story when it has one, else the templates
 * filled from served data. A Demo room, the one with a name, is "someone's": the Architect welcomes a visitor there
 * (`architect_welcome_visitor`, the Demo template when the story has none) and thanks the player only in their own
 * Room. The first riddle's opening is the one the story wrote for it. A returning player's Greeting (`greeting`,
 * Local mode) takes the Guide's line.
 */
export function introLines(
  room: Room & Pick<PlayView, 'interactables'>,
  first: string,
  greeting: string | null,
): IntroLines {
  const story = room.story
  const counts = {
    areas: joinedAreas(room),
    photos: room.photos.length,
    things: room.interactables.filter((interactable) => (interactable.polygons ?? []).length > 0).length,
  }
  const opening = story?.riddles.find((riddle) => riddle.puzzle_id === first)?.opening ?? strings.riddleOpening
  return {
    welcome: room.name
      ? (story?.architect_welcome_visitor ?? fill(strings.introArchitectDemo, counts))
      : (story?.architect_welcome ?? fill(strings.introArchitect, counts)),
    trap: story?.trickster_trap ?? strings.introTrap,
    entrance: story?.riddler_entrance ?? fill(strings.introRiddler, { riddles: room.puzzles.length }),
    guide: greeting ?? story?.guide_chest ?? fill(strings.introGuide, { hints: CHEST_HINTS }),
    first: `${firstWhereLine(room, first)} ${opening}`,
  }
}

/**
 * The Riddler's reaction to a solved Puzzle: the Room's story line when it has one, else the line for its lock type;
 * a `find` whose solve put its target in the pack (`carried`, as the server's Inventory says) is kept for later.
 */
export function reaction(room: Room, id: string, carried: boolean): string {
  const told = room.story?.riddles.find((riddle) => riddle.puzzle_id === id)?.solved
  if (told !== undefined) return told
  const puzzle = room.puzzles.find((shown) => shown.id === id)
  if (puzzle === undefined || puzzle.is_exit) return strings.reactExit
  if (puzzle.lock_type === 'find') return carried ? strings.reactFindKept : strings.reactFind
  return { use_on: strings.reactUseOn, code: strings.reactCode, order: strings.reactOrder }[puzzle.lock_type]
}

/**
 * Where the next riddle waits, said from the photo you stand on (`here`): the way out; right here in your area; back
 * to an area an earlier solved riddle started in; else the next area. A `use_on` riddle adds "Bring what you're
 * carrying." while the pack holds something.
 */
export function whereLine(room: Room, next: string, here: number, locksOpen: readonly string[], carrying: boolean): string {
  const puzzle = room.puzzles.find((shown) => shown.id === next)
  const area = startArea(room, next)
  let line: string
  if (puzzle?.is_exit === true) line = fill(strings.whereExit, { area })
  else if (area === areaLabel(room, here)) line = fill(strings.whereHere, { area })
  else if (locksOpen.some((id) => startArea(room, id) === area)) line = fill(strings.whereBack, { area })
  else line = fill(strings.whereNext, { area })
  return puzzle?.lock_type === 'use_on' && carrying ? `${line} ${strings.bringCarrying}` : line
}

/** The solve beat's line: the reaction, then the where-line for `next`; the Exit (no next) reacts alone. */
export function solveLine(
  room: Room,
  solved: string,
  next: string | null,
  here: number,
  locksOpen: readonly string[],
  carried: boolean,
  carrying: boolean,
): string {
  const said = reaction(room, solved, carried)
  return next === null ? said : `${said} ${whereLine(room, next, here, locksOpen, carrying)}`
}

/** The chest's count under its name: "{k} hints for the whole house", "1 hint …" or "Empty". */
export function chestCount(hintsLeft: number): string {
  if (hintsLeft <= 0) return strings.chestEmpty
  return hintsLeft === 1 ? strings.chestOneHint : fill(strings.chestHints, { k: hintsLeft })
}

/** The chest's accessible name: "Treasure chest: {k} hints left", "… 1 hint left" or "… empty". */
export function chestName(hintsLeft: number): string {
  if (hintsLeft <= 0) return strings.chestNameEmpty
  return hintsLeft === 1 ? strings.chestNameOne : fill(strings.chestName, { k: hintsLeft })
}

/** The chest dialog's plain line for spending one of `hintsLeft` on riddle `n`. */
export function spendLine(hintsLeft: number, n: number): string {
  return hintsLeft === 1 ? fill(strings.spendOneHint, { n }) : fill(strings.spendHints, { k: hintsLeft, n })
}

const HINT_LABELS = [strings.hintNudge, strings.hintDirection, strings.hintNearAnswer]
const HINT_SAID = [strings.hintSaidNudge, strings.hintSaidDirection, strings.hintSaidNearAnswer]

/** "The Guide's hint · Nudge" (rung 1), "· Direction" (2) or "· Near-answer" (3). */
export function hintLabel(rung: number): string {
  return HINT_LABELS[rung - 1] ?? strings.hintNudge
}

/** What the live region reads for a bought hint: "The Guide's hint, nudge: {text}". */
export function hintAnnouncement(rung: number, text: string): string {
  return fill(HINT_SAID[rung - 1] ?? strings.hintSaidNudge, { text })
}

/** Each wizard's closing line: the Room's story when it has one, else the templates; the Guide's by hints spent. */
export function closingLines(room: Room, hintsSpent: number): { trickster: string; riddler: string; guide: string } {
  const story = room.story
  if (story !== null) {
    const guide = hintsSpent === 0 ? story.guide_closing_no_hints : story.guide_closing_hints
    return { trickster: story.trickster_closing, riddler: story.riddler_closing, guide }
  }
  const guide = hintsSpent === 0 ? strings.signOffNoHints : strings.signOffSomeHints
  return { trickster: strings.tricksterClosing, riddler: strings.riddlerClosing, guide }
}

/** The closing sheet's subline: "{Room.name or 'Your room'} · every riddle answered, the door open". */
export function escapedSubline(room: Pick<PlayView, 'name'>): string {
  return fill(strings.escapedSubline, { room: room.name || strings.yourRoom })
}
