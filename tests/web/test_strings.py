"""UX-DR73, UX-DR75: one strings module for every client-authored line, each copied verbatim from EXPERIENCE.md
Voice and Tone; the lines the server serves never live in the client."""

import re

from src.api.app import DEMO_ROOM_WELCOME, FIRST_ROOM_WELCOME
from src.api.meta import CUT1_LINE, RETENTION_LOCAL, SCRIPTED_LINE, TIMESCALE_LINE
from tests.web.design import REPO, WEB_SRC, source_ts

STRINGS = WEB_SRC / "strings.ts"
EXPERIENCE = REPO / "docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/EXPERIENCE.md"
ENTRY = re.compile(r"""^  (\w+): (?:'([^'\\]*)'|"([^"\\]*)"),$""", re.MULTILINE)


def _strings() -> dict[str, str]:
    body = STRINGS.read_text().split("export const strings = {", 1)[1].split("} as const", 1)[0]
    entries = {key: single or double for key, single, double in ENTRY.findall(body)}
    assert len(entries) == len([line for line in body.splitlines() if line.strip()]), "one plain literal per line"
    return entries


COMPONENT_PATTERNS_ONLY = {"noRooms"}
"""Lines EXPERIENCE.md words only in a Component Patterns row (the Stored Room row's empty list)."""
UNWORDED = {"photoThumbnail": "Remove photo {n}"}
"""Names EXPERIENCE.md never words, each derived from the Voice and Tone line given: the Thumbnail strip's
"Photo {n}" is the photo tray's remove control without its verb."""


def _voice_and_tone() -> str:
    return EXPERIENCE.read_text().split("\n## Voice and Tone\n", 1)[1].split("\n## Component Patterns\n", 1)[0]


def _component_patterns() -> str:
    return EXPERIENCE.read_text().split("\n## Component Patterns\n", 1)[1].split("\n## ", 1)[0]


def test_every_string_is_verbatim_from_voice_and_tone():
    source = _voice_and_tone()
    for key, value in _strings().items():
        if key in UNWORDED:
            assert UNWORDED[key] in source and UNWORDED[key].removeprefix("Remove p") == value.removeprefix("P"), key
            continue
        if key in COMPONENT_PATTERNS_ONLY:
            assert value in _component_patterns(), f"strings.{key} {value!r} is not verbatim in Component Patterns"
            continue
        assert value in source, f"strings.{key} {value!r} is not verbatim in EXPERIENCE.md Voice and Tone"


def test_the_stored_room_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["noRooms"] == "No rooms yet." and strings["play"] == "Play"
    assert strings["puzzleCount"].format(n=5) == "5 puzzles"
    assert strings["sessionStartRefused"] == "Keyframe couldn't start this room."
    assert strings["sessionStartRefusedBody"] == "Your room is safe. Try again." and strings["tryAgain"] == "Try again"


def test_the_shell_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["serverUnreachable"] == "Keyframe can't reach its server. Retrying."
    assert strings["wordmark"] == "Keyframe"
    assert (strings["modeLocal"], strings["modeHosted"]) == ("Local mode", "Hosted mode")
    assert (strings["cacheOn"], strings["cacheOff"], strings["modeProfile"]) == ("Cache on", "Cache off", "profile {name}")
    local = strings["modeSeparator"].join([strings["modeLocal"], strings["cacheOn"], strings["modeProfile"].format(name="dev")])
    assert local == "Local mode · Cache on · profile dev"


def test_the_capture_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["inputRequirement"] == "6 to 10 JPEG photos"
    assert strings["iphoneTip"] == "On iPhone, set Settings > Camera > Formats to Most Compatible so photos save as JPEG."
    assert strings["reminder"] == "Leave out faces, documents and other people's belongings."
    assert strings["pickerSentence"] == "Choose 6 to 10 JPEG photos of one room."
    assert (strings["choosePhotos"], strings["upload"]) == ("Choose photos", "Upload")
    assert strings["readingPhotos"] == "Reading your photos"  # the ingest stage name, Upload's pending label
    assert strings["removePhoto"].format(n=3) == "Remove photo 3" and strings["photosChosen"].format(n=8) == "8 photos chosen"
    assert strings["notAJpeg"] == "Not a JPEG"
    assert strings["photosRefused"] == "Keyframe needs 6 to 10 JPEG photos."  # verbatim, FR-1
    assert strings["choosePhotosAgain"] == "Choose photos again"
    assert strings["photosUnreadable"] == "Keyframe couldn't read these photos. Choose them again."
    assert strings["uploadFailed"] == "Your photos didn't reach Keyframe."
    assert strings["uploadFailedBody"] == "Nothing was built. Check the connection and try again."
    assert strings["retentionHeading"] == "Where your photos go." and strings["playHistory"] == "Your play history"
    assert strings["privacyLine"] == "the player profile stays on your machine."  # verbatim, the Privacy line


def _code(text: str) -> str:
    """TypeScript with its comments removed, so a doc comment may quote a line it explains."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def test_client_strings_live_only_in_the_strings_module():
    others = {path: _code(text) for path, text in source_ts().items() if not path.endswith("web/src/strings.ts")}
    for key, value in _strings().items():
        if key == "modeSeparator":  # " · " is punctuation, not a line
            continue
        repeated = re.compile(rf"(?<!\w){re.escape(value)}(?!\w)")  # "Play" as a word, not inside `PlayView`
        for path, text in others.items():
            assert not repeated.search(text), f"{path} repeats {value!r}; import it from strings.ts"


def test_served_lines_are_never_in_the_client():
    served = [TIMESCALE_LINE.split("{n}")[0], TIMESCALE_LINE.split("{n}")[1], SCRIPTED_LINE, CUT1_LINE,
              RETENTION_LOCAL[:60], FIRST_ROOM_WELCOME, DEMO_ROOM_WELCOME, "This room was built earlier", "Hosted mode: hints are shown"]
    for path, text in source_ts().items():
        for line in served:
            assert line not in text, f"{path} holds the served line {line!r}; render it as received"


def test_the_scene_strings_are_the_experience_lines():
    strings = _strings()
    # EXPERIENCE.md words no Scene loading line; it reuses the scene stage's name from the Stage names row.
    assert strings["sceneLoading"] == "Setting the scene" and '"Setting the scene" (scene)' in _voice_and_tone()
    assert strings["photoThumbnail"].format(n=3) == "Photo 3"


def test_the_timer_strings_are_the_experience_lines():
    strings = _strings()
    assert (strings["photosToPlay"], strings["playableIn"]) == ("Photos to play", "Playable in")
    # EXPERIENCE.md words no end status for the Timer; a failed upload shows the name Voice and Tone gives it.
    assert strings["uploadFailedStatus"] == "Upload failed"
    assert "| Upload failed (any other failure of the upload: network, 5xx) |" in _voice_and_tone()
