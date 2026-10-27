import type { PlayInteractable } from '../../types'
import { photoUrl } from '../api/index.ts'
import { bounds, squareAround } from '../scene/geometry.ts'

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
 * A `size` px square crop of `interactable` cut from its photo using its polygons' bounds (AD-11; never `box`), drawn
 * once the photo has loaded. Decorative: the label beside it names the object.
 */
export function crop(roomId: string, interactable: PlayInteractable, size: number): HTMLCanvasElement {
  const canvas = document.createElement('canvas')
  canvas.className = 'crop'
  canvas.setAttribute('aria-hidden', 'true')
  canvas.width = canvas.height = Math.round(size * window.devicePixelRatio)
  canvas.style.width = canvas.style.height = `${size}px`
  const polygons = interactable.polygons ?? []
  if (polygons.flat().length === 0) return canvas
  photo(roomId, interactable.photo).then(
    (image) => {
      const square = squareAround(bounds(polygons), { width: image.naturalWidth, height: image.naturalHeight })
      canvas
        .getContext('2d')
        ?.drawImage(image, square.x, square.y, square.width, square.height, 0, 0, canvas.width, canvas.height)
    },
    () => undefined, // the empty crop stays
  )
  return canvas
}
