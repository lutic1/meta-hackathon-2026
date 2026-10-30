import type { Meta, PlayPuzzle, PlayView, PostedEvent, SessionState } from '../types'
import { getEffectiveRoom, getSession, postEvent, RequestFailed, startSession } from './api/index.ts'
import { cardLogButton, mountCardLog } from './card-log.ts'
import { secondaryButton, toggleButton } from './components/button.ts'
import { inventory } from './components/inventory.ts'
import { playEnded } from './components/play-ended.ts'
import { riddleNote } from './components/riddle-note.ts'
import { statusStrip } from './components/status-strip.ts'
import { storyStage } from './components/story-stage.ts'
import { treasureChest } from './components/treasure-chest.ts'
import { stateFadeMs } from './fade.ts'
import { feedbackFor } from './feedback.ts'
import { mountLeaveRoom } from './leave-room.ts'
import { lockOpened, SOLVE_BEAT_DELAY_MS } from './lock-opened.ts'
import { announce } from './live-region.ts'
import { sessionStart } from './profile/index.ts'
import { riddleNumber, solveLine } from './riddles.ts'
import { currentPlace, placeHref } from './router.ts'
import { type RoomGone, roomGone, showRoomGone } from './room-gone.ts'
import { foundTargets, lastShownPhoto, type MountedScene, mountScene, solvedTargets } from './scene/index.ts'
import { introDue, introPhoto, playIntro } from './story.ts'
import { strings } from './strings.ts'
import { tricksterRequest } from './trickster-request.ts'
import { type UseOnSelection, useOnSelection } from './use-on.ts'

/** The Play screen reads `GET /sessions/<id>` this often while it is open, hidden tab included (AD-4, UX-DR65). */
export const POLL_MS = 2000

/** This many consecutive missed polls show the reconnecting state (UX-DR13). */
export const MISSES_TO_RECONNECT = 2

/** The story intro waits at most this long for the Scene's first photo; one that never loads holds it no longer. */
export const INTRO_PHOTO_WAIT_MS = 4000

/** The closing sheet rises this long into the way out (spec 5.6); at once under reduced motion. */
export const EXIT_SHEET_DELAY_MS = 900

/** The Sessions whose Exit opened on the Play screen in this page load; a reload or a new tab starts with none. */
const exited = new Set<string>()

/**
 * Whether Session `sessionId` ended on the Play screen in this page load, so its Completion screen followed the Exit
 * there; a Completion screen mounted any other way (a reload, a bookmark, history from an earlier page load) is a
 * reopened one.
 */
export function endedOnPlay(sessionId: string): boolean {
  return exited.has(sessionId)
}

/** The way out's Scene as it stands, with its stage and the Effective room it showed, for the closing sheet. */
interface ExitScene {
  sessionId: string
  stage: HTMLElement
  scene: MountedScene
  view: PlayView
}

/** The way out's Scene between the Play screen's teardown and the Completion screen that takes it. */
let exitScene: ExitScene | undefined

/**
 * Keeps `kept` for the Completion screen of its Session, which the shell mounts in the same task as the Play screen's
 * teardown; one not taken by then (another route, or the unreachable strip) is torn down.
 */
function keepExitScene(kept: ExitScene): void {
  exitScene = kept
  queueMicrotask(() => {
    if (exitScene !== kept) return
    exitScene = undefined
    kept.scene.unmount()
  })
}

/** The way out's Scene the Play screen kept for Session `sessionId`, taken once; undefined for any other. */
function takeExitScene(sessionId: string): ExitScene | undefined {
  if (exitScene?.sessionId !== sessionId) return undefined
  const kept = exitScene
  exitScene = undefined
  return kept
}

/** The session as the Play screen's parts share it: the latest state the server sent, and the one way to post. */
export interface PlaySession {
  readonly id: string
  readonly roomId: string
  state: () => SessionState
  /** Posts one event (never stamped by the client); every part redraws from the server's reply. */
  post: (body: PostedEvent) => Promise<SessionState>
  /** Draws `render` with every later state the server sends, a poll or a reply. */
  onState: (render: (state: SessionState) => void) => void
  /** The Inventory item a `use_on` is given with, selected or dragged: the Scene and the Inventory share it. */
  useOn: UseOnSelection
}

