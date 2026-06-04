"""Task #220 — route-level tests for lead outreach emails.

Pins:
  * POST /api/admin/leads/{id}/contact sends the qualify template for WAITLIST
    leads and marks them contacted.
  * The demo_schedule template is used for DEMO_REQUEST leads.
  * email_type / lead_type mismatches are rejected (400) WITHOUT marking the
    lead contacted.
  * Unsupported lead types (investor / intern) are rejected (400).
  * An unknown email_type is rejected (400).
  * A missing lead is rejected (404).
  * A provider failure returns 500 and does NOT mark the lead contacted.
  * The endpoint is gated to platform super-admins.
"""
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.database import Base, get_db
from backend.models.models import User
from backend.models.misc import Lead
from backend.utils.auth import (
    get_current_user,
    get_current_super_admin,
    get_password_hash as hash_password,
)


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _fk(dbapi_conn, _record):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def ctx():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    def _override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    yield db, TestClient(app)
    app.dependency_overrides.clear()
    db.close()


def _mk_user(db, username, email, is_super=False, is_admin=False):
    u = User(
        username=username, email=email,
        hashed_password=hash_password("x"),
        is_admin=is_admin, is_super_admin=is_super,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _mk_lead(db, email, lead_type, name="Jane Doe"):
    lead = Lead(email=email, name=name, lead_type=lead_type)
    db.add(lead); db.commit(); db.refresh(lead)
    return lead


def _login(db, user):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_super_admin] = lambda: user


def _fake_provider(result=True, explode=False):
    fake = MagicMock()
    if explode:
        fake.send_email.side_effect = RuntimeError("smtp down")
    else:
        fake.send_email.return_value = result
    return fake


# ----------------------------------------------------------------------
# Happy paths
# ----------------------------------------------------------------------

