"""UX-DR1 to UX-DR6, UX-DR9 to UX-DR11: every DESIGN.md token in web/src/tokens.css, the fonts self-hosted,
the type styles, the motion rule and the base buttons and focus ring."""

import re

import pytest

from tests.web.design import GROUPS, REPO, WEB_SRC, css_custom_properties, css_rules, frontmatter, source_css

FONTS = REPO / "web/public/fonts"
FAMILIES = {"EB Garamond": "eb-garamond", "Source Sans 3": "source-sans-3", "IBM Plex Mono": "ibm-plex-mono"}
TYPE_STYLES = ("display-lg", "display-md", "display-sm", "wizard-line-lg", "wizard-line", "lore", "body-md", "body-sm",
               "label", "caption", "mono-timer", "mono-code", "mono-sm")
FAMILY_VAR = {"EB Garamond": "var(--font-serif)", "Source Sans 3": "var(--font-sans)", "IBM Plex Mono": "var(--font-mono)"}
ROLE_PREFIXES = ("card-", "clue-card-", "graph-", "mask-overlay-")
FADE_OR_GLOW = {"opacity", "box-shadow", "background-color", "border-color", "color", "outline-color"}
MOTION = {"motion-hover": "150ms", "motion-state": "200ms", "motion-overlay": "300ms", "motion-count": "800ms"}
CHOOSER = "web/src/chooser.css"
"""The Hosted landing chooser, the owner's one exception to the motion rule (DESIGN.md Motion, test_chooser.py)."""


@pytest.fixture(scope="module")
def design():
    return frontmatter()


@pytest.fixture(scope="module")
def props():
    return css_custom_properties()


@pytest.fixture(scope="module")
def tokens_rules():
    return css_rules((WEB_SRC / "tokens.css").read_text())


def test_design_frontmatter_has_every_group(design):
    assert all(design[g] for g in GROUPS)
    assert len(design["colors"]) == 60 and len(design["typography"]) == 13


def test_every_color_token_is_a_custom_property_with_its_exact_hex(design, props):
    for name, hex_value in design["colors"].items():
        assert props.get(name) == hex_value, f"--{name} should be {hex_value}, is {props.get(name)}"
        assert re.fullmatch(r"#[0-9A-F]{6}([0-9A-F]{2})?", hex_value), name


def test_role_tokens_repeat_their_base_hex(design, props):
    roles = [n for n in design["colors"] if n.startswith(ROLE_PREFIXES)]
    assert len(roles) == 19
    for name in roles:
        base = design["bases"].get(name)
        if base is None:
            assert name in ("graph-edge", "mask-overlay-fill", "mask-overlay-stroke"), f"{name} names no base"
            continue
        assert props[name] == props[base] == design["colors"][base], f"--{name} must repeat --{base}"
    assert props["pending"] == props["text-muted"] and props["pending-ink"] == props["ink-muted"]


def test_dark_theme_only():
    for path, text in source_css().items():
        assert "prefers-color-scheme" not in text and "light" not in re.findall(r"color-scheme:\s*(\w+)", text), path


def test_spacing_rounded_and_elevation_tokens_match_design(design, props):
    for group in ("spacing", "rounded", "elevation"):
        for name, value in design[group].items():
            assert props.get(f"{group}-{name}") == value, f"--{group}-{name} should be {value}"
    assert [props[f"spacing-{n}"] for n in "12345678"] == ["4px", "8px", "12px", "16px", "24px", "32px", "48px", "64px"]
    assert props["spacing-frame-margin"] == "24px" and props["spacing-side-column"] == "400px"
    assert props["spacing-top-bar"] == "48px" and props["spacing-disclosure-min"] == "32px"
    assert props["spacing-thumbnail-strip"] == "88px" and props["spacing-narrow-gutter"] == "16px"
    assert props["rounded-none"] == "0px" and props["rounded-sm"] == "4px" and props["rounded-md"] == "8px"
    assert props["rounded-lg"] == "12px" and props["rounded-full"] == "9999px"
    assert set(design["elevation"]) == {"paper", "overlay", "lamp-glow", "vignette"}


