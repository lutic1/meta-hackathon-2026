import './landing.css'
import type { Meta, RoomSummary } from '../types'
import { getBuildView } from './api/index.ts'
import { accessCodeBuild } from './components/access-code-build.ts'
import { secondaryButton, secondaryLink } from './components/button.ts'
import { type DemoRoomCard, demoRoomCard } from './components/demo-room-card.ts'
import { bannerSlot } from './components/error-banner.ts'
import { buildViewHref, CUT_0 } from './router.ts'
import { roomStarter } from './stored-rooms.ts'
import { strings } from './strings.ts'

export interface HostedLanding {
  children: HTMLElement[]
  /**
   * Runs once the landing is in the page: focuses the first Demo room card (or "Try again" after a failed load) and
   * asks each card's Build view for its thumbnail; returns the teardown.
   */
  mount: () => () => void
}

function paragraph(className: string, text: string): HTMLParagraphElement {
  const element = document.createElement('p')
  element.className = className
  element.textContent = text
  return element
}

/**
 * The title block: "Keyframe" in `display-lg`, the subtitle and the pipeline line in `body-md`, then the lead-in in
 * `text-muted` with "How a room is built" (secondary), which opens `first`'s Build view. With no Demo room to open,
 * and under cut 0, the lead-in and its link are absent.
 */
function titleBlock(first: RoomSummary | undefined, profile: string): HTMLElement {
  const block = document.createElement('section')
  block.className = 'landing-title'
  const title = document.createElement('h1')
  title.className = 'landing-heading display-lg'
  title.textContent = strings.wordmark
  block.append(title, paragraph('landing-line body-md', strings.landingSubtitle), paragraph('landing-line body-md', strings.pipelineLine))
  if (first !== undefined && !CUT_0) {
    const lead = document.createElement('div')
    lead.className = 'landing-lead'
    const link = secondaryLink({ label: strings.howARoomIsBuilt, href: buildViewHref(first.job_id, profile) })
    lead.append(paragraph('landing-lead-in body-md', strings.landingLeadIn), link)
    block.append(lead)
  }
  return block
}

/**
 * The Hosted landing (UX-DR57, UX-DR68): the title block across the top, then the left area, with the banner slot at
 * its top and the Demo room cards three across from `rooms` in served order, beside the 400 px right column that
 * holds the Access-code build, whose accepted code calls `onAccepted` with the builds left. `rooms` is null when
 * `GET /rooms` failed: the plain failed line with "Try again" (`onRetry`) stands in place of the cards. An empty list
 * shows the no-demo-rooms line. In every case the Access-code build stays usable. A card starts a Session through
 * `roomStarter`, so a refused start shows the session-start-refused banner in the slot, focused.
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
  const block = titleBlock(rooms?.[0], profile)

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
    return { children: [block, left, right], mount }
  }
  if (rooms.length === 0) {
    left.append(paragraph('landing-state body-md', strings.noDemoRooms))
    return { children: [block, left, right], mount: () => () => {} }
  }

  const start = roomStarter(profile, mode, banners)
  const cards: DemoRoomCard[] = rooms.map((room) => demoRoomCard(room, profile, () => void start(room)))
  const list = document.createElement('ul')
  list.className = 'demo-room-list'
  list.append(...cards.map(({ element }) => element))
  left.append(list)
  return {
    children: [block, left, right],
    mount: () => {
      cards[0].card.focus()
      let mounted = true
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
      }
    },
  }
}

