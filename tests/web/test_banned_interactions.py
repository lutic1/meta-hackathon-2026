"""UX-DR85 for the client source: no sound, no browser notification, no offline mode.

Walks every module under web/src and the page itself. The other UX-DR85 bans are asserted by the stories that own
each surface.
"""

import re

import pytest

from tests.web.design import REPO, source_css, source_ts

BANS = {
    # `video.play()` is the landing clip's Play toggle; that video is muted (test_landing_clip.py), so it plays no sound.
    # The intro's video starts muted too; its music plays only once the player presses "Sound on" (test_intro.py).
    "plays audio": r"\bnew Audio\(|\bAudioContext\b|\bwebkitAudioContext\b|<audio\b|(?<!\bvideo)\.play\(\)|\bspeechSynthesis\b",
    "uses the Notification API": r"\bNotification\b|\bshowNotification\b|\bpushManager\b",
    "registers a service worker": r"\bserviceWorker\b|\bworkbox\b|\bimportScripts\(|\bCacheStorage\b|\bcaches\.open\(",
}
PAGE = (REPO / "web/index.html").read_text()


def _sources() -> dict[str, str]:
    return {**source_ts(), **source_css(), "web/index.html": PAGE}


@pytest.mark.parametrize("ban", BANS)
def test_no_module(ban):
    for path, text in _sources().items():
        hit = re.search(BANS[ban], text)
        assert hit is None, f"{path} {ban}: {hit.group(0)!r}"


def test_the_page_declares_no_manifest_or_service_worker():
    assert 'rel="manifest"' not in PAGE and "sw.js" not in PAGE
    assert not list((REPO / "web/public").rglob("*.webmanifest")) and not list((REPO / "web/public").glob("sw.js"))


def test_the_bans_catch_each_api():
    assert not re.search(BANS["plays audio"], "void video.play()")
    for sample, ban in (("const a = new Audio('x')", "plays audio"), ("sound.play()", "plays audio"),
                        ("new Notification('x')", "uses the Notification API"),
                        ("navigator.serviceWorker.register('/sw.js')", "registers a service worker")):
        assert re.search(BANS[ban], sample), sample
