"""Owner decision Oct 29: a full-screen intro over the Hosted landing on the first visit, once, with Replay and Enter
at its end, remembered in the browser so it never shows by itself again, and a control that reopens it: "Play intro" at
the top bar's right end since the owner's request of Oct 30 (it was "Watch the intro" in the chooser's footer). The owner's own generated teaser, re-encoded under web/public/intro/; its sound starts only when the player turns
it on (the owner's exception to the no-sound rule, DESIGN.md Motion and EXPERIENCE.md Theme and senses).

As in test_landing_clip.py, the client checks read the TypeScript and the stylesheet (the client has no test runner);
the last check serves the committed files from the hosted app with their media types.
"""

import re
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from tests.api.hosted import hosted_handles, make_hosted_app
from tests.web.design import REPO, WEB_SRC, css_rules, design_text
from tests.web.test_landing_clip import _dimensions
from tests.web.test_strings import EXPERIENCE, _section, _strings

INTRO = REPO / "web/public/intro"
FILES = ("intro.webm", "intro.mp4", "intro-poster.jpg")


def _code(name: str) -> str:
    """A module with its comments removed, so a doc comment never satisfies a check on the code."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", (WEB_SRC / name).read_text(), flags=re.DOTALL)


def _body(ts: str, head: str) -> str:
    """The body of the function that starts with `head`, up to its closing brace at the same indent."""
    indent = head[: len(head) - len(head.lstrip())]
    return ts.split(head, 1)[1].split(f"\n{indent}}}\n", 1)[0]


def _intro() -> str:
    return _code("intro.ts")


def test_the_intro_files_are_committed_under_web_public_intro():
    assert (INTRO / "intro.webm").read_bytes()[:4] == b"\x1a\x45\xdf\xa3"  # EBML: a WebM file
    assert (INTRO / "intro.mp4").read_bytes()[4:8] == b"ftyp"
    assert (INTRO / "intro-poster.jpg").read_bytes()[:3] == b"\xff\xd8\xff"
    assert all((INTRO / name).stat().st_size < 3_000_000 for name in FILES)
    assert _dimensions(INTRO / "intro.mp4") == (1280, 720)
    # Faststart: the index comes before the media, so the intro starts before the whole file is in.
    mp4 = (INTRO / "intro.mp4").read_bytes()
    assert mp4.index(b"moov") < mp4.index(b"mdat")


def test_one_module_names_the_intro_files_and_the_lines_that_made_them():
    intro = _intro()
    assert "webm: '/intro/intro.webm'" in intro and "mp4: '/intro/intro.mp4'" in intro
    assert "poster: '/intro/intro-poster.jpg'" in intro
    doc = (WEB_SRC / "intro.ts").read_text()
    assert "-c:v libx264 -pix_fmt yuv420p -crf 23" in doc and "-c:a aac -b:a 128k -movflags +faststart" in doc
    assert "-c:v libvpx-vp9 -b:v 0 -crf 34 -row-mt 1" in doc and "-c:a libopus -b:a 96k" in doc


def test_the_intro_strings_are_the_experience_lines():
    strings = _strings()
    expected = {
        "introLabel": "Keyframe intro",
        "introSoundOn": "Sound on",
        "introSoundOff": "Sound off",
        "introSkip": "Skip intro",
        "introReplay": "Replay",
        "introEnter": "Enter Keyframe",
        "introCountdown": "Entering in {n}…",
        "playIntro": "Play intro",
    }
    assert {key: strings.get(key) for key in expected} == expected
    assert "watchIntro" not in strings  # the footer's "Watch the intro" went with the top-right button
    voice = _section("Voice and Tone")
    assert "| Intro (full screen, the first visit" in voice


def test_the_first_visit_to_the_landing_shows_it_and_the_stored_flag_skips_it():
    intro = _intro()
    assert "export const INTRO_SEEN_KEY = 'keyframe.introSeen.v1'" in intro
    due = _body(intro, "export function introDue(reduced: boolean): boolean {")
    assert "return OPENED_ON_HOME && !reduced && !introSeen()" in due
    seen = _body(intro, "function introSeen(): boolean {")
    assert "localStorage.getItem(INTRO_SEEN_KEY) === 'yes'" in seen and "} catch {" in seen
    assert "if (seenThisLoad) return true" in seen  # storage refused: at most once per page load
    mark = _body(intro, "function markIntroSeen(): void {")
    assert "seenThisLoad = true" in mark and "localStorage.setItem(INTRO_SEEN_KEY, 'yes')" in mark and "} catch {" in mark
    # The chooser opens it on mount, by itself only when due.
    chooser = _code("chooser.ts")
    mount = chooser.split("    mount() {", 1)[1]
    assert "if (introDue(reduced)) introShown = openIntro(true)" in mount


def test_a_deep_link_never_shows_it():
    # Only a page load that opened on the landing's route; `#/play/…`, `#/build/…` and `#/done/…` load other surfaces.
    intro = _intro()
    assert "const OPENED_ON_HOME = parsePlace(location.hash, location.search).route.name === 'home'" in intro
    # The landing is Hosted `#/` only, so Local mode never mounts the chooser.
    assert "introDue" not in _code("shell.ts") and "introDue" not in _code("capture.ts")


def test_the_chooser_deals_in_only_once_the_intro_is_gone():
    chooser = _code("chooser.ts")
    mount = chooser.split("    mount() {", 1)[1]
    assert "Promise.all([document.fonts.ready, introShown?.closed])" in mount
    assert mount.index("if (introDue(reduced)) introShown = openIntro(true)") < mount.index("Promise.all(")
    teardown = mount.split("return () => {", 1)[1]
    assert "introShown?.remove()" in teardown


def test_skip_and_enter_set_the_flag_and_fade_the_overlay_out():
    intro = _intro()
    close = _body(intro, "  function close(fade: boolean): void {")
    assert "markIntroSeen()" in close
    assert "overlay.animate([{ opacity: 1 }, { opacity: 0 }], { duration: FADE_OUT_MS, easing: 'ease-out', fill: 'forwards' })" in close
    assert "const FADE_OUT_MS = 600" in intro
    assert "skip.addEventListener('click', () => close(true))" in intro
    assert "primaryButton({ label: strings.introEnter, pendingLabel: strings.introEnter, onActivate: async () => close(true) })" in intro
    ended = intro.split("video.addEventListener('ended', () => {", 1)[1].split("\n  })", 1)[0]
    assert "markIntroSeen()" in ended and "showEnd()" in ended
    # Escape skips while it plays and enters at its end.
    keys = _body(intro, "  function onKey(event: KeyboardEvent): void {")
    assert "if (event.key === 'Escape') {" in keys and "close(true)" in keys


def test_the_end_counts_down_and_enters_unless_replay_is_chosen():
    intro = _intro()
    assert "const COUNTDOWN_S = 4" in intro
    end = _body(intro, "  function showEnd(): void {")
    assert "if (!counting) return" in end
    assert "countdown.textContent = fill(strings.introCountdown, { n: left })" in end
    assert "if (left === 0) close(true)" in end
    assert "secondaryButton({ label: strings.introReplay, onActivate: restart })" in intro
    replay = _body(intro, "  function restart(): void {")
    assert "counting = false" in replay and "clearInterval(ticker)" in replay
    assert "video.currentTime = 0" in replay and "close(" not in replay
    # Only the intro that showed by itself counts down; reopened by hand it waits on Replay and Enter.
    assert "let counting = first" in intro


def test_reduced_motion_skips_the_auto_show_and_the_control_reopens_it_with_native_controls():
    intro = _intro()
    assert "video.controls = reduced" in intro and "sound.hidden = reduced" in intro
    assert "if (!reduced) video.play().catch(() => close(false))" in intro
    # The native control bar runs along the bottom, so "Skip intro" moves to the top right, where "Sound on" would be.
    assert "overlay.classList.toggle('is-reduced', reduced)" in intro
    rules = css_rules((WEB_SRC / "intro.css").read_text())
    assert rules[".intro-skip"]["bottom"] == "var(--spacing-5)"
    assert rules[".intro.is-reduced .intro-skip"] == {"top": "var(--spacing-5)", "bottom": "auto"}
    chooser = _code("chooser.ts")
    assert "const introButton = secondaryButton({ label: strings.playIntro, onActivate: () => reopenIntro() })" in chooser
    assert "introShown = openIntro(false)" in _body(chooser, "  function reopenIntro(): void {")
    assert "introButton.hidden" not in chooser  # shown under reduced motion too: the player asked for it


def test_play_intro_sits_at_the_top_bar_s_right_end_on_the_landing_and_every_back():
    """Owner request Oct 30: "a button on the top right that says play Intro". It is the play screen's quiet top-bar
    button (fix D12), put in the top bar's controls slot by the landing's chooser alone, so it shows on the landing and
    on every card back and on no other screen; it opens the same overlay the footer's "Watch the intro" did, which goes.
    Open on a back, the dialog leaves it out of the inert top bar and its Tab ring takes it after the panel's controls;
    while the intro shows, the chooser's own keys wait and the videos behind it pause, so no two play at once."""
    chooser = _code("chooser.ts")
    mount = chooser.split("    mount() {", 1)[1]
    assert "document.querySelector<HTMLElement>('.top-bar-controls')?.append(introButton)" in mount
    assert "introButton.remove()" in mount.split("return () => {", 1)[1]
    assert "element('footer', 'chooser-keys body-sm', hints, element('div', 'chooser-keys-end', stillToggle))" in chooser
    css = (WEB_SRC / "chooser.css").read_text()
    assert "chooser-intro-toggle" not in chooser and "chooser-intro-toggle" not in css
    assert ".top-bar-controls > .button-secondary" in (WEB_SRC / "components/top-bar.css").read_text()
    outside = _body(chooser, "  function outside(): HTMLElement[] {")
    assert "!node.contains(introButton)" in outside
    trap = _body(chooser, "  function trapTab(event: KeyboardEvent): void {")
    assert "const ring = introButton.isConnected ? [...controls, introButton] : controls" in trap
    assert "if (introOpen) return" in _body(chooser, "  function onKey(event: KeyboardEvent): void {")
    reopen = _body(chooser, "  function reopenIntro(): void {")
    for line in ("introOpen = true", "for (const video of [frontVideo, tutorialVideo, panelVideo, playVideo]) video.pause()",
                 "introOpen = false", "startFrontVideo()"):
        assert line in reopen, line
    for name in ("shell.ts", "play.ts", "capture.ts", "build-view.ts", "completion.ts", "landing.ts"):
        assert "strings.playIntro" not in _code(name), name
    experience = EXPERIENCE.read_text()
    assert '"Play intro"' in experience and "Watch the intro" not in experience
    rows = [line for line in experience.splitlines() if '"Play intro"' in line]
    assert rows and all("(amended 30 Oct 2026, owner request)" in row for row in rows)
    assert '"Play intro"' in design_text() and "Watch the intro" not in design_text()

