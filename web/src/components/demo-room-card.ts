import './demo-room-card.css'
import type { BuildView, RoomSummary } from '../../types'
import { photoUrl } from '../api/index.ts'
import { buildViewLink } from '../build-view.ts'
import { secondaryButton } from './button.ts'
import { hotspotPath, type Size } from '../scene/geometry.ts'
import { fill, strings } from '../strings.ts'
import { type Wizard, wizardPortrait } from '../wizards/portrait.ts'
import { graphEdges, layoutGraph, NODE_HEIGHT, NODE_WIDTH } from './graph-layout.ts'
import { roomTitle } from './stored-room-row.ts'

const SVG = 'http://www.w3.org/2000/svg'

const WIZARDS: readonly Wizard[] = ['architect', 'riddler', 'guide', 'trickster']

/** The stored downscale's size until the cover has loaded: its 1280 px long edge at 4:3. */
const DEFAULT_SIZE: Size = { width: 1280, height: 960 }

/** The width the inset graph is laid out at before it is scaled into the thumbnail: the Build view's at 1440 px. */
const GRAPH_WIDTH = 864

function svg<K extends keyof SVGElementTagNameMap>(tag: K, attributes: Record<string, string | number>): SVGElementTagNameMap[K] {
  const element = document.createElementNS(SVG, tag)
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, String(value))
  return element
}

/**
 * The 96 px mask-and-graph thumbnail, decorative: the cover photo with its Interactables' masks drawn as on the Build
 * view, and the puzzle graph inset in the bottom-right corner, its nodes and `requires` edges laid out as the Build
 * view lays them. Drawn from the Room's `BuildView`, so it holds no solution.
 */
export function buildThumbnail(view: BuildView, coverPhoto: number): HTMLElement {
  const thumb = document.createElement('div')
  thumb.className = 'demo-room-thumb'
  thumb.setAttribute('aria-hidden', 'true')
  const image = document.createElement('img')
  image.className = 'demo-room-thumb-photo'
  image.alt = ''
  image.src = photoUrl(view.room_id, coverPhoto)
  const masks = svg('svg', { class: 'demo-room-thumb-masks', preserveAspectRatio: 'xMidYMid meet' })
  const viewBox = ({ width, height }: Size): void => masks.setAttribute('viewBox', `0 0 ${width} ${height}`)
  viewBox(DEFAULT_SIZE)
  image.addEventListener('load', () => viewBox({ width: image.naturalWidth, height: image.naturalHeight }))
  const cover = view.photos.find(({ photo }) => photo === coverPhoto)?.masks ?? []
  const paths = cover.map(({ polygons }) => hotspotPath(polygons)).filter((d) => d !== '')
  masks.append(...paths.map((d) => svg('path', { class: 'demo-room-thumb-mask', d })))

  const layout = layoutGraph(view.puzzles, GRAPH_WIDTH)
  const graph = svg('svg', {
    class: 'demo-room-thumb-graph',
    viewBox: `0 0 ${layout.width} ${layout.height}`,
    preserveAspectRatio: 'xMidYMid meet',
  })
  const edges = graphEdges(view.puzzles, layout).map(({ points }) =>
    svg('path', { class: 'demo-room-thumb-edge', d: `M${points.join(' L')}` }),
  )
  const nodes = layout.nodes.map(({ x, y }, index) =>
    svg('rect', {
      class: view.puzzles[index].is_exit ? 'demo-room-thumb-node demo-room-thumb-exit' : 'demo-room-thumb-node',
      x,
      y,
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      rx: 8,
    }),
  )
  graph.append(...edges, ...nodes)
  thumb.append(image, masks, graph)
  return thumb
}

export interface DemoRoomCard {
  element: HTMLLIElement
  /** Puts the mask-and-graph thumbnail in the footer, before the card's buttons; absent under cut 0. */
  showThumbnail: (view: BuildView) => void
}

/**
 * `{components.demo-room-card}` (UX-DR58): a `chrome-raised` card per `RoomSummary` with the 4:3 cover photo, the
 * Room's name (or its build time) in `display-sm`, "{n} puzzles · 15 to 25 min" in `body-sm`, the four Wizard portraits
 * at 24 px under one accessible name, and a footer holding the thumbnail, once the landing has the Build view to draw
 * it from, beside "Play this room" and "How this room was built" (both secondary). Under cut 0 the footer holds
 * "Play this room" alone, with no link and no thumbnail.
 *
 * "Play this room" calls `onStart`, reading "Opening the room…" until the promise it returns settles, as does a click
 * anywhere else on the card but the link; the card is named by its title and is no Tab stop itself, so its two
 * controls are its Tab stops, each with its own focus ring. The link opens that Room's Build view.
 */
export function demoRoomCard(room: RoomSummary, profile: string, onStart: () => Promise<void>): DemoRoomCard {
  const element = document.createElement('li')
  element.className = 'demo-room-item'
  const card = document.createElement('article')
  card.className = 'demo-room-card'
  const cover = document.createElement('img')
  cover.className = 'demo-room-cover'
  cover.src = photoUrl(room.room_id, room.cover_photo)
  cover.alt = ''
  const body = document.createElement('div')
  body.className = 'demo-room-body'
  const title = document.createElement('h2')
  title.className = 'demo-room-title display-sm'
  title.id = `demo-room-${room.room_id}`
  title.textContent = roomTitle(room)
  card.setAttribute('aria-labelledby', title.id)
  const meta = document.createElement('p')
  meta.className = 'demo-room-meta body-sm'
  const puzzles = room.puzzle_count === 1 ? strings.onePuzzle : fill(strings.puzzleCount, { n: room.puzzle_count })
  meta.textContent = fill(strings.demoRoomMeta, { puzzles })
  const portraits = document.createElement('div')
  portraits.className = 'demo-room-portraits'
  portraits.setAttribute('role', 'img')
  portraits.setAttribute('aria-label', strings.demoRoomPortraits)
  portraits.append(...WIZARDS.map((wizard) => wizardPortrait(wizard, 24)))
  body.append(title, meta, portraits)

  const link = buildViewLink(room.job_id, profile)
  const actions = document.createElement('div')
  actions.className = 'demo-room-actions'
  const play = secondaryButton({ label: strings.playThisRoom, pendingLabel: strings.openingRoom, onActivate: onStart })
  actions.append(play)
  if (link !== null) actions.append(link)
  const footer = document.createElement('div')
  footer.className = 'demo-room-footer'
  footer.append(actions)
  card.append(cover, body, footer)

  card.addEventListener('click', (event) => {
    if (event.target instanceof Element && event.target.closest('a, button') !== null) return
    play.click()
  })
  element.append(card)
  return {
    element,
    showThumbnail: (view) => {
      if (link !== null) footer.prepend(buildThumbnail(view, room.cover_photo))
    },
  }
}
