// The Capture Timer (FR-5, UX-DR17, AR-14): one run from the Upload click (T0) to the first Hotspot pointer response
// on the Play screen its Build opened (T1), or to an end status. Every time is a wall-clock epoch ms (`Date.now()`),
// never read from the server or `GET /meta`, so the Timer counts in real time whatever the Demo timescale, never waits
// on a poll, and a reload resumes from the recorded T0. The run is kept in this tab's session storage, the one thing
// the client stores; when storage is refused the Timer still runs for the page.
import type { JobState } from '../types'
import { timer } from './components/timer.ts'
import { FIRST_POINTER_RESPONSE, type FirstPointerResponseDetail } from './scene/index.ts'
import { strings } from './strings.ts'

/** A Build that ended without a Room, as the Timer names it in player words: never the raw job status (decision 62). */
type EndStatus = Extract<JobState['status'], 'failed' | 'needs_more_photos' | 'needs_recapture'>

const END_STATUS: Record<EndStatus, string> = {
  failed: strings.timerFailed,
  needs_more_photos: strings.timerMorePhotos,
  needs_recapture: strings.timerRecapture,
}

export interface TimerRun {
  /** The Upload click (T0). */
  t0: number
  /** The Build `POST /builds` accepted for the run's set. */
  jobId: string | null
  /** The Session that Build opened on the Play screen. */
  sessionId: string | null
  /** When it stopped (T1 or the end status); null while it counts. */
  stoppedAt: number | null
  /** The end status beside the frozen digits, in player words; null while it counts and once frozen at T1. */
  status: string | null
  /** Hosted: the Build's last poll read `queued`, so "Waiting to build" stands in place of the digits (absent on older runs). */
  queued?: boolean
  /** Hosted: T0 to the first poll that read the Build no longer `queued`, once it was seen queued; else absent. */
  queueMs?: number
}

const STORAGE_KEY = 'keyframe-capture-timer'
/** How often the running digits are redrawn; each redraw reads the clock afresh, so nothing drifts. */
const TICK_MS = 250

const listeners = new Set<() => void>()
let run: TimerRun | null = read()

function read(): TimerRun | null {
  try {
    const stored = sessionStorage.getItem(STORAGE_KEY)
    return stored === null ? null : (JSON.parse(stored) as TimerRun)
  } catch {
    return null
  }
}

function save(next: TimerRun): void {
  run = next
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    // Storage refused: the run lives as long as the page.
  }
  for (const listener of listeners) listener()
}

/** The run still counting, if there is one. */
function counting(): TimerRun | null {
  return run !== null && run.stoppedAt === null ? run : null
}

/** The Upload click at `t0`: a new run, replacing any earlier one. */
export function startTimer(t0: number): void {
  save({ t0, jobId: null, sessionId: null, stoppedAt: null, status: null })
}

/** `POST /builds` accepted the set as `jobId`: a reload of `#/build/<job_id>` resumes the run from its T0. */
export function buildAccepted(jobId: string): void {
  const current = counting()
  if (current !== null && current.jobId === null) save({ ...current, jobId })
}

/** A poll read the Build `jobId` `queued` (Hosted): its run shows "Waiting to build" in place of the digits, still counting. */
export function buildQueued(jobId: string): void {
  const current = counting()
  if (current !== null && current.jobId === jobId && current.queued !== true) save({ ...current, queued: true })
}

/**
 * A poll read the Build `jobId` past `queued`: the digits return, and a run that was shown queued records its time
 * in the queue, T0 to now, measured by the client.
 */
export function buildDequeued(jobId: string): void {
  const current = counting()
  if (current !== null && current.jobId === jobId && current.queued === true) {
    save({ ...current, queued: false, queueMs: Date.now() - current.t0 })
  }
}

/** The Build opened `sessionId` on the Play screen: that Session shows the run until T1, and frozen after it. */
export function sessionOpened(jobId: string, sessionId: string): void {
  const current = counting()
  if (current !== null && current.jobId === jobId) save({ ...current, sessionId })
}

/**
 * The Build `jobId` ended without a Room (`failed`, `needs_more_photos`, `needs_recapture`): its run stops beside
 * that status in player words; a run of another Build is left as it is.
 */
export function buildEnded(jobId: string, status: EndStatus): void {
  if (counting()?.jobId === jobId) stopTimer(END_STATUS[status])
}

/** The Build that opened `sessionId` in this tab, while its run is the one kept; null for any other Session. */
export function sessionJob(sessionId: string): string | null {
  return run !== null && run.sessionId === sessionId ? run.jobId : null
}

/** Stops the counting run: at T1 when `status` is null, else beside that end status. A stopped run stays frozen. */
export function stopTimer(status: string | null): void {
  const current = counting()
  if (current !== null) save({ ...current, stoppedAt: Date.now(), status })
}

/**
 * Shows the run in the top bar's Timer slot while `belongs(run)` holds, else leaves the slot empty: the Capture
 * screen shows the run it started, `#/build/<job_id>` the run of that Build, the Play and Completion screens the run
 * of the Session the Build opened, so a replayed stored Room never shows it. The run stops at T1 on the first Hotspot
 * pointer response of its Session (the 1.19 signal; keyboard focus never sends it). `frozen` (the Completion screen)
 * draws the run without ticking, so the digits never move there. Returns the teardown.
 */
export function mountTimer(slot: HTMLElement, belongs: (run: TimerRun) => boolean, frozen = false): () => void {
  const view = timer()
  let ticking: ReturnType<typeof setInterval> | undefined

  function render(): void {
    const shown = run !== null && belongs(run) ? run : null
    if (shown === null) {
      slot.replaceChildren()
    } else {
      const elapsedMs = (shown.stoppedAt ?? Date.now()) - shown.t0
      if (shown.stoppedAt === null) view.render({ kind: 'running', elapsedMs, queued: shown.queued === true })
      else if (shown.status === null) view.render({ kind: 'playable', elapsedMs, queueMs: shown.queueMs ?? null })
      else view.render({ kind: 'ended', elapsedMs, status: shown.status })
      if (!view.element.isConnected) slot.replaceChildren(view.element)
    }
    if (shown?.stoppedAt === null && !frozen) ticking ??= setInterval(render, TICK_MS)
    else {
      clearInterval(ticking)
      ticking = undefined
    }
  }

  function respond(event: Event): void {
    const { sessionId } = (event as CustomEvent<FirstPointerResponseDetail>).detail
    if (counting()?.sessionId === sessionId) stopTimer(null)
  }

  listeners.add(render)
  window.addEventListener(FIRST_POINTER_RESPONSE, respond)
  render()
  return () => {
    listeners.delete(render)
    window.removeEventListener(FIRST_POINTER_RESPONSE, respond)
    clearInterval(ticking)
    slot.replaceChildren()
  }
}