/**
 * What the Play screen takes from the shell: the page body and the top bar, which the story intro holds inert, the top
 * bar's controls slot, and the `mode` that decides which Derived block "Start again" sends.
 */
export interface PlayFrame {
  body: HTMLElement
  topBar: HTMLElement
  /** The top bar's wordmark, whose link to the start asks the Leave room confirmation first. */
  wordmark: HTMLAnchorElement
  controls: HTMLElement
  mode: Meta['mode']
}

/** Focuses the first Hotspot of the Scene in `sceneColumn`, once its photo is live. Returns the teardown. */
function focusFirstHotspot(sceneColumn: HTMLElement): () => void {
  const first = (): SVGElement | null => sceneColumn.querySelector<SVGElement>('.hotspot')
  const hotspot = first()
  if (hotspot !== null) {
    hotspot.focus()
    return () => undefined
  }
  const observer = new MutationObserver(() => {
    const live = first()
    if (live === null) return
    observer.disconnect()
    live.focus()
  })
  observer.observe(sceneColumn, { childList: true, subtree: true })
  return () => observer.disconnect()
}

/**
 * The top bar's "Show all objects" toggle: pressed, every Hotspot of every Scene in `sceneColumn` is outlined until it
 * is released (NFR-14); the class lives on the column, so it outlives a walk.
 */
function showAllToggle(sceneColumn: HTMLElement): HTMLButtonElement {
  return toggleButton({
    label: strings.showAllObjects,
    state: 'pressed',
    onToggle: (on) => sceneColumn.classList.toggle('is-showing-all', on),
  })
}

/** Pauses `ms`; at once for 0. */
const pause = (ms: number): Promise<void> => new Promise((done) => setTimeout(done, ms))


/**
 * The Play screen (FR-11; story mode, owner decision Oct 29): the Scene, walked around from the active riddle's start
 * photo, with the Riddle note pinned to the wall at its top left, "Your pack" on the floor left of the photo and the
 * Treasure chest right of it, over the session's Effective room from `GET /sessions/<id>/room` (never `GET
 * /rooms/<room_id>`), whose revision is the `room_revision` of the state it mounted with. The side column stays empty.
 * The client polls `GET /sessions/<id>` every 2000 ms, from a worker so the cadence holds while the tab is hidden, and
 * every part draws open locks, the pack, the hints left and Wrong attempts from the latest state the server sent: a
 * poll or the reply to a posted event, never its own clicks. A poll sent before a reply that arrived first is stale and
 * dropped. A Session that starts plays the story intro first (`playIntro`, once per Session: a reload of a Session in
 * progress skips it), from the first view of the first area once its photo is live (4 s at most), on the Story
 * stage with the Scene and the top bar inert and the note, the pack, the walk map, the turn discs and the doorway signs
 * out of sight; a returning player's Greeting (Local mode) is the Guide's line there, as far as the poll has brought
 * it. Play starts once the intro has ended (or at once), on the first riddle's start photo: focus goes to the note's
 * heading, and on the first riddle (no lock open yet) the coach pill shows for 15 s, until the first Hotspot click or
 * the chest opens, while the Trickster's bubble by the chest says the chest line once. The top bar's "Show all
 * objects" toggle outlines every Hotspot while pressed, across walks. Each reply to a posted input reads one feedback
 * line (`feedbackFor`, against the state it was sent against), shown at the photo's bottom and written once to the live
 * region as the Guide's.
 *
 * A state that shows a lock newly open plays the unlock moment (`lockOpened`): the solved Hotspot blooms and the Scene
 * frame glows once, the note stamps the riddle "Solved", and 1100 ms later the solve beat opens over the Scene (the
 * Story stage, light): the Riddler, the row "Riddle {n} solved" with its seal, his reaction and the where-line for the
 * next riddle, the item the solve put in the pack, and "Take me there", which takes focus (spec 3.3, 3.4). Pressing it
 * (or Enter) shows the next riddle on the note at once, walks to its start photo and puts focus on the note's heading.
 * On the Exit puzzle the beat's button is "Step outside": the door fills with daylight, the area grows toward it, and
 * 900 ms in the client routes to `#/done/<session_id>`, replacing the Play route and its Back guard in the history
 * (`LeaveRoom.exit`); the Session counts as ended in this page load (`endedOnPlay`), and the teardown keeps the Scene,
 * door lit, for the closing sheet (`mountPlayBehind`). An Exit already open when the screen mounts routes at once,
 * and its Completion screen is a reopened one. A reload plays no beat for locks already open and shows the active
 * riddle.
 *
 * "Leave room" in the top bar, the top bar's wordmark (a link to the start elsewhere), or the browser Back button, asks
 * the Leave room confirmation (see `mountLeaveRoom`), never during the intro; confirming goes to `#/` in place of
 * the Play route (`LeaveRoom.exit`, so Back never resumes the play-through) and records no Room result. A state that
 * shows a Trickster window open asks for its proposal once (`tricksterRequest`), and the Card arrives in the
 * Trickster's bubble by the chest through the poll. The top bar's "Card log" button, between "Show all objects" and
 * "Leave room", opens the Card log (see `mountCardLog`), which lists every Card of `cards[]` and how hints work; neither
 * it nor the Leave room confirmation opens over the other. A state whose `room_revision` differs from the revision of
 * the room last fetched (an accepted edit; a rejected or skipped Card leaves it as it was) refetches `GET
 * /sessions/<id>/room`, one request at a time, and redraws the note, the chest's numbers and the Hotspots from it
 * without a reload: the walk, the pack and keyboard focus stay (FR-19, AD-12).
 *
 * A reload mounts the same way from `GET /sessions/<id>` and the Effective room, with no intro once play has begun and
 * nothing announced. A poll that fails, or is still unanswered at the next tick, is missed; after two in a row comes
 * the reconnecting state: the status strip at the top of the Scene column, the Scene frame shrunk by its height, the
 * photo dimmed and every input inert, the line written to the live region once. An input posted meanwhile never reached
 * the server and is dropped (the Code field keeps its value); the next state the server sends re-renders everything
 * and removes the strip. A poll answered 404 ends the play-through: the photo dims under the Session-gone line, whose
 * "Start again" starts a new Session on the same Room. A Room, or that start, answered 410 `room_deleted` or 404
 * `room_not_found`, or a poll answered 410 `room_deleted` (the Session went with its deleted Judge room), replaces the
 * page body with the Deleted Judge room notice or the unknown-room card (`showRoomGone`), focused on its heading.
 * Returns the teardown.
 */
