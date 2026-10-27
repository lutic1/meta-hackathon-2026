"""FR-1, FR-6, NFR-4, UX-DR14, UX-DR15, UX-DR20, UX-DR21, UX-DR62, UX-DR82, AR-10: the Capture screen before a Build.

The client has no test runner (a runner is added only through bmad-correct-course), so these checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile. The numbers and field names
the client shares with ingest are compared with the server's own constants.
"""

import re
from io import BytesIO

from PIL import Image

from src.api.app import DOWNSCALE, ORIGINAL
from src.pipeline.ingest import LONG_EDGE, MAX_PHOTOS, MIN_PHOTOS
from tests.web.design import WEB_SRC, css_rules, design_text, source_ts

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
    return text.split(f"function {name}(", 1)[1].split("{\n", 1)[1].split("\n  }\n", 1)[0]


# --- Cold load and the right column ------------------------------------------------------------------------------


def test_local_home_is_the_capture_screen_built_from_the_same_get_meta():
    shell = _ts("shell.ts")
    render = shell.split("async function render()", 1)[1].split("\n  }\n", 1)[0]
    assert render.index("getMeta(place.profile)") < render.index("show(")
    assert "content = { name: 'rooms', rooms, profile: place.profile, retention: meta.retention }" in render
    assert "const capture = captureScreen(content.rooms, content.profile, content.retention, timerSlot)" in shell
    assert "element.append(capture.left, capture.right)" in shell and "mount: capture.mount" in shell
    # While GET /meta fails the shell shows only the unreachable strip, retried every 2000 ms (1.17).
    assert "export const RETRY_MS = 2000" in shell and "show(unreachable())" in shell


def test_the_right_column_holds_the_three_lines_then_the_retention_summary_in_order():
    capture = _ts("capture.ts")
    assert ("right.append(line(strings.inputRequirement), line(strings.iphoneTip), line(strings.reminder), "
            "retentionSummary(retention))") in capture
    assert "element.className = 'capture-line body-md'" in capture
    # Built with the screen, before any photo is chosen: nothing in the right column waits on the set.
    assert capture.index("right.append(") < capture.index("function choose(")
    rules = _css("shell.css")
    assert rules[".capture-line"]["color"] == "var(--text)"
    assert rules[".capture-right"]["gap"] == "var(--spacing-4)"
    text = (WEB_SRC / "shell.css").read_text()
    assert re.search(r"^\.capture-layout \{[^}]*grid-template-columns: minmax\(0, 1fr\) var\(--spacing-side-column\);",
                     text, re.MULTILINE)
    # The right column narrows with the Play side column: 360 px at 1280 to 1439, 340 px at 1024 to 1279.
    assert re.findall(r"@media \(max-width: (\d+)px\) \{\s*\.capture-layout \{\s*grid-template-columns: "
                      r"minmax\(0, 1fr\) ([^;]+);", text) == [("1439", "360px"), ("1279", "340px")]


def test_the_retention_summary_renders_the_served_text_then_the_privacy_line_never_truncated():
    ts = (COMPONENTS / "retention-summary.ts").read_text()
    assert "text.textContent = retention" in ts and "innerHTML" not in ts
    assert "heading.textContent = strings.retentionHeading" in ts and "heading.className = 'retention-heading display-sm'" in ts
    assert "text.className = 'retention-text body-sm'" in ts
    assert "label.className = 'retention-label label'" in ts and "label.textContent = strings.playHistory" in ts
    assert "privacy.className = 'retention-privacy body-md'" in ts and "privacy.textContent = strings.privacyLine" in ts
    assert "summary.append(heading, text, label, privacy)" in ts
    assert not re.search(r"button|addEventListener|hidden|details|tabIndex", ts.split("*/", 1)[1])
    rules = _css("components/retention-summary.css")
    assert rules[".retention-summary"]["background"] == "var(--chrome-raised)"
    assert rules[".retention-summary"]["border-radius"] == "var(--rounded-md)"
    assert rules[".retention-text"]["color"] == "var(--text-muted)"
    assert rules[".retention-privacy"] == {"margin": "0", "font-weight": "600", "color": "var(--text)"}
    for rule in rules.values():
        assert not {"overflow", "max-height", "height", "text-overflow", "-webkit-line-clamp", "white-space"} & set(rule)


def test_the_left_area_is_the_banner_slot_then_the_dropzone_the_tray_upload_and_the_stored_rooms():
    capture = _ts("capture.ts")
    assert "controls.append(dropzone.element, tray, actions, storedRooms(rooms, profile, banners))" in capture
    assert "left.append(banners, controls)" in capture
    assert "const controls = document.createElement('fieldset')" in capture
    rules = _css("shell.css")
    assert rules[".capture-controls"] == {"margin": "0", "padding": "0", "border": "0"}


