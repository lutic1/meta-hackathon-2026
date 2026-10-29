import './shell.css'
import type { Meta, RoomSummary, SessionState } from '../types'
import { getMeta, getSession, listRooms, RequestFailed } from './api/index.ts'
import { judgeBuildsLeft } from './access-code.ts'
import { requestCapture, takeCaptureRequest } from './build-photos.ts'
import { buildScreen } from './build-progress.ts'
import { type BuildViewOptions, type BuildViewState, buildViewSurface, loadBuildView } from './build-view.ts'
import { captureScreen } from './capture.ts'
import { mountCompletion } from './completion.ts'
import { mountTimer, type TimerRun } from './capture-timer.ts'
import { disclosureBanner } from './components/disclosure-banner.ts'
import { narrowScreenMessage } from './components/narrow-screen-message.ts'
import { playEnded } from './components/play-ended.ts'
import { statusStrip } from './components/status-strip.ts'
import { type TopBar, topBar } from './components/top-bar.ts'
import { hostedLanding } from './landing.ts'
import { liveRegion } from './live-region.ts'
import { currentPlace, placeHref, type Route } from './router.ts'
import { mountPlay } from './play.ts'
import { roomGone, showRoomGone } from './room-gone.ts'
import { getResults, watchResults } from './profile/index.ts'
import { mountTriggersWindow } from './triggers-window.ts'
import { strings } from './strings.ts'

/** How long the server-unreachable state waits between attempts (UX-DR61). */
export const RETRY_MS = 2000

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms))

/**
 * null for a 4xx: the server answered and refused, so there is nothing to retry and no Room to disclose;
 * `room_deleted` when the refusal is a 410 for a Session its Judge room's deletion took.
 */
function refused(error: unknown): 'room_deleted' | null {
  if (roomGone(error) === 'room_deleted') return 'room_deleted'
  if (error instanceof RequestFailed && error.status !== null && error.status < 500) return null
  throw error
}

/**
 * The app shell (UX-DR7): the top bar, the body for the current route and the Disclosure banner, the footer strip
 * under the body.
 *
 * Nothing renders until `GET /meta` answers, and a Room-bound route also waits for its session state, so no
 * surface ever shows without its Disclosure lines. While a request fails the page body holds only the centered
 * status strip, retried every 2000 ms; nothing is guessed in the meantime. A session the server refuses (4xx) has
 * no Room, so its route shows the global lines: `#/play/<session_id>` and `#/done/<session_id>` hold the Session-gone
 * line with "Start again", which goes to `#/` since the refusal names no Room to start again, or, for a Session its
 * Judge room's deletion took (410 `room_deleted`), the Deleted Judge room notice; `#/triggers/<session_id>` holds an
 * empty body.
 * The top bar's mode indicator counts the Room results of the `?profile=` profile (web/profile) and is rewritten as
 * soon as one is recorded. In Local mode `#/` also waits for `GET /rooms`, read afresh on every visit: the browser keeps no list of its own;
 * it is the Capture screen, its Retention summary the `retention` text of the same `GET /meta`. In Hosted mode `#/` is
 * the Hosted landing: it reads `GET /rooms` once, and a failed read shows the landing's own failed state, never the
 * unreachable strip, so the title block stays usable; its "Try again" renders the route afresh. An Access code the
 * landing accepts renders `#/` once more as the Capture screen, with the builds left in place of the Stored Rooms
 * list, and so does a Build end state's "Add photos" or "Start over" while the tab holds that code; any other visit
 * to `#/` ("Build another room", "Leave room") is the Hosted landing again. That Hosted Capture screen reads `GET
 * /rooms` once more for the first Demo room its dropzone offers as the sample room; a failed read offers none.
 * `#/build/<job_id>`
 * holds the global lines, the Timer of that Build and the Capture screen during that Build, in both modes. The top
 * bar's Timer slot shows the run the route owns (see `timerOwner`), the Capture screen the run its own Upload starts.
 * `#/build/<job_id>/view` waits for `GET /builds/<job_id>/view` once and shows the Build view, ready, not ready or
 * failed (never the unreachable strip), with the `BuildView`'s own Disclosure list once it answered; only its body
 * scrolls, so the top bar and the banner stay pinned. Either Build route whose job's Room is gone (410
 * `room_deleted`, or 404 `room_not_found` on the view) holds only the Deleted Judge room notice or the unknown-room
 * card in its body (`showRoomGone`). `#/done/<session_id>` is the Completion screen over the
 * dimmed Play screen, its top bar inert and its Timer frozen. `#/triggers/<session_id>` is cut 5's second window,
 * the "How hints work" panel of that session with its Room's Disclosure lines. Below 1024 px the Narrow-screen message, a
 * sibling of `root`, replaces the whole app on every route; `root` is only hidden meanwhile, so its state survives
 * the resize.
 */
