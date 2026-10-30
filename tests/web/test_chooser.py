"""Story 7.16, owner decision Oct 29: the Hosted landing's first screen is a hero-select chooser of three cards (Watch
the demo, Play the sample room, Build your own) that turn over into one shared back panel, a modal dialog.

The client has no test runner, so these checks read web/src/chooser.ts and chooser.css (comments stripped) and the
contract; `npm run build` and `tsc --noEmit` prove they compile, and the browser run proves the motion.
"""

import re

from tests.web.design import WEB_SRC, css_rules, design_text
from tests.web.test_contrast import PROPS, _hex, contrast
from tests.web.test_strings import _section, _strings


def _code(name: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", (WEB_SRC / name).read_text(), flags=re.DOTALL)


def _chooser() -> str:
    return _code("chooser.ts")


def _body(ts: str, start: str) -> str:
    """The block from `start` to the first line closing it at the indent of its opening line."""
    at = ts.index(start)
    indent = at - ts.rfind("\n", 0, at) - 1
    return ts[at:ts.index("\n" + " " * indent + "}", at)]


def _rules() -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / "chooser.css").read_text())


# --- The strings ------------------------------------------------------------------------


def test_the_chooser_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["chooserSubline"] == "Pick a card. Any card." and strings["chooserGroup"] == "Three ways in"
    # Since the tutorial (Oct 29) the card promises both videos and its tag reads the tutorial's length.
    assert (strings["watchCardEyebrow"], strings["watchCardTitle"], strings["watchCardTag"]) == ("Two videos", "Watch the demo", "0:20")
    assert strings["watchCardLine"] == "A twenty-second tutorial, then a real room played start to finish."
    assert (strings["watchCardPrompt"], strings["watchBackTag"]) == ("Watch it bigger", "muted · 1:48")
    assert (strings["playCardEyebrow"], strings["playCardPrompt"]) == ("The sample room", "Step inside")
    assert (strings["buildCardEyebrow"], strings["buildCardTitle"], strings["buildCardTag"]) == ("Your photos", "Build your own", "~3 min")
    assert strings["buildCardLine"] == (
        "Six to ten photos of one room. Four wizards, Meta's Muse Spark and SAM underneath, find the objects, write the riddles"
        " and test every lock. About three minutes.")
    assert strings["buildCardPrompt"] == "See how it works"
    assert [strings[f"buildStep{n}"] for n in (1, 2, 3)] == [
        "Six to ten photos in", "Four wizards build a room", "Three minutes later, you play"]
    assert strings["buildStep2Body"] == (
        "With Meta's Muse Spark and SAM underneath, they find the objects, write the riddles and test that every lock opens.")
    assert strings["accessCodeAsk"] == "Have an access code?"
    assert strings["accessCodeNote"] == "Building a room needs the code from the submission."
    assert (strings["back"], strings["backToCards"], strings["pauseMotion"]) == ("Back", "Back to the three cards", "Pause motion")
    assert strings["cardAnnounce"].format(title="Watch the demo", n=1) == "Watch the demo, card 1 of 3. Click or press Enter to choose."
    # No line on the first screen names AI, an assistant, an agent or a model, but the Build card and its second step
    # say what the four wizards stand on: Meta's Muse Spark and SAM, by name, never a model id (owner decision Oct 29).
    named = {"buildCardLine", "buildStep2Body"}
    first_screen = {key: value for key, value in strings.items() if key.startswith(("chooser", "watch", "play", "build", "hero", "keys"))}
    for key, value in first_screen.items():
        assert not re.search(r"(?i)\b(AI|assistant|agent|model|llama)\b|\b(muse|sam)-", value), value
        assert ("Meta's Muse Spark and SAM" in value) == (key in named), key
    rows = {row.split(" |", 1)[0]: row for row in _section("Voice and Tone").split("\n| ")}
    assert f'"{strings["buildCardLine"]}"' in rows["Build card"]
    assert f'"{strings["buildStep2"]}" / "{strings["buildStep2Body"]}"' in rows["Build back"]
    assert "except the Build card and its second step" in rows["Chooser pitch (the wordmark \"Keyframe\" stays in the top bar)"]
    for key in ("chooserSubline", "watchCardLine", "buildCardLine", "cardAnnounce", "backToCards", "accessCodeNote"):
        assert strings[key].replace("{title}", "").replace("{n}", "") .split(",")[0][:20] in _section("Voice and Tone"), key


# --- Structure and data -----------------------------------------------------------------


