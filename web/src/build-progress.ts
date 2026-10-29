import type { JobState, Meta } from '../types'
import { accessCode } from './access-code.ts'
import { getBuild, photoUrl, postBuild, RequestFailed, startSession } from './api/index.ts'
import { type EndAction, buildEnd } from './build-end.ts'
import { carryPhotos, heldPhotos, passPhotos, releasePhotos } from './build-photos.ts'
import { stageRows } from './build-stages.ts'
import { buildViewLink } from './build-view.ts'
import { backButton, captureColumn, goHome, HOSTED_REFUSALS } from './capture.ts'
import { buildAccepted, buildDequeued, buildEnded, buildQueued, sessionOpened, startTimer } from './capture-timer.ts'
import { primaryButton } from './components/button.ts'
import { type BannerAction, type BannerState, bannerSlot, showBanner } from './components/error-banner.ts'
import { type ConfirmationCopy, leaveRoomConfirmation } from './components/leave-room-confirmation.ts'
import { reveal } from './components/fade.ts'
import { fitChips, maskPreview, type TilePhoto } from './components/mask-preview.ts'
import { compactPhotoTray } from './components/photo-tray.ts'
import { stageList } from './components/stage-list.ts'
import { statusStrip } from './components/status-strip.ts'
import { askToLeave } from './leave-room.ts'
import { announce } from './live-region.ts'
import { MAX_PHOTOS } from './photos.ts'
import { sessionStart } from './profile/index.ts'
import { captureHref, placeHref, type Route } from './router.ts'
import { type RoomGone, roomGone } from './room-gone.ts'
import type { Size } from './scene/geometry.ts'
import { strings } from './strings.ts'

/** How often `#/build/<job_id>` reads job state (UX-DR8, the session cadence). */
export const BUILD_POLL_MS = 2000
/** Consecutive missed polls that show the reconnecting strip (EXPERIENCE.md State Patterns, Reconnecting (Build)). */
export const MISSED_POLLS = 2

export interface BuildScreen {
  left: HTMLElement
  right: HTMLElement
  /** Runs once the screen is in the page: starts polling; returns the teardown that stops it. */
  mount: () => () => void
}

/** "Back to the start" asks first while the Build still runs: it keeps building, and this page's address returns to it. */
const LEAVE_PAGE: ConfirmationCopy = {
  question: strings.leavePageQuestion,
  sentence: strings.leavePageBody,
  stay: strings.stay,
  leave: strings.leave,
}

/** The warning a `queued` Build shows (Hosted): it waits in line and starts on its own, so it offers no action. */
const QUEUED: BannerState = { variant: 'warning', heading: strings.queued, actions: [] }

/** The two plain `body-sm` lines under the Stage list in Hosted mode, from Upload on (UX-DR18). */
function hostedLines(): HTMLElement {
  const lines = document.createElement('div')
  lines.className = 'build-hosted-lines'
  for (const text of [strings.ownLink, strings.targetMeasured]) {
    const line = document.createElement('p')
    line.className = 'build-hosted-line body-sm'
    line.textContent = text
    lines.append(line)
  }
  return lines
}

/** The pixel size of the photo at `url` once it decodes; null when it does not. */
async function photoSize(url: string): Promise<Size | null> {
  const image = new Image()
  image.src = url
  try {
    await image.decode()
    return { width: image.naturalWidth, height: image.naturalHeight }
  } catch {
    return null
  }
}

