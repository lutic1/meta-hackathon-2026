"""The status model: `Meta`, the Disclosure lines and the Retention summary (AD-15, UX-DR79).

`meta(settings, profile)` is what `GET /meta` returns. `mode` is the
constant wiring sets (`local` until `Settings.mode` lands in 7.2); `trickster` reads
`DEMO_TRICKSTER` as AD-15 states (`live` and `record` are `live`,
`authored` is `cut1`); `guide_model` names `llama3.2:3b` at `OLLAMA_HOST`
under `GUIDE=ollama` and is null under `GUIDE=verbatim`.

`disclosure_lines(settings)` is the one function that composes a
Disclosure list: the global lines `GET /meta` serves and the session
state carries. No other module writes a Disclosure line; the per-Room
line joins here in 6.2 and the hosted line in 7.x. `RETENTION_LOCAL` is
the one Local Retention summary, served as `retention`; the hosted text
replaces its last sentence, never appends to it (PRD §13 Q3 owns the
final wording).
"""

from __future__ import annotations

from typing import Literal

from src.api.wiring import MODE
from src.config import Settings
from src.domain.schema import GuideModel, Meta

GUIDE_MODEL_ID = "llama3.2:3b"
DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
"""Where the Ollama server listens when `OLLAMA_HOST` is unset."""

MetaProfile = Literal["dev", "demo"]
"""The `profile` query of `GET /meta`: `dev` unless the client asks for `demo`."""
Trickster = Literal["live", "scripted", "cut1"]

TIMESCALE_LINE = "Hint and Trickster timings run at {n}× speed; the build timer is real time."
SCRIPTED_LINE = "Trickster proposals replayed from a recording; the Validator ran live."
CUT1_LINE = "Trickster proposals were written in advance; the Validator ran live on each."

RETENTION_LOCAL = (
    "Your photos and the puzzle text go to the Meta Model API (standard tier) to find objects, "
    "write puzzles and test them. If a backup model is switched on for the Riddler or the Trickster, "
    "that role's prompt goes to Baseten or Fireworks, never with an answer or anything from your "
    "player profile. Leave out faces, documents and other people's belongings. "
    "A copy of your photos is also kept on this computer."
)
"""The Local Retention summary: the shared opening, the faces and documents request, the local storage sentence."""


def trickster(settings: Settings) -> Trickster:
    """The proposal source as `GET /meta` reports it (AD-15)."""
    if settings.demo_trickster == "authored":
        return "cut1"
    if settings.demo_trickster == "scripted":
        return "scripted"
    return "live"


def guide_model(settings: Settings) -> GuideModel | None:
    """The Guide model `GUIDE=ollama` runs; null when Rungs are shown as written."""
    if settings.guide != "ollama":
        return None
    return GuideModel(id=GUIDE_MODEL_ID, host=settings.ollama_host or DEFAULT_OLLAMA_HOST)


def disclosure_lines(settings: Settings) -> list[str]:
    """The global Disclosure lines in display order; empty at the defaults."""
    lines: list[str] = []
    if settings.demo_timescale > 1:
        lines.append(TIMESCALE_LINE.format(n=settings.demo_timescale))
    source = trickster(settings)
    if source == "scripted":
        lines.append(SCRIPTED_LINE)
    elif source == "cut1":
        lines.append(CUT1_LINE)
    return lines


def meta(settings: Settings, profile: MetaProfile = "dev") -> Meta:
    return Meta(
        mode=MODE,
        guide=settings.guide,
        guide_model=guide_model(settings),
        trickster=trickster(settings),
        demo_timescale=settings.demo_timescale,
        cache=settings.cache,
        profile=profile,
        disclosure=disclosure_lines(settings),
        retention=RETENTION_LOCAL,
    )
