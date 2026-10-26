import type { RoomSummary } from '../types'
import { postBuild, RequestFailed, type UploadPhoto } from './api/index.ts'
import { primaryButton } from './components/button.ts'
import { captureDropzone } from './components/capture-dropzone.ts'
import { type BannerState, bannerSlot, showBanner } from './components/error-banner.ts'
import { photoTray } from './components/photo-tray.ts'
import { retentionSummary } from './components/retention-summary.ts'
import { downscale, isJpeg, isValidSet } from './photos.ts'
import { storedRooms } from './stored-rooms.ts'
import { strings } from './strings.ts'

export interface CaptureScreen {
  left: HTMLElement
  right: HTMLElement
  /** Runs once the screen is in the page: focuses "Choose photos"; returns the teardown releasing the thumbnails. */
  mount: () => () => void
}

interface ChosenPhoto {
  file: File
  jpeg: boolean
  /** The local object URL its thumbnail shows; nothing is fetched for it. */
  url: string
}

/** The ingest refusals that mean the set breaks FR-1, answered with the same banner as the client's own check. */
const FR1_CODES = new Set(['unsupported_image', 'photo_count'])

function line(text: string): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = 'capture-line body-md'
  element.textContent = text
  return element
}

function release(photos: readonly ChosenPhoto[]): void {
  for (const { url } of photos) URL.revokeObjectURL(url)
}

/**
 * The Capture screen before a Build (Local `#/`, UX-DR62). Right: the Input requirement standing alone, the iPhone
 * tip, the faces, documents and belongings reminder, then the Retention summary, all there before any photo is
 * chosen. Left: the banner slot, the dropzone, the Photo tray, Upload and the Stored Rooms list.
 *
 * Every addition or removal re-validates the whole set (FR-1): a refused set shows the FR-1 banner and keeps Upload
 * disabled, so nothing is sent; a valid set clears it and enables Upload. Upload downscales each photo and posts
 * them all with their originals in one `POST /builds`; its pending label is the ingest stage name, the step the
 * server runs before it answers. A refused or failed upload keeps the photos and shows its banner; an accepted one
 * starts the Build, and everything but the Retention summary and the banners is disabled.
 */
export function captureScreen(rooms: readonly RoomSummary[], profile: string, retention: string): CaptureScreen {
  let photos: ChosenPhoto[] = []
  let refusal: HTMLElement | null = null

  const banners = bannerSlot()
  const dropzone = captureDropzone((files, replace) => void choose(files, replace))
  const tray = document.createElement('div')
  const upload = primaryButton({ label: strings.upload, pendingLabel: strings.readingPhotos, onActivate: send })
  upload.disabled = true
  const actions = document.createElement('div')
  actions.className = 'capture-actions'
  actions.append(upload)
  // One fieldset holds every control below the banners, so a Build disables them all at once.
  const controls = document.createElement('fieldset')
  controls.className = 'capture-controls'
  controls.append(dropzone.element, tray, actions, storedRooms(rooms, profile, banners))
  const left = document.createElement('section')
  left.className = 'capture-left'
  left.append(banners, controls)
  const right = document.createElement('aside')
  right.className = 'capture-right'
  right.append(line(strings.inputRequirement), line(strings.iphoneTip), line(strings.reminder), retentionSummary(retention))

  const chooseAgain = { label: strings.choosePhotosAgain, onActivate: dropzone.chooseAgain }
  const refused: BannerState = { variant: 'error', heading: strings.photosRefused, actions: [chooseAgain] }
  const unreadable: BannerState = { variant: 'error', heading: strings.photosUnreadable, actions: [chooseAgain] }
  const failed: BannerState = {
    variant: 'error',
    heading: strings.uploadFailed,
    sentence: strings.uploadFailedBody,
    actions: [{ label: strings.tryAgain, onActivate: () => upload.click() }], // the same set, through Upload
  }

  function show(state: BannerState | null): void {
    const element = showBanner(banners, state)
    refusal = state === refused ? element : null
  }

  function render(uploading = false): void {
    const shown = photos.map(({ url, jpeg }) => ({ url, rejected: !jpeg }))
    tray.replaceChildren(...(photos.length === 0 ? [] : [photoTray(shown, remove, uploading)]))
    dropzone.button.disabled = uploading
    upload.disabled = !isValidSet(photos)
  }

  /** A refused set shows the FR-1 banner once; a valid or emptied set clears it. */
  function validate(): void {
    const refusedSet = photos.length > 0 && !isValidSet(photos)
    if (refusedSet && !refusal?.isConnected) show(refused)
    else if (!refusedSet && refusal?.isConnected) show(null)
  }

  async function choose(files: readonly File[], replace: boolean): Promise<void> {
    const chosen = await Promise.all(
      files.map(async (file) => ({ file, jpeg: await isJpeg(file), url: URL.createObjectURL(file) })),
    )
    if (replace) release(photos)
    photos = replace ? chosen : [...photos, ...chosen]
    render()
    validate()
  }

  function remove(index: number): void {
    release(photos.slice(index, index + 1))
    photos = photos.filter((_, other) => other !== index)
    render()
    const removes = tray.querySelectorAll<HTMLButtonElement>('.photo-tray-remove')
    ;(removes[Math.min(index, removes.length - 1)] ?? dropzone.button).focus()
    validate()
  }

  async function send(): Promise<void> {
    if (!isValidSet(photos)) return
    render(true)
    const outcome = await submit(photos)
    render()
    show(outcome)
    // An accepted set starts the Build; the Build's own route (`#/build/<job_id>`) joins in 2.18.
    if (outcome === null) controls.disabled = true
  }

  /** null once `POST /builds` accepted the set, else the banner for why it did not. */
  async function submit(set: readonly ChosenPhoto[]): Promise<BannerState | null> {
    const pairs: UploadPhoto[] = []
    try {
      for (const { file } of set) pairs.push({ downscale: await downscale(file), original: file })
    } catch {
      return unreadable
    }
    try {
      await postBuild(pairs)
      return null
    } catch (error) {
      const code = error instanceof RequestFailed && error.status === 422 ? error.code : null
      if (code !== null && FR1_CODES.has(code)) return refused
      return code === 'bad_downscale' ? unreadable : failed
    }
  }

  return {
    left,
    right,
    mount: () => {
      dropzone.button.focus()
      return () => release(photos)
    },
  }
}