def test_fonts_are_self_hosted_woff2_with_their_license():
    expected = {
        "eb-garamond": {"400-normal", "500-normal", "400-italic"},
        "source-sans-3": {"400-normal", "600-normal"},
        "ibm-plex-mono": {"400-normal", "500-normal"},
    }
    for folder, faces in expected.items():
        files = {p.name for p in (FONTS / folder).iterdir()}
        assert files == {f"{folder}-latin-{face}.woff2" for face in faces} | {"LICENSE"}, folder
        assert "SIL Open Font License" in (FONTS / folder / "LICENSE").read_text()
        for face in faces:
            assert (FONTS / folder / f"{folder}-latin-{face}.woff2").read_bytes()[:4] == b"wOF2"


def test_font_faces_point_at_the_self_hosted_files_and_no_third_party_host(tokens_rules):
    text = (WEB_SRC / "tokens.css").read_text()
    faces = re.findall(r"@font-face \{([^}]*)\}", text)
    assert len(faces) == 7
    for face in faces:
        family = re.search(r"font-family: '([^']+)'", face).group(1)
        weight = re.search(r"font-weight: (\d+)", face).group(1)
        style = re.search(r"font-style: (\w+)", face).group(1)
        folder = FAMILIES[family]
        assert f"url('/fonts/{folder}/{folder}-latin-{weight}-{style}.woff2') format('woff2')" in face
    for path, text in source_css().items() | {"web/index.html": (REPO / "web/index.html").read_text()}.items():
        assert not re.search(r"https?://|fonts\.googleapis|fonts\.gstatic|@import url", text), path


def test_the_13_type_styles_match_design(design, tokens_rules):
    assert tuple(design["typography"]) == TYPE_STYLES
    for name, spec in design["typography"].items():
        rule = tokens_rules[f".{name}"]
        assert rule["font-family"] == FAMILY_VAR[spec["fontFamily"]], name
        assert rule["font-size"] == spec["fontSize"] and rule["font-weight"] == spec["fontWeight"], name
        assert rule["line-height"] == spec["lineHeight"], name
        assert rule.get("letter-spacing") == spec.get("letterSpacing"), name
        assert rule.get("font-style") == spec.get("fontStyle"), name
        if spec["fontFamily"] == "EB Garamond":
            assert int(spec["fontSize"].removesuffix("px")) >= 17, f"Garamond never below 17 px: {name}"
        if spec["fontFamily"] == "IBM Plex Mono":
            assert rule["font-variant-numeric"] == "tabular-nums", name
    assert tokens_rules[".display-lg"]["font-size"] == "40px" and tokens_rules[".mono-sm"]["font-size"] == "13px"
    assert tokens_rules[".lore"]["font-size"] == "17px" and tokens_rules[".lore"]["font-style"] == "italic"
    assert tokens_rules[".mono-code"]["font-size"] == "20px" and tokens_rules[".mono-code"]["letter-spacing"] == "0.2em"


def test_italic_only_on_lore_and_sentence_case_everywhere():
    for path, text in source_css().items():
        rules = css_rules(text)
        italic = [s for s, r in rules.items() if r.get("font-style") == "italic"]
        assert italic == ([".lore"] if path.endswith("tokens.css") else []), path
        assert not re.search(r"text-transform:\s*(uppercase|capitalize)", text), path
        assert "font-variant-caps" not in text and "small-caps" not in text, path


def test_motion_tokens_and_every_transition_is_a_fade_or_glow_with_ease_out(props):
    assert props["motion-ease"] == "ease-out"
    assert {name: props[name] for name in MOTION} == MOTION
    assert "motion-attract" not in props  # the attract frame is gone with its cycle (owner decision Oct 29)
    for path, text in source_css().items():
        if path.endswith(CHOOSER):
            continue
        assert not re.search(r"@keyframes|animation|transform|translate|scale\(", text), f"{path}: nothing slides, bounces, shakes or loops"
        for value in re.findall(r"transition:\s*([^;]+);", text):
            for part in value.split(","):
                prop, duration, easing = part.split()
                assert prop in FADE_OR_GLOW, f"{path}: {prop} is not a fade or a glow"
                assert duration.startswith("var(--motion-") and easing == "var(--motion-ease)", f"{path}: {part}"
        assert "transition-duration" not in text or path.endswith("tokens.css")


def test_reduced_motion_makes_every_transition_instant():
    text = (WEB_SRC / "tokens.css").read_text()
    block = re.search(r"@media \(prefers-reduced-motion: reduce\) \{(.*?)\n\}", text, flags=re.S).group(1)
    for name in MOTION:
        assert f"--{name}: 0ms;" in block
    assert re.search(r"\*,\s*::before,\s*::after \{\s*transition-duration: 0ms !important;", block)


