"""Migration concurrency lock.

Two engineers (or two Reserved-VM instances coming up at the same
time during a deploy) could each try to run Alembic migrations
concurrently and corrupt schema state. This module gives us a
single-row Postgres lock table that brackets the migration step.

Design notes:
  * The lock table itself is bootstrapped with raw DDL — it has to
    exist BEFORE Alembic can run, so it cannot be an Alembic revision.
  * Single-row design: PK is hard-coded to id=1, so concurrent
    INSERT…ON CONFLICT racers serialize cleanly on the primary key.
  * Stale lock auto-clear: if `started_at` is older than 10 minutes
    (a previous deploy crashed mid-migration), we override the lock
    rather than wedging every subsequent deploy.
  * Always release in a `finally` block so a crashed migration
    doesn't permanently block the next deploy. Fail-safe semantics:
    `release_migration_lock` swallows its own errors so it never
    masks the original migration exception.
"""
from __future__ import annotations

import socket
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import text
from sqlalchemy.engine import Engine

from .logging_config import logger

STALE_LOCK_AFTER = timedelta(minutes=10)


def bootstrap_migration_lock_table(engine: Engine) -> None:
    """Create the migration_lock table if it doesn't exist.

    Safe to call on every boot — uses CREATE TABLE IF NOT EXISTS.
    """
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS migration_lock (
                id          INTEGER PRIMARY KEY DEFAULT 1
                            CHECK (id = 1),
                status      VARCHAR NOT NULL DEFAULT 'idle',
                started_at  TIMESTAMPTZ,
                host        VARCHAR,
                revision    VARCHAR
            )
        """))
        conn.execute(text("""
            INSERT INTO migration_lock (id, status)
            VALUES (1, 'idle')
            ON CONFLICT (id) DO NOTHING
        """))


def acquire_migration_lock(engine: Engine, revision_label: str = "pending") -> bool:
    """Attempt to acquire the migration lock.

    Returns True if the lock was acquired by this process. Returns
    False if another live process holds it. A stale lock (older than
    STALE_LOCK_AFTER) is overridden and a WARNING is logged.
    """
    host = socket.gethostname()
    now = datetime.now(timezone.utc)
    stale_cutoff = now - STALE_LOCK_AFTER

    # Capture prior state so we can emit a clear stale-clear log
    # AFTER the takeover, then attempt the conditional UPDATE in a
    # single statement so the row lock serializes concurrent racers.
    with engine.begin() as conn:
        prior = conn.execute(text(
            "SELECT status, started_at, host FROM migration_lock WHERE id = 1 FOR UPDATE"
        )).fetchone()

        result = conn.execute(
            text("""
                UPDATE migration_lock
                SET status     = 'running',
                    started_at = :now,
                    host       = :host,
                    revision   = :rev
                WHERE id = 1
                  AND (
                       status = 'idle'
                    OR started_at IS NULL
                    OR started_at < :stale_cutoff
                  )
                RETURNING id
            """),
            {"now": now, "host": host, "rev": revision_label, "stale_cutoff": stale_cutoff},
        )
        row = result.fetchone()

    if row is not None and prior is not None and prior.status == "running":
        # We just stole a stale lock from a previous owner — emit a
        # loud, explicit log line so operators see this in incident
        # postmortems.
        logger.warning(
            f"Stale migration lock auto-cleared: previous owner host={prior.host} "
            f"started_at={prior.started_at} (older than {STALE_LOCK_AFTER}). "
            f"Taking ownership as host={host}."
        )

    if row is None:
        # Lock held by a live process. Show who has it for ops debugging.
        with engine.connect() as conn:
            holder = conn.execute(text(
                "SELECT host, started_at FROM migration_lock WHERE id = 1"
            )).fetchone()
        logger.warning(
            f"Migration lock is held by host={holder.host if holder else '?'} "
            f"since {holder.started_at if holder else '?'}; this process will not run migrations."
        )
        return False

    return True


def release_migration_lock(engine: Engine, revision_label: Optional[str] = None) -> None:
    """Release the migration lock.

    Always called in a `finally` block. Swallows its own exceptions
    so it never masks an upstream migration error.
    """
    try:
        with engine.begin() as conn:
            conn.execute(
                text("""
                    UPDATE migration_lock
                    SET status     = 'idle',
                        revision   = COALESCE(:rev, revision)
                    WHERE id = 1
                """),
                {"rev": revision_label},
            )
    except Exception as e:
        logger.error(f"Failed to release migration lock (manual cleanup may be required): {e}")


def get_migration_lock_state(engine: Engine) -> dict:
    """Snapshot of the lock row for the migration-status endpoint.

    Resilient to the table not existing yet (e.g. when /api/internal
    is hit before db_setup has ever bootstrapped) — returns nulls
    rather than 500ing.
    """
    empty = {"status": None, "started_at": None, "host": None, "revision": None}
    try:
        with engine.connect() as conn:
            row = conn.execute(text(
                "SELECT status, started_at, host, revision FROM migration_lock WHERE id = 1"
            )).fetchone()
    except Exception as e:
        logger.warning(f"migration_lock not yet bootstrapped: {e}")
        return empty
    if row is None:
        return empty
    return {
        "status": row.status,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "host": row.host,
        "revision": row.revision,
    }
