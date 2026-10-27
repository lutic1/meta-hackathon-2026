// Every client-authored user-facing string, copied verbatim from EXPERIENCE.md Voice and Tone (UX-DR73, UX-DR75);
// "No rooms yet." is the one line EXPERIENCE.md gives only in Component Patterns (Stored Room row). EXPERIENCE.md
// words no Scene loading line, no thumbnail name and no Timer end status, so the loading line reuses the "Setting
// the scene" stage name, a thumbnail is named "Photo {n}", the photo tray's "Remove photo {n}" without its verb, and
// the end status after a failed upload is "Upload failed", the name Voice and Tone gives that moment. The speaker
// prefixes are worded only in Component Patterns (Wizard portrait), and the Inventory and the Wizard notes take
// their component names as their accessible names.
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
  inputRequirement: '6 to 10 JPEG photos',
  iphoneTip: 'On iPhone, set Settings > Camera > Formats to Most Compatible so photos save as JPEG.',
  reminder: "Leave out faces, documents and other people's belongings.",
  pickerSentence: 'Choose 6 to 10 JPEG photos of one room.',
  choosePhotos: 'Choose photos',
  upload: 'Upload',
  readingPhotos: 'Reading your photos',
  removePhoto: 'Remove photo {n}',
  photosChosen: '{n} photos chosen',
  notAJpeg: 'Not a JPEG',
  photosRefused: 'Keyframe needs 6 to 10 JPEG photos.',
  choosePhotosAgain: 'Choose photos again',
  photosUnreadable: "Keyframe couldn't read these photos. Choose them again.",
  uploadFailed: "Your photos didn't reach Keyframe.",
  uploadFailedBody: 'Nothing was built. Check the connection and try again.',
  retentionHeading: 'Where your photos go.',
  playHistory: 'Your play history',
  privacyLine: 'the player profile stays on your machine.',
  sceneLoading: 'Setting the scene',
  photoThumbnail: 'Photo {n}',
  photosToPlay: 'Photos to play',
  playableIn: 'Playable in',
  uploadFailedStatus: 'Upload failed',
  inventory: 'Inventory',
  nothingInHand: 'Nothing in hand yet.',
  wizardNotes: 'Wizard notes',
  puzzleHeading: 'Puzzle {n}',
  current: 'Current',
  evidenceCards: '{k} evidence cards',
  evidenceCard: '1 evidence card',
  notThis: 'Not this · {n}',
  open: 'Open',
  speakerArchitect: 'The Architect:',
  speakerRiddler: 'The Riddler:',
  speakerGuide: 'The Guide:',
  speakerTrickster: 'The Trickster:',
} as const

/** `template` with each `{name}` replaced by `values[name]`. */
export function fill(template: string, values: Record<string, string | number>): string {
  return template.replace(/\{(\w+)\}/g, (match, name: string) => (name in values ? String(values[name]) : match))
}
