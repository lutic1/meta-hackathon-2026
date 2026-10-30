import './treasure-chest.css'
import type { PlayView, SessionState } from '../../types'
import { RequestFailed } from '../api/index.ts'
import { announce } from '../live-region.ts'
import type { PlaySession } from '../play.ts'
import { CHEST_HINTS, chestCount, chestName, hintAnnouncement, riddleNumber, spendLine } from '../riddles.ts'
import { strings } from '../strings.ts'
import { speakerPrefix, wizardPortrait } from '../wizards/portrait.ts'
import { cardAnnouncement, cardText } from './trickster-card.ts'

/** The Trickster's bubble by the chest is held this long (spec 3.2). */
export const BUBBLE_MS = 7000
/** A gem's flight from the chest to the note (spec 5.4). */
export const GEM_FLIGHT_MS = 650

const reduced = (): boolean => matchMedia('(prefers-reduced-motion: reduce)').matches

const CHEST_ART =
  '<svg viewBox="0 0 96 72" aria-hidden="true"><ellipse cx="48" cy="69" rx="44" ry="4" fill="#0A0806" opacity=".7"/>' +
  '<g class="chest-inner"><path d="M12 31h72v6H12z" fill="#F4C470"/><ellipse cx="48" cy="31" rx="34" ry="7" fill="#F4C470" opacity=".55"/></g>' +
  '<rect x="10" y="32" width="76" height="35" rx="3" fill="#4A2E18"/><rect x="10" y="32" width="76" height="6" fill="#3A2312"/>' +
  '<rect x="24" y="32" width="6" height="35" fill="#B08A4E"/><rect x="66" y="32" width="6" height="35" fill="#B08A4E"/>' +
  '<rect x="42" y="38" width="12" height="14" rx="2" fill="#B08A4E"/><circle cx="48" cy="44" r="2.2" fill="#2A1D11"/>' +
  '<rect x="47" y="45" width="2" height="4" fill="#2A1D11"/><g class="chest-lid"><path d="M10 32 Q10 12 48 10 Q86 12 86 32Z" fill="#5A3820"/>' +
  '<path d="M24 31 Q24 14 30 12.2 L30 31Z M66 12.2 Q72 14 72 31 L66 31Z" fill="#B08A4E"/>' +
  '<path d="M10 32 Q10 12 48 10 Q86 12 86 32" fill="none" stroke="#2A1D11" stroke-width="1.5"/></g>' +
  '<rect x="10" y="32" width="76" height="35" rx="3" fill="none" stroke="#2A1D11" stroke-width="1.5"/></svg>'

/** Where a bought hint lands on the Riddle note. */
export interface HintLanding {
  hintSlot: () => HTMLElement
  hintArrived: () => void
}

export interface TreasureChest {
  /** The chest on the floor right of the photo, the Trickster's bubble above it and its dialog. */
  element: HTMLElement
  /** Draws `state`: the gems from `hints_left`, and each new Trickster Card in the bubble. */
  render: (state: SessionState) => void
  /** The Trickster's bubble above the chest, held 7 s; `text` is announced once as the Trickster's. */
  bubble: (text: string) => void
  /** Closes the dialog, if open, without moving focus: a beat takes the stage. */
  shut: () => void
  /** The refetched Effective room (AD-12): the riddle numbers and Card labels it gives. */
  reshape: (view: PlayView) => void
}

function paragraph(className: string, ...children: (Node | string)[]): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = className
  element.append(...children)
  return element
}

function dialogButton(label: string, className: string, onActivate: () => void): HTMLButtonElement {
  const element = document.createElement('button')
  element.type = 'button'
  element.className = `chest-button ${className}`
  element.textContent = label
  element.addEventListener('click', onActivate)
  return element
}

