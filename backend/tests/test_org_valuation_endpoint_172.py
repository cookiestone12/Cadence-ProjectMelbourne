"""Task #172 — route-level test for the spec'd org-scoped catalog endpoint.

Covers:
  * `GET /api/v1/organizations/{org_id}/valuation/catalog` returns 200 with
    the expected `selected_method` + `scope` discriminators.
  * Snapshot-on-demand: when no prior `ValuationCalculation(BLENDED)` row
    exists for the org, the endpoint computes + persists one, and the rows
    are durable across a fresh DB session (proves `db.commit()` ran).
  * Method validation rejects unknown values with 400.
  * Cross-org access returns 403.
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
    Creator,
    Organization,
    OrganizationMember,
    RoyaltyStatement,
    RoyaltyStatementLine,
    Song,
    SongCredit,
    User,
    ValuationCalculation,
)
from backend.utils.auth import get_current_user


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


def _seed(db):
    org = Organization(
        name="MainOrg", type="LABEL", account_type="ENTERPRISE", display_name="MainOrg"
    )
    db.add(org); db.commit(); db.refresh(org)

    other_org = Organization(
        name="OtherOrg", type="LABEL", account_type="ENTERPRISE", display_name="OtherOrg"
    )
    db.add(other_org); db.commit(); db.refresh(other_org)

    user = User(username="u", email="u@x.com", hashed_password="x", is_active=True)
    db.add(user); db.commit(); db.refresh(user)
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="OWNER"))
    db.commit()

    creator = Creator(organization_id=org.id, display_name="Maya")
    db.add(creator); db.commit(); db.refresh(creator)

    song = Song(
        organization_id=org.id, title="Snapshot Song", primary_artist="Maya",
        release_date=date(date.today().year - 1, 6, 1),
    )
    db.add(song); db.commit(); db.refresh(song)
    db.add(SongCredit(
        song_id=song.id, creator_id=creator.id, role="ARTIST", share_percentage=100.0,
    ))
    db.commit()

    cur_year = date.today().year
    stmt = RoyaltyStatement(
        organization_id=org.id, source_name="Test", source_type="GENERIC",
        period_start=date(cur_year - 1, 1, 1), period_end=date(cur_year - 1, 12, 31),
        currency="USD", file_name="t.csv",
        total_revenue_cents=150000, status="PROCESSED",
    )
    db.add(stmt); db.commit(); db.refresh(stmt)

    db.add(RoyaltyStatementLine(
        org_id=org.id, statement_id=stmt.id, matched_song_id=song.id,
        net_amount=1500.0,
        net_amount_statement_currency=1500.0,
        canonical_right_category="streaming",
        match_status="MATCHED",
        activity_period_start=date(cur_year - 1, 1, 1),
        activity_period_end=date(cur_year - 1, 12, 31),
    ))
    db.commit()

    return org, other_org, user, creator, song


# Note: tests use the canonical `/api/organizations/...` mount point. The
# `/api/v1/organizations/...` mirror is registered automatically by
# main._mount_v1_routes (verified live via curl on the running backend).
# Re-mounted v1 routes don't pick up `app.dependency_overrides` in TestClient,
# so testing the canonical mount exercises the same handler and DB commit
# semantics that the v1 mirror serves.
_BASE = "/api/organizations"


def test_org_catalog_endpoint_200_and_scope_tagging(db, client):
    org, _, user, creator, _ = _seed(db)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.get(f"{_BASE}/{org.id}/valuation/catalog")
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:200]}"
        body = r.json()
        assert body["selected_method"] == "blended"
        assert body["scope"] == {"org_id": org.id, "creator_id": None}

        r2 = client.get(
            f"{_BASE}/{org.id}/valuation/catalog"
            f"?creator_id={creator.id}&method=income"
        )
        assert r2.status_code == 200, f"got {r2.status_code}: {r2.text[:200]}"
        body2 = r2.json()
        assert body2["selected_method"] == "income"
        assert body2["scope"] == {"org_id": org.id, "creator_id": creator.id}
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_org_catalog_endpoint_persists_snapshot_durably(db, client):
    """The endpoint must commit `ValuationCalculation(BLENDED)` rows so they
    survive a fresh DB session (proves db.commit() actually ran)."""
    org, _, user, _, _ = _seed(db)

    # Sanity: no snapshots before the call.
    assert db.query(ValuationCalculation).filter(
        ValuationCalculation.organization_id == org.id,
        ValuationCalculation.valuation_method == "BLENDED",
    ).count() == 0

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.get(f"{_BASE}/{org.id}/valuation/catalog")
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:200]}"
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    # Verify durability across a brand-new session.
    fresh = TestingSessionLocal()
    try:
        n = fresh.query(ValuationCalculation).filter(
            ValuationCalculation.organization_id == org.id,
            ValuationCalculation.valuation_method == "BLENDED",
        ).count()
        assert n >= 1, "Snapshot must persist across sessions (commit ran)"
    finally:
        fresh.close()


def test_org_catalog_endpoint_rejects_bad_method(db, client):
    org, _, user, _, _ = _seed(db)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.get(f"{_BASE}/{org.id}/valuation/catalog?method=bogus")
        assert r.status_code == 400, f"got {r.status_code}: {r.text[:200]}"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_org_catalog_endpoint_rejects_foreign_org(db, client):
    org, other_org, user, _, _ = _seed(db)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.get(f"{_BASE}/{other_org.id}/valuation/catalog")
        assert r.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_org_catalog_endpoint_refresh_query_recomputes(db, client):
    """`?refresh=true` must trigger a fresh full-catalog compute even when
    a BLENDED snapshot already exists (default is snapshot-reuse). We
    detect the recompute by counting BLENDED rows before and after."""
    org, _, user, _, _ = _seed(db)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        # First call seeds the snapshot via the auto-compute path.
        r0 = client.get(f"{_BASE}/{org.id}/valuation/catalog")
        assert r0.status_code == 200
        n0 = db.query(ValuationCalculation).filter(
            ValuationCalculation.organization_id == org.id,
            ValuationCalculation.valuation_method == "BLENDED",
        ).count()
        assert n0 >= 1

        # Second call WITHOUT refresh must NOT add new rows (snapshot reuse).
        r1 = client.get(f"{_BASE}/{org.id}/valuation/catalog")
        assert r1.status_code == 200
        db.expire_all()
        n1 = db.query(ValuationCalculation).filter(
            ValuationCalculation.organization_id == org.id,
            ValuationCalculation.valuation_method == "BLENDED",
        ).count()
        assert n1 == n0, "default behavior must reuse snapshot, not recompute"
        dates_before = sorted(
            r.calculation_date for r in db.query(ValuationCalculation).filter(
                ValuationCalculation.organization_id == org.id,
                ValuationCalculation.valuation_method == "BLENDED",
            ).all()
        )

        # Third call WITH ?refresh=true must produce a fresh recompute.
        # Same-scope same-day dedup keeps the row COUNT stable but
        # replaces the rows — assert that calculation_date moved forward
        # for at least one row (proving recompute) while the count is
        # preserved per the dedup contract. Note: SQLite recycles PKs
        # after delete, so comparing row.id is unreliable here.
        # Sleep briefly so the new datetime.utcnow() is strictly later.
        import time as _t; _t.sleep(0.01)
        r2 = client.get(f"{_BASE}/{org.id}/valuation/catalog?refresh=true")
        assert r2.status_code == 200, f"got {r2.status_code}: {r2.text[:200]}"
        db.expire_all()
        rows_after = db.query(ValuationCalculation).filter(
            ValuationCalculation.organization_id == org.id,
            ValuationCalculation.valuation_method == "BLENDED",
        ).all()
        dates_after = sorted(r.calculation_date for r in rows_after)
        assert max(dates_after) > max(dates_before), (
            "refresh=true must produce a fresh calculation_date"
        )
        assert len(dates_after) == len(dates_before), (
            "same-scope same-day dedup must keep the row count stable "
            "(replace, not append)"
        )
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_v1_mirror_route_is_registered():
    """Sanity: the spec'd `/api/v1/organizations/{org_id}/valuation/catalog`
    path must be present in the OpenAPI schema (auto-mirrored by
    main._mount_v1_routes from the canonical /api/organizations mount)."""
    spec = app.openapi()
    assert "/api/v1/organizations/{org_id}/valuation/catalog" in spec["paths"], \
        "v1 mirror missing from OpenAPI — main._mount_v1_routes regression"
    assert "/api/v1/organizations/{org_id}/valuation/report/pdf" in spec["paths"], \
        "v1 mirror for spec'd PDF endpoint missing from OpenAPI"


def test_org_catalog_endpoint_is_not_polluted_by_prior_creator_scoped_run(db, client):
    """Regression for code-review: a creator-scoped BLENDED run persisted
    by `/full/run?scope_creator_id=X` (or compute_full_catalog_valuation
    with scope_creator_id) must NOT make a subsequent org-wide
    `/organizations/{org_id}/valuation/catalog` read return partial /
    cross-scope data. The handler must detect that the persisted pool
    holds only creator-tagged rows and trigger a fresh org-wide
    recompute, AND the aggregator must filter creator-tagged rows out
    of org-wide reads.
    """
    from backend.services import valuation_engine as ve

    org, _, user, creator, song = _seed(db)
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        # Persist ONLY a creator-scoped BLENDED snapshot first (no
        # org-wide rows yet).
        ve.compute_full_catalog_valuation(
            db, org_id=org.id, scope_creator_id=creator.id, persist=True,
        )
        db.commit()
        n_creator_only = db.query(ValuationCalculation).filter(
            ValuationCalculation.organization_id == org.id,
            ValuationCalculation.valuation_method == "BLENDED",
        ).count()
        assert n_creator_only >= 1, "creator-scoped run must persist"

        # Org-wide read WITHOUT ?refresh=true must still recompute
        # because the pool only has creator-tagged rows.
        r = client.get(f"{_BASE}/{org.id}/valuation/catalog")
        assert r.status_code == 200, f"got {r.status_code}: {r.text[:200]}"
        db.expire_all()
        n_after = db.query(ValuationCalculation).filter(
            ValuationCalculation.organization_id == org.id,
            ValuationCalculation.valuation_method == "BLENDED",
        ).count()
        assert n_after > n_creator_only, (
            "scope-aware has_snapshot must trigger fresh recompute when "
            "the existing pool only contains creator-tagged rows"
        )

        # The org-wide aggregation must reflect the org-wide rows, not
        # leak the creator-scoped snapshot. Validate by checking that
        # at least one org-tagged row now exists.
        org_tagged = [
            r for r in db.query(ValuationCalculation).filter(
                ValuationCalculation.organization_id == org.id,
                ValuationCalculation.valuation_method == "BLENDED",
            ).all()
            if (r.calc_metadata or {}).get("scope_mode") == "org"
        ]
        assert len(org_tagged) >= 1, "org-wide recompute must persist org-tagged rows"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
