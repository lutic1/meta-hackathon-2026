// What the attract frame shows over each photo, read from the `PlayView` alone. A pure module with no DOM or CSS, so
// Node runs it as it ships under the tests.

import type { PlayInteractable, PlayPuzzle, PlayView } from '../../types'
import { hotspotPath } from '../scene/geometry.ts'

export interface AttractSlide {
  /** The photo's index in the Room. */
  photo: number
  /** The first scenery Interactable on the photo with a Hotspot to draw, null when it has none. */
  interactable: PlayInteractable | null
  /** The Puzzle whose clue shows with the photo, none of its Evidence on it; null when every Puzzle's is. */
  puzzle: PlayPuzzle | null
}

/**
 * What the frame shows over each photo of `view`, in the Room's photo order, giving away no lock's object or where it
 * lies. The lit Hotspot is the first Interactable on the photo whose polygons draw one and that no Evidence card
 * names (scenery), else none. The clue is a Puzzle's whose Evidence cards name nothing on the photo, a non-Exit one
 * while any is eligible, taken in turn after the previous photo's so successive photos show different clues; none
 * when every Puzzle's Evidence is on the photo.
 */
export function attractSlides(view: PlayView): AttractSlide[] {
  const named = new Set(view.puzzles.flatMap((puzzle) => puzzle.evidence_cards.map((card) => card.interactable)))
  let last = -1
  return view.photos.map((_, photo) => {
    const on = view.interactables.filter((interactable) => interactable.photo === photo)
    const interactable =
      on.find((candidate) => !named.has(candidate.id) && hotspotPath(candidate.polygons ?? []) !== '') ?? null
    const ids = new Set(on.map(({ id }) => id))
    const eligible = view.puzzles.filter((puzzle) => !puzzle.evidence_cards.some((card) => ids.has(card.interactable)))
    const locks = eligible.filter((puzzle) => !puzzle.is_exit)
    const choices = locks.length > 0 ? locks : eligible
    const puzzle = choices.find((choice) => view.puzzles.indexOf(choice) > last) ?? choices[0] ?? null
    if (puzzle !== null) last = view.puzzles.indexOf(puzzle)
    return { photo, interactable, puzzle }
  })
}