def test_each_card_is_a_real_button_named_by_its_title_described_by_its_line_and_opening_the_dialog():
    ts = _chooser()
    card = _body(ts, "  function card(")
    assert "title.id = `chooser-title-${i}`" in card and "description.id = `chooser-line-${i}`" in card
    for attribute in ("'aria-labelledby', [title.id, ...named].join(' ')", "'aria-describedby', description.id", "'aria-haspopup', 'dialog'",
                      "'aria-expanded', 'false'", "'aria-controls', 'chooser-panel'"):
        assert f"choose.setAttribute({attribute})" in card, attribute
    assert "choose.type = 'button'" in card
    assert "row.setAttribute('role', 'group')" in ts and "row.setAttribute('aria-label', strings.chooserGroup)" in ts
    assert "const titles = [strings.watchCardTitle, strings.playSampleRoom, strings.buildCardTitle]" in ts
    # One dialog for the three backs, named by the chosen card's title.
    assert "panel.setAttribute('role', 'dialog')" in ts and "panel.setAttribute('aria-modal', 'true')" in ts
    assert "panel.setAttribute('aria-labelledby', `chooser-title-${i}`)" in ts
    # Only the buttons take the pointer, so no transformed plane catches a click in 3D.
    rules = _rules()
    assert rules[".chooser-slot,\n.chooser-deal,\n.chooser-breath,\n.chooser-tilt,\n.chooser-card,\n.chooser-face"] == {"pointer-events": "none"}
    assert rules[".chooser-choose"]["pointer-events"] == "auto"


def test_the_play_card_reads_the_first_demo_room_and_its_photos_from_the_api_at_runtime():
    ts = _chooser()
    assert "const order: number[] = first === undefined ? [] : [first.cover_photo]" in ts
    assert "const urls = order.map((n) => photoUrl(first.room_id, n))" in ts
    shown = _body(ts, "    showPhotos(total) {")
    assert "first.cover_photo, ...Array.from({ length: total }, (_, n) => n).filter((n) => n !== first.cover_photo)" in shown
    assert "playLine = [`${roomTitle(first)}.`, ' ', element('span', 'chooser-meta', fill(strings.demoRoomMeta, { puzzles }))]" in ts
    assert "fact(strings.puzzleCount, first.puzzle_count)" in ts and "fact(strings.minutesRange, '15–25')" in ts
    assert "fact(strings.photoCount, urls.length)" in ts
    # The photos come from the API at runtime; nothing under web/ is a room photo.
    for path in (WEB_SRC.parent / "public").rglob("*"):
        # The clip's posters, the intro's title frame and the tutorial's first caption are stills of videos, not room photos.
        assert path.suffix.lower() not in {".jpg", ".jpeg"} or path.parent.name in {"clip", "intro", "tutorial"}, path


def test_play_this_room_is_the_guarded_start_with_its_pending_label_so_no_session_starts_twice():
    ts = _chooser()
    assert "primaryButton({ label: strings.playThisRoom, pendingLabel: strings.openingRoom, onActivate: () => start(first) })" in ts
    assert "const link = buildViewLink(first.job_id, profile)" in ts and "if (link !== null) actions.append(link)" in ts
    landing = _code("landing.ts")
    assert landing.count("roomStarter(") == 1  # one starter for the whole landing
    starter = _code("stored-rooms.ts")
    assert "if (starting || started) return" in starter
    # The pending primary button ignores repeat activation until the start settles, and a routed start never settles.
    assert "if (pending) return" in _code("components/button.ts")
    assert "return new Promise<never>(() => undefined)" in starter



def test_the_play_back_and_the_further_cards_share_one_start_guard_so_no_session_starts_twice():
    landing = _code("landing.ts")
    # One guarded starter serves the Play back and every further Demo room card; each keeps its own banner slot, so a
    # start opening from one is never joined by a second from the other.
    assert landing.count("roomStarter(") == 1 and "const start = roomStarter(profile, mode, banners)" in landing
    assert "chooser({ first, failed: rooms === null, profile, start, banners, onRetry, onAccepted })" in landing
    assert "demoRoomCard(room, profile, () => start(room, moreBanners))" in landing
    assert "startMore" not in landing
    starter = _code("stored-rooms.ts").split("export function roomStarter(", 1)[1].split("\n}\n", 1)[0]
    assert "async function start(room: RoomSummary, slot: HTMLElement = banners): Promise<void> {" in starter
    assert starter.count("let starting = false") == 1 and starter.count("let started = false") == 1
    assert "if (starting || started) return" in starter

