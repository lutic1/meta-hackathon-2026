"""Owner decision Oct 29: the Watch back opens on a captioned tutorial. The owner's own generated ten-second video, slowed
to half speed (20 s), its sound dropped and five short captions burned in, plays under a "Tutorial" tab, selected first;
a "Real play-through" tab holds the recorded play-through of the real room (`DEMO_VIDEO`). The Watch card's front keeps
its own loop of the real room; its line promises both and its tag reads the tutorial's length.

As in test_landing_clip.py, the client checks read the TypeScript (the client has no test runner); the last check
serves the committed files from the hosted app with their media types.
"""

import re
import shutil
from pathlib import Path

from fastapi.testclient import TestClient

from tests.api.hosted import hosted_handles, make_hosted_app
from tests.web.design import REPO, WEB_SRC, design_text
from tests.web.test_landing_clip import _dimensions, _seconds
from tests.web.test_strings import EXPERIENCE, _section, _strings

TUTORIAL = REPO / "web/public/tutorial"
FILES = ("tutorial.webm", "tutorial.mp4", "tutorial-poster.jpg")
LINES = (
    "Snap a room. Your photos become the game.",
    "Read a riddle, then click the thing it means.",
    "Pick things up. They wait in your inventory.",
    "Use them where they belong to open the locks.",
    "Open the last lock and walk out.",
)


