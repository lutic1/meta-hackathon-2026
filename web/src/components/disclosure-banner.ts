import './disclosure-banner.css'

/**
 * `{components.disclosure-banner}`: one line per Disclosure, exactly as served (UX-DR56, UX-DR80).
 * No close control, nothing focusable; null when the list is empty, so the banner is absent.
 */
export function disclosureBanner(lines: readonly string[]): HTMLElement | null {
  if (lines.length === 0) return null
  const banner = document.createElement('div')
  banner.className = 'disclosure-banner'
  for (const line of lines) {
    const row = document.createElement('p')
    row.className = 'body-sm'
    row.textContent = line
    banner.append(row)
  }
  return banner
}