# --- The dropzone and the Photo tray -----------------------------------------------------------------------------


def test_the_dropzone_takes_drops_and_picks_with_the_picker_sentence_and_choose_photos():
    ts = (COMPONENTS / "capture-dropzone.ts").read_text()
    assert "sentence.textContent = strings.pickerSentence" in ts and "sentence.className = 'capture-dropzone-sentence body-md'" in ts
    assert "secondaryButton({ label: strings.choosePhotos, onActivate: () => open(false) })" in ts
    assert "input.type = 'file'" in ts and "input.multiple = true" in ts
    for event in ("dragover", "dragleave", "drop", "change"):
        assert f"addEventListener('{event}'" in ts
    assert "if (files.length > 0 && !disabled()) onFiles(files, false)" in ts  # a drop joins the set
    assert "chooseAgain: () => open(true)" in ts  # "Choose photos again" replaces it
    assert "button.matches(':disabled')" in ts  # its own flag or the Build's disabled fieldset
    rules = _css("components/capture-dropzone.css")
    zone = rules[".capture-dropzone"]
    assert zone["background"] == "var(--chrome-raised)" and zone["border"] == "2px dashed var(--hairline)"
    assert zone["border-radius"] == "var(--rounded-lg)" and zone["min-height"] == "320px"
    assert rules[".capture-dropzone.drag-over"] == {"border-color": "var(--lamp)"}


def test_the_tray_shows_120_by_90_thumbnails_in_upload_order_with_the_count_and_remove_controls():
    ts = (COMPONENTS / "photo-tray.ts").read_text()
    assert "count.textContent = fill(strings.photosChosen, { n: photos.length })" in ts
    assert "count.className = 'photo-tray-count label'" in ts
    assert "image.width = 120" in ts and "image.height = 90" in ts and "image.alt = ''" in ts
    assert "remove.setAttribute('aria-label', fill(strings.removePhoto, { n: index + 1 }))" in ts
    assert "remove.type = 'button'" in ts and "remove.addEventListener('click', () => onRemove(index))" in ts
    assert "const grid = document.createElement('ol')" in ts and "photos.map(" in ts
    assert not re.search(r"\.sort\(|\.reverse\(", ts), "upload order is the order chosen"
    rules = _css("components/photo-tray.css")
    thumb = rules[".photo-tray-thumb"]
    assert (thumb["width"], thumb["height"], thumb["border-radius"]) == ("120px", "90px", "var(--rounded-sm)")
    assert rules[".photo-tray-grid"]["gap"] == "var(--spacing-3)"
    remove = rules[".photo-tray-remove"]
    assert (remove["width"], remove["height"]) == ("32px", "32px")
    assert remove["background"] == "var(--scrim)" and remove["color"] == "var(--text)"
    assert remove["border"] == "1px solid var(--hairline)" and remove["border-radius"] == "var(--rounded-md)"
    assert (remove["top"], remove["right"]) == ("var(--spacing-1)", "var(--spacing-1)")


def test_a_rejected_file_has_the_2px_wrong_border_and_not_a_jpeg_and_stays_removable():
    ts = (COMPONENTS / "photo-tray.ts").read_text()
    assert "thumb.classList.toggle('rejected', rejected)" in ts
    assert "why.textContent = strings.notAJpeg" in ts and "why.className = 'photo-tray-why label'" in ts
    rejected = ts.split("if (rejected) {", 1)[1].split("}", 1)[0]
    assert "remove" not in rejected  # the remove control is drawn for every file, rejected or not
    rules = _css("components/photo-tray.css")
    assert rules[".photo-tray-thumb.rejected"]["outline"] == "2px solid var(--wrong)"
    assert rules[".photo-tray-why"]["color"] == "var(--wrong)"
    assert "rejected: !jpeg" in _ts("capture.ts")


# --- Validation: all or nothing ----------------------------------------------------------------------------------


def test_the_set_rule_is_ingest_s_6_to_10_jpegs_checked_by_bytes():
    photos = _ts("photos.ts")
    assert f"export const MIN_PHOTOS = {MIN_PHOTOS}" in photos and f"export const MAX_PHOTOS = {MAX_PHOTOS}" in photos
    assert ("return photos.length >= MIN_PHOTOS && photos.length <= MAX_PHOTOS && photos.every((photo) => photo.jpeg)"
            in photos)
    assert "await file.slice(0, JPEG_START.length).arrayBuffer()" in photos
    assert not re.search(r"\.name|\.type\b|endsWith", _code("photos.ts")), "the bytes decide, never the name or type"


