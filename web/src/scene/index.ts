import './scene.css'
import './walk.css'
import {
  Mesh,
  MeshBasicMaterial,
  OrthographicCamera,
  PlaneGeometry,
  Scene,
  SRGBColorSpace,
  type Texture,
  TextureLoader,
  WebGLRenderer,
} from 'three'
import type { PlayInteractable, PlayView, PostedEvent } from '../../types'
import { photoUrl } from '../api/index.ts'
import { cue } from '../audio.ts'
import { bannerSlot, showBanner } from '../components/error-banner.ts'
import { feedbackLine } from '../components/feedback-line.ts'
import { GLOW_MS, GLOW_REDUCED_MS } from '../components/inventory.ts'
import { lockSeal as lockSealSvg } from '../components/wax-seal.ts'
import { areaName, viewDescription, type WalkMap, walkMap } from '../components/walk-map.ts'
import { glowOnce } from '../fade.ts'
import { foundBy } from '../feedback.ts'
import type { PlaySession } from '../play.ts'
import { fill, strings } from '../strings.ts'
import { useOnChip } from '../use-on.ts'
import { areaOf, doorways, neighbours, signCentre, type WalkArea, walkGraph, walkKey, wallPose } from '../walk.ts'
import { bounds, centroid, contain, type Size } from './geometry.ts'
import { type HotspotLayer, hotspotLayer } from './hotspots.ts'

/** A turn's swing (DESIGN.md Motion, the walk and story exception). */
export const TURN_MS = 780
/** A push-in through a doorway: the area you leave grows and fades over 720 ms; the next fades in 260 ms after it. */
export const PUSH_OUT_MS = 720
export const PUSH_IN_DELAY_MS = 260
export const PUSH_IN_MS = 640
/** The way out (spec 5.6): the daylight fades in over 1200 ms while the area grows 12% over 1400 ms. */
export const DAYLIGHT_MS = 1200
export const EXIT_PUSH_MS = 1400
/** The Trickster's trap (spec 5.5): the lights flicker over 700 ms, stepping between these brightnesses. */
export const FLICKER_MS = 700
const FLICKER = [
  [0, 0.25], [0.12, 1], [0.22, 0.15], [0.4, 0.9], [0.55, 0.3], [0.7, 1], [1, 1],
].map(([offset, brightness]) => ({ offset, filter: `brightness(${brightness})`, easing: 'step-end' }))
/** The room either side of the photo you face, kept free so its walls show (spec 1.6). */
const WALL_GUTTER_PX = 32

const reduced = (): boolean => matchMedia('(prefers-reduced-motion: reduce)').matches
const pause = (ms: number): Promise<void> => new Promise((done) => setTimeout(done, ms))

const ARCH =
  '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
  'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 21V9a7 7 0 0 1 14 0v12"/>' +
  '<path d="M12 17V11M9 14l3-3 3 3"/></svg>'
const TURN_ICON = {
  left: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6"/></svg>',
  right: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" ' +
    'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg>',
}

/** One view of the area you stand in, as a wall: its photo as a plain image, inert, posed by its offset. */
interface Wall {
  element: HTMLElement
  drift: HTMLElement
  rest: HTMLElement
}

/**
 * Whether a key pressed on `target` may walk: on the page, in the Scene, or on a button; never in a field or tray, and
 * never inside a dialog (the chest's).
 */
function walksFrom(target: EventTarget | null, frame: HTMLElement): boolean {
  if (target === document.body) return true
  if (!(target instanceof Element) || target.closest('[role="dialog"]') !== null) return false
  return frame.contains(target) || target.closest('button, a') !== null
}

/**
 * Dispatched on `window` the first time any Hotspot responds to the pointer in a session (T1): the Timer stops on
 * it (2.17). Keyboard focus never sends it.
 */
export const FIRST_POINTER_RESPONSE = 'first-pointer-response'

export interface FirstPointerResponseDetail {
  sessionId: string
}

const responded = new Set<string>()
/** The photo each session's Scene last showed in this page, so the Completion screen dims the same one. */
const shownPhoto = new Map<string, number>()

/** The photo the Scene of `sessionId` last showed in this page; the first photo when it showed none (a reload). */
export function lastShownPhoto(sessionId: string): number {
  return shownPhoto.get(sessionId) ?? 0
}

/** Targets kept per session for this tab: `targets` reads them, `keep` adds one. */
interface TabTargets {
  targets: (sessionId: string) => string[]
  keep: (sessionId: string, target: string) => void
}

/**
 * Targets per session kept in sessionStorage under `prefix` + session id, so they outlive a reload of the tab; in
 * memory alone when storage refuses. Only targets of locks the player already solved are kept, so nothing leaks.
 */
