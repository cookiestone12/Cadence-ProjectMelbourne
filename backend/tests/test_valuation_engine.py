"""Phase 5 Valuation Engine tests (Task #172).

Covers:
  * Income engine bucket math + multipliers (via _compute_song_breakdown).
  * Market-comparable: tier band selection, ownership %, no-data path.
  * DCF: monotonic discount, terminal value, growth-rate clamping.
  * Blended weights = 0.4 income + 0.3 market + 0.3 dcf.
  * Per-creator scope correctly restricts the song set.
  * Catalog aggregation: sum of per-song = catalog total.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models.database import Base
from backend.models.models import (
    Contract,
    ContractAsset,
    Creator,
    Organization,
    RightsSplit,
    RoyaltyStatement,
    RoyaltyStatementLine,
    Song,
    SongCredit,
    SongStreamingMetrics,
    ValuationCalculation,
)
from backend.services import valuation_engine as ve


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

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
    o = Organization(name="Test Label", type="LABEL")
    db.add(o); db.commit(); db.refresh(o)
    return o


@pytest.fixture
def creator_a(db, org):
    c = Creator(organization_id=org.id, display_name="Alice")
    db.add(c); db.commit(); db.refresh(c)
    return c


@pytest.fixture
def creator_b(db, org):
    c = Creator(organization_id=org.id, display_name="Bob")
    db.add(c); db.commit(); db.refresh(c)
    return c


def _make_song(db, org, title, primary_artist="Test", release_years_ago=2):
    s = Song(
        organization_id=org.id,
        title=title,
        primary_artist=primary_artist,
        release_date=date.today() - timedelta(days=int(365.25 * release_years_ago)),
        is_released=True,
    )
    db.add(s); db.commit(); db.refresh(s)
    return s


def _make_statement(db, org, source_type="GENERIC", year=None):
    yr = year or (date.today().year - 1)
    st = RoyaltyStatement(
        organization_id=org.id,
        source_name=f"{source_type}-{yr}",
        source_type=source_type,
        period_start=date(yr, 1, 1),
        period_end=date(yr, 12, 31),
        currency="USD",
        status="PROCESSED",
    )
    db.add(st); db.commit(); db.refresh(st)
    return st


def _make_line(db, org, statement, song, net_dollars, category="streaming"):
    ln = RoyaltyStatementLine(
        org_id=org.id,
        statement_id=statement.id,
        matched_song_id=song.id,
        net_amount=float(net_dollars),
        net_amount_statement_currency=float(net_dollars),
        canonical_right_category=category,
        match_status="MATCHED",
    )
    db.add(ln); db.commit()
    return ln


# ---------------------------------------------------------------------------
# Income engine — bucket math
# ---------------------------------------------------------------------------

def test_income_bucket_math_streaming(db, org):
    song = _make_song(db, org, "Stream Hit")
    st = _make_statement(db, org, source_type="GENERIC")  # annual factor = 1
    _make_line(db, org, st, song, 1000.0, category="streaming")
    _make_line(db, org, st, song, 500.0, category="streaming")

    bd = ve._compute_song_breakdown(db, song.id)
    # Annual revenue = sum of lines × annualization factor (1.0 for annual DSP)
    assert bd["total_annual_revenue_cents"] == 150_000  # $1500 in cents
    # Streaming bucket × 12.5 multiplier
    assert bd["bucket_value_cents"]["streaming"] == int(150_000 * 12.5)
    # Total catalog value cents = streaming * 12.5
    assert bd["total_value_cents"] == int(150_000 * 12.5)


def test_income_multiple_buckets(db, org):
    song = _make_song(db, org, "Multi Bucket")
    st = _make_statement(db, org, source_type="GENERIC")
    _make_line(db, org, st, song, 100.0, category="performance")
    _make_line(db, org, st, song, 200.0, category="mechanical")
    _make_line(db, org, st, song, 50.0, category="sync")
    _make_line(db, org, st, song, 1000.0, category="streaming")

    bd = ve._compute_song_breakdown(db, song.id)
    expected = (
        int(100 * 100 * 10.0)   # performance × 10
        + int(200 * 100 * 9.0)  # mechanical × 9
        + int(50 * 100 * 7.0)   # sync × 7
        + int(1000 * 100 * 12.5)  # streaming × 12.5
    )
    assert bd["total_value_cents"] == expected


# ---------------------------------------------------------------------------
# Market-comparable engine
# ---------------------------------------------------------------------------

def test_market_comparable_no_data(db, org):
    song = _make_song(db, org, "Quiet Song")
    res = ve.market_comparable_valuation(db, song.id)
    assert res["has_data"] is False
    assert res["value_base"] == 0.0


def test_market_comparable_indie_tier(db, org):
    # 50,000 streams over 2 years => 25,000/year  → indie tier
    song = _make_song(db, org, "Indie Track", release_years_ago=2)
    sm = SongStreamingMetrics(
        song_id=song.id, organization_id=org.id,
        period_date=date.today(), total_streams=50_000,
        ownership_percentage=100.0,
    )
    db.add(sm); db.commit()
    res = ve.market_comparable_valuation(db, song.id)
    assert res["has_data"] is True
    assert res["tier"] == "indie"
    # 25,000 streams × $0.035 (indie mid) × 1.0 ownership × 10× multiplier = $8,750
    assert res["value_base"] == pytest.approx(25_000 * 0.035 * 10.0, rel=0.001)


def test_market_comparable_premium_tier(db, org):
    # 4,000,000 streams / 2 yrs => 2,000,000/year → premium
    song = _make_song(db, org, "Hit Track", release_years_ago=2)
    sm = SongStreamingMetrics(
        song_id=song.id, organization_id=org.id,
        period_date=date.today(), total_streams=4_000_000,
        ownership_percentage=50.0,  # Half ownership
    )
    db.add(sm); db.commit()
    res = ve.market_comparable_valuation(db, song.id)
    assert res["tier"] == "premium"
    # 2,000,000 × 0.150 × 0.5 × 10 = $1,500,000
    assert res["value_base"] == pytest.approx(2_000_000 * 0.150 * 0.5 * 10.0, rel=0.001)
    # Ownership reflected
    assert res["ownership_pct"] == pytest.approx(50.0)


def test_market_comparable_tier_band_constants():
    # Spec sanity: indie 0.020-0.050, mid 0.050-0.100, premium 0.100-0.200
    assert ve._TIER_BANDS["indie"][0] == 0.020 and ve._TIER_BANDS["indie"][2] == 0.050
    assert ve._TIER_BANDS["mid"][0] == 0.050 and ve._TIER_BANDS["mid"][2] == 0.100
    assert ve._TIER_BANDS["premium"][0] == 0.100 and ve._TIER_BANDS["premium"][2] == 0.200


# ---------------------------------------------------------------------------
# DCF engine
# ---------------------------------------------------------------------------

def test_dcf_no_data(db, org):
    song = _make_song(db, org, "No History")
    res = ve.dcf_valuation(db, song.id)
    assert res["has_data"] is False
    assert res["value_base"] == 0.0


def test_dcf_three_year_history_pv_and_terminal(db, org):
    # Three years of declining annual revenue → flat/contracting growth.
    song = _make_song(db, org, "DCF Test", release_years_ago=4)
    cur_year = date.today().year
    for i, amt in enumerate([1000.0, 800.0, 600.0]):  # declining
        st = _make_statement(db, org, source_type="GENERIC", year=cur_year - 3 + i)
        _make_line(db, org, st, song, amt, category="streaming")

    res = ve.dcf_valuation(db, song.id, discount_rate=0.10, projection_years=10, terminal_growth_rate=0.02)
    assert res["has_data"] is True
    # Year-0 = most recent observed = 600
    assert res["year_0_revenue"] == 600.0
    # PV-cashflows < 10 × year_0 (because of declining growth + discount)
    assert res["pv_cash_flows"] < 6000.0
    # Has 10 projection rows, monotonic decline (negative growth)
    assert len(res["projections"]) == 10
    nets = [p["projected_net"] for p in res["projections"]]
    assert all(nets[i] >= nets[i + 1] for i in range(len(nets) - 1))
    # Terminal value present and discounted
    assert res["terminal_value"] > 0
    assert res["pv_terminal"] < res["terminal_value"]
    # Total = pv_sum + pv_terminal
    assert res["value_base"] == pytest.approx(res["pv_cash_flows"] + res["pv_terminal"], rel=0.001)
    # Low/high band ±20%
    assert res["value_low"] == pytest.approx(res["value_base"] * 0.80, rel=0.001)
    assert res["value_high"] == pytest.approx(res["value_base"] * 1.20, rel=0.001)


def test_dcf_higher_discount_lowers_pv(db, org):
    """PV is monotonically decreasing in the discount rate."""
    song = _make_song(db, org, "Mono Disc")
    cur_year = date.today().year
    for i, amt in enumerate([1000.0, 1000.0, 1000.0]):
        st = _make_statement(db, org, source_type="GENERIC", year=cur_year - 3 + i)
        _make_line(db, org, st, song, amt, category="streaming")

    low_disc = ve.dcf_valuation(db, song.id, discount_rate=0.05)
    high_disc = ve.dcf_valuation(db, song.id, discount_rate=0.20)
    assert low_disc["value_base"] > high_disc["value_base"]


# ---------------------------------------------------------------------------
# Blended weights
# ---------------------------------------------------------------------------

def test_blend_weights_sum_to_one():
    s = sum(ve._BLEND_WEIGHTS.values())
    assert abs(s - 1.0) < 1e-9
    assert ve._BLEND_WEIGHTS["income"] == 0.40
    assert ve._BLEND_WEIGHTS["market_comparable"] == 0.30
    assert ve._BLEND_WEIGHTS["dcf"] == 0.30


def test_full_valuation_blend_formula(db, org):
    song = _make_song(db, org, "Blend Test", release_years_ago=2)
    cur_year = date.today().year
    st = _make_statement(db, org, source_type="GENERIC", year=cur_year - 1)
    _make_line(db, org, st, song, 500.0, category="streaming")
    sm = SongStreamingMetrics(
        song_id=song.id, organization_id=org.id,
        period_date=date.today(), total_streams=200_000,
        ownership_percentage=100.0,
    )
    db.add(sm); db.commit()

    fv = ve.full_valuation(db, song.id)
    expected_blended = (
        fv["income"]["value_base"] * 0.40
        + fv["market_comparable"]["value_base"] * 0.30
        + fv["dcf"]["value_base"] * 0.30
    )
    assert fv["blended"]["value_base"] == pytest.approx(expected_blended, rel=1e-6)
    assert fv["blended"]["weights"] == ve._BLEND_WEIGHTS


# ---------------------------------------------------------------------------
# Per-creator scope
# ---------------------------------------------------------------------------

def test_per_creator_scope_filters_song_set(db, org, creator_a, creator_b):
    s1 = _make_song(db, org, "Alice Song 1")
    s2 = _make_song(db, org, "Alice Song 2")
    s3 = _make_song(db, org, "Bob Song")
    db.add_all([
        SongCredit(song_id=s1.id, creator_id=creator_a.id, role="ARTIST", share_percentage=100.0),
        SongCredit(song_id=s2.id, creator_id=creator_a.id, role="ARTIST", share_percentage=100.0),
        SongCredit(song_id=s3.id, creator_id=creator_b.id, role="ARTIST", share_percentage=100.0),
    ])
    db.commit()

    alice_ids = ve._resolve_song_ids(db, org_id=org.id, scope_creator_id=creator_a.id)
    assert sorted(alice_ids) == sorted([s1.id, s2.id])

    bob_ids = ve._resolve_song_ids(db, org_id=org.id, scope_creator_id=creator_b.id)
    assert bob_ids == [s3.id]

    org_ids = ve._resolve_song_ids(db, org_id=org.id)
    assert sorted(org_ids) == sorted([s1.id, s2.id, s3.id])


# ---------------------------------------------------------------------------
# Catalog aggregation: sum of per-song = catalog total
# ---------------------------------------------------------------------------

def test_catalog_aggregation_equals_per_song_sum(db, org, creator_a):
    s1 = _make_song(db, org, "Cat Song 1")
    s2 = _make_song(db, org, "Cat Song 2")
    db.add_all([
        SongCredit(song_id=s1.id, creator_id=creator_a.id, role="ARTIST", share_percentage=100.0),
        SongCredit(song_id=s2.id, creator_id=creator_a.id, role="ARTIST", share_percentage=100.0),
    ])
    cur_year = date.today().year
    st = _make_statement(db, org, source_type="GENERIC", year=cur_year - 1)
    _make_line(db, org, st, s1, 100.0, category="streaming")
    _make_line(db, org, st, s2, 200.0, category="performance")
    db.commit()

    catalog = ve.compute_full_catalog_valuation(db, org_id=org.id, persist=False)
    fv1 = ve.full_valuation(db, s1.id)
    fv2 = ve.full_valuation(db, s2.id)

    expected_blended_base = fv1["blended"]["value_base"] + fv2["blended"]["value_base"]
    expected_income_base = fv1["income"]["value_base"] + fv2["income"]["value_base"]
    assert catalog["by_methodology"]["blended"]["base"] == pytest.approx(expected_blended_base, rel=1e-6)
    assert catalog["by_methodology"]["income"]["base"] == pytest.approx(expected_income_base, rel=1e-6)
    assert catalog["song_count"] == 2


def test_catalog_aggregation_persists_blended_rows(db, org):
    s1 = _make_song(db, org, "Persist Song")
    cur_year = date.today().year
    st = _make_statement(db, org, source_type="GENERIC", year=cur_year - 1)
    _make_line(db, org, st, s1, 100.0, category="streaming")

    ve.compute_full_catalog_valuation(db, org_id=org.id, persist=True)
    db.commit()  # The route handler commits — replicate that here.

    rows = db.query(ValuationCalculation).filter(ValuationCalculation.song_id == s1.id).all()
    assert len(rows) == 1
    row = rows[0]
    assert row.valuation_method == "BLENDED"
    assert row.valuation_methodology == "BLENDED"
    # All four legs persisted
    assert row.revenue_multiple_value_cents > 0  # income
    assert row.black_box_value_cents > 0  # DCF projects from 1-yr base + terminal growth
    assert row.final_valuation_cents > 0  # blended
    # Blended ≈ 0.4*income + 0.3*market(0) + 0.3*dcf
    expected_blended = int(round(
        0.40 * (row.revenue_multiple_value_cents / 100)
        + 0.30 * (row.streaming_multiple_value_cents / 100)
        + 0.30 * (row.black_box_value_cents / 100)
    ) * 100)
    assert abs(row.final_valuation_cents - expected_blended) < 100  # ≤ $1 rounding diff
    assert row.organization_id == org.id


def test_catalog_per_creator_scope_only_sums_credited(db, org, creator_a, creator_b):
    s1 = _make_song(db, org, "Alice Only")
    s2 = _make_song(db, org, "Bob Only")
    db.add_all([
        SongCredit(song_id=s1.id, creator_id=creator_a.id, role="ARTIST", share_percentage=100.0),
        SongCredit(song_id=s2.id, creator_id=creator_b.id, role="ARTIST", share_percentage=100.0),
    ])
    cur_year = date.today().year
    st = _make_statement(db, org, source_type="GENERIC", year=cur_year - 1)
    _make_line(db, org, st, s1, 100.0, category="streaming")
    _make_line(db, org, st, s2, 999.0, category="streaming")
    db.commit()

    alice_cat = ve.compute_full_catalog_valuation(db, org_id=org.id, scope_creator_id=creator_a.id, persist=False)
    bob_cat = ve.compute_full_catalog_valuation(db, org_id=org.id, scope_creator_id=creator_b.id, persist=False)

    assert alice_cat["song_count"] == 1
    assert bob_cat["song_count"] == 1
    # Income leg differs because Bob's song earns ~10× Alice's
    assert bob_cat["by_methodology"]["income"]["base"] > alice_cat["by_methodology"]["income"]["base"] * 5


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def test_confidence_score_buckets():
    low = ve._confidence_score(False, False, 0)
    mid = ve._confidence_score(True, False, 0)  # 1/3 ≈ 0.333 → 'medium'
    high = ve._confidence_score(True, True, 3)
    assert low["label"] == "low" and low["score"] == 0.0
    assert mid["label"] == "medium" and mid["score"] == pytest.approx(1 / 3, rel=1e-2)
    assert high["label"] == "high" and high["score"] == 1.0


# ---------------------------------------------------------------------------
# Post-review regression tests
# ---------------------------------------------------------------------------


def test_market_comparable_explicit_zero_ownership_returns_zero(db, org):
    """Regression: explicit 0% ownership must NOT default to 100%."""
    s = _make_song(db, org, "Zero Owned", release_years_ago=2)
    metric = SongStreamingMetrics(
        song_id=s.id, organization_id=org.id,
        period_date=date.today(), total_streams=1_000_000,
        ownership_percentage=0.0,  # explicit zero
    )
    db.add(metric)
    db.commit()
    result = ve.market_comparable_valuation(db, s.id)
    assert result["value_base"] == 0.0
    assert result["ownership_pct"] == 0.0


def test_per_creator_share_emits_share_pct_and_blended_base_aliases(db, org, creator_a, creator_b):
    """Regression: frontend reads c.blended_base + c.share_pct."""
    s1 = _make_song(db, org, "Alpha")
    s2 = _make_song(db, org, "Bravo")
    db.add_all([
        SongCredit(song_id=s1.id, creator_id=creator_a.id, role="ARTIST", share_percentage=100.0),
        SongCredit(song_id=s2.id, creator_id=creator_b.id, role="ARTIST", share_percentage=100.0),
    ])
    cur_year = date.today().year
    st = _make_statement(db, org, source_type="GENERIC", year=cur_year - 1)
    _make_line(db, org, st, s1, 100.0, category="streaming")
    _make_line(db, org, st, s2, 300.0, category="streaming")
    db.commit()

    summary = ve.compute_full_catalog_valuation(db, org_id=org.id, persist=False)
    pcs = summary["per_creator_share"]
    assert len(pcs) == 2
    for row in pcs:
        assert "blended_value" in row
        assert "blended_base" in row
        assert "share_pct" in row
        assert row["blended_base"] == row["blended_value"]
        assert 0.0 <= row["share_pct"] <= 100.0
    # Shares should sum to ~100% (each song has exactly 1 credit).
    assert abs(sum(r["share_pct"] for r in pcs) - 100.0) < 0.5


def test_persisted_blended_row_carries_scope_metadata(db, org, creator_a):
    """Regression: persisted rows must carry scope tag so /full/trend can
    distinguish org-wide snapshots from creator-scoped subset snapshots."""
    s1 = _make_song(db, org, "Scoped Song")
    db.add(SongCredit(song_id=s1.id, creator_id=creator_a.id, role="ARTIST", share_percentage=100.0))
    cur_year = date.today().year
    st = _make_statement(db, org, source_type="GENERIC", year=cur_year - 1)
    _make_line(db, org, st, s1, 250.0, category="streaming")
    db.commit()

    # Org-wide run
    ve.compute_full_catalog_valuation(db, org_id=org.id, persist=True)
    db.commit()
    # Creator-scoped run
    ve.compute_full_catalog_valuation(db, org_id=org.id, scope_creator_id=creator_a.id, persist=True)
    db.commit()

    rows = db.query(ValuationCalculation).filter(
        ValuationCalculation.song_id == s1.id,
        ValuationCalculation.valuation_method == "BLENDED",
    ).order_by(ValuationCalculation.calculation_date.asc()).all()
    assert len(rows) == 2

    org_row, scoped_row = rows
    assert (org_row.calc_metadata or {}).get("scope_mode") == "org"
    assert (org_row.calc_metadata or {}).get("scope_creator_id") is None
    assert (scoped_row.calc_metadata or {}).get("scope_mode") == "creator"
    assert (scoped_row.calc_metadata or {}).get("scope_creator_id") == creator_a.id


# ---------------------------------------------------------------------------
# RightsSplit-weighted per-creator attribution
# ---------------------------------------------------------------------------


def _attach_rights(db, song, splits):
    """Helper: create a Contract + ContractAsset + RightsSplit rows for `song`.

    `splits` is a list of (creator, share_pct, rights_type) tuples.
    """
    contract = Contract(
        organization_id=song.organization_id,
        title=f"Rights for {song.title}",
        contract_type="OTHER",
        status="ACTIVE",
    )
    db.add(contract)
    db.flush()
    asset = ContractAsset(
        contract_id=contract.id,
        asset_type="SONG",
        asset_id=song.id,
    )
    db.add(asset)
    db.flush()
    for creator, pct, rights_type in splits:
        db.add(RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=creator.id,
            rights_holder_name=creator.display_name,
            rights_type=rights_type,
            share_percentage=pct,
        ))
    db.commit()


def test_per_creator_share_uses_rightssplit_unequal_shares(db, org, creator_a, creator_b):
    """RightsSplit-weighted attribution must reflect unequal shares.

    Equal-split SongCredit would give 50/50; with a 70/30 RightsSplit the
    creators' blended_value must follow 70/30 instead.
    """
    s = _make_song(db, org, "Shared Song", release_years_ago=1)
    db.add_all([
        SongCredit(song_id=s.id, creator_id=creator_a.id, role="ARTIST", share_percentage=70.0),
        SongCredit(song_id=s.id, creator_id=creator_b.id, role="ARTIST", share_percentage=30.0),
    ])
    cur_year = date.today().year
    st = _make_statement(db, org, source_type="GENERIC", year=cur_year - 1)
    _make_line(db, org, st, s, 1000.0, category="streaming")
    _attach_rights(db, s, [(creator_a, 70.0, "MASTER"), (creator_b, 30.0, "MASTER")])

    summary = ve.compute_full_catalog_valuation(db, org_id=org.id, persist=False)
    pcs = {r["creator_id"]: r for r in summary["per_creator_share"]}
    assert creator_a.id in pcs and creator_b.id in pcs
    a_val = pcs[creator_a.id]["blended_value"]
    b_val = pcs[creator_b.id]["blended_value"]
    # 70/30 attribution → ratio ≈ 70/30 ≈ 2.333
    assert a_val > b_val
    assert b_val > 0
    assert a_val / b_val == pytest.approx(70.0 / 30.0, rel=0.02)
    # Shares sum to 100% (only two creators on the catalog).
    assert pcs[creator_a.id]["share_pct"] + pcs[creator_b.id]["share_pct"] == pytest.approx(100.0, abs=0.5)


def test_per_creator_share_falls_back_to_equal_split_when_no_rights(db, org, creator_a, creator_b):
    """Songs without RightsSplit rows fall back to equal SongCredit split."""
    s = _make_song(db, org, "Unmapped Song", release_years_ago=1)
    db.add_all([
        SongCredit(song_id=s.id, creator_id=creator_a.id, role="ARTIST", share_percentage=50.0),
        SongCredit(song_id=s.id, creator_id=creator_b.id, role="ARTIST", share_percentage=50.0),
    ])
    cur_year = date.today().year
    st = _make_statement(db, org, source_type="GENERIC", year=cur_year - 1)
    _make_line(db, org, st, s, 1000.0, category="streaming")
    db.commit()

    summary = ve.compute_full_catalog_valuation(db, org_id=org.id, persist=False)
    pcs = {r["creator_id"]: r for r in summary["per_creator_share"]}
    a_val = pcs[creator_a.id]["blended_value"]
    b_val = pcs[creator_b.id]["blended_value"]
    assert a_val == pytest.approx(b_val, rel=0.001)


def test_attribute_helper_normalizes_share_fractions(db, org, creator_a, creator_b):
    """RightsSplit shares for a song must sum to 1.0 in the helper output."""
    s = _make_song(db, org, "Norm Song", release_years_ago=1)
    _attach_rights(db, s, [
        (creator_a, 60.0, "MASTER"),
        (creator_a, 50.0, "PUBLISHING"),  # Same creator multiple rights_types
        (creator_b, 40.0, "MASTER"),
    ])
    out = ve._attribute_songs_to_creators(db, [s.id])
    assert s.id in out
    fractions = {cid: frac for cid, _, frac in out[s.id]}
    assert sum(fractions.values()) == pytest.approx(1.0, abs=0.001)
    # Creator A should get (60+50)/(60+50+40) = 110/150 = 0.733
    assert fractions[creator_a.id] == pytest.approx(110.0 / 150.0, rel=0.001)
    assert fractions[creator_b.id] == pytest.approx(40.0 / 150.0, rel=0.001)
