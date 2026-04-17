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
    AdvanceV2, ActionItem, Payee, PayoutBatch, PayoutItem,
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


# ---------- T002.6: PayoutItem.paid_at unwound + audited per payout ----------

def test_delete_unwinds_payout_item_paid_at(db, org_user, client):
    """When a PAYMENT ledger entry is deleted, the matching PayoutItem
    (matched by payee + amount + paid_at within ±5min of ledger
    created_at) must have paid_at cleared and an audit entry written
    for the payout id specifically (not just the ledger entry)."""
    org, _ = org_user
    stmt = _make_statement(db, org.id)
    payee = _make_payee(db, org.id)
    run = _make_run(db, org.id, stmt.id)

    batch = PayoutBatch(org_id=org.id, name="Q1 batch", currency="USD", status="PAID")
    db.add(batch); db.commit(); db.refresh(batch)
    paid_at = datetime(2026, 2, 1, 12, 0, 0)
    payout = PayoutItem(
        org_id=org.id, batch_id=batch.id, payee_id=payee.id,
        amount_cents=50_000, paid_at=paid_at,
    )
    db.add(payout); db.commit(); db.refresh(payout)
    stmt_id_local = stmt.id  # capture before delete (statement row will be removed)

    # PAYMENT ledger entry created at the same instant as the payout
    # (mirroring record_payment_ledger which stamps both in the same tx)
    # Ledger entry uses the deterministic FK column (the modern path).
    ledger = RoyaltyLedgerEntry(
        org_id=org.id, statement_id=stmt.id, processing_run_id=run.id,
        payee_id=payee.id, entry_type="PAYMENT", amount_cents=-50_000,
        memo=f"Payment via payout batch '{batch.name}'",
        payout_item_id=payout.id,
        created_at=paid_at,
    )
    db.add(ledger); db.commit()

    res = client.delete(f"/api/royalties/statements/{org.id}/{stmt.id}")
    assert res.status_code == 200, res.text

    db.expire_all()
    po = db.query(PayoutItem).filter(PayoutItem.id == payout.id).first()
    assert po is not None, "PayoutItem itself must NOT be deleted"
    assert po.paid_at is None, "paid_at must be cleared so the payout flows back to unpaid"

    from backend.models.models import AuditLog
    per_payout_logs = db.query(AuditLog).filter(
        AuditLog.organization_id == org.id,
        AuditLog.action == "PAYOUT_UNWOUND_BY_STATEMENT_DELETE",
        AuditLog.entity_type == "PAYOUT_ITEM",
        AuditLog.entity_id == po.id,
    ).all()
    assert len(per_payout_logs) == 1, "must audit-log per affected payout id"
    details = per_payout_logs[0].details or {}
    assert details.get("payout_item_id") == po.id
    assert details.get("amount_cents") == -50_000
    assert details.get("statement_id") == stmt_id_local
    assert details.get("linkage") == "fk"


# ---------- T066: notify users when statement delete unwinds paid payouts ----------

