import './shell.css'
import type { Meta, RoomSummary, SessionState } from '../types'
import { getMeta, getSession, listRooms, RequestFailed } from './api/index.ts'
import { captureScreen } from './capture.ts'
import { mountTimer, type TimerRun } from './capture-timer.ts'
import { disclosureBanner } from './components/disclosure-banner.ts'
import { statusStrip } from './components/status-strip.ts'
import { topBar } from './components/top-bar.ts'
import { currentPlace, type Route } from './router.ts'
import { mountScene } from './scene/index.ts'
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
 * In Local mode `#/` also waits for `GET /rooms`, read afresh on every visit: the browser keeps no list of its own;
 * it is the Capture screen, its Retention summary the `retention` text of the same `GET /meta`. `#/build/<job_id>`
 * holds the global lines and the Timer of that Build; its body belongs to 2.18. The top bar's Timer slot shows the
 * run the route owns (see `timerOwner`), the Capture screen the run its own Upload starts.
 */
export function startShell(root: HTMLElement): void {
  const metas = new Map<string, Meta>()
  let generation = 0
  let unmount: (() => void) | undefined

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
    if (place.route.name === 'play' || place.route.name === 'done') {
      const { name, sessionId } = place.route
      const state = await answered(mine, () => getSession(sessionId).catch(refused))
      if (state === undefined) return
      if (state !== null) disclosure = state.disclosure
      if (name === 'play' && state !== null) content = { name: 'play', session: state }
    } else if (place.route.name === 'home' && meta.mode === 'local') {
      const rooms = await answered(mine, listRooms)
      if (rooms === undefined) return
      content = { name: 'rooms', rooms, profile: place.profile, retention: meta.retention }
    }
    if (mine !== generation) return
    const banner = disclosureBanner(disclosure)
    const bar = topBar(meta)
    const body = surface(content, bar.timer)
    show(...(banner === null ? [] : [banner]), bar.element, body.element)
    const unmountBody = body.mount?.()
    const owns = timerOwner(place.route)
    const unmountTimer = owns === null ? undefined : mountTimer(bar.timer, owns)
    unmount = () => {
      unmountBody?.()
      unmountTimer?.()
    }
  }

  window.addEventListener('hashchange', () => void render())
  void render()
}

interface Surface {
  element: HTMLElement
  /** Runs once the element is in the page; returns its teardown. */
  mount?: () => () => void
}

/** What a route's body holds: the Play layout for a session, the Capture screen with the Stored Rooms list (Local `#/`) or nothing yet. */
type Content =
  | { name: 'play'; session: SessionState }
  | { name: 'rooms'; rooms: RoomSummary[]; profile: string; retention: string }
  | { name: 'empty' }

/**
 * The Timer run each route owns: `#/build/<job_id>` the run of that Build, the Play and Completion screens the run of
 * the Session the Build opened (never a replayed stored Room's). null on `#/`, where the Capture screen shows only the
 * run its own Upload starts.
 */
function timerOwner(route: Route): ((run: TimerRun) => boolean) | null {
  if (route.name === 'home') return null
  if (route.name === 'build') return (run) => run.jobId === route.jobId
  return (run) => run.sessionId === route.sessionId
}

/** The body for a route; each later surface story fills its own. `timerSlot` is the top bar's, for the Capture screen. */
function surface(content: Content, timerSlot: HTMLElement): Surface {
  const element = document.createElement('main')
  element.className = 'shell-body'
  if (content.name === 'empty') return { element }
  if (content.name === 'rooms') {
    element.classList.add('capture-layout')
    const capture = captureScreen(content.rooms, content.profile, content.retention, timerSlot)
    element.append(capture.left, capture.right)
    return { element, mount: capture.mount }
  }
  element.classList.add('play-layout')
  const sceneColumn = document.createElement('section')
  sceneColumn.className = 'scene-column'
  const sideColumn = document.createElement('aside')
  sideColumn.className = 'side-column'
  element.append(sceneColumn, sideColumn)
  return { element, mount: () => mountScene(sceneColumn, content.session) }
}

/** The page body empty except the centered status strip (UX-DR61). */
function unreachable(): HTMLElement {
  const element = document.createElement('main')
  element.className = 'shell-unreachable'
  element.append(statusStrip(strings.serverUnreachable))
  return element
}