def test_the_build_back_holds_the_three_steps_and_the_access_code_build_unchanged():
    ts = _chooser()
    build = ts.split("const buildView = element(", 1)[1].split("const views = ", 1)[0]
    assert "head(strings.buildYourOwnRoom, voice('architect', strings.architectVoice))" in build
    assert "accessCodeBuild(onAccepted, { heading: false })" in build
    assert "step(1, thumbs, strings.buildStep1, strings.buildStep1Body)" in ts
    assert "step(3, solvedChips, strings.buildStep3, strings.buildStep3Body)" in ts
    assert "if (first !== undefined && !CUT_0) {" in ts and "link.href = buildViewHref(first.job_id, profile)" in ts
    assert "panel.querySelector<HTMLElement>(`#${ACCESS_CODE_FIELD}`)" in ts  # the open focus target


def test_with_no_demo_room_or_a_failed_listing_watch_and_build_stay_and_the_play_back_holds_its_line():
    ts = _chooser()
    assert "playLine = [failed ? strings.demoRoomsFailed : strings.sampleRoomSoon]" in ts
    assert "playTag.hidden = first === undefined" in ts
    assert "frontPhotos.firstElementChild?.append(art(keyholeArt('chooser-lattice-none')))" in ts
    no_room = ts.split("  } else {\n    playFocus = failed", 1)[1].split("\n  }\n", 1)[0]
    assert "? secondaryButton({ label: strings.tryAgain, onActivate: onRetry })" in no_room
    assert ": secondaryButton({ label: strings.buildCardTitle, onActivate: () => void goto(2) })" in no_room
    # The Watch back's "Play the sample room" needs a room; its "Build your own" never does.
    actions = ts.split("const watchActions = element(", 1)[1].split("const watchView", 1)[0]
    assert "secondaryButton({ label: strings.buildCardTitle, onActivate: () => void goto(2) })" in actions
    assert "if (first !== undefined) {" in actions
    # The Build card shows the portraits alone, with no photo fan.
    assert "...(first === undefined ? [] : [fan]), heroes" in ts


# --- The state machine and the keyboard ---------------------------------------------------


def test_the_states_run_arriving_rest_choosing_chosen_returning_and_input_waits_for_rest():
    ts = _chooser()
    assert "type State = 'arriving' | 'rest' | 'choosing' | 'chosen' | 'returning'" in ts
    assert "let state: State = reduced ? 'rest' : 'arriving'" in ts
    choose = _body(ts, "  function choose(i: number): void {")
    assert "if (state !== 'rest' || !mounted) return" in choose
    assert "state = 'choosing'" in choose and "state = 'chosen'" in choose
    assert "later(() => {\n      slot.style.transition = ''\n      finish()\n    }, T_CHOOSE)" in choose
    home = _body(ts, "  function goHome(then?: () => void): void {")
    assert "if (state !== 'chosen') return" in home and "state = 'returning'" in home and "state = 'rest'" in home
    assert "later(done, T_RETURN_PANEL + T_RETURN_CARD + 40)" in home
    # Escape during the turn is held and runs once the panel is open.
    assert "queuedHome = true" in ts and "if (queuedHome) goHome()" in choose
    # A cross-link turns home first, then opens its card.
    assert "goHome(() => choose(target))" in ts
    assert (ts.count("const T_CHOOSE = 1150"), ts.count("const T_RETURN_PANEL = 380"), ts.count("const T_RETURN_CARD = 560")) == (1, 1, 1)


def test_choosing_makes_everything_outside_the_dialog_inert_and_locks_the_scroll_and_home_undoes_it():
    ts = _chooser()
    outside = _body(ts, "  function outside(): HTMLElement[] {")
    assert "document.querySelector<HTMLElement>('.top-bar')" in outside
    assert "return [...(bar === null ? [] : [bar]), row, keys, ...below]" in outside
    modal = _body(ts, "  function setModal(on: boolean): void {")
    assert "for (const node of outside()) node.inert = on" in modal and "scroller.classList.toggle('is-locked', on)" in modal
    assert "setModal(true)" in _body(ts, "  function choose(i: number): void {")
    assert "setModal(false)" in _body(ts, "  function goHome(then?: () => void): void {")
    assert "button.setAttribute('aria-expanded', 'true')" in ts and "button.setAttribute('aria-expanded', 'false')" in ts
    # Focus moves in on open and back to the card on the way home.
    assert "const target = i === 0 ? watchVideos[watchTab] : i === 1 ? playFocus : panel.querySelector<HTMLElement>(`#${ACCESS_CODE_FIELD}`)" in ts
    assert "button.focus({ preventScroll: true })" in ts


