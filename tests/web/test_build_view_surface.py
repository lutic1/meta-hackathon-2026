"""FR-38, UX-DR8, UX-DR48, UX-DR53, UX-DR54, UX-DR67, UX-DR78: the Build view's header, Model table and In play block.

The client has no test runner (a runner is added only through bmad-correct-course), so these checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile. The wire values the client
keys on (the `build_not_ready` code, the Meta hosts, the roles and the cut 4 verdict) are checked against the server.
"""

import re
from typing import get_args

import httpx

from src.api.errors import BuildNotReady
from src.domain.schema import DryRunVerdict, ModelRow
from src.providers.meta_api import DEFAULT_BASE_URL, MetaModelProvider
from tests.web.design import WEB_SRC, css_rules, design_text, source_css
from tests.web.test_contrast import PROPS, _hex, contrast

COMPONENTS = WEB_SRC / "components"


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _code(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _css(name: str) -> dict[str, dict[str, str]]:
    """The stylesheet's rules, a selector list spread over several lines read as one line."""
    return {" ".join(selector.split()): rule for selector, rule in css_rules((WEB_SRC / name).read_text()).items()}


def _render() -> str:
    return _ts("shell.ts").split("async function render()", 1)[1].split("\n  }\n", 1)[0]


# --- Route, request and states ---------------------------------------------------------------------------------


def test_the_build_view_route_resolves_and_carries_the_profile():
    router = _ts("router.ts")
    assert r"const BUILD_VIEW_ROUTE = /^\/build\/([\w-]+)\/view$/" in router
    assert "if (view !== null) return { route: { name: 'view', jobId: view[1] }, profile }" in router
    assert "route.name === 'view' ? `/build/${route.jobId}/view`" in router
    # The not-ready link: the Build's Capture screen, `#/build/<job_id>`, with the profile.
    assert "return `#/build/${jobId}?profile=${encodeURIComponent(profile)}`" in router


def test_the_view_reads_get_builds_view_once_and_its_disclosure_list():
    api, render = _ts("api/index.ts"), _render()
    assert "return getJson<BuildView>(`/builds/${encodeURIComponent(jobId)}/view`)" in api
    assert "const state = await loadBuildView(place.route.jobId)" in render
    assert render.index("loadBuildView(") < render.index("show(")
    assert "if (state.name === 'ready') disclosure = state.view.disclosure" in render
    # Never through `answered`: a failed load is the view's own error state, not the unreachable strip.
    assert "answered(mine, () => loadBuildView" not in render


def test_not_ready_is_the_409_build_not_ready_keyed_on_the_job_status_and_anything_else_failed():
    api, view = _ts("api/index.ts"), _ts("build-view.ts")
    assert "this.jobStatus = detail?.status ?? null" in api
    load = view.split("export async function loadBuildView", 1)[1].split("\n}\n", 1)[0]
    assert "error.status === 409 && error.code === 'build_not_ready'" in load
    assert "if (notReady && error.jobStatus !== null) return { name: 'not-ready', jobId }" in load
    assert "return gone === null ? { name: 'failed' } : { name: 'gone', gone }" in load
    assert BuildNotReady.status == 409 and BuildNotReady.code == "build_not_ready"


def test_not_ready_shows_the_header_and_the_line_linking_to_capture_with_no_panels():
    view = _ts("build-view.ts")
    branch = view.split("if (state.name === 'not-ready') {", 1)[1].split("\n  }\n", 1)[0]
    assert "buildViewHeader(null, onBack)" in branch and "link.href = captureHref(state.jobId, profile)" in branch
    assert "link.textContent = strings.buildNotReady" in branch
    assert "return { children: [header.element, line], focus: () => link.focus() }" in branch
    assert "modelTable" not in branch and "inPlayBlock" not in branch


def test_a_failed_load_shows_the_plain_line_and_try_again_which_loads_afresh():
    view, render = _ts("build-view.ts"), _render()
    branch = view.split("if (state.name === 'failed') {", 1)[1].split("\n  }\n", 1)[0]
    assert "line.textContent = strings.buildLoadFailed" in branch and "line.className = 'body-md'" in branch
    assert "secondaryButton({ label: strings.tryAgain, onActivate: onRetry })" in branch
    assert "buildViewHeader" not in branch and "modelTable" not in branch
    assert "onRetry: () => void render()" in render


def test_back_returns_to_the_opener_or_to_home_with_the_profile():
    shell, render = _ts("shell.ts"), _render()
    assert "window.addEventListener('hashchange', () => {\n    navigated = true\n  })" in shell
    assert shell.index("navigated = true") < shell.index("window.addEventListener('hashchange', () => void render())")
    assert "if (navigated) history.back()" in render
    assert "else location.hash = placeHref({ route: { name: 'home' }, profile })" in render


# --- Layout ------------------------------------------------------------------------------------------------------


def test_only_the_body_scrolls_under_the_pinned_banner_and_top_bar_in_two_columns():
    rules = _css("shell.css")
    assert rules[".build-view-layout"]["overflow-y"] == "auto"
    assert rules[".build-view-layout"]["padding"] == "var(--spacing-frame-margin)"
    assert rules[".shell-body"]["min-height"] == "0" and rules[".shell-body"]["flex"] == "1 1 0"
    columns = rules[".build-view-columns"]
    assert columns["grid-template-columns"] == "minmax(0, 2fr) minmax(0, 1fr)"
    assert columns["column-gap"] == "var(--spacing-column-gap)"
    assert rules[".build-view-left, .build-view-right"]["min-width"] == "0"
    # The top bar holds the wordmark and the mode indicator only: the view fills neither its Timer nor its controls.
    assert "timer" not in _code(_ts("build-view.ts")) and "controls" not in _code(_ts("build-view.ts"))
    assert "element.classList.add('build-view-layout')" in _ts("shell.ts")


def test_the_right_column_holds_the_model_table_first_then_the_in_play_block():
    view = _ts("build-view.ts")
    assert "right.append(modelTable(state.view), inPlayBlock(meta), verdictTable(state.view), dryRunRows(state.view))" in view
    # The right column first in the page, for Tab order (UX-DR71); the stylesheet places it in the right third.
    assert "columns.append(right, left)" in view
    assert "return { children: [header.element, columns], focus: () => header.title?.focus() }" in view


def test_every_table_cell_wraps_so_the_table_fits_the_right_third():
    css = (COMPONENTS / "model-table.css").read_text()
    rules = _css("components/model-table.css")
    assert rules[".model-table th, .model-table td"]["overflow-wrap"] == "break-word"
    assert rules[".model-table"]["width"] == "100%" and "nowrap" not in css
    assert rules[".model-table-role"]["flex-wrap"] == "wrap"
    right_third = (1280 - 2 * 24 - 24) / 3
    assert right_third - 2 * 16 > 5 * 40, "five wrapped columns of at least 40 px fit the 1280 px right third"


# --- Header ------------------------------------------------------------------------------------------------------


def test_the_header_title_is_the_name_or_the_build_time_in_display_md():
    ts = (COMPONENTS / "build-view-header.ts").read_text()
    assert "title.className = 'build-view-title display-md'" in ts and "title.tabIndex = 0" in ts
    assert "title.textContent = view.name || time" in ts
    assert "if (view.name) heading.append(line('build-view-time body-sm', time))" in ts
    # "Tue Nov 3, 10:42": short weekday and month, day, then hours and two-digit minutes.
    assert "new Intl.DateTimeFormat('en-US', { weekday: 'short' })" in ts
    assert "new Intl.DateTimeFormat('en-US', { month: 'short' })" in ts
    assert "`${WEEKDAY.format(date)} ${MONTH.format(date)} ${date.getDate()}, ${date.getHours()}:${minutes}`" in ts
    assert "String(date.getMinutes()).padStart(2, '0')" in ts
    rules = _css("components/build-view-header.css")
    assert rules[".build-view-header"]["background"] == "var(--chrome)"


def test_the_header_shows_regenerations_each_sent_back_attempt_and_back():
    ts = (COMPONENTS / "build-view-header.ts").read_text()
    assert "withNumbers(strings.regenerations, { n: view.regeneration_count, max: view.regen_max })" in ts
    assert "number.className = 'mono-sm'" in ts
    assert "...view.sent_back.map(({ attempt, messages }) =>" in ts
    # `sent_back.attempt` is 0-based (the first failed attempt is recorded as attempt 0); the line numbers attempts
    # from 1, as the Stage list's "Rewriting puzzles, attempt n of {max}" does.
    assert "fill(strings.attemptSentBack, { k: attempt + 1, messages: messages.join(' ') })" in ts
    assert "secondaryButton({ label: strings.back, onActivate: onBack })" in ts
    # Tab order: the title, then "Back".
    assert "element.append(text, back)" in ts


# --- Model table -------------------------------------------------------------------------------------------------


def test_the_model_table_is_a_real_table_with_header_cells_and_its_caption_under_it():
    ts = (COMPONENTS / "model-table.ts").read_text()
    assert "document.createElement('table')" in ts and "table.tabIndex = 0" in ts
    assert ("for (const heading of [strings.modelRole, strings.modelModel, strings.modelHost, strings.modelWhat, "
            "strings.modelBilling])") in ts
    assert "th.scope = 'col'" in ts and "role.scope = 'row'" in ts
    assert "caption.textContent = strings.modelCaption" in ts and "table.append(caption, head, body)" in ts
    assert _css("components/model-table.css")[".model-table"]["caption-side"] == "bottom"


def test_wizard_rows_lead_with_a_24px_portrait_and_carry_their_role_lines_full_width():
    ts = (COMPONENTS / "model-table.ts").read_text()
    assert "roleCell(wizardPortrait(who, 24), name)" in ts
    assert "roleLines(models('architect'), wizard('architect', strings.architect)).map(bodyRow)" in ts
    assert "roleLineRow(strings.architectRole)" in ts and "roleLineRow(strings.riddlerRole)" in ts
    assert "line.colSpan = 5" in ts
    # One row per model, the portrait and name on the first only.
    assert "role: index === 0 ? label() : null" in ts
    assert "cell('td', line.model, line.id ? 'mono-sm model-table-id' : 'body-sm')" in ts


def test_the_fixed_rows_and_no_guide_or_trickster_row():
    ts = (COMPONENTS / "model-table.ts").read_text()
    validator = ts.split("role: roleCell(strings.validator),", 1)[1].split("}),", 1)[0]
    assert "model: strings.validatorModel" in validator and "id: false" in validator
    assert "host: strings.hostThisMac" in validator and "did: strings.validatorDid" in validator
    assert "billing: ''" in validator
    assert "did: DRY_RUN_OFF, billing: ''" in ts and "model: '', id: true, host: ''" in ts
    assert "roleLines(models('dryrun'), () => roleCell(strings.dryRun))" in ts
    # A Build with no Dry run verdict at all reads "skipped" here too, as the Dry run rows and the graph read it.
    assert "const dryRunOff = view.dry_run.every(({ verdict }) => verdict === DRY_RUN_OFF)" in ts
    assert "dry_run.length" not in ts
    muse = ts.split("role: roleCell(strings.museImage),", 1)[1].split("}),", 1)[0]
    assert "model: strings.museImageModel" in muse and "did: strings.museImageDid" in muse
    assert "host: strings.hostMeta" in muse
    code = _code(ts)
    assert not re.search(r"strings\.(guide|trickster)|models\('trickster'\)", code)


def test_cached_or_billed_spells_both_counts_and_meta_rows_read_meta_model_api():
    ts = (COMPONENTS / "model-table.ts").read_text()
    assert "billed > 0 ? fill(strings.billed, { n: billed }) : ''" in ts
    assert "cached > 0 ? fill(strings.cached, { n: cached }) : ''" in ts
    assert "counts.filter((count) => count !== '').join(strings.modeSeparator)" in ts
    assert "return META_HOSTS.has(host) ? strings.hostMeta : host" in ts


def test_the_wire_values_the_model_table_keys_on_are_the_servers():
    ts = (COMPONENTS / "model-table.ts").read_text()
    hosts = set(re.findall(r"'([^']+)'", ts.split("const META_HOSTS = new Set([", 1)[1].split("])", 1)[0]))
    assert hosts == {MetaModelProvider.name, httpx.URL(DEFAULT_BASE_URL).host}
    assert "const DRY_RUN_OFF: DryRunVerdict['verdict'] = 'skipped'" in ts
    assert "skipped" in get_args(DryRunVerdict.model_fields["verdict"].annotation)
    roles = set(get_args(ModelRow.model_fields["role"].annotation))
    assert {"architect", "riddler", "dryrun", "image"} <= roles
    for role in ("architect", "riddler", "dryrun", "image"):
        assert f"models('{role}')" in ts


# --- In play block -----------------------------------------------------------------------------------------------


def test_the_in_play_block_reads_get_meta_for_the_guide_and_the_trickster():
    ts = (COMPONENTS / "in-play-block.ts").read_text()
    assert "live: strings.sourceLive," in ts and "scripted: strings.sourceScripted," in ts and "cut1: strings.sourceCut1," in ts
    assert "if (meta.guide_model === null) return text('in-play-model body-sm', strings.guideWritten)" in ts
    assert "id.textContent = strings.guideModel" in ts and "id.className = 'mono-sm'" in ts
    assert "strings.modeSeparator, strings.hostOllama" in ts
    assert "meta.guide === 'ollama' ? strings.guideRoleLocal : strings.guideRoleWritten" in ts
    assert "wizardPortrait(wizard, 32)" in ts and "block.tabIndex = 0" in ts
    assert "SOURCES[meta.trickster]" in ts
    assert "addEventListener" not in ts, "the block is static"


# --- Accessibility floor -----------------------------------------------------------------------------------------


def test_initial_focus_is_the_title_and_the_tab_stops_run_title_back_table_block():
    shell = _ts("shell.ts")
    assert "view.focus()" in shell
    header = (COMPONENTS / "build-view-header.ts").read_text()
    # DOM order is Tab order: the title in the header text, "Back" after it, then the right column's two stops.
    assert header.index("title.tabIndex = 0") < header.index("element.append(text, back)")
    assert "table.tabIndex = 0" in (COMPONENTS / "model-table.ts").read_text()
    assert "block.tabIndex = 0" in (COMPONENTS / "in-play-block.ts").read_text()
    assert "tabIndex = -1" not in _code(header)


def test_wizard_rows_use_the_wizard_portrait_at_24_and_32_px():
    assert "wizardPortrait(who, 24)" in (COMPONENTS / "model-table.ts").read_text()
    assert "wizardPortrait(wizard, 32)" in (COMPONENTS / "in-play-block.ts").read_text()
    portrait = _ts("wizards/portrait.ts")
    assert "export function wizardPortrait(wizard: Wizard, size: PortraitSize): HTMLElement" in portrait
    assert "display-sm" in portrait  # the placeholder initial in display-sm, never Garamond below 17 px
    assert _css("wizards/portrait.css")[".wizard-portrait"]["border"] == "2px solid var(--gilt)"


def test_every_build_view_text_pair_meets_aa():
    table = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = [[re.findall(r"`([\w-]+)`", cell) for cell in line.strip("|").split("|")[:2]]
            for line in table.splitlines() if line.startswith("| `")]
    for fg, bg in (("text", "chrome"), ("text-muted", "chrome"), ("lamp", "chrome"), ("focus-ring", "chrome")):
        assert any(fg in f and bg in b for f, b in rows), f"{fg} on {bg} is not in the DESIGN.md contrast table"
    # Two pairs the table does not list, computed here: the not-ready link on the page and the portrait initial.
    assert contrast(_hex(PROPS["lamp"])[0], _hex(PROPS["canvas"])[0]) >= 4.5
    assert contrast(_hex(PROPS["gilt"])[0], _hex(PROPS["chrome-raised"])[0]) >= 4.5


def test_the_build_view_adds_no_motion():
    for path, text in source_css().items():
        if any(name in path for name in ("build-view-header", "model-table", "in-play-block", "wizards/portrait")):
            assert not re.search(r"transition|animation|@keyframes", text), path
