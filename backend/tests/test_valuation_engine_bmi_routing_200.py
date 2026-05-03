"""Task #200 — BMI source-typed routing in per-song valuation buckets.

Verifies that the source-typed engine routes BMI lines through the new
``platform_source`` / ``society`` classifiers added in Task #199 Phase 3:

  * BMI line with ``platform_source='SPOTIFY PREM'`` -> streaming bucket.
  * BMI line with ``platform_source='BET'`` -> sync_adjacent bucket.
  * BMI line with ``society='PRS'`` -> international bucket using the
    UK-specific multiplier (9.5x), not the flat 8.0x default.
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
    o = Organization(name="BMI Routing Test", type="LABEL")
    db.add(o); db.commit(); db.refresh(o)
    return o


def _make_song(db, org, title):
    s = Song(
        organization_id=org.id,
        title=title,
        primary_artist="Test",
        release_date=date.today() - timedelta(days=365),
        is_released=True,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s


_BMI_FACTOR = 4  # BMI cadence is quarterly => annualization factor 4x


def _make_bmi_statement(db, org):
    yr = date.today().year - 1
    st = RoyaltyStatement(
        organization_id=org.id,
        source_name=f"BMI-{yr}",
        source_type="BMI",
        period_start=date(yr, 1, 1),
        period_end=date(yr, 3, 31),  # one quarter
        currency="USD",
        status="PROCESSED",
    )
    db.add(st); db.commit(); db.refresh(st)
    return st


def _make_bmi_line(
    db, org, statement, song, net_dollars,
    platform_source=None, society=None, category=None,
):
    ln = RoyaltyStatementLine(
        org_id=org.id,
        statement_id=statement.id,
        matched_song_id=song.id,
        net_amount=float(net_dollars),
        net_amount_statement_currency=float(net_dollars),
        canonical_right_category=category,
        platform_source=platform_source,
        society=society,
        match_status="MATCHED",
    )
    db.add(ln); db.commit()
    return ln


def test_bmi_spotify_line_routes_to_streaming(db, org):
    song = _make_song(db, org, "Spotify Song")
    st = _make_bmi_statement(db, org)
    _make_bmi_line(db, org, st, song, 100.0, platform_source="SPOTIFY PREM")

    bd = ve._compute_song_breakdown(db, song.id)

    expected_rev = 10_000 * _BMI_FACTOR  # $100/qtr * 4 = $400/yr
    assert bd["bucket_revenue_cents"]["streaming"] == expected_rev
    assert bd["bucket_revenue_cents"]["performance"] == 0
    assert bd["bucket_revenue_cents"]["sync_adjacent"] == 0
    assert bd["bucket_revenue_cents"]["international"] == 0
    # streaming multiplier = 12.5
    assert bd["bucket_value_cents"]["streaming"] == int(expected_rev * 12.5)


def test_bmi_bet_cable_line_routes_to_sync_adjacent(db, org):
    song = _make_song(db, org, "BET Song")
    st = _make_bmi_statement(db, org)
    _make_bmi_line(db, org, st, song, 50.0, platform_source="BET")

    bd = ve._compute_song_breakdown(db, song.id)

    expected_rev = 5_000 * _BMI_FACTOR
    assert bd["bucket_revenue_cents"]["sync_adjacent"] == expected_rev
    assert bd["bucket_revenue_cents"]["streaming"] == 0
    assert bd["bucket_revenue_cents"]["performance"] == 0
    # sync_adjacent multiplier = 8.5
    assert bd["bucket_value_cents"]["sync_adjacent"] == int(expected_rev * 8.5)


def test_bmi_prs_society_line_uses_uk_international_multiplier(db, org):
    song = _make_song(db, org, "PRS UK Song")
    st = _make_bmi_statement(db, org)
    _make_bmi_line(db, org, st, song, 200.0, society="PRS")

    bd = ve._compute_song_breakdown(db, song.id)

    expected_rev = 20_000 * _BMI_FACTOR
    assert bd["bucket_revenue_cents"]["international"] == expected_rev
    # PRS = 9.5x (UK), NOT the flat 8.0x default
    assert bd["bucket_value_cents"]["international"] == int(expected_rev * 9.5)
    # Sanity: 8.0x flat would give a different value
    assert bd["bucket_value_cents"]["international"] != int(expected_rev * 8.0)


def test_bmi_unknown_society_falls_back_to_default_multiplier(db, org):
    song = _make_song(db, org, "Unknown PRO")
    st = _make_bmi_statement(db, org)
    _make_bmi_line(db, org, st, song, 100.0, society="ZZTOP")

    bd = ve._compute_song_breakdown(db, song.id)

    expected_rev = 10_000 * _BMI_FACTOR
    assert bd["bucket_revenue_cents"]["international"] == expected_rev
    # DEFAULT = 7.5x
    assert bd["bucket_value_cents"]["international"] == int(expected_rev * 7.5)


def test_bmi_society_takes_precedence_over_platform_source(db, org):
    """A line carrying both society and platform_source is treated as
    international (society wins) — foreign PROs sometimes ride alongside
    a platform_source string from the original BMI section."""
    song = _make_song(db, org, "Both Fields")
    st = _make_bmi_statement(db, org)
    _make_bmi_line(
        db, org, st, song, 100.0,
        platform_source="SPOTIFY PREM", society="GEMA",
    )

    bd = ve._compute_song_breakdown(db, song.id)

    expected_rev = 10_000 * _BMI_FACTOR
    assert bd["bucket_revenue_cents"]["international"] == expected_rev
    assert bd["bucket_revenue_cents"]["streaming"] == 0
    # GEMA = 9.0x
    assert bd["bucket_value_cents"]["international"] == int(expected_rev * 9.0)


def test_mixed_bmi_buckets_aggregate_correctly(db, org):
    """A BMI statement with streaming + cable + foreign society lines on
    the same song aggregates each into its own bucket."""
    song = _make_song(db, org, "Mixed Routing")
    st = _make_bmi_statement(db, org)
    _make_bmi_line(db, org, st, song, 100.0, platform_source="SPOTIFY PREM")
    _make_bmi_line(db, org, st, song, 50.0, platform_source="BET")
    _make_bmi_line(db, org, st, song, 200.0, society="PRS")
    # No platform_source / society -> falls back to BMI->performance
    _make_bmi_line(db, org, st, song, 25.0)

    bd = ve._compute_song_breakdown(db, song.id)

    f = _BMI_FACTOR
    assert bd["bucket_revenue_cents"]["streaming"] == 10_000 * f
    assert bd["bucket_revenue_cents"]["sync_adjacent"] == 5_000 * f
    assert bd["bucket_revenue_cents"]["international"] == 20_000 * f
    assert bd["bucket_revenue_cents"]["performance"] == 2_500 * f

    expected_total_value = (
        int(10_000 * f * 12.5)   # streaming
        + int(5_000 * f * 8.5)   # sync_adjacent
        + int(20_000 * f * 9.5)  # PRS international
        + int(2_500 * f * 10.0)  # performance fallback
    )
    assert bd["total_value_cents"] == expected_total_value


def test_aggregate_summary_includes_new_buckets(db, org):
    """compute_source_typed_valuation rolls up the new buckets in
    its by_bucket summary."""
    song = _make_song(db, org, "Agg Summary")
    st = _make_bmi_statement(db, org)
    _make_bmi_line(db, org, st, song, 50.0, platform_source="BET")
    _make_bmi_line(db, org, st, song, 200.0, society="PRS")

    summary = ve.compute_source_typed_valuation(
        db, org_id=org.id, persist=False,
    )
    f = _BMI_FACTOR
    assert "sync_adjacent" in summary["by_bucket"]
    assert "international" in summary["by_bucket"]
    assert summary["by_bucket"]["sync_adjacent"]["revenue_cents"] == 5_000 * f
    assert summary["by_bucket"]["sync_adjacent"]["value_cents"] == int(5_000 * f * 8.5)
    assert summary["by_bucket"]["international"]["revenue_cents"] == 20_000 * f
    assert summary["by_bucket"]["international"]["value_cents"] == int(20_000 * f * 9.5)


def test_non_bmi_line_unaffected_by_new_routing(db, org):
    """Regression: a non-BMI line with a platform_source / society set
    (shouldn't happen in practice but defensive) must still flow through
    the canonical-right-category mapping, not through BMI classifiers."""
    song = _make_song(db, org, "Generic Line")
    yr = date.today().year - 1
    # GENERIC source_type has no registered cadence -> annualization 1.0
    st = RoyaltyStatement(
        organization_id=org.id,
        source_name=f"GEN-{yr}",
        source_type="GENERIC",
        period_start=date(yr, 1, 1),
        period_end=date(yr, 12, 31),
        currency="USD",
        status="PROCESSED",
    )
    db.add(st); db.commit(); db.refresh(st)
    ln = RoyaltyStatementLine(
        org_id=org.id,
        statement_id=st.id,
        matched_song_id=song.id,
        net_amount=100.0,
        net_amount_statement_currency=100.0,
        canonical_right_category="streaming",
        platform_source="BET",  # would route to sync_adjacent if BMI
        match_status="MATCHED",
    )
    db.add(ln); db.commit()

    bd = ve._compute_song_breakdown(db, song.id)
    # Routed via canonical category, not BMI classifier
    assert bd["bucket_revenue_cents"]["streaming"] == 10_000
    assert bd["bucket_revenue_cents"]["sync_adjacent"] == 0
