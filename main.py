"""Smoke CLI. Runs against whichever provider MODEL_PROVIDER names.

    uv run python main.py chat "Summarize why agent verification matters"
    uv run python main.py image "a red convertible on a coastal road"

MODEL_PROVIDER=mock needs no keys. MODEL_PROVIDER=meta reads
META_MODEL_API_KEY from .env; see docs/MONDAY.md before the first paid call.
"""

from __future__ import annotations

import sys

from src.config import Settings
from src.domain.schema import Role
from src.providers.base import ChatMessage, ModelProvider
from src.providers.meta_api import MetaModelProvider
from src.providers.mock import MockProvider


def get_provider(settings: Settings, role: Role = "architect") -> ModelProvider:
    """Pick the adapter `Settings` names (per-role wiring lands in `src/api/wiring.py`)."""
    if settings.model_provider == "mock":
        return MockProvider(role)
    if settings.model_provider == "meta":
        return MetaModelProvider(
            api_key=settings.meta_model_api_key,
            base_url=settings.meta_model_api_base_url,
        )
    raise ValueError(f"Unknown MODEL_PROVIDER {settings.model_provider!r}. Use 'mock' or 'meta'.")


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] not in ("chat", "image"):
        print(__doc__.strip())
        return 2

    command, prompt = argv[1], " ".join(argv[2:])
    settings = Settings.from_env()
    provider = get_provider(settings, "architect" if command == "chat" else "image")
    print(f"provider={provider.name}")

    if command == "chat":
        response = provider.chat([ChatMessage(role="user", content=prompt)])
        print(f"model={response.model}")
        print(response.text)
    else:
        image = provider.generate_image(prompt)
        print(f"model={image.model}")
        print(image.data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
