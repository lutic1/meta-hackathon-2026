"""Settings: the one place that reads the environment (AD-14).

`Settings.from_env()` reads each key once from the environment (and from
`.env`, loaded at import; a variable that is already set wins) and
validates it. Every other module receives what it needs by injection.
`scripts/doctor.py` is exempt (stdlib, runs before `uv sync`).

`MODE` picks the defaults a key takes when it is unset (`MODE_DEFAULTS`:
`SPEND_CAP_USD` 60 and `GUIDE=ollama` locally, 20 and `GUIDE=verbatim`
hosted) and the values the running mode refuses at startup
(`MODE_REFUSED`: hosted refuses `GUIDE=ollama` and `DEMO_TRICKSTER=record`).
An explicit `SPEND_CAP_USD` overrides the running mode's default; a later
allocation is set by configuration at the ledger reset, with no date logic
here (AD-6, AD-14). `HOSTED_SPEND_CAP_USD` (default 20) is the Hosted
allocation the local ledger export adds to the Local one; it must equal the
`SPEND_CAP_USD` in the `keyframe` Secret, and the export records whether it
was set or is the default.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from src.domain.rungs import HINTS_PER_SESSION, HintPolicy

load_dotenv()

ROLES = ("architect", "riddler", "dryrun", "storyteller", "trickster", "image")

ENV_KEYS = (
    "MODE",
    "MIN_CONTAINERS",
    "CACHE",
    "SPEND_CAP_USD",
    "HOSTED_SPEND_CAP_USD",
    "DEMO_TIMESCALE",
    "DEMO_TRICKSTER",
    "DEMO_PROPOSALS_DIR",
    "DRY_RUN",
    "REGEN_MAX",
    "GUIDE",
    "HINT_POLICY",
    "HINT_CAP",
    "MODEL_PROVIDER",
    *(f"PROVIDER_{role.upper()}" for role in ROLES),
    *(f"MODEL_{role.upper()}" for role in ROLES),
    "MODEL_API_KEY",
    "META_MODEL_API_BASE_URL",
    "OPENAI_COMPATIBLE_BASE_URL",
    "OPENAI_COMPATIBLE_API_KEY",
    "FAL_KEY",
    "OLLAMA_HOST",
    "ACCESS_CODE",
)
"""Every environment key `Settings` reads; `.env.example` lists each one blank."""

SECRET_KEYS = ("MODEL_API_KEY", "FAL_KEY", "OPENAI_COMPATIBLE_API_KEY", "ACCESS_CODE")

MUSE_SPARK = "muse-spark-1.3"
MUSE_IMAGE = "muse-image-1.0"

type Mode = Literal["local", "hosted"]
type CapSource = Literal["env", "default"]

MODE_DEFAULTS: dict[str, dict[str, object]] = {
    "local": {"spend_cap_usd": 60, "guide": "ollama"},
    "hosted": {"spend_cap_usd": 20, "guide": "verbatim"},
}
"""Per mode, the value a field takes when its key is unset: the 2.3 spend allocations and the Guide (AD-6, AD-14)."""
MODE_REFUSED: dict[Mode, dict[str, str]] = {
    "local": {},
    "hosted": {"guide": "ollama", "demo_trickster": "record"},
}
"""Per mode, the values `Settings` refuses at startup: no Guide model and no recorder in Hosted mode (AD-14, AD-15)."""


class Settings(BaseModel, frozen=True):
    # Product flags (AD-14).
    mode: Mode = "local"
    min_containers: int = Field(default=0, ge=0)
    """The warm-container floor the hosted `web` function is deployed with (AD-9)."""
    cache: Literal["on", "off"] = "on"
    spend_cap_usd: float = Field(default=60, ge=0)
    """The running mode's allocation (AD-6): `SPEND_CAP_USD`, else the mode's default in `MODE_DEFAULTS`."""
    hosted_spend_cap_usd: float = Field(default=20, ge=0)
    """The Hosted-mode allocation the local export adds to the Local one for the combined ceiling (AD-6): `HOSTED_SPEND_CAP_USD`, else 20.

    The hosted process enforces its own allocation, `SPEND_CAP_USD` in the
    `keyframe` Secret, which the local process cannot see; set this key to
    the same value. `hosted_spend_cap_source` says whether it was set.
    """
    demo_timescale: int = Field(default=1, ge=1)
    demo_trickster: Literal["live", "record", "scripted", "authored"] = "live"
    demo_proposals_dir: Path | None = None
    """The folder holding the proposals `scripted` and `authored` replay and `record` writes (AD-15).

    Unset, wiring reads `proposals/` at the repo root; `scripts/load_fixtures.py`
    installs the four-lock recording under `rooms/proposals/` and prints the
    value to set for local play.
    """
    dry_run: Literal["on", "off"] = "on"
    regen_max: int = Field(default=2, ge=0)
    guide: Literal["ollama", "verbatim"] = "ollama"
    hint_policy: HintPolicy = "chest"
    """Story mode: `chest` (only asked Rungs, `hint_cap` per Session) or `ladder` (idle and wrong-attempt Rungs too)."""
    hint_cap: int = Field(default=HINTS_PER_SESSION, ge=0)
    """The chest's hints per Session under `chest`, fixed at each Session's start."""

    # Adapter settings. `MODEL_PROVIDER` is the default for every `PROVIDER_<ROLE>`.
    model_provider: str = "meta"
    provider_architect: str = "meta"
    provider_riddler: str = "meta"
    provider_dryrun: str = "meta"
    provider_storyteller: str = "meta"
    provider_trickster: str = "meta"
    provider_image: str = "meta"
    model_architect: str = MUSE_SPARK
    model_riddler: str = MUSE_SPARK
    model_dryrun: str = MUSE_SPARK
    model_storyteller: str = MUSE_SPARK
    model_trickster: str = MUSE_SPARK
    model_image: str = MUSE_IMAGE
    model_api_key: str | None = None
    meta_model_api_base_url: str | None = None
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: str | None = None
    fal_key: str | None = None
    ollama_host: str | None = None
    access_code: str | None = None

    @property
    def hosted_spend_cap_source(self) -> CapSource:
        """`env` when `HOSTED_SPEND_CAP_USD` set the Hosted allocation, `default` when it is the default 20."""
        return "env" if "hosted_spend_cap_usd" in self.model_fields_set else "default"

    @model_validator(mode="before")
    @classmethod
    def _mode_defaults(cls, data: Any) -> Any:
        """Fill each unset field `MODE_DEFAULTS` names with the running mode's value; a set one wins."""
        if not isinstance(data, dict):
            return data
        return {**MODE_DEFAULTS.get(data.get("mode", "local"), {}), **data}

    @field_validator(*sorted({field for refused in MODE_REFUSED.values() for field in refused}))
    @classmethod
    def _refused_in_mode(cls, value: str, info: ValidationInfo) -> str:
        """Fail at startup on a value the running mode refuses; the error names only that field's value."""
        mode = info.data.get("mode")
        field = info.field_name or ""
        if mode is not None and MODE_REFUSED[mode].get(field) == value:
            raise ValueError(f"MODE={mode} refuses {field.upper()}={value}")
        return value

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> Settings:
        """Build the settings, reading each key exactly once. A blank value means unset."""
        env = os.environ if environ is None else environ
        values = {key: env.get(key) or None for key in ENV_KEYS}
        model_provider = (values.pop("MODEL_PROVIDER") or "meta").lower()
        fields: dict[str, object] = {"model_provider": model_provider}
        for role in ROLES:
            provider = values.pop(f"PROVIDER_{role.upper()}")
            fields[f"provider_{role}"] = (provider or model_provider).lower()
        for key, value in values.items():
            if value is not None:
                fields[key.lower()] = value
        return cls(**fields)
