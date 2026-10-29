/**
 * Fades `element` in from transparent, by its own `opacity` transition (CSS has no animations: nothing loops). Call
 * it once the element is in the document; its stylesheet gives `.is-arriving` opacity 0, and reduced motion makes the
 * change instant.
 */
export function fadeIn(element: HTMLElement): void {
  element.classList.add('is-arriving')
  void getComputedStyle(element).opacity // the transparent start is drawn before the class leaves
  element.classList.remove('is-arriving')
}

/** A `--motion-*` token in ms as the page resolves it now ("200ms" or ".2s"); 0 under reduced motion. */
export function motionMs(token: `--motion-${string}`): number {
  const value = getComputedStyle(document.documentElement).getPropertyValue(token).trim()
  return (parseFloat(value) || 0) * (value.endsWith('ms') ? 1 : 1000)
}

/** `--motion-state` in ms: 200, or 0 under reduced motion. */
export function stateFadeMs(): number {
  return motionMs('--motion-state')
}

const glowing = new WeakMap<Element, ReturnType<typeof setTimeout>>()

/**
 * Lights `element` once by `className`, whose stylesheet fades it in and out: the class is removed after `hold` ms
 * (DESIGN.md Motion: 150 ms lit between the two `--motion-hover` fades, 300 ms in all; 2 s with no animation under
 * reduced motion). A second glow before then restarts the hold.
 */
export function glowOnce(element: Element, className: string, hold: number): void {
  clearTimeout(glowing.get(element))
  element.classList.add(className)
  glowing.set(element, setTimeout(() => element.classList.remove(className), hold))
}
