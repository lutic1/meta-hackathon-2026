import './retention-summary.css'
import { strings } from '../strings.ts'

/**
 * `{components.retention-summary}` (UX-DR20, FR-6): "Where your photos go.", the `GET /meta` `retention` text exactly
 * as served, then the label "Your play history" over the verbatim Privacy line. Always fully expanded: no control,
 * nothing collapsed or truncated.
 */
export function retentionSummary(retention: string): HTMLElement {
  const summary = document.createElement('section')
  summary.className = 'retention-summary'
  const heading = document.createElement('h2')
  heading.className = 'retention-heading display-sm'
  heading.textContent = strings.retentionHeading
  const text = document.createElement('p')
  text.className = 'retention-text body-sm'
  text.textContent = retention
  const label = document.createElement('p')
  label.className = 'retention-label label'
  label.textContent = strings.playHistory
  const privacy = document.createElement('p')
  privacy.className = 'retention-privacy body-md'
  privacy.textContent = strings.privacyLine
  summary.append(heading, text, label, privacy)
  return summary
}