def test_a_video_that_cannot_play_falls_through_to_the_landing():
    intro = _intro()
    assert "last.addEventListener('error', () => close(false))" in intro
    assert "video.addEventListener('error', () => close(false))" in intro
    close = _body(intro, "  function close(fade: boolean): void {")
    assert "if (fade && !reduced)" in close and "else done()" in close


def test_the_overlay_is_a_named_modal_that_traps_focus_and_starts_muted():
    intro = _intro()
    assert "overlay.setAttribute('role', 'dialog')" in intro and "overlay.setAttribute('aria-modal', 'true')" in intro
    assert "overlay.setAttribute('aria-label', strings.introLabel)" in intro
    assert "video.muted = true" in intro
    toggle = intro.split("sound.addEventListener('click', () => {", 1)[1].split("\n  })", 1)[0]
    assert "video.muted = !video.muted" in toggle
    assert "sound.textContent = video.muted ? strings.introSoundOn : strings.introSoundOff" in toggle
    keys = _body(intro, "  function onKey(event: KeyboardEvent): void {")
    assert "event.key === 'Tab'" in keys
    # Everything else in the page is inert while it shows, and focus returns to where it was.
    assert "for (const node of others) node.inert = true" in intro
    done = _body(intro, "  function done(): void {")
    assert "overlay.remove()" in done and "node.inert = false" in done and "previous" in done


