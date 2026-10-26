"""The pipeline: the stage runner over the council, the domain and the ports in `ports.py` (AD-1, AD-7).

Pipeline code imports only `src/domain`, `src/council` and port modules; it
receives every adapter by injection from `src/api/wiring.py`.
"""
