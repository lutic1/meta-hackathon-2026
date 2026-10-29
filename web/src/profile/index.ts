// The Player profile (FR-20, FR-22, AD-8): the browser is its system of record and this module its only writer. Every
// other module reads Room results and the Derived block through these exports, and a Session start carries only the
// Derived block. Under cut 2 the profile is a file on this computer, read and written by the file backend through the
// Local-mode `GET|PUT /profile/<name>` alone, and only once the player opens it; until then its Room results live in
// the page. Without cut 2 nothing here makes a request: each profile lives in the IndexedDB database named after it;
// where there is no IndexedDB (Node runs the tests on this module as it ships) it lives in memory, and where IndexedDB
// fails (the browser blocks site data, or refuses a write) it falls back to memory, marked temporary.
import type { Derived, Meta, Profile, RoomResult, SessionStart } from '../../types'
import { derive, freshDerived } from './derive.ts'
import { type FileStorage, fileStorage } from './file.ts'

export { FileNotSaved } from './file.ts'

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

/** The Session a Room result came from, and whether it was recorded from a reopened Completion screen. */
interface RecordedSession {
  id: string
  reopened: boolean
}

interface Held {
  storage: ProfileStorage
  results: Map<string, RoomResult>
  derived: Derived
  /**
   * The Session each Room's result came from in this page load (session ids are ULIDs, so they sort by start time),
   * and whether its Completion screen was a reopened one: a completion is recorded once per Session, an older
   * Session's result never replaces a newer one's, and a Room whose result came from elsewhere (IndexedDB, the
   * profile file) has none.
   */
  sessions: Map<string, RecordedSession>
  /** IndexedDB failed, so the Room results live in memory and last only as long as the page. */
  temporary: boolean
}

interface Opened {
  /** The profile file under cut 2, read and written only once opened; null without cut 2. */
  file: FileStorage | null
  held: Promise<Held>
  listeners: Set<Listener>
}

const profiles = new Map<string, Opened>()

/** One profile's Room results as loaded from `storage`, keyed by `room_id`, with their Derived block. */
function hold(storage: ProfileStorage, results: RoomResult[], temporary: boolean): Held {
  const held = new Map(results.map((result) => [result.room_id, result]))
  return { storage, results: held, derived: derive(results), sessions: new Map(), temporary }
}

/** The IndexedDB database of profile `name`, or memory where the page has no IndexedDB (Node). Reading it may throw. */
function browserStorage(name: string): ProfileStorage {
  return typeof indexedDB === 'undefined' ? memoryStorage() : indexedDbStorage(name)
}

/**
 * The profile named `name` (the `?profile=` value), opened on first use: under cut 2 in the page, with its file opened
 * only by the player; else its IndexedDB database. A database that will not open leaves the profile in memory, marked
 * temporary, so play goes on without persistence.
 */
function open(name: string): Opened {
  let profile = profiles.get(name)
  if (profile === undefined) {
    const file = CUT_2 ? fileStorage(name) : null
    let held: Promise<Held>
    try {
      const storage = CUT_2 ? memoryStorage() : browserStorage(name)
      held = storage.getResults().then(
        (results) => hold(storage, results, false),
        () => hold(memoryStorage(), [], true),
      )
    } catch {
      held = Promise.resolve(hold(memoryStorage(), [], true))
    }
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

/** Whether the profile lives only in this page because IndexedDB failed, so the Completion screen says so. */
export async function profileTemporary(name: string): Promise<boolean> {
  return (await open(name).held).temporary
}

/** Tells every listener of `profile` its Room results now. */
function heard(profile: Opened, held: Held): void {
  const results = [...held.results.values()]
  for (const listener of profile.listeners) listener(results)
}

/** Whether `next` may take the place of `before` for its Room: a demo-flagged result never replaces a counted one. */
const replaces = (before: RoomResult | undefined, next: RoomResult): boolean => !(next.demo && before?.demo === false)

/** Sets `held`'s Room results to `results` and recomputes the Derived block in the same step. */
function settle(held: Held, results: Map<string, RoomResult>): void {
  held.results = results
  held.derived = derive([...results.values()])
}

/**
 * Records `result`, the result of Session `sessionId`, under its `room_id` once: a Session already recorded, or older
 * than the one whose result the Room holds from this page load, records nothing, and a demo-flagged result never
 * replaces a counted one. A `reopened` Completion screen (not reached from the Exit on the Play screen in this page
 * load) fills a Room the profile lacks, or follows an older Session of this page load, but never replaces a result
 * from elsewhere (IndexedDB, the profile file), whose Session this page cannot order. The Derived block is recomputed
 * in the same step and every listener hears at once; then the result is stored. A failed IndexedDB write moves the
 * profile to memory, marked temporary. Under cut 2 the result is written to the profile file only once the player has
 * opened it, and only in Local mode (Hosted mode has no profile route); a failed write throws `FileNotSaved` while the
 * result stays recorded in the page.
 */
export async function putResult(
  name: string,
  result: RoomResult,
  mode: Meta['mode'],
  sessionId: string,
  reopened: boolean,
): Promise<void> {
  const profile = open(name)
  const held = await profile.held
  const recorded = held.sessions.get(result.room_id)
  if (recorded !== undefined && recorded.id >= sessionId) return
  if (reopened && recorded === undefined && held.results.has(result.room_id)) return
  if (!replaces(held.results.get(result.room_id), result)) return
  held.sessions.set(result.room_id, { id: sessionId, reopened })
  settle(held, new Map(held.results).set(result.room_id, result))
  heard(profile, held)
  try {
    await held.storage.putResult(result)
  } catch {
    held.storage = memoryStorage()
    held.temporary = true
  }
  if (profile.file?.opened() === true && mode === 'local') await profile.file.save([...held.results.values()])
}

/**
 * Cut 2, Local mode: "Open profile file" loads the chosen `file` as the profile `name` through `PUT /profile/<name>`,
 * then reads it back with `GET /profile/<name>` and merges it with the Room results this page holds: each fills a Room
 * the file lacks, but replaces the file's only when its Session ended on the Play screen in this page load (a
 * reopened Completion screen's result never does, nor does a demo-flagged result replace a counted one); the Derived
 * block is recomputed and every listener hears at once. A merge that changed the file is written back; a failed write
 * throws `FileNotSaved`, the merged profile still shown. A refused file (422: it does not parse, or its Derived block
 * is out of bounds) throws and the profile stays as it was, still unopened.
 */
export async function openProfileFile(name: string, file: Blob): Promise<void> {
  const profile = open(name)
  if (profile.file === null) throw new Error('A profile file opens under cut 2 only')
  const held = await profile.held
  const stored = new Map((await profile.file.load(file)).map((result) => [result.room_id, result]))
  const merged = new Map(stored)
  for (const [roomId, result] of held.results) {
    const endedHere = held.sessions.get(roomId)?.reopened === false
    if (!stored.has(roomId) || (endedHere && replaces(stored.get(roomId), result))) merged.set(roomId, result)
    else held.sessions.delete(roomId) // the Room holds the file's result now, from a Session this page cannot order
  }
  settle(held, merged)
  heard(profile, held)
  const changed = [...merged].some(([roomId, result]) => stored.get(roomId) !== result)
  if (changed) await profile.file.save([...merged.values()])
}

/** Cut 2: writes the profile file again after a failed write ("Try again"); nothing before the file is opened. */
export async function saveProfileFile(name: string): Promise<void> {
  const profile = open(name)
  const held = await profile.held
  if (profile.file?.opened() === true) await profile.file.save([...held.results.values()])
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
