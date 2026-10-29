"""FR-26, UX-DR7, UX-DR8, UX-DR12, UX-DR21, UX-DR56, UX-DR61, UX-DR80: the app shell, read from its source.

The client has no test runner (a runner is added only through bmad-correct-course), so these checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile.
"""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.api.test_app import make_app
from tests.web.design import REPO, WEB_SRC, css_rules, design_text, source_ts
from tests.web.test_strings import _strings

COMPONENTS = WEB_SRC / "components"
PLAY_WIDTHS = {1440: 400, 1280: 360, 1024: 340}


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _css(name: str) -> dict[str, dict[str, str]]:
    return css_rules((WEB_SRC / name).read_text())


def test_nothing_renders_before_meta_answers_and_failures_retry_every_2000_ms():
    shell = _ts("shell.ts")
    assert "export const RETRY_MS = 2000" in shell
    assert "await sleep(RETRY_MS)" in shell and "show(unreachable())" in shell
    # The surface renders only after GET /meta (and, on a Room-bound route, the session state) answered.
    render = shell.split("async function render()", 1)[1].split("\n  }\n", 1)[0]
    assert render.index("getMeta(place.profile)") < render.index("show(")
    assert render.index("getSession(sessionId)") < render.index("show(")
    unreachable = shell.split("function unreachable()", 1)[1]
    assert "element.append(statusStrip(strings.serverUnreachable))" in unreachable
    assert "disclosureBanner" not in unreachable and "topBar" not in unreachable
    assert css_rules((WEB_SRC / "shell.css").read_text())[".shell-unreachable"]["place-items"] == "center"


def test_meta_is_read_once_per_profile_and_the_profile_reaches_get_meta():
    shell, api = _ts("shell.ts"), _ts("api/index.ts")
    assert "metas.get(place.profile) ??" in shell and "metas.set(place.profile, meta)" in shell
    assert "`/meta?profile=${encodeURIComponent(profile)}`" in api
    assert "fetch(`/api${path}`" in api  # one origin, routes under /api/ (AD-9)


def test_disclosure_lines_come_from_meta_on_home_and_from_session_state_on_play_and_done():
    shell = _ts("shell.ts")
    assert "let disclosure = meta.disclosure" in shell and "if (state !== null) disclosure = state.disclosure" in shell
    assert "if (place.route.name === 'play' || place.route.name === 'done' || place.route.name === 'triggers')" in shell
    # A 4xx is an answer, not an unreachable server: no retry, and no Room whose lines could be missing.
    assert "getSession(sessionId).catch(refused)" in shell
    assert "error instanceof RequestFailed && error.status !== null && error.status < 500" in shell
    # The top bar, then the body, then the banner: the footer strip of the frame, under the body.
    assert "const bar = topBar(meta, played)" in shell
    assert "show(bar.element, body.element, ...(banner === null ? [] : [banner]))" in shell


def test_disclosure_banner_renders_lines_as_served_with_no_control_and_no_focus():
    ts = (COMPONENTS / "disclosure-banner.ts").read_text()
    assert "if (lines.length === 0) return null" in ts
    assert "row.textContent = line" in ts and "innerHTML" not in ts
    assert not re.search(r"tabIndex|button|focus|close|addEventListener", ts.split("*/", 1)[1])
    rules = _css("components/disclosure-banner.css")
    banner = rules[".disclosure-banner"]
    assert banner["background"] == "var(--disclosure-surface)" and banner["color"] == "var(--disclosure-text)"
    assert banner["border-top"] == "1px solid var(--disclosure-edge)" and banner["border-radius"] == "var(--rounded-none)"
    line = rules[".disclosure-banner p"]
    assert line["min-height"] == "var(--spacing-disclosure-min)" and "body-sm" in ts
    for rule in rules.values():
        assert not {"position", "z-index", "opacity"} & set(rule), "the banner sits in the flow, never over the Scene"


