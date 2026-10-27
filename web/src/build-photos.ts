// The photos of the Build this page just uploaded, handed from the Capture screen to `#/build/<job_id>`: each
// photo's thumbnail (the local object URL the Photo tray showed), its downscale, the 1280 px JPEG whose pixel
// space the Mask preview's polygons are in, and the pair `POST /builds` took, so an end state's "Try again" posts
// the same photos and "Add photos" appends to them. They live in memory only, like the chosen files they come from,
// so a reloaded page holds none; nothing is ever fetched for them.
import type { UploadPhoto } from './api/index.ts'

export interface HeldPhotos {
  jobId: string
  thumbnails: readonly string[]
  downscales: readonly string[]
  uploads: readonly UploadPhoto[]
}

let held: HeldPhotos | null = null
/** The files "Add photos" hands to the next Capture screen, the set already uploaded first. */
let carried: File[] = []

/** Takes over the object URLs of `photos`, releasing any set held for an earlier Build. */
export function holdPhotos(photos: HeldPhotos): void {
  releasePhotos()
  held = photos
}

/** The photos held for `jobId`; null when this page did not upload that Build. */
export function heldPhotos(jobId: string): HeldPhotos | null {
  return held?.jobId === jobId ? held : null
}

/** "Try again" posted the photos held for `from` as the new Build `to`: they now belong to it, URLs and all. */
export function passPhotos(from: string, to: string): void {
  if (held?.jobId === from) held = { ...held, jobId: to }
}

/** Revokes the held object URLs: the Build has opened its Room, whose photos the server serves, or was left. */
export function releasePhotos(): void {
  for (const url of [...(held?.thumbnails ?? []), ...(held?.downscales ?? [])]) URL.revokeObjectURL(url)
  held = null
}

/** Hands `files` to the next Capture screen, which starts with them in its Photo tray. */
export function carryPhotos(files: readonly File[]): void {
  carried = [...files]
}

/** The files carried to this Capture screen, once; empty when none were. */
export function takeCarriedPhotos(): File[] {
  const files = carried
  carried = []
  return files
}
