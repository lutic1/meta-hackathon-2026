"""Typed route errors and the error envelope `{error: {code, message, stage}}` (AD-13).

A route raises one of these classes and `handle_api_error` answers with
the envelope; `stage` is null outside the pipeline and `status` appears
only on `build_not_ready`, so it is left unset here.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from src.domain.schema import ErrorDetail, ErrorEnvelope, Stage


class ApiError(Exception):
    """A refusal a route raises; `code` is the class name in snake_case (Conventions)."""

    status: int
    code: str
    stage: Stage | None = None

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class RoomNotFound(ApiError):
    status = 404
    code = "room_not_found"

    def __init__(self, room_id: str) -> None:
        super().__init__(f"no room {room_id}")


class PhotoNotFound(ApiError):
    status = 404
    code = "photo_not_found"

    def __init__(self, room_id: str, index: int) -> None:
        super().__init__(f"room {room_id} has no photo {index}")


class ProfileNotFound(ApiError):
    status = 404
    code = "profile_not_found"

    def __init__(self, name: str) -> None:
        super().__init__(f"no profile {name}")


class InvalidProfileName(ApiError):
    """A `/profile/<name>` that is not a plain file name under `rooms/profiles/`."""

    status = 422
    code = "invalid_profile_name"

    def __init__(self, name: str) -> None:
        super().__init__(f"profile name {name!r} is not a file name")


class InvalidProfile(ApiError):
    """A `PUT /profile/<name>` body that does not parse as a `Profile`; the stored file is left unchanged."""

    status = 422
    code = "invalid_profile"

    def __init__(self, name: str, reason: str) -> None:
        super().__init__(f"profile {name} does not parse: {reason}")


def envelope(error: ApiError) -> ErrorEnvelope:
    return ErrorEnvelope(error=ErrorDetail(code=error.code, message=error.message, stage=error.stage))


async def handle_api_error(request: Request, error: ApiError) -> JSONResponse:
    """The envelope with `status` left out, since no route here answers `build_not_ready`."""
    return JSONResponse(status_code=error.status, content=envelope(error).model_dump(mode="json", exclude_unset=True))
