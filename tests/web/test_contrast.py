"""UX-DR72: the contrast audit over every pair in the DESIGN.md contrast table, against the tokens in web/src/tokens.css.

WCAG 2.x relative-luminance ratios: 4.5:1 for text, 3:1 for the rows the table marks non-text.
"""

import re

import pytest

from tests.web.design import css_custom_properties, design_text

PROPS = css_custom_properties()
Rgb = tuple[float, float, float]


def _rows() -> list[tuple[str, str, float, str]]:
    section = design_text().split("### Contrast (load-bearing pairs)", 1)[1].split("\n## ", 1)[0]
    rows = []
    for line in section.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 5 and cells[4] == "pass":
            rows.append((cells[0], cells[1], float(cells[2]), cells[3]))
    return rows


def _hex(value: str) -> tuple[Rgb, float]:
    """A `#RRGGBB` or `#RRGGBBAA` string as sRGB channels in 0..1 plus alpha."""
    digits = value.lstrip("#")
    r, g, b = (int(digits[i:i + 2], 16) / 255 for i in (0, 2, 4))
    alpha = int(digits[6:8], 16) / 255 if len(digits) == 8 else 1.0
    return (r, g, b), alpha


def _over(top: str, base: Rgb) -> Rgb:
    """`top` (a token, possibly translucent) composited over the opaque color `base`."""
    (r, g, b), alpha = _hex(PROPS[top])
    return tuple(alpha * c + (1 - alpha) * d for c, d in zip((r, g, b), base))


def _color(cell: str) -> Rgb:
    """The first token named in a table cell, with any `+ token` layered on top (approximations in the cell are ignored)."""
    tokens = re.findall(r"`([\w-]+)`", cell)
    color = _over(tokens[0], _hex(PROPS["canvas"])[0])
    if "over the Scene" in cell:
        return color
    for extra in tokens[1:]:
        if "+" in cell:
            color = _over(extra, color)
    return color


def _luminance(rgb: Rgb) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(foreground: Rgb, background: Rgb) -> float:
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


ROWS = _rows()


def test_the_table_has_every_load_bearing_pair():
    assert len(ROWS) == 43
    names = {t for fg, bg, _, _ in ROWS for t in re.findall(r"`([\w-]+)`", fg + bg)}
    assert names <= set(PROPS)


@pytest.mark.parametrize("foreground,background,listed,use", ROWS, ids=[f"{r[0]} on {r[1]}" for r in ROWS])
def test_every_pair_meets_aa_on_the_dark_theme(foreground, background, listed, use):
    ratio = contrast(_color(foreground), _color(background))
    floor = 3.0 if "non-text" in use else 4.5
    assert ratio >= floor, f"{foreground} on {background}: {ratio:.2f} < {floor}"
    assert abs(ratio - listed) < 0.1, f"{foreground} on {background}: computed {ratio:.2f}, DESIGN.md lists {listed}"


def test_lamp_on_parchment_fails_and_is_not_listed():
    assert contrast(_hex(PROPS["lamp"])[0], _hex(PROPS["parchment"])[0]) < 3
    assert not any("`lamp`" in fg and "`parchment`" in bg for fg, bg, _, _ in ROWS)


def test_hairline_is_decorative_only():
    assert contrast(_hex(PROPS["hairline"])[0], _hex(PROPS["chrome"])[0]) < 3
    assert not any("`hairline`" in fg for fg, _, _, _ in ROWS)
