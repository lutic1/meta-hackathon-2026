import { CLIP } from '../clip.ts'
import { strings } from '../strings.ts'

/**
 * The ten-second clip under "How to play": a muted, looping play-through of the room `CLIP` names, in a box of the
 * clip's own aspect so nothing shifts while it loads, captioned in `label`. It autoplays unless reduced motion is set,
 * with the Pause toggle in its corner (WCAG 2.2.2); under reduced motion it waits on its poster with native controls
 * and no toggle. A video that fails to load takes the figure with it.
 */
export function sampleClip(): HTMLElement {
  const element = document.createElement('figure')
  element.className = 'landing-clip'
  const video = document.createElement('video')
  video.className = 'landing-clip-video'
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches
  video.defaultMuted = true
  video.muted = true
  video.loop = true
  video.playsInline = true
  video.preload = 'metadata'
  video.poster = CLIP.poster
  video.autoplay = !reduced
  video.controls = reduced
  video.setAttribute('aria-label', strings.clipLabel)
  const source = (src: string, type: string): HTMLSourceElement => {
    const tag = document.createElement('source')
    tag.src = src
    tag.type = type
    return tag
  }
  const mp4 = source(CLIP.mp4, 'video/mp4')
  video.append(source(CLIP.webm, 'video/webm'), mp4)
  mp4.addEventListener('error', () => element.remove())
  video.addEventListener('error', () => element.remove())
  const frame = document.createElement('div')
  frame.className = 'landing-clip-frame'
  frame.append(video)
  if (!reduced) frame.append(clipToggle(video))
  const caption = document.createElement('figcaption')
  caption.className = 'landing-clip-caption label'
  caption.textContent = strings.clipCaption
  element.append(frame, caption)
  return element
}

/**
 * "Pause" while the clip plays and "Play" while it is paused, named "Pause the clip" and "Play the clip"; it follows
 * the video's own play and pause events. A pause holds for the page: nothing but this toggle starts the clip again.
 */
function clipToggle(video: HTMLVideoElement): HTMLButtonElement {
  const toggle = document.createElement('button')
  toggle.type = 'button'
  toggle.className = 'landing-clip-toggle label'
  const show = (paused: boolean): void => {
    toggle.textContent = paused ? strings.play : strings.clipPause
    toggle.setAttribute('aria-label', paused ? strings.clipPlayName : strings.clipPauseName)
  }
  show(false)
  video.addEventListener('play', () => show(false))
  video.addEventListener('pause', () => show(true))
  toggle.addEventListener('click', () => {
    if (video.paused) void video.play().catch(() => undefined)
    else video.pause()
  })
  return toggle
}
