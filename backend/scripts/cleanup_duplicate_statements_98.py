"""Task #98 — One-shot cleanup of two known duplicate royalty
statements that were uploaded to production before the duplicate-blocking
guard shipped in task #94.

Targets (org-scoped, verified against the prod reconciliation report):

  - Statement #17 (BMI Jan-Jun 2024, $18,622.98) is a duplicate of #18
  - Statement #11 (Marri BMI 2026, $48.30)        is a duplicate of #15

Re-uses the production-grade ``_perform_statement_delete`` helper from
``routes/royalties.py`` so the cleanup goes through the *same* cascade
path as the user-facing delete button: lines, ledger entries, action
items, transactions/allocations, advance balance restore, payout
unwind, audit log, file-on-disk cleanup.

Safety:
  * Defaults to **dry-run**. Pass ``--apply`` to actually delete.
  * Idempotent: if a target statement is already gone, the script logs
    a "skipped" line and continues.
  * Verifies before deleting that the duplicate and its original share
    the same ``organization_id`` and the same ``total_revenue_cents``.
    If either check fails, the target is skipped (never deleted) and
    the operator is told to investigate.
  * The audit log entry is written by ``_perform_statement_delete`` so
    a forensic trail is left automatically.

Usage (run inside the backend venv from the project root)::

    # Dry-run (no DB writes)
    python -m backend.scripts.cleanup_duplicate_statements_98 \\
        --as-user-id <master_admin_user_id>

    # Actually delete
    python -m backend.scripts.cleanup_duplicate_statements_98 \\
        --as-user-id <master_admin_user_id> --apply
"""
from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from typing import List, Optional

from sqlalchemy.orm import Session

from ..models.database import SessionLocal
from ..models.models import RoyaltyStatement, User

logger = logging.getLogger("cleanup_duplicate_statements_98")


@dataclass(frozen=True)
class DuplicateTarget:
    duplicate_id: int
    original_id: int
    expected_total_cents: int
    description: str


TARGETS: List[DuplicateTarget] = [
    DuplicateTarget(
        duplicate_id=17,
        original_id=18,
        expected_total_cents=1_862_298,
        description="BMI January-June 2024 ($18,622.98)",
    ),
    DuplicateTarget(
        duplicate_id=11,
        original_id=15,
        expected_total_cents=4_830,
        description="Marri BMI 2026 ($48.30)",
    ),
]


@dataclass
class TargetResult:
    target: DuplicateTarget
    status: str
    message: str
    summary: Optional[dict] = None


def _verify_target(db: Session, t: DuplicateTarget) -> tuple[Optional[RoyaltyStatement], Optional[str]]:
    """Return (statement_to_delete, error_message). statement is None
    when the duplicate has already been removed (idempotent skip)."""
    dup = db.query(RoyaltyStatement).filter(RoyaltyStatement.id == t.duplicate_id).first()
    if dup is None:
        return None, "duplicate already deleted (idempotent skip)"

    orig = db.query(RoyaltyStatement).filter(RoyaltyStatement.id == t.original_id).first()
    if orig is None:
        return None, (
            f"REFUSING TO DELETE: original statement #{t.original_id} not found. "
            f"Duplicate #{t.duplicate_id} left in place."
        )

    if dup.organization_id != orig.organization_id:
        return None, (
            f"REFUSING TO DELETE: duplicate #{t.duplicate_id} is in org "
            f"{dup.organization_id} but original #{t.original_id} is in org "
            f"{orig.organization_id}. Not actually duplicates."
        )

    if (dup.total_revenue_cents or 0) != t.expected_total_cents:
        return None, (
            f"REFUSING TO DELETE: duplicate #{t.duplicate_id} total is "
            f"{dup.total_revenue_cents} cents but expected "
            f"{t.expected_total_cents}. Investigate before deleting."
        )

    if (orig.total_revenue_cents or 0) != t.expected_total_cents:
        return None, (
            f"REFUSING TO DELETE: original #{t.original_id} total is "
            f"{orig.total_revenue_cents} cents but expected "
            f"{t.expected_total_cents}. Investigate before deleting."
        )

    return dup, None


