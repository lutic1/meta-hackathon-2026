import './button.css'

export interface PrimaryButtonOptions {
  /** Its label, or a function read again each time a request settles (a label that follows the state). */
  label: string | (() => string)
  /** Shown while `onActivate` is in flight; repeat activation is ignored until it settles. */
  pendingLabel: string
  onActivate: () => Promise<void>
}

export type SecondaryButtonOptions = {
  label: string
  /** `lamp-ink` label and border for a button that sits on parchment (Code field Submit). */
  onParchment?: boolean
} & (
  | { pendingLabel?: undefined; onActivate: () => void }
  | {
      /** Shown while `onActivate` is in flight; repeat activation is ignored until it settles. */
      pendingLabel: string
      onActivate: () => Promise<void>
    }
)

export interface SecondaryLinkOptions {
  label: string
  href: string
  /** `lamp-ink` label and border for a link that sits on parchment (the Completion sheet). */
  onParchment?: boolean
}

export interface ToggleButtonOptions {
  label: string
  /** `pressed` ("Show all objects") or `expanded` ("How hints work", "Show the build JSON"). */
  state: 'pressed' | 'expanded'
  on?: boolean
  /** Id of the element an `expanded` toggle opens. */
  controls?: string
  onToggle: (on: boolean) => void
}

function button(className: string, label: string): HTMLButtonElement {
  const element = document.createElement('button')
  element.type = 'button'
  element.className = className
  element.textContent = label
  return element
}

/**
 * Calls `onActivate` on each click, showing `pendingLabel` and `aria-busy` while it is in flight and ignoring repeat
 * activation until it settles, then `settled()` again; the button keeps its focus throughout.
 */
function activateWhilePending(
  element: HTMLButtonElement,
  pendingLabel: string,
  settled: () => string,
  onActivate: () => Promise<void>,
): void {
  let pending = false
  element.addEventListener('click', () => {
    if (pending) return
    pending = true
    element.textContent = pendingLabel
    element.setAttribute('aria-busy', 'true')
    void onActivate().finally(() => {
      pending = false
      element.textContent = settled()
      element.removeAttribute('aria-busy')
    })
  })
}

/** `{components.button-primary}`: lamp fill, `on-lamp` label, 44 px; Enter and Space activate it. */
export function primaryButton({ label, pendingLabel, onActivate }: PrimaryButtonOptions): HTMLButtonElement {
  const settled = (): string => (typeof label === 'string' ? label : label())
  const element = button('button-primary', settled())
  activateWhilePending(element, pendingLabel, settled, onActivate)
  return element
}

/** `{components.button-secondary}`: 40 px, 1 px lamp border; `lamp-ink` on parchment. */
export function secondaryButton(options: SecondaryButtonOptions): HTMLButtonElement {
  const { label, onParchment = false } = options
  const element = button('button-secondary', label)
  element.classList.toggle('on-parchment', onParchment)
  if (options.pendingLabel === undefined) element.addEventListener('click', options.onActivate)
  else activateWhilePending(element, options.pendingLabel, () => label, options.onActivate)
  return element
}

/** A link drawn as `{components.button-secondary}`; Enter follows it, as on any link. */
export function secondaryLink({ label, href, onParchment = false }: SecondaryLinkOptions): HTMLAnchorElement {
  const element = document.createElement('a')
  element.className = 'button-secondary'
  element.classList.toggle('on-parchment', onParchment)
  element.href = href
  element.textContent = label
  return element
}

/** A secondary button that announces its pressed or expanded state and holds the pressed fill and 2 px border. */
export function toggleButton({ label, state, on = false, controls, onToggle }: ToggleButtonOptions): HTMLButtonElement {
  const element = button('button-secondary', label)
  const attribute = state === 'pressed' ? 'aria-pressed' : 'aria-expanded'
  if (controls !== undefined) element.setAttribute('aria-controls', controls)
  element.setAttribute(attribute, String(on))
  element.addEventListener('click', () => {
    const next = element.getAttribute(attribute) !== 'true'
    element.setAttribute(attribute, String(next))
    onToggle(next)
  })
  return element
}
