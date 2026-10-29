import './landing.css'
import type { Meta, PlayView, RoomSummary } from '../types'
import { getBuildView, getRoom } from './api/index.ts'
import { CLIP } from './clip.ts'
import { ACCESS_CODE_FIELD, accessCodeBuild } from './components/access-code-build.ts'
import { type AttractFrame, attractFrame } from './components/attract-frame.ts'
import { primaryButton, secondaryButton, secondaryLink } from './components/button.ts'
import { type DemoRoomCard, demoRoomCard } from './components/demo-room-card.ts'
import { bannerSlot } from './components/error-banner.ts'
import { evidenceCard } from './components/evidence-card.ts'
import { sampleClip } from './components/sample-clip.ts'
import { roomTitle } from './components/stored-room-row.ts'
import { buildViewHref, CUT_0 } from './router.ts'
import { roomStarter } from './stored-rooms.ts'
import { fill, strings } from './strings.ts'
import { speakerPrefix, type Wizard, wizardPortrait } from './wizards/portrait.ts'

export interface HostedLanding {
  children: HTMLElement[]
  /**
   * Runs once the landing is in the page: focuses the primary verb (or "Try again" after a failed load), asks the
   * first Demo room for its attract frame and the Riddler's sample page and each card's Build view for its thumbnail;
   * returns the teardown.
   */
  mount: () => () => void
}

interface CastMember {
  wizard: Wizard
  name: string
  role: string
  voice: string
}

/** The four wizards in pipeline order, each with its four-word role and the voice line of its introduction. */
const CAST: readonly CastMember[] = [
  { wizard: 'architect', name: strings.architect, role: strings.architectCastRole, voice: strings.architectVoice },
  { wizard: 'riddler', name: strings.riddler, role: strings.riddlerCastRole, voice: strings.riddlerVoice },
  { wizard: 'guide', name: strings.guide, role: strings.guideCastRole, voice: strings.guideVoice },
  { wizard: 'trickster', name: strings.trickster, role: strings.tricksterCastRole, voice: strings.tricksterVoice },
]

/**
 * "How a room is built" in three steps: each a wizard's name (in `label`) followed by what it does, the models named.
 * The Riddler's step counts `locks`, the first Demo room's Puzzle count, and names no number with no Demo room listed.
 */
function steps(locks: number | undefined): readonly (readonly string[])[] {
  const riddler =
    locks === undefined
      ? strings.howRiddlerUncounted
      : fill(strings.howRiddler, { locks: locks === 1 ? strings.oneLock : fill(strings.locksCount, { n: locks }) })
  return [
    [strings.architect, strings.howArchitect],
    [strings.riddler, riddler],
    [strings.guide, strings.howGuide, strings.trickster, strings.howTrickster],
  ]
}

function paragraph(className: string, ...children: (Node | string)[]): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = className
  element.append(...children)
  return element
}

function span(className: string, text: string): HTMLSpanElement {
  const element = document.createElement('span')
  element.className = className
  element.textContent = text
  return element
}

/**
 * The hero: the `display-lg` line, the tagline under it (naming no model) and, when `soon`, the note that the sample
 * room opens soon; at the right end the primary `verb`, then "How a room is built" (secondary), which opens `first`'s
 * Build view, absent with no Demo room and under cut 0.
 */
function hero(first: RoomSummary | undefined, profile: string, verb: HTMLElement, soon: boolean): HTMLElement {
  const block = document.createElement('section')
  block.className = 'landing-hero'
  const words = document.createElement('div')
  words.className = 'landing-hero-words'
  const title = document.createElement('h1')
  title.className = 'landing-heading display-lg'
  title.textContent = strings.landingSubtitle
  words.append(title, paragraph('landing-line body-md', strings.landingTagline))
  if (soon) words.append(paragraph('landing-note body-md', strings.sampleRoomSoon))
  const actions = document.createElement('div')
  actions.className = 'landing-actions'
  actions.append(verb)
  if (first !== undefined && !CUT_0) {
    actions.append(secondaryLink({ label: strings.howARoomIsBuilt, href: buildViewHref(first.job_id, profile) }))
  }
  block.append(words, actions)
  return block
}

/**
 * The one primary verb: "Play the sample room", which starts a Session on `first` by the same path its card uses,
 * reading "Opening the room…" until the start is refused or the Play screen opens, or, with no Demo room listed,
 * "Build your own room", which moves focus to the Access code field (`field`).
 */
function primaryVerb(
  first: RoomSummary | undefined,
  start: (room: RoomSummary) => Promise<void>,
  field: () => HTMLElement | null,
): HTMLButtonElement {
  if (first === undefined) {
    return primaryButton({
      label: strings.buildYourOwnRoom,
      pendingLabel: strings.buildYourOwnRoom,
      onActivate: async () => {
        field()?.focus()
      },
    })
  }
  return primaryButton({ label: strings.playSampleRoom, pendingLabel: strings.openingRoom, onActivate: () => start(first) })
}

