import './status-strip.css'

/** `{components.status-strip}`: one plain 32 px line, no portrait, no glow; it never takes focus. */
export function statusStrip(text: string): HTMLElement {
  const strip = document.createElement('div')
  strip.className = 'status-strip body-sm'
  strip.textContent = text
  return strip
}
