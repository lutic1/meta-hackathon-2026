"""The Architect prompt: one pure request over the stored photos (AD-5, AD-18).

`build_architect_prompt(photos)` takes only the stored downscaled JPEG bytes,
in upload order, so no Room, Clue or profile field exists to leak (AD-3), and
the same bytes always render the same request, which the AD-6 cache key and
the AD-16 prompt hash rely on. The photos travel as `images`, never inside a
message, and the adapter owns the HTTP. Attributes are short visible descriptions
a player can confirm (colour, material, shape, size, count, placement, readable text
verbatim), since Validator rule 4 only passes a Puzzle whose evidence cites one and most
objects in a real room carry no readable text. Candidates come back
without ids, correlated by list position; the segment stage mints `ix_` ids.
A reply off the response shape is a `malformed` `ProviderError` (AD-13) with
a fixed message, so a Build ends `failed` with code `provider_error` and
`validation_error` keeps its meaning: a draft the Validator sent back.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

import pydantic

from src.domain.schema import ArchitectResponse, JobId, Stage
from src.providers.base import ChatMessage, ChatResponse, ModelProvider, ProviderError, ReasoningEffort

REASONING_EFFORT: ReasoningEffort = "low"

SYSTEM = """\
You are the Architect of an escape room built from photos of a real room.
You list the distinct physical objects a player could click on in these photos.

For each object, give:
- label: a short noun phrase naming the object, as a segmentation model would be asked for it.
- plural: true when the label names several like objects (a row of books, three candles), false for one object.
- photo: the index of the photo that shows the object most clearly. Photos are indexed from 0 in the order given.
- box: the object's bounding box in that photo as [x0, y0, x1, y1] on a 0 to 1000 grid, origin top left, x across and y down.
- attributes: two to four short visible attributes of the object, each one a player could confirm by looking at it: its colour, material, shape, size, count, where it sits or hangs, and any text that can be read on it (a number, a word, a marking) exactly as it appears, character for character. Each attribute is at most four words, in lower case except readable text, which keeps its spelling and case. Never guess unreadable text, never give a brand name, never describe a person.
- confidence: from 0 to 1, how sure you are that the object is there and the label fits.

List each object once, in any order. Do not number them or give them ids; the list position is the only reference.
Prefer objects with a readable attribute or a distinct look. Skip walls, floors, ceilings and people.
Answer only with the JSON the schema asks for."""


def task_text(count: int) -> str:
    """The user text: the photo count, so every `photo` index has a stated range."""
    return f"{count} photos follow in upload order, indexed 0 to {count - 1}. List the objects as instructed."


def fixed_prefix() -> str:
    """The byte-stable part of every Architect request: the system message with its instructions."""
    return SYSTEM


def prompt_hash() -> str:
    """sha256 of the fixed prefix, for `Provenance.prompt_hashes['architect']` (AD-16)."""
    return hashlib.sha256(fixed_prefix().encode()).hexdigest()


@dataclass(frozen=True)
class ArchitectPrompt:
    """The `chat` arguments of the one vision call; `send` makes it and parses the reply, keeping the reply for its receipt.

    A reply that does not parse as the response schema raises `ProviderError(200, "malformed", ...)`
    quoting nothing from the reply, as `meta_api.py` does for a malformed sam-3.1 reply.
    """

    messages: list[ChatMessage]
    images: list[bytes]
    response_schema: type[ArchitectResponse]
    reasoning_effort: ReasoningEffort

    def send(
        self, provider: ModelProvider, *, job_id: JobId | None = None, stage: Stage | None = None
    ) -> tuple[ArchitectResponse, ChatResponse]:
        reply = provider.chat(
            self.messages,
            images=self.images,
            response_schema=self.response_schema,
            reasoning_effort=self.reasoning_effort,
            job_id=job_id,
            stage=stage,
        )
        try:
            response = self.response_schema.model_validate_json(reply.text)
        except pydantic.ValidationError:
            raise ProviderError(200, "malformed", "the Architect reply did not follow the response shape") from None
        return response, reply


def build_architect_prompt(photos: list[bytes]) -> ArchitectPrompt:
    """One request over every stored photo, as bytes in upload order; a photo set is never empty."""
    if not photos:
        raise ValueError("the Architect needs at least one photo")
    return ArchitectPrompt(
        messages=[
            ChatMessage(role="system", content=fixed_prefix()),
            ChatMessage(role="user", content=task_text(len(photos))),
        ],
        images=list(photos),
        response_schema=ArchitectResponse,
        reasoning_effort=REASONING_EFFORT,
    )
