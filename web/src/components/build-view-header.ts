import './build-view-header.css'
import type { BuildView } from '../../types'
import { fill, strings } from '../strings.ts'
import { secondaryButton } from './button.ts'

const WEEKDAY = new Intl.DateTimeFormat('en-US', { weekday: 'short' })
const MONTH = new Intl.DateTimeFormat('en-US', { month: 'short' })

/** A Build's time as the untitled-Room title reads it, "Tue Nov 3, 10:42", in the viewer's time zone. */
export function buildTime(iso: string): string {
  const date = new Date(iso)
  const minutes = String(date.getMinutes()).padStart(2, '0')
  return `${WEEKDAY.format(date)} ${MONTH.format(date)} ${date.getDate()}, ${date.getHours()}:${minutes}`
}

/** `template` filled with `values`, each value in its own `mono-sm` span (the header's numbers). */
function withNumbers(template: string, values: Record<string, number>): (string | HTMLElement)[] {
  return template.split(/\{(\w+)\}/).map((part, index) => {
    if (index % 2 === 0) return part
    const number = document.createElement('span')
    number.className = 'mono-sm'
    number.textContent = String(values[part])
    return number
  })
}

function line(className: string, ...content: (string | HTMLElement)[]): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = className
  element.append(...content)
  return element
}

export interface BuildViewHeader {
  element: HTMLElement
  /** The title, which takes the initial focus; null while the Build has no Room yet (the not-ready state). */
  title: HTMLElement | null
}

/**
 * `{components.build-view-header}` (UX-DR48): a `chrome` row with the Room's name as its `display-md` title and the
 * build time beside it, or the build time as the title when the Room has no name; "Regenerations: n of {max}" with
 * `mono-sm` numbers; one "Attempt {k} sent back: …" line per failed attempt with its fixed messages; and "Back".
 * The title is in the Tab order ahead of "Back". Without a `BuildView` (not ready) the row holds "Back" alone.
 */
export function buildViewHeader(view: BuildView | null, onBack: () => void): BuildViewHeader {
  const element = document.createElement('section')
  element.className = 'build-view-header'
  const back = secondaryButton({ label: strings.back, onActivate: onBack })
  if (view === null) {
    element.append(back)
    return { element, title: null }
  }
  const time = buildTime(view.built_at)
  const title = document.createElement('h1')
  title.className = 'build-view-title display-md'
  title.tabIndex = 0
  title.textContent = view.name || time
  const heading = document.createElement('div')
  heading.className = 'build-view-heading'
  heading.append(title)
  if (view.name) heading.append(line('build-view-time body-sm', time))
  const text = document.createElement('div')
  text.className = 'build-view-header-text'
  text.append(
    heading,
    line('build-view-meta body-sm', ...withNumbers(strings.regenerations, { n: view.regeneration_count, max: view.regen_max })),
    ...view.sent_back.map(({ attempt, messages }) =>
      line('build-view-sent body-sm', fill(strings.attemptSentBack, { k: attempt, messages: messages.join(' ') })),
    ),
  )
  element.append(text, back)
  return { element, title }
}
