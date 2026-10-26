"""The `Clock` port (AD-1, AD-10): the one source of time, declared here and implemented nowhere in the domain.

The session and build clocks live in `src/infra/clocks.py`, and
`src/pipeline/ports.py` re-exports this Protocol. Domain code never calls a
clock: a session sees time only as each event's `t_ms`, which the API stamps
from the session clock at append, so replay and live play read the same
milliseconds.
"""

from __future__ import annotations

from typing import Protocol


class Clock(Protocol):
    def now_ms(self) -> int:
        """Milliseconds on this clock; an interval is the difference of two readings."""
        ...
