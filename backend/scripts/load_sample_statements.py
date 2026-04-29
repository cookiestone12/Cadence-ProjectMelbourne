"""CLI: load the sample royalty-statement fixtures into a target org.

Usage:
    python -m backend.scripts.load_sample_statements \
        --org-id 1 --user-id 1

Loads ``mock_data/statements/{bmi_q4_2024,mlc_2024_10,ascap_q4_2024}.csv``
through the same parser orchestrator the HTTP upload route uses, then
runs auto-match so the seeded statements show up on the Royalties
page exactly as a real upload would.

Idempotent on file_name + organization_id (skips a fixture if a
statement with that file name already exists for the org).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session


SAMPLE_FIXTURES = [
    {
        "file_name": "bmi_q4_2024.csv",
        "source_name": "BMI Q4 2024 (Sample)",
        "source_type": "BMI",
        "period_start": date(2024, 10, 1),
        "period_end": date(2024, 12, 31),
        "currency": "USD",
    },
    {
        "file_name": "mlc_2024_10.csv",
        "source_name": "MLC October 2024 (Sample)",
        "source_type": "MLC",
        "period_start": date(2024, 10, 1),
        "period_end": date(2024, 10, 31),
        "currency": "USD",
    },
    {
        "file_name": "ascap_q4_2024.csv",
        "source_name": "ASCAP Q4 2024 (Sample)",
        "source_type": "ASCAP",
        "period_start": date(2024, 10, 1),
        "period_end": date(2024, 12, 31),
        "currency": "USD",
    },
]


def _fixtures_dir() -> str:
    here = os.path.dirname(__file__)
    return os.path.normpath(os.path.join(here, "..", "..", "mock_data", "statements"))


def load_sample_statements_for_org(
    db: Session,
    org_id: int,
    user_id: int,
    *,
    fixtures_dir: Optional[str] = None,
    auto_match: bool = True,
) -> list:
    """Load every sample fixture into ``org_id`` as the user
    ``user_id``. Returns a list of ``{fixture, statement_id, status,
    line_count}`` dicts. Skips fixtures that already exist for the org.
    """
    from ..models.models import RoyaltyStatement
    from ..services.statement_parser import parse_statement_file
    from ..services.royalty_processing_engine import (
        parse_statement_to_lines,
        auto_match_lines,
    )

    fdir = fixtures_dir or _fixtures_dir()
    results = []

    for fixture in SAMPLE_FIXTURES:
        path = os.path.join(fdir, fixture["file_name"])
        if not os.path.exists(path):
            results.append({"fixture": fixture["file_name"], "skipped": "missing_file"})
            continue

        existing = db.query(RoyaltyStatement).filter(
            RoyaltyStatement.organization_id == org_id,
            RoyaltyStatement.file_name == fixture["file_name"],
        ).first()
        if existing is not None:
            results.append({
                "fixture": fixture["file_name"],
                "skipped": "already_loaded",
                "statement_id": existing.id,
            })
            continue

        with open(path, "rb") as f:
            content = f.read()

        parsed = parse_statement_file(
            content,
            fixture["file_name"],
            source_name=fixture["source_name"],
            source_type=fixture["source_type"],
            org_id=org_id,
        )

        statement = RoyaltyStatement(
            organization_id=org_id,
            source_name=fixture["source_name"],
            source_type=parsed.resolved_source_type or fixture["source_type"],
            period_start=fixture["period_start"],
            period_end=fixture["period_end"],
            currency=fixture["currency"],
            file_name=fixture["file_name"],
            status="PROCESSING",
            column_mapping=parsed.suggested_mapping,
            uploaded_by_user_id=user_id,
        )
        db.add(statement)
        db.flush()

        line_count = parse_statement_to_lines(
            db,
            statement.id,
            org_id,
            parsed.suggested_mapping,
            parsed.rows,
            pdf_metadata=parsed.pdf_metadata,
        )
        statement.status = "UPLOADED"
        db.flush()

        match_stats = {}
        if auto_match:
            match_stats = auto_match_lines(db, statement.id, org_id)
            matched = match_stats.get("auto_matched", 0)
            review = match_stats.get("review_required", 0)
            unmatched = match_stats.get("unmatched", 0)
            if unmatched == 0 and review == 0:
                statement.status = "FULLY_MATCHED"
            elif unmatched == 0:
                statement.status = "REVIEW_REQUIRED"
            else:
                statement.status = "PARTIALLY_MATCHED"
            statement.matched_transactions = matched + review
            statement.unmatched_transactions = unmatched

        db.commit()
        db.refresh(statement)

        results.append({
            "fixture": fixture["file_name"],
            "statement_id": statement.id,
            "status": statement.status,
            "line_count": line_count,
            "match_stats": match_stats,
        })

    return results


def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Load sample royalty-statement fixtures into a target org."
    )
    parser.add_argument("--org-id", type=int, required=True)
    parser.add_argument("--user-id", type=int, required=True)
    parser.add_argument("--no-auto-match", action="store_true")
    args = parser.parse_args(argv)

    from ..models import get_db

    db = next(get_db())
    try:
        results = load_sample_statements_for_org(
            db, args.org_id, args.user_id, auto_match=not args.no_auto_match
        )
        for r in results:
            print(r)
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