def test_the_dialog_traps_tab_and_escape_back_and_the_bare_stage_turn_it_home():
    ts = _chooser()
    trap = _body(ts, "  function trapTab(event: KeyboardEvent): void {")
    assert "view.querySelectorAll<HTMLElement>('button, a[href], input, video[tabindex]')" in trap
    assert "if (event.shiftKey && at === firstControl)" in trap and "lastControl.focus()" in trap
    assert "else if (!event.shiftKey && at === lastControl)" in trap and "firstControl.focus()" in trap
    keys = _body(ts, "  function onKey(event: KeyboardEvent): void {")
    assert "event.key === 'Escape' && state === 'chosen'" in keys and "event.key === 'Tab' && state === 'chosen'" in keys
    # Listened for in the capture phase, so a control inside the panel never keeps Escape from the page.
    assert "document.addEventListener('keydown', onKey, true)" in ts and "document.removeEventListener('keydown', onKey, true)" in ts
    assert "back.addEventListener('click', () => goHome())" in ts and "back.setAttribute('aria-label', strings.backToCards)" in ts
    stage = ts.split("stage.addEventListener('click', (event) => {", 1)[1].split("})", 1)[0]
    assert "state === 'chosen' && event.target instanceof Node && !panel.contains(event.target)" in stage


def test_hover_and_focus_bring_a_card_forward_and_the_pointer_settling_is_announced_once():
    ts = _chooser()
    assert "button.addEventListener('focus', () => {" in ts and "if (state === 'rest') setActive(i)" in ts
    assert "slot.addEventListener('pointerenter', () => {" in ts
    announce = _body(ts, "  function announceSoon(i: number): void {")
    assert "}, ANNOUNCE_MS)" in announce and "const ANNOUNCE_MS = 500" in ts
    assert "slots[i].contains(document.activeElement)" in announce  # keyboard focus is announced by the button
    assert "if (line === lastAnnounced) return" in announce
    # The arc: rest, the card forward, the others back.
    arc = _body(ts, "  function transformFor(i: number): string {")
    assert "translate3d(0, -10px, 80px) rotateY(${-p * 3}deg) scale(1.03)" in arc
    assert "translate3d(0, ${a * 10 + 8}px, ${-120 * a - 110}px) rotateY(${-p * 12}deg)" in arc


# --- Size: the trio fills the stage, the text never under 14 px -----------------------------


