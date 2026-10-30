// The story intro (story mode, owner decision Oct 29; build spec 1.1, 3.1, 5.5): five beats on the Story stage before
// play, once per Session start, and the walk and the trap that play under them.
import type { PlayView, SessionState } from '../types'
import type { StoryBeat, StoryStage } from './components/story-stage.ts'
import type { TreasureChest } from './components/treasure-chest.ts'
import { introLines, placeTag, riddleHeading } from './riddles.ts'
import type { MountedScene } from './scene/index.ts'
import { strings } from './strings.ts'
import { walkGraph } from './walk.ts'

const INTRO_KEY = 'kf.story.'

function introDoneHere(sessionId: string): boolean {
  try {
    return sessionStorage.getItem(INTRO_KEY + sessionId) === 'done'
  } catch {
    return false
  }
}

/** Records that the intro of Session `sessionId` ended (its last beat, or "Skip intro"), so a reload skips it. */
export function markIntroDone(sessionId: string): void {
  try {
    sessionStorage.setItem(INTRO_KEY + sessionId, 'done')
  } catch {
    // Storage refused: the session state alone tells a reload whether play has begun.
  }
}

/**
 * Whether the intro plays for `state`: not once it ended in this tab, nor once the state already carries play (an
 * open lock, a held item, a Wrong attempt, an armed order, a hint asked, a Rung or a Card), so a reload of a Session
 * in progress opens straight into play.
 */
export function introDue(state: SessionState): boolean {
  return !(
    introDoneHere(state.id) ||
    state.locks_open.length > 0 ||
    state.inventory.length > 0 ||
    Object.values(state.wrong_attempts).some((count) => count > 0) ||
    (state.order_buffer.puzzle_id ?? null) !== null ||
    state.rungs_used > 0 ||
    state.rung_changes.length > 0 ||
    state.cards.length > 0
  )
}

/** The photo the intro opens on: the first view of the first area. */
export function introPhoto(view: Pick<PlayView, 'photos'>): number {
  return walkGraph(view.photos)[0]?.ring[0] ?? 0
}

/** What the intro plays on: the Effective room, the latest state, the stage, the Scene and the chest it lights. */
export interface Intro {
  view: PlayView
  state: () => SessionState
  beats: StoryStage
  scene: Pick<MountedScene, 'walkTo' | 'lockSeal'>
  chest: Pick<TreasureChest, 'element' | 'button'>
}

/**
 * The story intro (spec 3.1): the Architect's welcome on the first view; the Trickster's trap, the Scene turning to the
 * way out's start photo, the lights flickering and the lock seal slamming on; the Riddler stepping in beside the dimmed
 * Trickster; the Guide, with the chest lit through the scrim (a returning player's Greeting in Local mode takes the
 * Guide's line); and the Riddler again, the seal lifted, walking to the first riddle's start photo and setting it under
 * his line, with "Start looking". The speech box stays clear of the chest on all five beats, in one place, so Next
 * never moves. Lines change at once while the Scene moves under them, walking without announcing its views (the
 * beat's line is what is said); a press during a move is held until it ends. "Skip intro" ends it at once, and the
 * Scene then walks on to the first riddle's start photo. Either way the seal is lifted and the intro is recorded as
 * done for the Session. Resolves then; the caller closes the stage.
 */
export async function playIntro({ view, state, beats, scene, chest }: Intro): Promise<void> {
  const shown = state()
  const first = view.puzzles.find((puzzle) => puzzle.id === shown.active_puzzle_id) ?? view.puzzles[0]
  const exit = view.puzzles.find((puzzle) => puzzle.is_exit) ?? first
  const lines = (): ReturnType<typeof introLines> => {
    const opening = state().opening_line
    return introLines(view, first.id, opening?.kind === 'greeting' ? opening.text : null)
  }
  const said = lines()
  let skipped = false
  const intro: { beat: StoryBeat; move?: () => Promise<void> }[] = [
    { beat: { speaker: 'architect', role: strings.roleArchitect, line: said.welcome, button: strings.next } },
    {
      beat: { speaker: 'trickster', cast: { right: 'trickster' }, role: strings.roleTrickster, line: said.trap, button: strings.next },
      move: async () => {
        await scene.walkTo(exit.start_photo, true)
        if (!skipped) scene.lockSeal(true)
      },
    },
    {
      beat: { speaker: 'riddler', cast: { left: 'riddler', right: 'trickster' }, role: strings.roleRiddler, line: said.entrance, button: strings.next },
    },
    { beat: { speaker: 'guide', role: strings.roleGuide, line: said.guide, button: strings.next, spot: chest.button } },
    {
      beat: {
        speaker: 'riddler',
        role: strings.roleRiddler,
        line: said.first,
        button: strings.startLooking,
        riddle: { heading: riddleHeading(view.puzzles, shown.locks_open, first.id), place: placeTag(view, first.id), clue: first.clue },
      },
      move: async () => {
        scene.lockSeal(false)
        await scene.walkTo(first.start_photo, true)
      },
    },
  ]

  for (const [at, { beat, move }] of intro.entries()) {
    if (beat.speaker === 'guide') beat.line = lines().guide // a Greeting phrased since the intro began
    chest.element.classList.toggle('is-beckoning', beat.spot !== undefined)
    if (beat.spot !== undefined) chest.element.classList.add('is-shown')
    const moved = move?.() ?? Promise.resolve()
    if ((await beats.play({ ...beat, page: { at, of: intro.length }, clear: chest.element })) === 'skip') {
      skipped = true
      break
    }
    await moved // a press during a move is held until it ends
  }
  chest.element.classList.remove('is-beckoning')
  scene.lockSeal(false)
  markIntroDone(shown.id)
  void scene.walkTo(first.start_photo) // after "Skip intro", from wherever the walk stands
}