export function mountPlay(
  sceneColumn: HTMLElement,
  sideColumn: HTMLElement,
  session: SessionState,
  frame: PlayFrame,
): () => void {
  let mounted = true
  let latest = session
  let replies = 0
  const parts: ((state: SessionState) => void)[] = []
  /** Shows and announces the feedback line for one reply, once the Effective room is known. */
  let feedback: ((body: PostedEvent, before: SessionState, reply: SessionState) => void) | undefined
  /** The Scene frame and its reconnecting strip or ended state; the frame takes what the strip leaves. */
  const stage = document.createElement('div')
  stage.className = 'scene-stage'
  const strip = statusStrip(strings.reconnectingPlay)
  const beats = storyStage()
  let misses = 0
  let reconnecting = false
  /** The play-through ended or its Room is missing: nothing polls or takes input again. */
  let ended = false
  /** A beat holds the stage: the Scene, the note, the pack and the chest take no input under it. */
  let beating = false
  /** The story intro plays once per Session start; a reload of a Session in progress opens straight into play. */
  let introducing = introDue(session)

  /** Every input inert, and the photo dimmed, while reconnecting or once the play-through has ended; inert under a beat. */
  function holdInputs(): void {
    const held = reconnecting || ended
    const sceneFrame = stage.querySelector<HTMLElement>('.scene-frame')
    if (sceneFrame !== null) sceneFrame.inert = held || beating
    stage.classList.toggle('is-dimmed', held)
  }

  function missed(): void {
    misses += 1
    if (misses < MISSES_TO_RECONNECT || reconnecting || ended) return
    reconnecting = true
    stage.prepend(strip)
    holdInputs()
    announce(strings.reconnectingPlay)
  }

  function receive(state: SessionState): void {
    if (!mounted || ended) return
    misses = 0
    if (reconnecting) {
      reconnecting = false
      strip.remove()
      holdInputs()
    }
    latest = state
    for (const render of parts) render(state)
  }

  const play: PlaySession = {
    id: session.id,
    roomId: session.room_id,
    state: () => latest,
    post: async (body) => {
      const before = latest
      if (body.type === 'click') scene.coach(false) // the first Hotspot click: the player has the idea
      const reply = await postEvent(session.id, body)
      replies += 1
      receive(reply)
      feedback?.(body, before, reply)
      return reply
    },
    onState: (render) => {
      parts.push(render)
    },
    useOn: useOnSelection(),
  }

  parts.push(tricksterRequest(session.id, session))

  let polling = false
  async function poll(): Promise<void> {
    if (polling) return missed()
    polling = true
    const before = replies
    try {
      const state = await getSession(session.id)
      if (before === replies) receive(state)
    } catch (error) {
      if (error instanceof RequestFailed && error.status === 404) endPlay()
      else if (roomGone(error) === 'room_deleted') roomMissing('room_deleted')
      else missed()
    } finally {
      polling = false
    }
  }
  const ticker = new Worker(new URL('./poll-ticker.ts', import.meta.url), { type: 'module' })
  ticker.onmessage = () => void poll()
  ticker.postMessage(POLL_MS)

  let starting = false
  async function startAgain(): Promise<void> {
    if (starting) return
    starting = true
    try {
      const next = await startSession(await sessionStart(session.room_id, currentPlace().profile, frame.mode))
      location.hash = placeHref({ route: { name: 'play', sessionId: next.id }, profile: currentPlace().profile })
    } catch (error) {
      // Nothing started; "Start again" stays for another try, unless the Room itself is gone.
      const gone = roomGone(error)
      if (mounted && gone !== null) roomMissing(gone)
    } finally {
      starting = false
    }
  }

  /** The session is gone (404): the photo dims under the Session-gone line and "Start again". */
  function endPlay(): void {
    if (ended) return
    ended = true
    ticker.terminate()
    reconnecting = false
    strip.remove()
    beats.close()
    stage.append(playEnded(() => void startAgain()))
    holdInputs()
  }

  /** The Room is gone (410 `room_deleted` or 404 `room_not_found`): the page body holds only its card. */
  function roomMissing(gone: RoomGone): void {
    ended = true
    ticker.terminate()
    beats.close()
    cardLog.unmount()
    leaveRoom.unmount()
    showRoomGone(frame.body, gone, frame.mode, currentPlace().profile)
  }

  let leaving: ReturnType<typeof setTimeout> | undefined
  /** The Effective room the way out showed: once set, the teardown keeps the Scene for the closing sheet. */
  let exitView: PlayView | undefined
  /** To the Completion route, replacing the Play route; `after` ms in. */
  function leaveForDone(after: number): void {
    if (leaving !== undefined) return
    const done = placeHref({ route: { name: 'done', sessionId: session.id }, profile: currentPlace().profile })
    leaving = setTimeout(() => leaveRoom.exit(done), after)
  }

  let unfocus: (() => void) | undefined
  const showAll = showAllToggle(sceneColumn)
  const room: Promise<PlayView> = getEffectiveRoom(session.id)
  const cardLog = mountCardLog({ body: frame.body, held: [frame.topBar, sceneColumn, sideColumn], room, play })
  const leaveRoom = mountLeaveRoom({
    body: frame.body,
    held: [frame.topBar, sceneColumn, sideColumn],
    wordmark: frame.wordmark,
    modalOpen: () => introducing || cardLog.isOpen(),
    focusScene: () => {
      unfocus?.()
      // An inert Scene (reconnecting, or the play-through ended) takes no focus, so it stays in the top bar.
      if (reconnecting || ended) leaveRoom.button.focus()
      else unfocus = focusFirstHotspot(sceneColumn)
    },
    leave: () => leaveRoom.exit(placeHref({ route: { name: 'home' }, profile: currentPlace().profile })),
  })
  frame.controls.append(showAll, cardLog.button, leaveRoom.button)

  /** The `room_revision` of the Effective room last fetched: the mounting state's, as the first fetch follows it. */
  let fetchedRevision = session.room_revision
  let refetching = false
  sceneColumn.append(stage)
  frame.body.append(beats.element)
  // The intro opens on the first view of the first area; a reload, on the active riddle's start photo (story mode).
  const start = (view: PlayView): number =>
    introducing ? introPhoto(view) : (view.puzzles.find((puzzle) => puzzle.id === latest.active_puzzle_id)?.start_photo ?? 0)
  const scene: MountedScene = mountScene(stage, play, room, start)
  /** The intro holds the Scene and the top bar inert and keeps the play parts out of sight until play starts. */
  function holdForIntro(on: boolean): void {
    introducing = on
    beating = on
    frame.topBar.inert = on
    stage.classList.toggle('is-intro', on)
    holdInputs()
  }
  room
    .then((view) => {
      if (!mounted) return
      /** The Effective room last fetched: the labels the feedback line names, a Decoy's included. */
      let shown = view
      const speak = (line: string): void => {
        if (!mounted || ended) return
        scene.say(line)
        announce(`${strings.speakerGuide} ${line}`)
      }
      const held = inventory(view, play.useOn, speak)
      const note = riddleNote(view, play)
      const chest = treasureChest(view, play, note, () => scene.coach(false), speak)
      feedback = (body, before, reply) => {
        const line = feedbackFor(shown, body, before, reply, foundTargets(session.id))
        if (line !== null) speak(line)
      }
      /** Refetches the Effective room when `state` names another revision, then redraws the note and Hotspots. */
      const refetchRoom = async (state: SessionState): Promise<void> => {
        if (refetching || state.room_revision === fetchedRevision) return
        refetching = true
        try {
          const next = await getEffectiveRoom(session.id)
          if (!mounted || ended) return
          fetchedRevision = state.room_revision
          shown = next
          scene.reshape(next)
          note.reshape(next)
          chest.reshape(next)
        } catch {
          return // the next state that names another revision asks again
        } finally {
          refetching = false
        }
        void refetchRoom(latest) // a later revision arrived while this one was fetched
      }

      /** The beats wait their turn: two locks opening at once play one after the other. */
      let queue = Promise.resolve()
      /** The solve beat for `puzzle` (spec 3.3), then the walk to the next riddle or the way out. */
      async function solveBeat(puzzle: PlayPuzzle, before: SessionState, after: SessionState): Promise<void> {
        await pause(SOLVE_BEAT_DELAY_MS)
        if (!mounted || ended) return
        const picked = after.inventory.find((id) => !before.inventory.includes(id))
        const item = shown.interactables.find((interactable) => interactable.id === picked)
        const next = puzzle.is_exit ? null : latest.active_puzzle_id
        beating = true
        chest.shut()
        holdInputs()
        await beats.play({
          speaker: 'riddler',
          role: strings.roleRiddler,
          line: solveLine(shown, puzzle.id, next, scene.current(), after.locks_open, item !== undefined, latest.inventory.length > 0),
          button: puzzle.is_exit ? strings.stepOutside : strings.takeMeThere,
          solved: riddleNumber(shown.puzzles, after.locks_open, puzzle.id),
          item: item === undefined ? undefined : { roomId: shown.id, interactable: item },
        })
        beats.close()
        if (!mounted || ended) return
        if (puzzle.is_exit) return wayOut()
        beating = false
        holdInputs()
        note.release() // the note changes the moment you set off
        const target = shown.puzzles.find((candidate) => candidate.id === latest.active_puzzle_id)
        if (target !== undefined) await scene.walkTo(target.start_photo)
        if (mounted) note.focus()
      }
      /** The way out (spec 5.6): the door fills with daylight, then the closing sheet on the Completion route. */
      function wayOut(): void {
        exited.add(session.id)
        exitView = shown
        for (const part of [note.element, held.element, chest.element]) part.hidden = true
        void scene.daylight(solvedTargets(session.id).at(-1) ?? null)
        leaveForDone(stateFadeMs() === 0 ? 0 : EXIT_SHEET_DELAY_MS) // at once under reduced motion
      }

      scene.slots.note.append(note.element)
      scene.slots.floor.append(held.element, chest.element)
      parts.push(held.render, note.render, chest.render)
      held.render(latest)
      holdInputs()
      parts.push(
        lockOpened(() => shown, latest, scene, (puzzle, before, after) => {
          queue = queue.then(() => solveBeat(puzzle, before, after))
        }),
      )
      parts.push((state) => void refetchRoom(state))
      void refetchRoom(latest)
      const exit = view.puzzles.find((puzzle) => puzzle.is_exit)
      // An Exit already open when the screen mounted ended in an earlier page load: its Completion screen is reopened.
      if (exit !== undefined && latest.locks_open.includes(exit.id)) return leaveForDone(0)
      /** Play starts once the intro has ended, or at once without one. */
      async function begin(): Promise<void> {
        if (introducing) {
          holdForIntro(true)
          // Beat 1 waits for the first photo, which places the chest, so the box is fitted where the chest stands.
          await Promise.race([scene.live, pause(INTRO_PHOTO_WAIT_MS)])
          if (mounted && !ended) await playIntro({ view, state: () => latest, beats, scene, chest })
          beats.close()
          holdForIntro(false)
        }
        if (!mounted || ended) return
        note.focus()
        if (latest.locks_open.length > 0) return
        scene.coach(true)
        chest.bubble(strings.chestBubble)
      }
      void begin()
    })
    .catch((error: unknown) => {
      // Any other failure keeps the Scene's loading line.
      const gone = roomGone(error)
      if (mounted && gone !== null) roomMissing(gone)
    })

  return () => {
    mounted = false
    frame.topBar.inert = false
    cardLog.unmount()
    leaveRoom.unmount()
    unfocus?.()
    clearTimeout(leaving)
    ticker.terminate()
    play.useOn.dispose()
    showAll.remove()
    if (exitView !== undefined) keepExitScene({ sessionId: session.id, stage, scene, view: exitView })
    else {
      scene.unmount()
      stage.remove()
    }
    beats.close()
    beats.element.remove()
    sideColumn.replaceChildren()
  }
}