/**
 * The Capture screen during a Build (`#/build/<job_id>`, FR-5, UX-DR62): the right column as before the Build; on
 * the left, under the banner slot, the done Build's actions (so "Play this room" is in view at 1024 x 768 above the
 * Stage list's history), the Stage list in the dropzone's place, the Mask preview once job state carries it, and the
 * Photo tray, compact. `GET /builds/<job_id>` is read at once and every 2000 ms while the Build is `queued` or
 * `running`; a missed poll is tried again on the same cadence, while a refused one (4xx) ends the polling with the
 * list as last seen. Job state alone drives the list; nothing is inferred between polls, and the Architect's line
 * naming the objects stays on the "Finding objects" row from the first poll that carries the Mask preview on.
 *
 * The page that uploaded the Build holds its photos (`build-photos.ts`): the tray shows them and the Mask preview
 * draws on their downscales. When a poll reads `done` after this page saw the Build unfinished, or uploaded it, a
 * Session starts, carrying the profile's Derived block (`sessionStart`), and the Play screen opens, the Timer passing to that Session.
 * A Build already `done` when the route opens shows "Play this room" instead, and the photos the server now serves
 * for its Room. Either way a `done` Build shows "How this room was built", opening its Build view (absent under
 * cut 0), beside "Play this room" or alone while the Session starts, so a refused start still reaches it. A
 * refused session start shows the session-start-refused banner, whose "Try again" posts it again; the Timer keeps
 * running toward T1.
 *
 * Hosted mode adds two plain lines under the Stage list (the Build's own link, where the two-minute target is
 * measured), since a reopened `#/build/<job_id>` resumes polling with no Access code. A poll that reads `queued`
 * shows the queued warning, which takes focus once, and the Timer reads "queued" in place of the digits; the first
 * poll past it clears that warning and records the client-measured time in the queue for the frozen Timer's note.
 *
 * A Build that ends without a Room (`build-end.ts`) stops its Timer beside the status, marks the row it stopped at
 * failed, keeps its photos in the tray and shows one banner, which takes focus, its actions next in Tab order:
 * "Try again" posts the held photos as a new Build, with this tab's Access code in Hosted mode, and opens its route; "Add photos" opens the picker and carries
 * the set plus the new files, up to 10 in all, to the Capture screen, whose next Upload is a new Build; "Start
 * over" opens the empty Capture screen. A page that holds no photos (reloaded) cannot post or extend the set, so
 * "Start over" takes the place of both. Two consecutive missed polls put the reconnecting strip at the top of the
 * left area, above any banner, written once to the live region and never focused; the Stage list, the Mask preview
 * and the Timer go on as they were, and the next answered poll removes the strip and renders from job state. A
 * refused poll, which ends the polling, removes it too.
 *
 * "Back to the start", on top of the left area, goes to `#/`; while the Build is not known to have ended (before the
 * first answered poll, `queued` or `running`) it first asks, with the Leave room confirmation's card and focus handling
 * over `page.body` (the top bar and both columns inert): "Your room keeps building. Leave this page? This page's
 * address brings you back.", "Stay" focused, Escape or "Stay" returning focus to the button, "Leave" going home.
 *
 * A poll refused with 410 `room_deleted` (the Build's Judge room was deleted), or a session start refused with it or
 * with 404 `room_not_found`, is handed to `onGone`, which replaces the page body with that Room's card; a poll refused
 * with 404 `job_not_found` (a link no Build has) is handed to it as `room_not_found`, the unknown-room card.
 */
