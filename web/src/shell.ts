import './shell.css'
import type { Meta, RoomSummary } from '../types'
import { getMeta, getSession, listRooms, RequestFailed } from './api/index.ts'
import { disclosureBanner } from './components/disclosure-banner.ts'
import { bannerSlot } from './components/error-banner.ts'
import { statusStrip } from './components/status-strip.ts'
import { topBar } from './components/top-bar.ts'
import { currentPlace } from './router.ts'
import { mountScene } from './scene/index.ts'
import { storedRooms } from './stored-rooms.ts'
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
 * In Local mode `#/` also waits for `GET /rooms`, read afresh on every visit: the browser keeps no list of its own.
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
    if (place.route.name !== 'home') {
      const { name, sessionId } = place.route
      const state = await answered(mine, () => getSession(sessionId).catch(refused))
      if (state === undefined) return
      if (state !== null) disclosure = state.disclosure
      if (name === 'play' && state !== null) content = { name: 'play' }
    } else if (meta.mode === 'local') {
      const rooms = await answered(mine, listRooms)
      if (rooms === undefined) return
      content = { name: 'rooms', rooms, profile: place.profile }
    }
    if (mine !== generation) return
    const banner = disclosureBanner(disclosure)
    const body = surface(content)
    show(...(banner === null ? [] : [banner]), topBar(meta).element, body.element)
    unmount = body.mount?.()
  }

  window.addEventListener('hashchange', () => void render())
  void render()
}

interface Surface {
  element: HTMLElement
  /** Runs once the element is in the page; returns its teardown. */
  mount?: () => () => void
}

/** What a route's body holds: the Play layout, the Stored Rooms list (Local `#/`) or nothing yet. */
type Content = { name: 'play' } | { name: 'rooms'; rooms: RoomSummary[]; profile: string } | { name: 'empty' }

/** The body for a route; each later surface story fills its own. */
function surface(content: Content): Surface {
  const element = document.createElement('main')
  element.className = 'shell-body'
  if (content.name === 'empty') return { element }
  if (content.name === 'rooms') {
    // The Capture layout's left area: the banner slot on top; the dropzone joins above the list in 2.16.
    element.classList.add('capture-layout')
    const left = document.createElement('section')
    left.className = 'capture-left'
    const banners = bannerSlot()
    left.append(banners, storedRooms(content.rooms, content.profile, banners))
    element.append(left)
    return { element }
  }
  element.classList.add('play-layout')
  const sceneColumn = document.createElement('section')
  sceneColumn.className = 'scene-column'
  const sideColumn = document.createElement('aside')
  sideColumn.className = 'side-column'
  element.append(sceneColumn, sideColumn)
  return { element, mount: () => mountScene(sceneColumn) }
}

/** The page body empty except the centered status strip (UX-DR61). */
function unreachable(): HTMLElement {
  const element = document.createElement('main')
  element.className = 'shell-unreachable'
  element.append(statusStrip(strings.serverUnreachable))
  return element
}
