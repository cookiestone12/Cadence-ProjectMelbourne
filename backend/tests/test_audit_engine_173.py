"""Task #173 — Royalty Audit Engine tests.

Covers each of the four checks (cross-statement, rate-check,
missing-period, decay-anomaly) as well as the route surface
(list / summary / scan / resolve / reopen).
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.database import Base, get_db as original_get_db
from backend.models.models import (
    Organization,
    OrganizationMember,
    RoyaltyAudit,
    RoyaltyStatement,
    RoyaltyStatementLine,
    Song,
    User,
)
from backend.services import audit_engine
from backend.utils.auth import get_current_user


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_conn, _):
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


def _seed_org_user(db):
    org = Organization(
        name="AuditOrg", type="LABEL",
        account_type="ENTERPRISE", display_name="AuditOrg",
    )
    db.add(org); db.commit(); db.refresh(org)
    user = User(username="a", email="a@x.com", hashed_password="x", is_active=True)
    db.add(user); db.commit(); db.refresh(user)
    db.add(OrganizationMember(
        organization_id=org.id, user_id=user.id, role="OWNER"
    ))
    db.commit()
    return org, user


def _add_song(db, org_id, title="Song"):
    s = Song(organization_id=org_id, title=title, primary_artist="X")
    db.add(s); db.commit(); db.refresh(s)
    return s


def _add_stmt(db, org_id, ps, pe, src="Test"):
    st = RoyaltyStatement(
        organization_id=org_id, source_name=src, source_type="GENERIC",
        period_start=ps, period_end=pe, currency="USD",
        file_name=f"{src}.csv", total_revenue_cents=0, status="PROCESSED",
    )
    db.add(st); db.commit(); db.refresh(st)
    return st


def _add_line(db, org_id, stmt_id, song_id, ps, pe, net, *,
              units=None, store=None, usage_type=None):
    line = RoyaltyStatementLine(
        org_id=org_id, statement_id=stmt_id, matched_song_id=song_id,
        net_amount=net,
        net_amount_statement_currency=net,
        canonical_right_category="streaming",
        match_status="MATCHED",
        activity_period_start=ps,
        activity_period_end=pe,
        unit_count=units,
        store=store,
        usage_type=usage_type,
    )
    db.add(line); db.commit()
    return line


# --- Check 1: cross-statement ---------------------------------------------

def test_cross_statement_flags_mismatched_totals(db):
    org, _ = _seed_org_user(db)
    song = _add_song(db, org.id, "CrossSong")
    ps, pe = date(2025, 1, 1), date(2025, 3, 31)
    s1 = _add_stmt(db, org.id, ps, pe, src="A")
    s2 = _add_stmt(db, org.id, ps, pe, src="B")
    _add_line(db, org.id, s1.id, song.id, ps, pe, 1000.0)
    _add_line(db, org.id, s2.id, song.id, ps, pe, 600.0)

    findings = audit_engine.check_cross_statement(db, org.id)
    db.commit()

    assert len(findings) == 1
    f = findings[0]
    assert f.audit_type == "CROSS_STATEMENT"
    assert f.song_id == song.id
    assert f.severity in ("MEDIUM", "HIGH", "CRITICAL")
    # delta = 400 on 1000 hi → 40% → HIGH
    assert f.severity == "HIGH"
    assert f.discrepancy_cents == 40000


def test_cross_statement_ignores_within_tolerance(db):
    org, _ = _seed_org_user(db)
    song = _add_song(db, org.id, "InTolerance")
    ps, pe = date(2025, 1, 1), date(2025, 3, 31)
    s1 = _add_stmt(db, org.id, ps, pe, src="A")
    s2 = _add_stmt(db, org.id, ps, pe, src="B")
    _add_line(db, org.id, s1.id, song.id, ps, pe, 1000.0)
    _add_line(db, org.id, s2.id, song.id, ps, pe, 980.0)  # 2% delta

    findings = audit_engine.check_cross_statement(db, org.id)
    assert findings == []


# --- Check 2: rate-check ---------------------------------------------------

def test_rate_check_flags_under_market_payout(db):
    org, _ = _seed_org_user(db)
    song = _add_song(db, org.id, "RateSong")
    ps, pe = date(2025, 1, 1), date(2025, 3, 31)
    st = _add_stmt(db, org.id, ps, pe, src="Spotify")
    # Spotify premium expected ~$0.004/stream. We'll book $0.001/stream
    # over 100k units = $100 vs expected $400.
    _add_line(
        db, org.id, st.id, song.id, ps, pe,
        net=100.0, units=100_000,
        store="Spotify", usage_type="premium",
    )

    findings = audit_engine.check_rate(db, org.id)
    db.commit()
    assert len(findings) == 1
    f = findings[0]
    assert f.audit_type == "RATE_CHECK"
    assert f.song_id == song.id
    # 75% short → CRITICAL
    assert f.severity == "CRITICAL"
    assert f.details["store"] == "Spotify"


def test_rate_check_skips_unknown_platform(db):
    org, _ = _seed_org_user(db)
    song = _add_song(db, org.id, "UnknownPlat")
    ps, pe = date(2025, 1, 1), date(2025, 3, 31)
    st = _add_stmt(db, org.id, ps, pe)
    _add_line(
        db, org.id, st.id, song.id, ps, pe,
        net=10.0, units=50_000, store="ObscureDSP", usage_type="premium",
    )
    assert audit_engine.check_rate(db, org.id) == []


# --- Check 3: missing-period ----------------------------------------------

def test_missing_period_flags_recent_gap(db):
    org, _ = _seed_org_user(db)
    song = _add_song(db, org.id, "MissingSong")
    today = date.today()
    # Create lines for the last 4 quarters except the most-recently-closed
    # one; the engine flags any quarter between first-seen and the
    # in-progress quarter that has zero lines.
    def quarter_dates(year, q):
        ps = date(year, (q - 1) * 3 + 1, 1)
        pe_month = q * 3
        pe = (date(year, 12, 31) if pe_month == 12
              else date(year, pe_month + 1, 1) - timedelta(days=1))
        return ps, pe

    # Use four prior quarters, skip the third to create a gap.
    cur_q = (today.month - 1) // 3 + 1
    cur_y = today.year
    quarters = []
    y, q = cur_y, cur_q
    for _ in range(5):
        q -= 1
        if q < 1:
            q = 4; y -= 1
        quarters.append((y, q))
    quarters = list(reversed(quarters))  # oldest → newest
    # Drop the second-newest quarter to create a gap
    quarters_to_post = quarters[:-2] + [quarters[-1]]
    st = _add_stmt(db, org.id, *quarter_dates(*quarters[0]))
    for (yy, qq) in quarters_to_post:
        ps, pe = quarter_dates(yy, qq)
        _add_line(db, org.id, st.id, song.id, ps, pe, 100.0)

    findings = audit_engine.check_missing_period(db, org.id)
    db.commit()
    assert len(findings) >= 1
    f = findings[0]
    assert f.audit_type == "MISSING_PERIOD"
    assert f.song_id == song.id


def test_missing_period_ignores_short_history(db):
    org, _ = _seed_org_user(db)
    song = _add_song(db, org.id, "ShortHistory")
    ps, pe = date(2025, 1, 1), date(2025, 3, 31)
    st = _add_stmt(db, org.id, ps, pe)
    _add_line(db, org.id, st.id, song.id, ps, pe, 50.0)
    assert audit_engine.check_missing_period(db, org.id) == []


# --- Check 4: decay-anomaly -----------------------------------------------

def test_decay_anomaly_flags_observed_below_fit(db):
    """Build a clean exponential decay then plant a sharply low last
    period; the engine should flag it."""
    org, _ = _seed_org_user(db)
    song = _add_song(db, org.id, "DecayDrop")

    quarters = [
        (2024, 1), (2024, 2), (2024, 3), (2024, 4),
        (2025, 1), (2025, 2), (2025, 3),
    ]
    # Decaying values then a crash on the final quarter
    values = [1000, 700, 500, 350, 250, 175, 30]
    for (y, q), v in zip(quarters, values):
        ps = date(y, (q - 1) * 3 + 1, 1)
        pe_month = q * 3
        pe = (date(y, 12, 31) if pe_month == 12
              else date(y, pe_month + 1, 1) - timedelta(days=1))
        st = _add_stmt(db, org.id, ps, pe, src=f"S{y}{q}")
        _add_line(db, org.id, st.id, song.id, ps, pe, float(v))

    findings = audit_engine.check_decay_anomaly(db, org.id)
    db.commit()
    # At minimum, the crash quarter should produce a finding.
    assert len(findings) >= 1
    assert findings[0].audit_type == "DECAY_ANOMALY"
    assert findings[0].song_id == song.id


def test_decay_anomaly_uses_catalog_fallback_when_per_song_fit_poor(db):
    """Task #199 Phase 4 regression — when a song has too few quarters
    to fit its own decay curve, ``check_decay_anomaly`` must fall back
    to projecting the prior period forward by the catalog's measured
    decay rate (median per-song decay). This exercises the rewired
    fallback branch and proves the ``net``/``net_total`` key alignment
    between ``build_time_series`` and the fallback code is correct.
    """
    org, _ = _seed_org_user(db)

    # Catalog reference songs — 4 quarters of clean monotonic decay
    # each, enough for ``compute_catalog_decay_rate`` (min_periods=4).
    quarters_full = [(2024, 1), (2024, 2), (2024, 3), (2024, 4)]
    catalog_curves = [
        [1000.0, 700.0, 490.0, 343.0],
        [800.0, 560.0, 392.0, 274.0],
        [1200.0, 840.0, 588.0, 411.0],
    ]
    for i, curve in enumerate(catalog_curves):
        s = _add_song(db, org.id, f"CatalogSong{i}")
        for (y, q), v in zip(quarters_full, curve):
            ps = date(y, (q - 1) * 3 + 1, 1)
            pe_month = q * 3
            pe = (date(y, 12, 31) if pe_month == 12
                  else date(y, pe_month + 1, 1) - timedelta(days=1))
            st = _add_stmt(db, org.id, ps, pe, src=f"Cat{i}{y}{q}")
            _add_line(db, org.id, st.id, s.id, ps, pe, v)

    # Subject song: only 2 quarters → ``fit_exponential_decay`` returns
    # None, forcing the fallback path. Last quarter craters from $500
    # to $20 (96% drop), well past the catalog decay's expected ~30%.
    subject = _add_song(db, org.id, "ShortHistoryCrash")
    for (y, q), v in zip([(2025, 1), (2025, 2)], [500.0, 20.0]):
        ps = date(y, (q - 1) * 3 + 1, 1)
        pe = date(y, q * 3 + 1, 1) - timedelta(days=1)
        st = _add_stmt(db, org.id, ps, pe, src=f"Sub{y}{q}")
        _add_line(db, org.id, st.id, subject.id, ps, pe, v)

    findings = audit_engine.check_decay_anomaly(db, org.id)
    db.commit()

    subject_findings = [f for f in findings if f.song_id == subject.id]
    assert subject_findings, (
        "expected catalog-fallback path to flag the subject song's "
        "97% drop against the projected catalog decay baseline"
    )
    f = subject_findings[0]
    assert f.audit_type == "DECAY_ANOMALY"
    # Fallback path stamps a distinct decay_quality marker so we can
    # verify which branch produced the finding.
    assert (f.details or {}).get("decay_quality") == "catalog_fallback"
    assert (f.details or {}).get("catalog_decay_rate") is not None


# --- Orchestrator + idempotency -------------------------------------------

def test_run_full_scan_is_idempotent(db):
    org, _ = _seed_org_user(db)
    song = _add_song(db, org.id, "Idem")
    ps, pe = date(2025, 1, 1), date(2025, 3, 31)
    s1 = _add_stmt(db, org.id, ps, pe, src="A")
    s2 = _add_stmt(db, org.id, ps, pe, src="B")
    _add_line(db, org.id, s1.id, song.id, ps, pe, 1000.0)
    _add_line(db, org.id, s2.id, song.id, ps, pe, 600.0)

    audit_engine.run_full_scan(db, org.id)
    n1 = db.query(RoyaltyAudit).filter(
        RoyaltyAudit.organization_id == org.id
    ).count()

    audit_engine.run_full_scan(db, org.id)
    n2 = db.query(RoyaltyAudit).filter(
        RoyaltyAudit.organization_id == org.id
    ).count()

    assert n1 == n2, "Re-running the scan should not duplicate findings"


# --- Route surface --------------------------------------------------------

_BASE = "/api/organizations"


def test_audit_routes_list_summary_resolve_reopen(db, client):
    org, user = _seed_org_user(db)
    song = _add_song(db, org.id, "RouteSong")
    ps, pe = date(2025, 1, 1), date(2025, 3, 31)
    s1 = _add_stmt(db, org.id, ps, pe, src="A")
    s2 = _add_stmt(db, org.id, ps, pe, src="B")
    _add_line(db, org.id, s1.id, song.id, ps, pe, 1000.0)
    _add_line(db, org.id, s2.id, song.id, ps, pe, 500.0)

    app.dependency_overrides[get_current_user] = lambda: user
    try:
        r = client.post(f"{_BASE}/{org.id}/audit/scan")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["counts"]["CROSS_STATEMENT"] >= 1
        assert body["total"] >= 1

        r = client.get(f"{_BASE}/{org.id}/audit/findings")
        assert r.status_code == 200
        listed = r.json()
        assert listed["total"] >= 1
        finding_id = listed["findings"][0]["id"]

        r = client.get(f"{_BASE}/{org.id}/audit/summary")
        assert r.status_code == 200
        s = r.json()
        assert s["open_total"] >= 1
        assert "CROSS_STATEMENT" in s["by_type"]

        r = client.post(
            f"{_BASE}/{org.id}/audit/findings/{finding_id}/resolve",
            json={"resolution_notes": "duplicate report from B"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["resolved"] is True

        r = client.get(
            f"{_BASE}/{org.id}/audit/findings?resolved=false"
        )
        assert all(not f["resolved"] for f in r.json()["findings"])

        r = client.post(
            f"{_BASE}/{org.id}/audit/findings/{finding_id}/reopen"
        )
        assert r.status_code == 200
        assert r.json()["resolved"] is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)


def test_audit_routes_403_for_non_member(db, client):
    org, _ = _seed_org_user(db)
    other_user = User(
        username="b", email="b@x.com", hashed_password="x", is_active=True
    )
    db.add(other_user); db.commit(); db.refresh(other_user)
    app.dependency_overrides[get_current_user] = lambda: other_user
    try:
        r = client.get(f"{_BASE}/{org.id}/audit/findings")
        assert r.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)
