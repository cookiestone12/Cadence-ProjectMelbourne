"""Task #105 — per-creator scope for the underwriting engine.

Covers:
  * `build_song_period_spine(scope_creator_id=…)` returns only the rows whose
    `matched_song_id` belongs to a song the scoped creator is credited on.
  * Scope filter to a creator with no matching credits returns an empty spine
    (instead of leaking the org-wide spine).
  * `/api/valuation/underwriting/latest?scope_creator_id=N` returns the most
    recent run with that scope and ignores org-wide runs (and vice-versa).
"""
from datetime import date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.database import Base, get_db as original_get_db
from backend.models.models import (
    User, Organization, OrganizationMember, Creator, Song, SongCredit,
    RoyaltyStatement, RoyaltyStatementLine, UnderwritingRun,
    ValuationCalculation, TerritoryRevenue,
)
from backend.utils.auth import get_current_user
from backend.services.underwriting_engine import build_song_period_spine


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


def _override_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def db():
    # Set the override for THIS test only, then restore so other test modules'
    # module-level overrides aren't permanently clobbered by ours.
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


def _seed_two_creators_with_lines(db):
    """Seed an org with creators A and B, each with one song and one matched
    royalty line, so we can verify the spine filter."""
    org = Organization(name="O", type="LABEL", account_type="ENTERPRISE", display_name="O")
    db.add(org); db.commit(); db.refresh(org)

    user = User(username="u", email="u@x.com", hashed_password="x", is_active=True)
    db.add(user); db.commit(); db.refresh(user)
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="OWNER"))
    db.commit()

    a = Creator(organization_id=org.id, display_name="Creator A")
    b = Creator(organization_id=org.id, display_name="Creator B")
    db.add_all([a, b]); db.commit(); db.refresh(a); db.refresh(b)

    song_a = Song(organization_id=org.id, title="Song A", primary_artist="A")
    song_b = Song(organization_id=org.id, title="Song B", primary_artist="B")
    db.add_all([song_a, song_b]); db.commit(); db.refresh(song_a); db.refresh(song_b)

    db.add_all([
        SongCredit(song_id=song_a.id, creator_id=a.id, role="WRITER"),
        SongCredit(song_id=song_b.id, creator_id=b.id, role="WRITER"),
    ])
    db.commit()

    stmt = RoyaltyStatement(
        organization_id=org.id, source_name="Test", source_type="OTHER",
        period_start=date(2024, 1, 1), period_end=date(2024, 6, 30),
        currency="USD", file_name="t.csv", total_revenue_cents=20000, status="PROCESSED",
    )
    db.add(stmt); db.commit(); db.refresh(stmt)

    db.add_all([
        RoyaltyStatementLine(
            org_id=org.id, statement_id=stmt.id, matched_song_id=song_a.id,
            net_amount=100.0, match_status="MATCHED",
            activity_period_start=date(2024, 1, 1), activity_period_end=date(2024, 6, 30),
        ),
        RoyaltyStatementLine(
            org_id=org.id, statement_id=stmt.id, matched_song_id=song_b.id,
            net_amount=100.0, match_status="MATCHED",
            activity_period_start=date(2024, 1, 1), activity_period_end=date(2024, 6, 30),
        ),
    ])
    db.commit()

    return org, user, a, b, song_a, song_b, stmt


def test_spine_filters_to_scope_creator_only(db):
    org, _, a, b, song_a, song_b, stmt = _seed_two_creators_with_lines(db)

    spine_all = build_song_period_spine(
        db, org.id, scope_statement_ids=[stmt.id],
    )
    matched_song_ids_all = {e["song_id"] for e in spine_all}
    assert matched_song_ids_all == {song_a.id, song_b.id}, \
        "Org-wide spine should include both songs"

    spine_a = build_song_period_spine(
        db, org.id, scope_creator_id=a.id, scope_statement_ids=[stmt.id],
    )
    matched_song_ids_a = {e["song_id"] for e in spine_a}
    assert matched_song_ids_a == {song_a.id}, \
        "Scoped spine should only include songs credited to Creator A"


