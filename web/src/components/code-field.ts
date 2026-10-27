import './code-field.css'
import type { PlayPuzzle, SessionState } from '../../types'
import type { PlaySession } from '../play.ts'
import { fill, strings } from '../strings.ts'
import { secondaryButton } from './button.ts'

/** The field takes up to 6 characters (UX-DR34). */
export const CODE_MAX = 6
/** Submit is disabled below 3 characters. */
export const CODE_MIN = 3

export interface CodeField {
  element: HTMLElement
  /** Draws "Not this · n" from the server's `wrong_attempts` while no input is waiting for its verdict. */
  update: (state: SessionState) => void
}

/**
 * A `code` Puzzle's lock input (`{components.code-field}`, FR-12, UX-DR34, UX-DR38): a 168 x 44 `parchment-shade`
 * inset in `mono-code` taking up to 6 characters, with no visible label or placeholder and the accessible name
 * "Code for Puzzle {n}", then a secondary Submit, disabled below 3 characters, and the feedback chip. Enter or Submit
 * posts exactly one code lock input and the client never compares the code. Until the server answers, the field is
 * read-only and the "Checking" chip shows with its static ellipsis, never announced. "Not this · n" shows the
 * server's count only when it rose since the last input on this lock, and the field keeps its value, selected for
 * retyping; an input that changed nothing (its Puzzle no longer available) only clears "Checking". Opening the lock
 * is drawn by the Wizard notes, which remove the field. The chip's text is the field's accessible description.
 */
export function codeField(puzzle: PlayPuzzle, n: number, play: PlaySession): CodeField {
  const element = document.createElement('div')
  element.className = 'code-lock'

  const field = document.createElement('input')
  field.type = 'text'
  field.className = 'code-field mono-code'
  field.maxLength = CODE_MAX
  field.autocomplete = 'off'
  field.spellcheck = false
  field.setAttribute('autocapitalize', 'off')
  field.setAttribute('aria-label', fill(strings.codeFor, { n }))

  const chip = document.createElement('span')
  chip.id = `code-chip-${puzzle.id}`
  chip.className = 'chip label'
  chip.hidden = true

  let pending = false
  /** Wrong attempts as the server counted them when the latest input was posted; "Not this" shows above it. */
  let since = 0

  function showChip(kind: 'pending' | 'not-this' | null, text = ''): void {
    chip.hidden = kind === null
    chip.className = kind === null ? 'chip label' : `chip chip-${kind} label`
    chip.textContent = text
    if (kind === null) field.removeAttribute('aria-describedby')
    else field.setAttribute('aria-describedby', chip.id)
  }

  function verdict(state: SessionState): void {
    const attempts = state.wrong_attempts[puzzle.id] ?? 0
    if (attempts > since) showChip('not-this', fill(strings.notThis, { n: attempts }))
    else showChip(null)
  }

  /** The whole value selected while the field has focus: the selected-for-retyping tint and edge. */
  function syncSelected(): void {
    const whole = field.value !== '' && field.selectionStart === 0 && field.selectionEnd === field.value.length
    field.classList.toggle('is-selected', whole && document.activeElement === field)
  }

  async function submit(): Promise<void> {
    const code = field.value
    if (pending || code.length < CODE_MIN) return
    pending = true
    since = play.state().wrong_attempts[puzzle.id] ?? 0
    field.readOnly = true
    showChip('pending', `${strings.checking}…`)
    let reply: SessionState
    try {
      reply = await play.post({ type: 'lock_input', input: { type: 'code', puzzle_id: puzzle.id, code } })
    } catch {
      showChip(null) // nothing reached the server, so the input is dropped; the field keeps its value
      return
    } finally {
      pending = false
      field.readOnly = false
    }
    verdict(reply)
    if (!chip.hidden && field.isConnected) {
      field.focus()
      field.select()
      syncSelected()
      chip.scrollIntoView({ block: 'nearest' }) // a narrow side column wraps the chip under the field
    }
  }

  const button = secondaryButton({ label: strings.submit, onActivate: () => void submit(), onParchment: true })
  button.disabled = true
  field.addEventListener('input', () => {
    button.disabled = field.value.length < CODE_MIN
    syncSelected()
  })
  field.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return
    event.preventDefault()
    void submit()
  })
  for (const name of ['select', 'keyup', 'pointerup', 'focus', 'blur']) field.addEventListener(name, syncSelected)

  element.append(field, button, chip)

  function update(state: SessionState): void {
    if (!pending) verdict(state)
  }

  return { element, update }
}
