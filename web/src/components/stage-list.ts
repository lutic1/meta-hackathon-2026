import './stage-list.css'
import type { StageRow } from '../build-stages.ts'
import { formatDuration } from '../build-stages.ts'
import { strings } from '../strings.ts'
import { fading, reveal } from './fade.ts'
import { speakerPrefix, type Wizard, wizardPortrait } from '../wizards/portrait.ts'

export interface StageList {
  element: HTMLElement
  /**
   * Brings the rows in line with `next`, keyed, so a row, a line or an introduction already shown is never redrawn;
   * a row `next` leaves out is removed.
   */
  update: (next: readonly StageRow[]) => void
}

interface RowView {
  element: HTMLLIElement
  name: HTMLElement
  sentBack: HTMLElement
  results: HTMLElement
  lineSlot: HTMLElement
  introSlot: HTMLElement
  model: HTMLElement
  duration: HTMLElement
  line: string | null
}

function text<K extends keyof HTMLElementTagNameMap>(tag: K, className: string, content = ''): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag)
  element.className = className
  element.textContent = content
  return element
}

/** An in-character line in `wizard-line`, its speaker named first for screen readers only. */
function spoken(className: string, speaker: Wizard, line: string): HTMLElement {
  const element = text('p', `${className} wizard-line`)
  element.append(speakerPrefix(speaker), line)
  return element
}

/** A wizard's introduction: the 48 px portrait beside the name in `label`, the role line and the voice line. */
function introduction(wizard: Wizard, name: string, role: string, voice: string): HTMLElement {
  const intro = text('div', 'stage-intro')
  const who = text('div', 'stage-intro-text')
  who.append(
    text('p', 'stage-intro-name label', name),
    text('p', 'stage-intro-role body-sm', role),
    spoken('stage-intro-voice', wizard, voice),
  )
  intro.append(wizardPortrait(wizard, 48), who)
  return intro
}

/**
 * `{components.stage-list-item}` on its `chrome-raised` tray (UX-DR16): the Architect's introduction at the top,
 * drawn once and static, over a hairline rule, then one row per stage: a 12 px marker, the name in `label`, and at
 * the right end the model id and the `mono-sm` duration of a done row. Pending is hollow `text-muted`, running a
 * filled `lamp` with the Architect's line for that stage under its name, done `success` with its plain results in
 * `body-sm`, failed `error-text`; "Finding objects" keeps its line naming the objects in every state once found. The line fades in (200 ms) each time it moves to a newly running row; the
 * Riddler's introduction fades in inside "Writing puzzles" when the author stage starts and stays. A Rewriting row
 * carries "Sent back: …" in `body-sm`. The list is not a live region and takes no focus; every in-character line
 * carries a visually hidden speaker prefix.
 */
export function stageList(): StageList {
  const element = text('section', 'stage-list')
  const rule = text('div', 'stage-list-rule')
  const list = text('ol', 'stage-rows')
  element.append(
    introduction('architect', strings.architect, strings.architectRole, strings.architectVoice),
    rule,
    list,
  )
  const views = new Map<string, RowView>()

  function view(key: string): RowView {
    const existing = views.get(key)
    if (existing !== undefined) return existing
    const row = text('li', 'stage-row')
    const marker = text('span', 'stage-marker')
    marker.setAttribute('aria-hidden', 'true')
    const body = text('div', 'stage-text')
    const created: RowView = {
      element: row,
      name: text('p', 'stage-name label'),
      sentBack: text('p', 'stage-sent-back body-sm'),
      results: text('div', 'stage-results'),
      lineSlot: text('div', 'stage-line-slot'),
      introSlot: text('div', 'stage-intro-slot'),
      model: text('span', 'stage-model'),
      duration: text('span', 'stage-duration'),
      line: null,
    }
    body.append(created.name, created.sentBack, created.results, created.lineSlot, created.introSlot)
    const meta = text('p', 'stage-meta mono-sm')
    meta.append(created.model, created.duration)
    row.append(marker, body, meta)
    views.set(key, created)
    return created
  }

  function update(next: readonly StageRow[]): void {
    // A row the job no longer shows (the test of an attempt the author stage sent back) leaves the list.
    const keys = new Set(next.map((row) => row.key))
    for (const [key, shown] of views) {
      if (keys.has(key)) continue
      shown.element.remove()
      views.delete(key)
    }
    next.forEach((row, index) => {
      const shown = view(row.key)
      shown.element.dataset.state = row.state
      shown.name.textContent = row.name
      shown.sentBack.hidden = row.sentBack === null
      shown.sentBack.textContent = row.sentBack ?? ''
      shown.results.replaceChildren(...row.results.map((result) => text('p', 'stage-result body-sm', result)))
      shown.model.textContent = row.model ?? ''
      shown.duration.textContent = row.durationMs === null ? '' : formatDuration(row.durationMs)
      if (row.line !== shown.line) {
        shown.line = row.line
        const line = row.line === null ? [] : [fading(spoken('stage-line', 'architect', row.line))]
        shown.lineSlot.replaceChildren(...line)
      }
      if (row.riddler && shown.introSlot.childElementCount === 0) {
        shown.introSlot.append(
          fading(introduction('riddler', strings.riddler, strings.riddlerRole, strings.riddlerVoice)),
        )
      }
      const at = list.children[index]
      if (at !== shown.element) list.insertBefore(shown.element, at ?? null)
    })
    reveal(list)
  }

  return { element, update }
}
