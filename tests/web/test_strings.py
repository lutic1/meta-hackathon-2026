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


COMPONENT_PATTERNS_ONLY = {"noRooms", "speakerArchitect", "speakerRiddler", "speakerGuide", "speakerTrickster",
                           "back", "regenerations", "attemptSentBack", "validatorDid", "museImage", "museImageModel",
                           "museImageDid", "guideWritten", "trickster", "submit", "graphNode", "requiresNone",
                           "exit", "guideIntroduction"}
"""Lines EXPERIENCE.md words only in a Component Patterns row (the Stored Room row's empty list, the Wizard
portrait's speaker prefixes, the Build view rows, the Code field's Submit, the puzzle graph node's name, the
First-room welcome's live-region text)."""

STATE_PATTERNS_ONLY = {"buildNotReady", "buildLoadFailed", "resultLoadFailed"}
"""Lines EXPERIENCE.md words only in State Patterns (the Build view's not-ready and error states, the Completion
screen's error state)."""

ACCESSIBILITY_FLOOR_ONLY = {"lockNotThis", "lockOpen"}
"""Lines EXPERIENCE.md words only in the Accessibility Floor (the live-region lines for lock outcomes)."""

UNWORDED = {"photoThumbnail": "Remove photo {n}"}
"""Names EXPERIENCE.md never words, each derived from the Voice and Tone line given: the Thumbnail strip's
"Photo {n}" is the photo tray's remove control without its verb."""


def _section(name: str) -> str:
    return EXPERIENCE.read_text().split(f"\n## {name}\n", 1)[1].split("\n## ", 1)[0]


def _voice_and_tone() -> str:
    return _section("Voice and Tone")


def _component_patterns() -> str:
    return _section("Component Patterns")


def _verbatim(value: str, source: str) -> bool:
    """`value` word for word in `source`, each `{name}` standing where the source shows a placeholder or an example
    ("4.2" for the duration's `{s}`)."""
    pattern = r"(?:\{[^}]+\}|[\w.]+)".join(re.escape(part) for part in re.split(r"\{\w+\}", value))
    return re.search(pattern, source) is not None


def test_every_string_is_verbatim_from_voice_and_tone():
    source = _voice_and_tone()
    for key, value in _strings().items():
        if key in UNWORDED:
            assert UNWORDED[key] in source and UNWORDED[key].removeprefix("Remove p") == value.removeprefix("P"), key
            continue
        if key in COMPONENT_PATTERNS_ONLY:
            assert _verbatim(value, _component_patterns()), f"strings.{key} {value!r} is not verbatim in Component Patterns"
            continue
        if key in STATE_PATTERNS_ONLY:
            assert _verbatim(value, _section("State Patterns")), f"strings.{key} {value!r} is not verbatim in State Patterns"
            continue
        if key in ACCESSIBILITY_FLOOR_ONLY:
            floor = _section("Accessibility Floor")
            assert _verbatim(value, floor), f"strings.{key} {value!r} is not verbatim in the Accessibility Floor"
            continue
        assert _verbatim(value, source), f"strings.{key} {value!r} is not verbatim in EXPERIENCE.md Voice and Tone"


def test_a_placeholder_stands_only_for_a_placeholder_or_an_example():
    assert _verbatim("Regenerations: {n} of {max}", 'reads "Regenerations: n of {max}"')
    assert _verbatim("{n} billed", 'for example "3 billed · 9 cached"')
    assert not _verbatim("Regenerations: {n} of {max}", "Regenerations: none")
    assert _verbatim("{s} s", 'the duration, which reads like "4.2 s"')


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


def test_the_build_view_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["back"] == "Back"
    assert strings["regenerations"].format(n=1, max=2) == "Regenerations: 1 of 2"
    assert strings["attemptSentBack"].format(k=1, messages="A hint gives part of an answer away.") == (
        "Attempt 1 sent back: A hint gives part of an answer away.")
    assert strings["buildNotReady"] == "This room is still being built."
    assert strings["buildLoadFailed"] == "Keyframe couldn't load how this room was built."
    headers = [strings[k] for k in ("modelRole", "modelModel", "modelHost", "modelWhat", "modelBilling")]
    assert headers == ["Role", "Model", "Where it ran", "What it did", "Cached or billed"]
    assert strings["modelCaption"] == ("Cached means an identical earlier call was served from the cache, unbilled; "
                                       "billed means it ran live and was paid for.")
    mixed = strings["modeSeparator"].join([strings["billed"].format(n=3), strings["cached"].format(n=9)])
    assert mixed == "3 billed · 9 cached"
    assert (strings["hostMeta"], strings["hostThisMac"], strings["hostOllama"]) == ("Meta Model API", "this Mac", "Ollama on the Mac")
    assert (strings["validator"], strings["validatorModel"], strings["validatorDid"]) == ("Validator", "code, no model", "checked 8 rules")
    assert strings["dryRun"] == "Dry run"
    assert (strings["museImage"], strings["museImageModel"]) == ("Muse Image", "muse-image-1.0")
    assert strings["museImageDid"] == "painted the four portraits, once"
    assert strings["guideWritten"] == "Hints are shown as written here. In Local mode, Llama 3.2 3B rewords them on the Mac."
    assert (strings["sourceLive"], strings["sourceScripted"], strings["sourceCut1"]) == (
        "Source: live", "Source: scripted", "Source: written in advance")
    assert (strings["architect"], strings["riddler"], strings["guide"], strings["trickster"]) == (
        "The Architect", "The Riddler", "The Guide", "The Trickster")
    name = strings["graphNode"].format(n=5, lockType="code", requires="Puzzle 3 and Puzzle 4", verdict="pass")
    assert f"{name}, {strings['exit']}" == "Puzzle 5, code, requires Puzzle 3 and Puzzle 4, Dry run pass, Exit"
    first = strings["graphNode"].format(n=1, lockType="find", requires=strings["requiresNone"], verdict="skipped")
    assert first == "Puzzle 1, find, requires none, Dry run skipped"


