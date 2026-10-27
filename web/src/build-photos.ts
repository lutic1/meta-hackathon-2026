// The photos of the Build this page just uploaded, handed from the Capture screen to `#/build/<job_id>`: each
// photo's thumbnail (the local object URL the Photo tray showed) and its downscale, the 1280 px JPEG whose pixel
// space the Mask preview's polygons are in. They live in memory only, like the chosen files they come from, so a
// reloaded page holds none; nothing is ever fetched for them.

export interface HeldPhotos {
  jobId: string
  thumbnails: readonly string[]
  downscales: readonly string[]
}

let held: HeldPhotos | null = null

/** Takes over the object URLs of `photos`, releasing any set held for an earlier Build. */
export function holdPhotos(photos: HeldPhotos): void {
  releasePhotos()
  held = photos
}

/** The photos held for `jobId`; null when this page did not upload that Build. */
export function heldPhotos(jobId: string): HeldPhotos | null {
  return held?.jobId === jobId ? held : null
}

/** Revokes the held object URLs: the Build has opened its Room, whose photos the server serves. */
export function releasePhotos(): void {
  for (const url of [...(held?.thumbnails ?? []), ...(held?.downscales ?? [])]) URL.revokeObjectURL(url)
  held = null
}
