import './error-banner.css'
import { secondaryButton } from './button.ts'

export interface BannerAction {
  label: string
  onActivate: () => void
}

/** One banner state: `{components.error-banner}`, or its `{components.warning-banner}` variant. */
export interface BannerState {
  variant: 'error' | 'warning'
  heading: string
  /** One plain sentence; the FR-1 refusal has none, its verbatim string being the heading. */
  sentence?: string
  actions: readonly BannerAction[]
}

function banner({ variant, heading, sentence, actions }: BannerState): HTMLElement {
  const element = document.createElement('div')
  element.className = `banner banner-${variant}`
  element.setAttribute('role', 'alert')
  element.tabIndex = -1
  const text = document.createElement('div')
  text.className = 'banner-text'
  const title = document.createElement('h2')
  title.className = 'banner-heading display-sm'
  title.textContent = heading
  text.append(title)
  if (sentence !== undefined) {
    const body = document.createElement('p')
    body.className = 'banner-sentence body-md'
    body.textContent = sentence
    text.append(body)
  }
  const buttons = document.createElement('div')
  buttons.className = 'banner-actions'
  buttons.append(...actions.map((action) => secondaryButton(action)))
  element.append(text, buttons)
  return element
}

/** The banner slot at the top of a surface's left area: full width, one banner at a time, never a portrait. */
export function bannerSlot(): HTMLElement {
  const slot = document.createElement('div')
  slot.className = 'banner-slot'
  return slot
}

/** Shows `state` in `slot`, replacing any older banner, and moves focus to it; null clears the slot. Returns the banner. */
export function showBanner(slot: HTMLElement, state: BannerState | null): HTMLElement | null {
  if (state === null) {
    slot.replaceChildren()
    return null
  }
  const element = banner(state)
  slot.replaceChildren(element)
  element.focus()
  return element
}
