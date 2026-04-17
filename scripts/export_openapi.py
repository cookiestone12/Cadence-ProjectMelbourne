"""Export the current OpenAPI schema to docs/openapi.json.

Run from the repo root:

    python scripts/export_openapi.py

Pretty-printed with sorted keys so PR diffs are reviewable.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# A SESSION_SECRET is required at import time by backend/main.py.
os.environ.setdefault("SESSION_SECRET", "openapi-export-noop-secret")
os.environ.setdefault("APP_ENV", "development")

from backend.main import app  # noqa: E402
from backend.utils.openapi_backfill import backfill_route_summaries  # noqa: E402


def main() -> int:
    backfill_route_summaries(app)
    schema = app.openapi()
    out_dir = ROOT / "docs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "openapi.json"
    out_path.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {out_path} ({len(schema.get('paths', {}))} paths)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
