"""Task #213 — Enterprise vs Professional plans.

Covers the plan source-of-truth (`plan_entitlements`), server-side catalog
limit enforcement on creator creation, the directional sharing rules
(Professional can only share OUT to Enterprise; Professional can't receive),
and the entitlement fields surfaced on the org responses.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.database import Base, get_db as original_get_db
from backend.models.models import (
    Creator,
    Organization,
    OrganizationMember,
    User,
    ClientShare,
)
from backend.utils.auth import get_current_user
from backend.services import plan_entitlements as pe


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


def _override_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db():
    prev = app.dependency_overrides.get(original_get_db)
    app.dependency_overrides[original_get_db] = _override_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    s = TestingSessionLocal()
    try:
        yield s
    finally:
        s.close()
        if prev is None:
            app.dependency_overrides.pop(original_get_db, None)
        else:
            app.dependency_overrides[original_get_db] = prev


@pytest.fixture(scope="function")
def client():
    return TestClient(app)


def _org(db, account_type="ENTERPRISE", packs=0, name="Org"):
    org = Organization(
        name=name, type="LABEL", account_type=account_type,
        display_name=name, catalog_addon_packs=packs,
    )
    db.add(org); db.commit(); db.refresh(org)
    return org


def _owner(db, org, email="owner@x.com"):
    user = User(username=email, email=email, hashed_password="x", is_active=True)
    db.add(user); db.commit(); db.refresh(user)
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="OWNER"))
    db.commit()
    return user


# ---- pure entitlement helpers -------------------------------------------------

def test_catalog_limit_professional_is_one(db):
    org = _org(db, account_type="INDIVIDUAL")
    assert pe.catalog_limit(org) == 1
    assert pe.roster_enabled(org) is False
    assert pe.can_receive_shares(org) is False


def test_catalog_limit_enterprise_scales_with_packs(db):
    assert pe.catalog_limit(_org(db, packs=0, name="A")) == 10
    assert pe.catalog_limit(_org(db, packs=1, name="B")) == 15
    assert pe.catalog_limit(_org(db, packs=3, name="C")) == 25
    ent = pe.get_entitlements(_org(db, packs=2, name="D"))
    assert ent["plan_label"] == "Enterprise"
    assert ent["roster_enabled"] is True
    assert ent["can_receive_shares"] is True
    assert ent["catalog_limit"] == 20


def test_unknown_account_type_defaults_enterprise(db):
    org = _org(db, account_type="ENTERPRISE")
    org.account_type = None
    assert pe.is_enterprise(org) is True
    assert pe.catalog_limit(org) == 10


# ---- creator-creation enforcement --------------------------------------------

def test_professional_blocked_from_second_catalog(db, client):
    org = _org(db, account_type="INDIVIDUAL")
    user = _owner(db, org)
    db.add(Creator(organization_id=org.id, display_name="First")); db.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.post(f"/api/creators/org/{org.id}", json={"display_name": "Second", "roles": ["ARTIST"]})
        assert r.status_code == 403, f"got {r.status_code}: {r.text[:200]}"
        assert "single catalog" in r.text.lower()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_professional_first_catalog_allowed(db, client):
    org = _org(db, account_type="INDIVIDUAL")
    user = _owner(db, org)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.post(f"/api/creators/org/{org.id}", json={"display_name": "Only", "roles": ["ARTIST"]})
        assert r.status_code in (200, 201), f"got {r.status_code}: {r.text[:200]}"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_enterprise_blocked_past_scaled_limit(db, client):
    org = _org(db, account_type="ENTERPRISE", packs=0)  # limit 10
    user = _owner(db, org)
    for i in range(10):
        db.add(Creator(organization_id=org.id, display_name=f"C{i}"))
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.post(f"/api/creators/org/{org.id}", json={"display_name": "Eleven", "roles": ["ARTIST"]})
        assert r.status_code == 403, f"got {r.status_code}: {r.text[:200]}"
        assert "limit of 10" in r.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ---- sharing direction rules -------------------------------------------------

def test_professional_cannot_receive_share(db, client):
    sender = _org(db, account_type="ENTERPRISE", name="Sender")
    sender_user = _owner(db, sender, email="sender@x.com")
    creator = Creator(organization_id=sender.id, display_name="Shared")
    db.add(creator); db.commit(); db.refresh(creator)

    recipient = _org(db, account_type="INDIVIDUAL", name="Pro")
    recipient_user = _owner(db, recipient, email="pro@x.com")

    share = ClientShare(
        creator_id=creator.id, primary_org_id=sender.id,
        recipient_user_email="pro@x.com", recipient_org_name_verification="Pro",
        passcode="123456", role="READER", status="PENDING",
        shared_by_user_id=sender_user.id,
    )
    db.add(share); db.commit(); db.refresh(share)

    app.dependency_overrides[get_current_user] = lambda: recipient_user
    try:
        r = client.post(
            f"/api/client-sharing/accept/{share.id}",
            json={"passcode": "123456", "org_name": "Pro"},
        )
        assert r.status_code == 403, f"got {r.status_code}: {r.text[:200]}"
        assert "professional" in r.text.lower()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_professional_cannot_share_to_non_enterprise(db, client):
    sender = _org(db, account_type="INDIVIDUAL", name="ProSender")
    sender_user = _owner(db, sender, email="prosender@x.com")
    creator = Creator(organization_id=sender.id, display_name="MyCatalog")
    db.add(creator); db.commit(); db.refresh(creator)

    # recipient is another Professional org -> not allowed as a target
    recipient = _org(db, account_type="INDIVIDUAL", name="ProRecv")
    _owner(db, recipient, email="prorecv@x.com")

    app.dependency_overrides[get_current_user] = lambda: sender_user
    try:
        r = client.post(
            "/api/client-sharing/share",
            json={
                "creator_id": creator.id,
                "recipient_email": "prorecv@x.com",
                "recipient_org_name": "ProRecv",
                "role": "READER",
                "passcode": "123456",
            },
        )
        assert r.status_code == 403, f"got {r.status_code}: {r.text[:200]}"
        assert "enterprise" in r.text.lower()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_professional_can_share_to_enterprise(db, client):
    sender = _org(db, account_type="INDIVIDUAL", name="ProSender")
    sender_user = _owner(db, sender, email="prosender@x.com")
    creator = Creator(organization_id=sender.id, display_name="MyCatalog")
    db.add(creator); db.commit(); db.refresh(creator)

    recipient = _org(db, account_type="ENTERPRISE", name="EntRecv")
    _owner(db, recipient, email="entrecv@x.com")

    app.dependency_overrides[get_current_user] = lambda: sender_user
    try:
        r = client.post(
            "/api/client-sharing/share",
            json={
                "creator_id": creator.id,
                "recipient_email": "entrecv@x.com",
                "recipient_org_name": "EntRecv",
                "role": "READER",
                "passcode": "123456",
            },
        )
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:200]}"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_accepted_shares_count_toward_capacity(db, client):
    """An Enterprise org with 0 owned creators but at its limit via accepted
    incoming shares must be blocked from accepting one more."""
    recipient = _org(db, account_type="ENTERPRISE", packs=0, name="EntAtLimit")  # limit 10
    recipient_user = _owner(db, recipient, email="recv@x.com")

    sender = _org(db, account_type="ENTERPRISE", name="Sender")
    sender_user = _owner(db, sender, email="snd@x.com")

    # 10 already-accepted incoming shares fill the recipient's roster.
    for i in range(10):
        c = Creator(organization_id=sender.id, display_name=f"S{i}")
        db.add(c); db.commit(); db.refresh(c)
        db.add(ClientShare(
            creator_id=c.id, primary_org_id=sender.id,
            recipient_org_id=recipient.id, recipient_user_email="recv@x.com",
            passcode="123456", role="READER", status="ACCEPTED",
            shared_by_user_id=sender_user.id,
        ))
    db.commit()

    assert pe.count_catalogs(db, recipient.id) == 10

    # One more pending share -> accept should be blocked at capacity.
    extra = Creator(organization_id=sender.id, display_name="Extra")
    db.add(extra); db.commit(); db.refresh(extra)
    pending = ClientShare(
        creator_id=extra.id, primary_org_id=sender.id,
        recipient_user_email="recv@x.com", recipient_org_name_verification="EntAtLimit",
        passcode="123456", role="READER", status="PENDING",
        shared_by_user_id=sender_user.id,
    )
    db.add(pending); db.commit(); db.refresh(pending)

    app.dependency_overrides[get_current_user] = lambda: recipient_user
    try:
        r = client.post(
            f"/api/client-sharing/accept/{pending.id}",
            json={"passcode": "123456", "org_name": "EntAtLimit"},
        )
        assert r.status_code == 403, f"got {r.status_code}: {r.text[:200]}"
        assert "limit of 10" in r.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# ---- entitlement payload on org response -------------------------------------

def test_current_org_response_includes_entitlements(db, client):
    org = _org(db, account_type="ENTERPRISE", packs=1)
    user = _owner(db, org)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.get("/api/organizations/current")
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:200]}"
        body = r.json()
        assert body["plan"] == "ENTERPRISE"
        assert body["plan_label"] == "Enterprise"
        assert body["catalog_limit"] == 15
        assert body["roster_enabled"] is True
        assert body["can_receive_shares"] is True
        assert body["add_on_packs"] == 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
