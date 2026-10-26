// Every client-authored user-facing string, copied verbatim from EXPERIENCE.md Voice and Tone (UX-DR73, UX-DR75);
// "No rooms yet." is the one line EXPERIENCE.md gives only in Component Patterns (Stored Room row).
// tests/web/test_strings.py checks each value against its source. Lines the server serves (Disclosure lines,
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
  noRooms: 'No rooms yet.',
  puzzleCount: '{n} puzzles',
  play: 'Play',
  sessionStartRefused: "Keyframe couldn't start this room.",
  sessionStartRefusedBody: 'Your room is safe. Try again.',
  tryAgain: 'Try again',
} as const

/** `template` with each `{name}` replaced by `values[name]`. */
export function fill(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, name: string) => (name in values ? String(values[name]) : match))
}