def test_contact_waitlist_sends_qualify_and_marks_contacted(ctx):
    db, client = ctx
    sa = _mk_user(db, "root", "root@x.com", is_super=True, is_admin=True)
    lead = _mk_lead(db, "wl@x.com", "WAITLIST")
    _login(db, sa)

    fake = _fake_provider()
    with patch("backend.services.email_provider.get_email_provider", return_value=fake):
        r = client.post(f"/api/admin/leads/{lead.id}/contact",
                        json={"email_type": "qualify"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["success"] is True
    assert body["status"] == "contacted"
    assert body["contacted_at"]

    assert fake.send_email.called
    kwargs = fake.send_email.call_args.kwargs
    assert kwargs["to"] == "wl@x.com"
    assert "waitlist" in kwargs["subject"].lower()

    db.refresh(lead)
    assert lead.status == "contacted"
    assert lead.contacted_at is not None


def test_contact_demo_sends_demo_schedule(ctx):
    db, client = ctx
    sa = _mk_user(db, "root", "root@x.com", is_super=True, is_admin=True)
    lead = _mk_lead(db, "demo@x.com", "DEMO_REQUEST")
    _login(db, sa)

    fake = _fake_provider()
    with patch("backend.services.email_provider.get_email_provider", return_value=fake):
        r = client.post(f"/api/admin/leads/{lead.id}/contact",
                        json={"email_type": "demo_schedule"})
    assert r.status_code == 200, r.text
    kwargs = fake.send_email.call_args.kwargs
    assert "demo" in kwargs["subject"].lower()
    db.refresh(lead)
    assert lead.status == "contacted"


# ----------------------------------------------------------------------
# Validation / rejections
# ----------------------------------------------------------------------

def test_mismatched_email_type_rejected_and_not_contacted(ctx):
    db, client = ctx
    sa = _mk_user(db, "root", "root@x.com", is_super=True, is_admin=True)
    lead = _mk_lead(db, "wl@x.com", "WAITLIST")
    _login(db, sa)

    fake = _fake_provider()
    with patch("backend.services.email_provider.get_email_provider", return_value=fake):
        r = client.post(f"/api/admin/leads/{lead.id}/contact",
                        json={"email_type": "demo_schedule"})
    assert r.status_code == 400, r.text
    assert not fake.send_email.called
    db.refresh(lead)
    assert lead.status == "new"
    assert lead.contacted_at is None


def test_unsupported_lead_type_rejected(ctx):
    db, client = ctx
    sa = _mk_user(db, "root", "root@x.com", is_super=True, is_admin=True)
    lead = _mk_lead(db, "inv@x.com", "INVESTOR_INQUIRY")
    _login(db, sa)

    fake = _fake_provider()
    with patch("backend.services.email_provider.get_email_provider", return_value=fake):
        r = client.post(f"/api/admin/leads/{lead.id}/contact",
                        json={"email_type": "qualify"})
    assert r.status_code == 400, r.text
    assert not fake.send_email.called
    db.refresh(lead)
    assert lead.status == "new"


def test_unknown_email_type_rejected(ctx):
    db, client = ctx
    sa = _mk_user(db, "root", "root@x.com", is_super=True, is_admin=True)
    lead = _mk_lead(db, "wl@x.com", "WAITLIST")
    _login(db, sa)

    r = client.post(f"/api/admin/leads/{lead.id}/contact",
                    json={"email_type": "bogus"})
    assert r.status_code == 400, r.text
    db.refresh(lead)
    assert lead.status == "new"


def test_missing_lead_returns_404(ctx):
    db, client = ctx
    sa = _mk_user(db, "root", "root@x.com", is_super=True, is_admin=True)
    _login(db, sa)

    r = client.post("/api/admin/leads/999999/contact",
                    json={"email_type": "qualify"})
    assert r.status_code == 404, r.text


def test_provider_failure_returns_500_and_not_contacted(ctx):
    db, client = ctx
    sa = _mk_user(db, "root", "root@x.com", is_super=True, is_admin=True)
    lead = _mk_lead(db, "wl@x.com", "WAITLIST")
    _login(db, sa)

    # Provider returns False (soft failure).
    fake = _fake_provider(result=False)
    with patch("backend.services.email_provider.get_email_provider", return_value=fake):
        r = client.post(f"/api/admin/leads/{lead.id}/contact",
                        json={"email_type": "qualify"})
    assert r.status_code == 500, r.text
    db.refresh(lead)
    assert lead.status == "new"
    assert lead.contacted_at is None


def test_provider_exception_returns_500_and_not_contacted(ctx):
    db, client = ctx
    sa = _mk_user(db, "root", "root@x.com", is_super=True, is_admin=True)
    lead = _mk_lead(db, "wl@x.com", "WAITLIST")
    _login(db, sa)

    fake = _fake_provider(explode=True)
    with patch("backend.services.email_provider.get_email_provider", return_value=fake):
        r = client.post(f"/api/admin/leads/{lead.id}/contact",
                        json={"email_type": "qualify"})
    assert r.status_code == 500, r.text
    db.refresh(lead)
    assert lead.status == "new"


# ----------------------------------------------------------------------
# List payload exposes outreach fields
# ----------------------------------------------------------------------

def test_list_leads_exposes_status_and_contacted_at(ctx):
    db, client = ctx
    sa = _mk_user(db, "root", "root@x.com", is_super=True, is_admin=True)
    lead = _mk_lead(db, "wl@x.com", "WAITLIST")
    _login(db, sa)

    fake = _fake_provider()
    with patch("backend.services.email_provider.get_email_provider", return_value=fake):
        client.post(f"/api/admin/leads/{lead.id}/contact",
                    json={"email_type": "qualify"})

    r = client.get("/api/admin/leads")
    assert r.status_code == 200, r.text
    rows = r.json()["leads"]
    row = next(x for x in rows if x["id"] == lead.id)
    assert row["status"] == "contacted"
    assert row["contacted_at"] is not None
