"""Task #204 — route-level tests for the welcome-email wiring.

Pins:
  * Admin create_user fires the welcome email with the temp password.
  * Admin create_user is gated by org-level welcome_email_enabled (off => no send).
  * Admin create_user STILL succeeds (201/200) when the email provider blows up.
  * /auth/register fires the welcome email with no temp password.
  * GET/PUT /api/organizations/{org_id}/welcome-email-settings authz + persistence.
"""
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.database import Base, get_db
from backend.models.models import User, Organization, OrganizationMember
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


def _mk_org(db, name, welcome_enabled=True):
    org = Organization(
        name=name, type="LABEL", account_type="ENTERPRISE", display_name=name,
        welcome_email_enabled=welcome_enabled,
    )
    db.add(org); db.commit(); db.refresh(org)
    return org


def _mk_user(db, username, email, is_super=False, is_admin=False):
    u = User(
        username=username, email=email,
        hashed_password=hash_password("x"),
        is_admin=is_admin, is_super_admin=is_super,
    )
    db.add(u); db.commit(); db.refresh(u)
    return u


def _login(db, user):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_current_super_admin] = lambda: user


# ----------------------------------------------------------------------
# /api/admin/users (super-admin create)
# ----------------------------------------------------------------------

def test_admin_create_user_sends_welcome_email_with_temp_password(ctx):
    db, client = ctx
    sa = _mk_user(db, "root", "root@x.com", is_super=True, is_admin=True)
    org = _mk_org(db, "Acme")
    _login(db, sa)

    fake = MagicMock()
    fake.send_email.return_value = True
    with patch("backend.routes.admin.get_email_provider", create=True, return_value=fake), \
         patch("backend.services.email_provider.get_email_provider", return_value=fake):
        r = client.post("/api/admin/users", json={
            "username": "newbie", "email": "newbie@x.com",
            "password": "TempPass!23", "is_admin": False,
            "organization_id": org.id, "organization_role": "MEMBER",
        })
    assert r.status_code in (200, 201), r.text
    assert fake.send_email.called
    kwargs = fake.send_email.call_args.kwargs
    assert kwargs["to"] == "newbie@x.com"
    assert "TempPass!23" in kwargs["html_body"]
    assert "Welcome to Cadence" in kwargs["subject"]


def test_admin_create_user_skips_email_when_org_toggle_off(ctx):
    db, client = ctx
    sa = _mk_user(db, "root", "root@x.com", is_super=True, is_admin=True)
    org = _mk_org(db, "Quiet Inc", welcome_enabled=False)
    _login(db, sa)

    fake = MagicMock()
    fake.send_email.return_value = True
    with patch("backend.services.email_provider.get_email_provider", return_value=fake):
        r = client.post("/api/admin/users", json={
            "username": "silent", "email": "silent@x.com",
            "password": "Pw!23456", "is_admin": False,
            "organization_id": org.id, "organization_role": "MEMBER",
        })
    assert r.status_code in (200, 201), r.text
    assert not fake.send_email.called


def test_admin_create_user_succeeds_when_email_provider_explodes(ctx):
    db, client = ctx
    sa = _mk_user(db, "root", "root@x.com", is_super=True, is_admin=True)
    org = _mk_org(db, "Acme")
    _login(db, sa)

    fake = MagicMock()
    fake.send_email.side_effect = RuntimeError("smtp down")
    with patch("backend.services.email_provider.get_email_provider", return_value=fake):
        r = client.post("/api/admin/users", json={
            "username": "resilient", "email": "resilient@x.com",
            "password": "Pw!23456", "is_admin": False,
            "organization_id": org.id, "organization_role": "MEMBER",
        })
    # The user row MUST be created even when the welcome-email send blows up.
    assert r.status_code in (200, 201), r.text
    assert db.query(User).filter(User.username == "resilient").first() is not None


# ----------------------------------------------------------------------
# /api/auth/register (self-signup / invite acceptance)
# ----------------------------------------------------------------------

def test_register_sends_welcome_email_without_temp_password(ctx):
    db, client = ctx
    fake = MagicMock()
    fake.send_email.return_value = True
    with patch("backend.services.email_provider.get_email_provider", return_value=fake):
        r = client.post("/api/auth/register", json={
            "username": "selfsign", "email": "self@x.com",
            "password": "ChosenPw!9",
        })
    assert r.status_code == 200, r.text
    assert fake.send_email.called
    body = fake.send_email.call_args.kwargs["html_body"]
    assert "ChosenPw!9" not in body
    assert "Temporary password" not in body
    assert "Welcome to Cadence" in body


# ----------------------------------------------------------------------
# /api/organizations/{id}/welcome-email-settings
# ----------------------------------------------------------------------

def test_welcome_email_settings_get_default_true(ctx):
    db, client = ctx
    org = _mk_org(db, "Acme")
    owner = _mk_user(db, "ownr", "o@x.com")
    db.add(OrganizationMember(organization_id=org.id, user_id=owner.id, role="OWNER"))
    db.commit()
    _login(db, owner)

    r = client.get(f"/api/organizations/{org.id}/welcome-email-settings")
    assert r.status_code == 200
    assert r.json()["welcome_email_enabled"] is True


def test_welcome_email_settings_put_admin_only(ctx):
    db, client = ctx
    org = _mk_org(db, "Acme")
    owner = _mk_user(db, "ownr", "o@x.com")
    member = _mk_user(db, "memb", "m@x.com")
    db.add_all([
        OrganizationMember(organization_id=org.id, user_id=owner.id, role="OWNER"),
        OrganizationMember(organization_id=org.id, user_id=member.id, role="MEMBER"),
    ])
    db.commit()

    _login(db, member)
    r = client.put(f"/api/organizations/{org.id}/welcome-email-settings",
                   json={"welcome_email_enabled": False})
    assert r.status_code == 403

    _login(db, owner)
    r = client.put(f"/api/organizations/{org.id}/welcome-email-settings",
                   json={"welcome_email_enabled": False})
    assert r.status_code == 200
    assert r.json()["welcome_email_enabled"] is False
    db.refresh(org)
    assert org.welcome_email_enabled is False


def test_welcome_email_settings_non_member_forbidden(ctx):
    db, client = ctx
    org = _mk_org(db, "Acme")
    outsider = _mk_user(db, "out", "out@x.com")
    _login(db, outsider)
    r = client.get(f"/api/organizations/{org.id}/welcome-email-settings")
    assert r.status_code == 403
