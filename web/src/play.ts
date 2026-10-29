import type { Meta, PlayView, PostedEvent, SessionState } from '../types'
import { getEffectiveRoom, getSession, postEvent, RequestFailed, startSession } from './api/index.ts'
import { cardLogButton, mountCardLog } from './card-log.ts'
import { secondaryButton, toggleButton } from './components/button.ts'
import { type HintArea, hintArea } from './components/hint-area.ts'
import { inventory } from './components/inventory.ts'
import { playEnded } from './components/play-ended.ts'
import { statusStrip } from './components/status-strip.ts'
import { triggersPanel } from './components/triggers-panel.ts'
import { OPEN_HOLD_MS, wizardNotes } from './components/wizard-notes.ts'
import { feedbackFor } from './feedback.ts'
import { mountLeaveRoom } from './leave-room.ts'
import { lockOpened } from './lock-opened.ts'
import { announce } from './live-region.ts'
import { sessionStart } from './profile/index.ts'
import { currentPlace, placeHref } from './router.ts'
import { type RoomGone, roomGone, showRoomGone } from './room-gone.ts'
import { foundTargets, lastShownPhoto, mountScene } from './scene/index.ts'
import { strings } from './strings.ts'
import { tricksterRequest } from './trickster-request.ts'
import { type UseOnSelection, useOnSelection } from './use-on.ts'
import { mountWelcome, playHasBegun } from './welcome.ts'

/** The Play screen reads `GET /sessions/<id>` this often while it is open, hidden tab included (AD-4, UX-DR65). */
export const POLL_MS = 2000

/** This many consecutive missed polls show the reconnecting state (UX-DR13). */
export const MISSES_TO_RECONNECT = 2

/** The session as the Play screen's parts share it: the latest state the server sent, and the one way to post. */
export interface PlaySession {
  readonly id: string
  readonly roomId: string
  state: () => SessionState
  /** Posts one event (never stamped by the client); every part redraws from the server's reply. */
  post: (body: PostedEvent) => Promise<SessionState>
  /** Draws `render` with every later state the server sends, a poll or a reply. */
  onState: (render: (state: SessionState) => void) => void
  /**
   * The Greeting or First-room welcome once its card has closed (or when play had already begun): the first Guide line
   * the Hint area shows, never announced again. null before "Begin" and for a session opened without an opening line.
   */
  openingLine: string | null
  /** The Inventory item a `use_on` is given with, selected or dragged: the Scene and the Inventory share it. */
  useOn: UseOnSelection
}

/**
 * What the Play screen takes from the shell: the page body and the top bar, which the First-room welcome covers and
 * holds inert, the top bar's controls slot, the `guide` setting the Hint area's thinking state follows, and the `mode`
 * that decides which Derived block "Start again" sends; the welcome card's role line follows both.
 */
