import './attract-frame.css'
import '../scene/scene.css'
import type { PlayView } from '../../types'
import { photoUrl } from '../api/index.ts'
import { contain, hotspotPath, type Size, topLeft } from '../scene/geometry.ts'
import { CHIP_OFFSET_PX, hotspotReveal } from '../scene/hotspots.ts'
import { fill, strings } from '../strings.ts'
import { speakerPrefix, wizardPortrait } from '../wizards/portrait.ts'
import { attractSlides, type AttractSlide } from './attract-slides.ts'

const SVG = 'http://www.w3.org/2000/svg'

/** Each photo holds this long before the next crossfades in over it (`--motion-attract`, 600 ms). */
export const HOLD_MS = 4000

interface Slide extends AttractSlide {
  /** The layer over the ground that crossfades: the photo plate, its Hotspot and chip. */
  element: HTMLElement
  /** The plate sized to the photo contained in the ground; the image fills it and the Hotspot lies over it. */
  plate: HTMLElement
  /** The Hotspot overlay, given the photo's pixel space as its viewBox once the photo has loaded. */
  svg: SVGSVGElement | null
  chip: HTMLElement | null
  /** The clue line under the frame, crossfading with the slide. */
  line: HTMLElement
  /** The photo's pixel size once loaded. */
  size?: Size
  loading?: Promise<Size>
}

export interface AttractFrame {
  element: HTMLElement
  /** Stops the cycle and drops what it holds outside the element. */
  unmount: () => void
}

function slideElement(view: PlayView, slide: AttractSlide): Slide {
  const element = document.createElement('div')
  element.className = 'attract-slide'
  const plate = document.createElement('div')
  plate.className = 'attract-photo'
  let svg: SVGSVGElement | null = null
  let chip: HTMLElement | null = null
  const { interactable } = slide
  if (interactable !== null) {
    svg = document.createElementNS(SVG, 'svg')
    svg.setAttribute('class', 'scene-hotspots')
    svg.setAttribute('preserveAspectRatio', 'none')
    const hotspot = document.createElementNS(SVG, 'g')
    hotspot.setAttribute('class', 'hotspot')
    hotspot.append(hotspotReveal(hotspotPath(interactable.polygons ?? [])))
    svg.append(hotspot)
    chip = document.createElement('div')
    chip.className = 'hotspot-label-chip label is-shown'
    chip.textContent = interactable.label
    plate.append(svg, chip)
  }
  element.append(plate)

  const { puzzle } = slide
  const line = document.createElement('div')
  line.className = 'attract-clue-line'
  if (puzzle !== null) {
    const clue = document.createElement('p')
    clue.className = 'wizard-line'
    clue.append(speakerPrefix('riddler'), puzzle.clue)
    const tag = document.createElement('span')
    tag.className = 'chip chip-current label'
    tag.textContent = fill(strings.lockOfM, { n: view.puzzles.indexOf(puzzle) + 1, m: view.puzzles.length })
    line.append(clue, tag)
  }
  return { ...slide, element, plate, svg, chip, line }
}

/**
 * The attract frame of the Hosted landing (DESIGN.md Hosted landing, Motion): a Scene frame that plays the Demo
 * room `view` by itself. Its photos crossfade in order, each held 4 s, over the frame's ground, which takes the first
 * photo's aspect (`--attract-aspect`), so the photos fill it without wide bars, contained as the Scene contains them;
 * on each lies the lit Hotspot reveal and label chip of its first scenery Interactable, drawn from the polygons as the
 * Scene draws them, and with the frame, on parchment, a Riddler's clue whose Evidence is not on that photo with its
 * "Lock {n} of {m}" tag (`attractSlides`; a photo without either shows the photo alone, the clue row keeping its
 * height). The frame is one control named "Play {name}": a click or Enter calls `onStart`, the verb's path. The
 * cycle pauses while the pointer is over the frame or it has focus, and while the tab is hidden; under reduced motion
 * the first photo stays, with its Hotspot and clue, and nothing cycles. Photos load one ahead of the cycle, never all
 * at once; a photo that fails is passed over. Resolves once the first photo has loaded, with the
 * frame, or null when the Room has no photos or that photo fails to load, so the landing keeps its layout without it.
 * Everything shown is read from the `PlayView`, so no solution or Derived field reaches the page.
 */
