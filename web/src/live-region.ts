// The one polite live region (UX-DR70, NFR-14). It sits outside #app, so a route change never replaces it, and the
// shell inserts it before anything is written to it, so a screen reader is already watching when a line lands.

let region: HTMLElement | undefined

/** The page's single `aria-live="polite"` region, inserted at the end of `<body>` on first use. */
export function liveRegion(): HTMLElement {
  if (region === undefined) {
    region = document.createElement('div')
    region.className = 'visually-hidden'
    region.setAttribute('aria-live', 'polite')
    document.body.append(region)
  }
  return region
}

/** Writes `text` to the live region; each call is one announcement. */
export function announce(text: string): void {
  liveRegion().textContent = text
}