def test_focus_ring_is_two_tone_at_2px_offset_on_focus_visible_and_never_removed(tokens_rules):
    ring = tokens_rules[":focus-visible"]
    assert ring == {"outline": "2px solid var(--focus-ring)", "outline-offset": "2px",
                    "box-shadow": "0 0 0 2px var(--focus-ring-inner)"}
    for path, text in source_css().items():
        assert not re.search(r"outline:\s*(none|0)", text), f"{path} removes a focus outline"
        for selector, rule in css_rules(text).items():
            if ":focus-visible" in selector and "box-shadow" in rule:
                # The chooser's card ring stands 4 px out at 3 px, so its inner ring fills that gap (DESIGN.md Chooser).
                inner = "0 0 0 4px" if selector == ".chooser-choose:focus-visible" else "0 0 0 2px"
                assert rule["box-shadow"].startswith(f"{inner} var(--focus-ring-inner)"), f"{path}: {selector} loses the inner ring"
            if ":hover" in selector and ":focus-visible" not in selector and "box-shadow" in rule:
                assert f"{selector}:focus-visible" in css_rules(text), f"{path}: the hover glow on {selector} replaces the focus ring"


def test_primary_button_is_44px_lamp_with_on_lamp_label_and_pending_state():
    rules = css_rules((WEB_SRC / "components/button.css").read_text())
    primary = rules[".button-primary"]
    assert primary["height"] == "44px" and primary["padding"] == "0 var(--spacing-5)"
    assert primary["background"] == "var(--lamp)" and primary["color"] == "var(--on-lamp)"
    assert rules[".button-primary:hover"] == {"background": "var(--lamp-strong)", "box-shadow": "var(--elevation-lamp-glow)"}
    assert rules[".button-primary:disabled"]["opacity"] == "0.4" and rules[".button-primary:disabled"]["box-shadow"] == "none"
    shared = rules[".button-primary,\n.button-secondary"]
    assert shared["border-radius"] == "var(--rounded-md)" and shared["font-size"] == "13px" and shared["font-weight"] == "600"
    ts = (WEB_SRC / "components/button.ts").read_text()
    assert "export function primaryButton(" in ts and "pendingLabel" in ts
    assert "if (pending) return" in ts and "element.textContent = pendingLabel" in ts
    assert "element.setAttribute('aria-busy', 'true')" in ts and ".finally(" in ts
    assert "element.type = 'button'" in ts and "disabled" not in ts  # pending keeps focus; Enter and Space stay native


def test_secondary_button_is_40px_lamp_border_with_toggle_and_parchment_variants():
    rules = css_rules((WEB_SRC / "components/button.css").read_text())
    secondary = rules[".button-secondary"]
    assert secondary["height"] == "40px" and secondary["border"] == "1px solid var(--lamp)"
    assert secondary["color"] == "var(--lamp)" and secondary["background"] == "transparent"
    assert rules[".button-secondary:hover"] == {"background": "var(--lamp-hover-fill)"}
    toggle = rules[".button-secondary[aria-pressed='true'],\n.button-secondary[aria-expanded='true']"]
    assert toggle["background"] == "var(--lamp-hover-fill)" and toggle["border"] == "2px solid var(--lamp)"
    paper = rules[".button-secondary.on-parchment"]
    assert paper == {"color": "var(--lamp-ink)", "border-color": "var(--lamp-ink)"}
    assert rules[".button-secondary.on-parchment:hover"] == {"background": "var(--lamp-ink-hover-fill)"}
    ts = (WEB_SRC / "components/button.ts").read_text()
    assert "export function secondaryButton(" in ts and "classList.toggle('on-parchment', onParchment)" in ts
    assert "export function toggleButton(" in ts and "state === 'pressed' ? 'aria-pressed' : 'aria-expanded'" in ts
    assert "element.setAttribute(attribute, String(next))" in ts


def test_components_import_their_stylesheets_and_the_page_imports_the_tokens():
    assert "@import './tokens.css';" in (WEB_SRC / "style.css").read_text()
    assert "import './button.css'" in (WEB_SRC / "components/button.ts").read_text()
