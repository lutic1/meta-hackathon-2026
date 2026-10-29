"""FR-26, NFR-12, UX-DR56, UX-DR80, UX-DR86: every Room-bound surface shows its own Room's Disclosures, as served.

The banner component runs in Node (which strips the types) over a stub document, so a served list is rendered as it
ships, an unknown line included. The rest reads the TypeScript and the stylesheets, as the other web tests do (the
client has no test runner); `npm run build` and `tsc --noEmit` prove they compile.
"""

import json
import re
import shutil
import subprocess
from typing import Any

import pytest

from tests.web.design import REPO, WEB_SRC, css_rules, source_css, source_ts

COMPONENTS = WEB_SRC / "components"
EXPERIENCE = REPO / "docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/EXPERIENCE.md"

# Renders each list read from stdin with the shipped banner and prints what it built. The stylesheet import loads as an
# empty module, and the document makes plain elements that keep their class, text and children.
RUNNER = """
import { readFileSync } from 'node:fs'
import { registerHooks } from 'node:module'
registerHooks({
  load: (url, context, nextLoad) =>
    url.endsWith('.css') ? { format: 'module', source: '', shortCircuit: true } : nextLoad(url, context),
})
class Element {
  constructor(tag) { Object.assign(this, { tagName: tag, className: '', textContent: '', children: [] }) }
  append(...nodes) { this.children.push(...nodes) }
}
globalThis.document = { createElement: (tag) => new Element(tag) }
const { disclosureBanner } = await import(process.argv[1])
const built = JSON.parse(readFileSync(0, 'utf8')).map((lines) => disclosureBanner(lines))
process.stdout.write(JSON.stringify(built))
"""
needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="Node 24 runs the banner component as it ships")


def _render(*lists: list[str]) -> list[Any]:
    result = subprocess.run(
        ["node", "--input-type=module", "-e", RUNNER, (COMPONENTS / "disclosure-banner.ts").as_uri()],
        input=json.dumps(lists), cwd=REPO, capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def _code(text: str) -> str:
    """TypeScript with its comments removed, so a doc comment may name what the code never reads."""
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.DOTALL)


def _client_code() -> dict[str, str]:
    """Every client module's code, the generated types and their type-level checks left out."""
    return {path: _code(text) for path, text in source_ts().items() if not path.endswith("types.check.ts")}


def _served_lines() -> list[str]:
    """The Disclosure copy table of EXPERIENCE.md, each line's fixed text split at its placeholder."""
    table = EXPERIENCE.read_text().split("**Disclosure copy", 1)[1].split("\n\n", 3)[2]
    lines = [re.search(r'\| "([^"]+)"', row).group(1) for row in table.splitlines()[2:]]
    return [part for line in lines for part in re.split(r"\{\w+\}|n×", line) if len(part) > 12]


@needs_node
def test_a_served_list_renders_verbatim_one_line_each_in_order_and_an_unknown_line_is_kept():
    served = [
        "A line this client has never seen <b>with markup</b> & a 6× sign.",
        "Hint and Trickster timings run at 6× speed; the build timer is real time.",
        "This room was built earlier, on Mon Oct 26.",
    ]
    banner, two = _render(served, served[1:])
    assert banner["className"] == "disclosure-banner"
    assert [row["textContent"] for row in banner["children"]] == served
    assert {(row["tagName"], row["className"]) for row in banner["children"]} == {("p", "body-sm")}
    assert [row["textContent"] for row in two["children"]] == served[1:]


@needs_node
def test_an_empty_served_list_renders_no_banner():
    assert _render([]) == [None]


def test_each_surface_renders_its_lists_as_served_and_the_client_composes_none():
    shell = _code((WEB_SRC / "shell.ts").read_text())
    # Capture and Hosted landing: GET /meta; Play, Completion, the second window: the session state; Build view: BuildView.
    assert set(re.findall(r"\bdisclosure = ([\w.]+)", shell)) == {"meta.disclosure", "state.disclosure",
                                                                  "state.view.disclosure"}
    assert "const banner = disclosureBanner(disclosure)" in shell
    callers = {path for path, code in _client_code().items() if "disclosureBanner(" in code}
    assert callers == {"web/src/shell.ts", "web/src/components/disclosure-banner.ts"}
    for path, code in _client_code().items():
        assert not re.search(r"disclosure\??\.(map|filter|sort|toSorted|concat|slice|splice|push|unshift|reverse|join|"
                             r"with)\b|disclosure\[", code), path
        for line in _served_lines():
            assert line not in code, f"{path} holds Disclosure copy the server composes: {line!r}"


