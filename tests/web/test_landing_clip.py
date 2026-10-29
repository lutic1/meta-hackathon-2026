"""Story 7.16, owner decision Oct 28: a ten-second clip of the sample room on the Hosted landing, under "How to play",
so a judge sees the game played before clicking. Shown only when the first Demo room is the room the clip shows;
autoplaying muted and looping unless reduced motion is set, then paused with native controls over its poster.

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


def _code(name: str) -> str:
    """A module with its comments removed, so a doc comment never satisfies a check on the code."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", (WEB_SRC / name).read_text(), flags=re.DOTALL)


def _clip_figure() -> str:
    return _code("components/sample-clip.ts").split("export function sampleClip(", 1)[1]


def test_the_clip_files_are_committed_under_web_public_clip():
    webm, mp4, poster = (CLIP / name for name in ("play.webm", "play.mp4", "poster.jpg"))
    assert webm.read_bytes()[:4] == b"\x1a\x45\xdf\xa3"  # EBML: a WebM file
    assert mp4.read_bytes()[4:8] == b"ftyp"
    assert poster.read_bytes()[:3] == b"\xff\xd8\xff"
    assert all(path.stat().st_size < 600_000 for path in (webm, mp4, poster))


def test_one_module_names_the_room_the_clip_shows_and_its_three_files():
    clip = _code("clip.ts")
    assert f"roomId: '{ROOM_ID}'" in clip
    assert "webm: '/clip/play.webm'" in clip and "mp4: '/clip/play.mp4'" in clip
    assert "poster: '/clip/poster.jpg'" in clip


def test_the_clip_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["clipCaption"] == "Ten seconds in this room."
    assert strings["clipLabel"] == (
        "A ten-second play-through of this room: a wrong click, a pickup, a lock opening, the way out.")
    voice = _section("Voice and Tone")
    assert strings["clipCaption"] in voice and strings["clipLabel"] in voice


def test_the_figure_shows_only_when_the_first_demo_room_is_the_clip_s_room():
    landing = _code("landing.ts")
    listed = landing.split("const cards: DemoRoomCard[]", 1)[1]
    assert "stage.append(attract, howToPlay())\n  if (first.room_id === CLIP.roomId) stage.append(sampleClip())" in listed
    # Never on the failed or empty paths, which return before the listed branch.
    before = landing.split("const cards: DemoRoomCard[]", 1)[0]
    assert "sampleClip(" not in before.split("export function hostedLanding(", 1)[1]
    assert landing.count("sampleClip()") == 1
    assert "import { CLIP } from './clip.ts'" in landing
    assert "import { sampleClip } from './components/sample-clip.ts'" in landing
    assert "import { CLIP } from '../clip.ts'" in _code("components/sample-clip.ts")


def test_the_video_autoplays_muted_and_looping_only_without_reduced_motion():
    figure = _clip_figure()
    assert "const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches" in figure
    assert "video.autoplay = !reduced" in figure and "video.controls = reduced" in figure
    assert "video.muted = true" in figure and "video.defaultMuted = true" in figure
    assert "video.loop = true" in figure and "video.playsInline = true" in figure
    assert "video.preload = 'metadata'" in figure and "video.poster = CLIP.poster" in figure
    assert "video.setAttribute('aria-label', strings.clipLabel)" in figure


def test_the_webm_source_comes_first_and_a_failed_load_removes_the_figure():
    figure = _clip_figure()
    assert "const mp4 = source(CLIP.mp4, 'video/mp4')" in figure
    assert "video.append(source(CLIP.webm, 'video/webm'), mp4)" in figure
    # A failed <source> fires its error on the source, never on the video; the last one failing means none played.
    assert "mp4.addEventListener('error', () => element.remove())" in figure
    assert "video.addEventListener('error', () => element.remove())" in figure
    assert "element.className = 'landing-clip'" in figure
    assert "caption.className = 'landing-clip-caption label'" in figure and "caption.textContent = strings.clipCaption" in figure


def test_the_figure_sits_in_the_stage_s_second_column_under_how_to_play_with_no_shift_while_it_loads():
    rules = css_rules((WEB_SRC / "landing.css").read_text())
    figure = rules[".landing-clip"]
    assert figure["grid-column"] == "2" and figure["grid-row"] == "3"
    video = rules[".landing-clip-video"]
    assert video["aspect-ratio"] == "960 / 454" and video["width"] == "100%" and video["box-sizing"] == "border-box"
    assert video["border"] == "1px solid var(--gilt)" and video["border-radius"] == "var(--rounded-sm)"
    # Only with the clip does the stage take a third row and the frame span it; without it, the layout is unchanged.
    assert rules[".landing-stage:has(> .landing-clip)"] == {"grid-template-rows": "auto auto 1fr"}
    assert rules[".landing-stage:has(> .landing-clip) .attract-frame"] == {"grid-row": "1 / span 3"}
    assert rules[".landing-stage"]["grid-template-rows"] == "auto 1fr"
    assert rules[".landing-stage .attract-frame"]["grid-row"] == "1 / span 2"


def test_the_hosted_app_serves_the_clip_files_with_their_media_types(tmp_path: Path):
    dist = tmp_path / "dist"
    (dist / "clip").mkdir(parents=True)
    (dist / "index.html").write_text('<!doctype html><div id="app"></div>')
    for name in ("play.webm", "play.mp4", "poster.jpg"):
        shutil.copyfile(CLIP / name, dist / "clip" / name)
    client = TestClient(make_hosted_app(tmp_path, hosted_handles(tmp_path), web_dist=dist))
    for name, media in (("play.webm", "video/webm"), ("play.mp4", "video/mp4"), ("poster.jpg", "image/jpeg")):
        response = client.get(f"/clip/{name}")
        assert response.status_code == 200 and response.headers["content-type"] == media, name
        assert response.content == (CLIP / name).read_bytes()
