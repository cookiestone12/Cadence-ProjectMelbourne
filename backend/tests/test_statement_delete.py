"""Task #64 — Exhaustive statement delete.

Verifies that DELETE /api/royalties/statements/{org}/{id} cleans up
all derived state for a statement (advance balances, action items,
file on disk, payment ledger entries) and that the new
/delete-preview endpoint returns the same summary without mutating.
"""
import os
import tempfile
import pytest
from datetime import date, datetime
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.database import Base
from backend.models.models import (
    User, Organization, OrganizationMember,
    RoyaltyStatement, RoyaltyStatementLine, RoyaltyTransaction,
    RoyaltyLedgerEntry, RoyaltyProcessingRun,
    AdvanceV2, ActionItem, Payee,
)
from backend.utils.auth import get_current_user
from backend.models.database import get_db as original_get_db


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


def _override_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[original_get_db] = _override_db


@pytest.fixture(scope="function")
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    s = TestingSessionLocal()
    yield s
    s.close()


@pytest.fixture(scope="function")
def org_user(db: Session):
    user = User(username="u1", email="u1@x.com", hashed_password="x", is_active=True)
    db.add(user); db.commit(); db.refresh(user)
    org = Organization(name="O1", type="LABEL", account_type="ENTERPRISE", display_name="O1")
    db.add(org); db.commit(); db.refresh(org)
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="OWNER"))
    db.commit()
    app.dependency_overrides[get_current_user] = lambda: user
    yield org, user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture(scope="function")
def client():
    return TestClient(app)


def _make_statement(db, org_id, file_path=None, total_revenue_cents=10000):
    stmt = RoyaltyStatement(
        organization_id=org_id,
        source_name="Test Statement",
        source_type="DSP",
        period_start=date(2026, 1, 1),
        period_end=date(2026, 3, 31),
        currency="USD",
        file_name="test.csv",
        file_path=file_path,
        total_revenue_cents=total_revenue_cents,
        status="PROCESSED",
    )
    db.add(stmt); db.commit(); db.refresh(stmt)
    return stmt


def _make_payee(db, org_id):
    p = Payee(org_id=org_id, payee_type="COMPANY", company_name="Test Payee")
    db.add(p); db.commit(); db.refresh(p)
    return p


def _make_run(db, org_id, stmt_id):
    run = RoyaltyProcessingRun(org_id=org_id, statement_id=stmt_id, run_version=1, status="SUCCEEDED")
    db.add(run); db.commit(); db.refresh(run)
    return run


# ---------- T002.1: advance balance restored ----------

def test_delete_restores_advance_balance(db, org_user, client):
    org, user = org_user
    stmt = _make_statement(db, org.id)
    payee = _make_payee(db, org.id)
    run = _make_run(db, org.id, stmt.id)

    advance = AdvanceV2(
        org_id=org.id, payee_id=payee.id, advance_name="Q1 Advance",
        advance_date=date(2026, 1, 1), currency="USD",
        principal_amount_cents=100_000, recoupable=True,
        recoupment_pool="GLOBAL", outstanding_balance_cents=70_000,
    )
    db.add(advance); db.commit(); db.refresh(advance)

    # Two RECOUPMENT_APPLIED entries for this statement totalling 30_000
    db.add(RoyaltyLedgerEntry(
        org_id=org.id, statement_id=stmt.id, processing_run_id=run.id,
        payee_id=payee.id, entry_type="RECOUPMENT_APPLIED",
        amount_cents=-20_000, advance_id=advance.id, recoupment_pool="GLOBAL",
    ))
    db.add(RoyaltyLedgerEntry(
        org_id=org.id, statement_id=stmt.id, processing_run_id=run.id,
        payee_id=payee.id, entry_type="RECOUPMENT_APPLIED",
        amount_cents=-10_000, advance_id=advance.id, recoupment_pool="GLOBAL",
    ))
    db.commit()

    stmt_id = stmt.id
    advance_id = advance.id
    res = client.delete(f"/api/royalties/statements/{org.id}/{stmt_id}")
    assert res.status_code == 200, res.text

    db.expire_all()
    adv = db.query(AdvanceV2).filter(AdvanceV2.id == advance_id).first()
    assert adv.outstanding_balance_cents == 100_000, (
        f"expected 70_000 + 30_000 restored = 100_000, got {adv.outstanding_balance_cents}"
    )
    assert db.query(RoyaltyLedgerEntry).filter(RoyaltyLedgerEntry.statement_id == stmt_id).count() == 0


# ---------- T002.2: action items removed ----------

def test_delete_removes_statement_action_items(db, org_user, client):
    org, _ = org_user
    stmt = _make_statement(db, org.id)
    db.add(ActionItem(
        organization_id=org.id, entity_type="STATEMENT",
        action_type="STATEMENT_UNMATCHED", title=f"Statement #{stmt.id}: 5 unmatched",
        is_auto_generated=True,
    ))
    db.add(ActionItem(
        organization_id=org.id, entity_type="STATEMENT",
        action_type="STATEMENT_READY", title=f"Statement #{stmt.id} is ready",
        is_auto_generated=True,
    ))
    # Unrelated action item — must NOT be deleted.
    db.add(ActionItem(
        organization_id=org.id, entity_type="STATEMENT",
        action_type="STATEMENT_READY", title="Statement #999 is ready",
        is_auto_generated=True,
    ))
    db.commit()

    res = client.delete(f"/api/royalties/statements/{org.id}/{stmt.id}")
    assert res.status_code == 200

    remaining = db.query(ActionItem).filter(ActionItem.organization_id == org.id).all()
    assert len(remaining) == 1
    assert "999" in remaining[0].title


