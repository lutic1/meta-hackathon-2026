import './portrait.css'
import { strings } from '../strings.ts'

export type Wizard = 'architect' | 'riddler' | 'guide' | 'trickster'

/** UX-DR29: 24 (Card log, Demo room card, Model table), 32 (signature, In play block, the Completion sheet's
 * "Built by" row), 48 (Hint area, Cards, introductions, Completion sign-off) or 96 px (the landing's cast, the
 * Narrow-screen message); story mode adds 26 (a hint on the Riddle note), 30 (the
 * feedback line), 36 (the empty chest) and 40 (the Riddle note's Riddler and the closing sheet's lines). */
export type PortraitSize = 24 | 26 | 30 | 32 | 36 | 40 | 48 | 96

const SPEAKERS: Record<Wizard, string> = {
  architect: strings.speakerArchitect,
  riddler: strings.speakerRiddler,
  guide: strings.speakerGuide,
  trickster: strings.speakerTrickster,
}

/** The committed painting `scripts/portraits.py` writes under `web/public/portraits/` (FR-23). */
export function portraitUrl(wizard: Wizard): string {
  return `/portraits/${wizard}.webp`
}

const paintings = new Map<Wizard, Promise<void>>()

/** Resolves once the wizard's painting has loaded, rejects when it is missing; asked once per page. */
function painting(wizard: Wizard): Promise<void> {
  let loaded = paintings.get(wizard)
  if (loaded === undefined) {
    loaded = new Promise((resolve, reject) => {
      const image = new Image()
      image.onload = () => resolve()
      image.onerror = () => reject(new Error(`${portraitUrl(wizard)} is missing`))
      image.src = portraitUrl(wizard)
    })
    paintings.set(wizard, loaded)
  }
  return loaded
}

/**
 * The Wizard portrait (`{components.wizard-portrait}`, UX-DR29): a circle with a 2 px gilt ring at `size` px,
 * decorative beside the line that names its speaker (empty alt). It shows the placeholder, the wizard's initial in
 * `display-sm` gilt on `chrome-raised`, until the painting has loaded, and keeps it when the file is missing, so a
 * broken image never shows. Play never generates one.
 */
export function wizardPortrait(wizard: Wizard, size: PortraitSize): HTMLElement {
  const element = document.createElement('span')
  element.className = 'wizard-portrait'
  element.style.setProperty('--portrait-size', `${size}px`)
  const initial = document.createElement('span')
  initial.className = 'wizard-portrait-initial display-sm'
  initial.setAttribute('aria-hidden', 'true')
  initial.textContent = wizard.charAt(0).toUpperCase()
  element.append(initial)
  painting(wizard).then(
    () => {
      const image = document.createElement('img')
      image.src = portraitUrl(wizard)
      image.alt = ''
      image.width = size
      image.height = size
      element.replaceChildren(image)
    },
    () => undefined, // the placeholder stays
  )
  return element
}

/** The visually hidden speaker prefix ("The Riddler:") that starts each in-character line for screen readers. */
export function speakerPrefix(wizard: Wizard): HTMLElement {
  const prefix = document.createElement('span')
  prefix.className = 'visually-hidden'
  prefix.textContent = `${SPEAKERS[wizard]} `
  return prefix
}
