import type { PlayView, PostedEvent, SessionState } from '../types'
import { getRoom, getSession, postEvent } from './api/index.ts'
import { inventory } from './components/inventory.ts'
import { wizardNotes } from './components/wizard-notes.ts'
import { mountScene } from './scene/index.ts'

/** The Play screen reads `GET /sessions/<id>` this often while it is open, hidden tab included (AD-4, UX-DR65). */
export const POLL_MS = 2000

/** The session as the Play screen's parts share it: the latest state the server sent, and the one way to post. */
export interface PlaySession {
  readonly id: string
  readonly roomId: string
  state: () => SessionState
  /** Posts one event (never stamped by the client); every part redraws from the server's reply. */
  post: (body: PostedEvent) => Promise<SessionState>
}

/**
 * The Play screen (FR-11): the Scene over the row of the Thumbnail strip and the Inventory, and the Wizard notes in
 * the side column, over the session's Room from `GET /rooms/<room_id>`. The client polls `GET /sessions/<id>` every
 * 2000 ms, from a worker so the cadence holds while the tab is hidden, and every part draws open locks, the
 * Inventory and Wrong attempts from the latest state the server sent: a poll or the reply to a posted event, never
 * its own clicks. A poll sent before a reply that arrived first is stale and dropped. Returns the teardown.
 */
export function mountPlay(sceneColumn: HTMLElement, sideColumn: HTMLElement, session: SessionState): () => void {
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

  const room: Promise<PlayView> = getRoom(session.room_id)
  const stripRow = document.createElement('div')
  stripRow.className = 'scene-strip-row'
  const unmountScene = mountScene(sceneColumn, stripRow, play, room)
  sceneColumn.append(stripRow)
  room
    .then((view) => {
      if (!mounted) return
      const held = inventory(view)
      const notes = wizardNotes(view)
      stripRow.append(held.element)
      sideColumn.append(notes.element)
      parts.push(held.render, notes.render)
      held.render(latest)
      notes.render(latest)
    })
    .catch(() => undefined) // the Scene keeps its loading line; the reconnecting state lands in 1.24

  return () => {
    mounted = false
    ticker.terminate()
    unmountScene()
    stripRow.remove()
    sideColumn.replaceChildren()
  }
}
