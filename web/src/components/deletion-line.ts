import './deletion-line.css'
import { strings } from '../strings.ts'

/**
 * `{components.deletion-line}` (FR-33, UX-DR44): "Deleted Tue Nov 10" as one plain `body-sm` paragraph on
 * `chrome-raised`, never parchment; it takes no focus and is read as plain text where it stands.
 */
export function deletionLine(): HTMLParagraphElement {
  const line = document.createElement('p')
  line.className = 'deletion-line body-sm'
  line.textContent = strings.deletedOn
  return line
}
