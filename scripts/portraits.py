#!/usr/bin/env python3
"""The four wizard portraits, painted once with `muse-image-1.0` and committed (FR-23, UX-DR83, AD-6).

    uv run scripts/portraits.py   # paints web/public/portraits/<wizard>.webp; commit the four files

One `generate_image` call per wizard through the `image` role's
`ModelProvider` as `wiring.py` builds it from `PROVIDER_IMAGE`, so every call
takes the guarded path: the cache first, then the ledger guard on a miss,
priced at $0.01 an image (about $0.04 for the set). With `CACHE=on` a second
run is four cache hits, adds no ledger entry and changes no file. Each prompt
is the shared oil-portrait style block plus one subject line, both fixed
here; no prompt carries room content, a photo or a Player profile field.

The four images are written only once all four have come back as webp, and a
file is rewritten only when its bytes change. A refused call
(`SpendCapExceeded`) exits 1 printing the cap and the running total, a
`ProviderError` exits 1 printing the error, and an answer that is not a webp
(the mock's canned reply, say) exits 1 too; in each case no portrait file is
written. Play never calls `generate_image` (CAP-7): the web client reads
these committed files and draws the placeholder when one is missing.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import sys
from pathlib import Path
from typing import Literal

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # so `src` imports from any working directory

from scripts.ledger import exit_on_spend_cap
from src.api import wiring
from src.config import Settings
from src.infra.local import CACHE_ROOT, LEDGER_PATH
from src.providers.base import ModelProvider, ProviderError
from src.providers.cache import GuardedCalls
from src.providers.spend import SpendLedger

type Wizard = Literal["architect", "riddler", "guide", "trickster"]

PORTRAITS_ROOT = Path("web/public/portraits")
"""Committed; the web client's Wizard portrait component reads `<wizard>.webp` from here."""

STYLE = (
    "Oil painting on canvas with visible brushwork. "
    "Chiaroscuro lit by a single candle from camera left. "
    "Warm umber, ochre and lamp-amber palette. "
    "Near-black background close to #14100C. "
    "Head and shoulders in three-quarter view, the face inside the center 70% of the frame. "
    "Square 1:1 at 1024 px. "
    "No text, no lettering, no painted frame, no resemblance to any real person."
)
"""The shared style block (DESIGN.md, Portrait art direction); `#14100C` is the `canvas` color."""

SUBJECTS: dict[Wizard, str] = {
    "architect": "The Architect, a wizard, calm and attentive, a brass loupe raised to one eye.",
    "riddler": "The Riddler, a wizard with a half-smile, a sealed folded note held between two fingers.",
    "guide": "The Guide, a wizard, kind and patient, a small lantern held low.",
    "trickster": "The Trickster, a wizard with a sly grin and one eyebrow up, a playing card turned toward the viewer.",
}
"""One subject line per wizard, in the order the script paints them."""


def prompt(wizard: Wizard) -> str:
    """The style block plus the wizard's subject line, and nothing else."""
    return f"{STYLE}\n{SUBJECTS[wizard]}"


def portrait_path(wizard: Wizard) -> Path:
    return PORTRAITS_ROOT / f"{wizard}.webp"


def webp(data: str) -> bytes | None:
    """The decoded image when the provider answered with a base64 webp; `None` otherwise."""
    try:
        image = base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        return None
    return image if image[:4] == b"RIFF" and image[8:12] == b"WEBP" else None


def image_provider(settings: Settings, root: Path) -> tuple[ModelProvider, SpendLedger]:
    """The `image` role's provider over the repo's cache and ledger, as the API wires it (`CACHE=off` skips the cache)."""
    ledger = wiring.spend_ledger(settings, wiring.ledger_store(root / LEDGER_PATH))
    cache = wiring.model_cache(root / CACHE_ROOT)
    enabled = settings.cache == "on"
    provider = wiring.model_provider(settings, "image", lambda host: GuardedCalls(cache, ledger, host=host, enabled=enabled))
    return provider, ledger


def paint(provider: ModelProvider, ledger: SpendLedger) -> dict[Wizard, bytes]:
    """One call per wizard, in order; the first refusal, error or non-webp answer exits 1 before any file is written."""
    images: dict[Wizard, bytes] = {}
    with exit_on_spend_cap():
        for wizard in SUBJECTS:
            before = ledger.running_total_usd()
            try:
                response = provider.generate_image(prompt(wizard))
            except ProviderError as error:
                sys.exit(f"{wizard}: {error}; no portrait file was written")
            image = webp(response.data)
            if image is None:
                sys.exit(f"{wizard}: the {provider.name} image role answered without a webp image; no portrait file was written")
            spent = ledger.running_total_usd() - before
            print(f"{wizard}: {f'billed {spent:.2f} USD' if spent else 'cached'}, {response.model}")
            images[wizard] = image
    return images


def main(argv: list[str] | None = None, *, root: Path = REPO, settings: Settings | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.parse_args(argv)
    provider, ledger = image_provider(settings or Settings.from_env(), root)
    images = paint(provider, ledger)
    for wizard, image in images.items():
        path = root / portrait_path(wizard)
        if path.is_file() and path.read_bytes() == image:
            print(f"unchanged {portrait_path(wizard)}")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(image)
        print(f"wrote {portrait_path(wizard)} ({len(image)} bytes)")
    print(f"running total {ledger.running_total_usd():.2f} USD against the {ledger.cap_usd:.2f} USD local cap")
    return 0


if __name__ == "__main__":
    sys.exit(main())
