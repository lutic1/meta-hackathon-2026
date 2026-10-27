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
