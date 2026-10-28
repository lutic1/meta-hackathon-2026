import './access-code-build.css'
import type { AccessCheck } from '../../types'
import { holdAccessCode } from '../access-code.ts'
import { checkAccess, RequestFailed } from '../api/index.ts'
import { fill, strings } from '../strings.ts'
import { primaryButton } from './button.ts'
import { type BannerState, bannerSlot, showBanner } from './error-banner.ts'

/** The status a rate-limited access attempt answers (AD-9: 429 `too_many_attempts`). */
const TOO_MANY_ATTEMPTS = 429

/** The Access code field's id: the landing's "Build your own room" verb moves focus to it. */
export const ACCESS_CODE_FIELD = 'access-code'

/** A refused code: `{ok: false}` from the check, or 403 `access_denied` on `POST /builds`. */
export const accessRefused: BannerState = { variant: 'error', heading: strings.accessCodeRefused, actions: [], compact: true }

/** Too many access attempts from this address (429 `too_many_attempts`). */
export const tooManyTries: BannerState = { variant: 'warning', heading: strings.tooManyTries, actions: [], compact: true }

/** Every judge build used: `builds_left` 0 from the check, or `build_quota_exceeded` on `POST /builds`. */
export const buildQuota: BannerState = { variant: 'warning', heading: strings.buildQuota, actions: [] }

/** The `body-sm` status line, empty until it shows the empty-submit line or, accepted, the builds left. */
function statusLine(): HTMLParagraphElement {
  const status = document.createElement('p')
  status.className = 'access-build-status body-sm'
  return status
}

function showStatus(status: HTMLElement, text: string, accepted = false): void {
  status.textContent = text
  status.classList.toggle('is-accepted', accepted)
}

/**
 * The accepted status line, "{n} of 20 builds left" in `success`, as the Capture screen keeps it under Upload, on the
 * panel's `chrome-raised` so it reads on the surface the contrast table names for it.
 */
export function buildsLeftLine(buildsLeft: number): HTMLParagraphElement {
  const status = statusLine()
  status.classList.add('access-build-left')
  showStatus(status, fill(strings.buildsLeft, { n: buildsLeft }), true)
  return status
}

/**
 * The Access-code build (`{components.access-code-field}`, FR-32, UX-DR59) in the Hosted landing's right column: the
 * heading "Build your own room", the visible label "Access code" over a 44 px `mono-code` field beside "Check code"
 * (primary), its compact banner slot, then the `body-sm` status line, plain page content and the field's description.
 *
 * Enter in the field or "Check code" submits. An empty field shows the empty-submit line and sends nothing; otherwise
 * the button shows its pending label while `POST /access/check {code}` is in flight. A wrong code shows the compact
 * error banner, too many tries the compact warning, and `builds_left` 0 the Build quota warning, each taking focus;
 * the Demo room cards beside the panel stay active throughout. An accepted code is held in memory for this tab
 * (`access-code.ts`), the status line reads "{n} of 20 builds left" in `success`, and `onAccepted` opens the Capture
 * screen. A check that gets no answer changes nothing, so the judge can check again.
 */
export function accessCodeBuild(onAccepted: (buildsLeft: number) => void): HTMLElement {
  const panel = document.createElement('section')
  panel.className = 'access-build'
  const heading = document.createElement('h2')
  heading.id = 'access-build-heading'
  heading.className = 'access-build-heading display-sm'
  heading.textContent = strings.buildYourOwnRoom
  panel.setAttribute('aria-labelledby', heading.id)

  const field = document.createElement('input')
  field.id = ACCESS_CODE_FIELD
  field.type = 'text'
  field.className = 'access-build-field mono-code'
  field.autocomplete = 'off'
  field.spellcheck = false
  field.setAttribute('autocapitalize', 'off')
  const label = document.createElement('label')
  label.className = 'access-build-label label'
  label.htmlFor = field.id
  label.textContent = strings.accessCode
  const status = statusLine()
  status.id = 'access-code-status'
  field.setAttribute('aria-describedby', status.id)

  const banners = bannerSlot()
  const button = primaryButton({ label: strings.checkCode, pendingLabel: strings.checking, onActivate: check })
  const row = document.createElement('div')
  row.className = 'access-build-row'
  row.append(field, button)
  panel.append(heading, label, row, banners, status)

  async function check(): Promise<void> {
    const code = field.value.trim()
    showBanner(banners, null)
    showStatus(status, '')
    if (code === '') {
      showStatus(status, strings.accessCodeEmpty)
      field.focus()
      return
    }
    let answer: AccessCheck
    try {
      answer = await checkAccess(code)
    } catch (error) {
      if (error instanceof RequestFailed && error.status === TOO_MANY_ATTEMPTS) showBanner(banners, tooManyTries)
      return
    }
    if (!answer.ok || answer.builds_left === null) {
      showBanner(banners, accessRefused)
      return
    }
    if (answer.builds_left === 0) {
      showBanner(banners, { ...buildQuota, compact: true })
      return
    }
    holdAccessCode(code, answer.builds_left)
    showStatus(status, fill(strings.buildsLeft, { n: answer.builds_left }), true)
    onAccepted(answer.builds_left)
  }

  field.addEventListener('keydown', (event) => {
    if (event.key !== 'Enter') return
    event.preventDefault()
    button.click()
  })
  return panel
}
