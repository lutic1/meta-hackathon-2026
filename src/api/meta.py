"""The status model: `Meta`, the Disclosure lines and the Retention summary (AD-15, UX-DR79).

`meta(settings, profile)` is what `GET /meta` returns. `mode` is the
constant wiring sets (`local` until `Settings.mode` lands in 7.2); `trickster` reads
`DEMO_TRICKSTER` as AD-15 states (`live` and `record` are `live`,
`authored` is `cut1`); `guide_model` names `llama3.2:3b` at `OLLAMA_HOST`
under `GUIDE=ollama` and is null under `GUIDE=verbatim`.

`disclosure_lines(settings, room, ...)` is the one function that composes a
Disclosure list: without a Room, the global lines `GET /meta` serves; with
one, that Room's list, the global lines plus the earlier-builds line for a
Demo room (one with a `name`), a Room with an earlier session, or a Build
whose job call rows hold any call served from the Cache. The session state
carries the Room's list, and `BuildView` reads the same function when its
projection lands (2.27). No other module writes a Disclosure line; the
hosted line joins here in 7.2. `RETENTION_LOCAL` is
the one Local Retention summary, served as `retention`; the hosted text
replaces its last sentence, never appends to it (PRD §13 Q3 owns the
final wording).
"""

from __future__ import annotations

from typing import Literal

from src.api.wiring import MODE
from src.config import Settings
from src.domain.schema import GuideModel, JobState, Meta, Room
from src.providers.ollama import DEFAULT_HOST, GUIDE_MODEL

Trickster = Literal["live", "scripted", "cut1"]

TIMESCALE_LINE = "Hint and Trickster timings run at {n}× speed; the build timer is real time."
SCRIPTED_LINE = "Trickster proposals replayed from a recording; the Validator ran live."
CUT1_LINE = "Trickster proposals were written in advance; the Validator ran live on each."
EARLIER_BUILD_LINE = "This room was built earlier, on {date}."

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
    return GuideModel(id=GUIDE_MODEL, host=settings.ollama_host or DEFAULT_HOST)


def built_earlier(room: Room, job: JobState | None, *, earlier_session: bool) -> bool:
    """A Demo room, a Room with an earlier session, or a Build with any call served from the Cache (AD-15)."""
    return room.name is not None or earlier_session or (job is not None and any(call.cached for call in job.calls))


def disclosure_lines(
    settings: Settings, room: Room | None = None, job: JobState | None = None, *, earlier_session: bool = False
) -> list[str]:
    """The Disclosure lines in display order: the global ones, then the Room's earlier-builds line; empty at the defaults."""
    lines: list[str] = []
    if settings.demo_timescale > 1:
        lines.append(TIMESCALE_LINE.format(n=settings.demo_timescale))
    source = trickster(settings)
    if source == "scripted":
        lines.append(SCRIPTED_LINE)
    elif source == "cut1":
        lines.append(CUT1_LINE)
    if room is not None and built_earlier(room, job, earlier_session=earlier_session):
        lines.append(EARLIER_BUILD_LINE.format(date=f"{room.created:%a %b} {room.created.day}"))
    return lines


def meta(settings: Settings, profile: str = "dev") -> Meta:
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
