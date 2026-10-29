import type { Meta, RoomSummary } from '../types'
import { accessCode } from './access-code.ts'
import { postBuild, RequestFailed, type UploadPhoto } from './api/index.ts'
import { holdPhotos, takeCarriedPhotos } from './build-photos.ts'
import { buildAccepted, mountTimer, startTimer, stopTimer } from './capture-timer.ts'
import { accessRefused, buildQuota, buildsLeftLine, tooManyTries } from './components/access-code-build.ts'
import { primaryButton, secondaryButton } from './components/button.ts'
import { captureDropzone } from './components/capture-dropzone.ts'
import { type BannerState, bannerSlot, showBanner } from './components/error-banner.ts'
import { photoTray } from './components/photo-tray.ts'
import { openProfileControl } from './components/profile-file.ts'
import { retentionSummary } from './components/retention-summary.ts'
import { downscale, isJpeg, isValidSet, MAX_ORIGINAL_BYTES } from './photos.ts'
import { CUT_2, openProfileFile, FileNotSaved, saveProfileFile } from './profile/index.ts'
import { captureHref, placeHref } from './router.ts'
import { roomStarter, storedRooms } from './stored-rooms.ts'
import { strings } from './strings.ts'

export interface CaptureScreen {
  left: HTMLElement
  right: HTMLElement
  /**
   * Runs once the screen is in the page: focuses "Choose photos" and readies the Timer slot; returns the teardown
   * releasing the thumbnails and the Timer.
   */
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

/** Hosted mode's refusals of `POST /builds` (AD-9): a wrong code, too many attempts, every judge build used. */
export const HOSTED_REFUSALS: ReadonlyMap<string, BannerState> = new Map([
  ['access_denied', accessRefused],
  ['too_many_attempts', tooManyTries],
  ['build_quota_exceeded', buildQuota],
])

function line(text: string): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = 'capture-line body-md'
  element.textContent = text
  return element
}

/** Goes to the start, `#/`: the Hosted landing, or Local mode's Capture screen. */
export function goHome(profile: string): void {
  location.hash = placeHref({ route: { name: 'home' }, profile })
}

/** A secondary button at the top of the left column, sized to its label, that leaves the screen. */
export function backButton(label: string, onActivate: () => void): HTMLButtonElement {
  const back = secondaryButton({ label, onActivate })
  back.classList.add('capture-back')
  return back
}

function release(photos: readonly ChosenPhoto[]): void {
  for (const { url } of photos) URL.revokeObjectURL(url)
}

/**
 * Cut 2, Local mode only (Hosted mode has no profile route): "Open profile file" for the Retention summary. The chosen
 * file becomes the profile through web/profile, and the mode indicator hears its count at once; a refused file leaves
 * the profile as it was and shows the error banner in `banners`, which takes focus and offers "Open profile file"
 * again. A file merged with this page's Room results that then failed to save shows the warning "Progress is still
 * here, but the profile file wasn't saved. Try again." with "Try again", which writes it again and clears the banner
 * once it is written. null without cut 2 or in Hosted mode.
 */
function openProfile(profile: string, mode: Meta['mode'], banners: HTMLElement): HTMLElement | null {
  if (!CUT_2 || mode !== 'local') return null
  let refusal: HTMLElement | null = null
  const cleared = (): void => {
    if (refusal?.isConnected) showBanner(banners, null)
  }
  const notSaved = (): void => {
    const action = { label: strings.tryAgain, onActivate: () => void saveProfileFile(profile).then(cleared, () => {}) }
    refusal = showBanner(banners, { variant: 'warning', heading: strings.profileNotSaved, actions: [action] })
  }
  const control = openProfileControl((file) => {
    void openProfileFile(profile, file).then(cleared, (error: unknown) => {
      if (error instanceof FileNotSaved) return notSaved()
      const action = { label: strings.openProfileFile, onActivate: control.choose }
      refusal = showBanner(banners, { variant: 'error', heading: strings.profileFileRefused, actions: [action] })
    })
  })
  return control.element
}

/**
 * The Capture screen's right column, before and during a Build: the Input requirement standing alone, the iPhone
 * tip, the faces, documents and belongings reminder, then the Retention summary, with "Open profile file" under cut 2
 * in Local mode, its refusals shown in `banners`.
 */
export function captureColumn(retention: string, profile: string, mode: Meta['mode'], banners: HTMLElement): HTMLElement {
  const right = document.createElement('aside')
  right.className = 'capture-right'
  const summary = retentionSummary(retention, openProfile(profile, mode, banners))
  right.append(line(strings.inputRequirement), line(strings.iphoneTip), line(strings.reminder), summary)
  return right
}

