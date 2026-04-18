"""Task #104 — PATCH /api/royalties/statements/{org_id}/{statement_id}.

Covers:
  * 200 with field-level diff for OWNER editing period_start / period_end
  * 422 when caller submits period_start > period_end
  * 403 for a VIEWER member of the same org
  * 404 for a statement that doesn't belong to the org
  * AuditLog row written with action=STATEMENT_UPDATE and the diff
  * No audit row when nothing actually changed (no-op call)
"""
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.database import Base, get_db as original_get_db
from backend.models.models import (
    User, Organization, OrganizationMember, RoyaltyStatement, AuditLog,
)
from backend.utils.auth import get_current_user


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
def client():
    return TestClient(app)


def _make_user(db, name, super_admin=False):
    u = User(
        username=name, email=f"{name}@x.com", hashed_password="x",
        is_active=True, is_super_admin=super_admin,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _make_org(db, name="O1"):
    o = Organization(name=name, type="LABEL", account_type="ENTERPRISE", display_name=name)
    db.add(o); db.commit(); db.refresh(o)
    return o


def _make_member(db, org_id, user_id, role):
    db.add(OrganizationMember(organization_id=org_id, user_id=user_id, role=role))
    db.commit()


def _make_stmt(db, org_id, **overrides):
    stmt = RoyaltyStatement(
        organization_id=org_id,
        source_name="BMI 2024 H1",
        source_type="BMI",
        period_start=None,
        period_end=None,
        currency="USD",
        file_name="bmi_2024_h1.pdf",
        total_revenue_cents=1862298,
        status="PROCESSED",
    )
    for k, v in overrides.items():
        setattr(stmt, k, v)
    db.add(stmt); db.commit(); db.refresh(stmt)
    return stmt


def _login(user):
    app.dependency_overrides[get_current_user] = lambda: user


def _logout():
    app.dependency_overrides.pop(get_current_user, None)


def test_owner_can_set_period_and_audit_row_written(db, client):
    owner = _make_user(db, "owner1")
    org = _make_org(db)
    _make_member(db, org.id, owner.id, "OWNER")
    stmt = _make_stmt(db, org.id)
    _login(owner)
    try:
        res = client.patch(
            f"/api/royalties/statements/{org.id}/{stmt.id}",
            json={"period_start": "2024-01-01", "period_end": "2024-06-30"},
        )
    finally:
        _logout()

    assert res.status_code == 200, res.text
    body = res.json()
    assert body["changed"] is True
    assert body["period_start"] == "2024-01-01"
    assert body["period_end"] == "2024-06-30"
    assert "period_start" in body["changes"]
    assert body["changes"]["period_start"]["old"] is None
    assert body["changes"]["period_start"]["new"] == "2024-01-01"

    db.expire_all()
    refreshed = db.query(RoyaltyStatement).filter(RoyaltyStatement.id == stmt.id).first()
    assert refreshed.period_start == date(2024, 1, 1)
    assert refreshed.period_end == date(2024, 6, 30)

    audit = db.query(AuditLog).filter(
        AuditLog.action == "STATEMENT_UPDATE",
        AuditLog.entity_id == stmt.id,
    ).first()
    assert audit is not None
    assert audit.user_id == owner.id
    assert audit.organization_id == org.id
    assert "period_start" in (audit.details or {}).get("changes", {})


def test_period_start_after_end_returns_422(db, client):
    owner = _make_user(db, "owner2")
    org = _make_org(db)
    _make_member(db, org.id, owner.id, "OWNER")
    stmt = _make_stmt(db, org.id)
    _login(owner)
    try:
        res = client.patch(
            f"/api/royalties/statements/{org.id}/{stmt.id}",
            json={"period_start": "2024-12-31", "period_end": "2024-01-01"},
        )
    finally:
        _logout()
    assert res.status_code == 422, res.text


def test_viewer_cannot_edit_returns_403(db, client):
    viewer = _make_user(db, "viewer1")
    org = _make_org(db)
    _make_member(db, org.id, viewer.id, "VIEWER")
    stmt = _make_stmt(db, org.id)
    _login(viewer)
    try:
        res = client.patch(
            f"/api/royalties/statements/{org.id}/{stmt.id}",
            json={"period_start": "2024-01-01"},
        )
    finally:
        _logout()
    assert res.status_code == 403, res.text


def test_statement_in_other_org_returns_404(db, client):
    owner = _make_user(db, "owner3")
    org_a = _make_org(db, "OrgA")
    org_b = _make_org(db, "OrgB")
    _make_member(db, org_a.id, owner.id, "OWNER")
    _make_member(db, org_b.id, owner.id, "OWNER")
    stmt_b = _make_stmt(db, org_b.id)
    _login(owner)
    try:
        # Submit org_a in path but the statement belongs to org_b → 404.
        res = client.patch(
            f"/api/royalties/statements/{org_a.id}/{stmt_b.id}",
            json={"period_start": "2024-01-01"},
        )
    finally:
        _logout()
    assert res.status_code == 404, res.text


def test_no_change_no_audit_row(db, client):
    owner = _make_user(db, "owner4")
    org = _make_org(db)
    _make_member(db, org.id, owner.id, "OWNER")
    stmt = _make_stmt(
        db, org.id,
        period_start=date(2024, 1, 1), period_end=date(2024, 6, 30),
    )
    _login(owner)
    try:
        res = client.patch(
            f"/api/royalties/statements/{org.id}/{stmt.id}",
            json={"period_start": "2024-01-01", "period_end": "2024-06-30"},
        )
    finally:
        _logout()

    assert res.status_code == 200, res.text
    assert res.json()["changed"] is False
    assert db.query(AuditLog).filter(
        AuditLog.action == "STATEMENT_UPDATE", AuditLog.entity_id == stmt.id
    ).count() == 0