def test_delete_notifies_payout_creator_and_admins(db, org_user, client, monkeypatch):
    """When PAYMENT ledger entries are unwound, the user who created
    the payout batch and all org OWNERs/ADMINs (excluding the deleter)
    must receive an in-app notification linking to the payouts page."""
    org, deleter = org_user

    # A second admin user (should be notified) and a separate user
    # who created the payout batch (should also be notified).
    admin2 = User(username="admin2", email="admin2@x.com", hashed_password="x", is_active=True)
    batch_creator = User(username="batchcreator", email="bc@x.com", hashed_password="x", is_active=True)
    bystander = User(username="bystander", email="bs@x.com", hashed_password="x", is_active=True)
    db.add_all([admin2, batch_creator, bystander])
    db.commit()
    db.refresh(admin2); db.refresh(batch_creator); db.refresh(bystander)

    db.add(OrganizationMember(organization_id=org.id, user_id=admin2.id, role="ADMIN"))
    db.add(OrganizationMember(organization_id=org.id, user_id=batch_creator.id, role="MEMBER"))
    db.add(OrganizationMember(organization_id=org.id, user_id=bystander.id, role="MEMBER"))
    db.commit()

    stmt = _make_statement(db, org.id)
    payee = _make_payee(db, org.id)
    run = _make_run(db, org.id, stmt.id)

    batch = PayoutBatch(
        org_id=org.id, name="Q1 batch", currency="USD", status="PAID",
        created_by_user_id=batch_creator.id,
    )
    db.add(batch); db.commit(); db.refresh(batch)
    paid_at = datetime(2026, 2, 1, 12, 0, 0)
    payout = PayoutItem(
        org_id=org.id, batch_id=batch.id, payee_id=payee.id,
        amount_cents=50_000, paid_at=paid_at,
    )
    db.add(payout); db.commit(); db.refresh(payout)

    db.add(RoyaltyLedgerEntry(
        org_id=org.id, statement_id=stmt.id, processing_run_id=run.id,
        payee_id=payee.id, entry_type="PAYMENT", amount_cents=-50_000,
        memo="Payment via batch", payout_item_id=payout.id, created_at=paid_at,
    ))
    db.commit()

    res = client.delete(f"/api/royalties/statements/{org.id}/{stmt.id}")
    assert res.status_code == 200, res.text

    from backend.models.models import Notification
    notes = db.query(Notification).filter(
        Notification.notification_type == "PAYOUT_UNWOUND_BY_STATEMENT_DELETE",
    ).all()
    notified_uids = {n.user_id for n in notes}

    # Deleter (also OWNER) must NOT be notified.
    assert deleter.id not in notified_uids
    # Bystander (MEMBER, didn't create batch) must NOT be notified.
    assert bystander.id not in notified_uids
    # Batch creator and the other ADMIN must be notified.
    assert batch_creator.id in notified_uids
    assert admin2.id in notified_uids

    sample = notes[0]
    assert stmt.source_name in sample.message
    assert deleter.username in sample.message
    assert sample.link and "payouts" in sample.link
    assert sample.organization_id == org.id
    assert sample.extra_data.get("statement_id") == stmt.id
    assert payout.id in (sample.extra_data.get("payout_item_ids") or [])


def test_delete_no_notifications_when_no_payments_unwound(db, org_user, client):
    """If a statement has no PAYMENT ledger entries, deleting it
    should not produce PAYOUT_UNWOUND notifications."""
    org, _ = org_user
    stmt = _make_statement(db, org.id)
    res = client.delete(f"/api/royalties/statements/{org.id}/{stmt.id}")
    assert res.status_code == 200

    from backend.models.models import Notification
    notes = db.query(Notification).filter(
        Notification.notification_type == "PAYOUT_UNWOUND_BY_STATEMENT_DELETE",
    ).count()
    assert notes == 0


# ---------- T002.7: anchored ActionItem title match (no #1 → #10 leak) ----------

