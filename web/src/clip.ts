/**
 * The ten-second clip of the Hosted landing: a scripted play-through of one Demo room. Re-recording it means swapping
 * the three files under `web/public/clip/`, the room id, and re-running the three lines under `CLIP_CARD`.
 */
export const CLIP = {
  roomId: 'room_01M61TZ74F0FP3X9HHTMXGTPB9',
  webm: '/clip/play.webm',
  mp4: '/clip/play.mp4',
  poster: '/clip/poster.jpg',
} as const

/**
 * The Watch card's own loop, derived from `CLIP`: its Scene photo only (x 218-454, y 18-352 of the 960 x 454 frame),
 * the three "Setting the scene" flashes cut and the end screen (from 8.73 s) dropped, so it loops with nothing but the
 * room in it. Made from `play.mp4` with:
 *   SEL="select='not(between(n\,46\,48)+between(n\,144\,148)+between(n\,212\,214))*lt(n\,255)',setpts=N/30/TB,crop=236:334:218:18"
 *   ffmpeg -i play.mp4 -vf "$SEL" -an -c:v libvpx-vp9 -b:v 0 -crf 30 -row-mt 1 card.webm
 *   ffmpeg -i play.mp4 -vf "$SEL" -an -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart card.mp4
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

/** The Watch back's video width over its height: the panel sizes itself to it (the clip is 960 x 454). */
export const DEMO_VIDEO_ASPECT: number = FULL_DEMO_VIDEO_ASPECT ?? 960 / 454
