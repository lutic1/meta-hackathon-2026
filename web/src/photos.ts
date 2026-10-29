// The chosen photos before Upload (FR-1, AD-7): the JPEG check by bytes, the set rule and the Canvas downscale.
// The numbers are ingest's own (src/pipeline/ingest.py), so a set the client accepts is one ingest accepts.

export const MIN_PHOTOS = 6
export const MAX_PHOTOS = 10
/** The downscale's long edge in px, which ingest requires exactly (else 422 `bad_downscale`). */
export const LONG_EDGE = 1280
export const JPEG_QUALITY = 0.85
/** The largest original ingest stores (else 413 `upload_too_large`); the player line calls it 20 MB. */
export const MAX_ORIGINAL_BYTES = 20 * 1024 * 1024

/** Every JPEG file starts with the SOI marker and the first marker's lead byte. */
const JPEG_START = [0xff, 0xd8, 0xff]

/** Whether `file` is a JPEG by its bytes, whatever its name or type says (a HEIC renamed `.jpg` is not). */
export async function isJpeg(file: Blob): Promise<boolean> {
  const head = new Uint8Array(await file.slice(0, JPEG_START.length).arrayBuffer())
  return JPEG_START.every((byte, index) => head[index] === byte)
}

/** The FR-1 rule, all or nothing: 6 to 10 photos, every one a JPEG. */
export function isValidSet(photos: readonly { jpeg: boolean }[]): boolean {
  return photos.length >= MIN_PHOTOS && photos.length <= MAX_PHOTOS && photos.every((photo) => photo.jpeg)
}

/**
 * The downscaled JPEG of `file`: drawn in a Canvas with its EXIF orientation applied, scaled so its long edge is
 * exactly 1280 px, encoded at quality 0.85. The Canvas writes no EXIF, so the result's orientation is 1.
 */
export async function downscale(file: Blob): Promise<Blob> {
  const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
  const { width, height } = bitmap
  const canvas = document.createElement('canvas')
  canvas.width = width >= height ? LONG_EDGE : Math.max(1, Math.round((width * LONG_EDGE) / height))
  canvas.height = width >= height ? Math.max(1, Math.round((height * LONG_EDGE) / width)) : LONG_EDGE
  const context = canvas.getContext('2d')
  if (context === null) throw new Error('no 2d canvas')
  context.imageSmoothingQuality = 'high'
  context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  bitmap.close()
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => (blob === null ? reject(new Error('no JPEG from the canvas')) : resolve(blob)), 'image/jpeg', JPEG_QUALITY)
  })
}