function tabTargets(prefix: string): TabTargets {
  const memory = new Map<string, string[]>()
  function targets(sessionId: string): string[] {
    const held = memory.get(sessionId)
    if (held !== undefined) return held
    let stored: string[] = []
    try {
      const parsed: unknown = JSON.parse(sessionStorage.getItem(prefix + sessionId) ?? '[]')
      if (Array.isArray(parsed)) stored = parsed.filter((target): target is string => typeof target === 'string')
    } catch {
      // Storage refused or unreadable: this page starts with none.
    }
    memory.set(sessionId, stored)
    return stored
  }
  function keep(sessionId: string, target: string): void {
    const held = targets(sessionId)
    if (held.includes(target)) return
    const next = [...held, target]
    memory.set(sessionId, next)
    try {
      sessionStorage.setItem(prefix + sessionId, JSON.stringify(next))
    } catch {
      // Storage refused: the targets live as long as the page.
    }
  }
  return { targets, keep }
}

/** The target each unlock moment of a session bloomed in this tab, so the Completion screen's filmstrip lights it. */
const solved = tabTargets('keyframe-solved:')

/** The Interactables the unlock moments of `sessionId` named in this tab, in order, kept across a reload. */
export function solvedTargets(sessionId: string): string[] {
  return solved.targets(sessionId)
}

/** The targets each session's clicks found in this tab (`foundBy`): solved `find` targets no `use_on` needs. */
const found = tabTargets('keyframe-found:')

/** The targets the clicks of `sessionId` found in this tab, in order, kept across a reload. */
export function foundTargets(sessionId: string): string[] {
  return found.targets(sessionId)
}

/** The mounted Scene: its teardown, and the redraw for the refetched Effective room. */
export interface MountedScene {
  unmount: () => void
  /**
   * Where the Play screen hangs its parts in the frame, in the Tab order (spec 6.3): the Riddle note before the photo,
   * the pack and the chest after the turn discs and before the walk map.
   */
  slots: { note: HTMLElement; floor: HTMLElement }
  /** The photo you face; -1 before the first is shown. */
  current: () => number
  /** Resolves once the first photo and its Hotspots are live, so the frame has set `--wall-width`. */
  live: Promise<void>
  /**
   * Walks to photo `index` as a move does (a turn, or a push-in across areas); resolves once you stand there. With
   * `quiet` the view is not announced (a story beat speaks over the walk).
   */
  walkTo: (index: number, quiet?: boolean) => Promise<void>
  /**
   * The way out: once the photo is live, the Hotspot of `target` fills with daylight and the area grows toward it
   * (instant with `still`).
   */
  daylight: (target: string | null, still?: boolean) => Promise<void>
  /** The coach pill in the feedback line's slot: shown for at most 15 s, or taken away. */
  coach: (on: boolean) => void
  /**
   * The story intro's trap: the lights flicker and the Trickster's lock seal slams onto the photo you face (onto its
   * part above the line `above` gives, with one); or lifts.
   */
  lockSeal: (on: boolean, above?: () => number) => void
  /** The Effective room after an accepted edit (AD-12): the shown photo's Hotspots from `view`; the photo stays. */
  reshape: (view: PlayView) => void
  /** The Interactable the latest `click` or `use_on` named, null before the first: the unlock moment's target. */
  lastTarget: () => string | null
  /** The unlock moment: the frame's gilt rule lights once; the Hotspot of `target` on the shown photo blooms with it. */
  bloom: (target: string | null) => void
  /** The feedback line over the bottom edge of the frame shows `line`, held 2.5 s, then fades out. */
  say: (line: string) => void
}

/** The Scene that cannot be drawn: the frame holds the error banner with "Reload" in place of the photo. */
function sceneUnavailable(frame: HTMLElement, ground: HTMLElement, say: (line: string) => void): MountedScene {
  frame.classList.remove('is-loading')
  const slot = bannerSlot()
  slot.classList.add('scene-unavailable')
  ground.replaceChildren(slot)
  showBanner(slot, {
    variant: 'error',
    heading: strings.sceneUnavailable,
    sentence: strings.sceneUnavailableBody,
    actions: [{ label: strings.reload, onActivate: () => location.reload() }],
  })
  const slots = { note: document.createElement('div'), floor: document.createElement('div') }
  return {
    unmount: () => frame.remove(),
    slots,
    current: () => -1,
    live: Promise.resolve(),
    walkTo: async () => {},
    daylight: async () => {},
    coach: () => {},
    lockSeal: () => {},
    reshape: () => {},
    lastTarget: () => null,
    bloom: () => {},
    say,
  }
}

