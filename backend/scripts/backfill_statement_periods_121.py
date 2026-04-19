"""
Backfill script for Task #121.

Walks every RoyaltyStatement with NULL `period_start` and tries to recover
the reporting period so the underwriting/decay engines can place the
statement in the correct historical bucket. Resolution order:

  1. Re-parse the original PDF if `file_path` still resolves to a readable
     file under `uploads/` (uses utils.pdf_statement_parser.parse_period_from_pdf).
  2. Fall back to filename heuristics for legacy uploads where the PDF is
     no longer reachable (utils.pdf_statement_parser.parse_period_from_filename).
  3. Otherwise leave the statement in PERIOD_MISSING state — operators will
     correct it via the in-app "Fix period" action surfaced on the
     Royalties page reconciliation badge.

When a period is recovered, the script also fills `activity_period_start` /
`activity_period_end` on every `RoyaltyStatementLine` belonging to that
statement that has no per-line period of its own (the upload pipeline writes
these on new uploads — older lines were left NULL).

Usage:
    python -m backend.scripts.backfill_statement_periods_121 [--dry-run] [--org-id N]
"""
import argparse
import os
import sys
from datetime import date

from backend.models.database import SessionLocal
from backend.models.models import RoyaltyStatement, RoyaltyStatementLine
from backend.utils.pdf_statement_parser import (
    parse_period_from_filename,
    parse_period_from_pdf,
)


def _resolve_period(stmt: RoyaltyStatement):
    """Returns (start, end, source) or (None, None, None) when nothing parseable."""
    if stmt.file_path and os.path.isfile(stmt.file_path) and stmt.file_path.lower().endswith(".pdf"):
        try:
            with open(stmt.file_path, "rb") as f:
                content = f.read()
            start, end = parse_period_from_pdf(content, file_name=stmt.file_name)
            if start and end:
                return start, end, "pdf"
        except Exception as e:
            print(f"  ! pdf re-parse failed for stmt {stmt.id}: {e}")

    start, end = parse_period_from_filename(stmt.file_name)
    if start and end:
        return start, end, "filename"

    return None, None, None


def backfill(org_id=None, dry_run=False):
    db = SessionLocal()
    try:
        # Treat a statement as missing-period when EITHER endpoint is NULL —
        # a statement with start but no end can't be placed in the right
        # bucket either, and the underwriting engine ignores half-open ranges.
        from sqlalchemy import or_
        q = db.query(RoyaltyStatement).filter(
            or_(RoyaltyStatement.period_start.is_(None), RoyaltyStatement.period_end.is_(None))
        )
        if org_id is not None:
            q = q.filter(RoyaltyStatement.organization_id == org_id)
        statements = q.order_by(RoyaltyStatement.id).all()

        print(f"Found {len(statements)} statement(s) with NULL period_start"
              + (f" in org {org_id}" if org_id else ""))

        recovered = 0
        skipped = 0
        line_updates = 0

        for stmt in statements:
            start, end, source = _resolve_period(stmt)
            if not start or not end:
                skipped += 1
                print(f"  - stmt {stmt.id} ({stmt.file_name!r}): no period recovered, leaving as PERIOD_MISSING")
                continue

            print(f"  + stmt {stmt.id} ({stmt.file_name!r}): {start} .. {end}  [via {source}]")
            recovered += 1

            if not dry_run:
                stmt.period_start = start
                stmt.period_end = end

                # Propagate to line-level activity periods that were left NULL
                # by the upload pipeline. We don't overwrite existing per-line
                # periods because some statements legitimately have lines with
                # different reporting windows (e.g. catch-up adjustments).
                n = (
                    db.query(RoyaltyStatementLine)
                    .filter(
                        RoyaltyStatementLine.statement_id == stmt.id,
                        RoyaltyStatementLine.activity_period_start.is_(None),
                    )
                    .update(
                        {"activity_period_start": start, "activity_period_end": end},
                        synchronize_session=False,
                    )
                )
                line_updates += n

        if not dry_run:
            db.commit()

        print()
        print(f"Recovered period on {recovered} statement(s); skipped {skipped}.")
        print(f"Updated activity_period_start on {line_updates} statement line(s).")
        if dry_run:
            print("(dry-run — no changes committed)")

        return {
            "statements_scanned": len(statements),
            "statements_recovered": recovered,
            "statements_unrecoverable": skipped,
            "line_periods_updated": line_updates,
        }
    finally:
        db.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--org-id", type=int, default=None)
    args = ap.parse_args()
    stats = backfill(org_id=args.org_id, dry_run=args.dry_run)
    # Exit 0 unless we found statements but recovered nothing — that's the
    # signal ops watches for to know the run is worth investigating.
    scanned = stats["statements_scanned"]
    recovered = stats["statements_recovered"]
    sys.exit(0 if (scanned == 0 or recovered > 0 or stats["statements_unrecoverable"] == scanned) else 1)


if __name__ == "__main__":
    main()