export function startShell(root: HTMLElement): void {
  const metas = new Map<string, Meta>()
  let generation = 0
  let unmount: (() => void) | undefined
  /** Whether this page load reached its route by an in-app navigation, so "Back" has somewhere to return to. */
  let navigated = false

  /** `request` until it answers; undefined once a newer navigation has taken over. */
  async function answered<T>(mine: number, request: () => Promise<T>): Promise<T | undefined> {
    while (mine === generation) {
      try {
        return await request()
      } catch {
        if (mine !== generation) return undefined
        show(unreachable())
        await sleep(RETRY_MS)
      }
    }
    return undefined
  }

  function show(...children: HTMLElement[]): void {
    unmount?.()
    unmount = undefined
    root.replaceChildren(...children)
  }

  async function render(): Promise<void> {
    const mine = ++generation
    const place = currentPlace()
    const meta = metas.get(place.profile) ?? (await answered(mine, () => getMeta(place.profile)))
    if (meta === undefined) return
    metas.set(place.profile, meta)
    let disclosure = meta.disclosure
    let content: Content = { name: 'empty' }
    // Hosted `#/` is the Capture screen once when asked for and this tab holds an Access code, with the builds left
    // the server counts now; without that count it is the landing, where the code is entered again.
    const resumed = place.route.name === 'home' && takeCaptureRequest() ? await judgeBuildsLeft() : null
    if (place.route.name === 'view') {
      const state = await loadBuildView(place.route.jobId)
      if (state.name === 'ready') disclosure = state.view.disclosure
      const { profile } = place
      const back = (): void => {
        if (navigated) history.back()
        else location.hash = placeHref({ route: { name: 'home' }, profile })
      }
      content = { name: 'view', state, meta, profile, onBack: back, onRetry: () => void render() }
    } else if (place.route.name === 'play' || place.route.name === 'done' || place.route.name === 'triggers') {
      const { name, sessionId } = place.route
      const answer = await answered(mine, () => getSession(sessionId).catch(refused))
      if (answer === undefined) return
      const state = answer === 'room_deleted' ? null : answer
      if (state !== null) disclosure = state.disclosure
      if (state !== null) content = { name, session: state, guide: meta.guide, mode: meta.mode, profile: place.profile }
      else if (answer === 'room_deleted' && name !== 'triggers') content = { name: 'roomDeleted', mode: meta.mode, profile: place.profile }
      else if (name !== 'triggers') content = { name: 'gone', profile: place.profile }
    } else if (place.route.name === 'build') {
      content = { name: 'build', jobId: place.route.jobId, profile: place.profile, mode: meta.mode, retention: meta.retention }
    } else if (place.route.name === 'home' && meta.mode === 'local') {
      const rooms = await answered(mine, listRooms)
      if (rooms === undefined) return
      content = { name: 'rooms', rooms, profile: place.profile, mode: meta.mode, retention: meta.retention }
    } else if (place.route.name === 'home' && resumed !== null) {
      const rooms = await listRooms().catch(() => null)
      const { profile } = place
      content = { name: 'capture', buildsLeft: resumed, sample: rooms?.[0], profile, mode: meta.mode, retention: meta.retention }
    } else if (place.route.name === 'home') {
      const rooms = await listRooms().catch(() => null)
      const onAccepted = (): void => {
        requestCapture()
        void render()
      }
      content = { name: 'landing', rooms, profile: place.profile, mode: meta.mode, onRetry: () => void render(), onAccepted }
    }
    const played = (await getResults(place.profile)).length
    if (mine !== generation) return
    const banner = disclosureBanner(disclosure)
    const bar = topBar(meta, played)
    const body = surface(content, bar)
    const done = content.name === 'done'
    bar.element.inert = done // the Play screen's controls stay in place, taking no input
    show(bar.element, body.element, ...(banner === null ? [] : [banner]))
    const unmountBody = body.mount?.()
    const owns = timerOwner(place.route)
    const unmountTimer = owns === null ? undefined : mountTimer(bar.timer, owns, done)
    // The mode indicator follows the profile at once: a Room result recorded on this surface rewrites its count.
    const unwatch = watchResults(place.profile, (results) => bar.showPlayed(results.length))
    unmount = () => {
      unmountBody?.()
      unmountTimer?.()
      unwatch()
    }
  }

  window.addEventListener('hashchange', () => {
    navigated = true
  })
  root.after(narrowScreenMessage())
  liveRegion() // in the page before anything is written to it
  window.addEventListener('hashchange', () => void render())
  void render()
}

interface Surface {
  element: HTMLElement
  /** Runs once the element is in the page; returns its teardown. */
  mount?: () => () => void
}

/**
 * What a route's body holds: the Build view, the Play layout for a session, the Completion screen over it, the Capture
 * screen with the Stored Rooms list (Local `#/`), the Hosted landing (Hosted `#/`, `rooms` null when `GET /rooms`
 * failed), the Capture screen once its Access code is accepted (Hosted `#/`, `sample` the first Demo room listed, if
 * any, for the dropzone's sample-room button), the Capture screen during a Build
 * (`#/build/<job_id>`), the Session-gone state of a session the server refused, or nothing yet.
 */
