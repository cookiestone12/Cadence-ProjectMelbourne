"""Programmatic Alembic upgrade with the migration lock.

Wraps `alembic upgrade heads` so it can be invoked from `db_setup.py`
during boot rather than only from the CLI.

Why `heads` (plural): the project currently has more than one Alembic
head revision (multiple parallel branches that have not yet been
merged). `alembic upgrade head` is ambiguous in that case; `heads`
applies all of them.
"""
from __future__ import annotations

import os
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from alembic.runtime.migration import MigrationContext
from alembic import command as alembic_command

from sqlalchemy.engine import Engine

from .logging_config import logger
from .migration_lock import (
    bootstrap_migration_lock_table,
    acquire_migration_lock,
    release_migration_lock,
)


def _alembic_cfg() -> Config:
    """Build an Alembic Config that points at the repo's alembic.ini."""
    repo_root = Path(__file__).resolve().parents[2]
    ini_path = repo_root / "alembic.ini"
    cfg = Config(str(ini_path))
    # Ensure the script_location is absolute; the CLI inherits its
    # working directory but a programmatic call may not.
    cfg.set_main_option("script_location", str(repo_root / "alembic"))
    return cfg


def get_alembic_revision_info(engine: Engine) -> dict:
    """Return current vs head Alembic revision state.

    Used by the /api/internal/migration-status endpoint.
    """
    cfg = _alembic_cfg()
    script = ScriptDirectory.from_config(cfg)

    head_revisions = list(script.get_heads())

    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        current_heads = list(ctx.get_current_heads())

    pending: list[str] = []
    if head_revisions and set(current_heads) != set(head_revisions):
        # Use Alembic's own graph diff so branched / multi-head
        # topologies report correctly. `iterate_revisions(upper,
        # lower)` returns revisions you'd need to apply going from
        # `lower` to `upper` — exactly what "pending" means.
        # `lower=()` (empty) handles the brand-new-DB case.
        lower = tuple(current_heads) if current_heads else ()
        try:
            for rev in script.iterate_revisions(head_revisions, lower):
                if rev.revision and rev.revision not in pending:
                    pending.append(rev.revision)
        except Exception:
            # Graph traversal can fail if the alembic_version table
            # references a revision no longer present in the script
            # directory; surface as empty pending rather than 500.
            pending = []

    return {
        "current_revisions": current_heads,
        "head_revisions": head_revisions,
        "is_up_to_date": set(current_heads) == set(head_revisions) and bool(head_revisions),
        "pending_revisions": pending,
    }


def upgrade_to_heads(engine: Engine) -> None:
    """Run `alembic upgrade heads` (caller MUST already hold the lock)."""
    info = get_alembic_revision_info(engine)
    if info["is_up_to_date"]:
        logger.info(
            f"Alembic is already at head ({','.join(info['head_revisions'])}); "
            f"skipping upgrade."
        )
        return
    logger.info(
        f"Running alembic upgrade heads (current={info['current_revisions']}, "
        f"target={info['head_revisions']}, pending={len(info['pending_revisions'])})"
    )
    cfg = _alembic_cfg()
    alembic_command.upgrade(cfg, "heads")
    logger.info("Alembic upgrade heads complete.")
