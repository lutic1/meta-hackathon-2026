"""Storage and clock adapters behind the ports in `src/pipeline/ports.py` (AD-1, AD-9, AD-10).

`local.py` holds the disk adapters Local mode runs on and `clocks.py` the
session and build clocks; the hosted adapters land in `modal.py`. Adapters
import only ports and the domain, and `src/api/wiring.py` picks them from
`Settings.mode`.
"""
