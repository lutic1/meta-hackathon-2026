import './scene.css'
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
import { bannerSlot, showBanner } from '../components/error-banner.ts'
import { feedbackLine } from '../components/feedback-line.ts'
import { GLOW_MS, GLOW_REDUCED_MS } from '../components/hint-area.ts'
import { objectCounts, type ThumbnailStrip, thumbnailStrip } from '../components/thumbnail-strip.ts'
import { glowOnce } from '../fade.ts'
import { foundBy } from '../feedback.ts'
import type { PlaySession } from '../play.ts'
import { strings } from '../strings.ts'
import { useOnChip } from '../use-on.ts'
import { contain, type Size } from './geometry.ts'
import { type HotspotLayer, hotspotLayer } from './hotspots.ts'

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
  return { unmount: () => frame.remove(), reshape: () => {}, lastTarget: () => null, bloom: () => {}, say }
}

function firstPointerResponse(sessionId: string): void {
  if (responded.has(sessionId)) return
  responded.add(sessionId)
  window.dispatchEvent(new CustomEvent<FirstPointerResponseDetail>(FIRST_POINTER_RESPONSE, { detail: { sessionId } }))
}

/**
 * The Play screen's Scene (FR-11, AD-11): the Scene frame in `root` and the Thumbnail strip at the start of
 * `stripRow`, for the session's Effective room as `GET /sessions/<id>/room` serves it. Each photo from
 * `GET /rooms/<room_id>/photos/<i>` is drawn as a three textured plane, exactly as served (no tone mapping, no
 * light), on a canvas sized to the photo contained in the frame; the photo's Hotspots lie over it in its own pixel
 * space. The frame shows its loading line until a photo and its Hotspots are live. A Hotspot click posts one `click`
 * naming its Interactable and nothing else, its label chip showing with "Checking" beside it until the reply; when
 * the reply opened no lock, the click hit no target and the label chip stays ("{label} · in hand" on an Interactable
 * the Inventory holds, "{label} · found" on a found target). The Hotspots of collected Interactables follow
 * `inventory` in every state the server sends, so a solved `find` target's glow fades out; a click that found a target
 * no `use_on` needs (`foundBy`) keeps it in `foundTargets` for the tab, a reload included, and its glow fades out
 * the same way. An Inventory item dropped on a Hotspot, or a Hotspot activated while an item is selected (whose
 * "Using {item label}" chip is pinned to the frame's top-left), posts one `use_on` lock input naming the item and the Hotspot's Interactable, never a
 * `click` and never a Puzzle (AD-4), and clears the selection; until the reply, the target's label chip shows with
 * "Checking" beside it. The selection outlives photo switches. It opens on photo `first`. The Interactable the latest
 * click or `use_on` named is kept as `lastTarget`, and `bloom` plays the unlock moment (lock-opened.ts): the frame's
 * gilt rule turns lamp with the lamp glow once (in and out by `--motion-hover`, 300 ms in all; held 2 s with no
 * animation under reduced motion) and the solved target's Hotspot, when it is on the shown photo, blooms with it;
 * the target is kept for the tab, a reload included, for the Completion screen's filmstrip (`solvedTargets`).
 * `say` shows the Play screen's feedback line for a reply over the bottom edge of the frame.
 *
 * `reshape` lays the shown photo's Hotspots again from a refetched `PlayView` when its Interactables changed, keeping
 * the photo, the strip (its object counts redrawn in place) and the selection; keyboard focus on a Hotspot that is still there stays on it. Returns the
 * teardown and `reshape`.
 *
 * A browser that cannot start WebGL (hardware acceleration off, or a blocked GPU) has no Scene to draw and no DOM one
 * to fall back to: the frame holds the error banner "Keyframe can't draw this room in this browser." with how to fix
 * it and "Reload", which takes focus, so the Play screen never shows a blank frame.
 */
