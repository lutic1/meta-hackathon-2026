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
import type { PlayInteractable, PlayView, SessionState } from '../../types'
import { getRoom, photoUrl, postEvent } from '../api/index.ts'
import { type ThumbnailStrip, thumbnailStrip } from '../components/thumbnail-strip.ts'
import { strings } from '../strings.ts'
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

function firstPointerResponse(sessionId: string): void {
  if (responded.has(sessionId)) return
  responded.add(sessionId)
  window.dispatchEvent(new CustomEvent<FirstPointerResponseDetail>(FIRST_POINTER_RESPONSE, { detail: { sessionId } }))
}

/**
 * The Play screen's Scene column (FR-11, AD-11): the Scene frame over the Thumbnail strip, for the session's Room
 * from `GET /rooms/<room_id>`. Each photo from `GET /rooms/<room_id>/photos/<i>` is drawn as a three textured plane,
 * exactly as served (no tone mapping, no light), on a canvas sized to the photo contained in the frame; the photo's
 * Hotspots lie over it in its own pixel space. The frame shows its loading line until a photo and its Hotspots are
 * live. A Hotspot click posts one `click` naming its Interactable and nothing else; when the reply opened no lock,
 * the click hit no target and the label chip shows. Returns the teardown.
 */
export function mountScene(root: HTMLElement, session: SessionState): () => void {
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
  frame.append(ground)
  root.append(frame)

  const renderer = new WebGLRenderer({ antialias: true })
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
  let latest = session
  let room: PlayView | undefined
  let current = -1
  let size: Size | undefined
  let layer: HotspotLayer | undefined
  let strip: ThumbnailStrip | undefined

  function texture(index: number): Promise<Texture<HTMLImageElement>> {
    let loaded = textures.get(index)
    if (loaded === undefined) {
      loaded = loader.loadAsync(photoUrl(session.room_id, index)).then(
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

  async function activate(interactable: PlayInteractable): Promise<void> {
    const reply = await postEvent(session.id, { type: 'click', interactable_id: interactable.id })
    const opened = reply.locks_open.some((id) => !latest.locks_open.includes(id))
    latest = reply
    if (mounted && !opened) layer?.showLabel(interactable)
  }

  async function show(index: number): Promise<void> {
    if (room === undefined || index === current) return
    current = index
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
    layer = hotspotLayer(
      size,
      room.interactables.filter((interactable) => interactable.photo === index),
      {
        onActivate: (interactable) => void activate(interactable).catch(() => undefined),
        onPointerEnter: () => firstPointerResponse(session.id),
      },
    )
    photo.replaceChildren(renderer.domElement, ...layer.elements)
    frame.classList.remove('is-loading')
    loading.hidden = true
    photo.hidden = false
    render()
  }

  const observer = new ResizeObserver(render)
  observer.observe(ground)
  // A failed room or photo request leaves the loading line; the reconnecting state lands in 1.24.
  getRoom(session.room_id)
    .then((view) => {
      if (!mounted) return
      room = view
      strip = thumbnailStrip(session.room_id, view.photos.length, (index) => void show(index))
      root.append(strip.element)
      return show(0)
    })
    .catch(() => undefined)

  return () => {
    mounted = false
    observer.disconnect()
    for (const loaded of textures.values()) void loaded.then((map) => map.dispose(), () => undefined)
    plane.geometry.dispose()
    material.dispose()
    renderer.dispose()
    frame.remove()
    strip?.element.remove()
  }
}