def _code(text: str) -> str:
    """TypeScript with its comments removed, so a doc comment may quote a line it explains."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def test_client_strings_live_only_in_the_strings_module():
    others = {path: _code(text) for path, text in source_ts().items() if not path.endswith("web/src/strings.ts")}
    for key, value in _strings().items():
        if key == "modeSeparator":  # " · " is punctuation, not a line
            continue
        if key == "requiresNone":  # "none" is also the DataTransfer `dropEffect` keyword the drop zone sets
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


def test_the_stage_list_strings_are_the_experience_lines():
    strings = _strings()
    names = [strings[key] for key in ("readingPhotos", "findingObjects", "writingPuzzles", "testingRoom", "sceneLoading")]
    assert names == ["Reading your photos", "Finding objects", "Writing puzzles", "Testing the room", "Setting the scene"]
    for name, stage in zip(names, ("ingest", "architect, segment", "author", "validate, dry run", "scene"), strict=True):
        assert f'"{name}" ({stage})' in _voice_and_tone()
    assert strings["rewritingPuzzles"].format(n=1, max=1) == "Rewriting puzzles, attempt 1 of 1"
    assert strings["sentBack"].format(messages="A puzzle cites something the Architect never saw.") == (
        "Sent back: A puzzle cites something the Architect never saw.")
    assert strings["stageDuration"].format(s="33.1") == "33.1 s"
    assert [strings[key].format(n=8) for key in ("photoCount", "objectCount", "scenesReady")] == [
        "8 photos", "8 objects", "8 scenes ready"]
    assert strings["rulesPassed"].format(passed=8, total=8) == "Rules: 8 of 8 passed"
    assert strings["testRunReached"].format(reached=5, total=5) == "Test run: reached 5 of 5 answers"
    assert strings["playThisRoom"] == "Play this room"


def test_the_wizard_introductions_and_the_architect_lines_are_the_experience_lines():
    strings = _strings()
    assert strings["architectVoice"] == "I notice everything. Mostly mugs."
    assert strings["riddlerVoice"] == "I taught your things to talk. Pity they only speak in riddles."
    assert strings["readingLine"].format(n=8) == "8 photos of one room. Let me find my loupe."
    three = {"n": 9, "first": "mug", "second": "lamp", "third": "books"}
    assert strings["maskPreviewLine"].format(**three) == (
        "I see 9 things worth a closer look, starting with the mug, the lamp and the books.")
    assert strings["maskPreviewLineTwo"].format(**three) == (
        "I see 9 things worth a closer look, starting with the mug and the lamp.")
    assert strings["writingLine"] == "I've handed my notes to the Riddler. Brace yourself."
    assert strings["testingLine"] == "Now we make sure every lock can actually be opened. Fair is fair."
    assert strings["sceneLine"] == "Hanging your room on the wall. Mind the frame."
    assert strings["regenerationLine"] == "The Riddler's draft didn't pass. Another go."


def test_the_welcome_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["guide"] == "The Guide" and strings["begin"] == "Begin"
    assert strings["guideRoleLocal"] == (
        "Reads how you play; offers one hint at a time, never the answer, worded by Llama 3.2 3B on this Mac."
    )
    assert strings["guideRoleWritten"] == "Reads how you play; offers one hint at a time, never the answer, shown as written."
    assert strings["guideVoice"] == "Get stuck as often as you like. I'll help, a little at a time."
    assert strings["guideIntroduction"] == "The Guide. {role line} {opening line} {voice line}"


def test_the_build_end_state_strings_are_the_experience_lines():
    strings = _strings()
    source = _voice_and_tone()
    assert strings["reconnectingBuild"] == (
        "Reconnecting to Keyframe. Your build keeps going; this page catches up when it's back.")
    assert strings["buildStopped"].format(stage="writing puzzles") == "The build stopped while writing puzzles."
    assert '"The build stopped while {stage label, lowercased}."' in source
    assert strings["providerCause"] == "A model service didn't answer."
    assert strings["unexpectedCause"] == "The build stopped unexpectedly."
    assert strings["spendCap"] == "Keyframe has reached its spending limit, so this room can't be built right now."
    assert strings["spendCapBody"] == "Trying again won't help until the limit is raised; your photos are still here."
    assert strings["tooFewObjects"] == "Keyframe found too few objects to build a room."
    assert strings["tooFewObjectsBody"] == (
        "Add a few more photos of this room, closer to shelves and tables, up to 10 in all.")
    assert strings["tooFewObjectsFull"] == (
        "You already have 10 photos. Start over with closer shots of shelves and tables.")
    assert strings["recapture"] == "Keyframe couldn't build a fair room from these photos."
    assert strings["recaptureBody"] == "Try brighter, closer shots where labels and printed text are readable."
    assert (strings["addPhotos"], strings["startOver"], strings["tryAgain"]) == ("Add photos", "Start over", "Try again")
