"""Story 7.16, owner decisions Oct 28 and Oct 29: the clip of the sample room on the Hosted landing. Since
the chooser (Oct 29) it plays twice: on the Watch card's front as its own derived loop (the Scene photo only, muted,
under a pause toggle) and on the Watch back larger, with native controls, as the demo video until the full one is set.
Autoplaying muted and looping unless reduced motion or Pause motion is set. Owner report Oct 29 ("watch the demo is way
to fast"): it plays at real speed, with time to read each line, and its tags name its real length.

As in test_hosted_landing.py, the client checks read the TypeScript and the stylesheet (the client has no test
runner); the last check serves the committed files from the hosted app with their media types.
"""

import re
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from tests.api.hosted import hosted_handles, make_hosted_app
from tests.web.design import REPO, WEB_SRC, css_rules
from tests.web.test_strings import _section, _strings

CLIP = REPO / "web/public/clip"
ROOM_ID = "room_01M61TZ74F0FP3X9HHTMXGTPB9"
FILES = ("play.webm", "play.mp4", "poster.jpg", "card.webm", "card.mp4", "card-poster.jpg")


def _code(name: str) -> str:
    """A module with its comments removed, so a doc comment never satisfies a check on the code."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", (WEB_SRC / name).read_text(), flags=re.DOTALL)


def _chooser() -> str:
    return _code("chooser.ts")


def _dimensions(mp4: Path) -> tuple[int, int]:
    """The width and height in an MP4's first track header (`tkhd`, version 0, after the 3 x 3 matrix)."""
    data = mp4.read_bytes()
    at = data.index(b"tkhd") + 4
    end = at + (96 if data[at] == 1 else 84)
    width, height = int.from_bytes(data[end - 8 : end - 4]) >> 16, int.from_bytes(data[end - 4 : end]) >> 16
    return width, height


def _seconds(mp4: Path) -> float:
    """The length in an MP4's movie header (`mvhd`, version 0: timescale and duration after the two times)."""
    data = mp4.read_bytes()
    at = data.index(b"mvhd") + 4
    assert data[at] == 0
    timescale, duration = int.from_bytes(data[at + 12 : at + 16]), int.from_bytes(data[at + 16 : at + 20])
    return duration / timescale


def test_the_clip_files_are_committed_under_web_public_clip():
    for stem in ("play", "card"):
        poster = "poster.jpg" if stem == "play" else "card-poster.jpg"
        webm, mp4, still = CLIP / f"{stem}.webm", CLIP / f"{stem}.mp4", CLIP / poster
        assert webm.read_bytes()[:4] == b"\x1a\x45\xdf\xa3"  # EBML: a WebM file
        assert mp4.read_bytes()[4:8] == b"ftyp"
        assert still.read_bytes()[:3] == b"\xff\xd8\xff"
    # Raised from 600 KB (the ten-second cut) to fit the real-speed one (Oct 29): its largest file is play.webm, 691 KB.
    assert all((CLIP / name).stat().st_size < 700_000 for name in FILES)
    # Both are cut from one 2x recording (2560 x 1440 of a 1280 x 720 page), so neither is ever scaled up (Oct 29).
    assert _dimensions(CLIP / "play.mp4") == (1280, 604) and _dimensions(CLIP / "card.mp4") == (630, 840)


def test_one_module_names_the_clip_the_card_loop_and_the_demo_video():
    clip = _code("clip.ts")
    assert f"roomId: '{ROOM_ID}'" in clip
    assert "webm: '/clip/play.webm'" in clip and "mp4: '/clip/play.mp4'" in clip
    assert "poster: '/clip/poster.jpg'" in clip
    # The card's loop is derived from the clip; the lines that make it stay beside it, in its doc comment.
    assert "webm: '/clip/card.webm'" in clip and "mp4: '/clip/card.mp4'" in clip and "poster: '/clip/card-poster.jpg'" in clip
    doc = (WEB_SRC / "clip.ts").read_text()
    assert "crop=2560:1208:0:96" in doc and "crop=630:840:581:170" in doc
    assert "between(n\\,300\\,304)+between(n\\,701\\,705)+between(n\\,896\\,904)" in doc
    # The full demo video is unset for now, so the Watch back falls back to the clip; its aspect sizes the panel.
    assert "const FULL_DEMO_VIDEO: VideoSources | null = null" in clip
    assert "export const DEMO_VIDEO: VideoSources = FULL_DEMO_VIDEO ?? CLIP" in clip
    assert "export const DEMO_VIDEO_ASPECT: number = FULL_DEMO_VIDEO_ASPECT ?? 1280 / 604" in clip


