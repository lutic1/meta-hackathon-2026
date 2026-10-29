// The Access code a Hosted judge entered (FR-32, AD-9): held in this module's memory for the tab's lifetime and sent
// only as `X-Access-Code` on `POST /builds`. It is never written to any browser storage, so a reload or a reopened
// tab holds none; polling `#/build/<job_id>` and the Build view need no code. The builds left are never counted
// here: other judges build too, so the Capture screen shows the count the server last answered (decision 66).
import { checkAccess } from './api/index.ts'

let held: string | null = null
/** The builds left the accepting check just answered, taken once by the Capture screen it opens. */
let fresh: number | null = null

/** Keeps `code`, the one `POST /access/check` accepted, for this tab's `POST /builds`, and the count it answered. */
export function holdAccessCode(code: string, buildsLeft: number): void {
  held = code
  fresh = buildsLeft
}

/** The Access code this tab holds; null before one is accepted (and always in Local mode). */
export function accessCode(): string | null {
  return held
}

/**
 * The judge builds left as the server counts them now: the accepting check's answer once, then a fresh
 * `POST /access/check` with the held code; null when no code is held (always in Local mode) or the check does not
 * answer with a count, so the judge enters the code again.
 */
export async function judgeBuildsLeft(): Promise<number | null> {
  if (held === null) return null
  if (fresh !== null) {
    const left = fresh
    fresh = null
    return left
  }
  try {
    const answer = await checkAccess(held)
    return answer.ok ? answer.builds_left : null
  } catch {
    return null
  }
}
