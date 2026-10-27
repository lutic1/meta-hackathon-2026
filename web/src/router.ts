// Hash routes (UX-DR8): `#/`, `#/build/<job_id>`, `#/build/<job_id>/view`, `#/play/<session_id>` and
// `#/done/<session_id>`, each carrying
// `?profile=` (AD-14).

export type Route =
  | { name: 'home' }
  | { name: 'build'; jobId: string }
  | { name: 'view'; jobId: string }
  | { name: 'play'; sessionId: string }
  | { name: 'done'; sessionId: string }

export interface Place {
  route: Route
  profile: string
}

export const DEFAULT_PROFILE = 'dev'

const SESSION_ROUTE = /^\/(play|done)\/([\w-]+)$/ // session ids are `sess_` plus a ULID
const BUILD_ROUTE = /^\/build\/([\w-]+)$/ // job ids are `job_` plus a ULID
const BUILD_VIEW_ROUTE = /^\/build\/([\w-]+)\/view$/ // job ids are `job_` plus a ULID

/**
 * The route and profile in a URL's hash (`#/play/sess_…?profile=demo`); `?profile=` before the hash also counts,
 * and a hash without one keeps `carried`, the profile of the route before it.
 */
export function parsePlace(hash: string, search: string, carried = DEFAULT_PROFILE): Place {
  const [path, query = ''] = hash.replace(/^#/, '').split('?', 2)
  const profile = new URLSearchParams(query).get('profile') || new URLSearchParams(search).get('profile') || carried
  const build = BUILD_ROUTE.exec(path)
  if (build !== null) return { route: { name: 'build', jobId: build[1] }, profile }
  const view = BUILD_VIEW_ROUTE.exec(path)
  if (view !== null) return { route: { name: 'view', jobId: view[1] }, profile }
  const match = SESSION_ROUTE.exec(path)
  if (match === null) return { route: { name: 'home' }, profile }
  const sessionId = match[2]
  return { route: match[1] === 'play' ? { name: 'play', sessionId } : { name: 'done', sessionId }, profile }
}

/** The hash for `place`, always carrying its profile. */
export function placeHref({ route, profile }: Place): string {
  const path =
    route.name === 'home'
      ? '/'
      : route.name === 'view' ? `/build/${route.jobId}/view`
      : `/${route.name}/${route.name === 'build' ? route.jobId : route.sessionId}`
  return `#${path}?profile=${encodeURIComponent(profile)}`
}

/** The hash of a Build's Capture screen, `#/build/<job_id>`, carrying the profile. */
export function captureHref(jobId: string, profile: string): string {
  return `#/build/${jobId}?profile=${encodeURIComponent(profile)}`
}

let carried = DEFAULT_PROFILE

/** The current place; rewrites the URL in place when it lacks the canonical hash, so the profile rides on every route. */
export function currentPlace(): Place {
  const place = parsePlace(location.hash, location.search, carried)
  carried = place.profile
  const href = placeHref(place)
  if (location.hash !== href) history.replaceState(history.state, '', href)
  return place
}