def test_the_cards_are_sized_from_the_stage_height_then_width_with_no_cap_so_large_screens_fill():
    ts = _chooser()
    layout = _body(ts, "  function layout(): void {")
    assert "let H = Math.round(Math.max(360, sh - 80))" in layout and "let W = Math.round(H * 0.64)" in layout
    assert "const maxW = Math.floor((vw - 96) / 3.3)" in layout
    assert "740" not in layout  # the prototype's height cap left a 1920 x 1080 stage half empty
    # The stage heights measured in the browser at 1024 x 768, 1440 x 900 and 1920 x 1080, and the card widths shown.
    for stage, vw, w in ((548, 1024, 281), (674, 1440, 380), (842, 1920, 488)):
        H = max(360, stage - 80)
        assert min(round(H * 0.64), (vw - 96) // 3.3) == w
    # Layout reads the stage on mount and resize only; the tilt reads the cache.
    assert "new ResizeObserver(() => {" in ts and "resized = requestAnimationFrame(layout)" in ts
    assert "getBoundingClientRect" not in _body(ts, "  function tick(): void {")


def test_the_card_text_scales_with_the_card_and_never_drops_below_14_px():
    rules = _rules()
    for selector in (".chooser-eyebrow", ".chooser-tag", ".chooser-title", ".chooser-line", ".chooser-meta",
                     ".chooser-prompt", ".chooser-hero-name"):
        size = rules[selector]["font-size"]
        low = re.fullmatch(r"clamp\((\d+)px, [\d.]+cqw, \d+px\)", size)
        assert low and int(low.group(1)) >= 14, (selector, size)
    assert rules[".chooser-kbd"]["font-size"] == "14px"
    # Under 270 px of window the short names hide rather than shrink.
    assert "@container (max-width: 270px) {\n  .chooser-hero-name {\n    display: none;" in (WEB_SRC / "chooser.css").read_text()


# --- Motion: the owner's exception, Pause motion and reduced motion ---------------------------


def test_only_transform_and_opacity_animate_and_never_on_the_3d_planes():
    text = re.sub(r"/\*.*?\*/", "", (WEB_SRC / "chooser.css").read_text(), flags=re.DOTALL)
    for frames in re.findall(r"@keyframes [\w-]+ \{(.*?)\n\}", text, flags=re.DOTALL):
        props = set(re.findall(r"^\s+([\w-]+):", frames, flags=re.MULTILINE))
        assert props <= {"transform", "opacity"}, props
    animated = {"transform", "opacity", "background-color", "border-color"}
    for value in re.findall(r"transition:\s*([^;]+);", text):
        for part in re.sub(r"\([^)]*\)", "", value).split(","):
            assert part.split()[0] in animated | {"none"}, part
    rules = _rules()
    for plane in (".chooser-slot", ".chooser-deal,\n.chooser-breath,\n.chooser-tilt,\n.chooser-card"):
        assert not {"opacity", "filter", "overflow"} & set(rules[plane]), plane
    ts = _chooser()
    # The turn's opacity goes on the leaf face, never on the preserve-3d card.
    assert "reverse.animate([{ opacity: 1 }, { opacity: 1, offset: 0.96 }, { opacity: 0 }]" in ts
    assert "filter" not in rules[".chooser-beam"]


def test_pause_motion_holds_every_loop_still_and_the_player_s_own_motion_still_answers():
    ts = _chooser()
    assert "stillToggle.setAttribute('aria-pressed', String(still))" in ts
    toggle = ts.split("stillToggle.addEventListener('click', () => {", 1)[1].split("\n  })", 1)[0]
    assert "section.classList.toggle('is-still', still)" in toggle
    for line in ("frontVideo.pause()", "panelVideo.pause()", "playVideo.pause()", "frontCycler.stop()"):
        assert line in toggle
    assert "let still = false" in ts  # held for the page, across a re-render of the landing
    rules = _rules()
    assert rules[".chooser.is-still *,\n.chooser.is-still ::before,\n.chooser.is-still ::after"] == {
        "animation-play-state": "paused !important"}
    # The label stays; only the icon swaps.
    assert "strings.pauseMotion" in ts and rules[".chooser-still-toggle[aria-pressed='true'] .is-play"] == {"display": "inline"}


def test_reduced_motion_deals_nothing_crossfades_each_change_and_holds_the_loops():
    ts = _chooser()
    assert "const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches" in ts
    assert "if (!reduced) section.classList.add('is-arriving', 'is-pre')" in ts
    assert "if (reduced) return" in _body(ts, "  function arrive(): void {")
    fade = _body(ts, "  function crossfade(swap: () => void): void {")
    assert "stage.animate([{ opacity: 1 }, { opacity: 0 }], { duration: FADE_MS, easing: 'ease', fill: 'forwards' })" in fade
    assert "const FADE_MS = 160" in ts
    assert "if (reduced) {\n      crossfade(() => {" in _body(ts, "  function choose(i: number): void {")
    assert "if (reduced) {\n      crossfade(() => {" in _body(ts, "  function goHome(then?: () => void): void {")
    assert "if (state !== 'rest' || reduced) return" in ts  # no tilt
    assert "if (timer !== undefined || reduced || still || images.length < 2) return" in ts  # no cycling
    reduced = (WEB_SRC / "chooser.css").read_text().split("@media (prefers-reduced-motion: reduce) {", 1)[1]
    for selector in (".chooser-breath", ".chooser-beam", ".chooser-shine::before", ".chooser-photo.is-on"):
        assert selector in reduced
    assert "transform: translate3d(0, calc(var(--p) * -78vh), 0);" in reduced  # the dust holds still


def test_the_teardown_stops_every_loop_listener_and_animation():
    teardown = _chooser().split("      return () => {\n        mounted = false", 1)[1]
    for line in ("observer.disconnect()", "for (const timer of timers) clearTimeout(timer)",
                 "for (const animation of section.getAnimations({ subtree: true })) animation.cancel()",
                 "frontVideo.pause()", "panelVideo.pause()", "playVideo.pause()", "frontCycler.stop()",
                 "document.removeEventListener('visibilitychange', onVisibility)", "if (chosen !== -1) setModal(false)"):
        assert line in teardown, line


# --- The contract ------------------------------------------------------------------------------


def test_the_contract_records_the_chooser_and_the_owner_s_motion_exception():
    design = design_text()
    assert "**Owner exception: the Hosted landing chooser only (Oct 29).**" in design
    motion = design.split("**Motion.**", 1)[1].split("\n## ", 1)[0]
    for word in ("deal", "breathing idle", "lift", "tilt", "spin", "dust", "candle flicker", "Pause motion",
                 "160 ms crossfade", "Every other surface keeps the rule above."):
        assert word in motion, word
    assert "| Chooser |" in design and "  chooser:\n" in design.split("\n---\n", 1)[0]
    experience = (WEB_SRC.parents[1] / "docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/EXPERIENCE.md").read_text()
    states = experience.split("\n### Hosted landing\n", 1)[1].split("\n## ", 1)[0]
    for state in ("| Arriving |", "| Choosing / chosen / returning |", "| No Demo rooms |", "| Pause motion |",
                  "| Reduced motion |", "| Keyboard and focus |"):
        assert state in states, state
    assert "the Hosted landing's chooser alone excepted" in experience
    assert "the Hosted landing's card announcement" in experience


# --- The reviewer's feedback (owner decision Oct 29): one obvious start, the code up front, text that reads ----------

FRONT_PAD = 24
"""The card front's padding on both sides: its text's `cqw` is a hundredth of the card width less this."""
CARD_W = {1024: 281, 1440: 380, 1920: 488}
"""The card widths the browser measured at 1024 x 768, 1440 x 900 and 1920 x 1080 (the sizing test above)."""


def _clamp_px(size: str, width: int) -> float:
    """A card text's `clamp(min, n cqw, max)` (or a plain px size) in px on the card `width` px wide."""
    plain = re.fullmatch(r"(\d+)px", size)
    if plain:
        return float(plain.group(1))
    low, scale, high = re.fullmatch(r"clamp\((\d+)px, ([\d.]+)cqw, (\d+)px\)", size).groups()  # type: ignore[union-attr]
    return min(float(high), max(float(low), float(scale) * (width - FRONT_PAD) / 100))


def _mix(top: tuple[float, ...], under: tuple[float, ...], alpha: float) -> tuple[float, float, float]:
    r, g, b = (alpha * t + (1 - alpha) * u for t, u in zip(top, under))
    return r, g, b


def test_at_rest_the_play_card_leads_forward_lit_and_prompted_while_watch_and_build_wait_a_step_back():
    ts = _chooser()
    assert "const lead = first === undefined ? -1 : 1" in ts
    arc = _body(ts, "  function transformFor(i: number): string {")
    assert "if (active === -1 && i === lead) return 'translate3d(0, -6px, 50px)'" in arc
    assert "if (active === -1 && lead !== -1) return `translate3d(0, ${a * 10 + 4}px, ${-a * 120 - 50}px) rotateY(${-p * 10}deg)`" in arc
    apply = _body(ts, "  function applyAll(): void {")
    assert "const leading = chosen === -1 && active === -1 && i === lead && (state === 'rest' || state === 'arriving')" in apply
    assert "slot.classList.toggle('is-lead', leading)" in apply
    assert "slot.classList.toggle('is-back', chosen === -1 && active === -1 && lead !== -1 && i !== lead)" in apply
    rules = _rules()
    # The lead shows its prompt, its lamp rim, its pool and its plate at rest, as a card brought forward does.
    assert rules[".chooser-slot.is-active .chooser-prompt,\n.chooser-slot.is-lead .chooser-prompt"] == {"opacity": "1", "transform": "none"}
    assert rules[".chooser-slot.is-active .chooser-glow,\n.chooser-slot.is-lead .chooser-glow"] == {"opacity": "1"}
    assert "pools[i].classList.toggle('is-lit', lit || leading)" in apply
    # The two behind it dim less than a card stepped back by hover or focus, and keep their plate whole.
    back, dimmed = rules[".chooser-slot.is-back .chooser-dim"], rules[".chooser-slot.is-dimmed .chooser-dim"]
    assert float(back["opacity"]) < float(dimmed["opacity"])


def test_the_play_card_carries_the_lamp_tag_no_upload_needed():
    strings = _strings()
    assert strings["noUploadNeeded"] == "No upload needed"
    ts = _chooser()
    assert "const playTags = [playTag, ...(first === undefined ? [] : [tagChip(strings.noUploadNeeded, 'is-lamp')])]" in ts
    assert "card(1, MEDAL_KEY, frontPhotos, strings.playCardEyebrow, playTags, playLine, strings.playCardPrompt)" in ts
    lamp = _rules()[".chooser-tag.is-lamp"]
    assert lamp["background"] == "var(--lamp-strong)" and lamp["color"] == "var(--on-lamp)"
    assert contrast(_hex(PROPS["on-lamp"])[0], _hex(PROPS["lamp-strong"])[0]) >= 7


def test_the_card_group_s_one_tab_stop_starts_on_the_play_card_and_roves_with_focus():
    ts = _chooser()
    rove = _body(ts, "  function rove(i: number): void {")
    assert "cards.forEach(({ choose: button }, k) => {\n      button.tabIndex = k === i ? 0 : -1\n    })" in rove
    assert "clipToggle.tabIndex = i === 0 ? 0 : -1" in rove  # the Watch card's own toggle, a stop only after it
    assert "rove(Math.max(lead, 0))" in ts  # Play first; Watch with no Demo room listed, when nothing leads
    focus = ts.split("button.addEventListener('focus', () => {", 1)[1].split("\n    })", 1)[0]
    assert "rove(i)" in focus
    # The arrows still move across all three.
    keys = ts.split("button.addEventListener('keydown', (event) => {", 1)[1].split("\n    })", 1)[0]
    assert "cards[next[event.key]].choose.focus()" in keys


def test_the_build_card_says_access_code_required_on_its_face_and_in_its_name():
    strings = _strings()
    assert strings["accessCodeRequired"] == "Access code required"
    ts = _chooser()
    assert "const codeTag = tagChip(strings.accessCodeRequired)" in ts and "codeTag.id = 'chooser-code-tag'" in ts
    assert (
        "card( 2, MEDAL_CAMERA, buildArt, strings.buildCardEyebrow, [tagChip(strings.buildCardTag), codeTag], [strings.buildCardLine], "
        "strings.buildCardPrompt, [codeTag.id], )"
    ) in " ".join(ts.split())
    # The card's name is its title, then its code tag: "Build your own Access code required".
    card = _body(ts, "  function card(")
    assert "choose.setAttribute('aria-labelledby', [title.id, ...named].join(' '))" in card


def test_the_build_back_says_under_the_field_that_the_code_is_in_the_submission():
    strings = _strings()
    assert strings["accessCodeJudges"] == "Judges: the code is in the submission."
    ts = _chooser()
    before, build = ts.split("const buildView = element(", 1)
    build, after = build.split("const views = ", 1)[0].split("\n  )\n", 1)
    assert "const judges = element('p', 'chooser-code-judges body-md', strings.accessCodeJudges)" in before
    assert "element('div', 'chooser-code-form', accessCodeBuild(onAccepted, { heading: false }), judges)" in build
    # The field is described by it too, after its own status line.
    assert "const field = buildView.querySelector(`#${ACCESS_CODE_FIELD}`)" in after
    assert "field?.setAttribute('aria-describedby', `${field.getAttribute('aria-describedby') ?? ''} ${judges.id}`.trim())" in after
    assert _rules()[".chooser-code-judges"]["color"] == "var(--parchment)"


def _px(value: str) -> int:
    return int(re.findall(r"(\d+)px", value)[0])


def test_the_build_back_never_runs_past_its_stage_into_the_key_row():
    # Review X3, measured in the browser on the unfixed panel: at 1024 x 768 the stage is 554 px tall and the Build back
    # 524 px before a check, 588 px with the one-line error banner and 616 px with a two-line warning ("Too many tries",
    # the quota), so it ran up to 62 px under the key row, which is drawn on top.
    text = re.sub(r"/\*.*?\*/", "", (WEB_SRC / "chooser.css").read_text(), flags=re.DOTALL)
    media = r"@media \(max-height: 840px\) \{(.*?\n)\}"
    rules = css_rules(re.sub(media, "", text, flags=re.DOTALL))  # the values above 840 px of window
    short = css_rules("".join(re.findall(media, text, flags=re.DOTALL)))
    panel = rules[".chooser-panel"]
    # Capped at its stage, it scrolls its own body rather than run under the key row, in every state and size.
    assert panel["max-height"] == "100%" and panel["overflow-y"] == "auto"
    # Under 840 px of window the Build back alone tightens (Watch and Play take their height from the stage in layout()),
    # so the field, the banner and "Check code" all show unscrolled at 1024 x 768.
    build = short[".chooser-panel:has(> :not([hidden]) > .chooser-steps)"]
    assert (panel["gap"], build["gap"]) == ("var(--spacing-4)", "var(--spacing-3)")  # two gaps, 16 to 12 px each
    saved = (
        2 * (_px(panel["padding"]) - _px(build["padding-block"]))
        + 2 * (16 - 12)
        + 2 * (_px(rules[".chooser-steps li"]["padding"]) - _px(short[".chooser-steps li"]["padding-block"]))
        + _px(rules[".chooser-vis"]["height"]) - _px(short[".chooser-vis"]["height"])
        + _px(rules[".chooser-step-title"]["margin-top"]) - _px(short[".chooser-step-title"]["margin-top"])
        + 2 * (_px(rules[".chooser-code-box"]["padding"]) - _px(short[".chooser-code-box"]["padding-block"]))
    )
    assert 616 - saved <= 554 - 4, saved
    # The step pictures still fit: the photo thumbnails are 56 px tall.
    assert _px(short[".chooser-vis"]["height"]) >= 56


def test_the_chooser_text_meets_the_reviewer_s_minimum_sizes():
    rules = _rules()
    # Card descriptions: at least 16 px at 1440, growing at 1920.
    for selector in (".chooser-line", ".chooser-meta"):
        size = rules[selector]["font-size"]
        assert _clamp_px(size, CARD_W[1024]) >= 16 and _clamp_px(size, CARD_W[1440]) >= 16, selector
        assert _clamp_px(size, CARD_W[1920]) > _clamp_px(size, CARD_W[1440]), selector
    # Eyebrows and tags at least 13 px, on the cards and on the backs.
    for selector in (".chooser-eyebrow", ".chooser-tag", ".chooser-panel .chooser-tag", ".chooser-panel .chooser-eyebrow"):
        assert all(_clamp_px(rules[selector]["font-size"], w) >= 13 for w in CARD_W.values()), selector
    # Key chips and the Pause motion label at least 14 px, wherever they stand.
    for selector in (".chooser-kbd", ".chooser-keys .chooser-kbd", ".chooser-back .chooser-kbd", ".chooser-still-toggle"):
        assert int(rules[selector]["font-size"].removesuffix("px")) >= 14, selector
    # Voice lines (`wizard-line`, 19 px) and the backs' body (`body-md`, 16 px) at least 16 px; the footer's hints in
    # `body-sm`, 14 px.
    ts = _chooser()
    for made in ("element('p', 'wizard-line', speakerPrefix(wizard)", "element('span', 'chooser-fact body-md', before",
                 "element('span', 'body-md', ROLES[wizard])", "element('span', 'chooser-step-body body-md', body)",
                 "element('p', 'chooser-code-note body-md', strings.accessCodeNote)",
                 "element('p', 'chooser-code-judges body-md', strings.accessCodeJudges)", "element('footer', 'chooser-keys body-sm'"):
        assert made in ts, made


SENTENCES: dict[str, str] = {
    ".chooser-subline": "lamp-lit canvas",
    ".chooser-line": "chrome",
    ".chooser-meta": "chrome",
    ".chooser-voice p": "chrome",
    ".chooser-fact": "chrome-raised",
    ".chooser-hosts span:not(.wizard-portrait, .wizard-portrait *)": "chrome-raised",
    ".chooser-step-body": "chrome-raised",
    ".chooser-code-note": "chrome-raised",
    ".chooser-code-judges": "chrome-raised",
    ".chooser-keys": "canvas",
}
"""Every chooser text the player reads as a sentence, and the ground it sits on."""


def test_every_sentence_reads_in_text_or_parchment_at_7_to_1_and_text_muted_is_left_to_labels():
    rules = _rules()
    canvas = _hex(PROPS["canvas"])[0]
    grounds = {"canvas": canvas, "chrome": _hex(PROPS["chrome"])[0], "chrome-raised": _hex(PROPS["chrome-raised"])[0],
               # the lamp from above at its brightest behind the subline (the beam and the static light, about 30 %)
               "lamp-lit canvas": _mix(_hex(PROPS["lamp"])[0], canvas, 0.3)}
    for selector, ground in SENTENCES.items():
        colour = rules[selector]["color"]
        assert colour in ("var(--text)", "var(--parchment)"), (selector, colour)
        assert contrast(_hex(PROPS[colour[6:-1]])[0], grounds[ground]) >= 7, selector


def test_a_card_stepped_back_keeps_its_text_at_7_to_1():
    rules = _rules()
    chrome, dark = _hex(PROPS["chrome"])[0], _hex("#0a0806")[0]
    plate = {".chooser-line": "parchment", ".chooser-meta": "parchment", ".chooser-eyebrow": "lamp-strong", ".chooser-title": "text"}
    for selector, token in plate.items():
        assert rules[selector]["color"] == f"var(--{token})", selector
    # The shade falls on the face under the plate; the plate's text stays whole, stepped back by hover or at rest.
    assert ".chooser-slot.is-dimmed .chooser-plate" not in rules and ".chooser-slot.is-back .chooser-plate" not in rules
    states = ((float(rules[".chooser-slot.is-dimmed .chooser-dim"]["opacity"]), 1.0), (float(rules[".chooser-slot.is-back .chooser-dim"]["opacity"]), 1.0))
    for dim, shown in states:
        under = _mix(dark, chrome, dim)
        for token in plate.values():
            assert contrast(_mix(_hex(PROPS[token])[0], under, shown), under) >= 7, (token, dim)
        # The tags keep their own ground, dark or (the lamp tag) lamp, the plate's opacity over both words and ground.
        for words, ground in (("text", _hex("#0a0806")[0]), ("on-lamp", _hex(PROPS["lamp-strong"])[0])):
            assert contrast(_mix(_hex(PROPS[words])[0], under, shown), _mix(ground, under, shown)) >= 7, (words, dim)
