"""Task #108 — Credits page N+1 fix.

Asserts that `get_song_stream_summaries` issues a constant number of
queries (<= 2) regardless of how many songs are passed in, and that
its output matches the per-song `get_song_stream_summary` for every
song. This locks in the fix for the Credits tab hang where
`/api/streaming-credits/.../songs` did one StreamEstimate query per
song in the page.
"""
from datetime import date

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models.database import Base
from backend.models.models import Organization, Song, StreamEstimate
from backend.services.stream_estimator import (
    get_song_stream_summary,
    get_song_stream_summaries,
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
Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    s = TestingSessionLocal()
    try:
        yield s
    finally:
        s.close()


def _seed(db, n_songs=70, periods=3):
    org = Organization(name="O", type="LABEL", account_type="ENTERPRISE", display_name="O")
    db.add(org)
    db.flush()

    song_ids = []
    for i in range(n_songs):
        s = Song(organization_id=org.id, title=f"S{i}", primary_artist="A")
        db.add(s)
        db.flush()
        song_ids.append(s.id)

        for p in range(periods):
            for plat in ("SPOTIFY", "APPLE_MUSIC"):
                db.add(StreamEstimate(
                    song_id=s.id,
                    organization_id=org.id,
                    period_date=date(2024, 1 + p, 1),
                    platform=plat,
                    estimated_streams=1000 * (i + 1) * (p + 1),
                    estimation_method="MARKET_SHARE",
                    confidence_score=0.5,
                ))
    db.commit()
    return org.id, song_ids


def _make_query_counter(session):
    counter = {"n": 0}

    @event.listens_for(session.bind, "before_cursor_execute")
    def _count(conn, cursor, statement, parameters, context, executemany):
        s = statement.strip().lower()
        if s.startswith("select") and "stream_estimates" in s:
            counter["n"] += 1

    return counter, _count


def test_bulk_summary_is_constant_query_count(db):
    org_id, song_ids = _seed(db, n_songs=70, periods=3)
    db.expire_all()

    counter, listener = _make_query_counter(db)
    try:
        out = get_song_stream_summaries(song_ids, org_id, db)
    finally:
        event.remove(db.bind, "before_cursor_execute", listener)

    assert len(out) == 70
    # Contract: exactly 1 stream_estimates SELECT — SQLAlchemy compiles the
    # MAX(period_date) subquery inline as a derived table joined against
    # stream_estimates, so the whole bulk fetch is a single round-trip.
    assert counter["n"] == 1, f"bulk summary issued {counter['n']} stream_estimate queries; expected exactly 1"


def test_bulk_matches_per_song(db):
    org_id, song_ids = _seed(db, n_songs=10, periods=2)
    bulk = get_song_stream_summaries(song_ids, org_id, db)
    for sid in song_ids:
        single = get_song_stream_summary(sid, org_id, db)
        b = bulk[sid]
        assert single["total_streams"] == b["total_streams"], f"mismatch for song {sid}"
        assert single["last_updated"] == b["last_updated"]
        assert set(single["platforms"].keys()) == set(b["platforms"].keys())
        for plat, pdata in single["platforms"].items():
            assert pdata["streams"] == b["platforms"][plat]["streams"]


def test_bulk_handles_missing_song(db):
    org_id, song_ids = _seed(db, n_songs=3, periods=1)
    out = get_song_stream_summaries(song_ids + [99999], org_id, db)
    assert out[99999] == {"total_streams": 0, "platforms": {}, "confidence": 0}


def test_bulk_handles_empty(db):
    assert get_song_stream_summaries([], 1, db) == {}
    assert get_song_stream_summaries(None, 1, db) == {}


def test_bulk_isolates_by_org(db):
    org_id, song_ids = _seed(db, n_songs=2, periods=1)
    other = Organization(name="X", type="LABEL", account_type="ENTERPRISE", display_name="X")
    db.add(other); db.commit()
    out = get_song_stream_summaries(song_ids, other.id, db)
    for sid in song_ids:
        assert out[sid]["total_streams"] == 0