export function buildScreen(
  jobId: string,
  profile: string,
  mode: Meta['mode'],
  retention: string,
  page: { body: HTMLElement; topBar: HTMLElement },
  onGone: (gone: RoomGone) => void,
): BuildScreen {
  const held = heldPhotos(jobId)
  const banners = bannerSlot()
  const stages = stageList()
  stages.update(stageRows(null))
  const actions = document.createElement('div')
  actions.className = 'capture-actions'
  actions.hidden = true
  const maskSlot = document.createElement('div')
  const traySlot = document.createElement('div')
  if (held !== null) traySlot.append(compactPhotoTray(held.thumbnails))
  const picker = document.createElement('input')
  picker.type = 'file'
  picker.multiple = true
  picker.hidden = true
  const strip = statusStrip(strings.reconnectingBuild)
  /** The job status the last answered poll read; null before the first. */
  let status: JobState['status'] | null = null
  /** Closes the confirmation "Back to the start" opened, while it shows. */
  let asking: (() => void) | undefined
  const back = backButton(strings.backToStart, () => backToStart())
  const left = document.createElement('section')
  left.className = 'capture-left'
  left.append(back, banners, actions, stages.element, ...(mode === 'hosted' ? [hostedLines()] : []), maskSlot, traySlot, picker)
  const right = captureColumn(retention, profile, mode, banners)
  const frame = { body: page.body, held: [page.topBar, left, right] }

  /** Home at once once the Build has ended; while it may still run, after the confirmation. */
  function backToStart(): void {
    if (status !== null && status !== 'queued' && status !== 'running') return goHome(profile)
    if (asking !== undefined) return
    const stay = (): void => {
      asking = undefined
      back.focus()
    }
    asking = askToLeave(frame, leaveRoomConfirmation(LEAVE_PAGE), stay, () => goHome(profile))
  }

  return {
    left,
    right,
    mount: () => {
      let mounted = true
      let polling: ReturnType<typeof setTimeout> | undefined
      /** Whether reading `done` opens the Play screen: this page uploaded the Build, or saw it unfinished. */
      let live = held !== null
      let masked = false
      let starting = false
      let started = false
      let ended = false
      let retrying = false
      let missed = 0
      /** The queued warning while it is the banner shown. */
      let queuedBanner: HTMLElement | null = null

      /** The photo at `index`: this page's downscale, else, once the Room exists, the one the server stores. */
      function photo(job: JobState, index: number): string | null {
        if (held !== null) return held.downscales[index] ?? null
        return job.status === 'done' && job.room_id != null ? photoUrl(job.room_id, index) : null
      }

      async function showMask(job: JobState): Promise<void> {
        const tiles = job.mask_preview ?? []
        const photos = new Map<number, TilePhoto>()
        await Promise.all(
          [...new Set(tiles.map((tile) => tile.photo))].map(async (index) => {
            const url = photo(job, index)
            const size = url === null ? null : await photoSize(url)
            if (url !== null && size !== null) photos.set(index, { url, size })
          }),
        )
        if (!mounted) return
        const grid = maskPreview(tiles, photos)
        maskSlot.replaceChildren(grid)
        fitChips(grid)
        reveal(grid)
      }

      async function start(roomId: string): Promise<void> {
        if (starting || started) return
        starting = true
        try {
          const session = await startSession(await sessionStart(roomId, profile, mode))
          started = true
          showBanner(banners, null)
          sessionOpened(jobId, session.id)
          location.hash = placeHref({ route: { name: 'play', sessionId: session.id }, profile })
        } catch (error) {
          const gone = roomGone(error)
          if (gone !== null) {
            if (mounted) onGone(gone)
            return
          }
          showBanner(banners, {
            variant: 'error',
            heading: strings.sessionStartRefused,
            sentence: strings.sessionStartRefusedBody,
            actions: [{ label: strings.tryAgain, onActivate: () => void start(roomId) }],
          })
        } finally {
          starting = false
        }
      }

      function done(job: JobState, roomId: string): void {
        const link = buildViewLink(jobId, profile)
        if (live) {
          if (link !== null) {
            actions.replaceChildren(link)
            actions.hidden = false
          }
          void start(roomId)
          return
        }
        const photos = job.stages?.find((record) => record.stage === 'ingest')?.count ?? 0
        const urls = Array.from({ length: photos }, (_, index) => photoUrl(roomId, index))
        if (urls.length > 0) traySlot.replaceChildren(compactPhotoTray(urls))
        const play = primaryButton({
          label: strings.playThisRoom,
          pendingLabel: strings.playThisRoom,
          onActivate: () => start(roomId),
        })
        actions.replaceChildren(play, ...(link === null ? [] : [link]))
        actions.hidden = false
      }

      /** The Capture screen: Local `#/`, Hosted `#/build-your-own`, as this tab still holds the code its Upload sent. */
      function startOver(): void {
        releasePhotos()
        const capture: Route = mode === 'hosted' ? { name: 'buildYourOwn' } : { name: 'home' }
        location.hash = placeHref({ route: capture, profile })
      }

      /**
       * "Try again": the held photos as a new Build, its Timer run from this click; a failed post says so, and a Hosted
       * refusal shows the banner Upload shows for it, with no action, so no click spends another access attempt.
       */
      async function retry(): Promise<void> {
        if (held === null || retrying) return
        retrying = true
        const t0 = Date.now()
        try {
          const job = await postBuild(held.uploads, accessCode())
          startTimer(t0)
          buildAccepted(job.id)
          passPhotos(jobId, job.id)
          if (mounted) location.hash = captureHref(job.id, profile)
        } catch (error) {
          const hosted = error instanceof RequestFailed && error.code !== null ? HOSTED_REFUSALS.get(error.code) : undefined
          showBanner(banners, hosted ?? {
            variant: 'error',
            heading: strings.uploadFailed,
            sentence: strings.uploadFailedBody,
            actions: [{ label: strings.tryAgain, onActivate: () => void retry() }],
          })
        } finally {
          retrying = false
        }
      }

      /** "Add photos": the held set plus the files picked, up to 10 in all, carried to the Capture screen. */
      picker.addEventListener('change', () => {
        const files = [...(picker.files ?? [])]
        picker.value = ''
        if (held === null || files.length === 0) return
        carryPhotos([...held.uploads.map(({ original }) => original), ...files].slice(0, MAX_PHOTOS))
        startOver()
      })

      function action(kind: EndAction): BannerAction {
        if (kind === 'startOver') return { label: strings.startOver, onActivate: startOver }
        if (kind === 'tryAgain') return { label: strings.tryAgain, onActivate: () => void retry() }
        return { label: strings.addPhotos, onActivate: () => picker.click() }
      }

      function end(job: JobState): void {
        if (ended) return
        const photos = held?.uploads.length ?? job.stages?.find((record) => record.stage === 'ingest')?.count ?? 0
        const state = buildEnd(job, photos)
        if (state === null) return
        ended = true
        buildEnded(jobId, state.status)
        const { variant, heading } = state
        const kinds = new Set(state.actions.map((kind) => (held === null ? 'startOver' : kind)))
        // Hosted: a "Try again" on screen says it uses one of the remaining judge builds; a reopened tab holds no
        // photos, so it offers only "Start over" and the sentence stays out.
        const retries = mode === 'hosted' && kinds.has('tryAgain')
        const sentence = retries ? `${state.sentence} ${strings.judgeBuildRetry}` : state.sentence
        showBanner(banners, { variant, heading, sentence, actions: [...kinds].map(action) })
      }

      /** `queued` shows its warning once; the first poll past it clears that warning and ends the Timer's queue. */
      function queue(job: JobState): void {
        if (job.status === 'queued') {
          buildQueued(jobId)
          if (queuedBanner === null) queuedBanner = showBanner(banners, QUEUED)
          return
        }
        buildDequeued(jobId)
        if (queuedBanner?.isConnected === true) showBanner(banners, null)
        queuedBanner = null
      }

      function apply(job: JobState): void {
        status = job.status
        queue(job)
        stages.update(stageRows(job))
        if (!masked && (job.mask_preview ?? []).length > 0) {
          masked = true
          void showMask(job)
        }
        if (job.status !== 'done') live = true
        else if (job.room_id != null) done(job, job.room_id)
        end(job)
      }

      function hideStrip(): void {
        if (!strip.isConnected) return
        strip.remove()
        announce('')
      }

      async function poll(): Promise<void> {
        let job: JobState
        try {
          job = await getBuild(jobId)
        } catch (error) {
          const refused = error instanceof RequestFailed && error.status !== null && error.status < 500
          if (!mounted) return
          if (refused) {
            hideStrip() // polling ends here, so the strip's "catches up" line would no longer hold
            const gone = roomGone(error)
            if (gone !== null) onGone(gone)
            else if (error instanceof RequestFailed && error.code === 'job_not_found') onGone('room_not_found')
            return
          }
          missed += 1
          if (missed === MISSED_POLLS) {
            left.prepend(strip)
            announce(strings.reconnectingBuild)
          }
          polling = setTimeout(() => void poll(), BUILD_POLL_MS)
          return
        }
        if (!mounted) return
        missed = 0
        hideStrip()
        apply(job)
        if (job.status === 'queued' || job.status === 'running') polling = setTimeout(() => void poll(), BUILD_POLL_MS)
      }

      void poll()
      return () => {
        mounted = false
        asking?.()
        clearTimeout(polling)
        if (started) releasePhotos()
      }
    },
  }
}