# ---------- T002.3: file on disk removed ----------

def test_delete_removes_uploaded_file(db, org_user, client):
    org, _ = org_user

    # Place a fake file under backend/uploads/ so the safety guard
    # accepts it. Use a unique filename to avoid collisions.
    project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    uploads = os.path.join(project_root, "backend", "uploads")
    os.makedirs(uploads, exist_ok=True)
    fp = os.path.join(uploads, f"test_stmt_{os.getpid()}.csv")
    with open(fp, "w") as f:
        f.write("dummy")
    assert os.path.exists(fp)

    stmt = _make_statement(db, org.id, file_path=fp)
    res = client.delete(f"/api/royalties/statements/{org.id}/{stmt.id}")
    assert res.status_code == 200, res.text
    assert not os.path.exists(fp), "uploaded file should have been removed"


def test_delete_does_not_remove_file_outside_uploads(db, org_user, client):
    """Path-traversal guard: a file outside backend/uploads/ must not
    be removed even if file_path points there."""
    org, _ = org_user
    with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tf:
        tf.write(b"dummy")
        outside_path = tf.name
    try:
        stmt = _make_statement(db, org.id, file_path=outside_path)
        res = client.delete(f"/api/royalties/statements/{org.id}/{stmt.id}")
        assert res.status_code == 200
        assert os.path.exists(outside_path), "file outside uploads dir must not be removed"
    finally:
        if os.path.exists(outside_path):
            os.remove(outside_path)


# ---------- T002.4: payment ledger entries unwound + audited ----------

def test_delete_unwinds_payment_ledger_entries(db, org_user, client):
    org, _ = org_user
    stmt = _make_statement(db, org.id)
    payee = _make_payee(db, org.id)
    run = _make_run(db, org.id, stmt.id)

    db.add(RoyaltyLedgerEntry(
        org_id=org.id, statement_id=stmt.id, processing_run_id=run.id,
        payee_id=payee.id, entry_type="PAYMENT", amount_cents=-50_000,
        memo="Payment via batch X",
    ))
    db.commit()

    res = client.delete(f"/api/royalties/statements/{org.id}/{stmt.id}")
    assert res.status_code == 200, res.text

    body = res.json()
    assert body["summary"]["payments_unwound"], "summary should report unwound payments"
    assert body["summary"]["payments_unwound"][0]["amount_cents"] == -50_000
    assert db.query(RoyaltyLedgerEntry).filter(RoyaltyLedgerEntry.statement_id == stmt.id).count() == 0

    # Audit log entry written for the unwind
    from backend.models.models import AuditLog
    unwind_logs = db.query(AuditLog).filter(
        AuditLog.organization_id == org.id,
        AuditLog.action == "PAYOUT_UNWOUND_BY_STATEMENT_DELETE",
    ).all()
    assert len(unwind_logs) == 1


# ---------- T002.5: preview is non-mutating + matches delete ----------

def test_delete_preview_is_non_mutating_and_matches_summary(db, org_user, client):
    org, _ = org_user
    stmt = _make_statement(db, org.id)
    payee = _make_payee(db, org.id)
    run = _make_run(db, org.id, stmt.id)

    advance = AdvanceV2(
        org_id=org.id, payee_id=payee.id, advance_name="A1",
        advance_date=date(2026, 1, 1), currency="USD",
        principal_amount_cents=50_000, recoupable=True,
        recoupment_pool="GLOBAL", outstanding_balance_cents=40_000,
    )
    db.add(advance); db.commit(); db.refresh(advance)

    db.add(RoyaltyLedgerEntry(
        org_id=org.id, statement_id=stmt.id, processing_run_id=run.id,
        payee_id=payee.id, entry_type="RECOUPMENT_APPLIED",
        amount_cents=-10_000, advance_id=advance.id, recoupment_pool="GLOBAL",
    ))
    db.add(ActionItem(
        organization_id=org.id, entity_type="STATEMENT",
        action_type="STATEMENT_READY", title=f"Statement #{stmt.id} is ready",
        is_auto_generated=True,
    ))
    db.commit()

    preview = client.get(f"/api/royalties/statements/{org.id}/{stmt.id}/delete-preview")
    assert preview.status_code == 200, preview.text
    p = preview.json()
    assert p["statement_id"] == stmt.id
    assert p["ledger_entry_count"] == 1
    assert p["action_items_to_remove"] == 1
    assert len(p["advance_restores"]) == 1
    assert p["advance_restores"][0]["restore_cents"] == 10_000

    # Preview must not mutate
    db.expire_all()
    assert db.query(RoyaltyStatement).filter(RoyaltyStatement.id == stmt.id).first() is not None
    assert db.query(AdvanceV2).filter(AdvanceV2.id == advance.id).first().outstanding_balance_cents == 40_000
    assert db.query(ActionItem).filter(ActionItem.organization_id == org.id).count() == 1

    # Now delete and confirm the summary in the response matches preview
    delete_res = client.delete(f"/api/royalties/statements/{org.id}/{stmt.id}")
    assert delete_res.status_code == 200
    s = delete_res.json()["summary"]
    assert s["ledger_entry_count"] == p["ledger_entry_count"]
    assert s["action_items_to_remove"] == p["action_items_to_remove"]
    assert s["advance_restores"][0]["restore_cents"] == p["advance_restores"][0]["restore_cents"]
