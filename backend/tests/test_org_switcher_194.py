"""Task #194 — additional automated guardrails for the org-switcher.

Task #190 ships a persistent ``users.current_organization_id`` pointer
plus ``resolve_active_org_id`` / ``get_active_membership`` helpers that
auto-resolve the active org for every API call. ``test_active_org_pointer_190``
already pins the high-level switcher contract; this file fills in the
explicit gaps the QA checklist for #194 calls out:

* Unit coverage for ``resolve_active_org_id`` across every branch
  (valid pointer, null pointer w/ backfill, single-membership user,
  super-admin path, and the no-membership case).
* Unit coverage for ``get_active_membership`` mirroring those branches.
* ``PATCH /api/organizations/current`` returning 404 when the target
  org does not exist.
* A leak regression that hits an *auto-resolved* org-scoped widget
  endpoint (``/api/valuation-reports/catalog/summary``) — i.e. one that
  never takes ``org_id`` as a path param and trusts the active-org
  pointer entirely. If the pointer ever leaked across tenants, this
  endpoint is exactly where it would surface.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.database import Base, get_db
from backend.models.models import (
    User, Organization, OrganizationMember, Creator, Song,
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
    member = OrganizationMember(
        organization_id=org.id, user_id=user.id, role=role,
    )
    db.add(member); db.commit(); db.refresh(member)
    return member


def _login_as(user):
    app.dependency_overrides[get_current_user] = lambda: user


# ===================================================================
# resolve_active_org_id — unit branches
# ===================================================================

def test_resolve_returns_valid_pointer_for_multi_org_user(client):
    """Pointer points at a real membership → return it as-is, no
    self-heal, no rewrite."""
    db, _ = client
    org_a = _make_org(db, "AAA")
    org_b = _make_org(db, "BBB")
    user = _make_user(db, "valid")
    _join(db, org_a, user)
    _join(db, org_b, user)
    user.current_organization_id = org_b.id
    db.commit()

    assert resolve_active_org_id(db, user) == org_b.id

    db.refresh(user)
    # Pointer must NOT have been rewritten by the resolve call.
    assert user.current_organization_id == org_b.id


def test_resolve_backfills_null_pointer_to_oldest_membership(client):
    """Null pointer (legacy users pre-#190) → resolver returns the
    oldest membership AND persists it so subsequent calls are stable."""
    db, _ = client
    org_a = _make_org(db, "AAA")
    org_b = _make_org(db, "BBB")
    user = _make_user(db, "nullptr")
    _join(db, org_a, user)   # oldest membership row
    _join(db, org_b, user)
    assert user.current_organization_id is None  # pre-condition

    resolved = resolve_active_org_id(db, user)
    assert resolved == org_a.id

    db.refresh(user)
    # Self-heal must persist so the next request is stable.
    assert user.current_organization_id == org_a.id


def test_resolve_for_single_membership_user_returns_that_membership(client):
    """Single-membership user with no pointer set → returns the only
    membership and backfills the pointer."""
    db, _ = client
    org_a = _make_org(db, "AAA")
    user = _make_user(db, "solo")
    _join(db, org_a, user)
    assert user.current_organization_id is None

    assert resolve_active_org_id(db, user) == org_a.id

    db.refresh(user)
    assert user.current_organization_id == org_a.id


def test_resolve_returns_none_for_user_with_no_memberships(client):
    """No memberships at all → returns None and does not raise."""
    db, _ = client
    user = _make_user(db, "lonely")

    assert resolve_active_org_id(db, user) is None

    # Strict mode and impersonation mode agree when there's no org.
    assert resolve_active_org_id(
        db, user, allow_staff_impersonation=True,
    ) is None


def test_resolve_super_admin_with_no_memberships_is_none(client):
    """Super-admin with no real membership has no active org from this
    helper's perspective. The org-resolution route layer is what
    falls back to "first org in the system" for staff — the helper
    itself must not silently grant a tenant id, or write helpers
    using the strict default would inherit cross-tenant access."""
    db, _ = client
    admin = _make_user(db, "root", is_super_admin=True)

    assert resolve_active_org_id(db, admin) is None
    assert resolve_active_org_id(
        db, admin, allow_staff_impersonation=True,
    ) is None


def test_resolve_super_admin_with_membership_returns_pointer(client):
    """Super-admin who is also a real org member → pointer wins, just
    like a regular user. Super-admin-ness must not bypass the
    pointer."""
    db, _ = client
    org_a = _make_org(db, "AAA")
    org_b = _make_org(db, "BBB")
    admin = _make_user(db, "rootmember", is_super_admin=True)
    _join(db, org_a, admin)
    _join(db, org_b, admin)
    admin.current_organization_id = org_b.id
    db.commit()

    assert resolve_active_org_id(db, admin) == org_b.id


# ===================================================================
# get_active_membership — unit branches
# ===================================================================

def test_get_active_membership_returns_pointer_membership(client):
    db, _ = client
    org_a = _make_org(db, "AAA")
    org_b = _make_org(db, "BBB")
    user = _make_user(db, "ham")
    _join(db, org_a, user, role="OWNER")
    member_b = _join(db, org_b, user, role="ADMIN")
    user.current_organization_id = org_b.id
    db.commit()

    m = get_active_membership(db, user)
    assert m is not None
    assert m.id == member_b.id
    assert m.organization_id == org_b.id
    assert m.role == "ADMIN"


def test_get_active_membership_self_heals_stale_pointer(client):
    """Pointer references an org the user is no longer a member of
    → fall back to oldest membership row."""
    db, _ = client
    org_a = _make_org(db, "AAA")
    org_b = _make_org(db, "BBB")
    org_c = _make_org(db, "CCC")  # user is NOT a member here
    user = _make_user(db, "stalemem")
    member_a = _join(db, org_a, user)
    _join(db, org_b, user)
    user.current_organization_id = org_c.id
    db.commit()

    m = get_active_membership(db, user)
    assert m is not None
    assert m.id == member_a.id
    assert m.organization_id == org_a.id


def test_get_active_membership_backfills_null_pointer(client):
    db, _ = client
    org_a = _make_org(db, "AAA")
    org_b = _make_org(db, "BBB")
    user = _make_user(db, "nullmem")
    member_a = _join(db, org_a, user)
    _join(db, org_b, user)
    assert user.current_organization_id is None

    m = get_active_membership(db, user)
    assert m is not None
    assert m.id == member_a.id


def test_get_active_membership_single_membership(client):
    db, _ = client
    org_a = _make_org(db, "AAA")
    user = _make_user(db, "singlemem")
    member_a = _join(db, org_a, user)

    m = get_active_membership(db, user)
    assert m is not None
    assert m.id == member_a.id


def test_get_active_membership_returns_none_when_no_memberships(client):
    db, _ = client
    user = _make_user(db, "nomem")
    assert get_active_membership(db, user) is None


def test_get_active_membership_super_admin_with_no_memberships(client):
    """Super-admin without a real membership returns None from this
    helper — staff-only fallbacks live at the route layer."""
    db, _ = client
    admin = _make_user(db, "rootnomem", is_super_admin=True)
    assert get_active_membership(db, admin) is None


# ===================================================================
# PATCH /api/organizations/current — 404 path (190 covered success/403)
# ===================================================================

def test_patch_current_rejects_missing_org_for_non_member(client):
    """A regular user PATCHing to a non-existent org id is stopped at
    the membership gate (403), never reaches the org-lookup, and
    must not rewrite the pointer. The 404 path is exercised
    separately in the staff-bypass test below."""
    db, _ = client
    org_a = _make_org(db, "AAA")
    user = _make_user(db, "ghosthunter")
    _join(db, org_a, user)
    user.current_organization_id = org_a.id
    db.commit()

    _login_as(user)
    # Cadence staff is the only role allowed past the membership gate,
    # so a non-member regular user must still be 403'd here. The 404
    # path for a missing org is asserted separately via the staff
    # case below, where the membership check is bypassed and the
    # missing-org error path is reachable.
    r = client[1].patch(
        "/api/organizations/current",
        json={"organization_id": 999_999},
    )
    assert r.status_code == 403, r.text

    db.refresh(user)
    assert user.current_organization_id == org_a.id


def test_patch_current_returns_404_for_missing_org_as_staff(client):
    """Cadence staff bypasses the membership check, so a non-existent
    org id must surface as 404 from the org-lookup, not a silent 200."""
    db, _ = client
    org_a = _make_org(db, "AAA")
    staff = _make_user(db, "staff404", is_cadence_staff=True)
    _join(db, org_a, staff)
    staff.current_organization_id = org_a.id
    db.commit()

    _login_as(staff)
    r = client[1].patch(
        "/api/organizations/current",
        json={"organization_id": 999_999},
    )
    assert r.status_code == 404, r.text

    db.refresh(staff)
    assert staff.current_organization_id == org_a.id


# ===================================================================
# Leak regression — auto-resolved widget endpoint
# ===================================================================

def test_auto_resolved_widget_only_returns_active_org_data(client):
    """The repro for the original tenant-isolation bug: a multi-org
    user whose pointer is set to org A must only see org A's data
    when hitting an auto-resolved widget endpoint that takes no
    ``org_id`` path param.

    ``GET /api/organizations/current`` is the obvious one (already
    covered in test_active_org_pointer_190), but the more dangerous
    surface is widget endpoints that internally call
    ``get_active_membership`` and then query org-scoped tables. We
    use ``/api/valuation-reports/catalog/summary`` because it's
    auto-resolved AND lists the org's songs/top-contributors — i.e.
    exactly the cross-tenant bleed the user originally reported on
    the Home dashboard.
    """
    db, c = client
    org_a = _make_org(db, "Org-A")
    org_b = _make_org(db, "Org-B")
    user = _make_user(db, "leakcheck")
    _join(db, org_a, user)
    _join(db, org_b, user)

    # Distinct catalog data per tenant. If the pointer leaks, org_b's
    # songs/creators would surface in the response.
    db.add(Creator(organization_id=org_a.id, display_name="Alice A", roles=["WRITER"]))
    db.add(Creator(organization_id=org_b.id, display_name="Bob B", roles=["WRITER"]))
    db.add(Song(organization_id=org_a.id, title="Song A1", primary_artist="Alice A"))
    db.add(Song(organization_id=org_a.id, title="Song A2", primary_artist="Alice A"))
    db.add(Song(organization_id=org_b.id, title="Song B1", primary_artist="Bob B"))
    db.add(Song(organization_id=org_b.id, title="Song B2", primary_artist="Bob B"))
    db.add(Song(organization_id=org_b.id, title="Song B3", primary_artist="Bob B"))
    db.commit()

    user.current_organization_id = org_a.id
    db.commit()

    _login_as(user)

    # 1) /current must scope to org_a.
    r = c.get("/api/organizations/current")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == org_a.id
    # And the song_count tile must reflect only org_a's catalog.
    assert body["song_count"] == 2

    # 2) The org-scoped widget endpoint (auto-resolves the active org
    #    via get_active_membership — no org_id path param) must
    #    likewise scope strictly to org_a. ``total_songs`` and
    #    ``organization_name`` are the user-visible bleed surface from
    #    the original Home-dashboard repro.
    r = c.get("/api/valuation/catalog/summary")
    assert r.status_code == 200, r.text
    summary = r.json()
    assert summary["organization_name"] == "Org-A"
    assert summary["total_songs"] == 2

    # 3) Switch the pointer to org_b and re-check — both /current and
    #    the widget endpoint must move with the pointer, never leak
    #    the previous org.
    user.current_organization_id = org_b.id
    db.commit()

    r = c.get("/api/organizations/current")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == org_b.id
    assert body["song_count"] == 3

    r = c.get("/api/valuation/catalog/summary")
    assert r.status_code == 200, r.text
    summary = r.json()
    assert summary["organization_name"] == "Org-B"
    assert summary["total_songs"] == 3

    # 4) /mine flips the active flag in lockstep.
    r = c.get("/api/organizations/mine")
    assert r.status_code == 200, r.text
    by_id = {o["id"]: o for o in r.json()["organizations"]}
    assert by_id[org_b.id]["is_active"] is True
    assert by_id[org_a.id]["is_active"] is False
