"""Task #106 — Decay analytics "Songs Awaiting More Data" panel.

Covers the new `awaiting_data` array surfaced on `run.decay_data` by the
underwriting engine, plus the honest-empty-state for portfolio_k /
portfolio_half_life when no song fit a curve.

Cases:
  * 1 period of revenue            -> awaiting_data row with periods_needed=2
  * 2 periods of revenue           -> awaiting_data row with periods_needed=1
  * 3 pre-peak-only periods        -> awaiting_data row reason=no_post_peak_data
  * Mixed catalog (1 fits, 1 needs more, 1 zero) -> only the partial one shows up
  * Empty catalog                  -> portfolio_k / portfolio_half_life == None
"""
from datetime import date, datetime

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models.database import Base
from backend.models.models import (
    User, Organization, OrganizationMember, Creator, Song, SongCredit,
    RoyaltyStatement, RoyaltyStatementLine, UnderwritingRun,
)
from backend.services.underwriting_engine import run_underwriting


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


def _seed_org(db):
    org = Organization(name="O", type="LABEL", account_type="ENTERPRISE", display_name="O")
    db.add(org); db.commit(); db.refresh(org)
    user = User(username="u", email="u@x.com", hashed_password="x", is_active=True)
    db.add(user); db.commit(); db.refresh(user)
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="OWNER"))
    db.commit()
    return org, user


def _add_song(db, org_id, title):
    s = Song(organization_id=org_id, title=title, primary_artist="X")
    db.add(s); db.commit(); db.refresh(s)
    return s


def _add_line(db, org_id, stmt_id, song_id, amount, period_start, period_end):
    line = RoyaltyStatementLine(
        org_id=org_id, statement_id=stmt_id, matched_song_id=song_id,
        net_amount=amount, gross_amount=amount, match_status="MATCHED",
        activity_period_start=period_start, activity_period_end=period_end,
        canonical_right_category="streaming",
    )
    db.add(line)


def _make_stmt(db, org_id, period_start, period_end, file_name):
    stmt = RoyaltyStatement(
        organization_id=org_id, source_name="Test", source_type="OTHER",
        period_start=period_start, period_end=period_end,
        currency="USD", file_name=file_name, total_revenue_cents=10000, status="PROCESSED",
    )
    db.add(stmt); db.commit(); db.refresh(stmt)
    return stmt


# Six distinct half-year periods so a song can have 1..6 periods of revenue.
PERIOD_RANGES = [
    (date(2022, 1, 1), date(2022, 6, 30)),  # 2022H1
    (date(2022, 7, 1), date(2022, 12, 31)), # 2022H2
    (date(2023, 1, 1), date(2023, 6, 30)),  # 2023H1
    (date(2023, 7, 1), date(2023, 12, 31)), # 2023H2
    (date(2024, 1, 1), date(2024, 6, 30)),  # 2024H1
    (date(2024, 7, 1), date(2024, 12, 31)), # 2024H2
]


def _stmts(db, org_id, n):
    return [_make_stmt(db, org_id, ps, pe, f"stmt_{i}.csv") for i, (ps, pe) in enumerate(PERIOD_RANGES[:n])]


def _decay_data(db, org_id, user_id):
    out = run_underwriting(db, org_id, user_id=user_id)
    run = db.query(UnderwritingRun).get(out["run_id"])
    return run.decay_data


def test_one_period_yields_awaiting_with_two_more_needed(db):
    org, user = _seed_org(db)
    song = _add_song(db, org.id, "Single Period Song")
    stmts = _stmts(db, org.id, 1)
    _add_line(db, org.id, stmts[0].id, song.id, 100.0, *PERIOD_RANGES[0])
    db.commit()

    decay = _decay_data(db, org.id, user.id)
    assert decay["min_data_points"] == 3
    assert decay["per_song"] == {}
    assert decay["portfolio_k"] is None, "no fit -> portfolio_k must be None, not 0.1"
    assert decay["portfolio_half_life"] is None
    awaiting = decay["awaiting_data"]
    assert len(awaiting) == 1
    row = awaiting[0]
    assert row["song_id"] == song.id
    assert row["title"] == "Single Period Song"
    assert row["periods_present"] == 1
    assert row["periods_needed"] == 2  # need 3 post-peak, have 1
    assert row["reason"] == "insufficient_data"


