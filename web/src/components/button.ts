import './button.css'

export interface PrimaryButtonOptions {
  label: string
  /** Shown while `onActivate` is in flight; repeat activation is ignored until it settles. */
  pendingLabel: string
  onActivate: () => Promise<void>
}

export interface SecondaryButtonOptions {
  label: string
  onActivate: () => void
  /** `lamp-ink` label and border for a button that sits on parchment (Code field Submit). */
  onParchment?: boolean
}

export interface ToggleButtonOptions {
  label: string
  /** `pressed` ("Show all objects") or `expanded` (the Triggers toggle, "Show the build JSON"). */
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

/** `{components.button-primary}`: lamp fill, `on-lamp` label, 44 px; Enter and Space activate it. */
export function primaryButton({ label, pendingLabel, onActivate }: PrimaryButtonOptions): HTMLButtonElement {
  const element = button('button-primary', label)
  let pending = false
  element.addEventListener('click', () => {
    if (pending) return
    pending = true
    element.textContent = pendingLabel
    element.setAttribute('aria-busy', 'true')
    void onActivate().finally(() => {
      pending = false
      element.textContent = label
      element.removeAttribute('aria-busy')
    })
  })
  return element
}

/** `{components.button-secondary}`: 40 px, 1 px lamp border; `lamp-ink` on parchment. */
export function secondaryButton({ label, onActivate, onParchment = false }: SecondaryButtonOptions): HTMLButtonElement {
  const element = button('button-secondary', label)
  element.classList.toggle('on-parchment', onParchment)
  element.addEventListener('click', onActivate)
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
