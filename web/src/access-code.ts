// The Access code a Hosted judge entered (FR-32, AD-9): held in this module's memory for the tab's lifetime and sent
// only as `X-Access-Code` on `POST /builds`. It is never written to any browser storage, so a reload or a reopened
// tab holds none; polling `#/build/<job_id>` and the Build view need no code.

let held: string | null = null

/** Keeps `code`, the one `POST /access/check` accepted, for this tab's `POST /builds`. */
export function holdAccessCode(code: string): void {
  held = code
}

/** The Access code this tab holds; null before one is accepted (and always in Local mode). */
export function accessCode(): string | null {
  return held
}
