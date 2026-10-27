"""FR-5, UX-DR8, UX-DR15, UX-DR16, UX-DR18, UX-DR62, UX-DR63, UX-DR74, AR-31: the Capture screen during a Build.

The client has no test runner (a runner is added only through bmad-correct-course), so these checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile. The stage names and job-state
fields the client keys on are compared with the server's own.
"""

import re
from typing import get_args

from src.domain.schema import JobState, Stage, StageRecord
from src.pipeline.architect import ARCHITECT_MODEL
from src.pipeline.build import STAGES
from src.pipeline.segment import SEGMENT_MODEL
from tests.web.design import WEB_SRC, css_rules, design_text, source_css

COMPONENTS = WEB_SRC / "components"


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(name: str) -> str:
    """A module with its comments removed."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", _ts(name), flags=re.DOTALL)


def _css(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


def _function(text: str, name: str) -> str:
    """The body of the inner `function name(` or `async function name(` in `text`, up to its closing brace."""
    body = text.split(f"function {name}(", 1)[1].split("{\n", 1)[1]
    indent = re.match(r" *", body).group(0)
    return body.split(f"\n{indent[:-2]}}}\n", 1)[0]


# --- Routing: the Upload hands off to #/build/<job_id> -----------------------------------------------------------


def test_an_accepted_upload_hands_its_photos_to_the_build_route_and_carries_the_profile():
    capture = _code("capture.ts")
    submit = _function(capture, "submit")
    assert submit.index("buildAccepted(job.id)") < submit.index("accepted = job.id") < submit.index("holdPhotos({")
    assert "thumbnails: set.map(({ url }) => url)" in submit
    assert "downscales: pairs.map(({ downscale }) => URL.createObjectURL(downscale))" in submit
    send = _function(capture, "send")
    assert "if (accepted !== null) location.hash = captureHref(accepted, profile)" in send
    # The thumbnails now belong to the Build route, so the Capture screen's teardown keeps them.
    assert "if (accepted === null) release(photos)" in capture
    router = _code("router.ts")
    assert "return `#/build/${jobId}?profile=${encodeURIComponent(profile)}`" in router


def test_the_held_photos_live_in_memory_only_and_are_released_once_the_room_opens():
    held = _code("build-photos.ts")
    assert "let held: HeldPhotos | null = null" in held
    assert "return held?.jobId === jobId ? held : null" in held
    assert "URL.revokeObjectURL(url)" in held
    assert not re.search(r"localStorage|sessionStorage|indexedDB|fetch\(", held)
    assert "if (started) releasePhotos()" in _code("build-progress.ts")


def test_the_build_route_is_the_capture_layout_with_the_stage_list_in_place_of_the_dropzone():
    shell = _code("shell.ts")
    assert ("content = { name: 'build', jobId: place.route.jobId, profile: place.profile, retention: meta.retention }"
            in shell)
    assert "const build = buildScreen(content.jobId, content.profile, content.retention)" in shell
    assert "element.append(build.left, build.right)" in shell and "mount: build.mount" in shell
    screen = _code("build-progress.ts")
    assert "left.append(banners, stages.element, actions, maskSlot, traySlot, picker)" in screen
    assert "right: captureColumn(retention)" in screen
    assert "captureDropzone" not in screen and "storedRooms" not in screen
    capture = _code("capture.ts")
    assert "export function captureColumn(retention: string): HTMLElement" in capture
    assert "const right = captureColumn(retention)" in capture


def test_it_polls_get_builds_every_2000_ms_while_the_build_is_queued_or_running():
    screen = _code("build-progress.ts")
    assert "export const BUILD_POLL_MS = 2000" in screen
    poll = _function(screen, "poll")
    assert "job = await getBuild(jobId)" in poll
    assert ("if (job.status === 'queued' || job.status === 'running') polling = setTimeout(() => void poll(), "
            "BUILD_POLL_MS)") in poll
    # A missed poll is tried again on the same cadence; a refusal (4xx) ends polling with the list as last seen.
    assert "error instanceof RequestFailed && error.status !== null && error.status < 500" in poll
    assert "if (refused) {" in poll
    assert poll.index("if (refused) {") < poll.index("polling = setTimeout(() => void poll(), BUILD_POLL_MS)")
    assert "clearTimeout(polling)" in screen
    api = _code("api/index.ts")
    assert "return getJson<JobState>(`/builds/${encodeURIComponent(jobId)}`)" in api


def test_the_photo_tray_turns_compact_at_96_by_72_with_the_count_kept_and_no_remove_control():
    tray = (COMPONENTS / "photo-tray.ts").read_text()
    compact = tray.split("export function compactPhotoTray(", 1)[1]
    assert "tray.className = 'photo-tray compact'" in compact
    assert "count.textContent = fill(strings.photosChosen, { n: urls.length })" in compact
    assert "image.width = 96" in compact and "image.height = 72" in compact and "image.alt = ''" in compact
    assert "button" not in compact
    rules = _css("components/photo-tray.css")
    thumb = rules[".photo-tray.compact .photo-tray-thumb,\n.photo-tray.compact .photo-tray-thumb img"]
    assert (thumb["width"], thumb["height"]) == ("96px", "72px")
    assert "compactWidth: 96px" in design_text() and "compactHeight: 72px" in design_text()
    screen = _code("build-progress.ts")
    assert "if (held !== null) traySlot.append(compactPhotoTray(held.thumbnails))" in screen


# --- The Stage list ------------------------------------------------------------------------------------------------


def test_the_architect_introduction_sits_at_the_top_from_the_first_render():
    ts = _code("components/stage-list.ts")
    assert ("introduction('architect', strings.architect, strings.architectRole, strings.architectVoice),"
            "\n    rule,\n    list,") in ts
    assert "intro.append(wizardPortrait(wizard, 48), who)" in ts
    assert "text('p', 'stage-intro-name label', name)" in ts and "text('p', 'stage-intro-role body-sm', role)" in ts
    assert "spoken('stage-intro-voice', wizard, voice)" in ts
    # Drawn before the first poll answers: every stage pending under it.
    assert "stages.update(stageRows(null))" in _code("build-progress.ts")
    rules = _css("components/stage-list.css")
    assert rules[".stage-list"]["background"] == "var(--chrome-raised)"
    assert rules[".stage-list"]["border-radius"] == "var(--rounded-lg)"
    assert rules[".stage-list"]["padding"] == "var(--spacing-4) var(--spacing-5)"
    assert rules[".stage-list-rule"]["background"] == "var(--hairline)" and rules[".stage-list-rule"]["height"] == "1px"
    assert rules[".stage-intro-role"]["color"] == "var(--text-muted)"
    # The shared Wizard portrait: decorative beside the name, its placeholder hidden and its painting alt-less.
    portrait = (WEB_SRC / "wizards/portrait.ts").read_text()
    assert "initial.setAttribute('aria-hidden', 'true')" in portrait and "image.alt = ''" in portrait


def test_the_five_stage_names_cover_the_seven_pipeline_stages():
    stages = _code("build-stages.ts")
    kinds = dict(re.findall(r"^  (\w+): '(\w+)',$", stages.split("const KIND", 1)[1].split("}", 1)[0], re.MULTILINE))
    assert kinds == {"ingest": "reading", "architect": "finding", "segment": "finding", "author": "writing",
                     "validate": "testing", "dryrun": "testing", "scene": "scene"}
    assert set(kinds) == set(get_args(Stage)) == set(STAGES)
    name = _function(stages, "name")
    for kind, key in (("reading", "readingPhotos"), ("finding", "findingObjects"), ("testing", "testingRoom"),
                      ("scene", "sceneLoading")):
        assert f"if (kind === '{kind}') return strings.{key}" in name
    assert "if (attempt === 0) return strings.writingPuzzles" in name


def test_each_row_is_pending_running_done_or_failed_from_job_state():
    stages = _code("build-stages.ts")
    row = _function(stages, "row")
    assert "if (job?.status === 'done') state = 'done'" in row
    assert "else if (at === current) state = job?.status === 'running' ? 'running' : 'failed'" in row
    assert "else if (own.length > 0) state = 'done'" in row
    assert "const STOPPED = new Set<JobState['status']>(['failed', 'needs_more_photos', 'needs_recapture'])" in stages
    assert "current = key(kind, kind === 'writing' ? regenerations : Math.max(authored - 1, 0))" in stages
    rules = _css("components/stage-list.css")
    assert rules[".stage-marker"]["border"] == "2px solid var(--text-muted)"  # pending: hollow
    assert rules[".stage-marker"]["width"] == rules[".stage-marker"]["height"] == "12px"
    for state, color in (("running", "lamp"), ("done", "success"), ("failed", "error-text")):
        assert rules[f".stage-row[data-state='{state}'] .stage-marker"]["background"] == f"var(--{color})"
    assert rules[".stage-name"]["color"] == "var(--text-muted)"
    assert rules[".stage-row[data-state='running'] .stage-name"]["color"] == "var(--lamp)"
    assert rules[".stage-row[data-state='failed'] .stage-name"]["color"] == "var(--error-text)"


def test_a_done_row_shows_its_duration_result_and_model_id_from_job_state():
    stages = _code("build-stages.ts")
    assert set(StageRecord.model_fields) == {"stage", "duration_ms", "count", "model"}
    row = _function(stages, "row")
    assert "durationMs: done && own.length > 0 ? own.reduce((sum, record) => sum + record.duration_ms, 0) : null" in row
    assert "model: done && models.length > 0 ? models.join(strings.modeSeparator) : null" in row
    results = _function(stages, "results")
    assert "if (kind === 'reading') return counted(strings.photoCount, count('ingest'))" in results
    assert "if (kind === 'finding') return counted(strings.objectCount, count('segment'))" in results
    assert "if (kind === 'writing') return counted(strings.puzzleCount, count('author'))" in results
    assert "if (kind === 'scene') return counted(strings.scenesReady, count('scene'))" in results
    assert "lines.push(fill(strings.rulesPassed, { passed, total: validator.length }))" in results
    assert "lines.push(fill(strings.testRunReached, { reached: dryrun.count, total }))" in results
    assert "return fill(strings.stageDuration, { s: (ms / 1000).toFixed(1) })" in stages
    # The Finding objects row joins the architect and segment models: "muse-spark-1.3 · sam-3.1".
    assert (ARCHITECT_MODEL, SEGMENT_MODEL) == ("muse-spark-1.3", "sam-3.1")
    list_ts = _code("components/stage-list.ts")
    assert "meta.append(created.model, created.duration)" in list_ts and "text('p', 'stage-meta mono-sm')" in list_ts
    assert "text('p', 'stage-result body-sm', result)" in list_ts
    rules = _css("components/stage-list.css")
    assert rules[".stage-duration"]["color"] == "var(--success)" and rules[".stage-meta"]["color"] == "var(--text-muted)"
    assert rules[".stage-result,\n.stage-sent-back,\n.stage-line"]["color"] == "var(--text)"


def test_the_architect_line_follows_the_running_row_and_fades_in_on_each_move():
    stages = _code("build-stages.ts")
    assert "line: state === 'running' ? line(kind, attempt) : null" in _function(stages, "row")
    line = _function(stages, "line")
    assert "const reading = fill(strings.readingLine, { n: photos ?? 0 })" in line
    assert "if (kind === 'reading') return reading" in line
    assert "if (kind === 'finding') return maskPreviewLine((job?.mask_preview ?? []).map((tile) => tile.label)) ?? reading" in line
    assert "if (kind === 'writing') return attempt === 0 ? strings.writingLine : strings.regenerationLine" in line
    assert "if (kind === 'testing') return strings.testingLine" in line and "return strings.sceneLine" in line
    update = _function(_code("components/stage-list.ts"), "update")
    assert "if (row.line !== shown.line) {" in update
    assert "fading(spoken('stage-line', 'architect', row.line))" in update
    assert "reveal(list)" in update


def test_the_mask_preview_line_names_three_labels_or_two_in_segment_order():
    preview = _function(_code("build-stages.ts"), "maskPreviewLine")
    assert "const [first, second, third] = labels" in preview and "if (second === undefined) return null" in preview
    assert "fill(strings.maskPreviewLineTwo, { n, first, second })" in preview
    assert "fill(strings.maskPreviewLine, { n, first, second, third })" in preview
    assert "const n = labels.length" in preview


def test_the_riddler_introduction_fades_in_inside_writing_puzzles_and_stays():
    stages = _code("build-stages.ts")
    assert "riddler: kind === 'writing' && attempt === 0 && state !== 'pending'" in _function(stages, "row")
    update = _function(_code("components/stage-list.ts"), "update")
    assert "if (row.riddler && shown.introSlot.childElementCount === 0) {" in update
    assert "fading(introduction('riddler', strings.riddler, strings.riddlerRole, strings.riddlerVoice))" in update
    assert "introSlot.replaceChildren" not in update and "introSlot.remove" not in update  # it stays


def test_each_regeneration_adds_a_rewriting_row_with_its_sent_back_messages_and_testing_again():
    stages = _code("build-stages.ts")
    assert set(JobState.model_fields) >= {"regeneration_count", "regen_max", "sent_back", "stages", "mask_preview"}
    assert "const attempts = Math.max(1, authored, regenerations + 1)" in stages
    assert "for (let attempt = 0; attempt < attempts; attempt += 1) {\n    rows.push(row('writing', attempt))" in stages
    assert "const untested = attempt < attempts - 1 && !byKey.has(key('testing', attempt))" in stages
    assert "if (!untested) rows.push(row('testing', attempt))" in stages
    assert "return fill(strings.rewritingPuzzles, { n: attempt, max: job?.regen_max ?? 0 })" in stages
    sent = _function(stages, "sentBack")
    assert "job?.sent_back?.find((record) => record.attempt === attempt - 1)?.messages" in sent
    assert "fill(strings.sentBack, { messages: messages.join(' ') })" in sent
    assert "sentBack: kind === 'writing' && attempt > 0 ? sentBack(attempt) : null" in stages
    list_ts = _code("components/stage-list.ts")
    assert "sentBack: text('p', 'stage-sent-back body-sm')" in list_ts
    # A new attempt's rows are inserted before "Setting the scene"; a row already shown is never redrawn or moved.
    assert "if (at !== shown.element) list.insertBefore(shown.element, at ?? null)" in list_ts
    assert "if (keys.has(key)) continue\n      shown.element.remove()\n      views.delete(key)" in list_ts


# --- The Mask preview ----------------------------------------------------------------------------------------------


def test_the_mask_preview_tiles_draw_the_outline_and_the_label_chip_and_fade_in_together():
    ts = _code("components/mask-preview.ts")
    assert "const TILE: Size = { width: 120, height: 90 }" in ts
    assert "preserveAspectRatio: 'xMidYMid meet'" in ts  # contained, never cropped, like the Scene
    assert "svg('path', { class: 'mask-tile-halo', d }), svg('path', { class: 'mask-tile-outline', d })" in ts
    assert "chip.className = 'mask-tile-chip label'" in ts and "chip.textContent = label" in ts
    assert "const grid = fading(document.createElement('ul'))" in ts
    rules = _css("components/mask-preview.css")
    assert rules[".mask-tile-outline"]["fill"] == "var(--mask-overlay-fill)"
    assert rules[".mask-tile-outline"]["stroke"] == "var(--mask-overlay-stroke)"
    assert rules[".mask-tile-outline"]["stroke-width"] == "2px"
    assert rules[".mask-tile-halo"]["stroke"] == "var(--hotspot-halo)"
    assert rules[".mask-tile-chip"]["background"] == "var(--parchment)" and rules[".mask-tile-chip"]["color"] == "var(--ink)"
    tile = rules[".mask-tile"]
    assert (tile["width"], tile["height"], tile["border-radius"]) == ("120px", "90px", "var(--rounded-sm)")
    assert rules[".mask-preview"]["gap"] == "var(--spacing-3)"
    screen = _code("build-progress.ts")
    show = _function(screen, "showMask")
    assert "maskSlot.replaceChildren(grid)" in show and "reveal(grid)" in show


def test_the_mask_preview_appears_once_job_state_carries_it_on_this_pages_own_downscales():
    screen = _code("build-progress.ts")
    apply = _function(screen, "apply")
    assert "if (!masked && (job.mask_preview ?? []).length > 0) {" in apply
    photo = _function(screen, "photo")
    assert "if (held !== null) return held.downscales[index] ?? null" in photo
    assert "return job.status === 'done' && job.room_id != null ? photoUrl(job.room_id, index) : null" in photo


def test_the_mask_preview_has_no_heading_and_no_interaction():
    ts = _code("components/mask-preview.ts")
    assert not re.search(r"addEventListener|tabIndex|tabindex|button|role=|<h\d|'h\d'|aria-label", ts)
    assert _css("components/mask-preview.css")[".mask-tile"]["pointer-events"] == "none"


# --- Done: Play, or "Play this room" -----------------------------------------------------------------------------


def test_done_starts_a_session_and_opens_the_play_screen_with_the_timer_passing_to_it():
    screen = _code("build-progress.ts")
    assert "let live = held !== null" in screen
    apply = _function(screen, "apply")
    assert "if (job.status !== 'done') live = true" in apply
    assert "else if (job.room_id != null) done(job, job.room_id)" in apply
    done = _function(screen, "done")
    assert done.lstrip().startswith("if (live) {\n          void start(roomId)\n          return")
    start = _function(screen, "start")
    assert "const session = await startSession({ room_id: roomId, derived: freshDerived() })" in start
    assert start.index("sessionOpened(jobId, session.id)") < start.index(
        "location.hash = placeHref({ route: { name: 'play', sessionId: session.id }, profile })")
    assert "if (starting || started) return" in start


def test_a_build_already_done_shows_play_this_room_instead_of_starting():
    done = _function(_code("build-progress.ts"), "done")
    assert "label: strings.playThisRoom" in done and "onActivate: () => start(roomId)" in done
    assert "primaryButton({" in done and "actions.hidden = false" in done
    assert "const urls = Array.from({ length: photos }, (_, index) => photoUrl(roomId, index))" in done


def test_a_refused_session_start_shows_the_banner_whose_try_again_posts_it_again():
    start = _function(_code("build-progress.ts"), "start")
    assert "heading: strings.sessionStartRefused" in start and "sentence: strings.sessionStartRefusedBody" in start
    assert "actions: [{ label: strings.tryAgain, onActivate: () => void start(roomId) }]" in start
    assert "variant: 'error'" in start
    banner = (COMPONENTS / "error-banner.ts").read_text()
    assert "slot.replaceChildren(element)\n  element.focus()" in banner  # the banner takes focus
    # The Timer keeps running toward T1: nothing here stops it.
    assert "stopTimer" not in _code("build-progress.ts")


# --- Accessibility floor -------------------------------------------------------------------------------------------


def test_the_stage_list_is_not_a_live_region_and_every_in_character_line_names_its_speaker():
    for name in ("components/stage-list.ts", "components/mask-preview.ts", "build-progress.ts"):
        code = _code(name)
        assert "aria-live" not in code and not re.search(r"'role'|role=|\.role\b", code), name
        assert "tabIndex" not in code and "tabindex" not in code, name
    ts = _code("components/stage-list.ts")
    assert "element.append(speakerPrefix(speaker), line)" in ts
    assert "function spoken(className: string, speaker: Wizard, line: string)" in ts
    assert "text('p', `${className} wizard-line`)" in ts
    assert "prefix.className = 'visually-hidden'" in (WEB_SRC / "wizards/portrait.ts").read_text()
    hidden = _css("style.css")[".visually-hidden"]
    assert hidden["position"] == "absolute" and hidden["clip-path"] == "inset(50%)" and hidden["width"] == "1px"


def test_the_fades_are_200_ms_opacity_transitions_instant_under_reduced_motion():
    rules = _css("components/fade.css")
    assert rules[".fade"] == {"opacity": "0", "transition": "opacity var(--motion-state) var(--motion-ease)"}
    assert rules[".fade.is-shown"] == {"opacity": "1"}
    tokens = (WEB_SRC / "tokens.css").read_text()
    reduced = tokens.split("@media (prefers-reduced-motion: reduce)", 1)[1]
    assert "--motion-state: 0ms;" in reduced and "transition-duration: 0ms !important;" in reduced
    for path, text in source_css().items():
        assert "@keyframes" not in text and "animation" not in text, path


def test_every_stage_list_and_mask_preview_color_pair_is_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    pairs = {("text", "chrome-raised"), ("text-muted", "chrome-raised"), ("lamp", "chrome-raised"),
             ("success", "chrome-raised"), ("error-text", "chrome-raised"), ("ink", "parchment")}
    for fg, bg in pairs:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