/**
 * The Capture screen before a Build (Local `#/`, UX-DR62; Hosted `#/build-your-own` once an Access code is
 * accepted). Right: the Input requirement standing alone, the iPhone tip, the faces, documents and belongings
 * reminder, then the Retention summary as `GET /meta` serves it for the mode, all there before any photo is chosen.
 * Left: in Hosted mode "Back to the three cards" on top (to the landing, disabled while an upload is pending), the
 * banner slot, the dropzone, the Photo tray, Upload and, under it, `below`: the Stored Rooms list in Local mode, or in Hosted mode,
 * which has no Stored Rooms list, the accepted check's status line "{n} of 20 builds left". In Hosted mode `sample`
 * is the first Demo room listed, and the dropzone offers "No photos handy? Play the sample room" under "Choose
 * photos", which starts a Session on it by the landing's own path (`roomStarter`, its refusal banner in the slot);
 * with no Demo room, and in Local mode, the dropzone holds no such button.
 *
 * Every addition or removal re-validates the whole set (FR-1): a refused set shows the FR-1 banner and keeps Upload
 * disabled, so nothing is sent; a valid set clears it and enables Upload. Upload with an original over 20 MiB sends
 * nothing and shows "One of these photos is over 20 MB. Choose a smaller copy of it.", as a 413 `upload_too_large`
 * does. Otherwise Upload downscales each photo and posts them all with their originals in one `POST /builds`, with
 * the Access code this tab holds as `X-Access-Code` (Hosted); its pending label is the ingest stage name, the step the
 * server runs before it answers. A refused or failed upload
 * keeps the photos and shows its banner (Hosted: a wrong code the compact error, too many attempts the compact
 * warning, and `build_quota_exceeded`, a quota reached since the check, the Build quota warning); an accepted one
 * starts the Build: everything but the Retention summary and the banners is disabled, the photos and their
 * downscales are handed to `build-photos.ts`, and `#/build/<job_id>` opens with the profile carried.
 *
 * Photos "Add photos" carried here from a Build that ended `needs_more_photos` fill the tray at mount, re-validated
 * like any chosen set, so the next Upload is a new Build.
 *
 * Each Upload click is T0 (FR-5): the top bar's `timerSlot` shows the run it starts, nothing before. An upload that
 * fails or is refused freezes the run beside its end status, and the next Upload starts a new T0; an accepted one
 * records its job id, so `#/build/<job_id>` resumes the run after a reload.
 */
export function captureScreen(
  below: readonly RoomSummary[] | number,
  profile: string,
  mode: Meta['mode'],
  retention: string,
  timerSlot: HTMLElement,
  sample?: RoomSummary,
): CaptureScreen {
  let photos: ChosenPhoto[] = []
  let refusal: HTMLElement | null = null
  /** The T0 of the run this screen's last Upload started. */
  let t0: number | null = null
  /** The Build `POST /builds` accepted; its photos now belong to `#/build/<job_id>`. */
  let accepted: string | null = null

  const banners = bannerSlot()
  const start = roomStarter(profile, mode, banners)
  const dropzone = captureDropzone(
    (files, replace) => void choose(files, replace),
    sample === undefined ? undefined : () => void start(sample),
  )
  const tray = document.createElement('div')
  const upload = primaryButton({ label: strings.upload, pendingLabel: strings.readingPhotos, onActivate: send })
  upload.disabled = true
  const actions = document.createElement('div')
  actions.className = 'capture-actions'
  actions.append(upload)
  // One fieldset holds every control below the banners, so a Build disables them all at once.
  const controls = document.createElement('fieldset')
  controls.className = 'capture-controls'
  controls.append(
    dropzone.element,
    tray,
    actions,
    typeof below === 'number' ? buildsLeftLine(below) : storedRooms(below, profile, mode, banners),
  )
  // Hosted: "Back to the three cards" returns to the landing; the tab keeps its Access code. Local `#/` is the start.
  const back = typeof below === 'number' ? backButton(strings.backToCards, () => goHome(profile)) : null
  const left = document.createElement('section')
  left.className = 'capture-left'
  left.append(...(back === null ? [] : [back]), banners, controls)
  const right = captureColumn(retention, profile, mode, banners)
  const carried = takeCarriedPhotos()

  const chooseAgain = { label: strings.choosePhotosAgain, onActivate: dropzone.chooseAgain }
  const refused: BannerState = { variant: 'error', heading: strings.photosRefused, actions: [chooseAgain] }
  const unreadable: BannerState = { variant: 'error', heading: strings.photosUnreadable, actions: [chooseAgain] }
  const tooLarge: BannerState = { variant: 'error', heading: strings.photoTooLarge, actions: [chooseAgain] }
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
    if (back !== null) back.disabled = uploading
    if (dropzone.sample !== null) dropzone.sample.disabled = uploading
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
    // An original past ingest's cap is never sent, so no run starts for it.
    if (photos.some(({ file }) => file.size > MAX_ORIGINAL_BYTES)) {
      show(tooLarge)
      return
    }
    t0 = Date.now() // set before the run starts, so the slot shows it at once
    startTimer(t0)
    render(true)
    const outcome = await submit(photos)
    if (outcome !== null) stopTimer(strings.uploadFailedStatus)
    render()
    show(outcome)
    // An accepted set starts the Build, which its own route follows, carrying the profile.
    if (outcome === null) controls.disabled = true
    if (accepted !== null) location.hash = captureHref(accepted, profile)
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
      const job = await postBuild(pairs, accessCode())
      buildAccepted(job.id)
      accepted = job.id
      holdPhotos({
        jobId: job.id,
        thumbnails: set.map(({ url }) => url),
        downscales: pairs.map(({ downscale }) => URL.createObjectURL(downscale)),
        uploads: pairs,
      })
      return null
    } catch (error) {
      if (error instanceof RequestFailed && error.code === 'upload_too_large') return tooLarge
      const hosted = error instanceof RequestFailed && error.code !== null ? HOSTED_REFUSALS.get(error.code) : undefined
      if (hosted !== undefined) return hosted
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
      if (carried.length > 0) void choose(carried, true)
      const unmountTimer = mountTimer(timerSlot, (run) => run.t0 === t0)
      return () => {
        if (accepted === null) release(photos)
        unmountTimer()
      }
    },
  }
}
