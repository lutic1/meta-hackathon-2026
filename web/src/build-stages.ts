// The Stage list's rows read from job state (FR-5, UX-DR16, AR-31): the six stage names over the eight
// pipeline stages (A-11, and "Writing the story" since story mode), a "Rewriting puzzles" row and a second "Testing the room" row per Regeneration, and each done
// row's duration, result and model id exactly as `GET /builds/<job_id>` records them. Nothing here is guessed: a
// row shows what its stage records carry and leaves out what they do not.
import type { JobState, StageRecord } from '../types'
import { fill, strings } from './strings.ts'

export type RowState = 'pending' | 'running' | 'done' | 'failed'

export interface StageRow {
  /** Stable across polls: `reading`, `finding`, `writing-<k>`, `testing-<k>`, `story` or `scene`, k the attempt. */
  key: string
  name: string
  state: RowState
  /** The sum of the row's stage durations, on a done row. */
  durationMs: number | null
  /** The row's model ids joined, on a done row ("muse-spark-1.3 · sam-3.1"). */
  model: string | null
  /** The plain result lines of a done row: one, or two for "Testing the room" (the rules, then the test run). */
  results: string[]
  /** "Sent back: …" on a Rewriting row: the fixed messages of the attempt before it. */
  sentBack: string | null
  /**
   * The Architect's line: on the running row, and on the "Finding objects" row from the first job state that carries
   * the Mask preview on, whatever its state, so the summary of what was found stays in view through the later stages.
   */
  line: string | null
  /** The first "Writing puzzles" row once the author stage has started: it carries the Riddler's introduction. */
  riddler: boolean
}

type Stage = StageRecord['stage']
type Kind = 'reading' | 'finding' | 'writing' | 'testing' | 'story' | 'scene'

const KIND: Record<Stage, Kind> = {
  ingest: 'reading',
  architect: 'finding',
  segment: 'finding',
  author: 'writing',
  validate: 'testing',
  dryrun: 'testing',
  story: 'story',
  scene: 'scene',
}

/** Whether the job is in a status that names the stage it stopped at. */
const STOPPED = new Set<JobState['status']>(['failed', 'needs_more_photos', 'needs_recapture'])

/**
 * The row a status stops at whatever stage it names (EXPERIENCE.md Build job statuses): too few objects at "Finding
 * objects", a re-capture at the last attempt's "Testing the room", the Validator being the gate of every attempt sent
 * back, the author stage's own refusals included.
 */
const STOPPED_AT: Partial<Record<JobState['status'], Kind>> = { needs_more_photos: 'finding', needs_recapture: 'testing' }

function key(kind: Kind, attempt: number): string {
  return kind === 'writing' || kind === 'testing' ? `${kind}-${attempt}` : kind
}

/** `ms` as the done row's duration, one decimal ("4.2 s"). */
export function formatDuration(ms: number): string {
  return fill(strings.stageDuration, { s: (ms / 1000).toFixed(1) })
}

/**
 * The Architect's line for the Mask preview: the found count and the first three labels in segment order (or two);
 * null with fewer than two labels, since the line has no form for them.
 */
export function maskPreviewLine(labels: readonly string[]): string | null {
  const [first, second, third] = labels
  if (second === undefined) return null
  const n = labels.length
  return third === undefined
    ? fill(strings.maskPreviewLineTwo, { n, first, second })
    : fill(strings.maskPreviewLine, { n, first, second, third })
}

/**
 * The rows for `job` (null before the first poll answers: every row pending). Records split into attempts at each
 * author record; the job shows one attempt more than it has authored once its Regeneration count has risen past
 * them. The running row is the job's `stage` (author at the attempt the count names, validate and dry run at the
 * last authored attempt), a stopped job's row is failed (the row its status stops at, else its `stage`'s), every
 * other row with records is done, and `done` makes every row done.
 */
