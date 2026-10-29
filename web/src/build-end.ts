// How a Build that gives no Room ended, read from job state alone (FR-4, FR-10, AD-13, UX-DR21): the status the UI
// keys on, with the envelope codes mapped onto it (`too_few_interactables` asks for more photos, `spend_cap_exceeded`
// is the Spend cap, `provider_error` names the model service), and the banner each one shows. Nothing offers a
// partial Room: an end state's only ways on are a new Build or the Capture screen.
import type { JobState } from '../types'
import { stageRows } from './build-stages.ts'
import { MAX_PHOTOS } from './photos.ts'
import { fill, strings } from './strings.ts'

/** A banner action: a new Build with the same photos, more photos for a new Build, or the empty Capture screen. */
export type EndAction = 'tryAgain' | 'addPhotos' | 'startOver'

export interface BuildEnd {
  /** The status the UI keys on; the Timer shows it beside its frozen digits in player words. */
  status: 'failed' | 'needs_more_photos' | 'needs_recapture'
  variant: 'error' | 'warning'
  heading: string
  sentence: string
  actions: readonly EndAction[]
}

/** The end state of `job`, `photos` being how many photos its set holds; null while it runs or once it is done. */
export function buildEnd(job: JobState, photos: number): BuildEnd | null {
  const code = job.error?.code ?? null
  if (job.status === 'needs_more_photos' || code === 'too_few_interactables') {
    const full = photos >= MAX_PHOTOS
    return {
      status: 'needs_more_photos',
      variant: 'error',
      heading: strings.tooFewObjects,
      sentence: full ? strings.tooFewObjectsFull : strings.tooFewObjectsBody,
      actions: full ? ['startOver'] : ['addPhotos', 'startOver'],
    }
  }
  if (job.status === 'needs_recapture') {
    return {
      status: 'needs_recapture',
      variant: 'error',
      heading: strings.recapture,
      sentence: strings.recaptureBody,
      actions: ['startOver'],
    }
  }
  if (job.status !== 'failed') return null
  if (code === 'spend_cap_exceeded') {
    return { status: 'failed', variant: 'warning', heading: strings.spendCap, sentence: strings.spendCapBody, actions: ['startOver'] }
  }
  // The heading names the row the Stage list shows failed; a job failed before any stage ran names the first one left.
  const rows = stageRows(job)
  const stopped = rows.find((row) => row.state === 'failed') ?? rows.find((row) => row.state !== 'done')
  return {
    status: 'failed',
    variant: 'error',
    heading: fill(strings.buildStopped, { stage: (stopped?.name ?? strings.sceneLoading).toLowerCase() }),
    sentence: code === 'provider_error' ? strings.providerCause : strings.unexpectedCause,
    actions: ['tryAgain'],
  }
}
