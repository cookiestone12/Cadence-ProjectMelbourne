"""Task #227 — Propagate a manual line match to all matching lines in a catalog.

Covers:
  * ISRC auto-propagation cascades a manual match to every same-ISRC line in
    the org, retroactively across older statements.
  * ISWC auto-propagation behaves the same when no ISRC is present.
  * The title+artist tier is a reviewable preview (applied=False) until the
    operator explicitly applies it.
  * Org-scoping: a line in another organization is never touched.
  * Lines already confirmed to a different song, or ignored, are not
    overwritten.
  * Undo reverts a propagation batch, restoring each line's prior state.
"""
from datetime import datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models.database import Base
from backend.models.models import (
    User, Organization, Song,
    RoyaltyStatement, RoyaltyStatementLine,
)
from backend.services.royalty_processing_engine import (
    compute_propagation_key,
    confirm_match,
    apply_confirm_propagation,
    undo_propagation,
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _org(db, name="Org"):
    o = Organization(name=name)
    db.add(o)
    db.flush()
    return o


def _user(db, email):
    u = User(email=email, hashed_password="x")
    db.add(u)
    db.flush()
    return u


def _song(db, org_id, title="Song A", artist="Artist A", isrc=None, iswc=None):
    s = Song(organization_id=org_id, title=title, primary_artist=artist, isrc=isrc, iswc=iswc)
    db.add(s)
    db.flush()
    return s


def _stmt(db, org_id, name="Stmt"):
    st = RoyaltyStatement(organization_id=org_id, source_name=name)
    db.add(st)
    db.flush()
    return st


def _line(db, org_id, stmt_id, **kw):
    defaults = dict(match_status="UNMATCHED", net_amount=1.0)
    defaults.update(kw)
    ln = RoyaltyStatementLine(org_id=org_id, statement_id=stmt_id, **defaults)
    db.add(ln)
    db.flush()
    return ln


# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------

def test_compute_key_is_tiered(db):
    o = _org(db)
    st = _stmt(db, o.id)
    isrc_line = _line(db, o.id, st.id, isrc="us-abc-12-34567", iswc="T123", track_title_raw="X", artist_name_raw="Y")
    assert compute_propagation_key(isrc_line) == ("ISRC", "USABC1234567")

    iswc_line = _line(db, o.id, st.id, iswc="T-123.456.789-0", track_title_raw="X", artist_name_raw="Y")
    assert compute_propagation_key(iswc_line) == ("ISWC", "T1234567890")

    ta_line = _line(db, o.id, st.id, track_title_raw="My Song (feat. Bob)", artist_name_raw="Alice & Bob")
    tier, _ = compute_propagation_key(ta_line)
    assert tier == "TITLE_ARTIST"

    empty = _line(db, o.id, st.id)
    assert compute_propagation_key(empty) is None


# ---------------------------------------------------------------------------
# ISRC auto-propagation, retroactive across statements
# ---------------------------------------------------------------------------

def test_isrc_propagates_across_statements(db):
    o = _org(db)
    u = _user(db, "a@x.com")
    song = _song(db, o.id, isrc="USABC1234567")

    old = _stmt(db, o.id, "old")
    new = _stmt(db, o.id, "new")
    src = _line(db, o.id, new.id, isrc="USABC1234567", track_title_raw="A", artist_name_raw="B")
    other_old = _line(db, o.id, old.id, isrc="us-abc-12-34567")  # same ISRC, punctuation differs
    other_new = _line(db, o.id, new.id, isrc="USABC1234567")
    unrelated = _line(db, o.id, new.id, isrc="USXYZ9999999")

    confirm_match(db, src.id, o.id, song.id, u.id)
    result = apply_confirm_propagation(db, o.id, src.id, song.id, u.id)
    db.flush()

    assert result["applied"] is True
    assert result["tier"] == "ISRC"
    assert result["affected_count"] == 2
    assert result["statements_count"] == 2
    assert result["batch_id"]

    db.refresh(other_old)
    db.refresh(other_new)
    db.refresh(unrelated)
    assert other_old.matched_song_id == song.id and other_old.match_status == "CONFIRMED"
    assert other_new.matched_song_id == song.id
    assert unrelated.matched_song_id is None


def test_iswc_propagation(db):
    o = _org(db)
    u = _user(db, "a@x.com")
    song = _song(db, o.id, iswc="T1234567890")
    st = _stmt(db, o.id)
    src = _line(db, o.id, st.id, iswc="T-123.456.789-0", track_title_raw="A", artist_name_raw="B")
    other = _line(db, o.id, st.id, iswc="T1234567890")

    confirm_match(db, src.id, o.id, song.id, u.id)
    result = apply_confirm_propagation(db, o.id, src.id, song.id, u.id)
    db.flush()

    assert result["tier"] == "ISWC"
    assert result["affected_count"] == 1
    db.refresh(other)
    assert other.matched_song_id == song.id


# ---------------------------------------------------------------------------
# Title+artist is a preview until explicitly applied
# ---------------------------------------------------------------------------

def test_title_artist_is_preview_then_applies(db):
    o = _org(db)
    u = _user(db, "a@x.com")
    song = _song(db, o.id, title="Sunrise", artist="The Band")
    st = _stmt(db, o.id)
    src = _line(db, o.id, st.id, track_title_raw="Sunrise", artist_name_raw="The Band")
    other = _line(db, o.id, st.id, track_title_raw="sunrise", artist_name_raw="the band")

    confirm_match(db, src.id, o.id, song.id, u.id)
    preview = apply_confirm_propagation(db, o.id, src.id, song.id, u.id)
    db.flush()

    assert preview["applied"] is False
    assert preview["tier"] == "TITLE_ARTIST"
    assert preview["affected_count"] == 1
    assert preview["batch_id"] is None
    db.refresh(other)
    assert other.matched_song_id is None  # not yet applied

    applied = apply_confirm_propagation(db, o.id, src.id, song.id, u.id, apply_title_artist=True)
    db.flush()
    assert applied["applied"] is True
    assert applied["affected_count"] == 1
    db.refresh(other)
    assert other.matched_song_id == song.id


# ---------------------------------------------------------------------------
# Org scoping
# ---------------------------------------------------------------------------

def test_no_cross_org_bleed(db):
    o1 = _org(db, "One")
    o2 = _org(db, "Two")
    u = _user(db, "a@x.com")
    song = _song(db, o1.id, isrc="USABC1234567")
    st1 = _stmt(db, o1.id)
    st2 = _stmt(db, o2.id)
    src = _line(db, o1.id, st1.id, isrc="USABC1234567", track_title_raw="A", artist_name_raw="B")
    foreign = _line(db, o2.id, st2.id, isrc="USABC1234567")

    confirm_match(db, src.id, o1.id, song.id, u.id)
    result = apply_confirm_propagation(db, o1.id, src.id, song.id, u.id)
    db.flush()

    assert result["affected_count"] == 0
    db.refresh(foreign)
    assert foreign.matched_song_id is None


# ---------------------------------------------------------------------------
# Don't overwrite confirmed-to-different-song or ignored lines
# ---------------------------------------------------------------------------

def test_does_not_overwrite_confirmed_or_ignored(db):
    o = _org(db)
    u = _user(db, "a@x.com")
    song = _song(db, o.id, isrc="USABC1234567")
    other_song = _song(db, o.id, title="Other", isrc="USOTHER000001")
    st = _stmt(db, o.id)
    src = _line(db, o.id, st.id, isrc="USABC1234567", track_title_raw="A", artist_name_raw="B")
    confirmed_diff = _line(db, o.id, st.id, isrc="USABC1234567",
                           matched_song_id=other_song.id, match_status="CONFIRMED",
                           matched_by_user_id=u.id)
    ignored = _line(db, o.id, st.id, isrc="USABC1234567", match_status="IGNORED")
    plain = _line(db, o.id, st.id, isrc="USABC1234567")

    confirm_match(db, src.id, o.id, song.id, u.id)
    result = apply_confirm_propagation(db, o.id, src.id, song.id, u.id)
    db.flush()

    assert result["affected_count"] == 1  # only `plain`
    db.refresh(confirmed_diff)
    db.refresh(ignored)
    db.refresh(plain)
    assert confirmed_diff.matched_song_id == other_song.id
    assert ignored.match_status == "IGNORED" and ignored.matched_song_id is None
    assert plain.matched_song_id == song.id


# ---------------------------------------------------------------------------
# Undo
# ---------------------------------------------------------------------------

def test_undo_restores_prior_state(db):
    o = _org(db)
    u = _user(db, "a@x.com")
    song = _song(db, o.id, isrc="USABC1234567")
    st = _stmt(db, o.id)
    src = _line(db, o.id, st.id, isrc="USABC1234567", track_title_raw="A", artist_name_raw="B")
    # An auto-matched line to a different song should be restored to that prior state.
    prior_song = _song(db, o.id, title="Prior", isrc="USPRIOR00001")
    auto = _line(db, o.id, st.id, isrc="USABC1234567",
                 matched_song_id=prior_song.id, match_status="AUTO_MATCHED",
                 match_confidence=70.0, match_method="FUZZY")
    fresh = _line(db, o.id, st.id, isrc="USABC1234567")

    confirm_match(db, src.id, o.id, song.id, u.id)
    result = apply_confirm_propagation(db, o.id, src.id, song.id, u.id)
    db.flush()
    assert result["affected_count"] == 2
    batch_id = result["batch_id"]

    undo = undo_propagation(db, o.id, batch_id)
    db.flush()
    assert undo["reverted_count"] == 2

    db.refresh(auto)
    db.refresh(fresh)
    assert auto.matched_song_id == prior_song.id
    assert auto.match_status == "AUTO_MATCHED"
    assert auto.match_confidence == 70.0
    assert auto.propagation_batch_id is None
    assert fresh.matched_song_id is None
    assert fresh.match_status == "UNMATCHED"

    # The user's own source confirmation is untouched by undo.
    db.refresh(src)
    assert src.matched_song_id == song.id and src.match_status == "CONFIRMED"


def test_undo_unknown_batch_raises(db):
    o = _org(db)
    with pytest.raises(ValueError):
        undo_propagation(db, o.id, "does-not-exist")


# ---------------------------------------------------------------------------
# Cross-tenant entity guards
# ---------------------------------------------------------------------------

def test_confirm_rejects_foreign_org_song(db):
    o1 = _org(db, "One")
    o2 = _org(db, "Two")
    u = _user(db, "a@x.com")
    foreign_song = _song(db, o2.id, title="Foreign")
    st = _stmt(db, o1.id)
    line = _line(db, o1.id, st.id, track_title_raw="A", artist_name_raw="B")
    with pytest.raises(ValueError):
        confirm_match(db, line.id, o1.id, foreign_song.id, u.id)


def test_propagate_requires_confirmed_source(db):
    o = _org(db)
    u = _user(db, "a@x.com")
    song = _song(db, o.id, isrc="USABC1234567")
    st = _stmt(db, o.id)
    # Source line is unmatched, never confirmed.
    src = _line(db, o.id, st.id, isrc="USABC1234567", track_title_raw="A", artist_name_raw="B")
    with pytest.raises(ValueError):
        apply_confirm_propagation(db, o.id, src.id, song.id, u.id)


def test_propagate_cannot_retarget_different_song(db):
    o = _org(db)
    u = _user(db, "a@x.com")
    song = _song(db, o.id, isrc="USABC1234567")
    other = _song(db, o.id, title="Other", isrc="USOTHER000001")
    st = _stmt(db, o.id)
    src = _line(db, o.id, st.id, isrc="USABC1234567", track_title_raw="A", artist_name_raw="B")
    confirm_match(db, src.id, o.id, song.id, u.id)
    # Asking to propagate a different song than the source's confirmed song.
    with pytest.raises(ValueError):
        apply_confirm_propagation(db, o.id, src.id, other.id, u.id, apply_title_artist=True)
