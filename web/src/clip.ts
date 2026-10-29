/**
 * The ten-second clip of the Hosted landing: a scripted play-through of one Demo room. Re-recording it means swapping
 * the six files under `web/public/clip/`, the room id, and re-running the lines under `CLIP_CARD` on the new recording.
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
 * ever scaled up. The play runs from just after "Begin" (8.05 s) to
 * the full Completion card (26.0 s), sped to exactly 10.0 s (F = 10 / 17.95).
 *
 * `CLIP`: the top bar and the bottom strips cropped off (the 2560 x 1208 box at y 96), scaled to 1280 px wide:
 *   VF="trim=start=8.05:end=26.0,setpts=(PTS-STARTPTS)*0.5571,crop=2560:1208:0:96,fps=30,scale=1280:-2:flags=lanczos"
 *   ffmpeg -i raw.mp4 -vf "$VF" -an -c:v libvpx-vp9 -b:v 0 -crf 34 -row-mt 1 -pix_fmt yuv420p play.webm
 *   ffmpeg -i raw.mp4 -vf "$VF" -an -c:v libx264 -pix_fmt yuv420p -crf 25 -movflags +faststart play.mp4
 *   ffmpeg -ss 2.6 -i play.mp4 -frames:v 1 -q:v 3 poster.jpg (the throw pillows pickup)
 *
 * `CLIP_CARD`, the Watch card's own loop: the Scene photo only, at its native size (the 630 x 840 box at x 581, y 171
 * of the raw frame), the three "Setting the scene" flashes cut and the end screen (from frame 501) dropped, so it loops
 * with nothing but the room in it, at the clip's speed:
 *   SEL="trim=start=8.05,setpts=PTS-STARTPTS,select='not(between(n\,88\,97)+between(n\,264\,272)+between(n\,400\,409))*lt(n\,501)',setpts=N*0.5571/30/TB,fps=30,crop=630:840:581:171"
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
 * The full demo video's files, once it is cut: unset for now, so the Watch back plays the ten-second clip. Set it (and
 * `FULL_DEMO_VIDEO_ASPECT`, its width over its height) when the files are under `web/public/`.
 */
const FULL_DEMO_VIDEO: VideoSources | null = null
const FULL_DEMO_VIDEO_ASPECT: number | null = null

/** The video the Watch back plays, larger and with controls: the full demo video, else the ten-second clip. */
export const DEMO_VIDEO: VideoSources = FULL_DEMO_VIDEO ?? CLIP

/** The Watch back's video width over its height: the panel sizes itself to it (the clip is 1280 x 604). */
export const DEMO_VIDEO_ASPECT: number = FULL_DEMO_VIDEO_ASPECT ?? 1280 / 604
