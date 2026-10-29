import './model-table.css'
import type { BuildView, DryRunVerdict, Meta, ModelRow } from '../../types'
import { fill, strings } from '../strings.ts'
import { type Wizard, wizardPortrait } from '../wizards/portrait.ts'

/** The hosts a Meta-served call row names: the adapter's name, or the Meta Model API's default base URL host. */
const META_HOSTS = new Set(['meta', 'api.meta.ai'])

/**
 * The verdict every Dry run row carries under cut 4 (`DRY_RUN=off`), shown as served in the fixed Dry run row; a Build
 * that recorded no Dry run verdict reads the same, as the Dry run rows and the puzzle graph read it.
 */
const DRY_RUN_OFF: DryRunVerdict['verdict'] = 'skipped'

/** One body row: the first cell (a wizard's portrait and name, a fixed row's label, or empty) and four text cells. */
interface Line {
  role: HTMLElement | null
  model: string
  /** The model cell holds a model id, set in `mono-sm`; false for the Validator's "code, no model". */
  id: boolean
  host: string
  did: string
  billing: string
  /** The first row of a role, ruled off from the role above it. */
  first: boolean
}

/** "3 billed · 9 cached": each count spelled out, both when a role has both; empty when it made no call. */
export function cachedOrBilled(billed: number, cached: number): string {
  const counts = [billed > 0 ? fill(strings.billed, { n: billed }) : '', cached > 0 ? fill(strings.cached, { n: cached }) : '']
  return counts.filter((count) => count !== '').join(strings.modeSeparator)
}

function where(host: string): string {
  return META_HOSTS.has(host) ? strings.hostMeta : host
}

function roleCell(...content: (string | HTMLElement)[]): HTMLElement {
  const cell = document.createElement('span')
  cell.className = 'model-table-role label'
  cell.append(...content)
  return cell
}

/** One line per model row of a role, its label on the first; one empty line when the Build recorded no call for it. */
function roleLines(group: readonly ModelRow[], label: () => HTMLElement): Line[] {
  if (group.length === 0) return [{ role: label(), model: '', id: true, host: '', did: '', billing: '', first: true }]
  return group.map((row, index) => ({
    role: index === 0 ? label() : null,
    model: row.model,
    id: true,
    host: where(row.host),
    did: row.summary,
    billing: cachedOrBilled(row.billed, row.cached),
    first: index === 0,
  }))
}

function cell(tag: 'td' | 'th', text: string | HTMLElement | null, className = ''): HTMLTableCellElement {
  const element = document.createElement(tag)
  if (className !== '') element.className = className
  if (text !== null) element.append(text)
  return element
}

function bodyRow(line: Line): HTMLTableRowElement {
  const row = document.createElement('tr')
  row.classList.toggle('model-table-first', line.first)
  const role = line.role === null ? cell('td', null) : cell('th', line.role)
  if (line.role !== null) role.scope = 'row'
  row.append(
    role,
    cell('td', line.model, line.id ? 'mono-sm model-table-id' : 'body-sm'),
    cell('td', line.host, 'body-sm'),
    cell('td', line.did, 'body-sm'),
    cell('td', line.billing, 'body-sm model-table-billing'),
  )
  return row
}

/** The wizard's role line as a full-width row under its rows. */
function roleLineRow(text: string): HTMLTableRowElement {
  const row = document.createElement('tr')
  row.className = 'model-table-roleline'
  const line = cell('td', text, 'body-sm')
  line.colSpan = 5
  row.append(line)
  return row
}

/**
 * `{components.model-table}` (UX-DR53): a real `<table>` of the Build-time calls, from `BuildView.models` (AD-16).
 * The Architect's and the Riddler's rows (one per model, the 24 px portrait and name on the first, the role line as a
 * full-width row under them), then four fixed lines: the Validator (deterministic code, run where the API runs:
 * "this Mac" in Local mode, "this server" in Hosted mode, by `meta.mode`; "checked 8 rules" only when the Build
 * recorded its verdicts; no cached-or-billed count), the Dry run (its model and host, or "skipped" with neither under
 * cut 4), the Storyteller (its model and host; empty on a Room built before story mode) and Muse Image, a one-time generation whose count is only this Build's own image calls, so it reads none. No
 * Guide or Trickster row: the In play block carries both. Its caption sits under it, and the table is a Tab stop.
 */
export function modelTable(view: BuildView, meta: Meta): HTMLElement {
  const models = (role: ModelRow['role']): ModelRow[] => view.models.filter((row) => row.role === role)
  const wizard = (who: Wizard, name: string) => () => roleCell(wizardPortrait(who, 24), name)
  const dryRunOff = view.dry_run.every(({ verdict }) => verdict === DRY_RUN_OFF)
  const image = models('image')

  const table = document.createElement('table')
  table.className = 'model-table'
  table.tabIndex = 0
  const caption = document.createElement('caption')
  caption.className = 'model-table-caption body-sm'
  caption.textContent = strings.modelCaption
  const head = document.createElement('thead')
  const headings = document.createElement('tr')
  for (const heading of [strings.modelRole, strings.modelModel, strings.modelHost, strings.modelWhat, strings.modelBilling]) {
    const th = cell('th', heading, 'label')
    th.scope = 'col'
    headings.append(th)
  }
  head.append(headings)
  const body = document.createElement('tbody')
  body.append(
    ...roleLines(models('architect'), wizard('architect', strings.architect)).map(bodyRow),
    roleLineRow(strings.architectRole),
    ...roleLines(models('riddler'), wizard('riddler', strings.riddler)).map(bodyRow),
    roleLineRow(strings.riddlerRole),
    bodyRow({
      role: roleCell(strings.validator),
      model: strings.validatorModel,
      id: false,
      host: meta.mode === 'local' ? strings.hostThisMac : strings.hostThisServer,
      did: view.validator.length > 0 ? strings.validatorDid : '',
      billing: '',
      first: true,
    }),
    ...(dryRunOff
      ? [bodyRow({ role: roleCell(strings.dryRun), model: '', id: true, host: '', did: DRY_RUN_OFF, billing: '', first: true })]
      : roleLines(models('dryrun'), () => roleCell(strings.dryRun)).map(bodyRow)),
    ...roleLines(models('storyteller'), () => roleCell(strings.storyteller)).map(bodyRow),
    bodyRow({
      role: roleCell(strings.museImage),
      model: strings.museImageModel,
      id: true,
      host: strings.hostMeta,
      did: strings.museImageDid,
      billing: cachedOrBilled(
        image.reduce((sum, row) => sum + row.billed, 0),
        image.reduce((sum, row) => sum + row.cached, 0),
      ),
      first: true,
    }),
  )
  table.append(caption, head, body)
  const panel = document.createElement('div')
  panel.className = 'model-table-panel'
  panel.append(table)
  return panel
}