/**
 * The cast: the four wizards, each its 96 px portrait beside its name (`label`) and four-word role (`body-sm`
 * `text-muted`); on hover, and on focus, since each is a Tab stop, the row lifts to chrome, the ring turns lamp and
 * the wizard's voice line (`wizard-line`) fades in where the name was.
 */
function cast(): HTMLElement {
  const list = document.createElement('ul')
  list.className = 'landing-cast'
  list.setAttribute('aria-label', strings.theWizards)
  for (const { wizard, name, role, voice } of CAST) {
    const item = document.createElement('li')
    item.className = 'landing-wizard'
    item.tabIndex = 0
    const who = document.createElement('div')
    who.className = 'landing-wizard-who'
    who.append(span('landing-wizard-name label', name), span('landing-wizard-role body-sm', role))
    item.append(wizardPortrait(wizard, 96), who, paragraph('landing-wizard-voice wizard-line', voice))
    list.append(item)
  }
  return list
}

/**
 * A page of the Riddler's notes from `view`, the first Demo room's `PlayView`: the first Puzzle that waits on nothing,
 * headed "Puzzle {n}" (n = its place in the Room), with its Evidence cards (the Riddler's notes of an unsolved Puzzle),
 * the Riddler's portrait beside the Clue and the Lore, as the Wizard notes draw them. The view holds no solution; no
 * Session is open, so no Current marker. null when no Puzzle is free to start with.
 */
function riddlersNotes(view: PlayView): HTMLElement | null {
  const puzzle = view.puzzles.find((puzzle) => puzzle.requires.length === 0)
  if (puzzle === undefined) return null
  const sheet = document.createElement('article')
  sheet.className = 'landing-notes'
  sheet.setAttribute('aria-label', strings.riddlersNotes)
  const heading = document.createElement('h2')
  heading.className = 'landing-notes-heading display-sm'
  heading.textContent = fill(strings.puzzleHeading, { n: view.puzzles.indexOf(puzzle) + 1 })
  const interactables = new Map(view.interactables.map((interactable) => [interactable.id, interactable]))
  const evidence = document.createElement('ul')
  evidence.className = 'landing-notes-evidence'
  evidence.append(
    ...puzzle.evidence_cards.flatMap((card) => {
      const interactable = interactables.get(card.interactable)
      return interactable === undefined ? [] : [evidenceCard(view.id, interactable, card, false)]
    }),
  )
  const clue = document.createElement('div')
  clue.className = 'landing-notes-clue'
  clue.append(wizardPortrait('riddler', 32), paragraph('wizard-line', speakerPrefix('riddler'), puzzle.clue))
  sheet.append(heading, evidence, clue, paragraph('landing-notes-lore lore', speakerPrefix('riddler'), puzzle.lore))
  return sheet
}

/** The three numbered steps of a landing section, the number in `mono-sm` lamp beside each step's words. */
function numberedSteps(steps: readonly (readonly (Node | string)[])[]): HTMLOListElement {
  const list = document.createElement('ol')
  list.className = 'landing-how-steps'
  steps.forEach((words, index) => {
    const step = document.createElement('li')
    step.className = 'landing-how-step body-sm'
    const n = span('landing-how-n mono-sm', String(index + 1))
    n.setAttribute('aria-hidden', 'true')
    step.append(n, paragraph('landing-how-text', ...words))
    list.append(step)
  })
  return list
}

/** A landing section: its `display-sm` heading, named by id, over `body`. */
function section(className: string, id: string, title: string, body: HTMLElement): HTMLElement {
  const element = document.createElement('section')
  element.className = className
  const heading = document.createElement('h2')
  heading.id = id
  heading.className = 'landing-how-heading display-sm'
  heading.textContent = title
  element.setAttribute('aria-labelledby', heading.id)
  element.append(heading, body)
  return element
}

/** "How a room is built": the heading over the three numbered steps, the wizards' names in `label`. */
function howARoomIsBuilt(locks?: number): HTMLElement {
  const words = steps(locks).map((parts) =>
    parts.flatMap((part, at) => [at === 0 ? '' : ' ', at % 2 === 0 ? span('label', part) : part]),
  )
  return section('landing-how', 'landing-how-heading', strings.howARoomIsBuilt, numberedSteps(words))
}

/** "How to play": the heading over the First-room welcome's three steps, beside the attract frame. */
function howToPlay(): HTMLElement {
  const words = [strings.howToPlay1, strings.howToPlay2, strings.howToPlay3].map((step) => [step])
  return section('landing-how landing-play', 'landing-play-heading', strings.howToPlay, numberedSteps(words))
}