def test_the_banner_is_the_footer_under_the_body_and_every_scrim_is_inside_the_body_above_it():
    shell = _code((WEB_SRC / "shell.ts").read_text())
    # The top bar, then the body, then the banner: the last band of the frame, a footer strip under the body.
    assert "show(bar.element, body.element, ...(banner === null ? [] : [banner]))" in shell
    assert "element.className = 'shell-body'" in shell
    rules = {**css_rules((WEB_SRC / "completion.css").read_text()), **css_rules((WEB_SRC / "shell.css").read_text()),
             **css_rules((WEB_SRC / "style.css").read_text()), **css_rules((COMPONENTS / "disclosure-banner.css").read_text())}
    banner = rules[".disclosure-banner"]
    assert banner["border-top"] == "1px solid var(--disclosure-edge)" and "border-bottom" not in banner
    assert banner["flex"] == "none" and rules[".disclosure-banner p"]["min-height"] == "var(--spacing-disclosure-min)"
    # The frame fills the viewport and the body takes every pixel between the top bar and the footer, so the footer is in
    # view without scrolling and no surface reserves a strip of its own: the Play screen's Hint area and the Capture
    # dropzone keep their full height.
    assert rules["html,\nbody,\n#app"]["height"] == "100%"
    assert rules["#app"]["flex-direction"] == "column"  # the frame's flex column; media queries only hide it
    assert rules[".shell-body"]["flex"] == "1 1 0" and rules[".shell-body"]["min-height"] == "0"
    # Each body that scrolls is positioned, so a visually hidden speaker prefix (absolute) scrolls inside it instead of
    # lengthening the page: the footer stays in view without scrolling, the Hosted landing at 1024 x 768 included.
    rules.update(css_rules((WEB_SRC / "landing.css").read_text()))
    for layout in (".landing-layout", ".capture-layout", ".build-view-layout"):
        assert rules[layout]["overflow-y"] == "auto" and rules[layout]["position"] == "relative", layout
    placement = EXPERIENCE.read_text().split("- **Placement.**", 1)[1].split("\n", 1)[0]
    assert "footer strip" in placement and "sits at the top edge" not in placement
    # Each overlay is appended to the body (the `main.shell-body` the route owns), never to the page or the footer.
    mounts = {"completion.ts": "body.append(scrim)", "welcome.ts": "body.append(overlay.element)",
              "leave-room.ts": "frame.body.append(confirmation.element)"}
    for name, mount in mounts.items():
        assert mount in _code((WEB_SRC / name).read_text()), name
    for name in ("greeting-overlay.css", "leave-room-confirmation.css"):
        rules.update(css_rules((COMPONENTS / name).read_text()))
    for scrim in (".completion-scrim", ".greeting-scrim", ".leave-room-scrim"):
        assert rules[scrim]["position"] == "absolute" and rules[scrim]["inset"] == "0", scrim
    for layout in (".play-layout", ".completion-layout"):
        assert rules[layout]["position"] == "relative", f"{layout} must hold its scrim inside the body"
    # Neither the banner nor the top bar is ever made inert or dimmed by an overlay's held elements.
    for name in ("leave-room.ts", "welcome.ts", "play.ts"):
        assert "banner" not in _code((WEB_SRC / name).read_text()).lower(), name


def test_the_banner_never_glows_animates_takes_focus_or_hides_from_a_screen_reader():
    ts = _code((COMPONENTS / "disclosure-banner.ts").read_text())
    assert not re.search(r"aria-hidden|role|tabIndex|hidden|inert|animate|focus", ts)
    for path, css in source_css().items():
        for selector, rule in css_rules(css).items():
            if "disclosure-banner" not in selector:
                continue
            assert path == "web/src/components/disclosure-banner.css", f"{path} restyles the banner"
            banned = {"animation", "transition", "box-shadow", "filter", "opacity", "position", "z-index", "outline"}
            assert not banned & set(rule), (selector, rule)


def test_demo_settings_are_read_only_by_the_mode_indicator_the_triggers_header_and_the_in_play_block():
    readers = {path for path, code in _client_code().items()
               if re.search(r"\bdemo_timescale\b|(?<!strings)\.trickster\b|\[['\"]trickster['\"]\]", code)}
    allowed = {"web/src/components/top-bar.ts", "web/src/components/triggers-panel.ts",
               "web/src/components/in-play-block.ts"}
    assert readers and readers <= allowed, readers - allowed
    # No demo-only path: no client route, flag or branch names the scripted or cut-1 source or a timescale. The In play
    # block names its source, and strings.ts holds that row's text.
    for path, code in _client_code().items():
        if path in {"web/src/components/in-play-block.ts", "web/src/strings.ts"}:
            continue
        assert not re.search(r"\bscripted\b|\bcut1\b|timescale|DEMO_", code, flags=re.IGNORECASE), path
    router = _code((WEB_SRC / "router.ts").read_text())
    assert set(re.findall(r"name: '(\w+)'", router)) <= {"home", "build", "view", "play", "done", "triggers"}


def test_how_hints_work_never_opens_by_itself_under_a_disclosure():
    # Owner decision Oct 29: the coupled rule is retired; the panel opens only when the player asks.
    panel = _code((COMPONENTS / "triggers-panel.ts").read_text())
    assert "disclosure" not in panel and "auto" not in panel
    assert "list.element.hidden = true" in panel and "list.element.hidden = !on" in panel
    assert "onOpen(false)" in panel