def test_top_bar_is_48px_chrome_with_wordmark_mode_indicator_and_centered_timer_slot():
    rules = _css("components/top-bar.css")
    bar = rules[".top-bar"]
    assert bar["height"] == "var(--spacing-top-bar)" and bar["background"] == "var(--chrome)"
    assert bar["grid-template-columns"] == "minmax(0, 1fr) auto minmax(0, 1fr)"
    ts = (COMPONENTS / "top-bar.ts").read_text()
    assert "wordmark.className = 'top-bar-wordmark display-sm'" in ts and "wordmark.textContent = strings.wordmark" in ts
    assert "element.append(start, timer, controls)" in ts and "timer.className = 'top-bar-timer'" in ts


def test_mode_indicator_is_plain_body_sm_text_not_focusable_and_not_a_disclosure():
    ts = (COMPONENTS / "top-bar.ts").read_text()
    assert "mode.className = 'mode-indicator body-sm'" in ts and "mode.textContent = modeIndicatorText(meta, played)" in ts
    assert "if (meta.mode === 'hosted') return strings.modeHosted" in ts
    assert "meta.cache === 'on' ? strings.cacheOn : strings.cacheOff" in ts
    assert "fill(strings.modeProfile, { name: meta.profile }), rooms].join(strings.modeSeparator)" in ts
    assert not re.search(r"tabIndex|addEventListener|disclosure", ts)
    indicator = _css("components/top-bar.css")[".mode-indicator"]
    assert indicator["color"] == "var(--text-muted)" and not any("disclosure" in v for v in indicator.values())


def test_no_surface_offers_a_cache_clear_control():
    for path, text in {**source_ts(), "web/index.html": (REPO / "web/index.html").read_text()}.items():
        assert not re.search(r"clear\W{0,3}(the\W)?cache|cache\W{0,3}clear", text, flags=re.IGNORECASE), path


def _side_column_at(width: int) -> str:
    text = (WEB_SRC / "shell.css").read_text()
    base = re.search(r"^\.play-layout \{[^}]*grid-template-columns: minmax\(0, 1fr\) ([^;]+);", text, re.MULTILINE).group(1)
    bands = re.findall(r"@media \(max-width: (\d+)px\) \{\s*\.play-layout \{\s*grid-template-columns: minmax\(0, 1fr\) "
                       r"([^;]+);", text)
    value = base
    for limit, column in sorted(bands, key=lambda band: -int(band[0])):
        if width <= int(limit):
            value = column
    return value


@pytest.mark.parametrize("width,side", PLAY_WIDTHS.items())
def test_play_layout_side_column_per_width_with_24px_margins_and_no_horizontal_scroll(width, side):
    tokens = {"var(--spacing-side-column)": "400px"}
    column = _side_column_at(width)
    assert tokens.get(column, column) == f"{side}px"
    layout = _css("shell.css")[".play-layout"]
    assert layout["padding"] == "var(--spacing-frame-margin)" and layout["column-gap"] == "var(--spacing-column-gap)"
    assert width - 2 * 24 - 24 - side > 0  # the Scene column keeps a positive width, so nothing overflows
    for selector in (".scene-column", ".side-column"):
        assert _css("shell.css")[selector]["min-width"] == "0"


def test_hash_routes_resolve_and_carry_the_profile():
    router = _ts("router.ts")
    assert r"const SESSION_ROUTE = /^\/(play|done|triggers)\/([\w-]+)$/" in router
    assert "{ route: { name: 'home' }, profile }" in router
    assert "`#${path}?profile=${encodeURIComponent(profile)}`" in router  # carried on every route
    assert "new URLSearchParams(query).get('profile') || new URLSearchParams(search).get('profile') || carried" in router
    assert "export function parsePlace(hash: string, search: string, carried = DEFAULT_PROFILE)" in router
    assert "export const DEFAULT_PROFILE = 'dev'" in router and "carried = place.profile" in router
    assert "history.replaceState(history.state, '', href)" in router
    assert "window.addEventListener('hashchange', () => void render())" in _ts("shell.ts")