def test_the_clip_plays_at_real_speed_and_its_tags_name_its_length():
    """Owner report Oct 29: "watch the demo is way to fast". Neither video is sped up, so the play runs well past ten
    seconds, and the Watch back's play-through tag reads the clip's own length (the Watch card's tag reads the
    tutorial's since it came first, test_watch_tutorial.py)."""
    clip, card = _seconds(CLIP / "play.mp4"), _seconds(CLIP / "card.mp4")
    assert 30 <= clip <= 50 and 25 <= card < clip
    doc = (WEB_SRC / "clip.ts").read_text()
    assert "setpts=(PTS-STARTPTS)*" not in doc and "setpts=N/30/TB" in doc  # no speed-up factor on either cut
    strings = _strings()
    length = f"{int(round(clip)) // 60}:{int(round(clip)) % 60:02d}"
    assert strings["watchBackTag"] == f"muted · {length}"
    assert not any(re.search(r"\bten\b", strings[key], re.IGNORECASE) for key in ("clipCaption", "clipLabel", "watchCardEyebrow"))


def test_the_clip_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["clipCaption"] == "A play-through of this room."
    assert strings["clipLabel"] == "A play-through of this room: a wrong click, a pickup, a lock opening, the way out."
    voice = _section("Voice and Tone")
    assert strings["clipCaption"] in voice and strings["clipLabel"] in voice
    assert "clipPause" not in strings  # the card's toggle is an icon, named by its accessible name alone


def test_the_watch_card_plays_its_own_loop_muted_and_looping_and_shows_in_every_landing_state():
    chooser = _chooser()
    card = chooser.split("const frontVideo = element('video')", 1)[1].split("const watch = card(", 1)[0]
    for line in ("frontVideo.defaultMuted = true", "frontVideo.muted = true", "frontVideo.loop = true",
                 "frontVideo.playsInline = true", "frontVideo.tabIndex = -1", "hidden(frontVideo)",
                 "sourced(frontVideo, CLIP_CARD)"):
        assert line in card, line
    # It plays only once mounted, with no reduced motion, no Pause motion, no pause of the player's and no card chosen.
    start = chooser.split("function startFrontVideo(): void {", 1)[1].split("\n  }", 1)[0]
    assert "if (!mounted || reduced || still || clipPausedByUser || document.hidden || chosen !== -1) return" in start
    assert "play(frontVideo)" in start
    # The Watch card stands whatever `GET /rooms` answered: it is built before any branch on the rooms.
    assert chooser.index("const watch = card(") < chooser.index("if (first !== undefined) {")
    # webm first, then mp4, with the poster shown until it plays.
    sourced = chooser.split("function sourced(", 1)[1].split("\n}\n", 1)[0]
    assert "video.poster = sources.poster" in sourced
    assert sourced.index("sources.webm, 'video/webm'") < sourced.index("sources.mp4, 'video/mp4'")
    rules = css_rules((WEB_SRC / "chooser.css").read_text())
    assert rules[".chooser-vwin video"]["object-fit"] == "cover" and rules[".chooser-vwin video"]["object-position"] == "50% 40%"


