"""Task #228 — Earnings by track, broken out by source.

Verifies :func:`compute_earnings_by_track` and
:func:`compute_unattributed_earnings`:

  * Earnings aggregate across multiple statements (actual booked net, no
    annualization).
  * Right type is the top-level grouping; issuing source is nested under it.
  * MLC (mechanical) vs ASCAP/BMI (performance) vs DSP (master) lines land
    in distinct right types.
  * Only matched lines feed the per-track table; unmatched revenue is
    surfaced separately via the ``unattributed`` bucket (org-wide only).
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.database import Base
from backend.models.models import (
    Organization,
    RoyaltyStatement,
    RoyaltyStatementLine,
    Song,
)
from backend.services import valuation_engine as ve


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = Session()
    yield session
    session.close()
    engine.dispose()


@pytest.fixture
def org(db):
    o = Organization(name="Earnings By Track Test", type="LABEL")
    db.add(o); db.commit(); db.refresh(o)
    return o


def _make_song(db, org, title, isrc=None):
    s = Song(
        organization_id=org.id,
        title=title,
        primary_artist="Test Artist",
        isrc=isrc,
        release_date=date.today() - timedelta(days=365),
        is_released=True,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s


def _make_statement(db, org, source_type, name=None):
    yr = date.today().year - 1
    st = RoyaltyStatement(
        organization_id=org.id,
        source_name=name or f"{source_type}-{yr}",
        source_type=source_type,
        period_start=date(yr, 1, 1),
        period_end=date(yr, 12, 31),
        currency="USD",
        status="PROCESSED",
    )
    db.add(st); db.commit(); db.refresh(st)
    return st


def _make_line(
    db, org, statement, song, net_dollars,
    platform_source=None, society=None, category=None,
):
    ln = RoyaltyStatementLine(
        org_id=org.id,
        statement_id=statement.id,
        matched_song_id=song.id if song else None,
        net_amount=float(net_dollars),
        net_amount_statement_currency=float(net_dollars),
        canonical_right_category=category,
        platform_source=platform_source,
        society=society,
        match_status="MATCHED" if song else "UNMATCHED",
    )
    db.add(ln); db.commit()
    return ln


def _track(result, song_id):
    for t in result["tracks"]:
        if t["song_id"] == song_id:
            return t
    return None


def _right_type(track, label):
    for rt in track["right_types"]:
        if rt["right_type"] == label:
            return rt
    return None


def test_aggregates_across_multiple_statements(db, org):
    song = _make_song(db, org, "Multi Statement Song")
    st1 = _make_statement(db, org, "MLC", name="MLC-A")
    st2 = _make_statement(db, org, "MLC", name="MLC-B")
    _make_line(db, org, st1, song, 100.0, category="mechanical")
    _make_line(db, org, st2, song, 50.0, category="mechanical")

    result = ve.compute_earnings_by_track(db, org_id=org.id)
    track = _track(result, song.id)
    assert track is not None
    # $150 total = 15000 cents, aggregated across both statements.
    assert track["total_earnings_cents"] == 15_000
    assert track["line_count"] == 2
    assert result["total_attributed_earnings_cents"] == 15_000


def test_right_type_top_level_source_nested(db, org):
    song = _make_song(db, org, "Nested Source Song")
    mlc = _make_statement(db, org, "MLC")
    _make_line(db, org, mlc, song, 80.0, category="mechanical")

    result = ve.compute_earnings_by_track(db, org_id=org.id)
    track = _track(result, song.id)
    mech = _right_type(track, ve.RIGHT_TYPE_MECHANICAL)
    assert mech is not None
    assert mech["earnings_cents"] == 8_000
    # Issuing source nested under the right type.
    assert mech["sources"][0]["source"] == "MLC"
    assert mech["sources"][0]["earnings_cents"] == 8_000


def test_publishing_pro_dsp_separated_into_right_types(db, org):
    song = _make_song(db, org, "Mixed Rights Song")
    mlc = _make_statement(db, org, "MLC")
    ascap = _make_statement(db, org, "ASCAP")
    dsp = _make_statement(db, org, "DSP")
    _make_line(db, org, mlc, song, 100.0, category="mechanical")
    _make_line(db, org, ascap, song, 200.0)  # PRO performance fallback
    _make_line(db, org, dsp, song, 300.0, platform_source="Spotify", category="streaming")

    result = ve.compute_earnings_by_track(db, org_id=org.id)
    track = _track(result, song.id)

    mech = _right_type(track, ve.RIGHT_TYPE_MECHANICAL)
    perf = _right_type(track, ve.RIGHT_TYPE_PERFORMANCE)
    master = _right_type(track, ve.RIGHT_TYPE_MASTER)
    assert mech["earnings_cents"] == 10_000
    assert perf["earnings_cents"] == 20_000
    assert master["earnings_cents"] == 30_000
    # DSP source labelled by the paying platform.
    assert master["sources"][0]["source"] == "Spotify"
    # Catalog rollup carries each right type.
    rollup = {r["right_type"]: r["earnings_cents"] for r in result["catalog_right_type_totals"]}
    assert rollup[ve.RIGHT_TYPE_MECHANICAL] == 10_000
    assert rollup[ve.RIGHT_TYPE_PERFORMANCE] == 20_000
    assert rollup[ve.RIGHT_TYPE_MASTER] == 30_000


def test_only_matched_lines_feed_tracks(db, org):
    song = _make_song(db, org, "Matched Song")
    mlc = _make_statement(db, org, "MLC")
    _make_line(db, org, mlc, song, 100.0, category="mechanical")
    # Unmatched line on the same statement (no song).
    _make_line(db, org, mlc, None, 999.0, category="mechanical")

    result = ve.compute_earnings_by_track(db, org_id=org.id)
    track = _track(result, song.id)
    assert track["total_earnings_cents"] == 10_000
    assert result["total_attributed_earnings_cents"] == 10_000


def test_unattributed_bucket_org_wide_only(db, org):
    song = _make_song(db, org, "Has Match")
    mlc = _make_statement(db, org, "MLC")
    _make_line(db, org, mlc, song, 100.0, category="mechanical")
    _make_line(db, org, mlc, None, 40.0, category="mechanical")

    # Org-wide: unattributed surfaced separately.
    org_wide = ve.compute_earnings_by_track(db, org_id=org.id)
    assert org_wide["unattributed"] is not None
    assert org_wide["unattributed"]["earnings_cents"] == 4_000
    assert org_wide["unattributed"]["line_count"] == 1

    # Scoped to a creator/song set: unattributed not meaningful -> None.
    scoped = ve.compute_earnings_by_track(
        db, org_id=org.id, scope_song_ids=[song.id]
    )
    assert scoped["unattributed"] is None


def test_compute_unattributed_earnings_helper(db, org):
    song = _make_song(db, org, "Matched For Helper")
    mlc = _make_statement(db, org, "MLC")
    _make_line(db, org, mlc, song, 100.0, category="mechanical")
    _make_line(db, org, mlc, None, 25.0, category="mechanical")
    _make_line(db, org, mlc, None, 75.0, category="mechanical")

    cents, count = ve.compute_unattributed_earnings(db, org_id=org.id)
    assert cents == 10_000
    assert count == 2
