// The HTTP client: every route under /api/ on the page's own origin (AD-9), typed by the generated web/types (AD-2).
import type {
  AccessCheck,
  BuildView,
  ErrorDetail,
  ErrorEnvelope,
  JobState,
  Meta,
  PlayView,
  PostedEvent,
  Profile,
  RoomResult,
  RoomSummary,
  SessionStart,
  SessionState,
} from '../../types'

/**
 * A request that got no answer, or an answer that was not a 2xx, with the AD-13 envelope's `code` when it carried
 * one, and the job `status` that only `build_not_ready` carries.
 */
export class RequestFailed extends Error {
  readonly status: number | null
  readonly code: string | null
  readonly jobStatus: JobState['status'] | null

  constructor(path: string, status: number | null, detail: ErrorDetail | null = null) {
    const code = detail?.code ?? null
    super(`${path}: ${status ?? 'no answer'}${code === null ? '' : ` ${code}`}`)
    this.status = status
    this.code = code
    this.jobStatus = detail?.status ?? null
  }
}

/** The `error` of a refusal's envelope; null when the body is not one. */
async function errorDetail(response: Response): Promise<ErrorDetail | null> {
  try {
    return ((await response.json()) as ErrorEnvelope).error ?? null
  } catch {
    return null
  }
}

/**
 * A GET, a POST of a multipart `FormData` body (the browser writes its boundary), or a `method` (POST unless named) of a
 * `Blob` sent byte for byte as JSON (a chosen file) or of anything else as JSON, each with any extra `headers`; the
 * parsed JSON answer of a 2xx, else `RequestFailed`.
 */
async function requestJson<T>(
  path: string,
  body?: unknown,
  method: 'POST' | 'PUT' = 'POST',
  headers: Record<string, string> = {},
): Promise<T> {
  const json = { Accept: 'application/json', 'Content-Type': 'application/json', ...headers }
  const init: RequestInit =
    body === undefined
      ? { headers: { Accept: 'application/json', ...headers } }
      : body instanceof FormData
        ? { method: 'POST', headers: { Accept: 'application/json', ...headers }, body }
        : body instanceof Blob
          ? { method, headers: json, body }
          : { method, headers: json, body: JSON.stringify(body) }
  let response: Response
  try {
    response = await fetch(`/api${path}`, init)
  } catch {
    throw new RequestFailed(path, null)
  }
  if (!response.ok) throw new RequestFailed(path, response.status, await errorDetail(response))
  return (await response.json()) as T
}

const getJson = <T>(path: string): Promise<T> => requestJson<T>(path)
const postJson = <T>(path: string, body: unknown): Promise<T> => requestJson<T>(path, body)
const putJson = <T>(path: string, body: unknown): Promise<T> => requestJson<T>(path, body, 'PUT')

/** `GET /meta` for the `?profile=` name in the URL (AD-14, AD-15). */
export function getMeta(profile: string): Promise<Meta> {
  return getJson<Meta>(`/meta?profile=${encodeURIComponent(profile)}`)
}

/** `GET /sessions/<id>`: the replayed state, with the Room's own `disclosure` list (AD-4, AD-15). */
export function getSession(sessionId: string): Promise<SessionState> {
  return getJson<SessionState>(`/sessions/${encodeURIComponent(sessionId)}`)
}

/** `GET /sessions/<id>/result`: the `RoomResult` the server computes from the session's Event log (AD-4). */
export function getResult(sessionId: string): Promise<RoomResult> {
  return getJson<RoomResult>(`/sessions/${encodeURIComponent(sessionId)}/result`)
}

/** `GET /builds/<job_id>/view`: the solution-free `BuildView` of a `done` Build, open in both modes (AD-3). */
export function getBuildView(jobId: string): Promise<BuildView> {
  return getJson<BuildView>(`/builds/${encodeURIComponent(jobId)}/view`)
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

/**
 * `POST /sessions {room_id, derived}`: a fresh session over the stored Room, opened with its opening line (AD-4); the
 * body is web/profile's `sessionStart`, so nothing else from the Player profile is ever sent (AD-8).
 */
export function startSession(body: SessionStart): Promise<SessionState> {
  return postJson<SessionState>('/sessions', body)
}

/** `GET /builds/<job_id>`: the persisted job state (202 while `queued` or `running`, 200 once terminal), never a Room. */
export function getBuild(jobId: string): Promise<JobState> {
  return getJson<JobState>(`/builds/${encodeURIComponent(jobId)}`)
}

/** One chosen photo as `POST /builds` takes it: the client-made downscale and the original, byte for byte. */
export interface UploadPhoto {
  downscale: Blob
  original: File
}

/** The multipart field names `POST /builds` pairs in upload order (src/api/app.py `DOWNSCALE`, `ORIGINAL`). */
const DOWNSCALE = 'downscale'
const ORIGINAL = 'original'

/** The header Hosted mode's guarded routes read the Access code from (src/api/wiring.py `ACCESS_HEADER`, AD-9). */
const ACCESS_HEADER = 'X-Access-Code'

/**
 * `POST /builds`: every photo's downscale with its original, in upload order, in one multipart body (AD-7), with
 * the Access code this tab holds as `X-Access-Code` (Hosted mode); with no code held (Local mode) no header is sent.
 */
export function postBuild(photos: readonly UploadPhoto[], accessCode: string | null): Promise<JobState> {
  const body = new FormData()
  photos.forEach(({ downscale, original }, index) => {
    body.append(DOWNSCALE, downscale, `${index}.jpg`)
    body.append(ORIGINAL, original, original.name)
  })
  return requestJson<JobState>('/builds', body, 'POST', accessCode === null ? {} : { [ACCESS_HEADER]: accessCode })
}

/**
 * `POST /access/check {code}` (Hosted only, AD-9): `{ok, builds_left}` before any photo is chosen, starting no Build;
 * a wrong code answers 200 `{ok: false, builds_left: null}`, and too many attempts 429 `too_many_attempts`.
 */
export function checkAccess(code: string): Promise<AccessCheck> {
  return postJson<AccessCheck>('/access/check', { code })
}

/** `POST /sessions/<id>/events`: one posted event, never stamped by the client (the API stamps `t_ms`); the new state. */
export function postEvent(sessionId: string, body: PostedEvent): Promise<SessionState> {
  return postJson<SessionState>(`/sessions/${encodeURIComponent(sessionId)}/events`, body)
}

/** `GET /profile/<name>` (Local mode, cut 2 only): the profile file `rooms/profiles/<name>.json`; 404 when there is none. */
export function getProfile(name: string): Promise<Profile> {
  return getJson<Profile>(`/profile/${encodeURIComponent(name)}`)
}

/**
 * `PUT /profile/<name>` (Local mode, cut 2 only): writes the whole profile file, from web/profile's `Profile` or a
 * chosen file's bytes as they are; a body that does not parse or is out of bounds is refused with 422, the file
 * unchanged.
 */
export function putProfile(name: string, body: Profile | Blob): Promise<Profile> {
  return putJson<Profile>(`/profile/${encodeURIComponent(name)}`, body)
}

/**
 * `POST /sessions/<id>/trickster`: asks for the open Trickster window's proposal, which the server judges and logs as
 * a card (AD-4, AD-12); outside an open window it answers the unchanged state. The body is an empty object.
 */
export function postTrickster(sessionId: string): Promise<SessionState> {
  return postJson<SessionState>(`/sessions/${encodeURIComponent(sessionId)}/trickster`, {})
}
