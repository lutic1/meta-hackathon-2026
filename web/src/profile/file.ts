// The cut-2 backend (FR-20, AD-8): the Player profile as the file `rooms/profiles/<name>.json` on this computer, read
// and written whole through the Local-mode `GET|PUT /profile/<name>`, and only once the player has opened it in this
// page load (decision record Oct 29, items 27 and 48). No DOM, so Node runs it as it ships.
import type { Profile, RoomResult } from '../../types'
import { getProfile, putProfile, RequestFailed } from '../api/index.ts'
import { derive } from './derive.ts'

/** A write of the profile file that failed; the Room results it carried are still in the page. */
export class FileNotSaved extends Error {
  override readonly name = 'FileNotSaved'
}

/** The profile file of one profile name: never read or written until the player opens it. */
export interface FileStorage {
  /** Whether "Open profile file" loaded the file in this page load, so it may be read and written. */
  opened(): boolean
  /**
   * Writes the chosen file as the profile through `PUT /profile/<name>`, then reads it back with `GET`, a missing file
   * reading as empty, and answers its Room results. A refusal throws and changes nothing.
   */
  load(file: Blob): Promise<RoomResult[]>
  /** Writes `results` whole, keyed by `room_id`, with their Derived block; a failure throws `FileNotSaved`. */
  save(results: readonly RoomResult[]): Promise<void>
}

const notFound = (error: unknown): boolean => error instanceof RequestFailed && error.status === 404

export function fileStorage(name: string): FileStorage {
  let opened = false
  return {
    opened: () => opened,
    load: async (file) => {
      await putProfile(name, file)
      const stored = await getProfile(name).catch((error: unknown) => {
        if (notFound(error)) return null
        throw error
      })
      opened = true
      return Object.values(stored?.results ?? {})
    },
    save: async (results) => {
      const profile: Profile = {
        results: Object.fromEntries(results.map((result) => [result.room_id, result])),
        derived: derive(results),
      }
      try {
        await putProfile(name, profile)
      } catch {
        throw new FileNotSaved(`${name}.json was not written`)
      }
    },
  }
}
