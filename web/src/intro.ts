import './intro.css'
import type { VideoSources } from './clip.ts'
import { primaryButton, secondaryButton } from './components/button.ts'
import { parsePlace } from './router.ts'
import { fill, strings } from './strings.ts'

/**
 * The intro, the owner's own ten-second teaser (owner decision Oct 29): polaroids fly in, the four medallions trace
 * gold lines, a keyhole turns, then the gold "KEYFRAME" title over "An escape room built from your own photos.".
 * Re-encoded from the 1280 x 720, 24 fps HEVC source with its music kept:
 *   ffmpeg -i intro.mov -c:v libx264 -pix_fmt yuv420p -crf 23 -preset slow -c:a aac -b:a 128k -movflags +faststart intro.mp4
 *   ffmpeg -i intro.mov -c:v libvpx-vp9 -b:v 0 -crf 34 -row-mt 1 -pix_fmt yuv420p -c:a libopus -b:a 96k intro.webm
 *   ffmpeg -sseof -0.1 -i intro.mov -frames:v 1 -q:v 3 -update 1 intro-poster.jpg (the title, its last frame)
 */
export const INTRO: VideoSources = {
  webm: '/intro/intro.webm',
  mp4: '/intro/intro.mp4',
  poster: '/intro/intro-poster.jpg',
}

/** Set once the intro has ended, been skipped or been entered: it never shows by itself again in this browser. */
export const INTRO_SEEN_KEY = 'keyframe.introSeen.v1'
/** The end holds the title this many seconds before entering by itself. */
const COUNTDOWN_S = 4
const FADE_OUT_MS = 600

/** Whether this page load opened on the landing's route: a deep link (`#/play/…`, `#/build/…`) never shows the intro. */
const OPENED_ON_HOME = parsePlace(location.hash, location.search).route.name === 'home'
/** Seen in this page load, so a browser whose storage refuses shows it at most once per load. */
let seenThisLoad = false

function introSeen(): boolean {
  if (seenThisLoad) return true
  try {
    return localStorage.getItem(INTRO_SEEN_KEY) === 'yes'
  } catch {
    return false
  }
}

function markIntroSeen(): void {
  seenThisLoad = true
  try {
    localStorage.setItem(INTRO_SEEN_KEY, 'yes')
  } catch {
    // storage refused: `seenThisLoad` holds it for this page load
  }
}

/** The intro shows by itself on a page load opened on the landing, in a browser that has not seen it, without reduced motion. */
export function introDue(reduced: boolean): boolean {
  return OPENED_ON_HOME && !reduced && !introSeen()
}

export interface Intro {
  /** Settles once the overlay is gone, after its fade out. */
  closed: Promise<void>
  /** Takes the overlay out at once (the landing's teardown). */
  remove: () => void
}

function control(className: string, label: string): HTMLButtonElement {
  const button = document.createElement('button')
  button.type = 'button'
  button.className = `intro-control label ${className}`
  button.textContent = label
  return button
}

/**
 * The full-screen intro over the whole page, a modal named "Keyframe intro": the teaser covering the viewport on black,
 * muted, with "Sound on" top right (sound starts only when the player turns it on) and "Skip intro" bottom right; Escape
 * skips. At its end it holds the title and offers "Replay" and "Enter Keyframe"; the intro that showed by itself (`first`)
 * counts down "Entering in 4…" and enters by itself unless Replay is chosen. Entering or skipping fades it out over
 * 600 ms; ending, skipping or entering marks it seen. Under reduced motion it never plays by itself: it shows the native
 * controls and leaves the out instant. A video that errors or will not play falls straight through to the landing.
 * Everything else in the page is inert while it shows, and focus goes back where it was.
 */