/**
 * The Treasure chest (story mode, owner decision Oct 29; build spec 1.4): it stands on the floor right of the photo,
 * two gems over the illustrated chest, named "Treasure chest" over "{k} hints for the whole house", "1 hint …" or
 * "Empty", every count from the server's `hints_left`, never a client count. A click (or Enter) opens a dialog above
 * it that takes and traps focus (Tab cycles its buttons; Escape or "Not yet" closes it and focus returns to the
 * chest): with hints left, "Open the chest?" and "Spend 1 of your {k} hints on riddle {n}. There are only 2 for the
 * whole house." over "Open it" and "Not yet"; empty, "The chest is empty" with the Trickster's "Empty. I did warn
 * you." and "Back to the room". "Open it" posts one `hint_request` with no `puzzle_id` (AD-4: the server answers for
 * the active riddle, the one the note shows); on the reply the dialog closes, one gem flies to the note (spec 5.4,
 * a cut under reduced motion), the hint pinned there glows once, focus returns to the chest and the live region reads
 * "The Guide's hint, nudge: {text}". A reply that opened no Rung (the No-hint line) spends nothing and goes to
 * `onNoHint`; a refusal `hint_cap_reached` (409) shows the empty chest. Each new Trickster Card (`cards[]`, after the
 * first state) shows in the Trickster's bubble above the chest for 7 s and is announced once; it stays in the Card
 * log. `onOpen` hears each opening (the coach pill steps aside).
 */