export async function attractFrame(view: PlayView, name: string, onStart: () => void): Promise<AttractFrame | null> {
  const slides = attractSlides(view).map((slide) => slideElement(view, slide))
  if (slides.length === 0) return null
  const element = document.createElement('section')
  element.className = 'attract'
  const frame = document.createElement('div')
  frame.className = 'attract-frame scene-frame'
  frame.setAttribute('role', 'button')
  frame.tabIndex = 0
  frame.setAttribute('aria-label', fill(strings.attractFrame, { name }))
  const ground = document.createElement('div')
  ground.className = 'scene-ground'
  ground.append(...slides.map(({ element }) => element))
  frame.append(ground)
  const clue = document.createElement('div')
  clue.className = 'attract-clue'
  const lines = document.createElement('div')
  lines.className = 'attract-clue-lines'
  lines.append(...slides.map(({ line }) => line))
  clue.append(wizardPortrait('riddler', 32), lines)
  element.append(frame, clue)

  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches
  let mounted = true
  let shown = -1
  let hovered = false
  let focused = false
  let timer: ReturnType<typeof setTimeout> | undefined

  /** Sizes the slide's plate to its photo contained in the ground and places the chip 8 px above its Hotspot. */
  function place(slide: Slide): void {
    if (slide.size === undefined) return
    const fitted = contain(slide.size, ground.getBoundingClientRect())
    slide.plate.style.width = `${fitted.width}px`
    slide.plate.style.height = `${fitted.height}px`
    if (slide.chip === null || slide.interactable === null) return
    const scale = fitted.width / slide.size.width
    const [left, top] = topLeft(slide.interactable.polygons ?? [])
    slide.chip.style.left = `${left * scale}px`
    const bottom = Math.min(fitted.height - top * scale + CHIP_OFFSET_PX, fitted.height - slide.chip.offsetHeight)
    slide.chip.style.bottom = `${bottom}px`
  }

  /** Loads the slide's photo the first time it is asked for; the image stays on its plate once it has loaded. */
  function load(index: number): Promise<Size> {
    const slide = slides[index]
    if (slide.loading === undefined) {
      slide.loading = new Promise<Size>((resolve, reject) => {
        const img = document.createElement('img')
        img.className = 'attract-photo-image'
        img.alt = ''
        img.addEventListener('load', () => {
          slide.size = { width: img.naturalWidth, height: img.naturalHeight }
          slide.svg?.setAttribute('viewBox', `0 0 ${slide.size.width} ${slide.size.height}`)
          slide.plate.prepend(img)
          place(slide)
          resolve(slide.size)
        })
        img.addEventListener('error', () => reject(new Error(`photo ${slide.photo} failed to load`)))
        img.src = photoUrl(view.id, slide.photo)
      })
    }
    return slide.loading
  }

  function show(index: number): void {
    if (shown !== -1) {
      slides[shown].element.classList.remove('is-shown')
      slides[shown].line.classList.remove('is-shown')
      slides[shown].line.setAttribute('aria-hidden', 'true')
    }
    shown = index
    slides[index].element.classList.add('is-shown')
    slides[index].line.classList.add('is-shown')
    slides[index].line.removeAttribute('aria-hidden')
    void load((index + 1) % slides.length).catch(() => undefined)
  }

  /** The next photo that loads takes the frame; a photo that fails is passed over. */
  async function next(): Promise<void> {
    for (let step = 1; step < slides.length; step++) {
      const index = (shown + step) % slides.length
      try {
        await load(index)
      } catch {
        continue
      }
      if (!mounted || hovered || focused || document.hidden) return
      show(index)
      break
    }
    schedule()
  }

  function schedule(): void {
    clearTimeout(timer)
    if (reduced || hovered || focused || document.hidden || slides.length < 2) return
    timer = setTimeout(() => void next(), HOLD_MS)
  }

  frame.addEventListener('pointerenter', () => {
    hovered = true
    schedule()
  })
  frame.addEventListener('pointerleave', () => {
    hovered = false
    schedule()
  })
  frame.addEventListener('focusin', () => {
    focused = true
    schedule()
  })
  frame.addEventListener('focusout', () => {
    focused = false
    schedule()
  })
  document.addEventListener('visibilitychange', schedule)
  frame.addEventListener('click', onStart)
  frame.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' && event.target === frame) onStart()
  })

  const first = await load(0).catch(() => null)
  if (first === null) return null
  frame.style.setProperty('--attract-aspect', `${first.width} / ${first.height}`)
  for (const slide of slides) slide.line.setAttribute('aria-hidden', 'true')
  show(0)
  const observer = new ResizeObserver(() => slides.forEach(place))
  observer.observe(ground)
  schedule()

  function unmount(): void {
    mounted = false
    clearTimeout(timer)
    observer.disconnect()
    document.removeEventListener('visibilitychange', schedule)
  }

  return { element, unmount }
}
