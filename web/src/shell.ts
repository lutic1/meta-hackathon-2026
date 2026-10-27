import './shell.css'
import type { Meta, RoomSummary, SessionState } from '../types'
import { getMeta, getSession, listRooms, RequestFailed } from './api/index.ts'
import { buildScreen } from './build-progress.ts'
import { type BuildViewOptions, type BuildViewState, buildViewSurface, loadBuildView } from './build-view.ts'
import { captureScreen } from './capture.ts'
import { mountCompletion } from './completion.ts'
import { mountTimer, type TimerRun } from './capture-timer.ts'
import { disclosureBanner } from './components/disclosure-banner.ts'
import { narrowScreenMessage } from './components/narrow-screen-message.ts'
import { statusStrip } from './components/status-strip.ts'
import { type TopBar, topBar } from './components/top-bar.ts'
import { hostedLanding } from './landing.ts'
import { liveRegion } from './live-region.ts'
import { currentPlace, placeHref, type Route } from './router.ts'
import { mountPlay } from './play.ts'
import { getResults, watchResults } from './profile/index.ts'
import { strings } from './strings.ts'

/** How long the server-unreachable state waits between attempts (UX-DR61). */
export const RETRY_MS = 2000

const sleep = (ms: number): Promise<void> => new Promise((resolve) => setTimeout(resolve, ms))

/** null for a 4xx: the server answered and refused, so there is nothing to retry and no Room to disclose. */
function refused(error: unknown): null {
  if (error instanceof RequestFailed && error.status !== null && error.status < 500) return null
  throw error
}

/**
 * The app shell (UX-DR7): the Disclosure banner, the top bar and the body for the current route.
 *
 * Nothing renders until `GET /meta` answers, and a Room-bound route also waits for its session state, so no
 * surface ever shows without its Disclosure lines. While a request fails the page body holds only the centered
 * status strip, retried every 2000 ms; nothing is guessed in the meantime. A session the server refuses (4xx) has
 * no Room, so its route shows the global lines with an empty body; its own states belong to later surfaces.
 * The top bar's mode indicator counts the Room results of the `?profile=` profile (web/profile) and is rewritten as
 * soon as one is recorded. In Local mode `#/` also waits for `GET /rooms`, read afresh on every visit: the browser keeps no list of its own;
 * it is the Capture screen, its Retention summary the `retention` text of the same `GET /meta`. In Hosted mode `#/` is
 * the Hosted landing: it reads `GET /rooms` once, and a failed read shows the landing's own failed state, never the
 * unreachable strip, so the title block stays usable; its "Try again" renders the route afresh. `#/build/<job_id>`
 * holds the global lines, the Timer of that Build and the Capture screen during that Build, in both modes. The top
 * bar's Timer slot shows the run the route owns (see `timerOwner`), the Capture screen the run its own Upload starts.
 * `#/build/<job_id>/view` waits for `GET /builds/<job_id>/view` once and shows the Build view, ready, not ready or
 * failed (never the unreachable strip), with the `BuildView`'s own Disclosure list once it answered; only its body
 * scrolls, so the banner and the top bar stay pinned. `#/done/<session_id>` is the Completion screen over the
 * dimmed Play screen, its top bar inert and its Timer frozen. Below 1024 px the Narrow-screen message, a sibling of
 * `root`, replaces the whole app on every route; `root` is only hidden meanwhile, so its state survives the resize.
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
    if (place.route.name === 'view') {
      const state = await loadBuildView(place.route.jobId)
      if (state.name === 'ready') disclosure = state.view.disclosure
      const { profile } = place
      const back = (): void => {
        if (navigated) history.back()
        else location.hash = placeHref({ route: { name: 'home' }, profile })
      }
      content = { name: 'view', state, meta, profile, onBack: back, onRetry: () => void render() }
    } else if (place.route.name === 'play' || place.route.name === 'done') {
      const { name, sessionId } = place.route
      const state = await answered(mine, () => getSession(sessionId).catch(refused))
      if (state === undefined) return
      if (state !== null) disclosure = state.disclosure
      if (state !== null) content = { name, session: state, guide: meta.guide, mode: meta.mode, profile: place.profile }
    } else if (place.route.name === 'build') {
      content = { name: 'build', jobId: place.route.jobId, profile: place.profile, mode: meta.mode, retention: meta.retention }
    } else if (place.route.name === 'home' && meta.mode === 'local') {
      const rooms = await answered(mine, listRooms)
      if (rooms === undefined) return
      content = { name: 'rooms', rooms, profile: place.profile, mode: meta.mode, retention: meta.retention }
    } else if (place.route.name === 'home') {
      const rooms = await listRooms().catch(() => null)
      content = { name: 'landing', rooms, profile: place.profile, mode: meta.mode, onRetry: () => void render() }
    }
    const played = (await getResults(place.profile)).length
    if (mine !== generation) return
    const banner = disclosureBanner(disclosure)
    const bar = topBar(meta, played)
    const body = surface(content, bar)
    const done = content.name === 'done'
    bar.element.inert = done // the Play screen's controls stay in place, taking no input
    show(...(banner === null ? [] : [banner]), bar.element, body.element)
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
 * failed), the Capture screen during a Build (`#/build/<job_id>`) or nothing yet.
 */
type Content =
  | ({ name: 'view'; state: BuildViewState } & BuildViewOptions)
  | { name: 'play' | 'done'; session: SessionState; guide: Meta['guide']; mode: Meta['mode']; profile: string }
  | { name: 'rooms'; rooms: RoomSummary[]; profile: string; mode: Meta['mode']; retention: string }
  | { name: 'landing'; rooms: RoomSummary[] | null; profile: string; mode: Meta['mode']; onRetry: () => void }
  | { name: 'build'; jobId: string; profile: string; mode: Meta['mode']; retention: string }
  | { name: 'empty' }

/**
 * The Timer run each route owns: `#/build/<job_id>` the run of that Build, the Play and Completion screens the run of
 * the Session the Build opened (never a replayed stored Room's). null on the Build view and on `#/`, where the Capture
 * screen shows only the run its own Upload starts.
 */
function timerOwner(route: Route): ((run: TimerRun) => boolean) | null {
  if (route.name === 'home') return null
  if (route.name === 'view') return null
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
  if (content.name === 'view') {
    element.classList.add('build-view-layout')
    const view = buildViewSurface(content.state, content)
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
    const landing = hostedLanding(content.rooms, content.profile, content.mode, content.onRetry)
    element.append(...landing.children)
    return { element, mount: landing.mount }
  }
  if (content.name === 'build') {
    element.classList.add('capture-layout')
    const build = buildScreen(content.jobId, content.profile, content.mode, content.retention)
    element.append(build.left, build.right)
    return { element, mount: build.mount }
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
  const { session, profile } = content
  return { element, mount: () => mountCompletion(element, sceneColumn, sideColumn, session, profile, bar.controls) }
}

/** The page body empty except the centered status strip (UX-DR61). */
function unreachable(): HTMLElement {
  const element = document.createElement('main')
  element.className = 'shell-unreachable'
  element.append(statusStrip(strings.serverUnreachable))
  return element
}