def test_error_banner_replaces_the_older_one_takes_focus_and_has_no_portrait():
    ts = (COMPONENTS / "error-banner.ts").read_text()
    assert "slot.replaceChildren(element)\n  element.focus()" in ts
    assert "element.tabIndex = -1" in ts and "element.setAttribute('role', 'alert')" in ts
    assert "title.className = 'banner-heading display-sm'" in ts and "body.className = 'banner-sentence body-md'" in ts
    assert "secondaryButton(action)" in ts
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", ts, flags=re.DOTALL)
    assert not re.search(r"portrait|<img|createElement\('img'\)", code)
    rules = _css("components/error-banner.css")
    assert rules[".banner"]["width"] == "100%" and rules[".banner"]["border-radius"] == "var(--rounded-md)"
    for variant in ("error", "warning"):
        assert rules[f".banner-{variant}"] == {"background": f"var(--{variant}-surface)",
                                               "border-left": f"4px solid var(--{variant}-edge)"}
        assert rules[f".banner-{variant} .banner-heading"] == {"color": f"var(--{variant}-text)"}


def test_status_strip_is_32px_plain_and_takes_no_focus():
    ts = (COMPONENTS / "status-strip.ts").read_text()
    assert "strip.className = 'status-strip body-sm'" in ts and not re.search(r"tabIndex|focus\(", ts)
    strip = _css("components/status-strip.css")[".status-strip"]
    assert strip["height"] == "var(--spacing-status-strip)"
    assert strip["background"] == "var(--warning-surface)" and strip["color"] == "var(--text)"


def test_every_shell_color_pair_is_in_the_contrast_table():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    pairs = {("disclosure-text", "disclosure-surface"), ("text", "chrome"), ("text-muted", "chrome"),
             ("text", "warning-surface"), ("error-text", "error-surface"), ("text", "error-surface"),
             ("warning-text", "warning-surface"), ("lamp", "error-surface"), ("lamp", "warning-surface")}
    for fg, bg in pairs:
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"


def test_a_profile_name_the_server_refuses_stops_the_retry_loop_and_offers_the_dev_profile(tmp_path: Path):
    """Decision record Oct 29, item 67: a 422 `invalid_profile_name` is an input error, never "can't reach its server"."""
    shell = _ts("shell.ts")
    refused = shell.split("function refusedProfile(error: unknown): null {", 1)[1].split("\n}\n", 1)[0]
    assert "if (error instanceof RequestFailed && error.code === 'invalid_profile_name') return null" in refused
    assert "throw error" in refused  # anything else is still retried as unreachable
    render = shell.split("async function render()", 1)[1].split("\n  }\n", 1)[0]
    assert "await answered(mine, () => getMeta(place.profile).catch(refusedProfile))" in render
    assert render.index("if (meta === undefined) return") < render.index("if (meta === null) return showRefusedProfile(place)")
    assert render.index("if (meta === null) return showRefusedProfile(place)") < render.index("metas.set(place.profile, meta)")
    page = shell.split("function showRefusedProfile(place: Place): void {", 1)[1].split("\n  }\n", 1)[0]
    assert "heading: fill(strings.profileNameRefused, { name: place.profile })" in page
    assert "sentence: strings.profileNameRefusedBody" in page and "label: strings.useDevProfile" in page
    assert "location.hash = placeHref({ route: place.route, profile: DEFAULT_PROFILE })" in page  # nothing deleted
    assert "showBanner(slot, {" in page and "disclosureBanner" not in page and "topBar" not in page
    strings = _strings()
    assert strings["profileNameRefused"] == "Keyframe can't use the profile name “{name}”."
    assert strings["useDevProfile"] == "Use the dev profile"
    # The server's answer the client keys on.
    response = TestClient(make_app(tmp_path)).get("/api/meta", params={"profile": ".."})
    assert response.status_code == 422 and response.json()["error"]["code"] == "invalid_profile_name"
