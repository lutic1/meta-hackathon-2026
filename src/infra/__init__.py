"""Storage and clock adapters behind the ports in `src/pipeline/ports.py` (AD-1, AD-9, AD-10).

`local.py` holds the disk adapters Local mode runs on, `modal.py` the hosted
adapters over Modal Dicts and the Volume, and `clocks.py` the session and
build clocks. Adapters import only ports and the domain, and
`src/api/wiring.py` picks them from `Settings.mode`.
"""