def test_action_item_delete_does_not_leak_to_neighboring_ids(db, org_user, client):
    """Deleting Statement #1 must NOT also delete action items that
    point at Statement #10 / #100 (i.e. title.contains('#1') used to
    over-match — we now use anchored LIKE patterns)."""
    org, _ = org_user
    stmt1 = _make_statement(db, org.id)
    stmt_other = RoyaltyStatement(
        organization_id=org.id, source_name="Other", source_type="DSP",
        period_start=date(2026, 1, 1), period_end=date(2026, 3, 31),
        currency="USD", status="PROCESSED",
    )
    db.add(stmt_other); db.commit(); db.refresh(stmt_other)

    # Sibling action items with overlapping numeric prefixes
    db.add(ActionItem(
        organization_id=org.id, entity_type="STATEMENT",
        action_type="STATEMENT_READY",
        title=f"Statement #{stmt1.id}: ready to process",
        is_auto_generated=True,
    ))
    sibling_title = f"Statement #{stmt1.id}{stmt_other.id} is ready"
    db.add(ActionItem(
        organization_id=org.id, entity_type="STATEMENT",
        action_type="STATEMENT_READY",
        title=sibling_title,
        is_auto_generated=True,
    ))
    db.commit()

    res = client.delete(f"/api/royalties/statements/{org.id}/{stmt1.id}")
    assert res.status_code == 200, res.text

    remaining = db.query(ActionItem).filter(
        ActionItem.organization_id == org.id,
    ).all()
    titles = [a.title for a in remaining]
    assert sibling_title in titles, (
        f"Sibling action item must NOT be deleted. Titles remaining: {titles}"
    )
    assert all(not t.startswith(f"Statement #{stmt1.id}:") for t in titles)


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


# ---------- Task #67: performance regression guard ----------
#
# Budgets are intentionally generous (3x typical observed runtime on the
# in-memory SQLite test runner). They exist so a future regression that
# turns one of the per-statement delete queries into an O(N) loop will
# trip the test instead of silently timing out a real request.
#
# Observed local runtime (SQLite :memory:, ~10k tx + ~50k ledger entries):
#   delete-preview  ~1.5s
#   delete          ~3-4s
# Budgets:
#   PREVIEW_BUDGET_S = 6.0
#   DELETE_BUDGET_S  = 12.0
PREVIEW_BUDGET_S = 6.0
DELETE_BUDGET_S = 12.0


def _seed_large_statement(db, org_id, *, num_tx=10_000, num_ledger=50_000):
    """Bulk-seed a statement with the requested number of transactions
    and ledger entries (mix of EARNING / RECOUPMENT_APPLIED / PAYMENT)
    using SQLAlchemy core inserts so seeding stays well under a minute."""
    stmt = _make_statement(db, org_id, total_revenue_cents=num_tx * 100)
    payee = _make_payee(db, org_id)
    run = _make_run(db, org_id, stmt.id)

    # A handful of advances so RECOUPMENT_APPLIED rows distribute across
    # multiple advance_id values (exercises the GROUP BY in the summary).
    advances = []
    for i in range(20):
        a = AdvanceV2(
            org_id=org_id, payee_id=payee.id,
            advance_name=f"Adv {i}",
            advance_date=date(2026, 1, 1), currency="USD",
            principal_amount_cents=1_000_000, recoupable=True,
            recoupment_pool="GLOBAL",
            outstanding_balance_cents=1_000_000,
        )
        db.add(a)
    db.commit()
    advances = db.query(AdvanceV2).filter(AdvanceV2.org_id == org_id).all()
    advance_ids = [a.id for a in advances]

    # Bulk-insert transactions
    tx_rows = [
        {
            "statement_id": stmt.id,
            "organization_id": org_id,
            "original_track_title": f"Track {i}",
            "original_artist": "Artist",
            "revenue_cents": 100,
            "currency": "USD",
            "match_status": "MATCHED" if i % 2 else "UNMATCHED",
        }
        for i in range(num_tx)
    ]
    db.bulk_insert_mappings(RoyaltyTransaction, tx_rows)
    db.commit()

    # Mix: 60% EARNING, 30% RECOUPMENT_APPLIED, 10% PAYMENT
    n_earn = int(num_ledger * 0.6)
    n_recoup = int(num_ledger * 0.3)
    n_pay = num_ledger - n_earn - n_recoup
    base_dt = datetime(2026, 2, 1, 12, 0, 0)

    ledger_rows = []
    for i in range(n_earn):
        ledger_rows.append({
            "org_id": org_id, "statement_id": stmt.id,
            "processing_run_id": run.id, "payee_id": payee.id,
            "entry_type": "EARNING", "amount_cents": 100,
            "created_at": base_dt,
        })
    for i in range(n_recoup):
        ledger_rows.append({
            "org_id": org_id, "statement_id": stmt.id,
            "processing_run_id": run.id, "payee_id": payee.id,
            "entry_type": "RECOUPMENT_APPLIED", "amount_cents": -50,
            "advance_id": advance_ids[i % len(advance_ids)],
            "recoupment_pool": "GLOBAL",
            "created_at": base_dt,
        })
    for i in range(n_pay):
        ledger_rows.append({
            "org_id": org_id, "statement_id": stmt.id,
            "processing_run_id": run.id, "payee_id": payee.id,
            "entry_type": "PAYMENT", "amount_cents": -200,
            "memo": f"Payment {i}", "created_at": base_dt,
        })

    # Insert ledger entries in chunks to keep memory bounded.
    CHUNK = 5000
    for i in range(0, len(ledger_rows), CHUNK):
        db.bulk_insert_mappings(RoyaltyLedgerEntry, ledger_rows[i:i + CHUNK])
    db.commit()

    return stmt, n_pay