export function openIntro(first: boolean): Intro {
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches
  const overlay = document.createElement('div')
  overlay.className = 'intro'
  overlay.setAttribute('role', 'dialog')
  overlay.setAttribute('aria-modal', 'true')
  overlay.setAttribute('aria-label', strings.introLabel)

  const video = document.createElement('video')
  video.className = 'intro-video'
  video.muted = true
  video.playsInline = true
  video.preload = 'auto'
  video.controls = reduced
  video.poster = INTRO.poster
  const sources = (
    [
      [INTRO.webm, 'video/webm'],
      [INTRO.mp4, 'video/mp4'],
    ] as const
  ).map(([src, type]) => {
    const source = document.createElement('source')
    source.src = src
    source.type = type
    return source
  })
  video.append(...sources)

  const sound = control('intro-sound', strings.introSoundOn)
  sound.hidden = reduced
  const skip = control('intro-skip', strings.introSkip)
  const countdown = document.createElement('p')
  countdown.className = 'intro-countdown body-sm'
  const replay = secondaryButton({ label: strings.introReplay, onActivate: restart })
  const enter = primaryButton({ label: strings.introEnter, pendingLabel: strings.introEnter, onActivate: async () => close(true) })
  const actions = document.createElement('div')
  actions.className = 'intro-actions'
  actions.append(replay, enter)
  const end = document.createElement('div')
  end.className = 'intro-end'
  end.append(countdown, actions)
  end.hidden = true
  overlay.append(video, sound, skip, end)

  let counting = first
  let ticker: ReturnType<typeof setInterval> | undefined
  let closing = false
  let resolve: () => void = () => undefined
  const closed = new Promise<void>((settle) => {
    resolve = settle
  })
  const previous = document.activeElement
  const others = [...document.body.children].filter(
    (node): node is HTMLElement => node instanceof HTMLElement && !node.inert && !node.classList.contains('narrow-screen'),
  )

  function showEnd(): void {
    skip.hidden = true
    end.hidden = false
    enter.focus()
    if (!counting) return
    let left = COUNTDOWN_S
    countdown.textContent = fill(strings.introCountdown, { n: left })
    ticker = setInterval(() => {
      left -= 1
      countdown.textContent = fill(strings.introCountdown, { n: left })
      if (left === 0) close(true)
    }, 1000)
  }

  /** Replay: from the start, with no countdown after it; the player enters when ready. */
  function restart(): void {
    counting = false
    clearInterval(ticker)
    countdown.textContent = ''
    end.hidden = true
    skip.hidden = false
    video.currentTime = 0
    void video.play().catch(() => undefined)
    skip.focus()
  }

  function done(): void {
    overlay.remove()
    document.removeEventListener('keydown', onKey, true)
    for (const node of others) node.inert = false
    if (previous instanceof HTMLElement && previous !== document.body && previous.isConnected) previous.focus()
    resolve()
  }

  function close(fade: boolean): void {
    if (closing) return
    closing = true
    markIntroSeen()
    clearInterval(ticker)
    video.pause()
    if (fade && !reduced) {
      const fading = overlay.animate([{ opacity: 1 }, { opacity: 0 }], { duration: FADE_OUT_MS, easing: 'ease-out', fill: 'forwards' })
      fading.finished.then(done, done)
    } else done()
  }

  /** Escape skips (or enters, at the end); Tab cycles the overlay's visible controls. */
  function onKey(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      event.preventDefault()
      close(true)
    } else if (event.key === 'Tab') {
      const controls = [...overlay.querySelectorAll<HTMLElement>('button, video[controls]')].filter(
        (node) => node.offsetParent !== null,
      )
      if (controls.length === 0) return
      const at = controls.indexOf(document.activeElement as HTMLElement)
      const next = event.shiftKey ? (at <= 0 ? controls.length - 1 : at - 1) : (at + 1) % controls.length
      event.preventDefault()
      controls[next].focus()
    }
  }

  sound.addEventListener('click', () => {
    video.muted = !video.muted
    sound.textContent = video.muted ? strings.introSoundOn : strings.introSoundOff
  })
  skip.addEventListener('click', () => close(true))
  video.addEventListener('ended', () => {
    markIntroSeen()
    showEnd()
  })
  const last = sources[sources.length - 1]
  last.addEventListener('error', () => close(false))
  video.addEventListener('error', () => close(false))

  document.body.append(overlay)
  for (const node of others) node.inert = true
  document.addEventListener('keydown', onKey, true) // capture: ahead of the chooser's own keys
  skip.focus()
  if (!reduced) video.play().catch(() => close(false))

  return {
    closed,
    remove: () => {
      if (!overlay.isConnected) return
      closing = true
      clearInterval(ticker)
      video.pause()
      done()
    },
  }
}
