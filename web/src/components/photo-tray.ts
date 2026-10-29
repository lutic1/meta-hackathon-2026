import './photo-tray.css'
import { fill, strings } from '../strings.ts'

/** One chosen photo as the tray shows it: its local object URL, and whether it failed the JPEG check. */
export interface TrayPhoto {
  url: string
  rejected: boolean
}

/**
 * The Photo tray (UX-DR15): the count line, then a `{components.photo-tray-thumb}` per photo at 120 x 90 in upload
 * order, each with its 32 px "Remove photo {n}" control; a rejected file carries the 2 px `wrong` border and
 * "Not a JPEG" under it and stays removable. The thumbnail sits beside its named remove control, so its alt is empty.
 */
export function photoTray(photos: readonly TrayPhoto[], onRemove: (index: number) => void, disabled: boolean): HTMLElement {
  const tray = document.createElement('div')
  tray.className = 'photo-tray'
  const count = document.createElement('p')
  count.className = 'photo-tray-count label'
  count.textContent = photos.length === 1 ? strings.onePhotoChosen : fill(strings.photosChosen, { n: photos.length })
  const grid = document.createElement('ol')
  grid.className = 'photo-tray-grid'
  grid.append(
    ...photos.map(({ url, rejected }, index) => {
      const cell = document.createElement('li')
      cell.className = 'photo-tray-cell'
      const thumb = document.createElement('div')
      thumb.className = 'photo-tray-thumb'
      thumb.classList.toggle('rejected', rejected)
      const image = document.createElement('img')
      image.src = url
      image.alt = ''
      image.width = 120
      image.height = 90
      const remove = document.createElement('button')
      remove.type = 'button'
      remove.className = 'photo-tray-remove'
      remove.textContent = '×'
      remove.setAttribute('aria-label', fill(strings.removePhoto, { n: index + 1 }))
      remove.disabled = disabled
      remove.addEventListener('click', () => onRemove(index))
      thumb.append(image, remove)
      cell.append(thumb)
      if (rejected) {
        const why = document.createElement('p')
        why.className = 'photo-tray-why label'
        why.textContent = strings.notAJpeg
        cell.append(why)
      }
      return cell
    }),
  )
  tray.append(count, grid)
  return tray
}

/**
 * The Photo tray during a Build (UX-DR15): compact, the count line kept over `{components.photo-tray-thumb}` at
 * 96 x 72 in upload order, same radius and gaps, with no remove control, since the set can no longer change.
 */
export function compactPhotoTray(urls: readonly string[]): HTMLElement {
  const tray = document.createElement('div')
  tray.className = 'photo-tray compact'
  const count = document.createElement('p')
  count.className = 'photo-tray-count label'
  count.textContent = urls.length === 1 ? strings.onePhotoChosen : fill(strings.photosChosen, { n: urls.length })
  const grid = document.createElement('ol')
  grid.className = 'photo-tray-grid'
  grid.append(
    ...urls.map((url) => {
      const cell = document.createElement('li')
      cell.className = 'photo-tray-cell'
      const thumb = document.createElement('div')
      thumb.className = 'photo-tray-thumb'
      const image = document.createElement('img')
      image.src = url
      image.alt = ''
      image.width = 96
      image.height = 72
      thumb.append(image)
      cell.append(thumb)
      return cell
    }),
  )
  tray.append(count, grid)
  return tray
}
