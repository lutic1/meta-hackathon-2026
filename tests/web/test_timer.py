"""FR-5, UX-DR17, AR-14, NFR-1: the Capture Timer from the Upload click (T0) to the first Hotspot response (T1).

The client has no test runner (a runner is added only through bmad-correct-course), so these checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile.
"""

import re

from tests.web.design import WEB_SRC, css_rules, design_text

COMPONENTS = WEB_SRC / "components"


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(name: str) -> str:
    """A module with its comments removed."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", _ts(name), flags=re.DOTALL)


def _function(text: str, name: str) -> str:
    """The body of `function name(` in `text`, up to its closing brace at the same indent."""
    head, body = text.split(f"function {name}(", 1)
    indent = head.rsplit("\n", 1)[1].replace("async ", "").replace("export ", "")
    return body.split("{\n", 1)[1].split(f"\n{indent}}}\n", 1)[0]


def _timer_rules() -> dict[str, dict[str, str]]:
    return css_rules((COMPONENTS / "timer.css").read_text())


# --- T0: the Upload click starts the Timer ------------------------------------------------------------------------


def test_the_upload_click_is_t0_and_the_capture_screen_shows_only_the_run_it_started():
    capture = _code("capture.ts")
    send = _function(capture, "send")
    assert send.index("if (!isValidSet(photos)) return") < send.index("t0 = Date.now()") < send.index("startTimer(t0)")
    assert send.index("startTimer(t0)") < send.index("render(true)") < send.index("await submit(photos)")
    # Nothing shows before the first Upload: the slot is mounted for the run whose T0 this screen recorded.
    assert "let t0: number | null = null" in capture
    assert "mountTimer(timerSlot, (run) => run.t0 === t0)" in capture
    shell = _code("shell.ts")
    assert "const body = surface(content, bar)" in shell
    assert "captureScreen(content.rooms, content.profile, content.mode, content.retention, bar.timer)" in shell


def test_a_start_is_a_new_run_from_now_replacing_any_earlier_one():
    start = _function(_code("capture-timer.ts"), "startTimer")
    assert "export function startTimer(t0: number): void" in _code("capture-timer.ts")
    assert "save({ t0, jobId: null, sessionId: null, stoppedAt: null, status: null })" in start


def test_running_reads_photos_to_play_with_a_static_lamp_dot_and_text_digits():
    ts = _code("components/timer.ts")
    assert "label.className = 'timer-label label'" in ts and "digits.className = 'timer-digits mono-timer'" in ts
    assert "label.textContent = face.kind === 'playable' ? strings.playableIn : strings.photosToPlay" in ts
    assert "dot.hidden = face.kind !== 'running'" in ts
    assert "element.append(label, dot, digits, status)" in ts  # the label, the dot between, then the digits
    rules = _timer_rules()
    assert rules[".timer-label"]["color"] == "var(--text-muted)"
    assert rules[".timer-digits"]["color"] == "var(--text)"
    dot = rules[".timer-dot"]
    assert (dot["width"], dot["height"], dot["border-radius"], dot["background"]) == ("6px", "6px", "50%", "var(--lamp)")
    text = (COMPONENTS / "timer.css").read_text()
    assert not re.search(r"animation|@keyframes|transition|opacity", text), "the lamp dot never blinks"
    # mono-timer is 28 px IBM Plex Mono with tabular figures, so the digits never jitter.
    mono = css_rules((WEB_SRC / "tokens.css").read_text())[".mono-timer"]
    assert mono["font-size"] == "28px" and mono["font-variant-numeric"] == "tabular-nums"


def test_digits_are_m_ss_from_whole_seconds():
    ts = _code("components/timer.ts")
    assert "const seconds = Math.floor(Math.max(0, elapsedMs) / 1000)" in ts
    assert "`${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`" in ts
    assert "digits.textContent = formatElapsed(face.elapsedMs)" in ts


# --- Real time, whatever the Demo timescale ----------------------------------------------------------------------


def test_the_timer_counts_in_real_time_and_never_reads_the_demo_timescale():
    for name in ("capture-timer.ts", "components/timer.ts"):
        code = _code(name)
        assert not re.search(r"demo_timescale|timescale|getMeta|Meta\b", code), name
        assert "performance.now" not in code, f"{name}: a reload must resume from the same wall clock"
    timer = _code("capture-timer.ts")
    assert "const elapsedMs = (shown.stoppedAt ?? Date.now()) - shown.t0" in timer
    assert "ticking ??= setInterval(render, TICK_MS)" in timer


# --- Reconnecting and reload --------------------------------------------------------------------------------------


def test_the_timer_waits_on_no_request_so_missed_polls_never_stop_it():
    timer = _code("capture-timer.ts")
    assert "api/index" not in timer and "fetch(" not in timer
    # Only an Upload outcome, T1 or an end status stops it.
    assert re.findall(r"stopTimer\(([^)]*)\)", _code("capture.ts")) == ["strings.uploadFailedStatus"]


def test_an_accepted_upload_records_its_job_so_a_reload_of_the_build_route_resumes_from_t0():
    capture = _code("capture.ts")
    submit = _function(capture, "submit")
    assert submit.index("const job = await postBuild(pairs)") < submit.index("buildAccepted(job.id)") < submit.index(
        "return null")
    timer = _code("capture-timer.ts")
    assert "sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next))" in timer
    assert "let run: TimerRun | null = read()" in timer  # a reloaded page starts from the recorded run
    assert "if (current !== null && current.jobId === null) save({ ...current, jobId })" in timer
    # The run keeps its T0 through every update: nothing but startTimer writes a new one.
    updates = re.findall(r"save\(\{ \.\.\.current, ([^}]*)\}\)", timer)
    assert len(updates) == 3 and not any("t0" in update for update in updates)
    router = _code("router.ts")
    assert r"const BUILD_ROUTE = /^\/build\/([\w-]+)$/" in router
    assert "if (build !== null) return { route: { name: 'build', jobId: build[1] }, profile }" in router
    assert "route.name === 'build' ? route.jobId : route.sessionId" in router
    shell = _code("shell.ts")
    assert "if (route.name === 'build') return (run) => run.jobId === route.jobId" in shell


def test_storage_refused_still_runs_the_timer_for_the_page():
    timer = _code("capture-timer.ts")
    for name in ("read", "save"):
        assert "try {" in _function(timer, name) and "catch" in _function(timer, name)
    assert "run = next" in _function(timer, "save")


# --- T1: the first Hotspot pointer response ------------------------------------------------------------------------


def test_the_first_pointer_response_of_the_builds_session_stops_it_at_t1():
    timer = _code("capture-timer.ts")
    assert "import { FIRST_POINTER_RESPONSE, type FirstPointerResponseDetail } from './scene/index.ts'" in timer
    assert "window.addEventListener(FIRST_POINTER_RESPONSE, respond)" in timer
    assert "window.removeEventListener(FIRST_POINTER_RESPONSE, respond)" in timer
    assert "if (counting()?.sessionId === sessionId) stopTimer(null)" in _function(timer, "respond")
    assert "if (current !== null && current.jobId === jobId) save({ ...current, sessionId })" in timer
    shell = _code("shell.ts")
    assert "return (run) => run.sessionId === route.sessionId" in shell  # the Play and Completion screens


def test_keyboard_focus_never_stops_it():
    hotspots = _code("scene/hotspots.ts")
    assert "hotspot.addEventListener('pointerenter', handlers.onPointerEnter)" in hotspots
    assert not re.search(r"addEventListener\('(focus|focusin|keydown|keyup)', handlers\.onPointerEnter", hotspots)
    keydown = hotspots.split("addEventListener('keydown'", 1)[1].split("})", 1)[0]
    assert "onPointerEnter" not in keydown
    assert "onPointerEnter: () => firstPointerResponse(play.id)" in _code("scene/index.ts")


def test_at_t1_it_reads_playable_in_with_success_digits_no_dot_and_stays_frozen():
    timer = _code("capture-timer.ts")
    assert "else if (shown.status === null) view.render({ kind: 'playable', elapsedMs })" in timer
    stop = _function(timer, "stopTimer")
    assert "const current = counting()" in stop and "save({ ...current, stoppedAt: Date.now(), status })" in stop
    assert "return run !== null && run.stoppedAt === null ? run : null" in timer  # a stopped run never moves again
    rules = _timer_rules()
    assert rules[".timer[data-state='playable'] .timer-digits"]["color"] == "var(--success)"
    assert "element.dataset.state = face.kind" in _code("components/timer.ts")


def test_a_replayed_stored_room_never_shows_the_timer():
    rooms = _code("stored-rooms.ts")
    assert "capture-timer" not in rooms and "sessionOpened" not in rooms
    shell = _code("shell.ts")
    owner = _function(shell, "timerOwner")
    assert "if (route.name === 'home') return null" in owner
    timer = _code("capture-timer.ts")
    render = _function(timer, "render")
    assert "const shown = run !== null && belongs(run) ? run : null" in render
    assert "if (shown === null) {\n      slot.replaceChildren()" in render


# --- End states -----------------------------------------------------------------------------------------------------


def test_a_failed_upload_freezes_the_digits_beside_its_status_and_the_next_upload_starts_a_new_t0():
    send = _function(_code("capture.ts"), "send")
    assert send.index("await submit(photos)") < send.index("if (outcome !== null) stopTimer(strings.uploadFailedStatus)")
    assert send.index("startTimer(t0)") < send.index("stopTimer(")
    timer = _code("capture-timer.ts")
    assert "else view.render({ kind: 'ended', elapsedMs, status: shown.status })" in timer
    ts = _code("components/timer.ts")
    assert "status.className = 'timer-status label'" in ts
    assert "status.hidden = face.kind !== 'ended'" in ts
    assert "status.textContent = face.kind === 'ended' ? face.status : ''" in ts
    assert _timer_rules()[".timer-status"]["color"] == "var(--text-muted)"
    # "Try again" goes through Upload, so it is a new Upload click and a new T0.
    assert "actions: [{ label: strings.tryAgain, onActivate: () => upload.click() }]" in _code("capture.ts")


# --- Accessibility floor ------------------------------------------------------------------------------------------


def test_the_label_and_digits_are_one_timer_a_screen_reader_reads_together():
    ts = _code("components/timer.ts")
    assert "element.setAttribute('role', 'timer')" in ts
    assert "dot.setAttribute('aria-hidden', 'true')" in ts
    assert ts.count("aria-hidden") == 1 and "aria-label" not in ts  # the label and digits are read as their text
    assert "tabIndex" not in ts and "addEventListener" not in ts
    # The label always names what the digits measure: running and end status read "Photos to play", T1 "Playable in".
    assert "strings.playableIn : strings.photosToPlay" in ts


def test_every_timer_color_pair_meets_aa_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    for fg, bg in (("text", "chrome"), ("text-muted", "chrome"), ("success", "chrome"), ("lamp", "chrome")):
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
    assert css_rules((COMPONENTS / "top-bar.css").read_text())[".top-bar"]["background"] == "var(--chrome)"


def test_the_timer_sits_in_the_top_bar_center_slot_on_every_route():
    shell = _code("shell.ts")
    assert "const unmountTimer = owns === null ? undefined : mountTimer(bar.timer, owns, done)" in shell
    assert "unmountTimer?.()" in shell
    assert "if (!view.element.isConnected) slot.replaceChildren(view.element)" in _code("capture-timer.ts")
    assert "white-space" in _timer_rules()[".timer"]