export function stageRows(job: JobState | null): StageRow[] {
  const records = job?.stages ?? []
  const byKey = new Map<string, StageRecord[]>()
  let authored = 0
  for (const record of records) {
    const kind = KIND[record.stage]
    if (kind === 'writing') authored += 1
    const at = key(kind, Math.max(authored - 1, 0))
    byKey.set(at, [...(byKey.get(at) ?? []), record])
  }
  const regenerations = job?.regeneration_count ?? 0
  const attempts = Math.max(1, authored, regenerations + 1)

  let current: string | null = null
  const kind = job === null ? undefined : (STOPPED_AT[job.status] ?? (job.stage == null ? undefined : KIND[job.stage]))
  if (job !== null && kind !== undefined && (job.status === 'running' || STOPPED.has(job.status))) {
    current = key(kind, kind === 'writing' ? regenerations : Math.max(authored - 1, 0))
  }

  const lastValidate = records.findLastIndex((record) => record.stage === 'validate')
  const photos = byKey.get('reading')?.[0]?.count ?? null
  /** "I see {n} things worth a closer look, …" once job state carries the Mask preview. */
  const found = maskPreviewLine((job?.mask_preview ?? []).map((tile) => tile.label))

  function row(kind: Kind, attempt: number): StageRow {
    const at = key(kind, attempt)
    const own = byKey.get(at) ?? []
    let state: RowState = 'pending'
    if (job?.status === 'done') state = 'done'
    else if (at === current) state = job?.status === 'running' ? 'running' : 'failed'
    else if (own.length > 0) state = 'done'
    const done = state === 'done'
    const models = [...new Set(own.map((record) => record.model).filter((model) => model != null))]
    return {
      key: at,
      name: name(kind, attempt),
      state,
      durationMs: done && own.length > 0 ? own.reduce((sum, record) => sum + record.duration_ms, 0) : null,
      model: done && models.length > 0 ? models.join(strings.modeSeparator) : null,
      results: done ? results(kind, attempt, own) : [],
      sentBack: kind === 'writing' && attempt > 0 ? sentBack(attempt) : null,
      line: state === 'running' ? line(kind, attempt) : kind === 'finding' ? found : null,
      riddler: kind === 'writing' && attempt === 0 && state !== 'pending',
    }
  }

  function name(kind: Kind, attempt: number): string {
    if (kind === 'reading') return strings.readingPhotos
    if (kind === 'finding') return strings.findingObjects
    if (kind === 'testing') return strings.testingRoom
    if (kind === 'story') return strings.writingStory
    if (kind === 'scene') return strings.sceneLoading
    if (attempt === 0) return strings.writingPuzzles
    return fill(strings.rewritingPuzzles, { n: attempt, max: job?.regen_max ?? 0 })
  }

  function sentBack(attempt: number): string | null {
    const messages = job?.sent_back?.find((record) => record.attempt === attempt - 1)?.messages
    return messages === undefined ? null : fill(strings.sentBack, { messages: messages.join(' ') })
  }

  function results(kind: Kind, attempt: number, own: readonly StageRecord[]): string[] {
    const count = (stage: Stage): number | null => own.find((record) => record.stage === stage)?.count ?? null
    // A count of one reads `one` when the line has a singular ("1 puzzle"); photos and objects never count one here.
    const counted = (template: string, n: number | null, one = template): string[] =>
      n === null ? [] : [n === 1 ? one : fill(template, { n })]
    if (kind === 'reading') return counted(strings.photoCount, count('ingest'))
    if (kind === 'finding') return counted(strings.objectCount, count('segment'))
    if (kind === 'writing') return counted(strings.puzzleCount, count('author'), strings.onePuzzle)
    if (kind === 'story') return counted(strings.storyLines, count('story'))
    if (kind === 'scene') return counted(strings.scenesReady, count('scene'))
    const lines: string[] = []
    const validator = job?.validator ?? []
    // Job state keeps the latest attempt's Validator verdicts only, so the rules line sits on that attempt's row.
    if (validator.length > 0 && own.includes(records[lastValidate])) {
      const passed = validator.filter((verdict) => verdict.passed).length
      lines.push(fill(strings.rulesPassed, { passed, total: validator.length }))
    }
    const dryrun = own.find((record) => record.stage === 'dryrun')
    const total = byKey.get(key('writing', attempt))?.find((record) => record.stage === 'author')?.count
    // A Dry run that ran names its model; under DRY_RUN=off (cut 4) the record has none and no test run line shows.
    if (dryrun?.model != null && dryrun.count != null && total != null) {
      lines.push(fill(strings.testRunReached, { reached: dryrun.count, total }))
    }
    return lines
  }

  function line(kind: Kind, attempt: number): string {
    const reading = fill(strings.readingLine, { n: photos ?? 0 })
    if (kind === 'reading') return reading
    // The preview arrives with segment's record; until then the Finding objects row keeps the reading line.
    if (kind === 'finding') return found ?? reading
    if (kind === 'writing') return attempt === 0 ? strings.writingLine : strings.regenerationLine
    if (kind === 'testing') return strings.testingLine
    if (kind === 'story') return strings.storyLine
    return strings.sceneLine
  }

  const rows = [row('reading', 0), row('finding', 0)]
  for (let attempt = 0; attempt < attempts; attempt += 1) {
    rows.push(row('writing', attempt))
    // An attempt the author stage itself sent back was never tested: it has no "Testing the room" row.
    const untested = attempt < attempts - 1 && !byKey.has(key('testing', attempt))
    if (!untested) rows.push(row('testing', attempt))
  }
  rows.push(row('story', 0), row('scene', 0))
  return rows
}