/**
 * The Hosted landing (UX-DR57, UX-DR68), a title screen: the left area holds the banner slot, the hero with the one
 * primary verb, the stage (the first Demo room's attract frame, once its `PlayView` and first photo have answered,
 * with its clue and "How to play" beside it, and the ten-second clip under "How to play" while that room is the one
 * `CLIP` shows), the cast, then a row with the Riddler's sample page from the same `PlayView` and "How a room is
 * built", with any further cards three across under it in served order; the right
 * column holds the Access-code build, whose accepted code calls `onAccepted` with the builds left, over the first
 * Demo room's card. `rooms` is null when `GET /rooms` failed: the plain failed line with "Try again" (`onRetry`)
 * stands in the row's place. An empty list keeps the hero and the cast, notes that the sample room opens soon and
 * makes the verb "Build your own room".
 * In every case the Access-code build stays usable. The verb and a card start a Session through `roomStarter`, so a
 * refused start shows the session-start-refused banner in the slot, focused.
 */
export function hostedLanding(
  rooms: readonly RoomSummary[] | null,
  profile: string,
  mode: Meta['mode'],
  onRetry: () => void,
  onAccepted: (buildsLeft: number) => void,
): HostedLanding {
  const banners = bannerSlot()
  const left = document.createElement('section')
  left.className = 'landing-left'
  left.append(banners)
  const right = document.createElement('aside')
  right.className = 'landing-right'
  right.append(accessCodeBuild(onAccepted))
  const first = rooms?.[0]
  const start = roomStarter(profile, mode, banners)
  const verb = primaryVerb(first, start, () => right.querySelector(`#${ACCESS_CODE_FIELD}`))
  const attract = document.createElement('div')
  attract.className = 'landing-attract-slot'
  const stage = document.createElement('div')
  stage.className = 'landing-stage'
  left.append(hero(first, profile, verb, rooms !== null && rooms.length === 0), stage, cast())

  if (rooms === null) {
    const failed = document.createElement('div')
    failed.className = 'landing-state'
    failed.setAttribute('role', 'alert')
    const retry = secondaryButton({ label: strings.tryAgain, onActivate: onRetry })
    failed.append(paragraph('body-md', strings.demoRoomsFailed), retry)
    left.append(failed)
    const mount = (): (() => void) => {
      retry.focus()
      return () => {}
    }
    return { children: [left, right], mount }
  }
  if (first === undefined) {
    left.append(howARoomIsBuilt())
    return {
      children: [left, right],
      mount: () => {
        verb.focus()
        return () => {}
      },
    }
  }

  const cards: DemoRoomCard[] = [demoRoomCard(first, profile, () => start(first))]
  stage.append(attract, howToPlay())
  if (first.room_id === CLIP.roomId) stage.append(sampleClip())
  const sample = document.createElement('ul')
  sample.className = 'demo-room-list'
  sample.append(cards[0].element)
  right.append(sample)
  const notes = document.createElement('div')
  notes.className = 'landing-notes-slot'
  const below = document.createElement('div')
  below.className = 'landing-below'
  below.append(notes, howARoomIsBuilt(first.puzzle_count))
  left.append(below)
  if (rooms.length > 1) {
    cards.push(...rooms.slice(1).map((room) => demoRoomCard(room, profile, () => start(room))))
    const more = document.createElement('ul')
    more.className = 'demo-room-list'
    more.append(...cards.slice(1).map(({ element }) => element))
    left.append(more)
  }
  return {
    children: [left, right],
    mount: () => {
      verb.focus()
      let mounted = true
      let playing: AttractFrame | null = null
      getRoom(first.room_id).then(
        (view) => {
          const sheet = riddlersNotes(view)
          if (mounted && sheet !== null) notes.replaceChildren(sheet)
          attractFrame(view, roomTitle(first), () => verb.click()).then(
            (frame) => {
              if (frame === null) return
              if (!mounted) {
                frame.unmount()
                return
              }
              playing = frame
              attract.replaceChildren(frame.element)
            },
            () => undefined, // no attract frame; the landing keeps its layout without it
          )
        },
        () => undefined, // no sample page and no attract frame; the verb and the card still start Sessions
      )
      if (!CUT_0) {
        rooms.forEach((room, index) => {
          getBuildView(room.job_id).then(
            (view) => {
              if (mounted) cards[index].showThumbnail(view)
            },
            () => undefined, // no thumbnail; the card still starts Sessions
          )
        })
      }
      return () => {
        mounted = false
        playing?.unmount()
      }
    },
  }
}
