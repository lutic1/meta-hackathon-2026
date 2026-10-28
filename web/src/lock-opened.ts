import type { PlayPuzzle, PlayView, SessionState } from '../types'
import { strings } from './strings.ts'

/** What the unlock moment lights in the Scene: the frame, and the Hotspot of the target the last input named. */
export interface UnlockStage {
  /** The Interactable the latest `click` or `use_on` named: a `find`, `use_on` or `order` lock's solved target. */
  lastTarget: () => string | null
  /** Lights the Scene frame once and blooms the Hotspot of `target` with it, when it is on the shown photo. */
  bloom: (target: string | null) => void
}

/** Where the Guide speaks: the Hint area's aside, and its Wrong attempt line with the ring's glow. */
export interface UnlockVoice {
  aside: (line: string) => void
  notThat: () => void
}

const ASIDES: Record<PlayPuzzle['lock_type'], string> = {
  find: strings.asideFind,
  code: strings.asideCode,
  order: strings.asideOrder,
  use_on: strings.asideUseOn,
}

/** The Guide's aside for an opened Puzzle: the exit's line for the Exit puzzle, else its lock type's. */
export function asideFor(puzzle: PlayPuzzle): string {
  if (puzzle.is_exit) return strings.asideExit
  return ASIDES[puzzle.lock_type]
}

/**
 * The Hotspot that blooms for an opened Puzzle: the target the last click or `use_on` named for `find`, `use_on` and
 * `order` (the click that completed the sequence); none for `code`, whose lock is the frame itself.
 */
export function bloomTarget(puzzle: PlayPuzzle, lastTarget: string | null): string | null {
  return puzzle.lock_type === 'code' ? null : lastTarget
}

/**
 * The unlock moment (DESIGN.md Motion, EXPERIENCE.md Hotspot and Hint area rows), read from the session states the
 * server sends and never from a click: when a state shows a Puzzle newly open, its solved Hotspot blooms and the
 * Scene frame glows once (`stage`) and the Guide speaks one aside for its lock type (`voice`), the exit's line for the
 * Exit puzzle; the Wizard notes lift the Open chip in on their own draw. When a state instead shows a Puzzle's Wrong
 * attempts risen, the Guide's ring glows once with the Wrong attempt line, once per attempt. The asides are
 * client-side presentation: not Rungs, not counted, not logged, not announced (the lock outcome already is) and never
 * naming a solution, so a Rung the same state carries wins the Hint area and neither aside is spoken; the Scene still
 * blooms. `first` only sets what has been seen, so a reload blooms and says nothing for locks already open. Returns
 * the renderer the Play screen registers for every later state.
 */
export function lockOpened(room: PlayView, first: SessionState, stage: UnlockStage, voice: UnlockVoice): (state: SessionState) => void {
  let seen = first
  return (state) => {
    const opened = room.puzzles.filter(
      (puzzle) => state.locks_open.includes(puzzle.id) && !seen.locks_open.includes(puzzle.id),
    )
    const wrong = room.puzzles.some(
      (puzzle) => (state.wrong_attempts[puzzle.id] ?? 0) > (seen.wrong_attempts[puzzle.id] ?? 0),
    )
    const rung = state.rung_changes.length > seen.rung_changes.length
    seen = state
    const last = opened.at(-1)
    if (last !== undefined) stage.bloom(bloomTarget(last, stage.lastTarget()))
    if (rung) return
    if (last !== undefined) voice.aside(asideFor(last))
    else if (wrong) voice.notThat()
  }
}
