#!/bin/bash
# Fail-fast: if db_setup exits non-zero (e.g. migration lock wait
# timeout, fatal Alembic failure), do NOT start uvicorn. Serving
# traffic against an unmigrated/unknown schema is the exact regression
# the migration-safety work is designed to prevent.
set -euo pipefail

python -m backend.db_setup
exec python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000
