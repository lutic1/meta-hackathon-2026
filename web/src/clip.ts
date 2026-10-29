/**
 * The ten-second clip on the Hosted landing: a scripted play-through of one Demo room, shown only while that room is
 * the first one listed. Re-recording it means swapping the three files under `web/public/clip/` and the room id.
 */
export const CLIP = {
  roomId: 'room_01M61TZ74F0FP3X9HHTMXGTPB9',
  webm: '/clip/play.webm',
  mp4: '/clip/play.mp4',
  poster: '/clip/poster.jpg',
} as const
