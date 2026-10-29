import './verdict-table.css'
import type { BuildView, DryRunVerdict, RuleVerdict } from '../../types'
import { strings } from '../strings.ts'

type Word = DryRunVerdict['verdict']

/** The verdict every Dry run row carries under cut 4 (`DRY_RUN=off`). */
const DRY_RUN_OFF: Word = 'skipped'

/** The Decoy check: never a build verdict, since a build holds no Decoy; the Validator runs it on the Trickster's in play. */
const DECOY_RULE = 9

/** The Validator's fixed message by rule number, shown on a fail row only: the base checks, rules 1 to 8. */
const FIXED_MESSAGES: Record<number, string> = {
  1: strings.rule1Failed,
  2: strings.rule2Failed,
  3: strings.rule3Failed,
  4: strings.rule4Failed,
  5: strings.rule5Failed,
  6: strings.rule6Failed,
  7: strings.rule7Failed,
  8: strings.rule8Failed,
}

function text<K extends 'td' | 'th' | 'div'>(tag: K, content: string, className: string): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag)
  element.className = className
  element.textContent = content
  return element
}

/** The verdict cell: the word as served ("pass", "fail" or "skipped") after its 8 px marker. */
function verdictCell(verdict: Word): HTMLTableCellElement {
  const cell = document.createElement('td')
  cell.className = 'verdict-table-word'
  cell.append(text('div', verdict, `verdict-word verdict-word-${verdict} label`))
  return cell
}

/** A real `<table>` under its caption, with `label` header cells over a hairline rule; a Tab stop. */
function panel(caption: string, headings: readonly string[], lines: HTMLTableRowElement[]): HTMLElement {
  const table = document.createElement('table')
  table.className = 'verdict-table'
  table.tabIndex = 0
  const title = document.createElement('caption')
  title.className = 'verdict-table-caption body-sm'
  title.textContent = caption
  const head = document.createElement('thead')
  const row = document.createElement('tr')
  for (const heading of headings) {
    const th = text('th', heading, 'label')
    th.scope = 'col'
    row.append(th)
  }
  head.append(row)
  const body = document.createElement('tbody')
  body.append(...lines)
  table.append(title, head, body)
  const element = document.createElement('div')
  element.className = 'verdict-table-panel'
  element.append(table)
  return element
}

/** One rule: its number in `mono-sm`, its check-phrased name (and, on a fail row only, its fixed message) and verdict. */
function ruleRow({ rule, name, passed }: RuleVerdict): HTMLTableRowElement {
  const row = document.createElement('tr')
  const number = text('th', String(rule), 'mono-sm verdict-table-number')
  number.scope = 'row'
  const check = text('td', name, 'body-sm')
  const message = FIXED_MESSAGES[rule]
  if (!passed && message !== undefined) check.append(text('div', message, 'verdict-table-message body-sm'))
  row.append(number, check, verdictCell(passed ? 'pass' : 'fail'))
  return row
}

/** Rule 9 apart from the build's verdicts: its number and check-phrased name, "not applicable" after the ring marker. */
function decoyRow(): HTMLTableRowElement {
  const row = document.createElement('tr')
  const number = text('th', String(DECOY_RULE), 'mono-sm verdict-table-number')
  number.scope = 'row'
  const cell = document.createElement('td')
  cell.className = 'verdict-table-word'
  cell.append(text('div', strings.notApplicable, 'verdict-word verdict-word-skipped label'))
  row.append(number, text('td', strings.rule9Name, 'body-sm'), cell)
  return row
}

/**
 * `{components.verdict-table}` (UX-DR51): the Validator's verdict on each base check (rules 1 to 8) from
 * `BuildView.validator`, under its plain caption: rule number, check-phrased name and the verdict word; the rule's fixed
 * message only on a fail row. Rule 9, the Decoy check, follows as "not applicable": a build holds no Decoy.
 */
export function verdictTable(view: BuildView): HTMLElement {
  const rows = [...view.validator.map(ruleRow), decoyRow()]
  return panel(strings.verdictCaption, [strings.verdictRule, strings.verdictCheck, strings.verdictVerdict], rows)
}

/**
 * The Dry run rows (UX-DR52), drawn as `{components.verdict-table}`: one row per Puzzle in Room order from
 * `BuildView.puzzles` and `dry_run` (order number, Lock type, verdict), under the caption that says the test run never
 * saw the answers. When every row reads "skipped" (cut 4, or a Build that recorded no Dry run verdict, which the graph
 * also reads as skipped) the cut 4 caption replaces it, since the usual one would no longer be true.
 */
export function dryRunRows(view: BuildView): HTMLElement {
  const verdicts = new Map(view.dry_run.map(({ puzzle_id, verdict }) => [puzzle_id, verdict]))
  const words = view.puzzles.map((puzzle) => verdicts.get(puzzle.id) ?? DRY_RUN_OFF)
  const rows = view.puzzles.map((puzzle, index) => {
    const row = document.createElement('tr')
    const number = text('th', String(index + 1), 'mono-sm verdict-table-number')
    number.scope = 'row'
    row.append(number, text('td', puzzle.lock_type, 'mono-sm'), verdictCell(words[index]))
    return row
  })
  const off = words.length > 0 && words.every((word) => word === DRY_RUN_OFF)
  const caption = off ? strings.dryRunOffCaption : strings.dryRunCaption
  return panel(caption, [strings.dryRunPuzzle, strings.dryRunLockType, strings.verdictVerdict], rows)
}
