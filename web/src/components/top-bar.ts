import './top-bar.css'
import type { Meta } from '../../types'
import { fill, strings } from '../strings.ts'

/**
 * `{components.mode-indicator}` text (UX-DR12): "Hosted mode", or "Local mode · Cache on · profile dev".
 * The rooms-played count joins in 5.1.
 */
export function modeIndicatorText(meta: Meta): string {
  if (meta.mode === 'hosted') return strings.modeHosted
  const cache = meta.cache === 'on' ? strings.cacheOn : strings.cacheOff
  return [strings.modeLocal, cache, fill(strings.modeProfile, { name: meta.profile })].join(strings.modeSeparator)
}

export interface TopBar {
  element: HTMLElement
  /** The centered slot the Timer and its label sit in. */
  timer: HTMLElement
  /** The right end, where the Play screen puts its controls. */
  controls: HTMLElement
}

/** The 48 px `chrome` top bar: the wordmark and the mode indicator, the centered Timer slot, the controls slot. */
export function topBar(meta: Meta): TopBar {
  const element = document.createElement('header')
  element.className = 'top-bar'
  const start = document.createElement('div')
  start.className = 'top-bar-start'
  const wordmark = document.createElement('span')
  wordmark.className = 'top-bar-wordmark display-sm'
  wordmark.textContent = strings.wordmark
  // Plain text, never focusable and never styled as a Disclosure.
  const mode = document.createElement('span')
  mode.className = 'mode-indicator body-sm'
  mode.textContent = modeIndicatorText(meta)
  start.append(wordmark, mode)
  const timer = document.createElement('div')
  timer.className = 'top-bar-timer'
  const controls = document.createElement('div')
  controls.className = 'top-bar-controls'
  element.append(start, timer, controls)
  return { element, timer, controls }
}
