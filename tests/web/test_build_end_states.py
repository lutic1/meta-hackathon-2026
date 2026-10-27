"""FR-4, FR-5, FR-10, FR-28, UX-DR13, UX-DR15, UX-DR21, UX-DR62, UX-DR63, UX-DR75: the Capture screen's end states.

The client has no test runner (a runner is added only through bmad-correct-course), so these checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile. The envelope codes and the
photo cap the client keys on are compared with the server's own.
"""

import re

from src.domain.ledger import SpendCapExceeded
from src.domain.schema import ErrorDetail, JobState
from src.pipeline.build import error_code
from src.pipeline.ingest import MAX_PHOTOS
from src.pipeline.segment import TooFewInteractables
from src.providers.base import ProviderError
from tests.web.design import WEB_SRC, css_rules, design_text


def _code(name: str) -> str:
    """A module with its comments removed."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", (WEB_SRC / name).read_text(), flags=re.DOTALL)


def _function(text: str, name: str) -> str:
    """The body of the inner `function name(` or `async function name(` in `text`, up to its closing brace."""
    body = text.split(f"function {name}(", 1)[1].split("{\n", 1)[1]
    indent = re.match(r" *", body).group(0)
    return body.split(f"\n{indent[:-2]}}}\n", 1)[0]


def _branch(text: str, condition: str) -> str:
    """The block that `if (condition) {` opens in `text`."""
    return text.split(f"if ({condition}) {{", 1)[1].split("\n  }\n", 1)[0]


# --- Job status and envelope codes --------------------------------------------------------------------------------


def test_the_codes_the_client_maps_are_the_codes_the_server_writes():
    assert error_code(ProviderError(503, "unavailable", "down")) == "provider_error"
    assert error_code(SpendCapExceeded(20.0, 19.9)) == "spend_cap_exceeded"
    assert error_code(TooFewInteractables("4 survived")) == "too_few_interactables"
    assert TooFewInteractables.status == "needs_more_photos"
    assert {"error", "status", "stage"} <= set(JobState.model_fields) and "code" in ErrorDetail.model_fields
    end = _code("build-end.ts")
    assert "const code = job.error?.code ?? null" in end
    assert "if (job.status === 'needs_more_photos' || code === 'too_few_interactables') {" in end
    assert "if (code === 'spend_cap_exceeded') {" in end
    assert "sentence: code === 'provider_error' ? strings.providerCause : strings.unexpectedCause" in end
    assert "if (job.status !== 'failed') return null" in end


def test_failed_names_the_row_the_stage_list_shows_failed_with_its_cause_and_try_again():
    end = _code("build-end.ts")
    assert "const stopped = rows.find((row) => row.state === 'failed') ?? rows.find((row) => row.state !== 'done')" in end
    assert "heading: fill(strings.buildStopped, { stage: (stopped?.name ?? strings.sceneLoading).toLowerCase() })" in end
    failed = end.split("const rows = stageRows(job)", 1)[1]
    assert "variant: 'error'" in failed and "actions: ['tryAgain']" in failed and "status: 'failed'" in failed
    stages = _code("build-stages.ts")
    assert "else if (at === current) state = job?.status === 'running' ? 'running' : 'failed'" in stages


def test_spend_cap_is_the_warning_variant_with_start_over_only():
    branch = _branch(_code("build-end.ts"), "code === 'spend_cap_exceeded'")
    assert "variant: 'warning'" in branch and "heading: strings.spendCap" in branch
    assert "sentence: strings.spendCapBody" in branch and "actions: ['startOver']" in branch
    assert "tryAgain" not in branch


def test_needs_more_photos_stops_at_finding_objects_and_offers_add_photos_below_10():
    stages = _code("build-stages.ts")
    assert ("const STOPPED_AT: Partial<Record<JobState['status'], Kind>> = { needs_more_photos: 'finding', "
            "needs_recapture: 'testing' }") in stages
    assert "STOPPED_AT[job.status] ?? (job.stage == null ? undefined : KIND[job.stage])" in stages
    branch = _branch(_code("build-end.ts"), "job.status === 'needs_more_photos' || code === 'too_few_interactables'")
    assert "const full = photos >= MAX_PHOTOS" in branch and "heading: strings.tooFewObjects" in branch
    assert "sentence: full ? strings.tooFewObjectsFull : strings.tooFewObjectsBody" in branch
    assert "actions: full ? ['startOver'] : ['addPhotos', 'startOver']" in branch
    assert "status: 'needs_more_photos'" in branch
    assert f"export const MAX_PHOTOS = {MAX_PHOTOS}" in _code("photos.ts")
    # The set's size: the photos this page holds, else the ingest record of a reloaded page.
    end = _function(_code("build-progress.ts"), "end")
    assert ("const photos = held?.uploads.length ?? job.stages?.find((record) => record.stage === 'ingest')?.count ?? 0"
            in end)


def test_add_photos_appends_up_to_10_in_all_and_the_next_upload_is_a_new_build():
    screen = _code("build-progress.ts")
    assert "return { label: strings.addPhotos, onActivate: () => picker.click() }" in screen
    assert "picker.type = 'file'" in screen and "picker.multiple = true" in screen and "picker.hidden = true" in screen
    change = screen.split("picker.addEventListener('change', () => {", 1)[1].split("\n      })", 1)[0]
    assert "carryPhotos([...held.uploads.map(({ original }) => original), ...files].slice(0, MAX_PHOTOS))" in change
    assert "startOver()" in change
    capture = _code("capture.ts")
    assert "const carried = takeCarriedPhotos()" in capture
    assert "if (carried.length > 0) void choose(carried, true)" in capture  # re-validated like any chosen set
    held = _code("build-photos.ts")
    assert "uploads: readonly UploadPhoto[]" in held and "uploads: pairs," in capture
    take = _function(held, "takeCarriedPhotos")
    assert "carried = []" in take  # carried once


def test_needs_recapture_stops_at_testing_the_room_with_start_over():
    branch = _branch(_code("build-end.ts"), "job.status === 'needs_recapture'")
    assert "heading: strings.recapture" in branch and "sentence: strings.recaptureBody" in branch
    assert "actions: ['startOver']" in branch and "status: 'needs_recapture'" in branch


def test_try_again_posts_the_same_photos_as_a_new_build_and_nothing_offers_a_partial_room():
    screen = _code("build-progress.ts")
    retry = _function(screen, "retry")
    assert "if (held === null || retrying) return" in retry
    assert "const job = await postBuild(held.uploads)" in retry
    order = ["startTimer(t0)", "buildAccepted(job.id)", "passPhotos(jobId, job.id)",
             "location.hash = captureHref(job.id, profile)"]
    assert [retry.index(step) for step in order] == sorted(retry.index(step) for step in order)
    assert "heading: strings.uploadFailed" in retry and "onActivate: () => void retry()" in retry
    assert "return { label: strings.tryAgain, onActivate: () => void retry() }" in screen
    held = _code("build-photos.ts")
    assert "if (held?.jobId === from) held = { ...held, jobId: to }" in _function(held, "passPhotos")
    # The end path never starts a Session or offers the Room: no room id, Play or session start in it.
    end = _code("build-end.ts")
    assert not re.search(r"room_id|startSession|playThisRoom|photoUrl", end)
    for name in ("end", "action", "retry", "startOver"):
        assert not re.search(r"room_id|startSession|playThisRoom", _function(screen, name)), name


def test_start_over_opens_the_empty_capture_screen_and_stands_in_when_no_photos_are_held():
    screen = _code("build-progress.ts")
    start_over = _function(screen, "startOver")
    assert "releasePhotos()" in start_over
    assert "location.hash = placeHref({ route: { name: 'home' }, profile })" in start_over
    end = _function(screen, "end")
    assert "const kinds = new Set(state.actions.map((kind) => (held === null ? 'startOver' : kind)))" in end
    assert "if (kind === 'startOver') return { label: strings.startOver, onActivate: startOver }" in screen


def test_every_end_state_stops_the_timer_beside_its_status_and_keeps_the_photos():
    screen = _code("build-progress.ts")
    end = _function(screen, "end")
    assert end.lstrip().startswith("if (ended) return") and "if (state === null) return" in end
    assert end.index("buildEnded(jobId, state.status)") < end.index("showBanner(banners,")
    assert "end(job)" in _function(screen, "apply")
    timer = _code("capture-timer.ts")
    assert "if (counting()?.jobId === jobId) stopTimer(status)" in _function(timer, "buildEnded")
    # The compact tray is drawn once from the held photos and an end state never clears it.
    assert "traySlot.replaceChildren" not in end and "traySlot.replaceChildren" not in _function(screen, "action")


# --- Reconnecting ---------------------------------------------------------------------------------------------------


def test_two_missed_polls_show_the_reconnecting_strip_above_any_banner_once_and_unfocused():
    screen = _code("build-progress.ts")
    assert "export const MISSED_POLLS = 2" in screen
    assert "const strip = statusStrip(strings.reconnectingBuild)" in screen
    poll = _function(screen, "poll")
    missed = poll.split("} catch (error) {", 1)[1].split("\n        }\n", 1)[0]
    assert "missed += 1" in missed
    assert "if (missed === MISSED_POLLS) {\n            left.prepend(strip)\n            announce(strings.reconnectingBuild)" in missed
    # A miss leaves the Stage list, the Mask preview and the Timer as they are, and polls on.
    assert "apply(" not in missed and "stages.update" not in missed and "Timer" not in missed
    assert "polling = setTimeout(() => void poll(), BUILD_POLL_MS)" in missed
    strip = _code("components/status-strip.ts")
    assert "tabIndex" not in strip and "focus" not in strip


def test_the_next_answered_poll_removes_the_strip_and_renders_from_job_state():
    screen = _code("build-progress.ts")
    poll = _function(screen, "poll")
    answered = poll.split("        }\n        if (!mounted) return\n", 1)[1]
    assert answered.index("missed = 0") < answered.index("hideStrip()") < answered.index("apply(job)")
    hide = _function(screen, "hideStrip")
    assert hide.lstrip().startswith("if (!strip.isConnected) return")
    assert hide.index("strip.remove()") < hide.index("announce('')")


def test_a_refused_poll_ends_polling_without_leaving_the_strip_up():
    poll = _function(_code("build-progress.ts"), "poll")
    refused = poll.split("if (refused) {", 1)[1].split("\n          }\n", 1)[0]
    assert "hideStrip()" in refused and "return" in refused and "setTimeout" not in refused


def test_the_live_region_is_one_polite_visually_hidden_region_in_the_page_from_the_start():
    region = _code("live-region.ts")
    assert "region.setAttribute('aria-live', 'polite')" in region
    assert "region.className = 'visually-hidden'" in region and "document.body.append(region)" in region
    assert "liveRegion().textContent = text" in _function(region, "announce")
    assert "liveRegion()" in _code("shell.ts")  # inserted by the shell before anything is written to it
    others = [path for path in WEB_SRC.rglob("*.ts") if path.name != "live-region.ts" and "aria-live" in path.read_text()]
    assert others == []


# --- Accessibility floor -------------------------------------------------------------------------------------------


def test_an_end_state_banner_takes_focus_with_its_actions_next_and_one_banner_at_a_time():
    banner = _code("components/error-banner.ts")
    assert "element.tabIndex = -1" in banner
    assert "slot.replaceChildren(element)\n  element.focus()" in banner  # replaces any older banner, then focuses
    assert "element.append(text, buttons)" in banner  # its actions follow it in Tab order
    assert "buttons.append(...actions.map((action) => secondaryButton(action)))" in banner
    assert "element.type = 'button'" in _code("components/button.ts")  # a real button: Enter activates it
    ring = css_rules((WEB_SRC / "tokens.css").read_text())[":focus-visible"]
    assert ring["outline"] == "2px solid var(--focus-ring)"
    end = _function(_code("build-progress.ts"), "end")
    assert "showBanner(banners, { variant, heading, sentence, actions: [...kinds].map(action) })" in end


def test_every_end_state_and_strip_color_pair_is_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    pairs = {("error-text", "error-surface"), ("text", "error-surface"), ("warning-text", "warning-surface"),
             ("text", "warning-surface"), ("lamp", "error-surface"), ("lamp", "warning-surface")}
    for fg, bg in pairs:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
    rules = css_rules((WEB_SRC / "components/error-banner.css").read_text())
    assert rules[".banner-warning"]["background"] == "var(--warning-surface)"
    assert rules[".banner-warning .banner-heading"]["color"] == "var(--warning-text)"
    strip = css_rules((WEB_SRC / "components/status-strip.css").read_text())[".status-strip"]
    assert (strip["background"], strip["color"]) == ("var(--warning-surface)", "var(--text)")