def test_spine_returns_empty_when_creator_has_no_credits(db):
    org, _, a, _, _, _, stmt = _seed_two_creators_with_lines(db)
    orphan = Creator(organization_id=org.id, display_name="Orphan")
    db.add(orphan); db.commit(); db.refresh(orphan)

    spine_orphan = build_song_period_spine(
        db, org.id, scope_creator_id=orphan.id, scope_statement_ids=[stmt.id],
    )
    assert spine_orphan == [], \
        "Scoping to a creator with no song credits must return [] (no leakage)"


def test_latest_endpoint_filters_by_scope(db, client):
    org, user, a, b, _, _, _ = _seed_two_creators_with_lines(db)

    org_wide_run = UnderwritingRun(
        organization_id=org.id, created_by_user_id=user.id,
        kb_version="test", status="COMPLETED", scope_creator_id=None,
        inputs={"scope_creator_id": None},
        valuation_data={"blended": {"base": 100000, "low": 80000, "high": 120000}},
        completed_at=datetime(2024, 1, 1),
    )
    creator_a_run = UnderwritingRun(
        organization_id=org.id, created_by_user_id=user.id,
        kb_version="test", status="COMPLETED", scope_creator_id=a.id,
        inputs={"scope_creator_id": a.id},
        valuation_data={"blended": {"base": 50000, "low": 40000, "high": 60000}},
        completed_at=datetime(2024, 2, 1),
    )
    db.add_all([org_wide_run, creator_a_run]); db.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        # Org-wide (no scope) -> the org_wide_run, NOT the creator-A run.
        r = client.get("/api/valuation/underwriting/latest")
        assert r.status_code == 200
        body = r.json()
        assert body["has_data"] is True
        assert body["valuation"]["blended"]["base"] == 100000

        # Scoped to creator A -> the creator_a_run.
        r = client.get(f"/api/valuation/underwriting/latest?scope_creator_id={a.id}")
        assert r.status_code == 200
        body = r.json()
        assert body["has_data"] is True
        assert body["valuation"]["blended"]["base"] == 50000

        # Scoped to creator B (no runs) -> has_data=False.
        r = client.get(f"/api/valuation/underwriting/latest?scope_creator_id={b.id}")
        assert r.status_code == 200
        assert r.json() == {"has_data": False}
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_latest_rejects_cross_org_scope_creator(db, client):
    """A scope_creator_id belonging to another org must 404, not silently
    return that org's underwriting run or leak its existence."""
    org, user, _, _, _, _, _ = _seed_two_creators_with_lines(db)

    other_org = Organization(name="Other", type="LABEL", account_type="ENTERPRISE", display_name="Other")
    db.add(other_org); db.commit(); db.refresh(other_org)
    other_creator = Creator(organization_id=other_org.id, display_name="Foreign")
    db.add(other_creator); db.commit(); db.refresh(other_creator)
    db.add(UnderwritingRun(
        organization_id=other_org.id, created_by_user_id=user.id,
        kb_version="test", status="COMPLETED", scope_creator_id=other_creator.id,
        inputs={}, valuation_data={"blended": {"base": 99999}},
    ))
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.get(f"/api/valuation/underwriting/latest?scope_creator_id={other_creator.id}")
        assert r.status_code == 404, "must not allow scoping to a creator outside the caller's org"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_runs_list_does_not_leak_cross_org_creator_name(db, client):
    """If a stray UnderwritingRun in the caller's org references a
    scope_creator_id that belongs to another org (legacy data, manual edit),
    the runs listing must NOT return the other org's display_name."""
    org, user, _, _, _, _, _ = _seed_two_creators_with_lines(db)

    other_org = Organization(name="Other", type="LABEL", account_type="ENTERPRISE", display_name="Other")
    db.add(other_org); db.commit(); db.refresh(other_org)
    foreign = Creator(organization_id=other_org.id, display_name="Foreign Creator")
    db.add(foreign); db.commit(); db.refresh(foreign)

    # A run rooted in the caller's org but pointing at a foreign creator id.
    db.add(UnderwritingRun(
        organization_id=org.id, created_by_user_id=user.id,
        kb_version="test", status="COMPLETED", scope_creator_id=foreign.id,
        inputs={}, valuation_data={"blended": {"base": 1}},
    ))
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.get("/api/valuation/underwriting/runs")
        assert r.status_code == 200
        runs = r.json()
        target = next(x for x in runs if x["scope_creator_id"] == foreign.id)
        assert target["scope_creator_name"] is None, \
            "must not leak display_name of a creator from a different org"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_catalog_summary_scope_filters_aggregates(db, client):
    """`/catalog/summary?scope_creator_id=A` must restrict total_catalog_value,
    total_thirty_day_revenue, top_songs and territory_breakdown to A's
    songs only — NOT return org-wide aggregates with a creator label."""
    org, user, a, b, song_a, song_b, _ = _seed_two_creators_with_lines(db)

    db.add_all([
        ValuationCalculation(
            song_id=song_a.id, organization_id=org.id,
            final_valuation_cents=100_00, thirty_day_revenue_cents=10_00,
            annual_revenue_cents=120_00, growth_rate=0.10,
        ),
        ValuationCalculation(
            song_id=song_b.id, organization_id=org.id,
            final_valuation_cents=900_00, thirty_day_revenue_cents=90_00,
            annual_revenue_cents=1080_00, growth_rate=0.50,
        ),
        TerritoryRevenue(
            song_id=song_a.id, organization_id=org.id,
            period_date=date(2024, 1, 1), territory_code="US", territory_name="USA",
            total_streams=1000, publishing_revenue_cents=50_00,
            master_revenue_cents=50_00, total_revenue_cents=100_00,
        ),
        TerritoryRevenue(
            song_id=song_b.id, organization_id=org.id,
            period_date=date(2024, 1, 1), territory_code="GB", territory_name="UK",
            total_streams=5000, publishing_revenue_cents=200_00,
            master_revenue_cents=200_00, total_revenue_cents=400_00,
        ),
    ])
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        # Org-wide totals include both songs.
        r = client.get("/api/valuation/catalog/summary")
        assert r.status_code == 200
        org_wide = r.json()
        assert org_wide["total_songs"] == 2
        assert abs(org_wide["total_catalog_value"] - 1000.0) < 0.001
        assert abs(org_wide["total_thirty_day_revenue"] - 100.0) < 0.001
        assert {t["territory_code"] for t in org_wide["territory_breakdown"]} == {"US", "GB"}

        # Scoped to creator A: only song_a counts toward totals + territory.
        r = client.get(f"/api/valuation/catalog/summary?scope_creator_id={a.id}")
        assert r.status_code == 200
        scoped = r.json()
        assert scoped["total_songs"] == 1
        assert abs(scoped["total_catalog_value"] - 100.0) < 0.001, \
            "scoped total_catalog_value must reflect ONLY creator A's songs"
        assert abs(scoped["total_thirty_day_revenue"] - 10.0) < 0.001
        assert {t["territory_code"] for t in scoped["territory_breakdown"]} == {"US"}, \
            "scoped territory_breakdown must NOT include creator B's territories"

        # Cross-org scope_creator_id must 404.
        other_org = Organization(name="X", type="LABEL", account_type="ENTERPRISE", display_name="X")
        db.add(other_org); db.commit(); db.refresh(other_org)
        foreign = Creator(organization_id=other_org.id, display_name="Foreign")
        db.add(foreign); db.commit(); db.refresh(foreign)
        r = client.get(f"/api/valuation/catalog/summary?scope_creator_id={foreign.id}")
        assert r.status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_runs_list_includes_scope_creator(db, client):
    org, user, a, _, _, _, _ = _seed_two_creators_with_lines(db)
    db.add_all([
        UnderwritingRun(
            organization_id=org.id, created_by_user_id=user.id,
            kb_version="test", status="COMPLETED", scope_creator_id=a.id,
            inputs={"scope_creator_id": a.id}, valuation_data={"blended": {"base": 1}},
        ),
        UnderwritingRun(
            organization_id=org.id, created_by_user_id=user.id,
            kb_version="test", status="COMPLETED", scope_creator_id=None,
            inputs={"scope_creator_id": None}, valuation_data={"blended": {"base": 2}},
        ),
    ])
    db.commit()

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.get("/api/valuation/underwriting/runs")
        assert r.status_code == 200
        runs = r.json()
        assert len(runs) == 2
        scoped = [x for x in runs if x["scope_creator_id"] == a.id]
        org_wide = [x for x in runs if x["scope_creator_id"] is None]
        assert len(scoped) == 1 and scoped[0]["scope_creator_name"] == "Creator A"
        assert len(org_wide) == 1 and org_wide[0]["scope_creator_name"] is None
    finally:
        app.dependency_overrides.pop(get_current_user, None)
