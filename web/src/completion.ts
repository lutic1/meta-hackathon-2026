import './completion.css'
import type { Meta, PlayView, RoomResult, SessionState } from '../types'
import { getResult, listRooms } from './api/index.ts'
import { buildViewLink } from './build-view.ts'
import { sessionJob } from './capture-timer.ts'
import { countedAt, shareLine } from './completion-line.ts'
import { buildTime } from './components/build-view-header.ts'
import { primaryButton, secondaryButton } from './components/button.ts'
import { deletionLine } from './components/deletion-line.ts'
import { filmstrip as roomFilmstrip } from './components/filmstrip.ts'
import { saveProfileControl } from './components/profile-file.ts'
import { formatElapsed } from './components/timer.ts'
import { motionMs } from './fade.ts'
import { announce } from './live-region.ts'
import { endedOnPlay, mountPlayBehind } from './play.ts'
import { CUT_2, profileFile, profileTemporary, putResult, saveProfileFile } from './profile/index.ts'
import { placeHref } from './router.ts'
import { type RoomGone, roomGone, showRoomGone } from './room-gone.ts'
import { solvedTargets } from './scene/index.ts'
import { fill, strings } from './strings.ts'
import { speakerPrefix, type Wizard, wizardPortrait } from './wizards/portrait.ts'

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

/** A stat counting up from 0 to `final`, drawn each frame through `format`. */
interface Count {
  stat: Stat
  final: number
  format: (value: number) => string
}

/**
 * Counts every stat up from 0 to its final value once (owner decision, Oct 29): a number change only, easing out over
 * `--motion-count`, which reduced motion sets to 0 ms, so the first frame shows the final values. `done` follows the
 * last frame.
 */
function countUp(counts: readonly Count[], done: () => void): void {
  const ms = motionMs('--motion-count')
  let start: number | undefined
  const frame = (now: number): void => {
    start ??= now
    const t = ms === 0 ? 1 : Math.min(1, (now - start) / ms)
    for (const { stat, final, format } of counts) stat.show(format(countedAt(final, t)))
    if (t < 1) requestAnimationFrame(frame)
    else done()
  }
  requestAnimationFrame(frame)
}

const WIZARD_NAMES: Record<Wizard, string> = {
  architect: strings.architect,
  riddler: strings.riddler,
  guide: strings.guide,
  trickster: strings.trickster,
}

