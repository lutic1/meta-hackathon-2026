import './completion.css'
import type { RoomResult, SessionState } from '../types'
import { getResult, listRooms } from './api/index.ts'
import { buildViewLink } from './build-view.ts'
import { sessionJob } from './capture-timer.ts'
import { primaryButton } from './components/button.ts'
import { formatElapsed } from './components/timer.ts'
import { announce } from './live-region.ts'
import { mountPlayBehind } from './play.ts'
import { putResult } from './profile/index.ts'
import { placeHref } from './router.ts'
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
 * under cut 0. The heading takes focus, and the sign-off is written to the live region once, as "The Guide: {line}".
 * The top bar's `controls` keep "Show all objects" in place, inert. Returns the teardown.
 */
export function mountCompletion(
  body: HTMLElement,
  sceneColumn: HTMLElement,
  sideColumn: HTMLElement,
  session: SessionState,
  profile: string,
  controls: HTMLElement,
): () => void {
  sceneColumn.inert = true
  sideColumn.inert = true
  const unmountPlay = mountPlayBehind(sceneColumn, sideColumn, session, controls)

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
  actions.append(
    primaryButton({
      label: strings.buildAnotherRoom,
      pendingLabel: strings.buildAnotherRoom,
      onActivate: async () => {
        location.hash = placeHref({ route: { name: 'home' }, profile })
      },
    }),
  )

  sheet.append(heading, signature, stats, times, failed, actions)
  scrim.append(sheet)
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

  let mounted = true
  let retry: ReturnType<typeof setTimeout> | undefined
  async function load(): Promise<void> {
    let result: RoomResult
    try {
      result = await getResult(session.id)
    } catch {
      if (!mounted) return
      failed.hidden = false
      retry = setTimeout(() => void load(), RESULT_RETRY_MS)
      return
    }
    if (!mounted) return
    void putResult(profile, result)
    show(result)
  }
  void load()
  void roomJob(session).then((jobId) => {
    const link = jobId === null ? null : buildViewLink(jobId, profile, true)
    if (mounted && link !== null) actions.append(link)
  })

  return () => {
    mounted = false
    clearTimeout(retry)
    unmountPlay()
    scrim.remove()
  }
}
