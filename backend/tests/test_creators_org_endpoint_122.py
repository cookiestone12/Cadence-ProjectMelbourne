"""Task #122 — Regression guard for the Valuation page Scope dropdown.

The Valuation page calls `GET /api/creators/org/{org_id}` to populate the
"Scope" picker. The bug was that the page previously called
`GET /api/creators/{org_id}`, which actually hits the single-creator detail
route (`/api/creators/{creator_id}`) and returns either 404 or a single
object — collapsing `Array.isArray(...)` to false and silently producing an
empty dropdown for every org.

These tests pin the contract the dropdown depends on:
  * The org-roster route returns a JSON ARRAY (not an object).
  * It returns one entry per creator (org with 0/1/many).
  * The single-creator route is NOT a substitute (different path, different shape).
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
from backend.utils.auth import get_current_user, get_password_hash as hash_password


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


def _seed(db, num_creators):
    org = Organization(name="O", type="LABEL", account_type="ENTERPRISE", display_name="O")
    db.add(org); db.commit(); db.refresh(org)
    user = User(username="u", email="u@x.com", hashed_password=hash_password("x"), is_active=True)
    db.add(user); db.commit(); db.refresh(user)
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="OWNER"))
    db.commit()

    # Names chosen so default sort puts them out of insertion order — verifies
    # the frontend doesn't have to rely on backend ordering for the dropdown.
    names = ["Zed Writer", "Mary Jordan", "Alice Producer"][:num_creators]
    for name in names:
        db.add(Creator(organization_id=org.id, display_name=name, roles=["WRITER"]))
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    return org, user


@pytest.mark.parametrize("n_creators", [0, 1, 3])
def test_org_creators_route_returns_array(client, n_creators):
    db, c = client
    org, _ = _seed(db, n_creators)

    r = c.get(f"/api/creators/org/{org.id}")
    assert r.status_code == 200, r.text
    payload = r.json()

    # Critical: must be a JSON array. The dropdown branches on
    # Array.isArray(...) — anything else collapses to an empty list.
    assert isinstance(payload, list), f"expected list, got {type(payload).__name__}"
    assert len(payload) == n_creators

    for entry in payload:
        # Dropdown labels off display_name; an entry without one would render
        # as "Creator #N" — acceptable, but every seeded creator has a name.
        assert "id" in entry
        assert "display_name" in entry


def test_singleton_creator_route_is_not_a_substitute(client):
    """The buggy ValuationPage URL `/api/creators/{org_id}` actually resolves
    to the singleton-detail route. This test pins the shape difference so
    nobody accidentally re-introduces the URL collision."""
    db, c = client
    org, _ = _seed(db, 1)
    creator = db.query(Creator).filter_by(organization_id=org.id).first()

    # Hitting /api/creators/{creator_id} returns a single object, NOT a list.
    r = c.get(f"/api/creators/{creator.id}")
    assert r.status_code == 200, r.text
    payload = r.json()
    assert isinstance(payload, dict)
    assert payload["id"] == creator.id
