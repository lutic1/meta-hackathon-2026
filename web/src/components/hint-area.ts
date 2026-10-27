import './hint-area.css'
import type { HintReply, Meta, PlayView, RungChangeEvent, SessionState } from '../../types'
import { fadeIn } from '../fade.ts'
import { announce } from '../live-region.ts'
import type { PlaySession } from '../play.ts'
import { fill, strings } from '../strings.ts'
import { speakerPrefix, wizardPortrait } from '../wizards/portrait.ts'
import { primaryButton } from './button.ts'

/** The arrival glow lights for this long and fades by `--motion-hover` each way: 300 ms in all (DESIGN.md Motion). */
export const GLOW_MS = 150
/** Under reduced motion the lit ring is held this long, with no animation (NFR-14). */
export const GLOW_REDUCED_MS = 2000

/** The label of each Rung, by its number: 0 is the No-hint line, labelled with its Puzzle alone. */
const RUNG_LABELS = [strings.puzzleHeading, strings.rungNudge, strings.rungDirection, strings.rungNearAnswer]

/** The Rung a line shows, by its Puzzle and number. */
interface Shown {
  puzzle_id: string
  rung: number
}

/** One Guide line: its label (none for the opening line), its words and the Rung it shows (none for a non-Rung). */
interface Line {
  label: string | null
  text: string
  shown: Shown | null
}

/** "Puzzle {n} · Nudge", "· Direction" or "· Near-answer", or "Puzzle {n}" alone for the No-hint line (rung 0). */
export function rungLabel(n: number, rung: number): string {
  return fill(RUNG_LABELS[rung] ?? strings.puzzleHeading, { n })
}

/** Every Rung change but the one on the Rung line, which are the opened Rungs the Wizard notes keep. */
export function openedRungs(changes: readonly RungChangeEvent[], shown: Shown | null): RungChangeEvent[] {
  return changes.filter(
    (change) => shown === null || change.puzzle_id !== shown.puzzle_id || change.rung !== shown.rung,
  )
}

export interface HintArea {
  element: HTMLElement
  /** Draws `state`: the field's label from the Active puzzle, and each newly arrived `rung_change` as the Rung line. */
  render: (state: SessionState) => void
  /** After "Begin": the opening line as the first Guide line, never announced, unless a Rung line already shows. */
  opening: (line: string) => void
  /** The slot under the helper line that holds the Triggers toggle and its panel. */
  triggers: HTMLElement
}

/** `--motion-state` in ms as the page resolves it now ("200ms" or ".2s"): 200, or 0 under reduced motion. */
function stateFadeMs(): number {
  const value = getComputedStyle(document.documentElement).getPropertyValue('--motion-state').trim()
  return (parseFloat(value) || 0) * (value.endsWith('ms') ? 1 : 1000)
}

function paragraph(className: string): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = className
  return element
}

/**
 * The Hint area (`{components.hint-area}`, FR-14, UX-DR30 to UX-DR32): a `chrome-raised` tray pinned under the Wizard
 * notes, up to `{spacing.hint-area-max}`, its upper part scrolling (the Rung line) over a lower part that never
 * scrolls: the hint field and "Ask the Guide", the permanent helper line, and the slot of the Triggers toggle. While
 * the Triggers panel is open (`is-triggers-open`) the tray may grow past its cap until the Wizard notes reach
 * `{spacing.notes-min}`.
 *
 * Enter or the button posts exactly one `hint_request` with no `puzzle_id`: the server answers for the Active puzzle,
 * the entry marked "Current". The typed text is never read, so it leaves the browser in no body, query or header; it
 * stays visible in the read-only field while the button reads "Asking" and one request is in flight, and clears when
 * the reply lands. With `guide` `ollama` the Guide portrait shows the static `lamp` ring and "thinking on this Mac"
 * until then; with `verbatim` no thinking state ever shows.
 *
 * The Rung line (`{components.rung-line}`) is the Guide portrait, the label "Puzzle {n} · {Rung name}" ("Puzzle {n}"
 * alone on the No-hint line) and the line. Every new line fades the shown one out and itself in (200 ms each way,
 * instant under reduced motion), so a reply that repeats the shown line still visibly arrives, and is announced in
 * the one live region as "The Guide: …". A `rung_change` in a state the server sent (never computed here, and its
 * words taken from `rung_changes[]`) shows the same way with one arrival glow on the portrait ring and the tray edge;
 * a reply the player asked for never glows. The line the Rung line no longer shows moves into its Puzzle's opened
 * Rungs, through `onOpened`. The first state is only read: the latest `rung_change`, else the opening line, is drawn
 * without a fade, a glow or an announcement, so a reload rebuilds the Rungs and re-announces nothing.
 */