def _jpeg_start() -> bytes:
    literal = re.search(r"const JPEG_START = \[([^\]]+)\]", _ts("photos.ts")).group(1)
    return bytes(int(byte, 16) for byte in literal.split(","))


def _encoded(fmt: str) -> bytes:
    out = BytesIO()
    Image.new("RGB", (8, 6), "white").save(out, format=fmt)
    return out.getvalue()


def test_the_byte_check_passes_a_real_jpeg_and_refuses_a_png_and_a_heic_renamed_jpg():
    start = _jpeg_start()
    assert _encoded("JPEG").startswith(start)
    assert not _encoded("PNG").startswith(start)
    heic = b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00mif1heic"  # an ISO BMFF header, whatever the file is named
    assert not heic.startswith(start)


def test_every_change_revalidates_and_a_refused_set_shows_the_fr1_banner_with_no_sentence():
    capture = _ts("capture.ts")
    refused = "const refused: BannerState = { variant: 'error', heading: strings.photosRefused, actions: [chooseAgain] }"
    assert refused in capture
    assert "const chooseAgain = { label: strings.choosePhotosAgain, onActivate: dropzone.chooseAgain }" in capture
    validate = _function(capture, "validate")
    assert "const refusedSet = photos.length > 0 && !isValidSet(photos)" in validate
    assert "if (refusedSet && !refusal?.isConnected) show(refused)" in validate
    assert "else if (!refusedSet && refusal?.isConnected) show(null)" in validate  # a valid set clears the banner
    for change in ("choose", "remove"):
        body = _function(capture, change)
        assert "render()" in body and body.rstrip().endswith("validate()"), change


def test_upload_is_enabled_only_for_a_valid_set_so_a_refused_set_sends_nothing():
    capture = _ts("capture.ts")
    assert "upload.disabled = true" in capture  # Empty: Upload disabled
    assert "upload.disabled = !isValidSet(photos)" in _function(capture, "render")
    assert _function(capture, "send").lstrip().startswith("if (!isValidSet(photos)) return")
    # POST /builds is the only request the screen makes, and only Upload reaches it.
    assert capture.count("postBuild(") == 1 and "fetch(" not in capture


def test_a_removal_moves_focus_to_the_next_remove_control_or_choose_photos():
    remove = _function(_ts("capture.ts"), "remove")
    assert "photos = photos.filter((_, other) => other !== index)" in remove
    assert "(removes[Math.min(index, removes.length - 1)] ?? dropzone.button).focus()" in remove


# --- Upload ------------------------------------------------------------------------------------------------------


def test_each_photo_is_downscaled_in_a_canvas_with_exif_orientation_to_a_1280_long_edge_at_0_85():
    photos = _ts("photos.ts")
    assert f"export const LONG_EDGE = {LONG_EDGE}" in photos and "export const JPEG_QUALITY = 0.85" in photos
    assert "createImageBitmap(file, { imageOrientation: 'from-image' })" in photos
    assert "document.createElement('canvas')" in photos and "context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)" in photos
    assert "canvas.width = width >= height ? LONG_EDGE :" in photos
    assert "canvas.height = width >= height ? Math.max(1, Math.round((height * LONG_EDGE) / width)) : LONG_EDGE" in photos
    assert "'image/jpeg', JPEG_QUALITY)" in photos


def test_every_downscale_goes_with_its_original_in_one_multipart_post_builds():
    api, capture = _ts("api/index.ts"), _ts("capture.ts")
    assert f"const DOWNSCALE = '{DOWNSCALE}'" in api and f"const ORIGINAL = '{ORIGINAL}'" in api
    post = api.split("export function postBuild(", 1)[1]
    assert "const body = new FormData()" in post
    assert "body.append(DOWNSCALE, downscale, `${index}.jpg`)" in post and "body.append(ORIGINAL, original, original.name)" in post
    assert "return postJson<JobState>('/builds', body)" in post
    # FormData goes as is, so the browser writes the multipart boundary; JSON bodies keep their content type.
    assert "body instanceof FormData" in api and "{ method: 'POST', headers: { Accept: 'application/json' }, body }" in api
    assert "pairs.push({ downscale: await downscale(file), original: file })" in capture
    assert capture.count("await postBuild(pairs)") == 1


