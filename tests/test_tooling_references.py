"""Repo hygiene (delivery plan, Wed Nov 4): code names no hackathon tooling path or dev skill.

tests/ joins the scan once story 6.8 removes the session-start hook and its test.
The patterns are written so that this file does not match itself.
"""

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCANNED = ("src", "scripts", "web/src")
TOOLING = re.compile(r"[.]claude/|keyframe-(sam31|muse|sam3d-fal|modal|devops)\b")


def test_code_carries_no_tooling_references():
    hits = [
        f"{path.relative_to(REPO)}:{number}: {line.strip()}"
        for root in SCANNED
        for path in sorted((REPO / root).rglob("*"))
        if path.is_file() and "__pycache__" not in path.parts
        for number, line in enumerate(path.read_text(errors="ignore").splitlines(), 1)
        if TOOLING.search(line)
    ]
    assert not hits, "\n".join(hits)
