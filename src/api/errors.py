"""Typed route errors and the error envelope `{error: {code, message, stage}}` (AD-13).

A route raises one of these classes and `handle_api_error` answers with
the envelope; `stage` is null outside the pipeline and `error.status`, the
job status, appears only on `BuildNotReady`'s `build_not_ready` and is left
out on every other code. A refusal that sets `headers` answers with them,
as `TooManyAttempts` does with `Retry-After`. A body, path or query
that fails validation is answered by `handle_validation_error` with the
same envelope under `invalid_request`. A failure's location is built from
declared names only, so a key the client sent inside a dict field never
appears; an `/api/` path no route serves is `NotFound`.
"""

from __future__ import annotations

from typing import Any, get_args

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ValidationError

from src.domain import schema
from src.domain.schema import ErrorDetail, ErrorEnvelope, JobStatus, Stage


class ApiError(Exception):
    """A refusal a route raises; `code` is the class name in snake_case (Conventions)."""

    status: int
    code: str
    stage: Stage | None = None
    headers: dict[str, str] | None = None

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFound(ApiError):
    """An `/api/` path no route serves, in either mode (AD-13); the path sent is not echoed."""

    status = 404
    code = "not_found"

    def __init__(self) -> None:
        super().__init__("no API route answers this path")


class RoomNotFound(ApiError):
    status = 404
    code = "room_not_found"

    def __init__(self, room_id: str) -> None:
        super().__init__(f"no room {room_id}")


class RoomDeleted(ApiError):
    """A room-keyed or job-keyed route whose Judge room was deleted (AD-9, AD-13): 410, distinct from 404 `room_not_found`."""

    status = 410
    code = "room_deleted"

    def __init__(self, room_id: str) -> None:
        super().__init__(f"room {room_id} was deleted")


class PhotoNotFound(ApiError):
    status = 404
    code = "photo_not_found"

    def __init__(self, room_id: str, index: int) -> None:
        super().__init__(f"room {room_id} has no photo {index}")


class SessionNotFound(ApiError):
    status = 404
    code = "session_not_found"

    def __init__(self, session_id: str) -> None:
        super().__init__(f"no session {session_id}")


class JobNotFound(ApiError):
    status = 404
    code = "job_not_found"

    def __init__(self, job_id: str) -> None:
        super().__init__(f"no job {job_id}")


class BuildNotReady(ApiError):
    """`GET /builds/<job_id>/view` or `/room` of a known job not yet `done` (AD-3, AD-13): 409 with the job `status` in the envelope."""

    status = 409
    code = "build_not_ready"

    def __init__(self, job_id: str, job_status: JobStatus) -> None:
        super().__init__(f"job {job_id} is {job_status}, not done")
        self.job_status: JobStatus = job_status


class UploadRefused(ApiError):
    """An upload ingest refuses before any job exists (AD-7, AD-13): 422 `photo_count`, `unsupported_image` or `bad_downscale`."""

    status = 422
    stage = "ingest"

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class UploadTooLargeRefused(ApiError):
    """The `UploadTooLarge` refusal of `POST /builds` (AD-7, AD-13): 413 at stage `ingest`, before any job, slot or file exists."""

    status = 413
    code = "upload_too_large"
    stage = "ingest"


class AccessDenied(ApiError):
    """Hosted mode: a guarded route without the right `X-Access-Code` (AD-9, AD-13); refused before anything is read or stored."""

    status = 403
    code = "access_denied"

    def __init__(self) -> None:
        super().__init__("this route needs the access code")


class TooManyAttempts(ApiError):
    """Hosted mode: an access attempt past the per-IP limit (AD-9, AD-13); refused before the code is compared."""

    status = 429
    code = "too_many_attempts"

    def __init__(self, retry_after_s: int) -> None:
        super().__init__(f"too many access attempts; try again in {retry_after_s} s")
        self.headers = {"Retry-After": str(retry_after_s)}


class BuildQuotaRefused(ApiError):
    """The `BuildQuotaExceeded` refusal of `POST /builds` (AD-9, AD-13): every judge build is used, so no photo is stored."""

    status = 403
    code = "build_quota_exceeded"


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

    def __init__(self, name: str, error: ValidationError) -> None:
        super().__init__(f"profile {name} does not parse: {_failure(error.errors(include_url=False)[0])}")


class InvalidRequest(ApiError):
    """A request whose body, path or query failed validation; the message names each failing location and never echoes a value sent."""

    status = 422
    code = "invalid_request"

    def __init__(self, error: RequestValidationError) -> None:
        super().__init__("; ".join(_failure(e) for e in error.errors()))


PARAMETER_SOURCES = frozenset({"path", "query", "header", "cookie"})
"""The request parts FastAPI names first in a parameter's location; the next segment is the route's own parameter name."""


def _declared_names() -> frozenset[str]:
    """Every field name of a Schema v1 model, `body`, and each `type` tag, the only words a body location may show."""
    names = {"body"}
    for model in vars(schema).values():
        if isinstance(model, type) and issubclass(model, BaseModel):
            for name, field in model.model_fields.items():
                names.update({name, field.alias or name})
                if name == "type":
                    names.update(tag for tag in get_args(field.annotation) if isinstance(tag, str))
    return frozenset(names)


DECLARED_NAMES = _declared_names()


def _field_path(loc: tuple[Any, ...]) -> str:
    """The declared field path: a dict key the client sent, or any segment the schema does not name, is left out."""
    if loc and loc[0] in PARAMETER_SOURCES:
        return ".".join(map(str, loc[:2]))
    return ".".join(str(part) for part in loc if isinstance(part, int) or part in DECLARED_NAMES) or "body"


def _failure(error: Any) -> str:
    """One failing location and why, built only from the schema's own words: a sent tag, key or value never appears."""
    loc, msg = tuple(error["loc"]), str(error["msg"])
    if error["type"] == "union_tag_invalid":
        ctx = error["ctx"]
        name = str(ctx["discriminator"]).strip("'")
        msg = f"{name} names none of the expected tags: {ctx['expected_tags']}"
    elif error["type"] == "extra_forbidden":
        loc, msg = loc[:-1], "unexpected field"
    elif isinstance(sent := error.get("input"), str) and sent and sent in msg:
        msg = "value is not accepted"
    return f"{_field_path(loc)}: {msg}"


def envelope(error: ApiError) -> ErrorEnvelope:
    status = error.job_status if isinstance(error, BuildNotReady) else None
    return ErrorEnvelope(error=ErrorDetail(code=error.code, message=error.message, stage=error.stage, status=status))


def _answer(error: ApiError) -> JSONResponse:
    """The envelope; `error.status` is set only on `build_not_ready`, so every other code leaves it out."""
    content = envelope(error).model_dump(mode="json")
    return JSONResponse(status_code=error.status, content=content, headers=error.headers)


async def handle_api_error(request: Request, error: ApiError) -> JSONResponse:
    return _answer(error)


async def handle_validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    return _answer(InvalidRequest(error))
