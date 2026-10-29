/**
 * The clip of the Hosted landing: a scripted play-through of one Demo room, at real speed. Re-recording it means
 * swapping the six files under `web/public/clip/`, the room id, the lengths in `strings.ts` (`watchCardTag`,
 * `watchBackTag`), and re-running the lines under `CLIP_CARD` on the new recording.
 */
export const CLIP = {
  roomId: 'room_01M61TZ74F0FP3X9HHTMXGTPB9',
  webm: '/clip/play.webm',
  mp4: '/clip/play.mp4',
  poster: '/clip/poster.jpg',
} as const

/**
 * Both videos come from one raw recording, `raw.mp4`: the play-through of a 1280 x 720 page captured at device pixel
 * ratio 2 (Chromium's `--force-device-scale-factor=2` screencast, 2560 x 1440 frames, set to 30 fps), so neither is
 * ever scaled up. It is paced to be read (owner report Oct 29: "watch the demo is way to fast"): 1.5 s after "Begin",
 * three objects hovered 0.8 s each, the wrong click on the entryway rug held 2.5 s, the throw pillows picked up at the
 * corner bend and held 3 s, one hint on Puzzle 2 held 3 s on its Rung, the floor vent held 2.5 s, the pillows used on
 * the sectional sofa held 3 s, then the double front door. Nothing is sped up: the play runs from just after "Begin"
 * (7.37 s) to 4.5 s into the full Completion card (44.37 s), 37.0 s.
 *
 * `CLIP`: the top bar and the bottom strips cropped off (the 2560 x 1208 box at y 96), scaled to 1280 px wide:
 *   VF="trim=start=7.37:end=44.37,setpts=PTS-STARTPTS,crop=2560:1208:0:96,fps=30,scale=1280:-2:flags=lanczos"
 *   ffmpeg -i raw.mp4 -vf "$VF" -an -c:v libvpx-vp9 -b:v 0 -crf 36 -row-mt 1 -pix_fmt yuv420p play.webm
 *   ffmpeg -i raw.mp4 -vf "$VF" -an -c:v libx264 -pix_fmt yuv420p -crf 26 -movflags +faststart play.mp4
 *   ffmpeg -ss 11.5 -i play.mp4 -frames:v 1 -q:v 3 poster.jpg (the throw pillows pickup)
 *
 * `CLIP_CARD`, the Watch card's own loop: the Scene photo only, at its native size (the 630 x 840 box at x 581, y 170
 * of the raw frame), the three "Setting the scene" flashes cut and the Completion card (from frame 974) dropped, so it
 * loops with nothing but the room in it, at real speed (31.8 s):
 *   SEL="trim=start=7.37,setpts=PTS-STARTPTS,select='not(between(n\,300\,304)+between(n\,701\,705)+between(n\,896\,904))*lt(n\,974)',setpts=N/30/TB,fps=30,crop=630:840:581:170"
 *   ffmpeg -i raw.mp4 -vf "$SEL" -an -c:v libvpx-vp9 -b:v 0 -crf 34 -row-mt 1 -pix_fmt yuv420p card.webm
 *   ffmpeg -i raw.mp4 -vf "$SEL" -an -c:v libx264 -pix_fmt yuv420p -crf 23 -movflags +faststart card.mp4
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
 * The full demo video's files, once it is cut: unset for now, so the Watch back plays the clip. Set it (and
 * `FULL_DEMO_VIDEO_ASPECT`, its width over its height) when the files are under `web/public/`.
 */
const FULL_DEMO_VIDEO: VideoSources | null = null
const FULL_DEMO_VIDEO_ASPECT: number | null = null

/** The video the Watch back plays, larger and with controls: the full demo video, else the clip. */
export const DEMO_VIDEO: VideoSources = FULL_DEMO_VIDEO ?? CLIP

/** The Watch back's video width over its height: the panel sizes itself to it (the clip is 1280 x 604). */
export const DEMO_VIDEO_ASPECT: number = FULL_DEMO_VIDEO_ASPECT ?? 1280 / 604
