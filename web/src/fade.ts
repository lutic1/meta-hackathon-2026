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

/** `--motion-state` in ms as the page resolves it now ("200ms" or ".2s"): 200, or 0 under reduced motion. */
export function stateFadeMs(): number {
  const value = getComputedStyle(document.documentElement).getPropertyValue('--motion-state').trim()
  return (parseFloat(value) || 0) * (value.endsWith('ms') ? 1 : 1000)
}
