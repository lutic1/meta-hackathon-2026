import type { PlayView } from '../types'
import { secondaryButton } from './components/button.ts'
import { type CardLogDialog, cardLogDialog } from './components/card-log.ts'
import type { PlaySession } from './play.ts'
import { strings } from './strings.ts'

/** The top bar's "Card log" button, which opens a dialog. */
export function cardLogButton(onActivate: () => void): HTMLButtonElement {
  const button = secondaryButton({ label: strings.cardLog, onActivate })
  button.setAttribute('aria-haspopup', 'dialog')
  return button
}

/** What the Card log takes from the Play screen. */
export interface CardLogFrame {
  /** The page body, which takes the scrim. */
  body: HTMLElement
  /** The top bar, the Scene column and the side column, inert while the Card log shows. */
  held: readonly HTMLElement[]
  /** The Room the Card labels number their Puzzles from; nothing opens before it is read. */
  room: Promise<PlayView>
  play: PlaySession
}

export interface CardLog {
  /** The top bar's "Card log" button. */
  button: HTMLButtonElement
  /** Opens the Card log from `opener`, where focus returns when it closes; never over itself. */
  open: (opener: HTMLElement) => void
  /** Whether the Card log shows, so no other modal opens over it. */
  isOpen: () => boolean
  /** Closes the Card log and removes the button. */
  unmount: () => void
}

/**
 * The Card log on the Play screen (FR-19, UX-DR43, UX-DR8, UX-DR71): the top bar's "Card log" button, or the Hint
 * area's "{n} more in the Card log" link, opens `{components.card-log}` over the scrim, its right edge under the
 * button's. It lists every entry of the session state's `cards[]`, oldest first, the dismissed ones and those a
 * reload rebuilt included, and takes each Card a later state brings while it shows. Focus starts on the close control
 * and is trapped in the dialog, with every element in `held` inert; Escape or the close control closes it and returns
 * focus to the control that opened it. Under the First-room welcome, the Leave room confirmation and the Completion
 * screen the top bar and the side column are already inert, so it never opens over another modal. Opening or closing
 * it writes nothing to the live region.
 */
export function mountCardLog(frame: CardLogFrame): CardLog {
  let room: PlayView | undefined
  let shown: { dialog: CardLogDialog; listed: number } | undefined
  let close: (() => void) | undefined
  frame.room.then(
    (view) => {
      room = view
    },
    () => undefined, // the Play screen shows what a missing Room means
  )

  const button = cardLogButton(() => open(button))

  function open(opener: HTMLElement): void {
    if (close !== undefined || room === undefined) return
    const dialog = cardLogDialog(room)
    const cards = frame.play.state().cards
    dialog.add(cards)
    shown = { dialog, listed: cards.length }
    /** No pointer press outside the dialog moves focus out of it; inside, rows stay selectable and scrollable. */
    const keepFocus = (event: MouseEvent): void => {
      if (!(event.target instanceof Node) || !dialog.dialog.contains(event.target)) event.preventDefault()
    }
    const trap = (event: KeyboardEvent): void => {
      if (event.key === 'Escape') {
        event.preventDefault()
        event.stopPropagation()
        shut()
        return
      }
      if (event.key !== 'Tab') return
      event.preventDefault()
      dialog.close.focus() // the close control is the dialog's one control
    }
    /** Lines the dialog's right edge up with the button's, measured against the body that holds the scrim. */
    const anchor = (): void => {
      const right = frame.body.getBoundingClientRect().right - button.getBoundingClientRect().right
      dialog.dialog.style.right = `${Math.max(0, right)}px`
    }

    for (const element of frame.held) element.inert = true
    anchor() // before the dialog enters the page, so no layout read draws it opaque ahead of the fade
    frame.body.append(dialog.element)
    window.addEventListener('resize', anchor)
    document.addEventListener('mousedown', keepFocus, true)
    document.addEventListener('keydown', trap, true)
    dialog.show()
    dialog.close.focus()

    close = () => {
      close = undefined
      shown = undefined
      window.removeEventListener('resize', anchor)
      document.removeEventListener('mousedown', keepFocus, true)
      document.removeEventListener('keydown', trap, true)
      dialog.element.remove()
      for (const element of frame.held) element.inert = false
    }
    function shut(): void {
      close?.()
      opener.focus()
    }
    dialog.close.addEventListener('click', shut)
  }

  frame.play.onState((state) => {
    if (shown === undefined) return
    shown.dialog.add(state.cards.slice(shown.listed))
    shown.listed = state.cards.length
  })

  return {
    button,
    open,
    isOpen: () => close !== undefined,
    unmount: () => {
      close?.()
      button.remove()
    },
  }
}
