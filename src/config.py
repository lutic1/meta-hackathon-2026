"""Settings: the one place that reads the environment (AD-14).

`Settings.from_env()` reads each key once from the environment (and from
`.env`, loaded at import; a variable that is already set wins) and
validates it. Every other module receives what it needs by injection.
`scripts/doctor.py` is exempt (stdlib, runs before `uv sync`).
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Literal

from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

ROLES = ("architect", "riddler", "dryrun", "trickster", "image")

ENV_KEYS = (
    "CACHE",
    "SPEND_CAP_USD",
    "DEMO_TIMESCALE",
    "DEMO_TRICKSTER",
    "DRY_RUN",
    "REGEN_MAX",
    "GUIDE",
    "MODEL_PROVIDER",
    *(f"PROVIDER_{role.upper()}" for role in ROLES),
    *(f"MODEL_{role.upper()}" for role in ROLES),
    "META_MODEL_API_KEY",
    "META_MODEL_API_BASE_URL",
    "OPENAI_COMPATIBLE_BASE_URL",
    "OPENAI_COMPATIBLE_API_KEY",
    "FAL_KEY",
    "OLLAMA_HOST",
    "ACCESS_CODE",
)
"""Every environment key `Settings` reads; `.env.example` lists each one blank."""

SECRET_KEYS = ("META_MODEL_API_KEY", "FAL_KEY", "OPENAI_COMPATIBLE_API_KEY", "ACCESS_CODE")

MUSE_SPARK = "muse-spark-1.3"
MUSE_IMAGE = "muse-image-1.0"


class Settings(BaseModel, frozen=True):
    # Product flags (AD-14). `MODE` and `MIN_CONTAINERS` land with the first hosted story.
    cache: Literal["on", "off"] = "on"
    spend_cap_usd: float = Field(default=60, ge=0)  # the Local-mode allocation (AD-6)
    demo_timescale: int = Field(default=1, ge=1)
    demo_trickster: Literal["live", "record", "scripted", "authored"] = "live"
    dry_run: Literal["on", "off"] = "on"
    regen_max: int = Field(default=2, ge=0)
    guide: Literal["ollama", "verbatim"] = "ollama"

    # Adapter settings. `MODEL_PROVIDER` is the default for every `PROVIDER_<ROLE>`.
    model_provider: str = "meta"
    provider_architect: str = "meta"
    provider_riddler: str = "meta"
    provider_dryrun: str = "meta"
    provider_trickster: str = "meta"
    provider_image: str = "meta"
    model_architect: str = MUSE_SPARK
    model_riddler: str = MUSE_SPARK
    model_dryrun: str = MUSE_SPARK
    model_trickster: str = MUSE_SPARK
    model_image: str = MUSE_IMAGE
    meta_model_api_key: str | None = None
    meta_model_api_base_url: str | None = None
    openai_compatible_base_url: str | None = None
    openai_compatible_api_key: str | None = None
    fal_key: str | None = None
    ollama_host: str | None = None
    access_code: str | None = None

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
