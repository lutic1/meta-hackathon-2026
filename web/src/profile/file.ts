// The cut-2 backend (FR-20, AD-8): the Player profile as the file `rooms/profiles/<name>.json` on this computer, read
// and written whole through the Local-mode `GET|PUT /profile/<name>`. No DOM, so Node runs it as it ships.
import type { Profile, RoomResult } from '../../types'
import { getProfile, putProfile, RequestFailed } from '../api/index.ts'
import type { ProfileStorage } from './index.ts'
import { derive } from './derive.ts'

/** The file backend: `ProfileStorage` plus loading a chosen file. */
export interface FileStorage extends ProfileStorage {
  /** Writes the chosen file as the profile through `PUT /profile/<name>`; a refusal throws, changing nothing. */
  load(file: Blob): Promise<void>
}

const notFound = (error: unknown): boolean => error instanceof RequestFailed && error.status === 404

/**
 * The profile `name` as its file. Until a file is loaded in this page load, nothing is read: the profile is empty and
 * its Room results live in the page. Each result put writes the whole file, every Room result keyed by `room_id` plus
 * the Derived block recomputed from them; once a file is loaded, reads `GET` it, a 404 reading as an empty profile.
 */
export function fileStorage(name: string): FileStorage {
  const results = new Map<string, RoomResult>()
  let loaded = false
  const profile = (): Profile => ({ results: Object.fromEntries(results), derived: derive([...results.values()]) })
  return {
    getResults: async () => {
      if (loaded) {
        const stored = await getProfile(name).catch((error: unknown) => {
          if (notFound(error)) return null
          throw error
        })
        results.clear()
        for (const result of Object.values(stored?.results ?? {})) results.set(result.room_id, result)
      }
      return [...results.values()]
    },
    putResult: async (result) => {
      const before = results.get(result.room_id)
      results.set(result.room_id, result)
      try {
        await putProfile(name, profile())
      } catch (error) {
        if (before === undefined) results.delete(result.room_id)
        else results.set(result.room_id, before)
        throw error
      }
    },
    load: async (file) => {
      await putProfile(name, file)
      loaded = true
    },
  }
}