def test_the_overlay_covers_the_viewport_on_black_and_letterboxes_an_extreme_aspect():
    rules = css_rules((WEB_SRC / "intro.css").read_text())
    overlay = rules[".intro"]
    assert overlay["position"] == "fixed" and overlay["inset"] == "0" and overlay["background"] == "#000"
    text = (WEB_SRC / "intro.css").read_text()
    assert ".intro-video {\n  display: block;\n  width: 100%;\n  height: 100%;\n  object-fit: cover;\n}" in text
    assert "@media (min-aspect-ratio: 21/9), (max-aspect-ratio: 5/4)" in text
    assert re.search(r"min-aspect-ratio: 21/9\), \(max-aspect-ratio: 5/4\) \{\s*\.intro-video \{\s*object-fit: contain;", text)


def test_the_docs_record_the_owner_exception_for_the_intro_and_its_sound():
    design = design_text()
    assert "**Owner exception: the intro (Oct 29).**" in design
    experience = EXPERIENCE.read_text()
    assert "the full-screen intro (owner decision Oct 29" in experience
    assert "No sound in v1, except the intro's" in experience and "No sound in v1, except the intro's" in design


def test_the_hosted_app_serves_the_intro_files_with_their_media_types(tmp_path: Path):
    dist = tmp_path / "dist"
    (dist / "intro").mkdir(parents=True)
    (dist / "index.html").write_text('<!doctype html><div id="app"></div>')
    for name in FILES:
        shutil.copyfile(INTRO / name, dist / "intro" / name)
    client = TestClient(make_hosted_app(tmp_path, hosted_handles(tmp_path), web_dist=dist))
    media = {".webm": "video/webm", ".mp4": "video/mp4", ".jpg": "image/jpeg"}
    for name in FILES:
        response = client.get(f"/intro/{name}")
        assert response.status_code == 200 and response.headers["content-type"] == media[Path(name).suffix], name
        assert response.content == (INTRO / name).read_bytes()
