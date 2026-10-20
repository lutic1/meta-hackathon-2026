"""Settings, read from the environment (and .env if present).

Copy .env.example to .env and fill in what you have. Today everything
runs on defaults: provider=mock, no keys needed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:  # python-dotenv is optional; env vars work without it.
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass


@dataclass
class Settings:
    provider: str = "mock"  # "mock" today, "meta" from Oct 26
    meta_api_key: str | None = None
    meta_base_url: str | None = None
    chat_model: str | None = None
    image_model: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            provider=os.environ.get("MODEL_PROVIDER", "mock").lower(),
            meta_api_key=os.environ.get("META_MODEL_API_KEY") or None,
            meta_base_url=os.environ.get("META_MODEL_API_BASE_URL") or None,
            chat_model=os.environ.get("CHAT_MODEL") or None,
            image_model=os.environ.get("IMAGE_MODEL") or None,
        )
