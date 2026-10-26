"""Storage adapters per mode (AD-9): `local.py` under `MODE=local`, `modal.py` under `MODE=hosted`.

Each adapter implements a port from `src/pipeline/ports.py` over the
domain only; API wiring picks one set from `Settings` and injects it.
"""