export function mountScene(
  root: HTMLElement,
  stripRow: HTMLElement,
  play: PlaySession,
  rooms: Promise<PlayView>,
  first = 0,
): MountedScene {
  const frame = document.createElement('div')
  frame.className = 'scene-frame is-loading'
  const ground = document.createElement('div')
  ground.className = 'scene-ground'
  const loading = document.createElement('p')
  loading.className = 'scene-loading body-sm'
  loading.textContent = strings.sceneLoading
  const photo = document.createElement('div')
  photo.className = 'scene-photo'
  photo.hidden = true
  ground.append(loading, photo)
  const feedback = feedbackLine()
  frame.append(ground, feedback.element)
  root.append(frame)

  let renderer: WebGLRenderer
  try {
    renderer = new WebGLRenderer({ antialias: true })
  } catch {
    return sceneUnavailable(frame, ground, feedback.say)
  }
  renderer.setPixelRatio(window.devicePixelRatio)
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
  let current = -1
  let size: Size | undefined
  let layer: HotspotLayer | undefined
  let strip: ThumbnailStrip | undefined
  let lastTarget: string | null = null

  function texture(index: number): Promise<Texture<HTMLImageElement>> {
    let loaded = textures.get(index)
    if (loaded === undefined) {
      loaded = loader.loadAsync(photoUrl(play.roomId, index)).then(
        (map) => {
          map.colorSpace = SRGBColorSpace
          return map
        },
        (error: unknown) => {
          textures.delete(index) // the next switch to this photo asks again
          throw error
        },
      )
      textures.set(index, loaded)
    }
    return loaded
  }

  /** Sizes the canvas to the photo contained in the ground and draws the plane. */
  function render(): void {
    if (size === undefined) return
    const fitted = contain(size, ground.getBoundingClientRect())
    photo.style.width = `${fitted.width}px`
    photo.style.height = `${fitted.height}px`
    renderer.setSize(fitted.width, fitted.height)
    renderer.render(scene, camera)
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

  function reshape(view: PlayView): void {
    const before = room
    room = view
    strip?.setCounts(objectCounts(view))
    // A photo still loading lays the new Room's Hotspots when it is live.
    if (before === undefined || size === undefined || photo.hidden || layer === undefined) return
    const on = (shown: PlayView): string =>
      JSON.stringify(shown.interactables.filter((interactable) => interactable.photo === current))
    if (on(before) === on(view)) return
    const [svg] = layer.elements
    const focused = svg.contains(document.activeElement) ? document.activeElement?.id : undefined
    layHotspots(view, size, current)
    if (focused !== undefined) layer.elements[0].querySelector<SVGElement>(`[id="${focused}"]`)?.focus()
    render()
  }

  async function show(index: number): Promise<void> {
    if (room === undefined || index === current) return
    current = index
    shownPhoto.set(play.id, index)
    strip?.setCurrent(index)
    frame.classList.add('is-loading')
    loading.hidden = false
    photo.hidden = true
    let map: Texture<HTMLImageElement>
    try {
      map = await texture(index)
    } catch {
      if (index === current) current = -1
      return
    }
    if (!mounted || index !== current) return
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
    frame.classList.remove('is-loading')
    loading.hidden = true
    photo.hidden = false
    render()
  }

  play.onState((state) => {
    if (mounted) layer?.setCollected(state.inventory, foundTargets(play.id))
  })

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
    .then((view) => {
      if (!mounted) return
      room = view
      frame.prepend(useOnChip(new Map(view.interactables.map(({ id, label }) => [id, label])), play.useOn))
      strip = thumbnailStrip(play.roomId, objectCounts(view), (index) => void show(index))
      stripRow.prepend(strip.element)
      return show(first)
    })
    .catch(() => undefined)

  function unmount(): void {
    mounted = false
    observer.disconnect()
    for (const loaded of textures.values()) void loaded.then((map) => map.dispose(), () => undefined)
    plane.geometry.dispose()
    material.dispose()
    renderer.dispose()
    frame.remove()
    strip?.element.remove()
  }

  return { unmount, reshape, lastTarget: () => lastTarget, bloom, say: feedback.say }
}
