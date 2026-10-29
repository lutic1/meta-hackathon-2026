"""The status model: `Meta`, the Disclosure lines and the Retention summary (AD-15, UX-DR79).

`meta(settings, profile)` is what `GET /meta` returns. `mode` reads `MODE`
from `Settings`; `trickster` reads `DEMO_TRICKSTER` as AD-15 states (`live`
and `record` are `live`, `authored` is `cut1`); `guide_model` names
`llama3.2:3b` at `OLLAMA_HOST` under `GUIDE=ollama` and is null under
`GUIDE=verbatim`, which `MODE=hosted` always runs.

`disclosure_lines(settings, room, ...)` is the one function that composes a
Disclosure list: without a Room, the global lines `GET /meta` serves (the
timescale line, the Trickster-source line and, in Hosted mode, the hosted
line); with one, that Room's list, the global lines plus the earlier-builds
line, dated by `Room.created` in ET, when the Room's durable provenance says
it was built earlier: a Demo room (`demo_room`: the caller asks
`ArtifactStore.is_demo_room`, the rule the welcome keys on; `Room.name` is
display data, never a room kind) or a Build whose job call rows hold any
call served from the Cache (decision record item 72). A session that found
an earlier session on the Room (`earlier_session`, fixed in its header)
adds the separately labelled replay line instead, when the build fact is
absent; it never changes that fact. The session state carries the Room's
list, and `GET /builds/<job_id>/view` fills `BuildView.disclosure` from the
same function over the Room and its job record alone, never its sessions.
No other module writes a Disclosure line.

`retention_summary(settings)` is the Retention summary `GET /meta` serves
(AD-15), stating only checked provider facts (decision record items 1 and
31): the Meta Model API Standard service and its terms; the Baseten or
Fireworks fallback only when `Settings` switches a role to
`openai_compatible`; then the running mode's ending, the Hosted ending
replacing the Local storage sentence, never appended to it; then the
provider-policy links, which the Retention panel renders as anchors. fal
never ships, so it is never named. The faces, documents and belongings
reminder is its own Capture line, not part of this text. The per-mode
texts and lines are tables keyed by `MODE`, so this module selects by mode
without branching on it (AD-9).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from src.config import ROLES, Mode, Settings
from src.domain.schema import GuideModel, JobState, Meta, Room
from src.providers.ollama import DEFAULT_HOST, GUIDE_MODEL

Trickster = Literal["live", "scripted", "cut1"]

TIMESCALE_LINE = "Hint and Trickster timings run at {n}× speed; the build timer is real time."
SCRIPTED_LINE = "Trickster proposals replayed from a recording; the Validator ran live."
CUT1_LINE = "Trickster proposals were written in advance; the Validator ran live on each."
EARLIER_BUILD_LINE = "This room was built earlier, on {date}."
REPLAY_LINE = "Replay: this room has been played before."
"""The session-specific line (decision record item 72): labelled apart from the build fact, which it never changes."""
DATES_TZ = ZoneInfo("America/New_York")
"""Every shown date is ET (decision record item 71), as the client's build times are."""
HOSTED_LINE = "Hosted mode: hints are shown as written; no hint model runs here."
MODE_LINES: dict[Mode, tuple[str, ...]] = {"local": (), "hosted": (HOSTED_LINE,)}
"""The global Disclosure lines the running mode adds (AD-15)."""

META_TERMS_URL = "https://dev.meta.ai/legal/terms-of-service"
META_ZDR_URL = "https://dev.meta.ai/help/policies-and-privacy/zero-data-retention"
BASETEN_SECURITY_URL = "https://www.baseten.co/security-practices/"
RETENTION_STANDARD = (
    "Building a room sends your photos and the puzzle text to the Meta Model API. Keyframe uses its Standard service, "
    "whose terms prohibit training on this content but permit retention for service operation, security, safety and "
    "policy review; it is not zero retention, which needs separate enablement."
)
"""Meta Model API Terms 4.4 and 5.1 and its zero-retention help page, both modes."""
RETENTION_FALLBACK = (
    "A backup model is switched on, so some prompts go to Baseten or Fireworks instead, never with an answer or "
    "anything from your player profile. If the Baseten fallback is used, its synchronous Model APIs publish zero "
    "retention for inference content, subject to the provider's exceptions."
)
"""Composed only when a role's provider is `openai_compatible` (Baseten's Security Practices)."""
RETENTION_ENDINGS: dict[Mode, str] = {
    "local": "Your player profile and room files stay on this computer until you delete them.",
    "hosted": (
        "Photos of a room you build on this site, and the room itself, are stored on its hosted volume and are "
        "scheduled for deletion after judging, on Tue Nov 10. Play sessions are deleted 24 hours after their last move."
    ),
}
"""The mode's storage sentences: the Hosted ending replaces the Local one (AD-15); the purge is scheduled, the 24 h sweep runs."""


def retention_summary(settings: Settings) -> str:
    """The Retention summary for the running mode and the configured providers, ending in the provider-policy links."""
    fallback = any(getattr(settings, f"provider_{role}") == "openai_compatible" for role in ROLES)
    links = [META_TERMS_URL, META_ZDR_URL, *([BASETEN_SECURITY_URL] if fallback else [])]
    sentences = [RETENTION_STANDARD, *([RETENTION_FALLBACK] if fallback else []), RETENTION_ENDINGS[settings.mode]]
    return " ".join([*sentences, "Provider policies:", *links])


RETENTION_LOCAL = retention_summary(Settings(mode="local"))
"""The Local Retention summary with every role on the Meta Model API."""
RETENTION_HOSTED = retention_summary(Settings(mode="hosted"))
"""The Hosted Retention summary with every role on the Meta Model API."""


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


def built_earlier(job: JobState | None, *, demo_room: bool) -> bool:
    """The Room's durable provenance: a Demo room (as `ArtifactStore.is_demo_room` names it) or a Build with any call served from the Cache (AD-15, item 72)."""
    return demo_room or (job is not None and any(call.cached for call in job.calls))


def build_date(created: datetime) -> str:
    """`created` as the Disclosure dates it, "Sat Oct 31", in ET; a naive time is read as UTC."""
    local = (created if created.tzinfo is not None else created.replace(tzinfo=UTC)).astimezone(DATES_TZ)
    return f"{local:%a %b} {local.day}"


def disclosure_lines(
    settings: Settings,
    room: Room | None = None,
    job: JobState | None = None,
    *,
    earlier_session: bool = False,
    demo_room: bool = False,
) -> list[str]:
    """The Disclosure lines in display order: the global ones, then the Room's earlier-builds line or the replay line; empty at the defaults."""
    lines: list[str] = []
    if settings.demo_timescale > 1:
        lines.append(TIMESCALE_LINE.format(n=settings.demo_timescale))
    source = trickster(settings)
    if source == "scripted":
        lines.append(SCRIPTED_LINE)
    elif source == "cut1":
        lines.append(CUT1_LINE)
    lines.extend(MODE_LINES[settings.mode])
    if room is not None and built_earlier(job, demo_room=demo_room):
        lines.append(EARLIER_BUILD_LINE.format(date=build_date(room.created)))
    elif room is not None and earlier_session:
        lines.append(REPLAY_LINE)
    return lines


def meta(settings: Settings, profile: str = "dev") -> Meta:
    return Meta(
        mode=settings.mode,
        guide=settings.guide,
        guide_model=guide_model(settings),
        trickster=trickster(settings),
        demo_timescale=settings.demo_timescale,
        cache=settings.cache,
        profile=profile,
        disclosure=disclosure_lines(settings),
        retention=retention_summary(settings),
    )
