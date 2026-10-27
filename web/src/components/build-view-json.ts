import './build-view-json.css'
import type { BuildView } from '../../types'
import { strings } from '../strings.ts'
import { toggleButton } from './button.ts'

const PANE_ID = 'build-view-json-pane'
const CAPTION_ID = 'build-view-json-caption'

/**
 * `{components.build-view-json}` (UX-DR55): "Show the build JSON", a secondary toggle with an expanded state,
 * collapsed by default. Open, it shows its plain caption, then the `GET /builds/<job_id>/view` response as served,
 * pretty-printed in `mono-sm` in a focusable region that scrolls past 360 px. It reads only the `BuildView` the page
 * already holds, which is solution-free by construction (AD-3).
 */
export function buildViewJson(view: BuildView): HTMLElement {
  const caption = document.createElement('p')
  caption.id = CAPTION_ID
  caption.className = 'build-view-json-caption body-sm'
  caption.textContent = strings.buildJsonCaption
  const data = document.createElement('pre')
  data.className = 'build-view-json-data mono-sm'
  data.tabIndex = 0
  data.setAttribute('role', 'region')
  data.setAttribute('aria-labelledby', CAPTION_ID)
  data.textContent = JSON.stringify(view, null, 2)
  const pane = document.createElement('div')
  pane.id = PANE_ID
  pane.className = 'build-view-json-pane'
  pane.hidden = true
  pane.append(caption, data)
  const toggle = toggleButton({
    label: strings.showBuildJson,
    state: 'expanded',
    controls: PANE_ID,
    onToggle: (open) => {
      pane.hidden = !open
    },
  })
  const panel = document.createElement('div')
  panel.className = 'build-view-json'
  panel.append(toggle, pane)
  return panel
}
