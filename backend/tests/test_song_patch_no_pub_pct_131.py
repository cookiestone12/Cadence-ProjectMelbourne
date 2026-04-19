"""Task #131 — Records inline edit save must succeed.

Pins the contract that PATCH /api/songs/{id} from the Roster -> Records
inline editor (which no longer sends pub/master percentage) returns 200,
and that the read-only-fields guard still rejects payloads that DO send
those fields.
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
from backend.utils.auth import get_current_user, get_password_hash


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
def env():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    def _override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db
    try:
        yield db, TestClient(app)
    finally:
        app.dependency_overrides.clear()
        db.close()


def _seed(db):
    org = Organization(name="O", type="LABEL", account_type="ENTERPRISE", display_name="O")
    db.add(org); db.commit(); db.refresh(org)

    user = User(
        username="u", email="u@x.com", hashed_password=get_password_hash("x"),
        is_active=True,
    )
    db.add(user); db.commit(); db.refresh(user)
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="OWNER"))

    creator = Creator(organization_id=org.id, display_name="MJ Jordan", roles=["WRITER"])
    db.add(creator); db.commit(); db.refresh(creator)

    song = Song(
        organization_id=org.id, title="Old Title", primary_artist="MJ Jordan",
        is_released=False, status_health_score=0.0,
    )
    db.add(song); db.commit(); db.refresh(song)
    return org, user, creator, song


def test_patch_song_without_pub_master_succeeds(env):
    """The inline editor's new payload shape (no pub/master pct) returns 200
    and applies the requested updates."""
    db, c = env
    _, user, _, song = _seed(db)
    app.dependency_overrides[get_current_user] = lambda: user

    payload = {
        "title": "New Title",
        "primary_artist": "MJ Jordan",
        "is_released": True,
        "spotify_link": "https://open.spotify.com/track/abc",
        "label": "Acme Records",
        "is_registered_with_pro": True,
    }
    r = c.patch(f"/api/songs/{song.id}", json=payload)
    assert r.status_code == 200, r.text

    db.expire_all()
    refreshed = db.query(Song).filter(Song.id == song.id).one()
    assert refreshed.title == "New Title"
    assert refreshed.is_released is True
    assert refreshed.spotify_link == "https://open.spotify.com/track/abc"
    assert refreshed.label == "Acme Records"


def test_patch_song_with_pub_pct_still_rejected(env):
    """Read-only guard remains: sending pub/master pct returns 400."""
    db, c = env
    _, user, _, song = _seed(db)
    app.dependency_overrides[get_current_user] = lambda: user

    r = c.patch(
        f"/api/songs/{song.id}",
        json={"title": "X", "publishing_percentage": 50},
    )
    assert r.status_code == 400, r.text
    assert "read-only" in r.json()["detail"].lower()
