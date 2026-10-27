// The Player profile (FR-20, FR-22, AD-8): the browser is its system of record and this module its only writer. Every
// other module reads Room results and the Derived block through these exports; nothing here makes a request, and a
// Session start carries only the Derived block. No DOM, so Node runs it as it ships.
import type { Derived, Meta, RoomResult, SessionStart } from '../../types'
import { derive, freshDerived } from './derive.ts'

/** Where one profile's Room results live, keyed by `room_id`; the backend can change behind it. */
export interface ProfileStorage {
  getResults(): Promise<RoomResult[]>
  putResult(result: RoomResult): Promise<void>
}

/** The in-memory backend: the Room results last as long as the page. */
export function memoryStorage(): ProfileStorage {
  const results = new Map<string, RoomResult>()
  return {
    getResults: async () => [...results.values()],
    putResult: async (result) => {
      results.set(result.room_id, result)
    },
  }
}

type Listener = (results: readonly RoomResult[]) => void

interface Held {
  results: Map<string, RoomResult>
  derived: Derived
}

interface Opened {
  storage: ProfileStorage
  held: Promise<Held>
  listeners: Set<Listener>
}

const profiles = new Map<string, Opened>()

/** The profile named `name` (the `?profile=` value), opened on first use. */
function open(name: string): Opened {
  let profile = profiles.get(name)
  if (profile === undefined) {
    const storage = memoryStorage()
    const held = storage.getResults().then((results) => ({
      results: new Map(results.map((result) => [result.room_id, result])),
      derived: derive(results),
    }))
    profile = { storage, held, listeners: new Set() }
    profiles.set(name, profile)
  }
  return profile
}

/** Every Room result in the profile, one per Room. */
export async function getResults(name: string): Promise<RoomResult[]> {
  return [...(await open(name).held).results.values()]
}

/** The profile's current Derived block. */
export async function getDerived(name: string): Promise<Derived> {
  return (await open(name).held).derived
}

/**
 * Records `result` under its `room_id`, replacing the Room's earlier result unless that one counts and this one is
 * demo-flagged, and recomputes the Derived block in the same step. Putting the same result again changes nothing.
 */
export async function putResult(name: string, result: RoomResult): Promise<void> {
  const profile = open(name)
  const held = await profile.held
  if (result.demo && held.results.get(result.room_id)?.demo === false) return
  await profile.storage.putResult(result)
  held.results.set(result.room_id, result)
  held.derived = derive([...held.results.values()])
  const results = [...held.results.values()]
  for (const listener of profile.listeners) listener(results)
}

/** Calls `listener` with every Room result each time one is recorded in the profile. Returns the unsubscribe. */
export function watchResults(name: string, listener: Listener): () => void {
  const { listeners } = open(name)
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/**
 * The `POST /sessions` body: the Room and the profile's Derived block, nothing else from the profile; in Hosted mode
 * always `Derived.fresh()`, whatever the profile holds.
 */
export async function sessionStart(roomId: string, name: string, mode: Meta['mode']): Promise<SessionStart> {
  return { room_id: roomId, derived: mode === 'hosted' ? freshDerived() : await getDerived(name) }
}