def test_two_periods_yields_awaiting_with_one_more_needed(db):
    org, user = _seed_org(db)
    song = _add_song(db, org.id, "Two Period Song")
    stmts = _stmts(db, org.id, 2)
    _add_line(db, org.id, stmts[0].id, song.id, 100.0, *PERIOD_RANGES[0])
    _add_line(db, org.id, stmts[1].id, song.id, 80.0,  *PERIOD_RANGES[1])
    db.commit()

    decay = _decay_data(db, org.id, user.id)
    awaiting = decay["awaiting_data"]
    assert len(awaiting) == 1
    row = awaiting[0]
    assert row["periods_present"] == 2
    assert row["periods_needed"] == 1  # have 2 post-peak (peak at idx 0), need 3
    assert row["reason"] == "insufficient_data"


def test_three_pre_peak_periods_then_zero_flags_no_post_peak(db):
    """Series rises on the last period -> peak at end -> only 1 post-peak point.
    The 3-positive count check passes but the post-peak check should not."""
    org, user = _seed_org(db)
    song = _add_song(db, org.id, "Late Bloomer")
    stmts = _stmts(db, org.id, 3)
    _add_line(db, org.id, stmts[0].id, song.id, 10.0, *PERIOD_RANGES[0])
    _add_line(db, org.id, stmts[1].id, song.id, 20.0, *PERIOD_RANGES[1])
    _add_line(db, org.id, stmts[2].id, song.id, 100.0, *PERIOD_RANGES[2])  # peak
    db.commit()

    decay = _decay_data(db, org.id, user.id)
    assert decay["per_song"] == {}, "Only 1 post-peak period -> should not fit"
    awaiting = decay["awaiting_data"]
    assert len(awaiting) == 1
    row = awaiting[0]
    assert row["periods_present"] == 3
    assert row["periods_needed"] == 2  # have 1 post-peak, need 3
    assert row["reason"] == "no_post_peak_data"


def test_mixed_catalog_only_partials_show_up(db):
    """Three songs: one fits, one is partial, one has zero revenue (not in spine).
    Awaiting list must contain only the partial."""
    org, user = _seed_org(db)
    fits = _add_song(db, org.id, "Fits Song")
    partial = _add_song(db, org.id, "Partial Song")
    _add_song(db, org.id, "Zero Song")  # never gets a line, won't appear at all

    stmts = _stmts(db, org.id, 4)
    # `fits` declines monotonically across all 4 periods -> 4 post-peak points
    for amt, st in zip([100.0, 80.0, 60.0, 40.0], stmts):
        _add_line(db, org.id, st.id, fits.id, amt, *PERIOD_RANGES[stmts.index(st)])
    # `partial` only has 1 period
    _add_line(db, org.id, stmts[0].id, partial.id, 50.0, *PERIOD_RANGES[0])
    db.commit()

    decay = _decay_data(db, org.id, user.id)
    assert str(fits.id) in decay["per_song"], "Fits song should produce a decay fit"
    assert decay["portfolio_k"] is not None
    awaiting = decay["awaiting_data"]
    assert len(awaiting) == 1
    assert awaiting[0]["song_id"] == partial.id
    assert awaiting[0]["periods_needed"] == 2


def test_empty_catalog_returns_none_portfolio_metrics(db):
    """No statements at all -> portfolio_k and portfolio_half_life are None,
    awaiting_data is empty, has_revenue_spine is False."""
    org, user = _seed_org(db)
    decay = _decay_data(db, org.id, user.id)
    assert decay["portfolio_k"] is None
    assert decay["portfolio_half_life"] is None
    assert decay["awaiting_data"] == []
    assert decay["has_revenue_spine"] is False