export function treasureChest(
  room: PlayView,
  play: PlaySession,
  note: HintLanding,
  onOpen: () => void,
  onNoHint: (line: string) => void,
): TreasureChest {
  const element = document.createElement('div')
  element.className = 'treasure-chest'
  const chest = document.createElement('button')
  chest.type = 'button'
  chest.className = 'chest'
  chest.setAttribute('aria-haspopup', 'dialog')
  const gems = document.createElement('span')
  gems.className = 'chest-gems'
  gems.setAttribute('aria-hidden', 'true')
  const gemList = Array.from({ length: CHEST_HINTS }, () => {
    const gem = document.createElement('span')
    gem.className = 'chest-gem'
    return gem
  })
  gems.append(...gemList)
  chest.innerHTML = CHEST_ART
  chest.prepend(gems)
  const label = document.createElement('span')
  label.className = 'chest-label'
  label.setAttribute('aria-hidden', 'true') // the chest's name says it
  const name = document.createElement('span')
  name.className = 'chest-name'
  name.textContent = strings.treasureChest
  const count = document.createElement('span')
  count.className = 'chest-count'
  label.append(name, count)
  const said = document.createElement('div')
  said.className = 'chest-bubble'
  said.setAttribute('aria-hidden', 'true') // announced once through the live region
  said.hidden = true
  const dialog = document.createElement('section')
  dialog.className = 'chest-dialog'
  dialog.setAttribute('role', 'dialog')
  dialog.setAttribute('aria-modal', 'true')
  dialog.setAttribute('aria-labelledby', 'chest-dialog-heading')
  dialog.hidden = true
  element.append(said, dialog, chest, label)

  let latest = play.state()
  let cardsHeard = latest.cards.length
  let bubbleTimer: ReturnType<typeof setTimeout> | undefined
  let asking = false

  function draw(state: SessionState): void {
    const left = state.hints_left
    gemList.forEach((gem, k) => gem.classList.toggle('is-spent', k >= left))
    chest.classList.toggle('is-empty', left <= 0)
    chest.setAttribute('aria-label', chestName(left))
    count.textContent = chestCount(left)
  }

  function bubble(text: string, speaker = true): void {
    const words = document.createElement('div')
    words.append(paragraph('chest-bubble-name label', strings.trickster), paragraph('wizard-line', text))
    said.replaceChildren(wizardPortrait('trickster', 32), words)
    said.hidden = false
    if (speaker) announce(`${strings.speakerTrickster} ${text}`)
    clearTimeout(bubbleTimer)
    bubbleTimer = setTimeout(() => {
      said.hidden = true
    }, BUBBLE_MS)
  }

  function close(): void {
    dialog.hidden = true
    dialog.replaceChildren()
    chest.classList.remove('is-open')
    chest.focus({ preventScroll: true })
  }

  /** Fills the dialog with `heading`, `content` and `buttons`, opens it and focuses its first button. */
  function open(heading: string, content: Node[], buttons: HTMLButtonElement[]): void {
    const title = document.createElement('h3')
    title.id = 'chest-dialog-heading'
    title.className = 'chest-dialog-heading'
    title.textContent = heading
    const row = document.createElement('div')
    row.className = 'chest-dialog-row'
    row.append(...buttons)
    dialog.replaceChildren(title, ...content, row)
    dialog.hidden = false
    chest.classList.add('is-open')
    buttons[0]?.focus({ preventScroll: true })
  }

  function openEmpty(): void {
    const line = document.createElement('div')
    line.className = 'chest-dialog-line'
    line.append(wizardPortrait('trickster', 36), paragraph('wizard-line', speakerPrefix('trickster'), strings.chestEmptyLine))
    open(strings.chestIsEmpty, [line], [dialogButton(strings.backToTheRoom, 'is-ink', close)])
  }

  function offer(): void {
    if (!dialog.hidden) return close()
    onOpen()
    said.hidden = true
    if (latest.hints_left <= 0) return openEmpty()
    const n = riddleNumber(room.puzzles, latest.locks_open, latest.active_puzzle_id ?? '')
    const spend = dialogButton(strings.openIt, 'is-ink', () => void spendOne(spend))
    open(strings.openTheChest, [paragraph('chest-dialog-plain', spendLine(latest.hints_left, n))], [spend, dialogButton(strings.notYet, 'is-quiet', close)])
  }

  /** The gem flying from the chest to the note's hint slot through a point 80 px above the middle (spec 5.4). */
  async function fly(from: Element): Promise<void> {
    if (reduced()) return
    const start = from.getBoundingClientRect()
    const end = note.hintSlot().getBoundingClientRect()
    const gem = document.createElement('span')
    gem.className = 'chest-gem is-flying'
    gem.style.left = `${start.left}px`
    gem.style.top = `${start.top}px`
    document.body.append(gem)
    const dx = end.left + 40 - start.left
    const dy = end.top + 4 - start.top
    const flight = gem.animate(
      [
        { transform: 'translate(0px, 0px) rotate(45deg) scale(1)' },
        { transform: `translate(${dx / 2}px, ${dy / 2 - 80}px) rotate(225deg) scale(1.6)` },
        { transform: `translate(${dx}px, ${dy}px) rotate(405deg) scale(1)`, opacity: 0.3 },
      ],
      { duration: GEM_FLIGHT_MS, easing: 'cubic-bezier(.5,0,.3,1)' },
    )
    await flight.finished.catch(() => undefined)
    gem.remove()
  }

  async function spendOne(button: HTMLButtonElement): Promise<void> {
    if (asking) return
    asking = true
    button.setAttribute('aria-busy', 'true')
    const gem = gemList[Math.max(0, latest.hints_left - 1)]
    try {
      const reply = (await play.post({ type: 'hint_request' })).hint_reply ?? null
      if (reply === null || reply.rung === 0) {
        close()
        if (reply !== null) onNoHint(reply.text)
        return
      }
      dialog.hidden = true
      dialog.replaceChildren()
      await fly(gem)
      note.hintArrived()
      announce(hintAnnouncement(reply.rung, reply.text))
      close()
    } catch (error) {
      if (error instanceof RequestFailed && error.code === 'hint_cap_reached') openEmpty()
      // Anything else never reached the server: the dialog stays for another try.
    } finally {
      asking = false
      button.removeAttribute('aria-busy')
    }
  }

  chest.addEventListener('click', offer)
  dialog.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation() // a held item stays in hand
      close()
      return
    }
    if (event.key !== 'Tab') return
    const buttons = [...dialog.querySelectorAll('button')]
    const at = buttons.indexOf(document.activeElement as HTMLButtonElement)
    event.preventDefault()
    buttons[(at + (event.shiftKey ? -1 : 1) + buttons.length) % buttons.length]?.focus()
  })

  function render(state: SessionState): void {
    latest = state
    draw(state)
    const arrived = state.cards.slice(cardsHeard)
    const first = cardsHeard === 0
    cardsHeard = state.cards.length
    const newest = arrived.at(-1)
    if (newest === undefined) return
    const text = cardText(room, newest)
    bubble(text.sentence, false)
    announce(arrived.map((card, k) => cardAnnouncement(cardText(room, card), first && k === 0)).join(' '))
  }

  draw(latest)
  return {
    element,
    render,
    bubble: (text) => bubble(text),
    shut: () => {
      dialog.hidden = true
      dialog.replaceChildren()
      chest.classList.remove('is-open')
    },
    reshape: (view) => {
      room = view
    },
  }
}