/** "Built by" over the four wizards, each a 32 px portrait beside its name in `body-sm`. */
function builtBy(): HTMLElement {
  const element = document.createElement('div')
  element.className = 'completion-built-by'
  const label = document.createElement('div')
  label.id = 'completion-built-by-label'
  label.className = 'completion-stat-label label'
  label.textContent = strings.builtBy
  const list = document.createElement('ul')
  list.className = 'completion-wizards'
  list.setAttribute('aria-labelledby', label.id)
  list.append(
    ...(['architect', 'riddler', 'guide', 'trickster'] as const).map((wizard) => {
      const item = document.createElement('li')
      item.className = 'completion-wizard body-sm'
      item.append(wizardPortrait(wizard, 32), WIZARD_NAMES[wizard])
      return item
    }),
  )
  element.append(label, list)
  return element
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
 * The Completion screen (FR-13, UX-DR44, UX-DR66; the celebration, owner decision Oct 29): the Play screen under the
 * soft scrim, which covers the page body only and leaves the exit photo brighter than the other overlays do, and the
 * centered 720 px parchment sheet (`{components.completion-sheet}`) over it. The sheet reads
 * `GET /sessions/<id>/result`: the heading "The room is open.", the Guide's sign-off beside its 48 px portrait, "Time",
 * "Hints used" (the Rungs used) and "Wrong attempts" three across in `mono-timer`, counting up once from 0 when the
 * result arrives (instant under reduced motion), the filmstrip of the Room's photos with each solved object's outline
 * lit, the "Time per puzzle" table with its plain caption (each Puzzle is timed from when it appeared, so the times
 * overlap) and "Built by" over the four wizards' 32 px portraits and names.
 * Until the result returns the stats show as pending; while the request fails a plain line says so and it is asked
 * again every 2000 ms, nothing recorded. The returned `RoomResult` is put into the `profile` once per Session (web/profile
 * keys it by `room_id` and remembers the Session, so mounting this route again records nothing new, and reopening an
 * older Session's Completion screen never replaces a newer result). A Completion screen that did not follow the Exit
 * on the Play screen in this page load (a reload, a bookmark, history) is a reopened one: its result fills a Room the
 * profile lacks but never replaces a stored or opened one. "Build another room", the one primary action, goes to `#/`
 * and is there from the start;
 * "Copy your result" (secondary) follows it once the result and the Room's title are known, copying one line of the
 * stats and the site's address with no route ("Keyframe - {room} - 4 locks - 3:28 - 2 hints - 0 wrong - {url}", no
 * solution text) and confirming under the actions and in the live region; "How this room was built" (secondary)
 * joins them once the Room's job is known, opening its Build view, and is absent under cut 0. Under cut 2 in Local
 * mode, once the result is recorded, "Save profile file" (secondary) follows them,
 * downloading the profile with that result, its plain line below the actions. Under the actions a plain line says
 * when the result is not safely kept: a profile file the player opened that failed to save ("Progress is still here,
 * but the profile file wasn't saved. Try again.", with "Try again", which writes it again and clears the line once it
 * succeeds), or a browser that refused its storage, so the profile lasts only as long as the page.
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
  const behind = mountPlayBehind(sceneColumn, sideColumn, session, controls, (gone) => {
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

  const filmstrip = document.createElement('div')
  filmstrip.className = 'completion-filmstrip'
  filmstrip.hidden = true

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
  const timesNote = document.createElement('p')
  timesNote.className = 'completion-times-note body-sm'
  timesNote.textContent = strings.timePerPuzzleNote
  times.append(timesLabel, table, timesNote)

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
  const copy = secondaryButton({ label: strings.copyResult, onParchment: true, onActivate: () => void copyResult() })
  copy.hidden = true
  actions.append(buildAnother, copy)
  const copied = document.createElement('p')
  copied.className = 'completion-copied body-sm'
  const kept = document.createElement('div')
  kept.className = 'completion-kept'
  kept.hidden = true
  const wizards = builtBy()

  sheet.append(heading, signature, stats, filmstrip, times, wizards, failed, actions, copied, kept)
  scrim.append(sheet)
  if (session.judge_room === true) scrim.append(deletionLine())
  body.append(scrim)
  heading.focus()

  let loaded: RoomResult | null = null
  let view: PlayView | null = null
  /** "Copy your result" once both the result and the Room's title are known. */
  function offerCopy(): void {
    if (mounted && loaded !== null && view !== null) copy.hidden = false
  }

  /** Copies the one shared line and confirms under the actions and in the live region; a refused write shows it. */
  async function copyResult(): Promise<void> {
    if (loaded === null || view === null) return
    const line = shareLine({
      room: view.name || buildTime(view.created),
      locks: loaded.puzzles.length,
      time: formatElapsed(loaded.elapsed_ms),
      hints: loaded.rungs_used,
      wrong: loaded.wrong_attempts,
      url: location.origin + location.pathname,
    })
    let said: string = strings.resultCopied
    try {
      await navigator.clipboard.writeText(line)
    } catch {
      said = fill(strings.resultNotCopied, { line })
    }
    if (!mounted) return
    copied.textContent = said
    copied.scrollIntoView({ block: 'nearest' }) // the scrim scrolls when the sheet is taller than the body
    announce(said)
  }

  function show(result: RoomResult): void {
    const said = signOff(result.rungs_used)
    line.replaceChildren(speakerPrefix('guide'), said)
    signature.hidden = false
    countUp(
      [
        { stat: time, final: Math.floor(result.elapsed_ms / 1000), format: (s) => formatElapsed(s * 1000) },
        { stat: hints, final: result.rungs_used, format: String },
        { stat: wrong, final: result.wrong_attempts, format: String },
      ],
      () => stats.removeAttribute('aria-busy'),
    )
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
    const recorded = putResult(profile, result, mode, session.id, !endedOnPlay(session.id))
    show(result)
    loaded = result
    offerCopy()
    // A failed save still leaves the result recorded in the page, so it can be downloaded and written again.
    void recorded.then(
      async () => {
        offerSave()
        if (await profileTemporary(profile)) note(strings.progressTemporary)
      },
      () => {
        offerSave()
        note(strings.profileNotSaved, { label: strings.tryAgain, onActivate: () => void saveAgain() })
      },
    )
  }

  /** The plain line under the actions about where the result is kept, with its one action, if any. */
  function note(text: string, action?: { label: string; onActivate: () => void }): void {
    if (!mounted) return
    const line = document.createElement('p')
    line.className = 'completion-kept-line body-sm'
    line.textContent = text
    const retry = action === undefined ? [] : [secondaryButton({ ...action, onParchment: true })]
    kept.replaceChildren(line, ...retry)
    kept.hidden = false
  }

  /** "Try again" on a failed save: writes the profile file again, clearing the line once it is written. */
  async function saveAgain(): Promise<void> {
    try {
      await saveProfileFile(profile)
    } catch {
      return
    }
    if (mounted) kept.hidden = true
  }

  /** Cut 2, Local mode: "Save profile file" after the actions, its plain line under them (after any copied line). */
  function offerSave(): void {
    if (!mounted || !CUT_2 || mode !== 'local') return
    const save = saveProfileControl(profile, () => profileFile(profile))
    actions.append(save.button)
    copied.after(save.line)
  }
  void load()
  behind.room.then(
    (room) => {
      if (!mounted) return
      view = room
      // The objects solved: every find target in the final Inventory, plus each unlock moment's target seen in this page.
      filmstrip.append(roomFilmstrip(room, new Set([...session.inventory, ...solvedTargets(session.id)])))
      filmstrip.hidden = false
      offerCopy()
    },
    () => undefined, // the Play screen behind handles a gone Room; the sheet keeps its stats
  )
  void roomJob(session).then((jobId) => {
    const link = jobId === null ? null : buildViewLink(jobId, profile, true)
    if (mounted && link !== null) copy.after(link)
  })

  return () => {
    mounted = false
    clearTimeout(retry)
    behind.unmount()
    scrim.remove()
  }
}
