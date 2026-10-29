import './completion.css'
import type { Meta, RoomResult, SessionState } from '../types'
import { getResult, listRooms } from './api/index.ts'
import { buildViewLink } from './build-view.ts'
import { sessionJob } from './capture-timer.ts'
import { primaryButton } from './components/button.ts'
import { deletionLine } from './components/deletion-line.ts'
import { saveProfileControl } from './components/profile-file.ts'
import { formatElapsed } from './components/timer.ts'
import { announce } from './live-region.ts'
import { mountPlayBehind } from './play.ts'
import { CUT_2, profileFile, putResult } from './profile/index.ts'
import { placeHref } from './router.ts'
import { type RoomGone, roomGone, showRoomGone } from './room-gone.ts'
import { fill, strings } from './strings.ts'
import { speakerPrefix, wizardPortrait } from './wizards/portrait.ts'

/** While `GET /sessions/<id>/result` fails, the sheet asks again this often (UX-DR66). */
export const RESULT_RETRY_MS = 2000

/** What a stat shows until the result returns: the static ellipsis of every pending state. */
const PENDING = '…'

/** The Guide's sign-off, chosen from the Rungs used alone, never from objects (UX-DR44). */
export function signOff(rungsUsed: number): string {
  if (rungsUsed === 0) return strings.signOffNoHints
  return rungsUsed <= 3 ? strings.signOffSomeHints : strings.signOffManyHints
}

interface Stat {
  element: HTMLElement
  show: (value: string) => void
}

/** One of the three stats: its `label` in `ink-muted` over the value in `mono-timer`, pending until shown. */
function stat(label: string): Stat {
  const element = document.createElement('div')
  element.className = 'completion-stat'
  const name = document.createElement('div')
  name.className = 'completion-stat-label label'
  name.textContent = label
  const value = document.createElement('div')
  value.className = 'completion-stat-value mono-timer is-pending'
  value.textContent = PENDING
  element.append(name, value)
  return {
    element,
    show: (text) => {
      value.classList.remove('is-pending')
      value.textContent = text
    },
  }
}

/** The per-Puzzle times: one "Puzzle {n}" row per Puzzle in Room order, no header row and no mark on the Exit. */
function timeRows(result: RoomResult): HTMLTableRowElement[] {
  return result.puzzles.map((puzzle, index) => {
    const row = document.createElement('tr')
    const name = document.createElement('th')
    name.scope = 'row'
    name.className = 'body-sm'
    name.textContent = fill(strings.puzzleHeading, { n: index + 1 })
    const time = document.createElement('td')
    time.className = 'mono-sm'
    time.textContent = formatElapsed(puzzle.time_spent_ms)
    row.append(name, time)
    return row
  })
}

/**
 * The job that built the Session's Room: the Build that opened it in this tab, else the `RoomSummary` of its Room in
 * `GET /rooms`; null when neither names one.
 */
async function roomJob(session: SessionState): Promise<string | null> {
  const opened = sessionJob(session.id)
  if (opened !== null) return opened
  try {
    return (await listRooms()).find((room) => room.room_id === session.room_id)?.job_id ?? null
  } catch {
    return null
  }
}

/**
 * The Completion screen (FR-13, UX-DR44, UX-DR66): the Play screen dimmed under the scrim, which covers the page body
 * only, and the centered 720 px parchment sheet (`{components.completion-sheet}`) over it. The sheet reads
 * `GET /sessions/<id>/result`: the heading "The room is open.", the Guide's sign-off beside its 48 px portrait, "Time",
 * "Hints used" (the Rungs used) and "Wrong attempts" three across in `mono-timer`, and the "Time per puzzle" table.
 * Until the result returns the stats show as pending; while the request fails a plain line says so and it is asked
 * again every 2000 ms, nothing recorded. The returned `RoomResult` is put into the `profile` once (web/profile keys it
 * by `room_id`, so a reload of this route records nothing new). "Build another room", the one primary action, goes to `#/` and is there from the start;
 * "How this room was built" (secondary) joins it once the Room's job is known, opening its Build view, and is absent
 * under cut 0. Under cut 2 in Local mode, once the result is recorded, "Save profile file" (secondary) follows them,
 * downloading the profile with that result, its plain line below the actions; a refused record offers no download.
 * The heading takes focus, and the sign-off is written to the live region once, as "The Guide: {line}".
 * A session state whose `judge_room` the server set (a Hosted Judge room, never a Demo or Local room) adds the
 * "Deleted Tue Nov 10" deletion line directly below the sheet, on the scrim, off the paper; the client never infers it.
 * The top bar's `controls` keep "Show all objects" in place, inert. A Room answered 410 `room_deleted` or 404
 * `room_not_found`, or a result read answered 410 `room_deleted`, replaces the page body with its card
 * (`showRoomGone`). Returns the teardown.
 */
