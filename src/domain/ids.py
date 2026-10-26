"""Prefixed ULIDs minted by server code (AD-18): `sess_`, `call_` and the rest of the Conventions' prefixes.

A ULID is 48 bits of Unix milliseconds then 80 random bits, in Crockford
base32; the millisecond prefix is identity, never session time, which
reaches the domain only as `t_ms` (AD-10).
"""

from __future__ import annotations

import secrets
import time

from .schema import SessionId

CROCKFORD_BASE32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def new_ulid() -> str:
    """26 Crockford base32 characters: 48 bits of Unix milliseconds then 80 random bits."""
    value = (time.time_ns() // 1_000_000) << 80 | int.from_bytes(secrets.token_bytes(10))
    return "".join(CROCKFORD_BASE32[(value >> shift) & 31] for shift in range(125, -1, -5))


def new_session_id() -> SessionId:
    return f"sess_{new_ulid()}"
