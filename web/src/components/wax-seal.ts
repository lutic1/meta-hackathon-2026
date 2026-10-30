const SVG = 'http://www.w3.org/2000/svg'

/** A wobbly wax outline around (cx, cy): `points` steps round a circle of radius `r`, each nudged by `seed`. */
function blob(cx: number, cy: number, r: number, points: number, seed: number): string {
  let d = ''
  for (let k = 0; k <= points; k++) {
    const a = (k / points) * Math.PI * 2
    const rr = r * (1 + 0.07 * Math.sin(a * 5 + seed) + 0.04 * Math.sin(a * 11 + seed * 2))
    d += `${k === 0 ? 'M' : 'L'}${(cx + rr * Math.cos(a)).toFixed(1)} ${(cy + rr * Math.sin(a)).toFixed(1)}`
  }
  return `${d}Z`
}

function part(name: string, attributes: Record<string, string>): SVGElement {
  const element = document.createElementNS(SVG, name)
  for (const [key, value] of Object.entries(attributes)) element.setAttribute(key, value)
  return element
}

/**
 * A red wax seal stamped with the riddle number `n` (story mode): its dashed empty slot, and the wax drawn over it once
 * the riddle is solved (`.wax-seal-wax`, shown by the stylesheet that places it). Decorative: the words beside it say it.
 */
export function waxSeal(n: number): SVGSVGElement {
  const svg = part('svg', { viewBox: '0 0 42 42', 'aria-hidden': 'true', class: 'wax-seal' }) as SVGSVGElement
  const wax = part('g', { class: 'wax-seal-wax' })
  const number = part('text', { x: '21', y: '26.5', 'text-anchor': 'middle', class: 'wax-seal-number' })
  number.textContent = String(n)
  wax.append(
    part('path', { d: blob(21, 21, 19, 48, n * 1.7), class: 'wax-seal-blob' }),
    part('circle', { cx: '21', cy: '21', r: '12.5', class: 'wax-seal-ring' }),
    number,
  )
  svg.append(part('circle', { cx: '21', cy: '21', r: '17', class: 'wax-seal-slot' }), wax)
  return svg
}