def cleanup_duplicates(
    db: Session,
    as_user: User,
    apply: bool = False,
    targets: Optional[List[DuplicateTarget]] = None,
) -> List[TargetResult]:
    """Delete each target duplicate. Returns one TargetResult per target.

    The caller controls commit/rollback so this can be exercised by
    tests inside a single transaction.
    """
    from ..routes.royalties import _perform_statement_delete

    targets = targets if targets is not None else TARGETS
    results: List[TargetResult] = []

    for t in targets:
        stmt, err = _verify_target(db, t)
        if err is not None and stmt is None:
            results.append(TargetResult(
                target=t,
                status="SKIPPED",
                message=err,
            ))
            logger.warning("[stmt #%d] SKIPPED: %s", t.duplicate_id, err)
            continue

        assert stmt is not None  # for type-checkers
        if not apply:
            results.append(TargetResult(
                target=t,
                status="DRY_RUN",
                message=(
                    f"Would delete duplicate #{t.duplicate_id} "
                    f"({t.description}) in org {stmt.organization_id}, "
                    f"original #{t.original_id} preserved."
                ),
            ))
            logger.info(
                "[stmt #%d] DRY-RUN: would delete %s in org %d (original #%d preserved)",
                t.duplicate_id, t.description, stmt.organization_id, t.original_id,
            )
            continue

        org_id = stmt.organization_id
        # Per-target SAVEPOINT so a failure on target B does NOT
        # silently undo target A. Without this, db.rollback() in the
        # except branch would unwind the whole outer transaction
        # while still reporting earlier targets as DELETED, which
        # would mislead operators reading the printed summary.
        savepoint = db.begin_nested()
        try:
            summary = _perform_statement_delete(db, stmt, org_id, as_user)
            savepoint.commit()
            results.append(TargetResult(
                target=t,
                status="DELETED",
                message=(
                    f"Deleted duplicate #{t.duplicate_id} ({t.description}) "
                    f"from org {org_id}. Audit log written."
                ),
                summary=summary,
            ))
            logger.info(
                "[stmt #%d] DELETED %s from org %d (audit logged)",
                t.duplicate_id, t.description, org_id,
            )
        except Exception as e:
            try:
                savepoint.rollback()
            except Exception:
                logger.exception("[stmt #%d] savepoint rollback failed", t.duplicate_id)
            results.append(TargetResult(
                target=t,
                status="ERROR",
                message=f"Delete failed for #{t.duplicate_id}: {e}",
            ))
            logger.exception("[stmt #%d] DELETE FAILED", t.duplicate_id)

    return results


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s :: %(message)s",
    )
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform the deletes. Without this flag the script is a dry-run.",
    )
    parser.add_argument(
        "--as-user-id",
        type=int,
        required=True,
        help="ID of the User the audit log should attribute the delete to. "
             "Use a master admin (is_super_admin=True) so it's clear this was "
             "an administrative cleanup, not an end-user action.",
    )
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == args.as_user_id).first()
        if user is None:
            logger.error("User #%d not found. Aborting.", args.as_user_id)
            return 2
        if not getattr(user, "is_super_admin", False):
            logger.error(
                "User #%d (%s) is not a master admin. Refusing to attribute "
                "a prod data cleanup to a non-admin. Aborting.",
                user.id, user.username,
            )
            return 2

        results = cleanup_duplicates(db, user, apply=args.apply)

        if args.apply:
            db.commit()

        deleted = sum(1 for r in results if r.status == "DELETED")
        skipped = sum(1 for r in results if r.status == "SKIPPED")
        dry = sum(1 for r in results if r.status == "DRY_RUN")
        errors = sum(1 for r in results if r.status == "ERROR")

        logger.info(
            "Done. deleted=%d skipped=%d dry_run=%d errors=%d",
            deleted, skipped, dry, errors,
        )
        for r in results:
            logger.info("  - stmt #%d: %s — %s", r.target.duplicate_id, r.status, r.message)

        return 0 if errors == 0 else 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
