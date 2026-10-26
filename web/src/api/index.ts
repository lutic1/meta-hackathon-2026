// The HTTP client: every route under /api/ on the page's own origin (AD-9), typed by the generated web/types (AD-2).
import type { Meta, SessionState } from '../../types'

/** A request that got no answer, or an answer that was not a 2xx. */
export class RequestFailed extends Error {
  readonly status: number | null

  constructor(path: string, status: number | null) {
    super(`${path}: ${status ?? 'no answer'}`)
    this.status = status
  }
}

async function getJson<T>(path: string): Promise<T> {
  let response: Response
  try {
    response = await fetch(`/api${path}`, { headers: { Accept: 'application/json' } })
  } catch {
    throw new RequestFailed(path, null)
  }
  if (!response.ok) throw new RequestFailed(path, response.status)
  return (await response.json()) as T
}

/** `GET /meta` for the `?profile=` name in the URL (AD-14, AD-15). */
export function getMeta(profile: string): Promise<Meta> {
  return getJson<Meta>(`/meta?profile=${encodeURIComponent(profile)}`)
}

/** `GET /sessions/<id>`: the replayed state, with the Room's own `disclosure` list (AD-4, AD-15). */
export function getSession(sessionId: string): Promise<SessionState> {
  return getJson<SessionState>(`/sessions/${encodeURIComponent(sessionId)}`)
}
