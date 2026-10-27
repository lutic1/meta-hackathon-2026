import './profile-file.css'
import type { Profile } from '../../types'
import { strings } from '../strings.ts'
import { secondaryButton } from './button.ts'

export interface OpenProfileControl {
  /** "Open profile file" over its plain line, for the Retention summary below the Privacy line. */
  element: HTMLElement
  /** Opens the browser file picker again, as the refusal banner's "Open profile file" does. */
  choose: () => void
}

/** The cut-2 plain line, "Your player profile is a file on this computer; Keyframe reads it only when you open it." */
function profileFileLine(): HTMLParagraphElement {
  const line = document.createElement('p')
  line.className = 'profile-file-line body-sm'
  line.textContent = strings.profileFileLine
  return line
}

/**
 * Cut 2 (UX-DR20, UX-DR84): "Open profile file" (`{components.button-secondary}` on `chrome-raised`) and its plain
 * line. The button opens the browser file picker for one JSON file, handed to `onFile` as chosen.
 */
export function openProfileControl(onFile: (file: File) => void): OpenProfileControl {
  const element = document.createElement('div')
  element.className = 'profile-file'
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json,application/json'
  input.hidden = true
  input.addEventListener('change', () => {
    const file = input.files?.[0]
    input.value = ''
    if (file !== undefined) onFile(file)
  })
  const choose = (): void => input.click()
  element.append(secondaryButton({ label: strings.openProfileFile, onActivate: choose }), profileFileLine(), input)
  return { element, choose }
}

export interface SaveProfileControl {
  /** "Save profile file", for the Completion sheet's actions. */
  button: HTMLButtonElement
  /** Its plain line, below the actions. */
  line: HTMLParagraphElement
}

/**
 * Cut 2 (UX-DR44, UX-DR84): "Save profile file" (`{components.button-secondary}` on parchment) and its plain line. The
 * button downloads the profile `name` as `<name>.json`, as `profile` gives it when activated.
 */
export function saveProfileControl(name: string, profile: () => Promise<Profile>): SaveProfileControl {
  const button = secondaryButton({
    label: strings.saveProfileFile,
    onParchment: true,
    onActivate: () => {
      void profile().then((current) => {
        const url = URL.createObjectURL(new Blob([JSON.stringify(current, null, 2)], { type: 'application/json' }))
        const link = document.createElement('a')
        link.href = url
        link.download = `${name}.json`
        link.click()
        setTimeout(() => URL.revokeObjectURL(url))
      })
    },
  })
  const line = profileFileLine()
  line.classList.add('on-parchment')
  return { button, line }
}
