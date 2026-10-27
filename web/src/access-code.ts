// The Access code a Hosted judge entered (FR-32, AD-9): held in this module's memory for the tab's lifetime and sent
// only as `X-Access-Code` on `POST /builds`. It is never written to any browser storage, so a reload or a reopened
// tab holds none; polling `#/build/<job_id>` and the Build view need no code. The builds left the accepted check
// reported are held beside it, less each Build this tab has had accepted since, since every accepted Build claims a
// judge build whatever it ends in (A-25).

let held: string | null = null
let left: number | null = null

/** Keeps `code`, the one `POST /access/check` accepted, for this tab's `POST /builds`, and the builds left it reported. */
export function holdAccessCode(code: string, buildsLeft: number): void {
  held = code
  left = buildsLeft
}

/** The Access code this tab holds; null before one is accepted (and always in Local mode). */
export function accessCode(): string | null {
  return held
}

/** The judge builds left as this tab knows them; null before a code is accepted (and always in Local mode). */
export function judgeBuildsLeft(): number | null {
  return left
}

/** `POST /builds` accepted a Build from this tab: it claimed one judge build. */
export function claimJudgeBuild(): void {
  if (left !== null) left = Math.max(0, left - 1)
}
