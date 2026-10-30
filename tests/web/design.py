"""Readers for the DESIGN.md frontmatter and the client stylesheets, shared by the token, contrast and ban tests."""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WEB_SRC = REPO / "web/src"
DESIGN = REPO / "docs/planning-artifacts/ux-designs/ux-Keyframe-2026-10-21/DESIGN.md"
GROUPS = ("colors", "typography", "rounded", "spacing", "elevation")
WALK_CSS = ("web/src/scene/walk.css", "web/src/components/walk-map.css", "web/src/components/riddle-note.css",
            "web/src/components/treasure-chest.css", "web/src/components/story-stage.css")
"""The walk and story stylesheets: DESIGN.md Motion's walk and story exception (owner decision Oct 29),
tests/web/test_walk.py and tests/web/test_story_play.py."""
RINGLESS = {"web/src/components/riddle-note.css": ".riddle-note-heading:focus-visible",
            "web/src/completion.css": ".completion-heading:focus-visible"}
"""The two headings that take focus but are no control, so no ring shows (EXPERIENCE.md Riddle note, DESIGN.md
Completion screen): the one place a stylesheet drops the focus ring."""


def design_text() -> str:
    return DESIGN.read_text()


def frontmatter() -> dict[str, dict]:
    """The token groups of the DESIGN.md frontmatter: flat `name: 'value'` lines, nested one level for typography.

    A color line's `# = base` comment is kept as `bases[name] = base`.
    """
    text = design_text().split("\n---\n", 1)[0]
    groups: dict[str, dict] = {"bases": {}}
    group = key = None
    for raw in text.splitlines():
        line = raw.split(" # ", 1)[0].rstrip() if not raw.lstrip().startswith("#") else ""
        if not line:
            continue
        indent = len(raw) - len(raw.lstrip())
        name, _, value = line.strip().partition(":")
        name, value = name.strip("'\""), value.strip().strip("'\"")
        if indent == 0:
            group, key = (name if name in GROUPS else None), None
            if group:
                groups[group] = {}
            continue
        if group is None:
            continue
        if indent == 2 and value:
            groups[group][name] = value
            base = re.search(r"# = ([\w-]+)", raw)
            if base:
                groups["bases"][name] = base.group(1)
        elif indent == 2:
            key = name
            groups[group][key] = {}
        elif indent == 4 and key:
            groups[group][key][name] = value
    return groups


def source_css() -> dict[str, str]:
    return {str(p.relative_to(REPO)): p.read_text() for p in sorted(WEB_SRC.rglob("*.css"))}


def source_ts() -> dict[str, str]:
    return {str(p.relative_to(REPO)): p.read_text() for p in sorted(WEB_SRC.rglob("*.ts"))}


def css_custom_properties() -> dict[str, str]:
    """Every `--name: value;` declared under `:root` in web/src/tokens.css, outside media queries."""
    text = (WEB_SRC / "tokens.css").read_text()
    root = re.search(r"^:root \{\n(.*?)^\}", text, flags=re.S | re.M).group(1)
    return dict(re.findall(r"--([\w-]+):\s*([^;]+);", re.sub(r"/\*.*?\*/", "", root)))


def css_rules(text: str) -> dict[str, dict[str, str]]:
    """`selector -> {property: value}` for every rule in a stylesheet, media blocks flattened."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"@media[^{]*\{", "", text)
    rules: dict[str, dict[str, str]] = {}
    for selector, body in re.findall(r"([^{}]+)\{([^{}]*)\}", text):
        declarations = dict(d.split(":", 1) for d in body.split(";") if ":" in d)
        rules.setdefault(selector.strip(), {}).update({k.strip(): " ".join(v.split()) for k, v in declarations.items()})
    return rules
