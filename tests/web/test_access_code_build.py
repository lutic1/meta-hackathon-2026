"""Story 7.17: the Access-code build panel and the hosted Capture differences (FR-32, FR-5, FR-20, UX-DR59, UX-DR17,
UX-DR18, UX-DR21, UX-DR63, UX-DR81, UX-DR46).

The client has no test runner, so most checks read the TypeScript and the stylesheets; `npm run build` and
`tsc --noEmit` prove they compile. The last checks run the hosted app over plain dicts and a temporary Volume, so the
check, the guarded upload and the poll answer the panel and the Capture screen as they expect.
"""

import re
from pathlib import Path

from fastapi.testclient import TestClient

from src.api.wiring import ACCESS_HEADER
from tests.api.hosted import hosted_handles, hosted_settings, make_hosted_app
from tests.api.test_builds import files
from tests.pipeline.uploads import make_uploads
from tests.web.design import WEB_SRC, css_rules, design_text
from tests.web.test_strings import _strings

CODE = "lantern-42"


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(name: str) -> str:
    """A module with its comments removed, so a doc comment never satisfies a check on the code."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", _ts(name), flags=re.DOTALL)


def _function(ts: str, name: str) -> str:
    """The body of the first `function name(` in `ts`, up to the next line that closes a block at its indent."""
    start = ts.index(f"function {name}(")
    indent = ts.rfind("\n", 0, start)
    pad = ts[indent + 1 : start].replace("async ", "").replace("export ", "")
    end = ts.index(f"\n{pad}}}\n", start)
    return ts[start:end]


def _panel() -> str:
    return _code("components/access-code-build.ts")


# --- Strings ----------------------------------------------------------------------------


def test_the_access_code_and_hosted_capture_strings_are_the_experience_lines():
    strings = _strings()
    assert strings["buildYourOwnRoom"] == "Build your own room"
    assert (strings["accessCode"], strings["checkCode"]) == ("Access code", "Check code")
    assert strings["accessCodeEmpty"] == "Enter the access code from the submission."
    assert strings["accessCodeRefused"] == "That access code isn't right. No photos were sent."
    assert strings["tooManyTries"] == "Too many tries. Wait a moment, then check the code again."
    assert strings["buildsLeft"].format(n=7) == "7 of 20 builds left"
    assert strings["buildQuota"] == "All 20 judge builds have been used. The demo rooms are still open."
    assert strings["queued"] == "Another room is being built. Yours is in line and will start on its own."
    assert strings["timerQueued"] == "queued"
    assert strings["queueNote"].format(m=1, ss="05") == "includes 1:05 in the queue"
    assert strings["ownLink"] == "This build has its own link; close this tab or play a demo room meanwhile."
    assert strings["targetMeasured"] == (
        "The two-minute build target is measured in Local mode on the Mac; here the timer also counts any time in the queue.")
    assert strings["judgeBuildRetry"] == "Trying again uses one of the remaining judge builds."
    assert strings["checking"] == "Checking"  # the pending label, the Code field's own word for a check in flight


# --- The panel ---------------------------------------------------------------------------


def test_the_panel_sits_in_the_landing_right_column_with_its_heading_label_field_and_button():
    landing = _code("landing.ts")
    assert "right.append(accessCodeBuild(onAccepted))" in landing
    # The panel stands in every landing state: before the failed and empty branches return.
    assert landing.index("right.append(accessCodeBuild(onAccepted))") < landing.index("if (rooms === null) {")
    panel = _panel()
    assert "heading.className = 'access-build-heading display-sm'" in panel and "heading.textContent = strings.buildYourOwnRoom" in panel
    assert "label.htmlFor = field.id" in panel and "label.textContent = strings.accessCode" in panel
    assert "field.className = 'access-build-field mono-code'" in panel
    assert "primaryButton({ label: strings.checkCode, pendingLabel: strings.checking, onActivate: check })" in panel
    assert "panel.append(heading, label, row, banners, status)" in panel
    rules = css_rules((WEB_SRC / "components/access-code-build.css").read_text())
    field = rules[".access-build-field"]
    assert (field["height"], field["background"], field["color"]) == ("44px", "var(--chrome)", "var(--text)")
    assert field["border-radius"] == "var(--rounded-md)"
    assert rules[".access-build"]["background"] == "var(--chrome-raised)"
    assert rules[".access-build-status.is-accepted"]["color"] == "var(--success)"
    assert "access-code-field:\n    background: '{colors.chrome}'" in design_text()


def test_enter_in_the_field_submits_like_check_code():
    panel = _panel()
    assert "if (event.key !== 'Enter') return" in panel and "button.click()" in panel


def test_an_empty_submit_shows_its_line_and_sends_nothing():
    check = _function(_panel(), "check")
    empty = check.split("if (code === '') {", 1)[1].split("}", 1)[0]
    assert "showStatus(status, strings.accessCodeEmpty)" in empty and "return" in empty
    assert check.index("if (code === '') {") < check.index("await checkAccess(code)")


def test_the_check_posts_the_code_and_maps_every_answer():
    api = _code("api/index.ts")
    assert "return postJson<AccessCheck>('/access/check', { code })" in api
    check = _function(_panel(), "check")
    assert "error instanceof RequestFailed && error.status === TOO_MANY_ATTEMPTS) showBanner(banners, tooManyTries)" in check
    assert "const TOO_MANY_ATTEMPTS = 429" in _panel()
    refused = check.split("if (!answer.ok || answer.builds_left === null) {", 1)[1].split("}", 1)[0]
    assert "showBanner(banners, accessRefused)" in refused
    quota = check.split("if (answer.builds_left === 0) {", 1)[1].split("return", 1)[0]
    assert "showBanner(banners, { ...buildQuota, compact: true })" in quota
    accepted = check.split("if (answer.builds_left === 0) {", 1)[1].split("return", 1)[1]
    assert accepted.index("holdAccessCode(code)") < accepted.index(
        "showStatus(status, fill(strings.buildsLeft, { n: answer.builds_left }), true)") < accepted.index(
        "onAccepted(answer.builds_left)")


def test_refused_and_too_many_tries_are_compact_banners_and_quota_is_the_warning():
    panel = _panel()
    assert "accessRefused: BannerState = { variant: 'error', heading: strings.accessCodeRefused, actions: [], compact: true }" in panel
    assert "tooManyTries: BannerState = { variant: 'warning', heading: strings.tooManyTries, actions: [], compact: true }" in panel
    assert "buildQuota: BannerState = { variant: 'warning', heading: strings.buildQuota, actions: [] }" in panel
    banner = _code("components/error-banner.ts")
    assert "element.classList.toggle('banner-compact', compact)" in banner
    rules = css_rules((WEB_SRC / "components/error-banner.css").read_text())
    assert rules[".banner-compact"]["flex-direction"] == "column"
    assert rules[".banner-actions:empty"] == {"display": "none"}


def test_quota_from_the_check_leaves_the_demo_room_cards_active():
    landing = _code("landing.ts")
    # Nothing the panel does reaches the cards: they keep their own start handler and are never disabled.
    assert "inert" not in landing and "disabled" not in landing and "disabled" not in _panel()
    assert "demoRoomCard(room, profile, () => void start(room))" in landing


# --- Accepted: the Capture screen, the code in memory only --------------------------------


def test_an_accepted_code_opens_the_capture_screen_once_with_no_stored_rooms_list():
    shell = _code("shell.ts")
    render = shell.split("async function render()", 1)[1].split("\n  }\n", 1)[0]
    capture = render.split("} else if (place.route.name === 'home' && accepted !== null) {", 1)[1].split("} else if", 1)[0]
    assert "content = { name: 'capture', buildsLeft: accepted, profile: place.profile, mode: meta.mode, retention: meta.retention }" in capture
    assert "accepted = null" in capture  # once: a later visit to `#/` is the landing again
    on_accepted = render.split("const onAccepted = (buildsLeft: number): void => {", 1)[1].split("}", 1)[0]
    assert "accepted = buildsLeft" in on_accepted and "void render()" in on_accepted
    assert "const capture = captureScreen(content.buildsLeft, content.profile, content.mode, content.retention, bar.timer)" in shell
    screen = _code("capture.ts")
    assert "typeof below === 'number' ? buildsLeftLine(below) : storedRooms(below, profile, mode, banners)," in screen
    # The Retention summary is the mode's text exactly as GET /meta serves it.
    assert "right.append(line(strings.inputRequirement), line(strings.iphoneTip), line(strings.reminder), retentionSummary(retention))" in screen


def test_the_code_lives_in_memory_only_and_rides_only_on_post_builds():
    holder = _code("access-code.ts")
    assert "let held: string | null = null" in holder
    assert not re.search(r"localStorage|sessionStorage|indexedDB|Storage", _ts("access-code.ts"))
    assert not re.search(r"localStorage|sessionStorage|indexedDB", _ts("components/access-code-build.ts"))
    api = _code("api/index.ts")
    assert "const ACCESS_HEADER = 'X-Access-Code'" in api
    post = api.split("export function postBuild(", 1)[1].split("\n}\n", 1)[0]
    assert "accessCode === null ? {} : { [ACCESS_HEADER]: accessCode }" in post
    assert api.count("ACCESS_HEADER") == 2  # declared once, sent only by `postBuild`
    assert "await postBuild(pairs, accessCode())" in _code("capture.ts")
    assert "await postBuild(held.uploads, accessCode())" in _code("build-progress.ts")
    assert ACCESS_HEADER == "X-Access-Code"


def test_post_builds_refusals_show_their_banners_on_the_capture_screen():
    capture = _code("capture.ts")
    assert "['access_denied', accessRefused]" in capture
    assert "['too_many_attempts', tooManyTries]" in capture
    assert "['build_quota_exceeded', buildQuota]" in capture
    submit = _function(capture, "submit")
    caught = submit.split("} catch (error) {", 1)[1]
    assert caught.index("HOSTED_REFUSALS.get(error.code)") < caught.index("if (hosted !== undefined) return hosted") < caught.index(
        "FR1_CODES.has(code)")


# --- queued ------------------------------------------------------------------------------


def test_queued_shows_the_warning_once_and_the_first_poll_past_it_clears_it():
    build = _code("build-progress.ts")
    assert "const QUEUED: BannerState = { variant: 'warning', heading: strings.queued, actions: [] }" in build
    queue = _function(build, "queue")
    assert "buildQueued(jobId)" in queue and "if (queuedBanner === null) queuedBanner = showBanner(banners, QUEUED)" in queue
    after = queue.split("return\n", 1)[1]
    assert "buildDequeued(jobId)" in after and "if (queuedBanner?.isConnected === true) showBanner(banners, null)" in after
    apply = _function(build, "apply")
    assert apply.index("queue(job)") < apply.index("end(job)")


def test_the_timer_reads_queued_in_place_of_the_digits_and_after_t1_carries_the_queue_note():
    timer = _code("capture-timer.ts")
    queued = _function(timer, "buildQueued")
    assert "save({ ...current, queued: true })" in queued
    dequeued = _function(timer, "buildDequeued")
    assert "current.queued === true" in dequeued and "save({ ...current, queued: false, queueMs: Date.now() - current.t0 })" in dequeued
    assert "view.render({ kind: 'running', elapsedMs, queued: shown.queued === true })" in timer
    assert "view.render({ kind: 'playable', elapsedMs, queueMs: shown.queueMs ?? null })" in timer
    face = _code("components/timer.ts")
    assert "const queued = face.kind === 'running' && face.queued === true" in face
    assert "digits.className = `timer-digits ${queued ? 'label' : 'mono-timer'}`" in face
    assert "digits.textContent = queued ? strings.timerQueued : formatElapsed(face.elapsedMs)" in face
    assert "const queueMs = face.kind === 'playable' ? (face.queueMs ?? null) : null" in face
    assert "else if (queueMs !== null) status.textContent = queueNote(queueMs)" in face
    note = _function(face, "queueNote")
    assert "const [m, ss] = formatElapsed(queueMs).split(':')" in note and "fill(strings.queueNote, { m, ss })" in note
    # The note reads in `label` `text-muted` after the frozen digits.
    assert css_rules((WEB_SRC / "components/timer.css").read_text())[".timer-status"]["color"] == "var(--text-muted)"


def test_the_two_hosted_lines_sit_under_the_stage_list_in_hosted_mode_only():
    build = _code("build-progress.ts")
    lines = _function(build, "hostedLines")
    assert "for (const text of [strings.ownLink, strings.targetMeasured]) {" in lines
    assert "line.className = 'build-hosted-line body-sm'" in lines
    assert "left.append(banners, stages.element, ...(mode === 'hosted' ? [hostedLines()] : []), actions, maskSlot, traySlot, picker)" in build
    assert css_rules((WEB_SRC / "shell.css").read_text())[".build-hosted-line"]["color"] == "var(--text)"


# --- failed and the Spend cap ------------------------------------------------------------


def test_a_hosted_failed_build_names_the_judge_build_cost_beside_try_again():
    end = _code("build-end.ts")
    assert "sentence: code === 'provider_error' ? strings.providerCause : strings.unexpectedCause," in end
    assert "actions: ['tryAgain']," in end
    assert "judgeBuildRetry" not in end  # the job alone cannot say whether "Try again" is on screen
    banner = _function(_code("build-progress.ts"), "end")
    # The sentence goes only beside a "Try again" actually offered: a page holding no photos (a reloaded or reopened
    # `#/build/<job_id>`) turns every action into "Start over", so it gets no judge-build sentence.
    assert "const kinds = new Set(state.actions.map((kind) => (held === null ? 'startOver' : kind)))" in banner
    assert "const retries = mode === 'hosted' && kinds.has('tryAgain')" in banner
    assert "const sentence = retries ? `${state.sentence} ${strings.judgeBuildRetry}` : state.sentence" in banner
    assert banner.index("const kinds =") < banner.index("const retries =") < banner.index("showBanner(banners,")
    assert "showBanner(banners, { variant, heading, sentence, actions: [...kinds].map(action) })" in banner


def test_the_spend_cap_keeps_its_warning_with_start_over_only():
    spend = _code("build-end.ts").split("if (code === 'spend_cap_exceeded') {", 1)[1].split("}\n", 1)[0]
    assert "variant: 'warning', heading: strings.spendCap, sentence: strings.spendCapBody, actions: ['startOver']" in spend


# --- The Build URL across a closed tab, and the automatic Play ---------------------------


def test_a_reopened_build_url_polls_every_2000ms_with_no_access_code():
    build = _code("build-progress.ts")
    assert "export const BUILD_POLL_MS = 2000" in build
    assert "polling = setTimeout(() => void poll(), BUILD_POLL_MS)" in build
    assert "job = await getBuild(jobId)" in build
    get = _code("api/index.ts").split("export function getBuild(", 1)[1].split("\n}\n", 1)[0]
    assert "return getJson<JobState>(`/builds/${encodeURIComponent(jobId)}`)" in get  # no header
    # A Build already done when the route opens shows "Play this room" rather than starting on its own.
    assert "label: strings.playThisRoom" in _function(build, "done")


def test_the_automatic_play_sends_a_fresh_derived_block_in_hosted_mode():
    assert "await startSession(await sessionStart(roomId, profile, mode))" in _code("build-progress.ts")
    assert "derived: mode === 'hosted' ? freshDerived() : await getDerived(name)" in _code("profile/index.ts")


# --- Back to the Hosted landing ----------------------------------------------------------


def test_build_another_room_and_a_confirmed_leave_return_to_the_landing_recording_nothing():
    assert "location.hash = placeHref({ route: { name: 'home' }, profile })" in _code("completion.ts")
    play = _code("play.ts")
    assert "const home = placeHref({ route: { name: 'home' }, profile: currentPlace().profile })" in play
    assert "putResult" not in play and "putResult" not in _code("leave-room.ts")
    # A Hosted `#/` with no code just accepted renders the landing, the code still held or not.
    render = _code("shell.ts").split("async function render()", 1)[1]
    assert "} else if (place.route.name === 'home') {\n      const rooms = await listRooms().catch(() => null)" in render


# --- Accessibility -----------------------------------------------------------------------


def test_banners_take_focus_the_field_is_labelled_and_the_status_line_is_page_content():
    assert "slot.replaceChildren(element)\n  element.focus()" in _ts("components/error-banner.ts")
    panel = _panel()
    assert "field.setAttribute('aria-describedby', status.id)" in panel
    # Read as page content: no live region, no role that announces it.
    assert not re.search(r"aria-live|role', 'status'|announce\(", panel)
    assert "field.focus()" in _function(panel, "check")  # an empty submit keeps the judge in the field


def test_every_new_pair_is_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    pairs = {("text", "chrome"), ("text", "chrome-raised"), ("success", "chrome-raised"), ("on-lamp", "lamp"),
             ("error-text", "error-surface"), ("warning-text", "warning-surface"), ("text-muted", "chrome"),
             ("text", "canvas")}
    for fg, bg in pairs:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
    assert "accepted Access code status line" in table
    # On the Capture screen the builds-left line keeps the panel's surface, so `success` sits on `chrome-raised` there
    # too, never on the canvas.
    assert "status.classList.add('access-build-left')" in _function(_panel(), "buildsLeftLine")
    left = css_rules((WEB_SRC / "components/access-code-build.css").read_text())[".access-build-left"]
    assert left["background"] == "var(--chrome-raised)"


# --- The hosted app answers the panel and the Capture screen ------------------------------


def test_the_hosted_app_answers_the_check_the_guarded_upload_and_the_open_poll(tmp_path: Path):
    handles = hosted_handles(tmp_path)
    client = TestClient(make_hosted_app(tmp_path, handles, settings=hosted_settings(ACCESS_CODE=CODE)))

    assert client.post("/api/access/check", json={"code": "lantern-41"}).json() == {"ok": False, "builds_left": None}
    assert client.post("/api/access/check", json={"code": CODE}).json() == {"ok": True, "builds_left": 20}

    refused = client.post("/api/builds", files=files(make_uploads(6)), headers={ACCESS_HEADER: "lantern-41"})
    assert refused.status_code == 403 and refused.json()["error"]["code"] == "access_denied"

    accepted = client.post("/api/builds", files=files(make_uploads(6)), headers={ACCESS_HEADER: CODE})
    assert accepted.status_code == 202 and accepted.json()["status"] == "queued"
    # The poll needs no code, so a closed and reopened tab resumes it.
    polled = client.get(f"/api/builds/{accepted.json()['id']}")
    assert polled.status_code == 202 and polled.json()["status"] == "queued"
    assert client.post("/api/access/check", json={"code": CODE}).json() == {"ok": True, "builds_left": 19}
