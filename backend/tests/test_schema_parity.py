"""Pytest wrapper around ``scripts/check_schema_parity.py``.

Runs the same dual-schema diff used by the post-merge hook so that drift
between ``backend/models/models.py`` and the Alembic migrations also
shows up in the regular test suite.

Skipped when ``DATABASE_URL`` does not point at Postgres (e.g. the
SQLite-backed unit-test runs in CI for unrelated reasons): the parity
check is a Postgres-shape question and has no meaning against SQLite.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def test_alembic_matches_models() -> None:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url.startswith(("postgresql://", "postgresql+psycopg2://")):
        pytest.skip(
            "schema parity check requires a Postgres DATABASE_URL "
            "(found: empty or non-Postgres)"
        )

    from scripts.check_schema_parity import run

    exit_code = run()
    assert exit_code == 0, (
        "Schema drift detected between Alembic migrations and "
        "backend/models/models.py — see captured stderr for the full list."
    )
