#!/bin/bash
set -e

cd frontend && npm install --no-fund --no-audit 2>&1
cd ..

# Catch schema drift between SQLAlchemy models and the Alembic
# migrations before it ships. The check is a hard fail: if the next
# `alembic upgrade heads` would produce a schema that disagrees with
# `backend/models/models.py`, the merge is blocked. See DEPLOYMENT.md
# §4 (Schema parity check) for the rationale and how to reconcile.
if [ -n "${DATABASE_URL:-}" ]; then
  python scripts/check_schema_parity.py
else
  echo "post-merge: DATABASE_URL not set, skipping schema parity check"
fi