/**
 * The Play screen as it stands under the closing sheet: the Scene on the photo it last showed in this page (the first
 * after a reload) with its walls and walk map, the way out's door still in daylight (story mode, spec 1.10), drawn once
 * from `session` over its Effective room (`GET /sessions/<id>/room`), and the "Show all objects" toggle, unpressed, the
 * "Card log" button and "Leave room" in the top bar's `controls`. A Session whose Exit opened on the Play screen in
 * this page load keeps that screen's Scene as it stands and the Effective room it showed, so the exit photo never
 * leaves view and nothing is fetched again. It never polls and never posts; the shell holds the Scene column and the
 * top bar inert. A Room answered 410 `room_deleted` or 404 `room_not_found` is handed to `onGone`. Returns the
 * teardown and the Effective room it drew, which the closing sheet's lines, filmstrip and shared line read too.
 */
export function mountPlayBehind(
  sceneColumn: HTMLElement,
  sideColumn: HTMLElement,
  session: SessionState,
  controls: HTMLElement,
  onGone: (gone: RoomGone) => void,
): { unmount: () => void; room: Promise<PlayView> } {
  let mounted = true
  const showAll = showAllToggle(sceneColumn)
  const log = cardLogButton(() => undefined) // held inert with the bar, as is "Leave room"
  const leave = secondaryButton({ label: strings.leaveRoom, onActivate: () => undefined })
  controls.append(showAll, log, leave)
  const play: PlaySession = {
    id: session.id,
    roomId: session.room_id,
    state: () => session,
    post: () => Promise.reject(new Error('the play-through is over')),
    onState: () => undefined,
    useOn: useOnSelection(),
  }
  // An Exit opened on the Play screen in this page load: its Scene stays as it stands, the door still in daylight.
  const kept = takeExitScene(session.id)
  if (kept !== undefined) sceneColumn.append(kept.stage)
  const room: Promise<PlayView> = kept === undefined ? getEffectiveRoom(session.id) : Promise.resolve(kept.view)
  const scene = kept?.scene ?? mountScene(sceneColumn, play, room, () => lastShownPhoto(session.id))
  room
    .then((view) => {
      const exit = view.puzzles.find((puzzle) => puzzle.is_exit)
      // The door the way out opened stays lit.
      if (mounted && kept === undefined && exit !== undefined && session.locks_open.includes(exit.id)) {
        void scene.daylight(solvedTargets(session.id).at(-1) ?? null, true)
      }
    })
    .catch((error: unknown) => {
      // Any other failure: the dimmed Scene keeps its loading line.
      const gone = roomGone(error)
      if (mounted && gone !== null) onGone(gone)
    })

  const unmount = (): void => {
    mounted = false
    play.useOn.dispose()
    showAll.remove()
    log.remove()
    leave.remove()
    scene.unmount()
    kept?.stage.remove()
    sideColumn.replaceChildren()
  }
  return { unmount, room }
}
