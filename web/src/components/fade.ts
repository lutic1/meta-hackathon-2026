import './fade.css'

/**
 * The 200 ms state fade (DESIGN.md Motion): `element`, created hidden by `fading`, is shown with an opacity
 * transition once it is in the page. Under reduced motion the transition is instant (tokens.css).
 */
export function fading<T extends HTMLElement>(element: T): T {
  element.classList.add('fade')
  return element
}

const HIDDEN = '.fade:not(.is-shown)'

/** Shows `root` and every `fading` element under it that is still hidden; a reflow first, so the transition runs. */
export function reveal(root: HTMLElement): void {
  const hidden = [...(root.matches(HIDDEN) ? [root] : []), ...root.querySelectorAll<HTMLElement>(HIDDEN)]
  if (hidden.length === 0) return
  void root.offsetWidth
  for (const element of hidden) element.classList.add('is-shown')
}
