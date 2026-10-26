// Type-level checks on the generated web/types, run by `tsc --noEmit` and `npm run build` (AD-2, AD-3).
// Never imported by the app: each switch below compiles only while its union stays discriminated
// on `type`, and `NoSolution` only while no client puzzle shape declares `solution`.
import type { Event, LockInput, PlayPuzzle, PlayView, PostedEvent } from '../types'

function unreachable(value: never): never {
  throw new Error(`unhandled ${JSON.stringify(value)}`)
}

export function eventTime(event: Event): number {
  switch (event.type) {
    case 'click':
    case 'lock_input':
    case 'hint_request':
    case 'idle_tick':
    case 'opening_line':
    case 'rung_change':
      return event.t_ms
    default:
      return unreachable(event)
  }
}

export function postedTarget(body: PostedEvent): string | null {
  switch (body.type) {
    case 'click':
      return body.interactable_id
    case 'lock_input':
      return lockInputTarget(body.input)
    case 'hint_request':
      return body.puzzle_id ?? null
    default:
      return unreachable(body)
  }
}

export function lockInputTarget(input: LockInput): string {
  switch (input.type) {
    case 'code':
    case 'order_start':
    case 'order_stop':
      return input.puzzle_id
    case 'use_on':
      return input.target
    default:
      return unreachable(input)
  }
}

type NoSolution<T> = 'solution' extends keyof T ? false : true
export const playViewHasNoSolution: NoSolution<PlayView> & NoSolution<PlayPuzzle> = true
