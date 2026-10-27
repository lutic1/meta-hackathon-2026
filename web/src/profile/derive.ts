// The Derived block (FR-21, AD-8): recomputed from the non-demo Room results alone. Pure, so Node runs it as it ships.
import type { Derived, PuzzleResult, RoomResult } from '../../types'

/** The most Rungs a Puzzle has: Nudge, Direction, Near-answer. */
const MAX_RUNGS = 3

/** `Derived.fresh()`: the block of a profile with no non-demo Room result. */
export function freshDerived(): Derived {
  return { sessions: 0, persistence: 0, time_to_first_hint_s: null, mean_rung_per_lock_type: {} }
}

const clamp = (value: number, low: number, high: number): number => Math.min(high, Math.max(low, value))

const mean = (values: readonly number[]): number => values.reduce((sum, value) => sum + value, 0) / values.length

function median(values: readonly number[]): number | null {
  if (values.length === 0) return null
  const sorted = [...values].sort((a, b) => a - b)
  const middle = Math.floor(sorted.length / 2)
  return sorted.length % 2 === 1 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2
}

/**
 * A-19: +1 for a Puzzle solved after its nudge fired with no Hint request on it, -1 for a Puzzle with an Early ask,
 * 0 otherwise.
 */
function persistenceScore(puzzle: PuzzleResult): number {
  if (puzzle.early_ask) return -1
  return puzzle.solved && puzzle.nudge_fired && !puzzle.hint_requested ? 1 : 0
}

/**
 * The Derived block of `results`, demo-flagged ones ignored: `sessions` counts the rest; `time_to_first_hint_s` is the
 * median per-Puzzle time to first hint in seconds, null when no Puzzle got a hint; `mean_rung_per_lock_type` is the
 * mean Rungs used per Puzzle of each Lock type, 0 to 3; `persistence` is the A-19 mean, -1 to 1, 0 with no Puzzle.
 */
export function derive(results: readonly RoomResult[]): Derived {
  const counted = results.filter((result) => !result.demo)
  const puzzles = counted.flatMap((result) => result.puzzles)
  const hints = puzzles.flatMap((puzzle) => (puzzle.time_to_first_hint === null ? [] : [puzzle.time_to_first_hint / 1000]))
  const rungs = new Map<PuzzleResult['lock_type'], number[]>()
  for (const puzzle of puzzles) rungs.set(puzzle.lock_type, [...(rungs.get(puzzle.lock_type) ?? []), puzzle.rungs_used])
  return {
    sessions: counted.length,
    persistence: puzzles.length === 0 ? 0 : clamp(mean(puzzles.map(persistenceScore)), -1, 1),
    time_to_first_hint_s: median(hints),
    mean_rung_per_lock_type: Object.fromEntries([...rungs].map(([lockType, used]) => [lockType, clamp(mean(used), 0, MAX_RUNGS)])),
  }
}
