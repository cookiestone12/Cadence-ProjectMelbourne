"""Task #171 — Phase 4 tests for the lazy auto-release service.

Verifies that ``backend.services.song_lifecycle.auto_release_songs``:

* flips a song whose ``release_date`` has already passed and which is
  currently ``is_released=False`` to ``is_released=True``,
  ``release_status='released'``;
* does NOT touch a song whose ``release_date`` is in the future;
* does NOT touch a song whose ``release_date`` is NULL;
* respects the optional ``organization_id`` scope so a flip in org A does
  not bleed into org B;
* is idempotent — calling it again on a steady-state catalog returns 0.
"""

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.database import Base
from backend.models.models import Organization, Song
from backend.services.song_lifecycle import auto_release_songs


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture()
def db():
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    s = TestingSessionLocal()
    try:
        yield s
    finally:
        s.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def _make_org(db, name="Test Org"):
    org = Organization(name=name)
    db.add(org)
    db.flush()
    return org


def _make_song(db, org_id, *, release_date, is_released=False, release_status="unreleased", title="Track"):
    song = Song(
        organization_id=org_id,
        title=title,
        primary_artist="Test",
        release_date=release_date,
        is_released=is_released,
        release_status=release_status,
    )
    db.add(song)
    db.flush()
    return song


def test_flips_song_with_past_release_date(db):
    org = _make_org(db)
    today = date(2026, 5, 1)
    song = _make_song(db, org.id, release_date=today - timedelta(days=1))

    updated = auto_release_songs(db, organization_id=org.id, today=today)

    assert updated == 1
    db.refresh(song)
    assert song.is_released is True
    assert song.release_status == "released"


def test_flips_song_released_today(db):
    """release_date == today should also flip (boundary)."""
    org = _make_org(db)
    today = date(2026, 5, 1)
    song = _make_song(db, org.id, release_date=today)

    updated = auto_release_songs(db, organization_id=org.id, today=today)

    assert updated == 1
    db.refresh(song)
    assert song.is_released is True
    assert song.release_status == "released"


def test_does_not_flip_future_release(db):
    org = _make_org(db)
    today = date(2026, 5, 1)
    song = _make_song(db, org.id, release_date=today + timedelta(days=1))

    updated = auto_release_songs(db, organization_id=org.id, today=today)

    assert updated == 0
    db.refresh(song)
    assert song.is_released is False
    assert song.release_status == "unreleased"


def test_does_not_flip_null_release_date(db):
    org = _make_org(db)
    today = date(2026, 5, 1)
    song = _make_song(db, org.id, release_date=None)

    updated = auto_release_songs(db, organization_id=org.id, today=today)

    assert updated == 0
    db.refresh(song)
    assert song.is_released is False


def test_does_not_re_flip_already_released(db):
    org = _make_org(db)
    today = date(2026, 5, 1)
    song = _make_song(
        db,
        org.id,
        release_date=today - timedelta(days=10),
        is_released=True,
        release_status="released",
    )

    updated = auto_release_songs(db, organization_id=org.id, today=today)

    assert updated == 0
    db.refresh(song)
    assert song.is_released is True
    assert song.release_status == "released"


def test_org_scope_does_not_bleed(db):
    org_a = _make_org(db, name="A")
    org_b = _make_org(db, name="B")
    today = date(2026, 5, 1)
    song_a = _make_song(db, org_a.id, release_date=today - timedelta(days=1), title="A-track")
    song_b = _make_song(db, org_b.id, release_date=today - timedelta(days=1), title="B-track")

    updated = auto_release_songs(db, organization_id=org_a.id, today=today)

    assert updated == 1
    db.refresh(song_a)
    db.refresh(song_b)
    assert song_a.is_released is True
    assert song_b.is_released is False, "Org scope should isolate the flip to org A only"


def test_no_org_filter_flips_across_orgs(db):
    """The ``organization_id=None`` form is used by the legacy catalog endpoint."""
    org_a = _make_org(db, name="A")
    org_b = _make_org(db, name="B")
    today = date(2026, 5, 1)
    song_a = _make_song(db, org_a.id, release_date=today - timedelta(days=1), title="A-track")
    song_b = _make_song(db, org_b.id, release_date=today - timedelta(days=2), title="B-track")

    updated = auto_release_songs(db, today=today)

    assert updated == 2
    db.refresh(song_a)
    db.refresh(song_b)
    assert song_a.is_released is True
    assert song_b.is_released is True


def test_idempotent_second_call_returns_zero(db):
    org = _make_org(db)
    today = date(2026, 5, 1)
    _make_song(db, org.id, release_date=today - timedelta(days=1))

    first = auto_release_songs(db, organization_id=org.id, today=today)
    second = auto_release_songs(db, organization_id=org.id, today=today)

    assert first == 1
    assert second == 0


def test_flip_persists_across_new_session():
    """Regression for the bug where the helper flushed but never committed.

    Architects flagged that GET handlers don't commit themselves, so the
    flush-only flip would be rolled back when the request session closed.
    This test creates the helper's update in one session, then opens a
    *new* session and re-reads the song to confirm the flip survived.
    """
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    today = date(2026, 5, 1)
    s1 = TestingSessionLocal()
    try:
        org = Organization(name="Persist Test")
        s1.add(org)
        s1.flush()
        song = Song(
            organization_id=org.id,
            title="Persist Track",
            primary_artist="X",
            release_date=today - timedelta(days=1),
            is_released=False,
            release_status="unreleased",
        )
        s1.add(song)
        s1.commit()
        song_id = song.id
        org_id = org.id

        updated = auto_release_songs(s1, organization_id=org_id, today=today)
        assert updated == 1
    finally:
        s1.close()

    s2 = TestingSessionLocal()
    try:
        reloaded = s2.query(Song).filter(Song.id == song_id).first()
        assert reloaded is not None
        assert reloaded.is_released is True, (
            "Flip should persist after the session closes — it does not "
            "if the helper only flushes without committing."
        )
        assert reloaded.release_status == "released"
    finally:
        s2.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
