"""Recorded-response replay for adapter tests (AD-17).

A fixture at `tests/fixtures/providers/<model>/<name>.json` holds one live
response only: its status and JSON body, never the request, an input image
or a `data:` URL; adapter tests build their input images in the test.
`transport(name)` serves the fixture to an adapter through an
`httpx.MockTransport`, so no socket opens, and a missing fixture is an
error that names it, never a live call.
"""

from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "providers"


class Fixture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    model: str
    status: int = 200
    body: dict[str, Any]


class MissingFixture(LookupError):
    pass


def load(name: str) -> Fixture:
    """The fixture `<model>/<name>`, e.g. `muse-spark-1.3/chat-three-objects`."""
    path = FIXTURES / f"{name}.json"
    if not path.is_file():
        raise MissingFixture(f"no recorded fixture {name!r} at {path}")
    return Fixture.model_validate_json(path.read_bytes())


def transport(name: str) -> httpx.MockTransport:
    fixture = load(name)
    return httpx.MockTransport(lambda request: httpx.Response(fixture.status, json=fixture.body))
