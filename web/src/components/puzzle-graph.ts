import './puzzle-graph.css'
import type { BuildView, DryRunVerdict, PuzzleNode } from '../../types'
import { fill, strings } from '../strings.ts'

const SVG = 'http://www.w3.org/2000/svg'

/** DESIGN.md `{components.graph-node}`: 168 x 64 px. */
export const NODE_WIDTH = 168
export const NODE_HEIGHT = 64
/** The column step when every column fits: a node and a 64 px gap, as in mockups/build-view.html. */
const STEP_MAX = NODE_WIDTH + 64
/** The narrowest step: below it the graph is wider than its column. */
const STEP_MIN = 48
/** The clear gap two nodes in the same band keep side by side. */
const GAP_MIN = 16
/** One row: a node and a 24 px gap. */
const PITCH = NODE_HEIGHT + 24
/** Where an edge stops short of its target: the 8 px arrowhead's tip clears the node, or the Exit's 6 px ring. */
const EDGE_MARGIN = 3
const EXIT_EDGE_MARGIN = 9
/** The width the graph is laid out at before its column is measured: the left column at 1440 px. */
const DEFAULT_WIDTH = 864

const LIST = new Intl.ListFormat('en-US', { style: 'long', type: 'conjunction' })

export interface Placed {
  x: number
  y: number
}

export interface GraphLayout {
  /** One position per Puzzle, in Puzzle order. */
  nodes: Placed[]
  width: number
  height: number
}

/**
 * Each Puzzle's column: one past the deepest Puzzle it `requires`, 0 with none; the Exit puzzle alone in the last
 * column, rightmost, whatever its own `requires` say.
 */
function columns(puzzles: readonly PuzzleNode[]): number[] {
  const byId = new Map(puzzles.map((puzzle) => [puzzle.id, puzzle]))
  const depth = new Map<string, number>()
  const level = (puzzle: PuzzleNode, path: ReadonlySet<string>): number => {
    const known = depth.get(puzzle.id)
    if (known !== undefined) return known
    const before = puzzle.requires.flatMap((id) => {
      const required = byId.get(id)
      return required === undefined || required.is_exit || path.has(id) ? [] : [required]
    })
    const value = Math.max(-1, ...before.map((required) => level(required, new Set([...path, puzzle.id])))) + 1
    depth.set(puzzle.id, value)
    return value
  }
  const ranks = puzzles.map((puzzle) => (puzzle.is_exit ? -1 : level(puzzle, new Set())))
  const exit = Math.max(-1, ...ranks) + 1
  return ranks.map((rank, index) => (puzzles[index].is_exit ? exit : rank))
}

/**
 * The graph laid out left to right in `width` px. Columns are spaced evenly, at most a node and a 64 px gap apart.
 * When the columns are closer than a node's width, neighbouring columns drop into separate bands, so no two nodes
 * overlap and the graph still fits its column without horizontal scroll. Within a column, nodes run top to bottom by
 * the mean row of the Puzzles they require (so edges cross as little as they can), ties in Puzzle order; with one
 * band, each column is centred on the tallest.
 */
export function layoutGraph(puzzles: readonly PuzzleNode[], width: number): GraphLayout {
  const column = columns(puzzles)
  const count = Math.max(0, ...column) + 1
  const step = count > 1 ? Math.max(STEP_MIN, Math.min(STEP_MAX, (width - NODE_WIDTH) / (count - 1))) : 0
  const bands = step > 0 ? Math.min(count, Math.ceil((NODE_WIDTH + GAP_MIN) / step)) : 1
  const index = new Map(puzzles.map((puzzle, i) => [puzzle.id, i]))
  const members = Array.from({ length: count }, (_, k) => column.flatMap((c, i) => (c === k ? [i] : [])))
  const tallest = Math.max(...members.map((group) => group.length))
  const row = new Array<number>(puzzles.length).fill(0)
  const centre = new Array<number>(puzzles.length).fill(0)
  const weight = (i: number): number => {
    const before = puzzles[i].requires.flatMap((id) => index.get(id) ?? [])
    return before.length === 0 ? 0 : before.reduce((sum, j) => sum + centre[j], 0) / before.length
  }
  for (const group of members) {
    group.sort((a, b) => weight(a) - weight(b) || a - b)
    group.forEach((i, r) => {
      row[i] = r
      centre[i] = r + (tallest - group.length) / 2
    })
  }
  const nodes = column.map((k, i) => ({
    x: k * step,
    y: (bands === 1 ? centre[i] : row[i] * bands + (k % bands)) * PITCH,
  }))
  return {
    nodes,
    width: (count - 1) * step + NODE_WIDTH,
    height: Math.max(0, ...nodes.map(({ y }) => y)) + NODE_HEIGHT,
  }
}

/** The segment between two nodes' centres, cut at the first's edge and `margin` px short of the second's. */
export function edgeLine(from: Placed, to: Placed, margin: number): [number, number, number, number] {
  const [cx, cy] = [from.x + NODE_WIDTH / 2, from.y + NODE_HEIGHT / 2]
  const [dx, dy] = [to.x - from.x, to.y - from.y]
  const reach = (pad: number): number =>
    Math.min(dx === 0 ? Infinity : (NODE_WIDTH / 2 + pad) / Math.abs(dx), dy === 0 ? Infinity : (NODE_HEIGHT / 2 + pad) / Math.abs(dy))
  const start = reach(0)
  const end = 1 - reach(margin)
  return [cx + dx * start, cy + dy * start, cx + dx * end, cy + dy * end]
}