function firstPointerResponse(sessionId: string): void {
  if (responded.has(sessionId)) return
  responded.add(sessionId)
  window.dispatchEvent(new CustomEvent<FirstPointerResponseDetail>(FIRST_POINTER_RESPONSE, { detail: { sessionId } }))
}

/**
 * The Play screen's Scene (FR-11, AD-11), for the session's Effective room as `GET /sessions/<id>/room` serves it:
 * the Scene frame in `root`, holding the walk (story mode, owner decision Oct 29). The photo you face stands in the
 * middle of the frame at its full height, the views either side of it in its area (`walkGraph`, from each photo's
 * `area` and `pan`) as dimmed, angled walls: plain images, inert, with no Hotspots. Only the photo you face is drawn
 * by three and takes input: a textured plane drawn exactly as served (no tone mapping, no light), on a canvas the
 * size of the photo, its Hotspots over it in its own pixel space. The frame shows its loading line until the first
 * photo and its Hotspots are live. You turn with the outer fifth of the photo either side, the turn discs at the
 * frame's edges or ArrowLeft and ArrowRight (a 780 ms swing that brings a wall to the middle; nothing at the ring's
 * ends), and go through to the next area with the doorway sign hanging from the photo's top edge, ArrowUp or the
 * walk map's area buttons (a 900 ms push-in to the area's entry view). Input is ignored while a move runs; every move
 * is a cut under reduced motion. After each move the photo's Hotspots are laid again, the next views' photos are
 * fetched ahead, and the view description is announced ("{Area}, view {i} of {n}. Here: ..."). At rest the photo
 * pushes in 3.5% over 26 s and drifts a few pixels against the pointer, the walls more.
 *
 * A Hotspot click posts one `click` naming its Interactable and nothing else, its label chip showing with "Checking"
 * beside it until the reply; when the reply opened no lock, the click hit no target and the label chip stays
 * ("{label} · in hand" on an Interactable the Inventory holds, "{label} · found" on a found target). The Hotspots of
 * collected Interactables follow `inventory` in every state the server sends, so a solved `find` target's glow fades
 * out; a click that found a target no `use_on` needs (`foundBy`) keeps it in `foundTargets` for the tab, a reload
 * included, and its glow fades out the same way. An Inventory item dropped on a Hotspot, or a Hotspot activated
 * while an item is selected (whose "Using {item label}" chip is pinned to the frame's top-left), posts one `use_on`
 * lock input naming the item and the Hotspot's Interactable, never a `click` and never a Puzzle (AD-4), and clears the
 * selection; until the reply, the target's label chip shows with "Checking" beside it. The selection outlives a
 * walk. It opens on photo `first(view)`. The Interactable the latest click or `use_on` named is kept as `lastTarget`,
 * and `bloom` plays the unlock moment (lock-opened.ts): the frame's gilt rule turns lamp with the lamp glow once (in
 * and out by `--motion-hover`, 300 ms in all; held 2 s with no animation under reduced motion) and the solved
 * target's Hotspot, when it is on the shown photo, blooms with it; the target is kept for the tab, a reload included,
 * for the Completion screen's filmstrip (`solvedTargets`). `say` shows the Play screen's feedback line for a reply
 * over the bottom edge of the frame.
 *
 * `reshape` lays the shown photo's Hotspots again from a refetched `PlayView` when its Interactables changed, keeping
 * the photo, the walk and the selection; keyboard focus on a Hotspot that is still there stays on it.
 *
 * Story mode (owner decision Oct 29): the frame's `slots` take the Riddle note (before the photo) and the pack and the
 * chest (after the turn discs), so the Tab order runs note, Hotspots, doorway, turns, floor, map; the frame sets the
 * width of the photo you face (`--wall-width`) for them to stand by. `walkTo` walks to a riddle's start photo ("Take me
 * there"), `daylight` lights the way out, `coach` shows the coach pill in the feedback line's slot, and `lockSeal`
 * plays the story intro's trap on the photo you face. Returns the teardown and these.
 *
 * A browser that cannot start WebGL (hardware acceleration off, or a blocked GPU) has no Scene to draw and no DOM one
 * to fall back to: the frame holds the error banner "Keyframe can't draw this room in this browser." with how to fix
 * it and "Reload", which takes focus, so the Play screen never shows a blank frame.
 */
