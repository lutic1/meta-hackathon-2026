import './walk-map.css'
import type { PlayView } from '../../types'
import { announce } from '../live-region.ts'
import { hotspotPath } from '../scene/geometry.ts'
import { fill, strings } from '../strings.ts'
import { areaOf, coneAngle, type WalkArea } from '../walk.ts'

const SVG = 'http://www.w3.org/2000/svg'
/** The plan's drawing, in its own viewBox units. */
const PLAN = { width: 164, height: 76, gap: 12 }

export interface WalkMap {
  element: HTMLElement
  /**
   * Lights photo `index` as where you stand, the view cone turning to it; `said`, the view description after a
   * move, is written to the live region.
   */
  setCurrent: (index: number, said?: string) => void
}

/** An area's name as a heading or button shows it: its label with the first letter capitalised. */
export function areaName(label: string): string {
  return label.charAt(0).toUpperCase() + label.slice(1)
}

/** "a", "a and b", "a, b and c". */
function joined(labels: readonly string[]): string {
  return labels.length < 2 ? labels.join('') : `${labels.slice(0, -1).join(', ')} and ${labels.at(-1)}`
}

/**
 * What a screen reader hears after a move (spec 3.7): "{Area}, view {i} of {n}. Here: {labels}." naming the objects
 * outlined on photo `index` (its Interactables with a drawable polygon), or "... Nothing outlined here.".
 */
export function viewDescription(areas: readonly WalkArea[], view: Pick<PlayView, 'interactables'>, index: number): string {
  const area = areas[areaOf(areas, index)]
  const values = { Area: areaName(area.label), i: area.ring.indexOf(index) + 1, n: area.ring.length }
  const labels = view.interactables
    .filter((ix) => ix.photo === index && hotspotPath(ix.polygons ?? []) !== '')
    .map((ix) => ix.label)
  if (labels.length === 0) return fill(strings.viewNothingHere, values)
  return fill(strings.viewHere, { ...values, labels: joined(labels) })
}

function shape<K extends keyof SVGElementTagNameMap>(tag: K, attributes: Record<string, string | number>): SVGElementTagNameMap[K] {
  const element = document.createElementNS(SVG, tag)
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, String(value))
  return element
}

let made = 0

/**
 * The walk map, "Where you are" (story mode, spec 1.5): a plan with one outlined box per area, sized by its photo
 * count and joined to the next by a dashed doorway tick, one dot per photo in ring order along a shallow arc, the dot
 * you stand on lit lamp under a view cone that turns with you (-50 to 50 degrees across the ring); under it one button
 * per area that walks to that area's entry view (`onWalk`), the area you stand in marked current. No thumbnails and
 * no Tab stop per photo. A `<nav>` named by its heading.
 */
export function walkMap(areas: readonly WalkArea[], onWalk: (photo: number) => void): WalkMap {
  const element = document.createElement('nav')
  element.className = 'walk-map'
  const heading = document.createElement('h2')
  heading.className = 'walk-map-heading label'
  heading.id = `walk-map-${made++}`
  heading.textContent = strings.whereYouAre
  element.setAttribute('aria-labelledby', heading.id)

  const plan = shape('svg', { class: 'walk-map-plan', viewBox: `0 0 ${PLAN.width} ${PLAN.height}`, 'aria-hidden': 'true' })
  const total = areas.reduce((sum, area) => sum + area.ring.length + 1.5, 0)
  const room = PLAN.width - 8 - PLAN.gap * (areas.length - 1)
  const dots = new Map<number, { dot: SVGCircleElement; x: number; y: number; angle: number }>()
  let x = 4
  areas.forEach((area, k) => {
    const width = (room * (area.ring.length + 1.5)) / total
    plan.append(shape('rect', { class: 'walk-map-area', x, y: 8, width, height: 60, rx: 4 }))
    if (k < areas.length - 1) plan.append(shape('path', { class: 'walk-map-door', d: `M${x + width} 40h${PLAN.gap}` }))
    area.ring.forEach((photo, j) => {
      const cx = x + (width * (j + 0.75)) / (area.ring.length + 0.5)
      const cy = 56 - 10 * Math.sin((Math.PI * (j + 0.5)) / area.ring.length)
      const dot = shape('circle', { class: 'walk-map-dot', cx, cy, r: 2.6 })
      dots.set(photo, { dot, x: cx, y: cy, angle: coneAngle(j, area.ring.length) })
    })
    x += width + PLAN.gap
  })
  const cone = shape('g', { class: 'walk-map-cone' })
  cone.append(shape('path', { d: 'M0 0L-13 -30A32 32 0 0 1 13 -30Z' }))
  plan.append(cone, ...[...dots.values()].map(({ dot }) => dot))

  const buttons = areas.map((area) => {
    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'walk-map-button'
    button.textContent = areaName(area.label)
    button.addEventListener('click', () => onWalk(area.entry))
    return button
  })
  const row = document.createElement('div')
  row.className = 'walk-map-areas'
  row.append(...buttons)
  element.append(heading, plan, row)

  function setCurrent(index: number, said?: string): void {
    for (const [photo, { dot }] of dots) {
      dot.classList.toggle('is-current', photo === index)
      dot.setAttribute('r', photo === index ? '4.5' : '2.6')
    }
    const here = dots.get(index)
    if (here !== undefined) {
      cone.style.transform = `translate(${here.x}px, ${here.y}px) rotate(${here.angle}deg)`
      // Placed before it shows, so only a turn swings it.
      if (!cone.classList.contains('is-shown')) {
        void cone.getBoundingClientRect()
        cone.classList.add('is-shown')
      }
    }
    const at = areaOf(areas, index)
    buttons.forEach((button, k) => {
      if (k === at) button.setAttribute('aria-current', 'true')
      else button.removeAttribute('aria-current')
    })
    if (said !== undefined) announce(said)
  }

  return { element, setCurrent }
}
