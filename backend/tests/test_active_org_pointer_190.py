"""Task #190 — regression tests for the active-org pointer & switcher.

The bug: a multi-org user's Home dashboard could leak another org's
catalog because `GET /api/organizations/current` resolved the org via
an unordered `OrganizationMember.first()`. The fix introduces a
persistent `users.current_organization_id` pointer with
`resolve_active_org_id` self-healing, plus `GET /api/organizations/mine`
and `PATCH /api/organizations/current`.

These tests pin the contract:
  * GET /current respects the pointer for multi-org users
  * GET /mine lists every membership with role + active flag
  * PATCH /current persists the pointer
  * PATCH /current rejects non-members with 403
  * PATCH /current allows is_cadence_staff to switch to any org
  * POST /api/organizations/ auto-activates the new org
  * resolve_active_org_id self-heals a stale pointer
"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.database import Base, get_db
from backend.models.models import (
    User, Organization, OrganizationMember, Creator,
)
from backend.utils.auth import (
    get_current_user,
    get_password_hash as hash_password,
    resolve_active_org_id,
    get_active_membership,
)


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
def client():
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


def _make_org(db, name):
    org = Organization(
        name=name, type="LABEL", account_type="ENTERPRISE", display_name=name,
    )
    db.add(org); db.commit(); db.refresh(org)
    return org


def _make_user(db, username="u", *, is_super_admin=False, is_cadence_staff=False):
    user = User(
        username=username,
        email=f"{username}@x.com",
        hashed_password=hash_password("x"),
        is_active=True,
        is_super_admin=is_super_admin,
        is_cadence_staff=is_cadence_staff,
    )
    db.add(user); db.commit(); db.refresh(user)
    return user


def _join(db, org, user, role="OWNER"):
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=role))
    db.commit()


def _login_as(user):
    app.dependency_overrides[get_current_user] = lambda: user


# ---------------------------------------------------------------- GET /current

def test_current_respects_active_org_pointer_for_multi_org_user(client):
    """The bug repro: user belongs to two orgs, pointer points to the second
    one, /current must return the second one regardless of insertion order."""
    db, c = client
    org_a = _make_org(db, "AAA")  # oldest membership
    org_b = _make_org(db, "BBB")  # active pointer target
    user = _make_user(db, "multiorg")
    _join(db, org_a, user)
    _join(db, org_b, user)

    user.current_organization_id = org_b.id
    db.commit()

    _login_as(user)
    r = c.get("/api/organizations/current")
    assert r.status_code == 200, r.text
    assert r.json()["id"] == org_b.id
    assert r.json()["name"] == "BBB"


def test_current_self_heals_stale_pointer(client):
    """If the pointer references an org the user is no longer a member of,
    resolve_active_org_id falls back to the oldest membership and persists
    the corrected value so subsequent reads are consistent."""
    db, c = client
    org_a = _make_org(db, "AAA")
    org_b = _make_org(db, "BBB")
    org_c = _make_org(db, "CCC")  # user will NOT be a member here
    user = _make_user(db, "stale")
    _join(db, org_a, user)
    _join(db, org_b, user)

    user.current_organization_id = org_c.id  # poisoned pointer
    db.commit()

    healed = resolve_active_org_id(db, user)
    db.refresh(user)
    assert healed == org_a.id  # oldest valid membership
    assert user.current_organization_id == org_a.id  # persisted


# ------------------------------------------------------------------- GET /mine

def test_mine_lists_all_orgs_with_role_and_active_flag(client):
    db, c = client
    org_a = _make_org(db, "AAA")
    org_b = _make_org(db, "BBB")
    user = _make_user(db, "lister")
    _join(db, org_a, user, role="OWNER")
    _join(db, org_b, user, role="ADMIN")
    user.current_organization_id = org_b.id
    db.commit()

    _login_as(user)
    r = c.get("/api/organizations/mine")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["active_organization_id"] == org_b.id
    by_id = {o["id"]: o for o in body["organizations"]}
    assert by_id[org_a.id]["role"] == "OWNER"
    assert by_id[org_a.id]["is_active"] is False
    assert by_id[org_b.id]["role"] == "ADMIN"
    assert by_id[org_b.id]["is_active"] is True


# -------------------------------------------------------------- PATCH /current

def test_patch_current_persists_pointer(client):
    db, c = client
    org_a = _make_org(db, "AAA")
    org_b = _make_org(db, "BBB")
    user = _make_user(db, "switcher")
    _join(db, org_a, user)
    _join(db, org_b, user)
    user.current_organization_id = org_a.id
    db.commit()

    _login_as(user)
    r = c.patch("/api/organizations/current", json={"organization_id": org_b.id})
    assert r.status_code == 200, r.text
    assert r.json()["id"] == org_b.id

    db.refresh(user)
    assert user.current_organization_id == org_b.id

    # And /current now reflects the new active org
    r = c.get("/api/organizations/current")
    assert r.json()["id"] == org_b.id


def test_patch_current_rejects_non_member_with_403(client):
    db, c = client
    org_a = _make_org(db, "AAA")
    org_b = _make_org(db, "BBB")  # user is NOT a member here
    user = _make_user(db, "outsider")
    _join(db, org_a, user)
    user.current_organization_id = org_a.id
    db.commit()

    _login_as(user)
    r = c.patch("/api/organizations/current", json={"organization_id": org_b.id})
    assert r.status_code == 403, r.text

    db.refresh(user)
    # Pointer must NOT have been moved to the unauthorized org
    assert user.current_organization_id != org_b.id
    assert user.current_organization_id == org_a.id


def test_patch_current_allows_cadence_staff_to_switch_to_any_org(client):
    """Cadence staff can switch into any org for cross-tenant support work,
    mirroring the read access semantics of GET /api/organizations/{org_id}.
    The switch must be DURABLE — subsequent /current reads must keep
    returning the impersonated org, otherwise the pointer would self-heal
    away on the very next request and break staff workflows."""
    db, c = client
    org_a = _make_org(db, "AAA")
    org_b = _make_org(db, "BBB")  # staff is NOT a member here
    staff = _make_user(db, "staff", is_cadence_staff=True)
    _join(db, org_a, staff)

    _login_as(staff)
    r = c.patch("/api/organizations/current", json={"organization_id": org_b.id})
    assert r.status_code == 200, r.text
    assert r.json()["id"] == org_b.id

    # Durability: /current must still resolve to org_b after the PATCH,
    # not self-heal back to the staff member's only real membership (org_a).
    r = c.get("/api/organizations/current")
    assert r.status_code == 200, r.text
    assert r.json()["id"] == org_b.id

    db.refresh(staff)
    assert staff.current_organization_id == org_b.id

    # And resolve_active_org_id directly returns the impersonated org
    assert resolve_active_org_id(db, staff) == org_b.id


def test_resolve_active_org_id_falls_back_when_impersonated_org_deleted(client):
    """If a staff member's pointer references an org that has since been
    deleted entirely, resolve_active_org_id should fall back to the
    staff member's own membership rather than returning a dangling id."""
    db, c = client
    org_a = _make_org(db, "AAA")
    org_b = _make_org(db, "BBB")  # will be deleted
    staff = _make_user(db, "staff2", is_cadence_staff=True)
    _join(db, org_a, staff)
    staff.current_organization_id = org_b.id
    db.commit()

    # Delete the impersonated org; FK is ON DELETE SET NULL on the
    # column, so the pointer becomes None on commit. Even if a future
    # schema variant kept a dangling id, the org-existence guard in
    # resolve_active_org_id should still send us back to org_a.
    db.delete(org_b); db.commit()
    db.refresh(staff)

    assert resolve_active_org_id(db, staff) == org_a.id


