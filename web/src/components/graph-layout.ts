// The puzzle graph's geometry: where each node sits and the path each `requires` edge takes. Pure, no DOM or CSS, so
// the tests run it as it ships.
import type { PuzzleNode } from '../../types'

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
/** How far an edge keeps from a node it passes: half the narrowest gap, so it still runs between any two nodes. */
const CLEARANCE = GAP_MIN / 2
/** The Exit's lamp double ring sits this far outside its node. */
const EXIT_RING = 6

export type Point = [number, number]

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

export interface GraphEdge {
  /** The required Puzzle's index and the requiring Puzzle's, in Puzzle order. */
  from: number
  to: number
  /** A polyline from the first node's edge to just short of the second's. */
  points: Point[]
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

interface Box {
  left: number
  top: number
  right: number
  bottom: number
}

function box({ x, y }: Placed, pad: number): Box {
  return { left: x - pad, top: y - pad, right: x + NODE_WIDTH + pad, bottom: y + NODE_HEIGHT + pad }
}

function centre({ x, y }: Placed): Point {
  return [x + NODE_WIDTH / 2, y + NODE_HEIGHT / 2]
}

function inside([x, y]: Point, { left, top, right, bottom }: Box): boolean {
  return left < x && x < right && top < y && y < bottom
}

/** Whether the segment from `p` to `q` runs through the inside of `b`; running along or touching its edge does not. */
function crosses(p: Point, q: Point, b: Box): boolean {
  let [enter, leave] = [0, 1]
  for (const [start, delta, low, high] of [
    [p[0], q[0] - p[0], b.left, b.right],
    [p[1], q[1] - p[1], b.top, b.bottom],
  ]) {
    if (delta === 0) {
      if (start <= low || start >= high) return false
      continue
    }
    const [a, z] = [(low - start) / delta, (high - start) / delta]
    enter = Math.max(enter, Math.min(a, z))
    leave = Math.min(leave, Math.max(a, z))
  }
  return (leave - enter) * Math.hypot(q[0] - p[0], q[1] - p[1]) > 1e-6
}

/** Where the ray from a node's centre `from` toward `to` leaves the node grown by `pad` px on every side. */
function rim(from: Point, to: Point, pad: number): Point {
  const [dx, dy] = [to[0] - from[0], to[1] - from[1]]
  const t = Math.min(
    dx === 0 ? Infinity : (NODE_WIDTH / 2 + pad) / Math.abs(dx),
    dy === 0 ? Infinity : (NODE_HEIGHT / 2 + pad) / Math.abs(dy),
  )
  return [from[0] + dx * t, from[1] + dy * t]
}

/**
 * The shortest path from one node's centre to another's that keeps `CLEARANCE` px from every other node (and from the
 * Exit's ring): a straight line when nothing is in the way, otherwise bent round the corners of the nodes between,
 * through the gap between rows or bands or above or below them. So an edge never runs under a node it does not join.
 * The path starts at the first node's edge and stops `margin` px short of the second's.
 */
function route(nodes: readonly Placed[], exits: readonly boolean[], from: number, to: number, margin: number): Point[] {
  const blocks = nodes.flatMap((node, i) =>
    i === from || i === to ? [] : [box(node, CLEARANCE + (exits[i] ? EXIT_RING : 0))],
  )
  const corners = blocks.flatMap(({ left, top, right, bottom }): Point[] => [
    [left, top],
    [right, top],
    [right, bottom],
    [left, bottom],
  ])
  const points = [centre(nodes[from]), ...corners.filter((p) => !blocks.some((b) => inside(p, b))), centre(nodes[to])]
  const last = points.length - 1
  const clear = (i: number, j: number): boolean => !blocks.some((b) => crosses(points[i], points[j], b))
  // Dijkstra over the corners each can see; a handful of nodes, so a plain scan.
  const distance = points.map((_, i) => (i === 0 ? 0 : Infinity))
  const previous = points.map(() => -1)
  const done = points.map(() => false)
  for (;;) {
    let i = -1
    distance.forEach((d, k) => {
      if (!done[k] && d < Infinity && (i === -1 || d < distance[i])) i = k
    })
    if (i === -1 || i === last) break
    done[i] = true
    points.forEach((p, j) => {
      const d = distance[i] + Math.hypot(p[0] - points[i][0], p[1] - points[i][1])
      if (!done[j] && d < distance[j] && clear(i, j)) [distance[j], previous[j]] = [d, i]
    })
  }
  const path: Point[] = []
  for (let k = previous[last] === -1 ? 0 : last; k !== -1; k = previous[k]) path.unshift(points[k])
  if (path.length < 2) path.push(points[last])
  path[0] = rim(path[0], path[1], 0)
  path[path.length - 1] = rim(path[path.length - 1], path[path.length - 2], margin)
  return path
}

/** Every `requires` edge of the laid-out graph, an arrow from the required Puzzle to the Puzzle that requires it. */
export function graphEdges(puzzles: readonly PuzzleNode[], layout: GraphLayout): GraphEdge[] {
  const order = new Map(puzzles.map((puzzle, index) => [puzzle.id, index]))
  const exits = puzzles.map((puzzle) => puzzle.is_exit)
  return puzzles.flatMap((puzzle, to) =>
    puzzle.requires.flatMap((id) => {
      const from = order.get(id)
      if (from === undefined || from === to) return []
      const margin = puzzle.is_exit ? EXIT_EDGE_MARGIN : EDGE_MARGIN
      return [{ from, to, points: route(layout.nodes, exits, from, to, margin) }]
    }),
  )
}