def _code(name: str) -> str:
    """A module with its comments removed, so a doc comment never satisfies a check on the code."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", (WEB_SRC / name).read_text(), flags=re.DOTALL)


def _body(ts: str, head: str) -> str:
    """The body of the function that starts with `head`, up to its closing brace at the same indent."""
    indent = head[: len(head) - len(head.lstrip())]
    return ts.split(head, 1)[1].split(f"\n{indent}}}\n", 1)[0]


def test_the_tutorial_files_are_committed_under_web_public_tutorial():
    assert (TUTORIAL / "tutorial.webm").read_bytes()[:4] == b"\x1a\x45\xdf\xa3"  # EBML: a WebM file
    mp4 = (TUTORIAL / "tutorial.mp4").read_bytes()
    assert mp4[4:8] == b"ftyp"
    assert (TUTORIAL / "tutorial-poster.jpg").read_bytes()[:3] == b"\xff\xd8\xff"
    assert all((TUTORIAL / name).stat().st_size < 3_000_000 for name in FILES)
    assert _dimensions(TUTORIAL / "tutorial.mp4") == (1280, 720)
    assert mp4.index(b"moov") < mp4.index(b"mdat")  # faststart
    # Half speed: the ten-second source runs 20 s; its sound is dropped (it would be distorted), so no audio track.
    assert 19.5 <= _seconds(TUTORIAL / "tutorial.mp4") <= 20.5
    assert b"soun" not in mp4[: mp4.index(b"mdat")]


def test_one_module_names_the_tutorial_files_and_the_lines_that_made_them():
    clip = _code("clip.ts")
    assert "webm: '/tutorial/tutorial.webm'" in clip and "mp4: '/tutorial/tutorial.mp4'" in clip
    assert "poster: '/tutorial/tutorial-poster.jpg'" in clip
    doc = (WEB_SRC / "clip.ts").read_text()
    # Plain half speed (motion interpolation warped the door and the outline on this footage), captions burned in.
    assert 'VF="setpts=2.0*PTS,fps=30,ass=tutorial.ass:fontsdir=fonts"' in doc
    assert "-an -c:v libx264 -pix_fmt yuv420p -crf 24 -preset slow -movflags +faststart tutorial.mp4" in doc
    assert "-an -c:v libvpx-vp9 -b:v 0 -crf 34 -row-mt 1 -pix_fmt yuv420p tutorial.webm" in doc
    # The five captions, in order, each with its own time, faded in and out over 250 ms, never two at once.
    times = re.findall(r"(\d+\.\d\d)-(\d+\.\d\d) s +(.+)", doc)
    assert [line for _, _, line in times] == list(LINES)
    spans = [(float(start), float(end)) for start, end, _ in times]
    assert all(end - start >= 2 for start, end in spans) and spans[-1][1] <= 20
    assert all(spans[k][1] < spans[k + 1][0] for k in range(len(spans) - 1))
    assert "\\fad(250,250)" in doc and "EB Garamond Medium" in doc


def test_the_tutorial_strings_are_the_experience_lines():
    strings = _strings()
    assert [strings[f"tutorialLine{n}"] for n in range(1, 6)] == list(LINES)
    assert (strings["watchTabTutorial"], strings["watchTabPlayThrough"]) == ("Tutorial", "Real play-through")
    assert strings["tutorialTag"] == "captioned · 0:20"
    voice = _section("Voice and Tone")
    row = next(line for line in voice.splitlines() if line.startswith("| Watch back"))
    for key in ("watchTabs", "watchTabTutorial", "watchTabPlayThrough", "tutorialCaption", "tutorialTag", "tutorialLabel",
                "clipCaption", "watchBackTag", "clipLabel", *(f"tutorialLine{n}" for n in range(1, 6))):
        assert f'"{strings[key]}"' in row, key


def test_the_watch_card_promises_both_and_its_tag_reads_the_tutorial_length():
    strings = _strings()
    seconds = round(_seconds(TUTORIAL / "tutorial.mp4"))
    assert strings["watchCardTag"] == f"{seconds // 60}:{seconds % 60:02d}"
    assert "tutorial" in strings["watchCardLine"] and "played" in strings["watchCardLine"]
    assert "play-through" not in strings["watchCardEyebrow"].lower() or "tutorial" in strings["watchCardEyebrow"].lower()
    # The card's front still loops the real room.
    assert "sourced(frontVideo, CLIP_CARD)" in _code("chooser.ts")


def test_the_watch_back_is_a_tablist_with_the_tutorial_selected_first():
    ts = _code("chooser.ts")
    assert "const tutorialVideo = watchVideo(TUTORIAL, strings.tutorialLabel)" in ts
    assert "const panelVideo = watchVideo(DEMO_VIDEO, strings.clipLabel)" in ts
    made = _body(ts, "  function watchVideo(sources: VideoSources, label: string): HTMLVideoElement {")
    for line in ("video.controls = true", "video.defaultMuted = true", "video.muted = true", "video.playsInline = true",
                 "video.tabIndex = 0", "video.setAttribute('aria-label', label)", "sourced(video, sources)"):
        assert line in made, line
    assert "tablist.setAttribute('role', 'tablist')" in ts and "tablist.setAttribute('aria-label', strings.watchTabs)" in ts
    assert "tab.setAttribute('role', 'tab')" in ts and "box.setAttribute('role', 'tabpanel')" in ts
    assert "tab.setAttribute('aria-controls', box.id)" in ts and "box.setAttribute('aria-labelledby', tab.id)" in ts
    show = _body(ts, "  function showTab(k: number): void {")
    assert "tab.setAttribute('aria-selected', String(n === k))" in show and "tab.tabIndex = n === k ? 0 : -1" in show
    assert "watchBoxes[n].hidden = n !== k" in show and "if (n !== k) watchVideos[n].pause()" in show
    assert "let watchTab = 0" in ts and "showTab(watchTab)" in ts
    # Arrow keys move between the tabs (wrapping), Home and End to the first and last; each move selects and focuses.
    keys = ts.split("tab.addEventListener('keydown', (event) => {", 1)[1].split("\n    })", 1)[0]
    for key in ("ArrowRight", "ArrowLeft", "Home", "End"):
        assert key in keys, key
    assert "selectTab(next[event.key], true)" in keys


def test_the_tutorial_is_described_by_its_five_captions():
    ts = _code("chooser.ts")
    assert "const tutorialLines = [strings.tutorialLine1, strings.tutorialLine2, strings.tutorialLine3, strings.tutorialLine4, strings.tutorialLine5]" in ts
    assert "tutorialVideo.setAttribute('aria-describedby', described.id)" in ts
    assert "const described = element('p', '', tutorialLines.join(' '))" in ts and "described.hidden = true" in ts


def test_the_selected_video_plays_once_the_panel_is_open_and_every_pause_holds_both():
    ts = _code("chooser.ts")
    finish = ts.split("const finish = (): void => {", 1)[1].split("\n    }\n", 1)[0]
    assert "if (i === 0 && !reduced && !still) {\n        watchVideos[watchTab].currentTime = 0\n        play(watchVideos[watchTab])" in finish
    assert "const target = i === 0 ? watchVideos[watchTab] : i === 1 ? playFocus" in ts
    still = ts.split("stillToggle.addEventListener('click', () => {", 1)[1].split("\n  })", 1)[0]
    home = _body(ts, "  function goHome(then?: () => void): void {")
    teardown = ts.split("      return () => {\n        mounted = false", 1)[1]
    for block in (still, home, teardown):
        assert "tutorialVideo.pause()" in block and "panelVideo.pause()" in block


def test_the_docs_record_the_tutorial():
    experience = EXPERIENCE.read_text()
    assert "the captioned tutorial (owner decision Oct 29" in experience
    assert "| Watch back (the tabs" in experience
    assert "**Owner decision: the tutorial (Oct 29).**" in design_text()


def test_the_hosted_app_serves_the_tutorial_files_with_their_media_types(tmp_path: Path):
    dist = tmp_path / "dist"
    (dist / "tutorial").mkdir(parents=True)
    (dist / "index.html").write_text('<!doctype html><div id="app"></div>')
    for name in FILES:
        shutil.copyfile(TUTORIAL / name, dist / "tutorial" / name)
    client = TestClient(make_hosted_app(tmp_path, hosted_handles(tmp_path), web_dist=dist))
    media = {".webm": "video/webm", ".mp4": "video/mp4", ".jpg": "image/jpeg"}
    for name in FILES:
        response = client.get(f"/tutorial/{name}")
        assert response.status_code == 200 and response.headers["content-type"] == media[Path(name).suffix], name
        assert response.content == (TUTORIAL / name).read_bytes()
