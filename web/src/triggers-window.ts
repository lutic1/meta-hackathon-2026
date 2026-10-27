import type { SessionState } from '../types'
import { getRoom, getSession } from './api/index.ts'
import { type TriggersList, triggersList } from './components/triggers-panel.ts'
import { POLL_MS } from './play.ts'

/**
 * Cut 5's second window, `#/triggers/<session_id>` (FR-16, UX-DR84): the Triggers panel's header and rows for the
 * session, always open, reading `GET /sessions/<id>` every 2000 ms from a worker like the Play screen, so both windows
 * show the same rows for the same session. A missed poll keeps the rows it last drew. Returns the teardown.
 */
export function mountTriggersWindow(body: HTMLElement, session: SessionState): () => void {
  let mounted = true
  let latest = session
  let list: TriggersList | undefined
  const ticker = new Worker(new URL('./poll-ticker.ts', import.meta.url), { type: 'module' })
  ticker.onmessage = () => {
    getSession(session.id)
      .then((state) => {
        latest = state
        if (mounted) list?.render(state)
      })
      .catch(() => undefined)
  }
  ticker.postMessage(POLL_MS)
  getRoom(session.room_id)
    .then((room) => {
      if (!mounted) return
      list = triggersList(room)
      body.append(list.element)
      list.render(latest)
    })
    .catch(() => undefined) // the window stays empty; the Play screen still has its toggle

  return () => {
    mounted = false
    ticker.terminate()
    body.replaceChildren()
  }
}
