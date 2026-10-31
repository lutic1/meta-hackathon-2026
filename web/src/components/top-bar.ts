import './top-bar.css'
import type { Meta } from '../../types'
import { placeHref } from '../router.ts'
import { fill, strings } from '../strings.ts'
import { soundToggle } from './sound-toggle.ts'

/**
 * `{components.mode-indicator}` text (UX-DR12): "Hosted mode", or "Local mode · Cache on · profile dev · 0 rooms
 * played", `played` being the number of Room results in the current profile.
 */
export function modeIndicatorText(meta: Meta, played: number): string {
  if (meta.mode === 'hosted') return strings.modeHosted
  const cache = meta.cache === 'on' ? strings.cacheOn : strings.cacheOff
  const rooms = played === 1 ? strings.oneRoomPlayed : fill(strings.roomsPlayed, { k: played })
  return [strings.modeLocal, cache, fill(strings.modeProfile, { name: meta.profile }), rooms].join(strings.modeSeparator)
}

export interface TopBar {
  element: HTMLElement
  /** The wordmark, a link to the start (`#/`) on every screen; the Play screen asks the Leave room confirmation first. */
  wordmark: HTMLAnchorElement
  /** The centered slot the Timer and its label sit in. */
  timer: HTMLElement
  /** The right end, where the Play screen puts its controls, before the sound toggle. */
  controls: HTMLElement
  /** Rewrites the mode indicator for a new count of Room results. */
  showPlayed: (played: number) => void
}

/**
 * The 48 px `chrome` top bar: the wordmark, a link to the start named "Keyframe, back to the start", and the mode
 * indicator, the centered Timer slot, then at the right end the controls slot and the sound toggle, outside the slot so
 * it stays live where the Play screen's controls are held inert. `played` is the current profile's count of Room results.
 */
export function topBar(meta: Meta, played: number): TopBar {
  const element = document.createElement('header')
  element.className = 'top-bar'
  const start = document.createElement('div')
  start.className = 'top-bar-start'
  const wordmark = document.createElement('a')
  wordmark.className = 'top-bar-wordmark display-sm'
  wordmark.href = placeHref({ route: { name: 'home' }, profile: meta.profile })
  wordmark.setAttribute('aria-label', strings.wordmarkLink)
  wordmark.textContent = strings.wordmark
  // Plain text, never focusable and never styled as a Disclosure.
  const mode = document.createElement('span')
  mode.className = 'mode-indicator body-sm'
  mode.textContent = modeIndicatorText(meta, played)
  start.append(wordmark, mode)
  const timer = document.createElement('div')
  timer.className = 'top-bar-timer'
  const controls = document.createElement('div')
  controls.className = 'top-bar-controls'
  const end = document.createElement('div')
  end.className = 'top-bar-end'
  end.append(controls, soundToggle())
  element.append(start, timer, end)
  const showPlayed = (count: number): void => {
    mode.textContent = modeIndicatorText(meta, count)
  }
  return { element, wordmark, timer, controls, showPlayed }
}