function svg<K extends keyof SVGElementTagNameMap>(tag: K, attributes: Record<string, string | number>): SVGElementTagNameMap[K] {
  const element = document.createElementNS(SVG, tag)
  for (const [name, value] of Object.entries(attributes)) element.setAttribute(name, String(value))
  return element
}

function line(className: string, text: string): HTMLElement {
  const element = document.createElement('div')
  element.className = className
  element.textContent = text
  return element
}

/** "Puzzle {n}, {lock type}, requires {list or none}, Dry run {verdict}", with "Exit" added on the Exit puzzle. */
export function nodeName(n: number, puzzle: PuzzleNode, requires: readonly number[], verdict: DryRunVerdict['verdict']): string {
  const list = requires.map((m) => fill(strings.puzzleHeading, { n: m }))
  const name = fill(strings.graphNode, {
    n,
    lockType: puzzle.lock_type,
    requires: list.length === 0 ? strings.requiresNone : LIST.format(list),
    verdict,
  })
  return puzzle.is_exit ? `${name}, ${strings.exit}` : name
}

/**
 * One `{components.graph-node}`: the Puzzle order number and Lock type in `mono-sm` on parchment, "Exit" in
 * `lamp-ink` on the Exit puzzle (whose lamp double ring the stylesheet draws), and the Dry run marker in the top-right
 * corner. A Tab stop named for the Puzzle; Enter acts as a click, and a click only focuses it.
 */
function graphNode(n: number, puzzle: PuzzleNode, requires: readonly number[], verdict: DryRunVerdict['verdict']): HTMLElement {
  const node = document.createElement('div')
  node.className = puzzle.is_exit ? 'graph-node graph-node-exit' : 'graph-node'
  node.tabIndex = 0
  node.setAttribute('role', 'img')
  node.setAttribute('aria-label', nodeName(n, puzzle, requires, verdict))
  const type = line('graph-node-type mono-sm', puzzle.lock_type)
  if (puzzle.is_exit) {
    const exit = document.createElement('span')
    exit.className = 'graph-node-exit-label label'
    exit.textContent = strings.exit
    type.append(exit)
  }
  const marker = line(`graph-dry-run graph-dry-run-${verdict} label`, verdict)
  node.append(line('graph-node-number mono-sm', fill(strings.puzzleHeading, { n })), type, marker)
  node.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') node.click()
  })
  node.addEventListener('click', () => node.focus())
  return node
}

/**
 * `{components.graph-node}` and `{components.graph-edge}` (UX-DR50): the puzzle chain from `BuildView.puzzles`, left
 * to right with the Exit puzzle rightmost, each `requires` edge a `graph-edge` line ending in an 8 px arrowhead. The
 * nodes come in Puzzle order, so Tab takes them in that order; each is static beyond focus. The graph is laid out
 * again whenever its column changes width. It reads no solution: `PuzzleNode` carries none.
 */
export function puzzleGraph(view: BuildView): HTMLElement {
  const order = new Map(view.puzzles.map((puzzle, index) => [puzzle.id, index + 1]))
  const verdicts = new Map(view.dry_run.map(({ puzzle_id, verdict }) => [puzzle_id, verdict]))
  const required = (puzzle: PuzzleNode): number[] =>
    puzzle.requires.flatMap((id) => order.get(id) ?? []).sort((a, b) => a - b)
  const nodes = view.puzzles.map((puzzle, index) =>
    graphNode(index + 1, puzzle, required(puzzle), verdicts.get(puzzle.id) ?? 'skipped'),
  )

  const edges = svg('svg', { class: 'puzzle-graph-edges', 'aria-hidden': 'true' })
  const marker = svg('marker', {
    id: 'graph-arrowhead',
    viewBox: '0 0 8 8',
    refX: 8,
    refY: 4,
    markerWidth: 8,
    markerHeight: 8,
    markerUnits: 'userSpaceOnUse',
    orient: 'auto',
  })
  marker.append(svg('path', { class: 'graph-arrowhead', d: 'M0,0 L8,4 L0,8 z' }))
  const defs = svg('defs', {})
  defs.append(marker)

  const stage = document.createElement('div')
  stage.className = 'puzzle-graph-stage'
  stage.append(edges, ...nodes)
  let laidOut = -1
  const place = (width: number): void => {
    if (width === laidOut) return
    laidOut = width
    const layout = layoutGraph(view.puzzles, width)
    stage.style.height = `${layout.height}px`
    edges.setAttribute('width', String(layout.width))
    edges.setAttribute('height', String(layout.height))
    nodes.forEach((node, index) => {
      node.style.left = `${layout.nodes[index].x}px`
      node.style.top = `${layout.nodes[index].y}px`
    })
    const lines = view.puzzles.flatMap((puzzle, index) =>
      puzzle.requires.flatMap((id) => {
        const from = order.get(id)
        if (from === undefined) return []
        const margin = puzzle.is_exit ? EXIT_EDGE_MARGIN : EDGE_MARGIN
        const [x1, y1, x2, y2] = edgeLine(layout.nodes[from - 1], layout.nodes[index], margin)
        return [svg('line', { class: 'graph-edge', x1, y1, x2, y2, 'marker-end': 'url(#graph-arrowhead)' })]
      }),
    )
    edges.replaceChildren(defs, ...lines)
  }
  place(DEFAULT_WIDTH)
  // Applied on the next frame, so the stage's own height change never re-enters the observer in the same pass.
  new ResizeObserver(([entry]) => requestAnimationFrame(() => place(Math.floor(entry.contentRect.width)))).observe(stage)

  const panel = document.createElement('div')
  panel.className = 'puzzle-graph'
  panel.append(stage)
  return panel
}
