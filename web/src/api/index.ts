// The HTTP client: every route under /api/ on the page's own origin (AD-9), typed by the generated web/types (AD-2).
import type {
  Derived,
  ErrorEnvelope,
  JobState,
  Meta,
  PlayView,
  PostedEvent,
  RoomSummary,
  SessionStart,
  SessionState,
} from '../../types'

/** A request that got no answer, or an answer that was not a 2xx, with the AD-13 envelope's `code` when it carried one. */
export class RequestFailed extends Error {
  readonly status: number | null
  readonly code: string | null

  constructor(path: string, status: number | null, code: string | null = null) {
    super(`${path}: ${status ?? 'no answer'}${code === null ? '' : ` ${code}`}`)
    this.status = status
    this.code = code
  }
}

/** The `error.code` of a refusal's envelope; null when the body is not one. */
async function errorCode(response: Response): Promise<string | null> {
  try {
    return ((await response.json()) as ErrorEnvelope).error.code
  } catch {
    return null
  }
}

/**
 * A GET, a POST of `body` as JSON, or a POST of a multipart `FormData` body (the browser writes its boundary);
 * the parsed JSON answer of a 2xx, else `RequestFailed`.
 */
async function requestJson<T>(path: string, body?: unknown): Promise<T> {
  const init: RequestInit =
    body === undefined
      ? { headers: { Accept: 'application/json' } }
      : body instanceof FormData
        ? { method: 'POST', headers: { Accept: 'application/json' }, body }
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
  if (!response.ok) throw new RequestFailed(path, response.status, await errorCode(response))
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

/** `GET /rooms/<room_id>`: the stored Room's `PlayView`, its photos in upload order (A-12) and its Interactables. */
export function getRoom(roomId: string): Promise<PlayView> {
  return getJson<PlayView>(`/rooms/${encodeURIComponent(roomId)}`)
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

/** One chosen photo as `POST /builds` takes it: the client-made downscale and the original, byte for byte. */
export interface UploadPhoto {
  downscale: Blob
  original: File
}

/** The multipart field names `POST /builds` pairs in upload order (src/api/app.py `DOWNSCALE`, `ORIGINAL`). */
const DOWNSCALE = 'downscale'
const ORIGINAL = 'original'

/** `POST /builds`: every photo's downscale with its original, in upload order, in one multipart body (AD-7). */
export function postBuild(photos: readonly UploadPhoto[]): Promise<JobState> {
  const body = new FormData()
  photos.forEach(({ downscale, original }, index) => {
    body.append(DOWNSCALE, downscale, `${index}.jpg`)
    body.append(ORIGINAL, original, original.name)
  })
  return postJson<JobState>('/builds', body)
}

/** `POST /sessions/<id>/events`: one posted event, never stamped by the client (the API stamps `t_ms`); the new state. */
export function postEvent(sessionId: string, body: PostedEvent): Promise<SessionState> {
  return postJson<SessionState>(`/sessions/${encodeURIComponent(sessionId)}/events`, body)
}
