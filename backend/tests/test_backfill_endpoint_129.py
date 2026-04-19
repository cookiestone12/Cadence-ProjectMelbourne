"""Task #129 — Regression guard for the prod-facing statement-period backfill.

Production has no shell, so the Task #121 statement-period backfill has to
be reachable over HTTP for ops to actually run it (#126 is blocked on this).
This test pins three guarantees:

  * The route exists at the expected path and method.
  * Auth is enforced — non-super-admin callers can't trigger writes.
  * Dry-run mode reports counts without committing, and a real run actually
    sets `period_start` / `period_end` on a previously-NULL statement.

If any of these break, ops loses the only safe way to repair legacy
statements' periods in production.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.database import Base, get_db
from backend.models.models import (
    User, Organization, OrganizationMember, Song,
    RoyaltyStatement, RoyaltyStatementLine,
)
from backend.utils.auth import get_current_user, get_password_hash


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


@pytest.fixture(scope="function")
def env():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    def _override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db

    # Repoint the script's own SessionLocal at the test DB so the
    # endpoint's in-process call hits the same in-memory schema.
    import backend.scripts.backfill_statement_periods_121 as backfill_mod
    _orig_session_local = backfill_mod.SessionLocal
    backfill_mod.SessionLocal = TestingSessionLocal

    try:
        yield db, TestClient(app)
    finally:
        backfill_mod.SessionLocal = _orig_session_local
        app.dependency_overrides.clear()
        db.close()


def _seed_org_with_legacy_statement(db):
    org = Organization(name="O", type="LABEL", account_type="ENTERPRISE", display_name="O")
    db.add(org); db.commit(); db.refresh(org)

    super_admin = User(
        username="root", email="r@x.com", hashed_password=get_password_hash("x"),
        is_active=True, is_super_admin=True,
    )
    member_user = User(
        username="m", email="m@x.com", hashed_password=get_password_hash("x"),
        is_active=True,
    )
    db.add_all([super_admin, member_user]); db.commit()
    db.refresh(super_admin); db.refresh(member_user)

    db.add(OrganizationMember(organization_id=org.id, user_id=member_user.id, role="OWNER"))
    db.commit()

    song = Song(organization_id=org.id, title="Legacy Song", primary_artist="X")
    db.add(song); db.commit(); db.refresh(song)

    # Legacy statement: NULL period_start / period_end, filename parseable
    # by the heuristic so the backfill can recover the period.
    stmt = RoyaltyStatement(
        organization_id=org.id,
        source_name="BMI",
        source_type="publisher",
        period_start=None,
        period_end=None,
        currency="USD",
        file_name="BMI 2023 Jul-Dec.pdf",
        total_revenue_cents=100000,
        status="PROCESSED",
    )
    db.add(stmt); db.commit(); db.refresh(stmt)
    line = RoyaltyStatementLine(
        org_id=org.id, statement_id=stmt.id, matched_song_id=song.id,
        net_amount=1000.0, gross_amount=1000.0, match_status="MATCHED",
        activity_period_start=None, activity_period_end=None,
        canonical_right_category="streaming",
    )
    db.add(line); db.commit()
    return org, super_admin, member_user, stmt


def test_endpoint_requires_super_admin(env):
    db, c = env
    _, _, member_user, _ = _seed_org_with_legacy_statement(db)
    # A regular org-member user must not be able to trigger the backfill.
    app.dependency_overrides[get_current_user] = lambda: member_user
    r = c.post("/api/internal/backfill/statement-periods?dry_run=true")
    # get_current_super_admin raises 403 for non-super-admin callers.
    assert r.status_code in (401, 403), r.text


def test_dry_run_reports_counts_without_committing(env):
    db, c = env
    org, super_admin, _, stmt = _seed_org_with_legacy_statement(db)
    app.dependency_overrides[get_current_user] = lambda: super_admin

    r = c.post(f"/api/internal/backfill/statement-periods?dry_run=true&org_id={org.id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dry_run"] is True
    assert body["statements_scanned"] == 1
    assert body["statements_recovered"] == 1
    assert body["statements_unrecoverable"] == 0

    # Critical: dry run must NOT have written period_start/period_end.
    db.expire_all()
    refreshed = db.query(RoyaltyStatement).get(stmt.id)
    assert refreshed.period_start is None
    assert refreshed.period_end is None


def test_real_run_sets_periods_on_statement(env):
    from datetime import date
    db, c = env
    org, super_admin, _, stmt = _seed_org_with_legacy_statement(db)
    app.dependency_overrides[get_current_user] = lambda: super_admin

    r = c.post(f"/api/internal/backfill/statement-periods?dry_run=false&org_id={org.id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dry_run"] is False
    assert body["statements_recovered"] == 1
    assert body["statements_unrecoverable"] == 0
    # The lines on the seeded statement had NULL activity_period_start, so
    # the backfill must have propagated the recovered period to them.
    assert body["line_periods_updated"] >= 1

    db.expire_all()
    refreshed = db.query(RoyaltyStatement).get(stmt.id)
    assert refreshed.period_start == date(2023, 7, 1)
    assert refreshed.period_end == date(2023, 12, 31)