# ----------------------------------------------------- POST / auto-activation

def test_create_org_auto_activates_new_org(client):
    """Creating a new org via POST /api/organizations/ must transparently
    switch the user into it, otherwise the new-org Home dashboard keeps
    showing the prior org's data (the original task #190 repro)."""
    db, c = client
    org_a = _make_org(db, "AAA")
    user = _make_user(db, "creator")
    _join(db, org_a, user)
    user.current_organization_id = org_a.id
    db.commit()

    _login_as(user)
    r = c.post(
        "/api/organizations/",
        json={"name": "PMCS", "type": "LABEL", "account_type": "ENTERPRISE"},
    )
    assert r.status_code in (200, 201), r.text
    new_org_id = r.json()["id"]

    db.refresh(user)
    assert user.current_organization_id == new_org_id

    # /current now scopes to the brand-new org
    r = c.get("/api/organizations/current")
    assert r.json()["id"] == new_org_id


# ------------------------------------------------------ tenant-isolation guard

def test_creators_org_endpoint_does_not_leak_across_tenants(client):
    """The user-visible repro: a multi-org user must only ever see the
    creators of the org they're scoped to. Calling /api/creators/org/{A}
    while authenticated as a member of A and B must return only A's
    creators — no cross-tenant bleed."""
    db, c = client
    org_a = _make_org(db, "AAA")
    org_b = _make_org(db, "BBB")
    user = _make_user(db, "scoped")
    _join(db, org_a, user)
    _join(db, org_b, user)
    user.current_organization_id = org_b.id
    db.commit()

    db.add(Creator(organization_id=org_a.id, display_name="Alice A", roles=["WRITER"]))
    db.add(Creator(organization_id=org_b.id, display_name="Bob B", roles=["WRITER"]))
    db.commit()

    _login_as(user)

    r = c.get(f"/api/creators/org/{org_a.id}")
    assert r.status_code == 200, r.text
    names = {c["display_name"] for c in r.json()}
    assert names == {"Alice A"}

    r = c.get(f"/api/creators/org/{org_b.id}")
    names = {c["display_name"] for c in r.json()}
    assert names == {"Bob B"}
