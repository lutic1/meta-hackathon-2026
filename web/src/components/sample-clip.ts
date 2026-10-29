import { CLIP } from '../clip.ts'
import { strings } from '../strings.ts'

/**
 * The ten-second clip under "How to play": a muted, looping play-through of the room `CLIP` names, in a box of the
 * clip's own aspect so nothing shifts while it loads, captioned in `label`. It autoplays unless reduced motion is set;
 * then it waits on its poster with native controls. A video that fails to load takes the figure with it.
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
  const caption = document.createElement('figcaption')
  caption.className = 'landing-clip-caption label'
  caption.textContent = strings.clipCaption
  element.append(video, caption)
  return element
}
