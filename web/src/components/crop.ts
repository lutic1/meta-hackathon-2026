import type { PlayInteractable } from '../../types'
import { photoUrl } from '../api/index.ts'
import { bounds, cropAround, largest } from '../scene/geometry.ts'

const photos = new Map<string, Promise<HTMLImageElement>>()

/** Photo `index` of a stored Room as an image, fetched once per page; a failed load asks again next time. */
function photo(roomId: string, index: number): Promise<HTMLImageElement> {
  const src = photoUrl(roomId, index)
  let loaded = photos.get(src)
  if (loaded === undefined) {
    loaded = new Promise((resolve, reject) => {
      const image = new Image()
      image.onload = () => resolve(image)
      image.onerror = () => {
        photos.delete(src)
        reject(new Error(`${src} did not load`))
      }
      image.src = src
    })
    photos.set(src, loaded)
  }
  return loaded
}

/**
 * A `width` x `height` px crop of `interactable` (square unless a height is given) cut from its photo around its
 * largest polygon's bounds (AD-11; never `box`), drawn once the photo has loaded. One instance, so instances far apart
 * never shrink the object to a slice of the room. Decorative: the label beside it names the object.
 */
export function crop(roomId: string, interactable: PlayInteractable, width: number, height = width): HTMLCanvasElement {
  const canvas = document.createElement('canvas')
  canvas.className = 'crop'
  canvas.setAttribute('aria-hidden', 'true')
  canvas.width = Math.round(width * window.devicePixelRatio)
  canvas.height = Math.round(height * window.devicePixelRatio)
  canvas.style.width = `${width}px`
  canvas.style.height = `${height}px`
  const polygon = largest(interactable.polygons ?? []) ?? []
  if (polygon.length === 0) return canvas
  photo(roomId, interactable.photo).then(
    (image) => {
      const region = cropAround(bounds([polygon]), { width: image.naturalWidth, height: image.naturalHeight }, width / height)
      canvas
        .getContext('2d')
        ?.drawImage(image, region.x, region.y, region.width, region.height, 0, 0, canvas.width, canvas.height)
    },
    () => undefined, // the empty crop stays
  )
  return canvas
}
