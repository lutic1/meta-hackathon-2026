"""UX-DR60, NFR-10, AR-32: below 1024 px the Narrow-screen message replaces the whole app, with no mobile layout and no
horizontal scroll; widening past 1024 px returns the app with its state intact.

The client has no test runner (a runner is added only through bmad-correct-course), so these checks read the
TypeScript and the stylesheets; `npm run build` and `tsc --noEmit` prove they compile, and the criteria are checked in
Chrome at 1440, 1280, 1024 and below.
"""

import re

from tests.web.design import WEB_SRC, css_rules, design_text, frontmatter
from tests.web.test_contrast import PROPS, _hex, contrast

NARROW = "@media (max-width: 1023px)"


def _ts(name: str) -> str:
    return (WEB_SRC / name).read_text()


def _media(css: str) -> str:
    """The body of the stylesheet's one narrow-screen media query."""
    return css.split(NARROW + " {", 1)[1].split("\n}\n", 1)[0]


def test_the_shell_hides_the_app_below_1024px_and_never_tears_it_down():
    shell_css = (WEB_SRC / "shell.css").read_text()
    assert css_rules(_media(shell_css))["#app"] == {"display": "none"}
    shell = _ts("shell.ts")
    assert "import { narrowScreenMessage } from './components/narrow-screen-message.ts'" in shell
    assert "root.after(narrowScreenMessage())" in shell  # outside #app, so no route change replaces it
    # Nothing listens for the width: the app is only hidden, so its state survives a resize.
    for path in ("shell.ts", "components/narrow-screen-message.ts", "play.ts"):
        code = _ts(path)
        assert "matchMedia" not in code and "'resize'" not in code and "innerWidth" not in code, path


def test_the_message_shows_only_below_1024px_on_the_canvas_inside_16px_gutters():
    css = (WEB_SRC / "components/narrow-screen-message.css").read_text()
    rules = css_rules(css.split(NARROW, 1)[0])
    assert rules[".narrow-screen"] == {"display": "none"}
    shown = css_rules(_media(css))[".narrow-screen"]
    assert shown["display"] == "grid" and shown["place-items"] == "center"
    assert shown["padding"] == "var(--spacing-narrow-gutter)" and shown["background"] == "var(--canvas)"
    assert shown["box-sizing"] == "border-box"
    assert frontmatter()["spacing"]["narrow-gutter"] == "16px" and PROPS["spacing-narrow-gutter"] == "16px"


def test_the_card_is_plain_chrome_raised_at_most_480px_and_never_scrolls_sideways():
    token = design_text().split("  narrow-screen-message:\n", 1)[1].split("\n---\n", 1)[0]
    rules = css_rules((WEB_SRC / "components/narrow-screen-message.css").read_text())
    card = rules[".narrow-screen-message"]
    assert "maxWidth: 480px" in token and card["max-width"] == "480px" and card["width"] == "100%"
    assert card["box-sizing"] == "border-box" and card["overflow-wrap"] == "break-word"
    assert "background: '{colors.chrome-raised}'" in token and card["background"] == "var(--chrome-raised)"
    assert "foreground: '{colors.text}'" in token and card["color"] == "var(--text)"
    assert "radius: '{rounded.lg}'" in token and card["border-radius"] == "var(--rounded-lg)"
    assert "gutter: '{spacing.narrow-gutter}'" in token
    assert "parchment" not in str(rules)
    assert contrast(_hex(PROPS["text"])[0], _hex(PROPS["chrome-raised"])[0]) >= 4.5


def test_the_card_holds_the_wordmark_the_guide_s_portrait_the_heading_the_sentence_and_the_copy_button():
    ts = _ts("components/narrow-screen-message.ts")
    assert "wordmark.textContent = strings.wordmark" in ts
    assert "const portrait = wizardPortrait('guide', 96)" in ts  # the existing component, so its placeholder stands in
    assert "heading.className = 'narrow-screen-heading display-sm'" in ts and "heading.textContent = strings.narrowHeading" in ts
    assert "body.className = 'narrow-screen-sentence body-md'" in ts and "body.textContent = strings.narrowBody" in ts
    assert "secondaryButton({ label: strings.copyLinkForLaptop, onActivate: () => void copyLink() })" in ts
    assert "status.className = 'narrow-screen-status body-sm'" in ts
    assert "card.append(wordmark, portrait, heading, body, copy, status)" in ts


def test_copy_link_copies_this_page_s_address_and_confirms_in_the_live_region_and_under_the_button():
    ts = _ts("components/narrow-screen-message.ts")
    copy = ts.split("async function copyLink(", 1)[1].split("\n  }\n", 1)[0]
    assert "let line: string = strings.linkCopied" in copy and "await navigator.clipboard.writeText(location.href)" in copy
    assert "line = strings.linkNotCopied" in copy  # no clipboard, or a refused write: the address bar still has it
    assert copy.index("status.textContent = line") < copy.index("announce(line)")
    assert "import { announce } from '../live-region.ts'" in ts


def test_no_control_on_the_card_leaves_the_page():
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", _ts("components/narrow-screen-message.ts"), flags=re.DOTALL)
    assert code.count("secondaryButton(") == 1 and "primaryButton" not in code
    assert not re.search(r"href\s*=|location\.(hash|assign|replace)|window\.open|createElement\('a'\)|tabIndex", code)
