// The HTTP client: every route under /api/ on the page's own origin (AD-9), typed by the generated web/types (AD-2).
import type { Derived, Meta, RoomSummary, SessionStart, SessionState } from '../../types'

/** A request that got no answer, or an answer that was not a 2xx. */
export class RequestFailed extends Error {
  readonly status: number | null

  constructor(path: string, status: number | null) {
    super(`${path}: ${status ?? 'no answer'}`)
    this.status = status
  }
}

/** A GET, or a POST of `body` as JSON when one is given; the parsed JSON answer of a 2xx, else `RequestFailed`. */
async function requestJson<T>(path: string, body?: unknown): Promise<T> {
  const init: RequestInit =
    body === undefined
      ? { headers: { Accept: 'application/json' } }
      : {
          method: 'POST',
          headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        }
  let response: Response
  try {
    response = await fetch(`/api${path}`, init)
  } catch {
    throw new RequestFailed(path, null)
  }
  if (!response.ok) throw new RequestFailed(path, response.status)
  return (await response.json()) as T
}

const getJson = <T>(path: string): Promise<T> => requestJson<T>(path)
const postJson = <T>(path: string, body: unknown): Promise<T> => requestJson<T>(path, body)

/** `GET /meta` for the `?profile=` name in the URL (AD-14, AD-15). */
export function getMeta(profile: string): Promise<Meta> {
  return getJson<Meta>(`/meta?profile=${encodeURIComponent(profile)}`)
}

/** `GET /sessions/<id>`: the replayed state, with the Room's own `disclosure` list (AD-4, AD-15). */
export function getSession(sessionId: string): Promise<SessionState> {
  return getJson<SessionState>(`/sessions/${encodeURIComponent(sessionId)}`)
}

/** `GET /rooms`: one `RoomSummary` per stored Room, newest build first (AD-9); the browser keeps no list of its own. */
export function listRooms(): Promise<RoomSummary[]> {
  return getJson<RoomSummary[]>('/rooms')
}

/** The URL of photo `index` of a stored Room: its downscaled JPEG. */
export function photoUrl(roomId: string, index: number): string {
  return `/api/rooms/${encodeURIComponent(roomId)}/photos/${index}`
}

/** `Derived.fresh()` (AD-8): the block a session start carries when no profile exists. */
export function freshDerived(): Derived {
  return { sessions: 0, persistence: 0, time_to_first_hint_s: null, mean_rung_per_lock_type: {} }
}

/** `POST /sessions {room_id, derived}`: a fresh session over the stored Room, opened with its opening line (AD-4). */
export function startSession(body: SessionStart): Promise<SessionState> {
  return postJson<SessionState>('/sessions', body)
}
