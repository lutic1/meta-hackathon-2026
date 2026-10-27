import type { Meta, PlayView, PostedEvent, SessionState } from '../types'
import { getRoom, getSession, postEvent } from './api/index.ts'
import { inventory } from './components/inventory.ts'
import { OPEN_HOLD_MS, wizardNotes } from './components/wizard-notes.ts'
import { currentPlace, placeHref } from './router.ts'
import { lastShownPhoto, mountScene } from './scene/index.ts'
import { mountWelcome, playHasBegun } from './welcome.ts'

/** The Play screen reads `GET /sessions/<id>` this often while it is open, hidden tab included (AD-4, UX-DR65). */
export const POLL_MS = 2000

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
   * The First-room welcome once its card has closed (or when play had already begun): the first Guide line the Hint
   * area shows (3.4), never announced again. null before "Begin" and for a session opened without a welcome.
   */
  openingLine: string | null
}

/**
 * What the Play screen takes from the shell: the page body and the top bar, which the First-room welcome covers and
 * holds inert, and the `guide` setting its role line names.
 */
export interface PlayFrame {
  body: HTMLElement
  topBar: HTMLElement
  guide: Meta['guide']
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
 * The Play screen (FR-11): the Scene over the row of the Thumbnail strip and the Inventory, and the Wizard notes in
 * the side column, over the session's Room from `GET /rooms/<room_id>`. The client polls `GET /sessions/<id>` every
 * 2000 ms, from a worker so the cadence holds while the tab is hidden, and every part draws open locks, the
 * Inventory and Wrong attempts from the latest state the server sent: a poll or the reply to a posted event, never
 * its own clicks. A poll sent before a reply that arrived first is stale and dropped. A session opened with a
 * First-room welcome shows its card over the first Scene until "Begin", unless play has already begun; "Begin" keeps
 * the line for the Hint area and moves focus to the first Hotspot. Once a state shows the Exit puzzle open, its "Open"
 * state (OPEN_HOLD_MS) ends and the client routes to `#/done/<session_id>`, replacing the Play route in the history;
 * an Exit already open when the screen mounts has no Open state, so it routes at once. Returns the teardown.
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

  function receive(state: SessionState): void {
    if (!mounted) return
    latest = state
    for (const render of parts) render(state)
  }

  const play: PlaySession = {
    id: session.id,
    roomId: session.room_id,
    state: () => latest,
    post: async (body) => {
      const reply = await postEvent(session.id, body)
      replies += 1
      receive(reply)
      return reply
    },
    onState: (render) => {
      parts.push(render)
    },
    openingLine: null,
  }

  let polling = false
  async function poll(): Promise<void> {
    if (polling) return
    polling = true
    const before = replies
    try {
      const state = await getSession(session.id)
      if (before === replies) receive(state)
    } catch {
      // A missed poll changes nothing on screen; the reconnecting state lands in 1.24.
    } finally {
      polling = false
    }
  }
  const ticker = new Worker(new URL('./poll-ticker.ts', import.meta.url), { type: 'module' })
  ticker.onmessage = () => void poll()
  ticker.postMessage(POLL_MS)

  let leaving: ReturnType<typeof setTimeout> | undefined
  function leaveOnExit(exitId: string, state: SessionState): void {
    if (leaving !== undefined || !state.locks_open.includes(exitId)) return
    const done = placeHref({ route: { name: 'done', sessionId: session.id }, profile: currentPlace().profile })
    leaving = setTimeout(() => location.replace(done), session.locks_open.includes(exitId) ? 0 : OPEN_HOLD_MS)
  }

  const room: Promise<PlayView> = getRoom(session.room_id)
  const stripRow = document.createElement('div')
  stripRow.className = 'scene-strip-row'
  const unmountScene = mountScene(sceneColumn, stripRow, play, room)
  sceneColumn.append(stripRow)
  room
    .then((view) => {
      if (!mounted) return
      const held = inventory(view)
      const notes = wizardNotes(view, play)
      stripRow.append(held.element)
      sideColumn.append(notes.element)
      parts.push(held.render, notes.render)
      held.render(latest)
      notes.render(latest)
      const exit = view.puzzles.find((puzzle) => puzzle.is_exit)
      if (exit === undefined) return
      parts.push((state) => leaveOnExit(exit.id, state))
      leaveOnExit(exit.id, latest)
    })
    .catch(() => undefined) // the Scene keeps its loading line; the reconnecting state lands in 1.24

  let unmountWelcome: (() => void) | undefined
  let unfocus: (() => void) | undefined
  const welcome = session.opening_line
  if (welcome?.kind === 'welcome' && welcome.text !== null) {
    const line = welcome.text
    if (playHasBegun(session)) play.openingLine = line
    else {
      unmountWelcome = mountWelcome(session.id, frame.guide, line, frame.body, [frame.topBar, sceneColumn, sideColumn], () => {
        play.openingLine = line
        unfocus = focusFirstHotspot(sceneColumn)
      })
    }
  }

  return () => {
    mounted = false
    unmountWelcome?.()
    unfocus?.()
    clearTimeout(leaving)
    ticker.terminate()
    unmountScene()
    stripRow.remove()
    sideColumn.replaceChildren()
  }
}

/**
 * The Play screen as it stands under the Completion sheet: the Scene on the photo it last showed in this page (the
 * first after a reload), the Thumbnail strip, the Inventory and the Wizard notes drawn once from `session`. It never
 * polls and never posts; the shell holds both columns inert. Returns the teardown.
 */
export function mountPlayBehind(sceneColumn: HTMLElement, sideColumn: HTMLElement, session: SessionState): () => void {
  let mounted = true
  const play: PlaySession = {
    id: session.id,
    roomId: session.room_id,
    state: () => session,
    post: () => Promise.reject(new Error('the play-through is over')),
    onState: () => undefined,
    openingLine: null,
  }
  const room: Promise<PlayView> = getRoom(session.room_id)
  const stripRow = document.createElement('div')
  stripRow.className = 'scene-strip-row'
  const unmountScene = mountScene(sceneColumn, stripRow, play, room, lastShownPhoto(session.id))
  sceneColumn.append(stripRow)
  room
    .then((view) => {
      if (!mounted) return
      const held = inventory(view)
      const notes = wizardNotes(view, play)
      stripRow.append(held.element)
      sideColumn.append(notes.element)
      held.render(session)
      notes.render(session)
    })
    .catch(() => undefined) // the dimmed Scene keeps its loading line

  return () => {
    mounted = false
    unmountScene()
    stripRow.remove()
    sideColumn.replaceChildren()
  }
}
