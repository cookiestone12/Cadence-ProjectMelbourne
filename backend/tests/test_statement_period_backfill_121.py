"""Task #121 — Backfill legacy statements' missing periods so the underwriting
engine sees distinct historical buckets.

Covers:
  * `parse_period_from_filename` recognizes the patterns ops staff actually
    use ("BMI 2023 Jul-Dec", "ASCAP 2024 H1", "Vanguard Q3 2024", bare years).
  * The backfill script repairs `period_start` / `period_end` and propagates
    the period down to `RoyaltyStatementLine.activity_period_start` rows that
    were left NULL by the upload pipeline.
  * After backfill, the underwriting engine groups three statements covering
    three different half-year periods into three distinct period buckets
    (the bug: when periods were NULL they all collapsed to `date.today()`,
    which made decay analytics refuse to fit a curve).
"""
from datetime import date

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models.database import Base
from backend.models.models import (
    User, Organization, OrganizationMember, Song,
    RoyaltyStatement, RoyaltyStatementLine,
)
from backend.utils.pdf_statement_parser import parse_period_from_filename
from backend.scripts.backfill_statement_periods_121 import backfill
from backend.services.underwriting_engine import run_underwriting


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _record):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="function")
def db(monkeypatch):
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    # Point the backfill script's SessionLocal at the in-memory test DB so
    # `backfill()` operates on the same session as the test setup.
    import backend.scripts.backfill_statement_periods_121 as mod
    monkeypatch.setattr(mod, "SessionLocal", TestingSessionLocal)
    s = TestingSessionLocal()
    try:
        yield s
    finally:
        s.close()


# ---------------------------------------------------------------------------
# Filename heuristic
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("file_name,expected", [
    ("BMI 2023 Jul-Dec.pdf",         (date(2023, 7, 1), date(2023, 12, 31))),
    ("BMI Jan-Jun 2024.pdf",         (date(2024, 1, 1), date(2024, 6, 30))),
    ("ASCAP 2024 H1.pdf",            (date(2024, 1, 1), date(2024, 6, 30))),
    ("ASCAP 2H 2023.pdf",            (date(2023, 7, 1), date(2023, 12, 31))),
    ("Vanguard Q3 2024.pdf",         (date(2024, 7, 1), date(2024, 9, 30))),
    ("Marri 2026.pdf",               (date(2026, 1, 1), date(2026, 12, 31))),
    ("BMI_2023_Jul_Dec.pdf",         (date(2023, 7, 1), date(2023, 12, 31))),
])
def test_parse_period_from_filename_recognized(file_name, expected):
    assert parse_period_from_filename(file_name) == expected


@pytest.mark.parametrize("file_name", [
    None,
    "",
    "random_statement.pdf",
    "BMI 2023 vs 2024 reconciliation.pdf",   # ambiguous (two years), no range
])
def test_parse_period_from_filename_unrecognized(file_name):
    assert parse_period_from_filename(file_name) == (None, None)


# ---------------------------------------------------------------------------
# Backfill end-to-end + underwriting bucketing
# ---------------------------------------------------------------------------

def _seed_org(db):
    org = Organization(name="O", type="LABEL", account_type="ENTERPRISE", display_name="O")
    db.add(org); db.commit(); db.refresh(org)
    user = User(username="u", email="u@x.com", hashed_password="x", is_active=True)
    db.add(user); db.commit(); db.refresh(user)
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="OWNER"))
    db.commit()
    return org, user


def _seed_legacy_statement(db, org_id, song_id, file_name, amount):
    """Statement with NULL period_start (the bug) and a line with NULL
    activity_period_start (also NULL on legacy data)."""
    stmt = RoyaltyStatement(
        organization_id=org_id,
        source_name="BMI",
        source_type="publisher",
        period_start=None,
        period_end=None,
        currency="USD",
        file_name=file_name,
        total_revenue_cents=int(amount * 100),
        status="PROCESSED",
    )
    db.add(stmt); db.commit(); db.refresh(stmt)
    line = RoyaltyStatementLine(
        org_id=org_id, statement_id=stmt.id, matched_song_id=song_id,
        net_amount=amount, gross_amount=amount, match_status="MATCHED",
        activity_period_start=None, activity_period_end=None,
        canonical_right_category="streaming",
    )
    db.add(line); db.commit()
    return stmt


def test_backfill_recovers_three_distinct_period_buckets(db):
    org, user = _seed_org(db)
    song = Song(organization_id=org.id, title="Hit Song", primary_artist="X")
    db.add(song); db.commit(); db.refresh(song)

    # Three legacy statements covering three different half-year windows —
    # this is exactly the configuration the underwriting engine needs to
    # see in order to fit a decay curve.
    s1 = _seed_legacy_statement(db, org.id, song.id, "BMI 2023 Jan-Jun.pdf", 1000.0)
    s2 = _seed_legacy_statement(db, org.id, song.id, "BMI 2023 Jul-Dec.pdf", 800.0)
    s3 = _seed_legacy_statement(db, org.id, song.id, "BMI Jan-Jun 2024.pdf", 600.0)

    # Pre-condition: every statement has NULL period_start, so the
    # underwriting engine would collapse them all into the same `date.today()`
    # bucket and decay analytics would refuse to fit a curve.
    assert all(s.period_start is None for s in (s1, s2, s3))

    stats = backfill(org_id=org.id, dry_run=False)
    assert stats["statements_scanned"] == 3
    assert stats["statements_recovered"] == 3
    assert stats["statements_unrecoverable"] == 0

    db.expire_all()
    s1, s2, s3 = (db.query(RoyaltyStatement).get(sid) for sid in (s1.id, s2.id, s3.id))
    assert (s1.period_start, s1.period_end) == (date(2023, 1, 1), date(2023, 6, 30))
    assert (s2.period_start, s2.period_end) == (date(2023, 7, 1), date(2023, 12, 31))
    assert (s3.period_start, s3.period_end) == (date(2024, 1, 1), date(2024, 6, 30))

    # Lines should have inherited the period (they were NULL on legacy data).
    lines = db.query(RoyaltyStatementLine).filter(
        RoyaltyStatementLine.org_id == org.id
    ).all()
    assert len(lines) == 3
    assert all(l.activity_period_start is not None for l in lines)
    distinct_line_periods = {(l.activity_period_start, l.activity_period_end) for l in lines}
    assert len(distinct_line_periods) == 3, (
        "Backfill must propagate per-statement period to each line so the "
        "underwriting engine groups them into separate buckets."
    )

    # Underwriting engine: the spine groups (song, period) pairs. With three
    # real periods restored, the song must occupy three distinct spine rows —
    # the acceptance criterion for #121. Pre-fix, all three lines collapsed
    # into a single `date.today()` bucket and decay analytics refused to fit.
    out = run_underwriting(db, org.id, user_id=user.id)
    from backend.models.models import UnderwritingRun
    run = db.query(UnderwritingRun).get(out["run_id"])
    entries = (run.spine_data or {}).get("entries") or []
    song_periods = {e["period"] for e in entries if e.get("song_id") == song.id}
    assert len(song_periods) == 3, (
        f"Expected 3 distinct period buckets after backfill, got {song_periods}. "
        f"Spine entries: {entries}"
    )
