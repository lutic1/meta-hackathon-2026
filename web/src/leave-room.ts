import { secondaryButton } from './components/button.ts'
import { type LeaveRoomConfirmation, leaveRoomConfirmation } from './components/leave-room-confirmation.ts'
import { strings } from './strings.ts'

/** Marks the history entry the Play screen pushes over its own, so the browser Back button lands on the Play route. */
const GUARD = 'keyframeLeaveGuard'

function isGuard(state: unknown): boolean {
  return typeof state === 'object' && state !== null && GUARD in state
}

/** Where a leave confirmation opens: the box its scrim covers, and what it holds inert while it shows. */
export interface LeaveFrame {
  /** The page body, which takes the scrim. */
  body: HTMLElement
  /** The top bar and the body's columns, inert while the confirmation shows. */
  held: readonly HTMLElement[]
}

/**
 * Opens `confirmation` over `frame.body`, focused on its stay button, with focus trapped on its two buttons and every
 * element in `frame.held` inert. Escape or the stay button closes it and calls `stay`, which returns focus; the leave
 * button closes it and calls `leave`. Returns the close that calls neither, for a screen torn down while it shows.
 */
export function askToLeave(
  frame: LeaveFrame,
  confirmation: LeaveRoomConfirmation,
  stay: () => void,
  leave: () => void,
): () => void {
  const order = [confirmation.stay, confirmation.leave]
  /** No pointer press anywhere moves focus out of the card; a click on either button still fires. */
  const keepFocus = (event: MouseEvent): void => event.preventDefault()
  const trap = (event: KeyboardEvent): void => {
    if (event.key === 'Escape') {
      event.preventDefault()
      event.stopPropagation()
      keep()
      return
    }
    if (event.key !== 'Tab') return
    event.preventDefault()
    const at = order.indexOf(document.activeElement as HTMLButtonElement)
    const step = event.shiftKey ? order.length - 1 : 1
    order[at === -1 ? 0 : (at + step) % order.length].focus()
  }

  for (const element of frame.held) element.inert = true
  frame.body.append(confirmation.element)
  document.addEventListener('mousedown', keepFocus, true)
  document.addEventListener('keydown', trap, true)
  confirmation.show()
  confirmation.stay.focus()

  let open = true
  function close(): void {
    if (!open) return
    open = false
    document.removeEventListener('mousedown', keepFocus, true)
    document.removeEventListener('keydown', trap, true)
    confirmation.element.remove()
    for (const element of frame.held) element.inert = false
  }
  function keep(): void {
    close()
    stay()
  }
  confirmation.stay.addEventListener('click', keep)
  confirmation.leave.addEventListener('click', () => {
    close()
    leave()
  })
  return close
}

/** What the Leave room confirmation takes from the Play screen. */
export interface LeaveRoomFrame extends LeaveFrame {
  /** The top bar's wordmark, whose link to the start asks the confirmation first. */
  wordmark: HTMLAnchorElement
  /** Another modal is open (the First-room welcome), so nothing opens over it. */
  modalOpen: () => boolean
  /** Focuses the Scene's first Hotspot: where focus returns when the Back button opened the confirmation. */
  focusScene: () => void
  /** Leaves the room: goes to `#/` through `exit`, recording no Room result. */
  leave: () => void
}

export interface LeaveRoom {
  /** The top bar's "Leave room" button. */
  button: HTMLButtonElement
  /**
   * Routes to `href` in place of the Play route, taking the guard entry off the history first, so Back from there
   * lands on the route before the Play screen, never on the Play route again.
   */
  exit: (href: string) => void
  /** Closes the confirmation, stops catching the Back button and the wordmark and removes the button. */
  unmount: () => void
}

/**
 * "Leave room" on the Play screen (UX-DR46, UX-DR8): the top bar's button, its wordmark or the browser Back button
 * opens `{components.leave-room-confirmation}` over the scrim (`askToLeave`), focused on "Keep playing", with focus
 * trapped on its two buttons and every element in `held` inert. Escape or "Keep playing" closes it, returning focus to
 * the control that opened it, or to the first Hotspot when the Back button opened it; "Leave room" in the card leaves.
 * It never opens over another modal, nor over itself, so modals never stack.
 *
 * The Back button is caught by a history entry pushed over the Play route at the same URL (once: a reload already
 * stands on it). Back pops it, the URL stays put and no route change happens; the entry is pushed again at once, so
 * the next Back is caught too. A navigation the client makes itself changes the hash, so it is never mistaken for Back.
 * `exit` pops the guard before it replaces the Play route, so the history keeps no Play entry behind the route it opens.
 */
export function mountLeaveRoom(frame: LeaveRoomFrame): LeaveRoom {
  const playHash = location.hash
  let close: (() => void) | undefined

  const button = secondaryButton({ label: strings.leaveRoom, onActivate: () => open(() => button.focus()) })

  function open(refocus: () => void): void {
    if (close !== undefined || frame.modalOpen()) return
    const keep = (): void => {
      close = undefined
      refocus()
    }
    close = askToLeave(frame, leaveRoomConfirmation(), keep, frame.leave)
  }

  /** The wordmark's link to the start asks first, as "Leave room" does. */
  const onWordmark = (event: MouseEvent): void => {
    event.preventDefault()
    open(() => frame.wordmark.focus())
  }
  frame.wordmark.addEventListener('click', onWordmark)

  const guard = (): void => history.pushState({ [GUARD]: true }, '')
  const onBack = (): void => {
    if (isGuard(history.state) || location.hash !== playHash) return
    guard()
    open(frame.focusScene)
  }
  if (!isGuard(history.state)) guard()
  window.addEventListener('popstate', onBack)

  let exiting: (() => void) | undefined
  function exit(href: string): void {
    window.removeEventListener('popstate', onBack)
    if (!isGuard(history.state)) return location.replace(href)
    exiting = () => location.replace(href)
    window.addEventListener('popstate', exiting, { once: true })
    history.back()
  }

  return {
    button,
    exit,
    unmount: () => {
      window.removeEventListener('popstate', onBack)
      frame.wordmark.removeEventListener('click', onWordmark)
      if (exiting !== undefined) window.removeEventListener('popstate', exiting)
      close?.()
      button.remove()
    },
  }
}