export interface PlayFrame {
  body: HTMLElement
  topBar: HTMLElement
  controls: HTMLElement
  guide: Meta['guide']
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
 * is released (NFR-14); the class lives on the column, so it outlives a photo switch.
 */
function showAllToggle(sceneColumn: HTMLElement): HTMLButtonElement {
  return toggleButton({
    label: strings.showAllObjects,
    state: 'pressed',
    onToggle: (on) => sceneColumn.classList.toggle('is-showing-all', on),
  })
}

/**
 * The Play screen (FR-11): the Scene over the row of the Thumbnail strip and the Inventory, and the Wizard notes in
 * the side column, over the session's Effective room from `GET /sessions/<id>/room` (never `GET /rooms/<room_id>`),
 * whose revision is the `room_revision` of the state it mounted with. The client polls `GET /sessions/<id>` every
 * 2000 ms, from a worker so the cadence holds while the tab is hidden, and every part draws open locks, the
 * Inventory and Wrong attempts from the latest state the server sent: a poll or the reply to a posted event, never
 * its own clicks. A poll sent before a reply that arrived first is stale and dropped. A session opened with a
 * Greeting or a First-room welcome shows its card over the first Scene until "Begin", unless play has already begun;
 * a Greeting still being phrased (`opening_line.text` null) shows the Guide thinking until a polled state brings its
 * line. "Begin" keeps the line as the first Guide line of the Hint area, pinned under the Wizard notes, and moves
 * focus to the first Hotspot. The top bar's "Show all objects" toggle outlines every Hotspot while pressed, across
 * Scene changes. Each reply to a posted input reads one feedback line (`feedbackFor`, against the state it was sent
 * against), shown over the bottom edge of the Scene frame and written once to the live region as the Guide's: a click
 * that opens nothing, a pickup, a solved lock, the way out or a Wrong attempt. A state that shows a lock newly open
 * plays the unlock moment (`lockOpened`): the solved Hotspot blooms and the Scene frame glows once, the Solved chip
 * lifts in and the Guide speaks one aside for the lock type in the Hint area. A reload plays none of it for locks
 * already open. "How hints work" under the hint button says when the Guide offers a hint and why each Rung
 * arrived, in player words. "Leave room" in the top bar, or
 * the browser Back button, asks the Leave room confirmation (see `mountLeaveRoom`), never over the Greeting card;
 * confirming goes to `#/` in place of the Play route (`LeaveRoom.exit`, so Back never resumes the play-through) and
 * records no Room result. A state that shows a Trickster window open asks for its
 * proposal once (`tricksterRequest`), and the Card arrives in the Hint area through the poll. The top bar's "Card log"
 * button, between "Show all objects" and "Leave room", and the Hint area's "{n} more in the Card log" link open the
 * Card log (see `mountCardLog`), which lists every Card of `cards[]`; neither it nor the Leave room confirmation opens
 * over the other. A state whose
 * `room_revision` differs from the revision of the room last fetched (an accepted edit; a rejected or skipped Card
 * leaves it as it was) refetches `GET /sessions/<id>/room`, one request at a time, and redraws the Wizard notes and
 * the Hotspots from it without a reload: the open Scene, the Inventory and keyboard focus stay (FR-19, AD-12). Once a state
 * shows the Exit puzzle open, its "Solved" state (OPEN_HOLD_MS) ends and the client routes to `#/done/<session_id>`,
 * replacing the Play route and its Back guard in the history (`LeaveRoom.exit`); an Exit already open when the screen mounts has no Solved state, so it routes
 * at once.
 *
 * A reload mounts the same way from `GET /sessions/<id>` and the Effective room: the first Scene, the Inventory and the open
 * locks, with no welcome once play has begun and nothing announced. A poll that fails, or is still unanswered at the
 * next tick, is missed; after two in a row comes the reconnecting state: the status strip at the top of the Scene
 * column, the Scene frame shrunk by its height, the photo dimmed and every input inert, the line written to the live
 * region once. An input posted meanwhile never reached the server and is dropped (the Code field keeps its value);
 * the next state the server sends re-renders everything and removes the strip. A poll answered 404 ends the
 * play-through: the photo dims under the Session-gone line, whose "Start again" starts a new Session on the same
 * Room. A Room, or that start, answered 410 `room_deleted` or 404 `room_not_found`, or a poll answered 410
 * `room_deleted` (the Session went with its deleted Judge room), replaces the page body with the
 * Deleted Judge room notice or the unknown-room card (`showRoomGone`), focused on its heading. Returns the teardown.
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
  const stripRow = document.createElement('div')
  stripRow.className = 'scene-strip-row'
  const strip = statusStrip(strings.reconnectingPlay)
  let misses = 0
  let reconnecting = false
  /** The play-through ended or its Room is missing: nothing polls or takes input again. */
  let ended = false
  let unmountWelcome: (() => void) | undefined

