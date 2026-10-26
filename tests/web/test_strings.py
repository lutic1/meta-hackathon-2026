"""UX-DR73, UX-DR75: one strings module for every client-authored line, each copied verbatim from EXPERIENCE.md
Voice and Tone; the lines the server serves never live in the client."""

import re

from src.api.app import FIRST_ROOM_WELCOME
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


def _voice_and_tone() -> str:
    return EXPERIENCE.read_text().split("\n## Voice and Tone\n", 1)[1].split("\n## Component Patterns\n", 1)[0]


def _component_patterns() -> str:
    return EXPERIENCE.read_text().split("\n## Component Patterns\n", 1)[1].split("\n## ", 1)[0]


def test_every_string_is_verbatim_from_voice_and_tone():
    source = _voice_and_tone()
    for key, value in _strings().items():
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
              RETENTION_LOCAL[:60], FIRST_ROOM_WELCOME, "This room was built earlier", "Hosted mode: hints are shown"]
    for path, text in source_ts().items():
        for line in served:
            assert line not in text, f"{path} holds the served line {line!r}; render it as received"
