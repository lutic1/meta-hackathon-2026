import type { SessionState } from '../types'
import { postTrickster } from './api/index.ts'

/**
 * The Trickster request (AD-4, UX-DR65): when a session state shows `trickster_window` open at an index not yet
 * asked, posts `POST /sessions/<id>/trickster` exactly once for that window, with no visible pending state. A closed
 * or `pending` window, or a repeated state of a window already asked, posts nothing. The reply is not drawn: the Card
 * arrives through the polled state's `cards[]`. A request that never reached the server is not repeated; the server
 * answers a repeat with the unchanged state anyway. `first` is the state the Play screen mounts with, so a reload
 * inside an open window still asks once. Returns the part the Play screen draws every later state with.
 */
export function tricksterRequest(sessionId: string, first: SessionState): (state: SessionState) => void {
  let asked: number | null = null

  function render(state: SessionState): void {
    const { state: phase, index = null } = state.trickster_window
    if (phase !== 'open' || index === null || index === asked) return
    asked = index
    postTrickster(sessionId).catch(() => undefined)
  }

  render(first)
  return render
}