export function mountCompletion(
  body: HTMLElement,
  sceneColumn: HTMLElement,
  sideColumn: HTMLElement,
  session: SessionState,
  profile: string,
  mode: Meta['mode'],
  controls: HTMLElement,
): () => void {
  sceneColumn.inert = true
  sideColumn.inert = true
  let mounted = true
  let retry: ReturnType<typeof setTimeout> | undefined
  const unmountPlay = mountPlayBehind(sceneColumn, sideColumn, session, controls, (gone) => {
    mounted = false
    clearTimeout(retry)
    showRoomGone(body, gone, mode, profile)
  })
  /** A result read refused for a deleted Judge room: the same card, in place of the sheet. */
  const gone = (which: RoomGone): void => {
    mounted = false
    showRoomGone(body, which, mode, profile)
  }

  const scrim = document.createElement('div')
  scrim.className = 'completion-scrim'
  const sheet = document.createElement('section')
  sheet.className = 'completion-sheet'
  sheet.setAttribute('role', 'region')
  sheet.setAttribute('aria-labelledby', 'completion-heading')

  const heading = document.createElement('h1')
  heading.id = 'completion-heading'
  heading.className = 'completion-heading display-lg'
  heading.tabIndex = -1
  heading.textContent = strings.roomOpen

  const signature = document.createElement('div')
  signature.className = 'completion-signoff'
  signature.hidden = true
  const line = document.createElement('p')
  line.className = 'wizard-line'
  signature.append(wizardPortrait('guide', 48), line)

  const time = stat(strings.statTime)
  const hints = stat(strings.statHints)
  const wrong = stat(strings.statWrong)
  const stats = document.createElement('div')
  stats.className = 'completion-stats'
  stats.setAttribute('aria-busy', 'true')
  stats.append(time.element, hints.element, wrong.element)

  const times = document.createElement('div')
  times.className = 'completion-times'
  times.hidden = true
  const timesLabel = document.createElement('div')
  timesLabel.id = 'completion-times-label'
  timesLabel.className = 'completion-stat-label label'
  timesLabel.textContent = strings.timePerPuzzle
  const table = document.createElement('table')
  table.setAttribute('aria-labelledby', timesLabel.id)
  const rows = document.createElement('tbody')
  table.append(rows)
  times.append(timesLabel, table)

  const failed = document.createElement('p')
  failed.className = 'completion-error body-sm'
  failed.textContent = strings.resultLoadFailed
  failed.hidden = true

  const actions = document.createElement('div')
  actions.className = 'completion-actions'
  const buildAnother = primaryButton({
    label: strings.buildAnotherRoom,
    pendingLabel: strings.buildAnotherRoom,
    onActivate: async () => {
      location.hash = placeHref({ route: { name: 'home' }, profile })
    },
  })
  actions.append(buildAnother)

  sheet.append(heading, signature, stats, times, failed, actions)
  scrim.append(sheet)
  if (session.judge_room === true) scrim.append(deletionLine())
  body.append(scrim)
  heading.focus()

  function show(result: RoomResult): void {
    const said = signOff(result.rungs_used)
    line.replaceChildren(speakerPrefix('guide'), said)
    signature.hidden = false
    time.show(formatElapsed(result.elapsed_ms))
    hints.show(String(result.rungs_used))
    wrong.show(String(result.wrong_attempts))
    stats.removeAttribute('aria-busy')
    rows.replaceChildren(...timeRows(result))
    times.hidden = false
    failed.hidden = true
    announce(`${strings.speakerGuide} ${said}`)
  }

  async function load(): Promise<void> {
    let result: RoomResult
    try {
      result = await getResult(session.id)
    } catch (error) {
      if (!mounted) return
      if (roomGone(error) === 'room_deleted') return gone('room_deleted')
      failed.hidden = false
      retry = setTimeout(() => void load(), RESULT_RETRY_MS)
      return
    }
    if (!mounted) return
    const recorded = putResult(profile, result, mode)
    show(result)
    void recorded.then(offerSave, () => {}) // a refused record leaves the profile as it was, with nothing to save
  }

  /** Cut 2, Local mode: "Save profile file" after the actions, its plain line under them. */
  function offerSave(): void {
    if (!mounted || !CUT_2 || mode !== 'local') return
    const save = saveProfileControl(profile, () => profileFile(profile))
    actions.append(save.button)
    actions.after(save.line)
  }
  void load()
  void roomJob(session).then((jobId) => {
    const link = jobId === null ? null : buildViewLink(jobId, profile, true)
    if (mounted && link !== null) buildAnother.after(link)
  })

  return () => {
    mounted = false
    clearTimeout(retry)
    unmountPlay()
    scrim.remove()
  }
}