type Content =
  | ({ name: 'view'; state: BuildViewState } & BuildViewOptions)
  | { name: 'play' | 'done' | 'triggers'; session: SessionState; guide: Meta['guide']; mode: Meta['mode']; profile: string }
  | { name: 'rooms'; rooms: RoomSummary[]; profile: string; mode: Meta['mode']; retention: string }
  | {
      name: 'landing'
      rooms: RoomSummary[] | null
      profile: string
      mode: Meta['mode']
      onRetry: () => void
      onAccepted: (buildsLeft: number) => void
    }
  | { name: 'capture'; buildsLeft: number; sample: RoomSummary | undefined; profile: string; mode: Meta['mode']; retention: string }
  | { name: 'build'; jobId: string; profile: string; mode: Meta['mode']; retention: string }
  | { name: 'gone'; profile: string }
  | { name: 'roomDeleted'; mode: Meta['mode']; profile: string }
  | { name: 'empty' }

/**
 * The Timer run each route owns: `#/build/<job_id>` the run of that Build, the Play and Completion screens the run of
 * the Session the Build opened (never a replayed stored Room's). null on the Build view and on `#/`, where the Capture
 * screen shows only the run its own Upload starts.
 */
function timerOwner(route: Route): ((run: TimerRun) => boolean) | null {
  if (route.name === 'home') return null
  if (route.name === 'view' || route.name === 'triggers') return null
  if (route.name === 'build') return (run) => run.jobId === route.jobId
  return (run) => run.sessionId === route.sessionId
}

/**
 * The body for a route; each later surface story fills its own. The Capture screen takes the top bar's Timer slot;
 * the Play screen takes the whole bar, which its First-room welcome holds inert.
 */
function surface(content: Content, bar: TopBar): Surface {
  const element = document.createElement('main')
  element.className = 'shell-body'
  if (content.name === 'empty') return { element }
  if (content.name === 'gone') {
    const { profile } = content
    element.classList.add('session-gone-layout')
    element.append(
      playEnded(() => {
        location.hash = placeHref({ route: { name: 'home' }, profile })
      }),
    )
    return { element }
  }
  if (content.name === 'roomDeleted') {
    const { profile, mode } = content
    return {
      element,
      mount: () => {
        showRoomGone(element, 'room_deleted', mode, profile)
        return () => {}
      },
    }
  }
  if (content.name === 'view') {
    const { state, meta, profile } = content
    if (state.name === 'gone') {
      return {
        element,
        mount: () => {
          showRoomGone(element, state.gone, meta.mode, profile)
          return () => {}
        },
      }
    }
    element.classList.add('build-view-layout')
    const view = buildViewSurface(state, content)
    element.append(...view.children)
    return {
      element,
      mount: () => {
        view.focus()
        return () => {}
      },
    }
  }
  if (content.name === 'rooms') {
    element.classList.add('capture-layout')
    const capture = captureScreen(content.rooms, content.profile, content.mode, content.retention, bar.timer)
    element.append(capture.left, capture.right)
    return { element, mount: capture.mount }
  }
  if (content.name === 'landing') {
    element.classList.add('landing-layout')
    const landing = hostedLanding(content.rooms, content.profile, content.mode, content.onRetry, content.onAccepted)
    element.append(...landing.children)
    return { element, mount: landing.mount }
  }
  if (content.name === 'capture') {
    element.classList.add('capture-layout')
    const capture = captureScreen(content.buildsLeft, content.profile, content.mode, content.retention, bar.timer, content.sample)
    element.append(capture.left, capture.right)
    return { element, mount: capture.mount }
  }
  if (content.name === 'build') {
    element.classList.add('capture-layout')
    const { jobId, profile, mode, retention } = content
    const build = buildScreen(jobId, profile, mode, retention, (gone) => showRoomGone(element, gone, mode, profile))
    element.append(build.left, build.right)
    return { element, mount: build.mount }
  }
  if (content.name === 'triggers') {
    element.classList.add('triggers-window')
    const { session } = content
    return { element, mount: () => mountTriggersWindow(element, session) }
  }
  element.classList.add('play-layout')
  const sceneColumn = document.createElement('section')
  sceneColumn.className = 'scene-column'
  const sideColumn = document.createElement('aside')
  sideColumn.className = 'side-column'
  element.append(sceneColumn, sideColumn)
  if (content.name === 'play') {
    const frame = { body: element, topBar: bar.element, controls: bar.controls, guide: content.guide, mode: content.mode }
    return { element, mount: () => mountPlay(sceneColumn, sideColumn, content.session, frame) }
  }
  element.classList.add('completion-layout')
  const { session, profile, mode } = content
  return { element, mount: () => mountCompletion(element, sceneColumn, sideColumn, session, profile, mode, bar.controls) }
}

/** The page body empty except the centered status strip (UX-DR61). */
function unreachable(): HTMLElement {
  const element = document.createElement('main')
  element.className = 'shell-unreachable'
  element.append(statusStrip(strings.serverUnreachable))
  return element
}
