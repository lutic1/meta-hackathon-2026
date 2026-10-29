import './thumbnail-strip.css'
import type { PlayView } from '../../types'
import { photoUrl } from '../api/index.ts'
import { hotspotPath } from '../scene/geometry.ts'
import { fill, strings } from '../strings.ts'

export interface ThumbnailStrip {
  element: HTMLElement
  /** Marks photo `index` as the current one, the only thumbnail announced as current. */
  setCurrent: (index: number) => void
  /** Redraws each thumbnail's object count in place, from a refetched Effective room's `objectCounts`. */
  setCounts: (counts: readonly number[]) => void
}

/** How many Hotspots each photo of `view` holds (its Interactables with a drawable polygon), in upload order. */
export function objectCounts(view: Pick<PlayView, 'photos' | 'interactables'>): number[] {
  return view.photos.map(
    (_, index) => view.interactables.filter((ix) => ix.photo === index && hotspotPath(ix.polygons ?? []) !== '').length,
  )
}

function described(count: number): string {
  if (count === 0) return strings.photoNoObjects
  return count === 1 ? strings.photoObject : fill(strings.photoObjects, { k: count })
}

let made = 0

/**
 * The Thumbnail strip (UX-DR25): one 96 x 72 `{components.thumbnail}` per photo of the Room, in upload order (A-12),
 * scrolling inside its own row. Each is a native button named "Photo {n}", so Tab reaches it and Enter or a click
 * switches the Scene; the current one carries `aria-current` and the 2 px lamp border. Each carries the count of
 * objects its photo holds (`counts`, from `objectCounts`) on a parchment badge at its bottom-right corner, read out as
 * its description ("{k} objects"); a photo with none has no badge and is dimmed (playtest Oct 29).
 */
export function thumbnailStrip(roomId: string, counts: readonly number[], onSelect: (index: number) => void): ThumbnailStrip {
  const element = document.createElement('div')
  element.className = 'thumbnail-strip'
  const strip = made++
  const thumbnails = counts.map((_, index) => {
    const thumbnail = document.createElement('button')
    thumbnail.type = 'button'
    thumbnail.className = 'thumbnail'
    const image = document.createElement('img')
    image.src = photoUrl(roomId, index)
    image.alt = fill(strings.photoThumbnail, { n: index + 1 })
    image.width = 96
    image.height = 72
    const badge = document.createElement('span')
    badge.className = 'thumbnail-count caption'
    badge.setAttribute('aria-hidden', 'true') // the description says it in words
    const description = document.createElement('span')
    description.hidden = true // read only as the description, so the name stays "Photo {n}"
    description.id = `thumbnail-count-${strip}-${index}`
    thumbnail.setAttribute('aria-describedby', description.id)
    thumbnail.append(image, badge, description)
    thumbnail.addEventListener('click', () => onSelect(index))
    // Browsers leave a partly visible button where it is on focus; scroll it, ring and all, fully into the row.
    thumbnail.addEventListener('focus', () => thumbnail.scrollIntoView({ block: 'nearest', inline: 'nearest' }))
    return { thumbnail, badge, description }
  })
  element.append(...thumbnails.map(({ thumbnail }) => thumbnail))

  function setCurrent(index: number): void {
    thumbnails.forEach(({ thumbnail }, i) => {
      if (i === index) thumbnail.setAttribute('aria-current', 'true')
      else thumbnail.removeAttribute('aria-current')
    })
  }

  function setCounts(next: readonly number[]): void {
    thumbnails.forEach(({ thumbnail, badge, description }, i) => {
      const count = next[i] ?? 0
      badge.textContent = String(count)
      badge.hidden = count === 0
      description.textContent = described(count)
      thumbnail.classList.toggle('is-empty', count === 0)
    })
  }
  setCounts(counts)

  return { element, setCurrent, setCounts }
}
