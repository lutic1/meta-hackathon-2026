"""Provider factory. The one place that knows which backend is live."""

from __future__ import annotations

from ..config import Settings
from .base import ModelProvider
from .meta_api import MetaModelProvider
from .mock import MockProvider

__all__ = [
    "ModelProvider",
    "MockProvider",
    "MetaModelProvider",
    "get_provider",
]


def get_provider(settings: Settings | None = None) -> ModelProvider:
    settings = settings or Settings.from_env()
    if settings.provider == "mock":
        return MockProvider()
    if settings.provider == "meta":
        return MetaModelProvider(
            api_key=settings.meta_api_key,
            base_url=settings.meta_base_url,
        )
    raise ValueError(
        f"Unknown MODEL_PROVIDER {settings.provider!r}. Use 'mock' or 'meta'."
    )
