"""Decision record Oct 29, items 62, 66, 70 and 71: player wording everywhere. The access-code card says what it is
doing and why a check failed, with the server's own count; no raw job status reaches the Timer; counts take their
singular; every shown build time is the Room's `created` in ET; the Model table claims only what the Build did.

The client has no test runner, so these checks read the TypeScript; the browser run proves them on screen.
"""

import re

from tests.web.design import WEB_SRC
from tests.web.test_strings import _strings, _voice_and_tone


def _code(name: str) -> str:
    """A module with its comments removed, so a doc comment never satisfies a check on the code."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", (WEB_SRC / name).read_text(), flags=re.DOTALL)


# --- Item 66: the access-code card ---------------------------------------------------------


def test_the_access_code_card_strings_are_the_decided_lines():
    strings = _strings()
    assert strings["checkingCode"] == "Checking code…"
    assert strings["accessCodeRefused"] == "That code doesn't open anything."
    assert strings["accessCheckFailed"] == "We couldn't check the code. Try again."


def test_the_check_shows_checking_code_while_pending_and_never_fails_silently():
    panel = _code("components/access-code-build.ts")
    assert "primaryButton({ label: strings.checkCode, pendingLabel: strings.checkingCode, onActivate: check })" in panel
    assert "checkFailed: BannerState = { variant: 'error', heading: strings.accessCheckFailed, actions: [], compact: true }" in panel
    caught = panel.split("answer = await checkAccess(code)", 1)[1].split("} catch (error) {", 1)[1].split("return", 1)[0]
    # Every failure of the check shows a banner: 429 its own warning, anything else (no answer, a 5xx) the failed check.
    assert "showBanner(banners, error instanceof RequestFailed && error.status === TOO_MANY_ATTEMPTS ? tooManyTries : checkFailed)" in caught


def test_the_capture_screen_shows_the_builds_left_the_server_counts_now():
    holder = _code("access-code.ts")
    # No count kept and decremented in the tab: the accepting check's answer once, then the server asked again.
    assert "claimJudgeBuild" not in holder and "left - 1" not in holder
    assert "held = code\n  fresh = buildsLeft" in holder
    left = holder.split("export async function judgeBuildsLeft(): Promise<number | null> {", 1)[1].split("\n}\n", 1)[0]
    assert "const answer = await checkAccess(held)" in left and "return answer.ok ? answer.builds_left : null" in left
    for name in ("capture.ts", "build-progress.ts"):
        assert "claimJudgeBuild" not in _code(name), name
    assert "place.route.name === 'buildYourOwn' ? await judgeBuildsLeft() : null" in _code("shell.ts")


# --- Item 62: statuses and plurals ------------------------------------------------------


def test_the_timer_names_every_status_in_player_words():
    strings = _strings()
    assert strings["timerQueued"] == "Waiting to build"
    assert (strings["timerFailed"], strings["timerMorePhotos"], strings["timerRecapture"]) == (
        "Build stopped", "Add more photos", "Try clearer photos")
    timer = _code("capture-timer.ts")
    assert "failed: strings.timerFailed" in timer
    assert "needs_more_photos: strings.timerMorePhotos" in timer and "needs_recapture: strings.timerRecapture" in timer
    ended = timer.split("export function buildEnded(", 1)[1].split("\n}\n", 1)[0]
    assert "stopTimer(END_STATUS[status])" in ended
    # The face prints only those words: the queued line in place of the digits, an end status as it was stopped.
    face = _code("components/timer.ts")
    assert "digits.textContent = queued ? strings.timerQueued : formatElapsed(face.elapsedMs)" in face
    assert "if (face.kind === 'ended') status.textContent = face.status" in face


def test_no_string_carries_an_assumption_marker_or_a_raw_status():
    for key, value in _strings().items():
        assert "ASSUMPTION" not in value and "[" not in value, key
        assert not re.search(r"\b(needs_recapture|needs_more_photos|queued|running)\b", value), key


def test_every_count_has_its_singular():
    strings = _strings()
    assert (strings["onePuzzle"], strings["onePhotoChosen"]) == ("1 puzzle", "1 photo chosen")
    assert strings["demoRoomMeta"] == "{puzzles} · 15 to 25 min"
    assert strings["howRiddler"].startswith("writes {locks} from what was found;")
    singular = "{n} === 1 ? strings.{one} : fill(strings.{many}, {{ n: {n} }})"
    assert singular.format(n="room.puzzle_count", one="onePuzzle", many="puzzleCount") in _code("components/stored-room-row.ts")
    tray = _code("components/photo-tray.ts")
    for n in ("photos.length", "urls.length"):
        assert singular.format(n=n, one="onePhotoChosen", many="photosChosen") in tray
    card = _code("components/demo-room-card.ts")
    assert "const puzzles = " + singular.format(n="room.puzzle_count", one="onePuzzle", many="puzzleCount") in card
    assert "fill(strings.demoRoomMeta, { puzzles })" in card
    stages = _code("build-stages.ts")
    assert "if (kind === 'writing') return counted(strings.puzzleCount, count('author'), strings.onePuzzle)" in stages
    landing = _code("landing.ts")
    assert "fill(strings.howRiddler, { locks: locks === 1 ? strings.oneLock : fill(strings.locksCount, { n: locks }) })" in landing


# --- Item 71: one time zone for every shown build time ------------------------------------


def test_every_build_time_is_formatted_in_et():
    header = _code("components/build-view-header.ts")
    assert "timeZone: 'America/New_York'" in header
    assert "getHours()" not in header and "getDate()" not in header and "getMinutes()" not in header
    # Every surface that names a build time goes through the one formatter.
    for name in ("components/stored-room-row.ts", "completion.ts"):
        assert "buildTime(" in _code(name), name
    assert "Dates are ET" in _voice_and_tone()


# --- Item 70: the Model table claims only what the Build did -----------------------------


def test_the_validator_reads_as_deterministic_code_and_the_portraits_as_a_one_time_generation():
    strings = _strings()
    assert strings["validatorModel"] == "deterministic code, no model"
    assert strings["museImageDid"] == "one-time generation of the four portraits, not part of this build"
    table = _code("components/model-table.ts")
    # "checked 8 rules" only when the Build recorded the Validator's verdicts.
    assert "did: view.validator.length > 0 ? strings.validatorDid : ''," in table