def test_while_the_upload_is_pending_upload_shows_its_pending_label_and_the_dropzone_is_disabled():
    capture = _ts("capture.ts")
    assert "primaryButton({ label: strings.upload, pendingLabel: strings.readingPhotos, onActivate: send })" in capture
    render = _function(capture, "render")
    assert "dropzone.button.disabled = uploading" in render and "photoTray(shown, remove, uploading)" in render
    send = _function(capture, "send")
    assert send.index("render(true)") < send.index("await submit(photos)") < send.index("render()")
    assert "remove.disabled = disabled" in (COMPONENTS / "photo-tray.ts").read_text()


def test_the_client_calls_only_its_own_server_under_api():
    for path, text in source_ts().items():
        # The SVG namespace the Scene's Hotspots are created in is a name, never a request.
        text = text.replace("'http://www.w3.org/2000/svg'", "")
        assert not re.search(r"https?:|wss?:|\bnew (WebSocket|EventSource)\(|sendBeacon", text), path
        for call in re.findall(r"fetch\(([^,)]+)", text):
            assert call == "`/api${path}`", f"{path} fetches {call}"
    # Thumbnails are local object URLs of the chosen files, never a request.
    assert "url: URL.createObjectURL(file)" in _ts("capture.ts") and "URL.revokeObjectURL(url)" in _ts("capture.ts")


# --- Refusals and failures ---------------------------------------------------------------------------------------


def test_422_codes_and_failures_map_to_their_banners_and_the_photos_stay():
    capture = _ts("capture.ts")
    assert "const FR1_CODES = new Set(['unsupported_image', 'photo_count'])" in capture
    submit = _function(capture, "submit")
    assert "error instanceof RequestFailed && error.status === 422 ? error.code : null" in submit
    assert "if (code !== null && FR1_CODES.has(code)) return refused" in submit
    assert "return code === 'bad_downscale' ? unreadable : failed" in submit  # network, 5xx and the rest: failed
    assert "const unreadable: BannerState = { variant: 'error', heading: strings.photosUnreadable, actions: [chooseAgain] }" in capture
    failed = capture.split("const failed: BannerState = {", 1)[1].split("\n  }\n", 1)[0]
    assert "heading: strings.uploadFailed" in failed and "sentence: strings.uploadFailedBody" in failed
    assert "actions: [{ label: strings.tryAgain, onActivate: () => upload.click() }]" in failed  # the same set
    # Nothing in a refusal or failure touches the set.
    assert "photos =" not in submit and "photos =" not in _function(capture, "send")
    api = _ts("api/index.ts")
    assert "if (!response.ok) throw new RequestFailed(path, response.status, await errorCode(response))" in api
    assert "return ((await response.json()) as ErrorEnvelope).error.code" in api


def test_banners_are_the_shared_error_banner_one_at_a_time_and_take_focus():
    capture = _ts("capture.ts")
    assert "const element = showBanner(banners, state)" in capture
    assert "refusal = state === refused ? element : null" in capture
    banner = (COMPONENTS / "error-banner.ts").read_text()
    assert "slot.replaceChildren(element)\n  element.focus()\n  return element" in banner


def test_an_accepted_upload_disables_everything_but_the_retention_summary_and_the_banners():
    capture = _ts("capture.ts")
    send = _function(capture, "send")
    assert "show(outcome)" in send and "if (outcome === null) controls.disabled = true" in send
    # The banners and the right column sit outside the fieldset the Build disables.
    assert "left.append(banners, controls)" in capture and "right.append(" in capture
    assert "controls.append(" in capture and "banners" not in capture.split("controls.append(", 1)[1].split("storedRooms(", 1)[0]


# --- Accessibility floor -----------------------------------------------------------------------------------------


def test_initial_focus_is_on_choose_photos_and_every_control_is_a_native_button():
    capture = _ts("capture.ts")
    assert "mount: () => {\n      dropzone.button.focus()" in capture
    for name in ("capture.ts", "components/capture-dropzone.ts", "components/photo-tray.ts", "components/retention-summary.ts"):
        code = _code(name)
        assert "tabIndex" not in code and "role=" not in code, name
    assert "document.createElement('button')" in (COMPONENTS / "photo-tray.ts").read_text()
    for name in ("components/photo-tray.css", "components/capture-dropzone.css", "components/retention-summary.css"):
        assert not re.search(r"outline:\s*(none|0)", (WEB_SRC / name).read_text()), name


def test_every_capture_color_pair_is_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    pairs = {("text", "canvas"), ("text", "chrome-raised"), ("text-muted", "chrome-raised"), ("wrong", "chrome-raised"),
             ("lamp", "chrome-raised"), ("on-lamp", "lamp"), ("error-text", "error-surface"),
             ("text", "error-surface"), ("lamp", "error-surface")}
    for fg, bg in pairs:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
