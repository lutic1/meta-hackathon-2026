// The Player profile (FR-20, FR-22, AD-8): the browser is its system of record and this module its only writer. Every
// other module reads Room results and the Derived block through these exports; nothing here makes a request, and a
// Session start carries only the Derived block. Each profile lives in the IndexedDB database named after it; where
// there is no IndexedDB (Node runs the tests on this module as it ships), or it will not open (the browser blocks site
// data), it lives in memory.
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

/** The object store holding one profile's Room results, keyed by `room_id`. */
const RESULTS = 'results'

/** The IndexedDB backend: the Room results of profile `name` live in the database of that name, one per `room_id`. */
function indexedDbStorage(name: string): ProfileStorage {
  const database = new Promise<IDBDatabase>((resolve, reject) => {
    const request = indexedDB.open(name, 1)
    request.onupgradeneeded = () => request.result.createObjectStore(RESULTS, { keyPath: 'room_id' })
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
  /** Runs `step` in one transaction and answers its request's result once the transaction has committed. */
  async function run<T>(mode: IDBTransactionMode, step: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
    const transaction = (await database).transaction(RESULTS, mode)
    const request = step(transaction.objectStore(RESULTS))
    return new Promise((resolve, reject) => {
      transaction.oncomplete = () => resolve(request.result)
      transaction.onabort = () => reject(transaction.error)
    })
  }
  return {
    getResults: () => run('readonly', (store) => store.getAll()),
    putResult: async (result) => {
      await run('readwrite', (store) => store.put(result))
    },
  }
}

type Listener = (results: readonly RoomResult[]) => void

interface Held {
  storage: ProfileStorage
  results: Map<string, RoomResult>
  derived: Derived
}

interface Opened {
  held: Promise<Held>
  listeners: Set<Listener>
}

const profiles = new Map<string, Opened>()

/** One profile's Room results as loaded from `storage`, keyed by `room_id`, with their Derived block. */
function hold(storage: ProfileStorage, results: RoomResult[]): Held {
  return { storage, results: new Map(results.map((result) => [result.room_id, result])), derived: derive(results) }
}

/**
 * The profile named `name` (the `?profile=` value), opened on first use: its IndexedDB database, else memory. A
 * database that will not open leaves the profile in memory, so play goes on without persistence.
 */
function open(name: string): Opened {
  let profile = profiles.get(name)
  if (profile === undefined) {
    const storage = typeof indexedDB === 'undefined' ? memoryStorage() : indexedDbStorage(name)
    const held = storage.getResults().then(
      (results) => hold(storage, results),
      () => hold(memoryStorage(), []),
    )
    profile = { held, listeners: new Set() }
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
  await held.storage.putResult(result)
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