export function mountScene(
  root: HTMLElement,
  play: PlaySession,
  rooms: Promise<PlayView>,
  first: (view: PlayView) => number = () => 0,
): MountedScene {
  const frame = document.createElement('div')
  frame.className = 'scene-frame is-loading'
  const ground = document.createElement('div')
  ground.className = 'scene-ground'
  const loading = document.createElement('p')
  loading.className = 'scene-loading body-sm'
  loading.textContent = strings.sceneLoading
  const world = document.createElement('div')
  world.className = 'scene-world'
  ground.append(loading, world)
  // The view on the wall you face: the turn zones under the photo and its Hotspots, the doorway signs over them.
  const view = document.createElement('div')
  view.className = 'scene-view'
  view.hidden = true
  const photo = document.createElement('div')
  photo.className = 'scene-photo'
  const zones = { left: turnZone('is-left'), right: turnZone('is-right') }
  view.append(zones.left, zones.right, photo)
  const turns = { left: turnDisc('is-left', strings.turnLeft, TURN_ICON.left), right: turnDisc('is-right', strings.turnRight, TURN_ICON.right) }
  const feedback = feedbackLine()
  const slots = { note: document.createElement('div'), floor: document.createElement('div') }
  slots.note.className = slots.floor.className = 'scene-slot'
  frame.append(slots.note, ground, feedback.element, feedback.coachPill, turns.left, turns.right, slots.floor)
  root.append(frame)

  let renderer: WebGLRenderer
  try {
    renderer = new WebGLRenderer({ antialias: true })
  } catch {
    return sceneUnavailable(frame, ground, feedback.say)
  }
  renderer.setPixelRatio(window.devicePixelRatio)
  renderer.domElement.setAttribute('role', 'img')
  const scene = new Scene()
  const camera = new OrthographicCamera()
  camera.position.z = 1
  const material = new MeshBasicMaterial({ toneMapped: false })
  const plane = new Mesh(new PlaneGeometry(1, 1), material)
  scene.add(plane)

  const loader = new TextureLoader()
  const textures = new Map<number, Promise<Texture<HTMLImageElement>>>()
  let mounted = true
  let room: PlayView | undefined
  let areas: WalkArea[] = []
  let walls = new Map<number, Wall>()
  let current = -1
  let moving = false
  let size: Size | undefined
  /** The width every wall is drawn at: the photo you face contained in the ground, less the gutter. */
  let width = 0
  let layer: HotspotLayer | undefined
  let mapView: WalkMap | undefined
  let signs: HTMLButtonElement[] = []
  let lastTarget: string | null = null
  let seal: HTMLElement | undefined
  /** The line, in px from the viewport's top, the seal lands above (the story intro's speech box; see `placeSeal`). */
  let sealAbove: (() => number) | undefined
  /** Resolves once the first photo and its Hotspots are live. */
  let markLive: () => void = () => undefined
  const live = new Promise<void>((resolve) => {
    markLive = resolve
  })

  function texture(index: number): Promise<Texture<HTMLImageElement>> {
    let loaded = textures.get(index)
    if (loaded === undefined) {
      loaded = loader.loadAsync(photoUrl(play.roomId, index)).then(
        (map) => {
          map.colorSpace = SRGBColorSpace
          return map
        },
        (error: unknown) => {
          textures.delete(index) // the next walk to this photo asks again
          throw error
        },
      )
      textures.set(index, loaded)
    }
    return loaded
  }

  function turnZone(side: string): HTMLElement {
    const zone = document.createElement('div')
    zone.className = `walk-zone ${side}`
    zone.addEventListener('click', () => void turn(side === 'is-left' ? 'left' : 'right'))
    return zone
  }

  function turnDisc(side: string, label: string, icon: string): HTMLButtonElement {
    const disc = document.createElement('button')
    disc.type = 'button'
    disc.className = `walk-turn ${side}`
    disc.setAttribute('aria-label', label)
    disc.innerHTML = icon
    const tip = document.createElement('span')
    tip.className = 'walk-turn-tip'
    tip.setAttribute('aria-hidden', 'true') // the disc's name says it
    tip.textContent = label
    disc.append(tip)
    disc.hidden = true
    disc.addEventListener('click', () => void turn(side === 'is-left' ? 'left' : 'right'))
    return disc
  }

  /** The walls of the area photo `index` stands in, replacing the last area's; posed around `index`. */
  function layArea(index: number): void {
    const ring = areas[areaOf(areas, index)]?.ring ?? [index]
    walls = new Map(
      ring.map((shown) => {
        const element = document.createElement('div')
        element.className = 'scene-wall'
        const drift = document.createElement('div')
        drift.className = 'scene-wall-drift'
        const rest = document.createElement('div')
        rest.className = 'scene-wall-rest'
        const image = document.createElement('img')
        image.className = 'scene-wall-photo'
        image.src = photoUrl(play.roomId, shown)
        image.alt = '' // a wall; the photo you face carries the name
        image.draggable = false
        const shade = document.createElement('div')
        shade.className = 'scene-wall-shade'
        rest.append(image)
        drift.append(rest, shade)
        element.append(drift)
        return [shown, { element, drift, rest }]
      }),
    )
    world.replaceChildren(...[...walls.values()].map(({ element }) => element))
    pose()
  }

  /** Poses every wall by its offset from the photo you face (`wallPose`); only that one takes input. */
  function pose(): void {
    const ring = [...walls.keys()]
    const here = ring.indexOf(current)
    for (const [shown, { element }] of walls) {
      const offset = ring.indexOf(shown) - here
      const { transform, opacity } = wallPose(offset, width)
      element.style.transform = transform
      element.style.opacity = String(opacity)
      element.style.zIndex = String(10 - Math.abs(offset))
      element.classList.toggle('is-centre', offset === 0)
      element.classList.toggle('is-left', offset === -1)
      element.classList.toggle('is-right', offset === 1)
      element.inert = offset !== 0
      if (offset === 0) element.removeAttribute('aria-hidden')
      else element.setAttribute('aria-hidden', 'true')
    }
  }

  /** Sizes the walls and the canvas to the photo you face, contained in the ground at its full height, and draws. */
  function render(): void {
    if (size === undefined) return
    const box = ground.getBoundingClientRect()
    const fitted = contain(size, { width: box.width - WALL_GUTTER_PX, height: box.height })
    // On the frame, so the note, the pack and the chest place themselves by the photo too.
    frame.style.setProperty('--wall-width', `${fitted.width}px`)
    frame.style.setProperty('--wall-height', `${fitted.height}px`)
    if (fitted.width !== width) {
      width = fitted.width
      pose()
    }
    renderer.setSize(fitted.width, fitted.height)
    renderer.render(scene, camera)
    placeSeal()
  }

  /** Posts the `use_on` of `item` on `target`, the target's label chip and "Checking" showing until the reply. */
  async function useOn(item: string, target: PlayInteractable): Promise<void> {
    lastTarget = target.id
    const pending = layer?.showPending(target)
    const reply = play.post({ type: 'lock_input', input: { type: 'use_on', item, target: target.id } })
    play.useOn.select(null)
    try {
      await reply
    } finally {
      pending?.()
    }
  }

  async function activate(interactable: PlayInteractable): Promise<void> {
    const item = play.useOn.selected()
    if (item !== null) return useOn(item, interactable)
    lastTarget = interactable.id
    const before = play.state()
    const click: PostedEvent = { type: 'click', interactable_id: interactable.id }
    const pending = layer?.showPending(interactable)
    const reply = await play.post(click).finally(pending)
    const target = room === undefined ? null : foundBy(room, click, before, reply)
    if (target !== null) {
      found.keep(play.id, target)
      if (mounted) layer?.setCollected(reply.inventory, foundTargets(play.id))
    }
    const opened = reply.locks_open.some((id) => !before.locks_open.includes(id))
    if (mounted && !opened) layer?.showLabel(interactable)
  }

  /** Lays the Hotspots of photo `index` of `view` over the photo, over the canvas. */
  function layHotspots(view: PlayView, photoSize: Size, index: number): void {
    layer = hotspotLayer(
      photoSize,
      view.interactables.filter((interactable) => interactable.photo === index),
      {
        onActivate: (interactable) => void activate(interactable).catch(() => undefined),
        onPointerEnter: () => firstPointerResponse(play.id),
        canDrop: () => play.useOn.dragging() !== null,
        onDrop: (interactable) => {
          const item = play.useOn.dragging()
          if (item !== null) void useOn(item, interactable).catch(() => undefined)
        },
      },
    )
    layer.setCollected(play.state().inventory, foundTargets(play.id))
    photo.replaceChildren(renderer.domElement, ...layer.elements)
  }

  /** Hangs one doorway sign per neighbouring area from the top edge of photo `index`, clear of its Hotspots. */
  function laySigns(shown: PlayView, photoSize: Size, index: number): void {
    for (const sign of signs) sign.remove()
    const boxes = shown.interactables
      .filter((interactable) => interactable.photo === index)
      .flatMap((interactable) => (interactable.polygons ?? []).filter((polygon) => polygon.length > 0).map((polygon) => bounds([polygon])))
    const centre = (signCentre(boxes, photoSize.width) / photoSize.width) * 100
    signs = doorways(areas, index).map((area, k) => {
      const sign = document.createElement('button')
      sign.type = 'button'
      sign.className = 'walk-door'
      sign.style.left = `${centre + k * 30}%`
      sign.setAttribute('aria-label', fill(strings.toAreaThroughDoorway, { area: area.label }))
      const chains = document.createElement('span')
      chains.className = 'walk-door-chains'
      const plaque = document.createElement('span')
      plaque.className = 'walk-door-sign'
      plaque.innerHTML = ARCH
      const label = document.createElement('span')
      label.textContent = fill(strings.toArea, { area: area.label })
      const key = document.createElement('kbd')
      key.setAttribute('aria-hidden', 'true')
      key.textContent = '↑'
      plaque.append(label, key)
      sign.append(chains, plaque)
      sign.addEventListener('click', () => void walk(area.entry, sign))
      return sign
    })
    view.append(...signs)
  }

  function reshape(next: PlayView): void {
    const before = room
    room = next
    // A photo still loading lays the new Room's Hotspots when it is live.
    if (before === undefined || size === undefined || view.hidden || layer === undefined) return
    const on = (shown: PlayView): string =>
      JSON.stringify(shown.interactables.filter((interactable) => interactable.photo === current))
    if (on(before) === on(next)) return
    const [stack] = layer.elements
    const focused = stack.contains(document.activeElement) ? document.activeElement?.id : undefined
    layHotspots(next, size, current)
    laySigns(next, size, current)
    if (focused !== undefined) layer.elements[0].querySelector<SVGElement>(`[id="${focused}"]`)?.focus()
    render()
  }

  /** The photo you face, at rest: pushing in slowly from scale 1 again (never under reduced motion). */
  function restAgain(): void {
    for (const { rest } of walls.values()) rest.classList.remove('is-resting')
    const centre = walls.get(current)?.rest
    if (centre === undefined || reduced()) return
    void centre.offsetWidth
    centre.classList.add('is-resting')
  }

  /**
   * Makes photo `index`, the one you now face, live: its texture on the plane, its Hotspots, turn zones and doorway
   * signs on its wall, the turn discs at the ring's ends hidden, and the map lit; `moved` announces the view.
   * Resolves false when the photo could not be fetched or another walk took its place.
   */
  async function arrive(index: number, moved: boolean): Promise<boolean> {
    let map: Texture<HTMLImageElement>
    try {
      map = await texture(index)
    } catch {
      return false
    }
    if (!mounted || index !== current || room === undefined) return false
    size = { width: map.image.width, height: map.image.height }
    material.map = map
    material.needsUpdate = true
    plane.scale.set(size.width, size.height, 1)
    camera.left = -size.width / 2
    camera.right = size.width / 2
    camera.top = size.height / 2
    camera.bottom = -size.height / 2
    camera.updateProjectionMatrix()
    layHotspots(room, size, index)
    laySigns(room, size, index)
    const area = areas[areaOf(areas, index)]
    const name = { Area: areaName(area.label), i: area.ring.indexOf(index) + 1, n: area.ring.length }
    renderer.domElement.setAttribute('aria-label', fill(strings.photoView, name))
    const side = neighbours(areas, index)
    zones.left.hidden = turns.left.hidden = side.left === null
    zones.right.hidden = turns.right.hidden = side.right === null
    walls.get(index)?.rest.append(view)
    frame.classList.remove('is-loading')
    loading.hidden = true
    view.hidden = false
    render()
    restAgain()
    markLive()
    mapView?.setCurrent(index, moved ? viewDescription(areas, room, index) : undefined)
    // The views a next move can reach are fetched ahead, so the swing ends on a photo that is ready.
    for (const next of [side.left, side.right, ...doorways(areas, index).map((area) => area.entry)]) {
      if (next !== null) void texture(next).catch(() => undefined)
    }
    return true
  }

  /** The first photo, behind the loading line. */
  async function show(index: number): Promise<void> {
    if (room === undefined || index === current) return
    current = index
    shownPhoto.set(play.id, index)
    frame.classList.add('is-loading')
    loading.hidden = false
    view.hidden = true
    moving = true
    layArea(index)
    const live = await arrive(index, false)
    moving = false
    if (!live && index === current) current = -1 // a later walk asks again
  }

  /**
   * Walks to photo `to`: a turn within its area, a push-in through the doorway (or toward the middle of the view)
   * into another; a cut under reduced motion. Ignored while a move runs. Focus that the move took from the Scene comes
   * back to the new view's first Hotspot, its doorway sign or a turn disc.
   */
  async function walk(to: number, via?: HTMLElement, quiet = false): Promise<void> {
    if (room === undefined || moving || to === current || areaOf(areas, to) < 0) return
    if (current < 0) return show(to)
    if (!quiet) cue('step')
    const focused = frame.contains(document.activeElement) ? document.activeElement : null
    const across = areaOf(areas, to) !== areaOf(areas, current)
    moving = true
    view.hidden = true // the Hotspots, zones and signs leave with the view; its wall stands in for the photo
    view.remove()
    for (const { rest } of walls.values()) rest.classList.remove('is-resting')
    current = to
    shownPhoto.set(play.id, to)
    const instant = reduced()
    const ready = texture(to).catch(() => undefined)
    if (across) await pushIn(to, via, instant)
    else if (instant) pose()
    else {
      world.classList.add('is-turning')
      pose()
      await pause(TURN_MS)
      world.classList.remove('is-turning')
    }
    await ready
    await arrive(to, !quiet)
    moving = false
    refocus(focused)
  }

  /** Into the area of photo `to`: the area you leave grows and fades from the doorway while the next fades in. */
  async function pushIn(to: number, via: HTMLElement | undefined, instant: boolean): Promise<void> {
    if (instant) return layArea(to)
    const leaving = world.cloneNode(true) as HTMLElement
    leaving.classList.add('is-leaving')
    leaving.inert = true
    leaving.setAttribute('aria-hidden', 'true')
    const box = ground.getBoundingClientRect()
    const door = via?.getBoundingClientRect()
    leaving.style.transformOrigin = door === undefined
      ? '50% 45%'
      : `${((door.left + door.width / 2 - box.left) / box.width) * 100}% ${((door.top + door.height / 2 - box.top) / box.height) * 100 + 18}%`
    ground.append(leaving)
    layArea(to)
    const out = leaving.animate(
      [{ transform: 'scale(1)', opacity: 1, filter: 'blur(0px)' }, { opacity: 0.85, offset: 0.5 },
        { transform: 'scale(1.55)', opacity: 0, filter: 'blur(3px)' }],
      { duration: PUSH_OUT_MS, easing: 'cubic-bezier(.5,0,.75,.2)', fill: 'forwards' },
    )
    const arriving = world.animate(
      [{ transform: 'scale(0.92)', opacity: 0 }, { transform: 'scale(1)', opacity: 1 }],
      { duration: PUSH_IN_MS, delay: PUSH_IN_DELAY_MS, easing: 'cubic-bezier(.2,.7,.2,1)', fill: 'backwards' },
    )
    await Promise.all([out.finished, arriving.finished]).catch(() => undefined)
    leaving.remove()
  }

  function turn(side: 'left' | 'right'): Promise<void> {
    if (current < 0) return Promise.resolve()
    const next = neighbours(areas, current)[side]
    return next === null ? Promise.resolve() : walk(next)
  }

  /** Puts back focus a move took from the Scene: on the disc still shown, else the new view's first control. */
  function refocus(focused: Element | null): void {
    if (focused === null || document.activeElement === focused || !mounted) return
    const disc = [turns.left, turns.right].find((button) => !button.hidden)
    const wasDisc = focused === turns.left || focused === turns.right
    const next = wasDisc ? disc : (photo.querySelector<SVGElement>('.hotspot') ?? signs[0] ?? disc)
    next?.focus()
  }

  /** ArrowLeft and ArrowRight turn, ArrowUp goes through the first doorway; never while the Scene is held inert. */
  function onKey(event: KeyboardEvent): void {
    const move = walkKey(event.key)
    if (move === null || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return
    if (frame.closest('[inert]') !== null || !walksFrom(event.target, frame) || current < 0) return
    event.preventDefault()
    if (move !== 'door') return void turn(move)
    const [area] = doorways(areas, current)
    if (area !== undefined) void walk(area.entry, signs[0])
  }
  window.addEventListener('keydown', onKey)

  /** The pointer drift: the photo you face moves a few pixels against the pointer, the walls 2.4 times as far. */
  let drift = 0
  let pointer = { x: 0, y: 0 }
  function onPointer(event: PointerEvent): void {
    pointer = { x: event.clientX, y: event.clientY }
    if (drift !== 0 || reduced()) return
    drift = requestAnimationFrame(() => {
      drift = 0
      const box = ground.getBoundingClientRect()
      const x = (pointer.x - box.left) / box.width - 0.5
      const y = (pointer.y - box.top) / box.height - 0.5
      for (const [shown, wall] of walls) {
        const k = shown === current ? 1 : 2.4
        wall.drift.style.transform = `translate3d(${-x * 14 * k}px, ${-y * 9 * k}px, 0px)`
      }
    })
  }
  ground.addEventListener('pointermove', onPointer)

  play.onState((state) => {
    if (mounted) layer?.setCollected(state.inventory, foundTargets(play.id))
  })

  /**
   * The way out (spec 5.6): the Hotspot of `target` fills with daylight, a warm light gathers round it over 1200 ms and
   * the area grows 12% toward it over 1400 ms; all of it at once under reduced motion or when `still`.
   */
  async function daylight(target: string | null, still = false): Promise<void> {
    await live
    const shown = room?.interactables.find((interactable) => interactable.id === target)
    if (target === null || shown === undefined || size === undefined) return
    layer?.daylight(target)
    const [x, y] = centroid(shown.polygons ?? [])
    const at = `${(x / size.width) * 100}% ${(y / size.height) * 100}%`
    const warmth = document.createElement('div')
    warmth.className = 'scene-warmth'
    warmth.style.background = `radial-gradient(ellipse 34% 46% at ${at}, #FFF8EAE6 0%, #F6DFAF99 40%, #C9964F33 75%, transparent 100%)`
    walls.get(current)?.rest.append(warmth)
    if (still || reduced()) return
    const box = ground.getBoundingClientRect()
    const photoBox = photo.getBoundingClientRect()
    world.style.transformOrigin = `${photoBox.left - box.left + (x / size.width) * photoBox.width}px ${photoBox.top - box.top + (y / size.height) * photoBox.height}px`
    warmth.animate([{ opacity: 0 }, { opacity: 1 }], { duration: DAYLIGHT_MS, easing: 'ease-out', fill: 'backwards' })
    await world.animate([{ transform: 'scale(1)' }, { transform: 'scale(1.12)' }], {
      duration: EXIT_PUSH_MS,
      easing: 'cubic-bezier(.4,0,.2,1)',
      fill: 'forwards',
    }).finished.catch(() => undefined)
  }

  /**
   * The Trickster's trap (spec 5.5): the lights flicker for 700 ms and 260 ms in the lock seal slams onto the middle of
   * the photo you face (the client never knows which object the way out is), or of the part of it above `above`, where
   * it stays until `lockSeal(false)` lifts it. Under reduced motion there is no flicker and the seal simply appears.
   */
  function lockSeal(on: boolean, above?: () => number): void {
    seal?.remove()
    seal = undefined
    sealAbove = above
    if (!on) return
    seal = document.createElement('div')
    seal.className = 'scene-seal is-slamming'
    seal.append(lockSealSvg())
    view.append(seal)
    placeSeal()
    cue('trap')
    if (reduced()) return
    world.animate(FLICKER, { duration: FLICKER_MS })
  }

  /** Centres the seal between the photo's top and the line it lands above, so the speech box held there leaves it seen. */
  function placeSeal(): void {
    if (seal === undefined || sealAbove === undefined) return
    const photo = view.getBoundingClientRect()
    const line = Math.max(photo.top, Math.min(photo.bottom, sealAbove()))
    seal.style.top = `${(line - photo.top) / 2}px`
  }

  function bloom(target: string | null): void {
    const hold = matchMedia('(prefers-reduced-motion: reduce)').matches ? GLOW_REDUCED_MS : GLOW_MS
    glowOnce(frame, 'is-glowing', hold)
    if (target === null) return
    solved.keep(play.id, target)
    layer?.bloom(target, hold)
  }

  const observer = new ResizeObserver(render)
  observer.observe(ground)
  // A failed room or photo request leaves the loading line; missed polls show the reconnecting state (play.ts).
  rooms
    .then((shown) => {
      if (!mounted) return
      room = shown
      areas = walkGraph(shown.photos)
      frame.prepend(useOnChip(new Map(shown.interactables.map(({ id, label }) => [id, label])), play.useOn))
      mapView = walkMap(areas, (index) => void walk(index))
      frame.append(mapView.element)
      const start = first(shown)
      return show(areaOf(areas, start) < 0 ? areas[0].ring[0] : start)
    })
    .catch(() => undefined)

  function unmount(): void {
    mounted = false
    observer.disconnect()
    window.removeEventListener('keydown', onKey)
    cancelAnimationFrame(drift)
    for (const loaded of textures.values()) void loaded.then((map) => map.dispose(), () => undefined)
    plane.geometry.dispose()
    material.dispose()
    renderer.dispose()
    frame.remove()
  }

  return {
    unmount,
    slots,
    current: () => current,
    live,
    walkTo: async (index, quiet) => {
      while (moving && mounted) await pause(50) // a move under way finishes first
      return walk(index, undefined, quiet)
    },
    daylight,
    coach: feedback.coach,
    lockSeal,
    reshape,
    lastTarget: () => lastTarget,
    bloom,
    say: feedback.say,
  }
}
