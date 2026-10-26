import './thumbnail-strip.css'
import { photoUrl } from '../api/index.ts'
import { fill, strings } from '../strings.ts'

export interface ThumbnailStrip {
  element: HTMLElement
  /** Marks photo `index` as the current one, the only thumbnail announced as current. */
  setCurrent: (index: number) => void
}

/**
 * The Thumbnail strip (UX-DR25): one 96 x 72 `{components.thumbnail}` per photo of the Room, in upload order (A-12),
 * scrolling inside its own row. Each is a native button named "Photo {n}", so Tab reaches it and Enter or a click
 * switches the Scene; the current one carries `aria-current` and the 2 px lamp border.
 */
export function thumbnailStrip(roomId: string, count: number, onSelect: (index: number) => void): ThumbnailStrip {
  const element = document.createElement('div')
  element.className = 'thumbnail-strip'
  const thumbnails = Array.from({ length: count }, (_, index) => {
    const thumbnail = document.createElement('button')
    thumbnail.type = 'button'
    thumbnail.className = 'thumbnail'
    const image = document.createElement('img')
    image.src = photoUrl(roomId, index)
    image.alt = fill(strings.photoThumbnail, { n: index + 1 })
    image.width = 96
    image.height = 72
    thumbnail.append(image)
    thumbnail.addEventListener('click', () => onSelect(index))
    // Browsers leave a partly visible button where it is on focus; scroll it, ring and all, fully into the row.
    thumbnail.addEventListener('focus', () => thumbnail.scrollIntoView({ block: 'nearest', inline: 'nearest' }))
    return thumbnail
  })
  element.append(...thumbnails)

  function setCurrent(index: number): void {
    thumbnails.forEach((thumbnail, i) => {
      if (i === index) thumbnail.setAttribute('aria-current', 'true')
      else thumbnail.removeAttribute('aria-current')
    })
  }

  return { element, setCurrent }
}
