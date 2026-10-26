#!/usr/bin/env python3
"""Write the `GET /schema` body to `web/types/schema.json`, the input `npm run types` compiles (AD-2).

    uv run scripts/schema.py

The body is `api_schema()`, the function the route returns, so no server
needs to run. `web/scripts/types.mjs` turns the file into `web/types/index.ts`;
both files are committed, and `tests/web/test_types.py` fails while the
file differs from what `GET /schema` serves.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # so `src` imports from any working directory

from src.api.app import api_schema

SCHEMA_JSON = REPO / "web" / "types" / "schema.json"


def render(schema: dict) -> str:
    """The committed form: two-space indent, keys in the served order, one trailing newline."""
    return json.dumps(schema, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    SCHEMA_JSON.parent.mkdir(parents=True, exist_ok=True)
    SCHEMA_JSON.write_text(render(api_schema()), encoding="utf-8")
    print(f"wrote {SCHEMA_JSON.relative_to(REPO)}")


if __name__ == "__main__":
    main()
