import type { BuildView, Meta } from '../types'
import { getBuildView, RequestFailed } from './api/index.ts'
import { buildViewHeader } from './components/build-view-header.ts'
import { secondaryButton } from './components/button.ts'
import { inPlayBlock } from './components/in-play-block.ts'
import { maskOverlays } from './components/mask-overlays.ts'
import { modelTable } from './components/model-table.ts'
import { puzzleGraph } from './components/puzzle-graph.ts'
import { captureHref } from './router.ts'
import { strings } from './strings.ts'

/** What `GET /builds/<job_id>/view` answered: the `BuildView`, a Build not yet `done`, or no usable answer. */
export type BuildViewState = { name: 'ready'; view: BuildView } | { name: 'not-ready'; jobId: string } | { name: 'failed' }

/**
 * Loads the Build view once. A not-done Build is the 409 `build_not_ready` answer, keyed on the job `status` its
 * envelope carries (AD-3, AD-13); any other refusal, and no answer at all, is a failed load.
 */
export async function loadBuildView(jobId: string): Promise<BuildViewState> {
  try {
    return { name: 'ready', view: await getBuildView(jobId) }
  } catch (error) {
    const notReady = error instanceof RequestFailed && error.status === 409 && error.code === 'build_not_ready'
    return notReady && error.jobStatus !== null ? { name: 'not-ready', jobId } : { name: 'failed' }
  }
}

export interface BuildViewOptions {
  meta: Meta
  profile: string
  /** "Back": returns to where the view was opened. */
  onBack: () => void
  /** "Try again": loads the view afresh. */
  onRetry: () => void
}

export interface BuildViewSurface {
  children: HTMLElement[]
  /** Moves the initial focus into the surface once it is in the page. */
  focus: () => void
}

/**
 * The Build view body (UX-DR67): the header row, then a left two-thirds column (the puzzle graph over the mask
 * overlays; the JSON pane joins in 2.31) and a right third holding the Model table, then the In play block. The right
 * column comes first in the page, so Tab runs the title, "Back", the right column, then the graph nodes and the mask
 * label chips (UX-DR71); the stylesheet places it on the right. Initial focus goes to the title. Not ready: the header,
 * then "This room is still being built." linking to the Build's Capture screen, with no panels. Failed: the plain
 * failed line with "Try again".
 */
export function buildViewSurface(state: BuildViewState, { meta, profile, onBack, onRetry }: BuildViewOptions): BuildViewSurface {
  if (state.name === 'failed') {
    const failed = document.createElement('div')
    failed.className = 'build-view-state'
    failed.setAttribute('role', 'alert')
    const line = document.createElement('p')
    line.className = 'body-md'
    line.textContent = strings.buildLoadFailed
    const retry = secondaryButton({ label: strings.tryAgain, onActivate: onRetry })
    failed.append(line, retry)
    return { children: [failed], focus: () => retry.focus() }
  }
  if (state.name === 'not-ready') {
    const header = buildViewHeader(null, onBack)
    const line = document.createElement('p')
    line.className = 'build-view-state body-md'
    const link = document.createElement('a')
    link.className = 'build-view-link'
    link.href = captureHref(state.jobId, profile)
    link.textContent = strings.buildNotReady
    line.append(link)
    return { children: [header.element, line], focus: () => link.focus() }
  }
  const header = buildViewHeader(state.view, onBack)
  const left = document.createElement('section')
  left.className = 'build-view-left'
  left.append(puzzleGraph(state.view), maskOverlays(state.view))
  const right = document.createElement('aside')
  right.className = 'build-view-right'
  right.append(modelTable(state.view), inPlayBlock(meta))
  const columns = document.createElement('div')
  columns.className = 'build-view-columns'
  columns.append(right, left)
  return { children: [header.element, columns], focus: () => header.title?.focus() }
}