def test_the_watch_back_plays_the_demo_video_larger_with_native_controls():
    """Since the tutorial (Oct 29) the demo video is the Watch back's second tab, "Real play-through"
    (test_watch_tutorial.py checks the tabs)."""
    chooser = _chooser()
    made = chooser.split("function watchVideo(sources: VideoSources, label: string): HTMLVideoElement {", 1)[1].split("\n  }\n", 1)[0]
    for line in ("video.controls = true", "video.muted = true", "video.loop = true", "video.tabIndex = 0",
                 "video.setAttribute('aria-label', label)", "sourced(video, sources)"):
        assert line in made, line
    assert "const panelVideo = watchVideo(DEMO_VIDEO, strings.clipLabel)" in chooser
    assert "const watchTags = [tagChip(strings.tutorialTag), tagChip(strings.watchBackTag)]" in chooser
    assert "watchTitle.textContent = k === 0 ? strings.tutorialCaption : strings.clipCaption" in chooser
    # The selected tab's video plays from the start once the panel is open, never under reduced motion or Pause motion.
    finish = chooser.split("const finish = (): void => {", 1)[1].split("\n    }\n", 1)[0]
    assert "if (i === 0 && !reduced && !still) {\n        watchVideos[watchTab].currentTime = 0\n        play(watchVideos[watchTab])" in finish
    # The panel takes the video's aspect: Watch is as wide as the aspect allows at the panel's height.
    assert "let watchWidth = Math.round(videoHeight * DEMO_VIDEO_ASPECT) + 60" in chooser


def test_the_toggle_strings_are_the_experience_lines():
    strings = _strings()
    assert (strings["clipPauseName"], strings["clipPlayName"]) == ("Pause the clip", "Play the clip")
    row = next(line for line in _section("Voice and Tone").splitlines() if line.startswith("| Watch card"))
    assert all(f'"{strings[key]}"' in row for key in ("clipPauseName", "clipPlayName"))


def test_a_pause_toggle_sits_on_the_watch_card_only_without_reduced_motion():
    """WCAG 2.2.2: a loop over five seconds needs a pause. Under reduced motion the clip waits on its poster."""
    chooser = _chooser()
    assert "clipToggle.type = 'button'" in chooser and "clipToggle.hidden = reduced" in chooser
    assert "watch.front.append(clipToggle)" in chooser
    shown = chooser.split("function showClipState(): void {", 1)[1].split("\n  }", 1)[0]
    assert "clipToggle.setAttribute('aria-label', playing ? strings.clipPauseName : strings.clipPlayName)" in shown
    assert "frontVideo.addEventListener('play', showClipState)" in chooser
    assert "frontVideo.addEventListener('pause', showClipState)" in chooser
    # A pause holds for the page: only the toggle starts the clip again.
    click = chooser.split("clipToggle.addEventListener('click', () => {", 1)[1].split("})", 1)[0]
    assert "clipPausedByUser = !frontVideo.paused" in click and "else play(frontVideo)" in click
    rules = css_rules((WEB_SRC / "chooser.css").read_text())
    toggle = rules[".chooser-clip-toggle"]
    assert toggle["width"] == "36px" and toggle["height"] == "36px" and toggle["pointer-events"] == "auto"
    assert rules[".chooser-clip-toggle[hidden]"] == {"display": "none"}
    # Muted, so its `play()` makes no sound (test_banned_interactions.py allows `video.play()` alone).
    assert "function play(video: HTMLVideoElement): void {\n  void video.play().catch(() => undefined)\n}" in chooser


def test_the_hosted_app_serves_the_clip_files_with_their_media_types(tmp_path: Path):
    dist = tmp_path / "dist"
    (dist / "clip").mkdir(parents=True)
    (dist / "index.html").write_text('<!doctype html><div id="app"></div>')
    for name in FILES:
        shutil.copyfile(CLIP / name, dist / "clip" / name)
    client = TestClient(make_hosted_app(tmp_path, hosted_handles(tmp_path), web_dist=dist))
    media = {".webm": "video/webm", ".mp4": "video/mp4", ".jpg": "image/jpeg"}
    for name in FILES:
        response = client.get(f"/clip/{name}")
        assert response.status_code == 200 and response.headers["content-type"] == media[Path(name).suffix], name
        assert response.content == (CLIP / name).read_bytes()
