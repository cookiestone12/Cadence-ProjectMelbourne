"""Task #98 — tests for the one-shot duplicate-statement cleanup script.

Covers:
  * Dry-run does not delete anything.
  * Apply deletes the duplicate (#17, #11) and preserves the original
    (#18, #15) plus an unrelated control statement.
  * Idempotent re-run (apply twice) reports SKIPPED and changes nothing.
  * Mismatched org or mismatched total = REFUSE TO DELETE.
  * Audit log entry is written for each successful delete.
"""
import pytest
from datetime import date
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.models.database import Base
from backend.models.models import (
    User, Organization, OrganizationMember,
    RoyaltyStatement, RoyaltyStatementLine, AuditLog,
)
from backend.scripts.cleanup_duplicate_statements_98 import (
    DuplicateTarget, cleanup_duplicates,
)


SQLALCHEMY_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db():
    engine = create_engine(
        SQLALCHEMY_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _fk_on(conn, _):
        c = conn.cursor(); c.execute("PRAGMA foreign_keys=ON"); c.close()

    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
        engine.dispose()


@pytest.fixture
def admin_user(db: Session):
    u = User(
        username="master",
        email="master@cadence.test",
        hashed_password="x",
        is_active=True,
        is_super_admin=True,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _seed_world(db: Session) -> dict:
    """Mirror the prod situation: org A has duplicate pair (17, 18) for
    $18,622.98 and duplicate pair (11, 15) for $48.30. Org A also has
    a NON-duplicate control statement #99 that must survive cleanup.
    """
    org = Organization(name="Cadence Test Org", type="LABEL", account_type="ENTERPRISE", display_name="Test")
    db.add(org); db.commit(); db.refresh(org)

    def _stmt(stmt_id: int, total: int, file_name: str) -> RoyaltyStatement:
        s = RoyaltyStatement(
            id=stmt_id,
            organization_id=org.id,
            source_name="BMI",
            source_type="BMI",
            period_start=date(2024, 1, 1),
            period_end=date(2024, 6, 30),
            currency="USD",
            file_name=file_name,
            total_revenue_cents=total,
            status="PROCESSED",
        )
        db.add(s)
        return s

    s17 = _stmt(17, 1_862_298, "BMI_2024_H1.pdf")
    s18 = _stmt(18, 1_862_298, "BMI_2024_H1.pdf")
    s11 = _stmt(11, 4_830, "Marri_BMI_2026.pdf")
    s15 = _stmt(15, 4_830, "Marri_BMI_2026.pdf")
    s99 = _stmt(99, 5_000_00, "Unrelated_2025.pdf")
    db.commit()

    # add a child line to each duplicate to prove the cascade works
    for sid, amt in [(17, 1_862_298), (11, 4_830)]:
        db.add(RoyaltyStatementLine(
            statement_id=sid,
            org_id=org.id,
            track_title_raw="X", artist_name_raw="Y",
            net_amount=amt / 100.0,
        ))
    db.commit()

    return {"org": org, "s17": s17, "s18": s18, "s11": s11, "s15": s15, "s99": s99}


TARGETS = [
    DuplicateTarget(17, 18, 1_862_298, "BMI 2024 H1"),
    DuplicateTarget(11, 15, 4_830,     "Marri BMI 2026"),
]


def _ids_present(db: Session) -> set[int]:
    return {r[0] for r in db.query(RoyaltyStatement.id).all()}


def test_dry_run_deletes_nothing(db, admin_user):
    world = _seed_world(db)
    before = _ids_present(db)

    results = cleanup_duplicates(db, admin_user, apply=False, targets=TARGETS)

    assert all(r.status == "DRY_RUN" for r in results)
    assert _ids_present(db) == before
    # no audit rows written
    assert db.query(AuditLog).count() == 0


def test_apply_deletes_duplicates_and_preserves_originals(db, admin_user):
    world = _seed_world(db)

    results = cleanup_duplicates(db, admin_user, apply=True, targets=TARGETS)
    db.commit()

    assert [r.status for r in results] == ["DELETED", "DELETED"]
    # duplicates gone, originals + control kept
    remaining = _ids_present(db)
    assert 17 not in remaining
    assert 11 not in remaining
    assert 18 in remaining
    assert 15 in remaining
    assert 99 in remaining

    # cascade: child lines for 17 and 11 are also gone
    line_stmt_ids = {r[0] for r in db.query(RoyaltyStatementLine.statement_id).all()}
    assert 17 not in line_stmt_ids
    assert 11 not in line_stmt_ids

    # audit log captured both deletes
    audit = db.query(AuditLog).filter(AuditLog.action == "DELETE", AuditLog.entity_type == "STATEMENT").all()
    audit_ids = {a.entity_id for a in audit}
    assert audit_ids == {17, 11}


def test_apply_is_idempotent(db, admin_user):
    _seed_world(db)
    cleanup_duplicates(db, admin_user, apply=True, targets=TARGETS)
    db.commit()

    # Second run finds nothing to do.
    results2 = cleanup_duplicates(db, admin_user, apply=True, targets=TARGETS)
    db.commit()

    assert all(r.status == "SKIPPED" for r in results2)
    assert all("already deleted" in r.message for r in results2)


def test_refuses_when_total_does_not_match(db, admin_user):
    world = _seed_world(db)
    # Tamper with the duplicate's total — operator should be forced to investigate
    world["s17"].total_revenue_cents = 9_999_999
    db.commit()

    results = cleanup_duplicates(db, admin_user, apply=True, targets=TARGETS)
    db.commit()

    by_id = {r.target.duplicate_id: r for r in results}
    assert by_id[17].status == "SKIPPED"
    assert "REFUSING TO DELETE" in by_id[17].message
    # #17 still present, #11 still got cleaned up
    assert 17 in _ids_present(db)
    assert 11 not in _ids_present(db)


def test_refuses_when_orgs_differ(db, admin_user):
    world = _seed_world(db)
    other_org = Organization(name="Other", type="LABEL", account_type="ENTERPRISE", display_name="Other")
    db.add(other_org); db.commit(); db.refresh(other_org)
    world["s17"].organization_id = other_org.id
    db.commit()

    results = cleanup_duplicates(db, admin_user, apply=True, targets=TARGETS)
    db.commit()

    by_id = {r.target.duplicate_id: r for r in results}
    assert by_id[17].status == "SKIPPED"
    assert "REFUSING TO DELETE" in by_id[17].message
    assert 17 in _ids_present(db)


def test_refuses_when_original_total_does_not_match(db, admin_user):
    world = _seed_world(db)
    # Original has the wrong amount → if these were truly duplicates
    # the original should also be $18,622.98. Operator must investigate.
    world["s18"].total_revenue_cents = 1
    db.commit()

    results = cleanup_duplicates(db, admin_user, apply=True, targets=TARGETS)
    db.commit()

    by_id = {r.target.duplicate_id: r for r in results}
    assert by_id[17].status == "SKIPPED"
    assert "original #18 total is" in by_id[17].message
    assert 17 in _ids_present(db)


def test_savepoint_isolates_failures_so_earlier_deletes_persist(db, admin_user, monkeypatch):
    """Per-target SAVEPOINT means a crash on target B must NOT undo
    target A's already-committed delete. Reported result is honest
    (DELETED for A, ERROR for B)."""
    _seed_world(db)
    from backend.routes import royalties as routes_royalties

    real = routes_royalties._perform_statement_delete
    call_count = {"n": 0}

    def flaky(db_, stmt, org_id, user):
        call_count["n"] += 1
        if call_count["n"] == 2:  # second target (#11) blows up
            raise RuntimeError("simulated crash mid-delete")
        return real(db_, stmt, org_id, user)

    monkeypatch.setattr(routes_royalties, "_perform_statement_delete", flaky)

    results = cleanup_duplicates(db, admin_user, apply=True, targets=TARGETS)
    db.commit()

    by_id = {r.target.duplicate_id: r for r in results}
    assert by_id[17].status == "DELETED"
    assert by_id[11].status == "ERROR"
    assert "simulated crash" in by_id[11].message
    # #17 truly gone (savepoint committed); #11 truly still present
    remaining = _ids_present(db)
    assert 17 not in remaining
    assert 11 in remaining


def test_refuses_when_original_missing(db, admin_user):
    world = _seed_world(db)
    db.delete(world["s18"]); db.commit()

    results = cleanup_duplicates(db, admin_user, apply=True, targets=TARGETS)
    db.commit()

    by_id = {r.target.duplicate_id: r for r in results}
    assert by_id[17].status == "SKIPPED"
    assert "original statement #18 not found" in by_id[17].message
    assert 17 in _ids_present(db)