  /** Every input inert, and the photo dimmed, while reconnecting or once the play-through has ended. */
  function holdInputs(): void {
    const held = reconnecting || ended
    const sceneFrame = stage.querySelector<HTMLElement>('.scene-frame')
    for (const element of [sceneFrame, stripRow, ...sideColumn.children]) if (element instanceof HTMLElement) element.inert = held
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
      const reply = await postEvent(session.id, body)
      replies += 1
      receive(reply)
      feedback?.(body, before, reply)
      return reply
    },
    onState: (render) => {
      parts.push(render)
    },
    openingLine: null,
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
    stage.append(playEnded(() => void startAgain()))
    holdInputs()
  }

  /** The Room is gone (410 `room_deleted` or 404 `room_not_found`): the page body holds only its card. */
  function roomMissing(gone: RoomGone): void {
    ended = true
    ticker.terminate()
    unmountWelcome?.()
    cardLog.unmount()
    leaveRoom.unmount()
    showRoomGone(frame.body, gone, frame.mode, currentPlace().profile)
  }

  let hints: HintArea | undefined
  let leaving: ReturnType<typeof setTimeout> | undefined
  function leaveOnExit(exitId: string, state: SessionState): void {
    if (leaving !== undefined || !state.locks_open.includes(exitId)) return
    const done = placeHref({ route: { name: 'done', sessionId: session.id }, profile: currentPlace().profile })
    leaving = setTimeout(() => leaveRoom.exit(done), session.locks_open.includes(exitId) ? 0 : OPEN_HOLD_MS)
  }

  let welcoming = false
  let unfocus: (() => void) | undefined
  const showAll = showAllToggle(sceneColumn)
  const room: Promise<PlayView> = getEffectiveRoom(session.id)
  const cardLog = mountCardLog({ body: frame.body, held: [frame.topBar, sceneColumn, sideColumn], room, play })
  const leaveRoom = mountLeaveRoom({
    body: frame.body,
    held: [frame.topBar, sceneColumn, sideColumn],
    modalOpen: () => welcoming || cardLog.isOpen(),
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
  sceneColumn.append(stage, stripRow)
  const scene = mountScene(stage, stripRow, play, room)
  room
    .then((view) => {
      if (!mounted) return
      const held = inventory(view, play.useOn)
      const notes = wizardNotes(view, play)
      /** The Effective room last fetched: the labels the feedback line names, a Decoy's included. */
      let shown = view
      feedback = (body, before, reply) => {
        const line = feedbackFor(shown, body, before, reply, foundTargets(session.id))
        if (!mounted || ended || line === null) return
        scene.say(line)
        announce(`${strings.speakerGuide} ${line}`)
      }
      /** Refetches the Effective room when `state` names another revision, then redraws the notes and Hotspots. */
      const refetchRoom = async (state: SessionState): Promise<void> => {
        if (refetching || state.room_revision === fetchedRevision) return
        refetching = true
        try {
          const next = await getEffectiveRoom(session.id)
          if (!mounted || ended) return
          fetchedRevision = state.room_revision
          shown = next
          scene.reshape(next)
          notes.reshape(next)
        } catch {
          return // the next state that names another revision asks again
        } finally {
          refetching = false
        }
        void refetchRoom(latest) // a later revision arrived while this one was fetched
      }
      stripRow.append(held.element)
      sideColumn.append(notes.element)
      parts.push(held.render, notes.render)
      held.render(latest)
      notes.render(latest)
      hints = hintArea(view, play, frame.guide, notes.openedRungs, cardLog.open, () => triggers.reveal())
      const area = hints
      const triggers = triggersPanel(view, latest, currentPlace().profile, (open) => area.triggersOpen(open))
      hints.triggers.append(triggers.element)
      sideColumn.append(hints.element)
      triggers.reveal() // opened on load with rows under a Disclosure: the newest row in view now the list can scroll
      holdInputs()
      parts.push(hints.render)
      parts.push(triggers.render)
      parts.push(lockOpened(view, latest, scene, hints))
      parts.push((state) => void refetchRoom(state))
      void refetchRoom(latest)
      const exit = view.puzzles.find((puzzle) => puzzle.is_exit)
      if (exit === undefined) return
      parts.push((state) => leaveOnExit(exit.id, state))
      leaveOnExit(exit.id, latest)
    })
    .catch((error: unknown) => {
      // Any other failure keeps the Scene's loading line.
      const gone = roomGone(error)
      if (mounted && gone !== null) roomMissing(gone)
    })

  const opening = session.opening_line
  if (opening !== null) {
    if (opening.text !== null && playHasBegun(session)) play.openingLine = opening.text
    else {
      welcoming = true
      const welcome = mountWelcome(session.id, frame.mode, frame.guide, opening, frame.body, [frame.topBar, sceneColumn, sideColumn], (line) => {
        welcoming = false
        play.openingLine = line
        hints?.opening(line)
        unfocus = focusFirstHotspot(sceneColumn)
      })
      unmountWelcome = welcome.close
      // A Greeting still being phrased: its line arrives with a later state the poll reads, phrased or the template.
      if (opening.text === null) parts.push((state) => {
        const line = state.opening_line?.text ?? null
        if (line !== null) welcome.arrive(line)
      })
    }
  }

  return () => {
    mounted = false
    unmountWelcome?.()
    cardLog.unmount()
    leaveRoom.unmount()
    unfocus?.()
    clearTimeout(leaving)
    ticker.terminate()
    play.useOn.dispose()
    showAll.remove()
    scene.unmount()
    stage.remove()
    stripRow.remove()
    sideColumn.replaceChildren()
  }
}

/**
 * The Play screen as it stands under the Completion sheet: the Scene on the photo it last showed in this page (the
 * first after a reload), the Thumbnail strip, the Inventory and the Wizard notes drawn once from `session` over its
 * Effective room (`GET /sessions/<id>/room`), and the "Show all objects" toggle, unpressed, the "Card log" button and
 * "Leave room" in the top bar's `controls`. It never polls and never posts; the shell holds both columns and the top
 * bar inert. A Room
 * answered 410 `room_deleted` or 404 `room_not_found` is handed to `onGone`. Returns the teardown and the Effective
 * room it drew, which the Completion sheet's filmstrip and shared line read too.
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
    openingLine: null,
    useOn: useOnSelection(),
  }
  const room: Promise<PlayView> = getEffectiveRoom(session.id)
  const stripRow = document.createElement('div')
  stripRow.className = 'scene-strip-row'
  const scene = mountScene(sceneColumn, stripRow, play, room, lastShownPhoto(session.id))
  sceneColumn.append(stripRow)
  room
    .then((view) => {
      if (!mounted) return
      const held = inventory(view, play.useOn)
      const notes = wizardNotes(view, play)
      stripRow.append(held.element)
      sideColumn.append(notes.element)
      held.render(session)
      notes.render(session)
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
    stripRow.remove()
    sideColumn.replaceChildren()
  }
  return { unmount, room }
}
