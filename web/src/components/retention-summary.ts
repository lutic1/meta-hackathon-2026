import './retention-summary.css'
import { strings } from '../strings.ts'

const POLICY_LINK = /https:\/\/\S*[^\s.,]/g

/** The served text as text nodes, each URL in it an anchor that opens that provider policy page. */
function servedText(retention: string): Node[] {
  const nodes: Node[] = []
  let last = 0
  for (const match of retention.matchAll(POLICY_LINK)) {
    nodes.push(document.createTextNode(retention.slice(last, match.index)))
    const link = document.createElement('a')
    link.className = 'retention-link'
    link.href = match[0]
    link.textContent = match[0]
    link.target = '_blank'
    link.rel = 'noopener noreferrer'
    nodes.push(link)
    last = match.index + match[0].length
  }
  nodes.push(document.createTextNode(retention.slice(last)))
  return nodes
}

/**
 * `{components.retention-summary}` (UX-DR20, FR-6): "Where your photos go.", the `GET /meta` `retention` text exactly
 * as served, each provider-policy URL in it a link, then the label "Your play history" over the verbatim Privacy
 * line, and below it, under cut 2 only, the `profileFile` control. Always fully expanded: nothing collapsed or
 * truncated.
 */
export function retentionSummary(retention: string, profileFile: HTMLElement | null): HTMLElement {
  const summary = document.createElement('section')
  summary.className = 'retention-summary'
  const heading = document.createElement('h2')
  heading.className = 'retention-heading display-sm'
  heading.textContent = strings.retentionHeading
  const text = document.createElement('p')
  text.className = 'retention-text body-sm'
  text.append(...servedText(retention))
  const label = document.createElement('p')
  label.className = 'retention-label label'
  label.textContent = strings.playHistory
  const privacy = document.createElement('p')
  privacy.className = 'retention-privacy body-md'
  privacy.textContent = strings.privacyLine
  summary.append(heading, text, label, privacy)
  if (profileFile !== null) summary.append(profileFile)
  return summary
}
