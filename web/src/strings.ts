// Every client-authored user-facing string, copied verbatim from EXPERIENCE.md Voice and Tone (UX-DR73, UX-DR75).
// tests/web/test_strings.py checks each value against that source. Lines the server serves (Disclosure lines,
// the Retention summary, opening lines) never live here: they are rendered exactly as received.

export const strings = {
  wordmark: 'Keyframe',
  serverUnreachable: "Keyframe can't reach its server. Retrying.",
  modeLocal: 'Local mode',
  modeHosted: 'Hosted mode',
  cacheOn: 'Cache on',
  cacheOff: 'Cache off',
  modeProfile: 'profile {name}',
  modeSeparator: ' · ',
} as const

/** `template` with each `{name}` replaced by `values[name]`. */
export function fill(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, name: string) => (name in values ? String(values[name]) : match))
}
