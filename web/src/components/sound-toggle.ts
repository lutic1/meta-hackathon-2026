import { setSoundOn, soundOn } from '../audio.ts'
import { strings } from '../strings.ts'

const SPEAKER =
  '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
  'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 9v6h4l5 4V5L8 9z"/>' +
  '<path class="top-bar-sound-waves" d="M16.5 8.5a5 5 0 0 1 0 7M19 6a8.5 8.5 0 0 1 0 12"/>' +
  '<path class="top-bar-sound-mute" d="M16 9.5l5 5M21 9.5l-5 5"/></svg>'

/**
 * The sound toggle (owner request Oct 30, WCAG 1.4.2), at the right end of the top bar on every screen: a speaker and
 * the current state, "Sound on" or "Sound off", pressed while the sound is on. The choice is remembered in this
 * browser; the default is on, and nothing sounds until the first gesture.
 */
export function soundToggle(): HTMLButtonElement {
  const button = document.createElement('button')
  button.type = 'button'
  button.className = 'button-secondary top-bar-sound'
  button.innerHTML = SPEAKER
  const label = document.createElement('span')
  button.append(label)
  const show = (on: boolean): void => {
    button.setAttribute('aria-pressed', String(on))
    label.textContent = on ? strings.soundOn : strings.soundOff
  }
  button.addEventListener('click', () => {
    const on = !soundOn()
    setSoundOn(on)
    show(on)
  })
  show(soundOn())
  return button
}
