import type { PlayPuzzle, PlayView, SessionState } from '../types'

/** What the unlock moment lights in the Scene: the frame, and the Hotspot of the target the last input named. */
export interface UnlockStage {
  /** The Interactable the latest `click` or `use_on` named: a `find`, `use_on` or `order` lock's solved target. */
  lastTarget: () => string | null
  /** Lights the Scene frame once and blooms the Hotspot of `target` with it, when it is on the shown photo. */
  bloom: (target: string | null) => void
}

/** The solve beat opens this long after the lock (spec 5.4): the bloom has played and the stamp is seen. */
export const SOLVE_BEAT_DELAY_MS = 1100

/**
 * The Hotspot that blooms for an opened Puzzle: the target the last click or `use_on` named for `find`, `use_on` and
 * `order` (the click that completed the sequence); none for `code`, whose lock is the frame itself.
 */
export function bloomTarget(puzzle: PlayPuzzle, lastTarget: string | null): string | null {
  return puzzle.lock_type === 'code' ? null : lastTarget
}

/**
 * The unlock moment (DESIGN.md Motion, EXPERIENCE.md Hotspot row), read from the session states the server sends and
 * never from a click: when a state shows a Puzzle newly open, its solved Hotspot blooms and the Scene frame glows once
 * (`stage`), and the moment hands over to the solve beat (story mode, spec 1.9): `onOpened` hears the opened Puzzle
 * with the states before and after it. A Wrong attempt opens nothing: the feedback line says it. `first` only sets what
 * has been seen, so a reload blooms nothing and plays no beat for locks already open. Returns the renderer the Play
 * screen registers for every later state.
 */
export function lockOpened(
  room: () => PlayView,
  first: SessionState,
  stage: UnlockStage,
  onOpened: (puzzle: PlayPuzzle, before: SessionState, after: SessionState) => void,
): (state: SessionState) => void {
  let seen = first
  return (state) => {
    const before = seen
    const opened = room().puzzles.filter((puzzle) => state.locks_open.includes(puzzle.id) && !before.locks_open.includes(puzzle.id))
    seen = state
    const last = opened.at(-1)
    if (last === undefined) return
    stage.bloom(bloomTarget(last, stage.lastTarget()))
    onOpened(last, before, state)
  }
}