def test_delete_preview_and_delete_stay_within_budget_for_huge_statement(db, org_user, client):
    """Performance guard for the new delete-preview + delete pipeline.

    Seeds ~10k transactions and ~50k ledger entries (mix of EARNING /
    RECOUPMENT_APPLIED / PAYMENT) and asserts both endpoints stay
    within a documented time budget. Also asserts zero residue after
    the delete.
    """
    import time
    org, _ = org_user
    stmt, n_pay = _seed_large_statement(db, org.id, num_tx=10_000, num_ledger=50_000)
    stmt_id = stmt.id

    # delete-preview ----------------------------------------------------
    t0 = time.perf_counter()
    res = client.get(f"/api/royalties/statements/{org.id}/{stmt_id}/delete-preview")
    preview_elapsed = time.perf_counter() - t0
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["transaction_count"] == 10_000
    assert body["ledger_entry_count"] == 50_000
    assert len(body["advance_restores"]) == 20
    assert len(body["payments_unwound"]) == n_pay
    assert preview_elapsed < PREVIEW_BUDGET_S, (
        f"delete-preview took {preview_elapsed:.2f}s, budget {PREVIEW_BUDGET_S}s. "
        f"A regression likely turned one of the summary queries into an O(N) loop."
    )

    # delete ------------------------------------------------------------
    t0 = time.perf_counter()
    res = client.delete(f"/api/royalties/statements/{org.id}/{stmt_id}")
    delete_elapsed = time.perf_counter() - t0
    assert res.status_code == 200, res.text
    assert delete_elapsed < DELETE_BUDGET_S, (
        f"delete took {delete_elapsed:.2f}s, budget {DELETE_BUDGET_S}s. "
        f"A regression likely turned the per-ledger-entry audit-log loop "
        f"or one of the cascade deletes into an O(N) round-trip."
    )

    # Zero residue ------------------------------------------------------
    db.expire_all()
    assert db.query(RoyaltyStatement).filter(RoyaltyStatement.id == stmt_id).first() is None
    assert db.query(RoyaltyLedgerEntry).filter(RoyaltyLedgerEntry.statement_id == stmt_id).count() == 0
    assert db.query(RoyaltyTransaction).filter(RoyaltyTransaction.statement_id == stmt_id).count() == 0
    assert db.query(RoyaltyProcessingRun).filter(RoyaltyProcessingRun.statement_id == stmt_id).count() == 0

    # Advance balances were restored: each advance got back 30%/20 of the
    # 50k ledger entries * 50 cents = 37_500 cents per advance on top of
    # its starting 1_000_000.
    adv_balances = [a.outstanding_balance_cents for a in db.query(AdvanceV2).filter(AdvanceV2.org_id == org.id).all()]
    assert all(b > 1_000_000 for b in adv_balances), (
        f"advance balances were not restored after delete: {adv_balances}"
    )
