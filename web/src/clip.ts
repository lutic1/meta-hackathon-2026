/**
 * The clip of the Hosted landing: a scripted play-through of one Demo room, at real speed. Re-recording it means
 * swapping the six files under `web/public/clip/`, the room id, its length in `strings.ts` (`watchBackTag`), and
 * re-running the lines under `CLIP_CARD` on the new recording.
 */
export const CLIP = {
  roomId: 'room_01M61TZ74F0FP3X9HHTMXGTPB9',
  webm: '/clip/play.webm',
  mp4: '/clip/play.mp4',
  poster: '/clip/poster.jpg',
} as const

/**
 * Both videos come from one raw recording, `raw.mp4`: a first-time play-through of the Demo room in story mode (re-recorded
 * Oct 30, the play screen of the earlier clip no longer exists), a 1280 x 720 page captured at device pixel ratio 2
 * (Chromium's `--force-device-scale-factor=2` screencast, 2560 x 1440 frames, set to 30 fps), so neither is ever scaled
 * up. The recorder is `fix-C2-record.cjs` in the build's browser scratch folder: it enters through "Play the sample room"
 * and "Play this room" with the first-visit intro marked seen, draws the pointer (headless frames carry none) and paces
 * the play to be read (owner report Oct 29: "watch the demo is way to fast"): each of the five intro beats held for
 * 3.5 s or 55 ms a character of its line, whichever is longer; on riddle 1 the wall clock and the tray hovered 0.8 s
 * each, one turn right by the edge zone and back, 1.5 s each; the corner pillow pair picked up; each solve beat held
 * 3.5 s or 40 ms a character; one hint from the chest held 3.5 s on the note; the floor vent; the pillows used on the
 * sectional sofa; the double front door, "Step outside" and the escape sheet. The room was the Demo room as served
 * (`ops/patches/` applied, its written story). The Completion route's one unpainted frame (0.23 s) is held on the frame
 * before it. Nothing is sped up: the play runs from the Architect's first beat (10.3 s) to 5.5 s into the escape sheet
 * (118.3 s), 108.0 s.
 *
 * `CLIP`: the top bar and the bottom strip cropped off (the 2560 x 1212 box at y 96), scaled to 1280 px wide:
 *   VF="trim=start=10.3:end=118.3,setpts=PTS-STARTPTS,crop=2560:1212:0:96,fps=30,scale=1280:-2:flags=lanczos"
 *   ffmpeg -i raw.mp4 -vf "$VF" -an -c:v libvpx-vp9 -b:v 0 -crf 40 -row-mt 1 -pix_fmt yuv420p play.webm
 *   ffmpeg -i raw.mp4 -vf "$VF" -an -c:v libx264 -pix_fmt yuv420p -crf 28 -preset slow -movflags +faststart play.mp4
 *   ffmpeg -ss 51.8 -i play.mp4 -frames:v 1 -q:v 3 poster.jpg (the corner pillows glowing as they are picked up)
 *
 * `CLIP_CARD`, the Watch card's own loop: the Scene photo only, at its native size (the 798 x 1064 box at x 881, y 170
 * of the raw frame), riddle 1 from its first moment in play to the pillows picked up, before the solve beat opens: two
 * hovers, a turn out and back and one solve, no intro beat and no escape sheet, so it loops on the same view (17.0 s):
 *   SEL="trim=start=45.4:end=62.4,setpts=PTS-STARTPTS,fps=30,crop=798:1064:881:170"
 *   ffmpeg -i raw.mp4 -vf "$SEL" -an -c:v libvpx-vp9 -b:v 0 -crf 34 -row-mt 1 -pix_fmt yuv420p card.webm
 *   ffmpeg -i raw.mp4 -vf "$SEL" -an -c:v libx264 -pix_fmt yuv420p -crf 26 -preset slow -movflags +faststart card.mp4
 *   ffmpeg -i card.mp4 -frames:v 1 -q:v 3 card-poster.jpg
 */
export const CLIP_CARD = {
  webm: '/clip/card.webm',
  mp4: '/clip/card.mp4',
  poster: '/clip/card-poster.jpg',
} as const

/** A video in the two formats the browsers here play, with the frame shown before it plays. */
export interface VideoSources {
  readonly webm: string
  readonly mp4: string
  readonly poster: string
}

/**
 * The tutorial, the Watch back's first tab (owner decision Oct 29): the owner's own ten-second generated video (a framed
 * photo clicked into, a glowing outline round a pillow, a key and a card landing in the inventory, a padlocked door, the
 * door opening into light), slowed to half speed, 20 s. Plain half speed, each frame held: motion interpolation
 * (`minterpolate`, mci and aobmc) smeared the pan and warped the padlock on this footage. Its sound is dropped (it would
 * be distorted at half speed), and five captions are burned in from `tutorial.ass` (1280 x 720): EB Garamond Medium
 * 46 px (the woff2 under `web/public/fonts/eb-garamond/` saved as a TTF with fontTools) in parchment `&HBEDBE8&`,
 * centred at y 545 on a soft band (the box 150..1130 x 504..584 in `#0A0806` at 81 %, `\blur14`) under a 2 px gilt
 * hairline (`#B08A4E`, 240..1040 at y 503), just above the video's own inventory bar; the band and the hairline fade in
 * and out with the video, and each caption fades in and out over 250 ms (`\fad(250,250)`), never two at once:
 *   0.25-2.75 s   Snap a room. Your photos become the game.
 *   3.00-6.10 s   Read a riddle, then click the thing it means.
 *   6.35-10.00 s   Pick things up. They wait in your inventory.
 *   10.25-15.60 s   Use them where they belong to open the locks.
 *   15.85-19.80 s   Open the last lock and walk out.
 *   VF="setpts=2.0*PTS,fps=30,ass=tutorial.ass:fontsdir=fonts"
 *   ffmpeg -i tutorial-source.mp4 -vf "$VF" -an -c:v libx264 -pix_fmt yuv420p -crf 24 -preset slow -movflags +faststart tutorial.mp4
 *   ffmpeg -i tutorial-source.mp4 -vf "$VF" -an -c:v libvpx-vp9 -b:v 0 -crf 34 -row-mt 1 -pix_fmt yuv420p tutorial.webm
 *   ffmpeg -ss 1.5 -i tutorial.mp4 -frames:v 1 -q:v 3 tutorial-poster.jpg (the first caption)
 */
export const TUTORIAL: VideoSources = {
  webm: '/tutorial/tutorial.webm',
  mp4: '/tutorial/tutorial.mp4',
  poster: '/tutorial/tutorial-poster.jpg',
}

/**
 * The full demo video's files, once it is cut: unset for now, so the Watch back plays the clip. Set it (and
 * `FULL_DEMO_VIDEO_ASPECT`, its width over its height) when the files are under `web/public/`.
 */
const FULL_DEMO_VIDEO: VideoSources | null = null
const FULL_DEMO_VIDEO_ASPECT: number | null = null

/** The video the Watch back plays, larger and with controls: the full demo video, else the clip. */
export const DEMO_VIDEO: VideoSources = FULL_DEMO_VIDEO ?? CLIP

/** The Watch back's video width over its height: the panel sizes itself to it (the clip is 1280 x 606). */
export const DEMO_VIDEO_ASPECT: number = FULL_DEMO_VIDEO_ASPECT ?? 1280 / 606
