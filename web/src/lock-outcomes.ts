import type { PlayView, SessionState } from '../types'
import { announce } from './live-region.ts'
import { fill, strings } from './strings.ts'

/**
 * Lock outcomes in the one polite live region (UX-DR70, an addition above the NFR-14 floor), read from the session
 * states the server sends and never from a click: each rise in a Puzzle's Wrong attempts is announced once as
 * "Puzzle {n}: not this, {count}." and each newly open lock once as "Puzzle {n}: open." (n = the Puzzle's fixed place
 * in the Room). `first` only sets what has been heard, so a reload announces nothing again; "Checking" never reaches
 * the region. Returns the renderer the Play screen registers for every later state.
 */
export function lockOutcomes(room: PlayView, first: SessionState): (state: SessionState) => void {
  let heard = first
  return (state) => {
    const lines = room.puzzles.flatMap((puzzle, place) => {
      const n = place + 1
      const count = state.wrong_attempts[puzzle.id] ?? 0
      const outcomes: string[] = []
      if (count > (heard.wrong_attempts[puzzle.id] ?? 0)) outcomes.push(fill(strings.lockNotThis, { n, count }))
      if (state.locks_open.includes(puzzle.id) && !heard.locks_open.includes(puzzle.id)) {
        outcomes.push(fill(strings.lockOpen, { n }))
      }
      return outcomes
    })
    heard = state
    if (lines.length > 0) announce(lines.join(' '))
  }
}