export function hintArea(
  room: PlayView,
  play: PlaySession,
  guide: Meta['guide'],
  onOpened: (lines: readonly RungChangeEvent[]) => void,
): HintArea {
  const element = document.createElement('section')
  element.className = 'hint-area'
  element.setAttribute('aria-label', strings.hintArea)

  const upper = document.createElement('div')
  upper.className = 'hint-upper'
  const rungLine = document.createElement('div')
  rungLine.className = 'rung-line'
  rungLine.hidden = true
  const portrait = wizardPortrait('guide', 48)
  const words = document.createElement('div')
  words.className = 'rung-line-words'
  const label = paragraph('rung-label label')
  const thinking = paragraph('rung-thinking label')
  thinking.textContent = strings.thinkingOnThisMac
  const said = paragraph('rung-text wizard-line')
  words.append(label, thinking, said)
  rungLine.append(portrait, words)
  upper.append(rungLine)

  const lower = document.createElement('div')
  lower.className = 'hint-lower'
  const ask = document.createElement('div')
  ask.className = 'hint-ask'
  const field = document.createElement('input')
  field.type = 'text'
  field.className = 'hint-field body-sm'
  field.placeholder = strings.hintPlaceholder
  field.autocomplete = 'off'
  const helper = paragraph('hint-helper body-sm')
  helper.id = 'hint-helper'
  helper.textContent = strings.hintHelper
  field.setAttribute('aria-describedby', helper.id)
  const button = primaryButton({ label: strings.askTheGuide, pendingLabel: strings.asking, onActivate: request })
  field.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return
    event.preventDefault()
    button.click() // the button ignores it while a request is in flight
  })
  ask.append(field, button)
  const triggers = document.createElement('div')
  triggers.className = 'hint-triggers' // the Triggers toggle and its panel
  lower.append(ask, helper, triggers)
  element.append(upper, lower)

  const place = (puzzleId: string | null): number | null => {
    const index = room.puzzles.findIndex((puzzle) => puzzle.id === puzzleId)
    return index < 0 ? null : index + 1
  }
  let latest = play.state()
  /** How many `rung_changes` have been drawn; only those after it arrive. */
  let heard = latest.rung_changes.length
  let version = 0
  let glowing: ReturnType<typeof setTimeout> | undefined

  function changeLine(change: RungChangeEvent): Line {
    const n = place(change.puzzle_id)
    return { label: n === null ? null : rungLabel(n, change.rung), text: change.text, shown: change }
  }

  function replyLine(reply: HintReply): Line {
    const { puzzle_id, rung, text } = reply
    const n = place(puzzle_id)
    const shown = puzzle_id !== null && rung > 0 ? { puzzle_id, rung } : null // the No-hint line is no Rung
    return { label: n === null ? null : rungLabel(n, rung), text, shown }
  }

  function think(on: boolean): void {
    rungLine.classList.toggle('is-thinking', on)
    thinking.hidden = !on
    label.hidden = on || label.textContent === ''
    said.hidden = on
    rungLine.hidden = !on && said.textContent === ''
  }

  function draw(line: Line): void {
    label.textContent = line.label ?? ''
    said.replaceChildren(speakerPrefix('guide'), line.text)
    words.classList.remove('is-leaving')
    think(false)
    onOpened(openedRungs(latest.rung_changes, line.shown))
  }

  function glow(): void {
    const hold = matchMedia('(prefers-reduced-motion: reduce)').matches ? GLOW_REDUCED_MS : GLOW_MS
    clearTimeout(glowing)
    element.classList.add('is-glowing')
    glowing = setTimeout(() => element.classList.remove('is-glowing'), hold)
  }

  /** Fades the shown line out, then `line` in; `arrived` glows once. The latest call wins a fade still running. */
  function present(line: Line, arrived: boolean): void {
    const mine = ++version
    const swap = (): void => {
      if (mine !== version || !element.isConnected) return
      draw(line)
      fadeIn(words)
      if (arrived) glow()
    }
    const fade = rungLine.hidden ? 0 : stateFadeMs()
    if (fade === 0) {
      swap()
      return
    }
    words.classList.add('is-leaving')
    setTimeout(swap, fade)
  }

  async function request(): Promise<void> {
    field.readOnly = true
    if (guide === 'ollama') think(true)
    try {
      const reply = (await play.post({ type: 'hint_request' })).hint_reply ?? null
      field.value = ''
      if (reply === null) {
        think(false)
        return
      }
      announce(`${strings.speakerGuide} ${reply.text}`)
      present(replyLine(reply), false)
    } catch {
      think(false) // nothing reached the server; the field keeps its words (the reconnecting state lands in 1.24)
    } finally {
      field.readOnly = false
    }
  }

  function render(state: SessionState): void {
    latest = state
    const n = place(state.active_puzzle_id)
    field.setAttribute('aria-label', n === null ? strings.askTheGuide : fill(strings.hintFieldLabel, { n }))
    const arrived = state.rung_changes.slice(heard)
    heard = state.rung_changes.length
    const newest = arrived.at(-1)
    if (newest === undefined) return
    announce(arrived.map((change) => `${strings.speakerGuide} ${change.text}`).join(' '))
    present(changeLine(newest), true)
  }

  function opening(line: string): void {
    if (rungLine.hidden) present({ label: null, text: line, shown: null }, false)
  }

  render(latest)
  const last = latest.rung_changes.at(-1)
  if (last !== undefined) draw(changeLine(last))
  else if (play.openingLine !== null) draw({ label: null, text: play.openingLine, shown: null })
  else think(false)

  return { element, render, opening, triggers }
}
