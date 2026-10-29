import './landing.css'
import type { Meta, PlayView, RoomSummary } from '../types'
import { getBuildView, getRoom } from './api/index.ts'
import { chooser } from './chooser.ts'
import { type DemoRoomCard, demoRoomCard } from './components/demo-room-card.ts'
import { bannerSlot } from './components/error-banner.ts'
import { evidenceCard } from './components/evidence-card.ts'
import { CUT_0 } from './router.ts'
import { roomStarter } from './stored-rooms.ts'
import { fill, strings } from './strings.ts'
import { speakerPrefix, type Wizard, wizardPortrait } from './wizards/portrait.ts'

export interface HostedLanding {
  children: HTMLElement[]
  /**
   * Runs once the landing is in the page: deals the chooser in, asks the first Demo room for its photo count and the
   * Riddler's sample page and each further card's Build view for its thumbnail; returns the teardown.
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

/**
 * The Hosted landing (UX-DR57, UX-DR68): the chooser fills the first screen (`chooser.ts`: Watch the demo, Play the
 * sample room, Build your own, the Access-code build in the Build back, whose accepted code calls `onAccepted` with the
 * builds left); below the fold, in the same scroll, the cast, then a row with the Riddler's sample page from the first
 * Demo room's `PlayView` and "How a room is built", then any further Demo room cards three across in served order.
 * `rooms` is null when `GET /rooms` failed: the Play back holds the plain failed line with "Try again" (`onRetry`). An
 * empty list keeps Watch, Build and the cast, and the Play card reads that the sample room opens soon.
 * The Play back starts a Session on the first Demo room through `roomStarter`, so a refused start shows the
 * session-start-refused banner in its slot at the top of the Play back, focused; the further cards go through the same
 * starter, so no second Session starts while one is opening, with their refusal in their own slot above their list.
 */
export function hostedLanding(
  rooms: readonly RoomSummary[] | null,
  profile: string,
  mode: Meta['mode'],
  onRetry: () => void,
  onAccepted: (buildsLeft: number) => void,
): HostedLanding {
  const first = rooms?.[0]
  const banners = bannerSlot()
  const start = roomStarter(profile, mode, banners)
  const screen = chooser({ first, failed: rooms === null, profile, start, banners, onRetry, onAccepted })
  const more = document.createElement('div')
  more.className = 'landing-more'
  more.append(cast())
  if (first === undefined) {
    more.append(howARoomIsBuilt())
    return { children: [screen.element, more], mount: screen.mount }
  }

  const notes = document.createElement('div')
  notes.className = 'landing-notes-slot'
  const below = document.createElement('div')
  below.className = 'landing-below'
  below.append(notes, howARoomIsBuilt(first.puzzle_count))
  more.append(below)
  const others = rooms?.slice(1) ?? []
  const cards: DemoRoomCard[] = []
  if (others.length > 0) {
    const moreBanners = bannerSlot()
    cards.push(...others.map((room) => demoRoomCard(room, profile, () => start(room, moreBanners))))
    const list = document.createElement('ul')
    list.className = 'demo-room-list'
    list.append(...cards.map(({ element }) => element))
    more.append(moreBanners, list)
  }
  return {
    children: [screen.element, more],
    mount: () => {
      const unmountChooser = screen.mount()
      let mounted = true
      getRoom(first.room_id).then(
        (view) => {
          if (!mounted) return
          screen.showPhotos(view.photos.length)
          const sheet = riddlersNotes(view)
          if (sheet !== null) notes.replaceChildren(sheet)
        },
        () => undefined, // no sample page; the Play card keeps its cover and still starts Sessions
      )
      if (!CUT_0) {
        others.forEach((room, index) => {
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
        unmountChooser()
      }
    },
  }
}
