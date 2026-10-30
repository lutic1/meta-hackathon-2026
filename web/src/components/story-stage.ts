import './story-stage.css'
import type { PlayInteractable } from '../../types'
import { announce } from '../live-region.ts'
import { fill, strings } from '../strings.ts'
import { portraitUrl, type Wizard } from '../wizards/portrait.ts'
import { crop } from './crop.ts'
import { waxSeal } from './wax-seal.ts'

const NAMES: Record<Wizard, string> = {
  architect: strings.architect,
  riddler: strings.riddler,
  guide: strings.guide,
  trickster: strings.trickster,
}

/** Where each painting is framed in its tall arch (spec 1.2). */
const CROPS: Record<Wizard, string> = {
  architect: '28% 40%',
  trickster: '86% 40%',
  riddler: '58% 40%',
  guide: '52% 40%',
}

/** One beat: who speaks (lit, on the left), their role line, the line, and the button that moves on. */
export interface StoryBeat {
  speaker: Wizard
  role: string
  line: string
  button: string
  /** A solve beat: the light stage, the shorter portrait and the row "Riddle {n} solved" with its wax seal. */
  solved?: number
  /** The item the solve put in the pack, shown as a crop beside "In your pack now: {label}. …". */
  item?: { roomId: string; interactable: PlayInteractable }
}

export interface StoryStage {
  element: HTMLElement
  /** Shows `beat` and resolves once Next is pressed: its button, or Enter anywhere. Focus moves to the button. */
  play: (beat: StoryBeat) => Promise<void>
  /** Takes the stage away. */
  close: () => void
}

/**
 * The Story stage (story mode, owner decision Oct 29; build spec 1.2): a stage over the Scene, below the top bar, on a
 * scrim rising from the bottom ("light" for a solve beat, so the room stays in view), with the speaker's tall painted
 * portrait in its gilt arch at the left and the parchment speech box: a brass name plate with the name and role line,
 * the optional "Riddle {n} solved" row with its wax seal, the line (whole, at once: no typing effect), the optional
 * pack row, and the button with its Enter key cap. Each beat's spoken line goes to the live region once, as
 * "{name}: {line}"; focus moves to the button, and Enter anywhere presses it. The portrait's slide and the seal's
 * stamp belong to DESIGN.md Motion's walk and story exception and are off under reduced motion.
 */
export function storyStage(): StoryStage {
  const element = document.createElement('section')
  element.className = 'story-stage'
  element.hidden = true
  const scrim = document.createElement('div')
  scrim.className = 'story-scrim'
  const figure = document.createElement('figure')
  figure.className = 'story-portrait'
  const frame = document.createElement('div')
  frame.className = 'story-portrait-frame'
  const painting = document.createElement('img')
  painting.alt = '' // the name plate says who speaks
  frame.append(painting)
  figure.append(frame)
  const box = document.createElement('div')
  box.className = 'story-box'
  const plate = document.createElement('div')
  plate.className = 'story-plate'
  const name = document.createElement('b')
  const role = document.createElement('small')
  plate.append(name, role)
  const solved = document.createElement('p')
  solved.className = 'story-solved label'
  const line = document.createElement('p')
  line.className = 'story-line'
  const item = document.createElement('p')
  item.className = 'story-item'
  const foot = document.createElement('div')
  foot.className = 'story-foot'
  const next = document.createElement('button')
  next.type = 'button'
  next.className = 'story-next'
  foot.append(next)
  box.append(plate, solved, line, item, foot)
  element.append(scrim, figure, box)

  let advance: (() => void) | null = null
  function press(): void {
    const done = advance
    advance = null
    done?.()
  }
  next.addEventListener('click', press)
  function onKey(event: KeyboardEvent): void {
    if (event.key !== 'Enter' || advance === null || event.target === next) return
    event.preventDefault()
    press()
  }

  function play(beat: StoryBeat): Promise<void> {
    element.classList.toggle('is-light', beat.solved !== undefined)
    element.setAttribute('aria-label', NAMES[beat.speaker])
    painting.src = portraitUrl(beat.speaker)
    painting.style.objectPosition = CROPS[beat.speaker]
    name.textContent = NAMES[beat.speaker]
    role.textContent = beat.role
    solved.hidden = beat.solved === undefined
    if (beat.solved !== undefined) solved.replaceChildren(waxSeal(beat.solved), fill(strings.riddleSolved, { n: beat.solved }))
    line.textContent = beat.line
    item.hidden = beat.item === undefined
    if (beat.item !== undefined) {
      const words = document.createElement('span')
      words.textContent = fill(strings.inYourPack, { label: beat.item.interactable.label })
      item.replaceChildren(crop(beat.item.roomId, beat.item.interactable, 44, 34), words)
    }
    const key = document.createElement('kbd')
    key.setAttribute('aria-hidden', 'true')
    key.textContent = strings.keyEnter
    next.replaceChildren(beat.button, key)
    element.hidden = false
    figure.classList.remove('is-in')
    requestAnimationFrame(() => figure.classList.add('is-in'))
    window.addEventListener('keydown', onKey)
    announce(`${NAMES[beat.speaker]}: ${beat.line}`)
    next.focus({ preventScroll: true })
    return new Promise((resolve) => {
      advance = resolve
    })
  }

  function close(): void {
    advance = null
    element.hidden = true
    window.removeEventListener('keydown', onKey)
  }

  return { element, play, close }
}
