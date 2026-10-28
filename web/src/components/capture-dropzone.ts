import './capture-dropzone.css'
import { strings } from '../strings.ts'
import { secondaryButton } from './button.ts'

export interface CaptureDropzone {
  element: HTMLElement
  /** "Choose photos", which takes the initial focus; disabled, it disables the whole dropzone. */
  button: HTMLButtonElement
  /** "No photos handy? Play the sample room", under "Choose photos" when the dropzone was given `onSample`; else null. */
  sample: HTMLButtonElement | null
  /** Opens the picker for "Choose photos again": the files it returns replace the set instead of joining it. */
  chooseAgain: () => void
}

/**
 * `{components.capture-dropzone}` (UX-DR14): a tray holding the picker sentence and "Choose photos", taking files by
 * drag-and-drop or the picker and handing them to `onFiles` in their order, `replace` set only for "Choose photos
 * again". It accepts nothing while "Choose photos" is disabled, by its own flag or a disabled fieldset around it.
 * Given `onSample` (Hosted mode with a Demo room listed), a second button under "Choose photos", "No photos handy?
 * Play the sample room", calls it, so a judge with no photos at hand still has a room to play.
 */
export function captureDropzone(onFiles: (files: File[], replace: boolean) => void, onSample?: () => void): CaptureDropzone {
  const element = document.createElement('div')
  element.className = 'capture-dropzone'
  const sentence = document.createElement('p')
  sentence.className = 'capture-dropzone-sentence body-md'
  sentence.textContent = strings.pickerSentence
  const input = document.createElement('input')
  input.type = 'file'
  input.multiple = true
  input.hidden = true
  let replace = false
  const open = (replacing: boolean): void => {
    replace = replacing
    input.click()
  }
  const button = secondaryButton({ label: strings.choosePhotos, onActivate: () => open(false) })
  const sample = onSample === undefined ? null : secondaryButton({ label: strings.playSampleRoomInstead, onActivate: onSample })
  const disabled = (): boolean => button.matches(':disabled')

  input.addEventListener('change', () => {
    const files = [...(input.files ?? [])]
    input.value = ''
    if (files.length > 0 && !disabled()) onFiles(files, replace)
  })
  element.addEventListener('dragover', (event) => {
    event.preventDefault()
    if (event.dataTransfer !== null) event.dataTransfer.dropEffect = disabled() ? 'none' : 'copy'
    element.classList.toggle('drag-over', !disabled())
  })
  element.addEventListener('dragleave', (event) => {
    if (!element.contains(event.relatedTarget as Node | null)) element.classList.remove('drag-over')
  })
  element.addEventListener('drop', (event) => {
    event.preventDefault()
    element.classList.remove('drag-over')
    const files = [...(event.dataTransfer?.files ?? [])]
    if (files.length > 0 && !disabled()) onFiles(files, false)
  })
  element.append(sentence, button, ...(sample === null ? [] : [sample]), input)
  return { element, button, sample, chooseAgain: () => open(true) }
}
