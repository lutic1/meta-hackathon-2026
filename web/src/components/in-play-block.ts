import './in-play-block.css'
import type { Meta } from '../../types'
import { strings } from '../strings.ts'
import { type Wizard, wizardPortrait } from '../wizards/portrait.ts'

const SOURCES: Record<Meta['trickster'], string> = {
  live: strings.sourceLive,
  scripted: strings.sourceScripted,
  cut1: strings.sourceCut1,
}

function text(className: string, ...content: (string | HTMLElement)[]): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = className
  element.append(...content)
  return element
}

function wizardRow(wizard: Wizard, name: string, role: string, model: HTMLParagraphElement): HTMLElement {
  const row = document.createElement('div')
  row.className = 'in-play-row'
  const lines = document.createElement('div')
  lines.append(text('in-play-name label', name), text('in-play-role body-sm', role), model)
  row.append(wizardPortrait(wizard, 32), lines)
  return row
}

/** The Guide's model line: Llama 3.2 3B on "Ollama on the Mac" while it words the hints, else the shown-as-written line. */
function guideModel(meta: Meta): HTMLParagraphElement {
  if (meta.guide_model === null) return text('in-play-model body-sm', strings.guideWritten)
  const id = document.createElement('span')
  id.className = 'mono-sm'
  id.textContent = strings.guideModel
  return text('in-play-model body-sm', id, strings.modeSeparator, strings.hostOllama)
}

/**
 * `{components.in-play-block}` (UX-DR54): a static `chrome` panel under the Model table, filled from `GET /meta`, not
 * from the Build's provenance. The Guide row (32 px portrait, name, role line, then its model and host, or in Hosted
 * mode, where `guide_model` is null, the line saying hints are shown as written) and the Trickster row (portrait,
 * name, role line, then its proposal source). It is a Tab stop after the Model table.
 */
export function inPlayBlock(meta: Meta): HTMLElement {
  const block = document.createElement('div')
  block.className = 'in-play-block'
  block.tabIndex = 0
  const guideRole = meta.guide === 'ollama' ? strings.guideRoleLocal : strings.guideRoleWritten
  block.append(
    wizardRow('guide', strings.guide, guideRole, guideModel(meta)),
    wizardRow('trickster', strings.trickster, strings.tricksterRole, text('in-play-model body-sm', SOURCES[meta.trickster])),
  )
  return block
}
