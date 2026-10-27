// The Player profile (FR-20, FR-22, AD-8): the browser is its system of record and this module its only writer. Every
// other module reads Room results and the Derived block through these exports, and a Session start carries only the
// Derived block. Under cut 2 the profile is a file on this computer, read and written by the file backend through the
// Local-mode `GET|PUT /profile/<name>` alone. Without cut 2 nothing here makes a request: each profile lives in the
// IndexedDB database named after it; where there is no IndexedDB (Node runs the tests on this module as it ships), or
// it will not open (the browser blocks site data), it lives in memory.
import type { Derived, Meta, Profile, RoomResult, SessionStart } from '../../types'
import { derive, freshDerived } from './derive.ts'
import { type FileStorage, fileStorage } from './file.ts'

/**
 * Cut 2 (FR-20, UX-DR84), taken: the Player profile is a file, opened with "Open profile file" and saved with "Save
 * profile file"; false puts the IndexedDB backend back and drops both controls and their line.
 */
export const CUT_2: boolean = true

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
  /** The file backend under cut 2, which can load a chosen file; null without cut 2. */
  file: FileStorage | null
  held: Promise<Held>
  listeners: Set<Listener>
}

const profiles = new Map<string, Opened>()

/** One profile's Room results as loaded from `storage`, keyed by `room_id`, with their Derived block. */
function hold(storage: ProfileStorage, results: RoomResult[]): Held {
  return { storage, results: new Map(results.map((result) => [result.room_id, result])), derived: derive(results) }
}

/**
 * The profile named `name` (the `?profile=` value), opened on first use: its file under cut 2, else its IndexedDB
 * database, else memory. A backend that will not open leaves the profile in memory, so play goes on without persistence.
 */
function open(name: string): Opened {
  let profile = profiles.get(name)
  if (profile === undefined) {
    const file = CUT_2 ? fileStorage(name) : null
    const storage = file ?? (typeof indexedDB === 'undefined' ? memoryStorage() : indexedDbStorage(name))
    const held = storage.getResults().then(
      (results) => hold(storage, results),
      () => hold(memoryStorage(), []),
    )
    profile = { file, held, listeners: new Set() }
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

/** Tells every listener of `profile` its Room results now. */
function heard(profile: Opened, held: Held): void {
  const results = [...held.results.values()]
  for (const listener of profile.listeners) listener(results)
}

/**
 * Records `result` under its `room_id`, replacing the Room's earlier result unless that one counts and this one is
 * demo-flagged, and recomputes the Derived block in the same step. Putting the same result again changes nothing.
 * Under cut 2 Hosted mode has no profile route, so there the result stays in the page and nothing is sent.
 */
export async function putResult(name: string, result: RoomResult, mode: Meta['mode']): Promise<void> {
  const profile = open(name)
  const held = await profile.held
  if (result.demo && held.results.get(result.room_id)?.demo === false) return
  if (mode === 'local' || profile.file === null) await held.storage.putResult(result)
  held.results.set(result.room_id, result)
  held.derived = derive([...held.results.values()])
  heard(profile, held)
}

/**
 * Cut 2, Local mode: "Open profile file" loads the chosen `file` as the profile `name` through `PUT /profile/<name>`,
 * then reads it back with `GET /profile/<name>` and recomputes the Derived block, every listener hearing at once. A
 * refused file (422: it does not parse, or its Derived block is out of bounds) throws and the profile stays as it was.
 */
export async function openProfileFile(name: string, file: Blob): Promise<void> {
  const profile = open(name)
  if (profile.file === null) throw new Error('A profile file opens under cut 2 only')
  const held = await profile.held
  await profile.file.load(file)
  const results = await profile.file.getResults()
  held.results = new Map(results.map((result) => [result.room_id, result]))
  held.derived = derive(results)
  heard(profile, held)
}

/** Cut 2: the profile `name` as "Save profile file" downloads it, every Room result keyed by `room_id` plus the Derived block. */
export async function profileFile(name: string): Promise<Profile> {
  const held = await open(name).held
  return { results: Object.fromEntries(held.results), derived: held.derived }
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
