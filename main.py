"""Demo entry point. Runs against whichever provider MODEL_PROVIDER names.

Today (mock):
    python main.py chat "Summarize why agent verification matters"
    python main.py image "a red convertible on a coastal road"

From Oct 26 (after wiring docs/MONDAY.md):
    MODEL_PROVIDER=meta python main.py chat "your prompt"
"""

from __future__ import annotations

import sys

from src.config import Settings
from src.providers import get_provider
from src.providers.base import ChatMessage


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[1] not in ("chat", "image"):
        print(__doc__.strip())
        return 2

    command, prompt = argv[1], " ".join(argv[2:])
    settings = Settings.from_env()
    provider = get_provider(settings)
    print(f"provider={provider.name}")

    if command == "chat":
        response = provider.chat(
            [ChatMessage(role="user", content=prompt)],
            model=settings.chat_model,
        )
        print(f"model={response.model}")
        print(response.text)
    else:
        image = provider.generate_image(prompt, model=settings.image_model)
        print(f"model={image.model}")
        print(image.data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
