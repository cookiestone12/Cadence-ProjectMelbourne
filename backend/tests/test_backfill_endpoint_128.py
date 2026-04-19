"""Task #128 — Regression guard for the prod-facing backfill endpoint.

Production has no shell, so the Schedule-A splits backfill (#120) has to
be reachable over HTTP. This test pins three guarantees:

  * The route exists at the expected path and method.
  * Auth is enforced — non-super-admin callers can't trigger writes.
  * Dry-run mode reports counts without committing rows.

If any of these break, ops loses the only safe way to repair legacy
catalogs in production.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.main import app
from backend.models.database import Base, get_db
from backend.models.models import (
    User, Organization, OrganizationMember, Creator, Song, SongCredit,
)
from backend.utils.auth import get_current_user, get_password_hash


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


@pytest.fixture(scope="function")
def env():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    def _override_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_db

    # Repoint the script's own SessionLocal at the test DB so the
    # endpoint's in-process call hits the same in-memory schema.
    # Restore on teardown to avoid cross-test leakage if any future
    # test imports the script directly.
    import backend.scripts.backfill_schedule_a_splits_120 as backfill_mod
    _orig_session_local = backfill_mod.SessionLocal
    backfill_mod.SessionLocal = TestingSessionLocal

    try:
        yield db, TestClient(app)
    finally:
        backfill_mod.SessionLocal = _orig_session_local
        app.dependency_overrides.clear()
        db.close()


def _seed_org_with_legacy_song(db):
    org = Organization(name="O", type="LABEL", account_type="ENTERPRISE", display_name="O")
    db.add(org); db.commit(); db.refresh(org)

    super_admin = User(
        username="root", email="r@x.com", hashed_password=get_password_hash("x"),
        is_active=True, is_super_admin=True,
    )
    member_user = User(
        username="m", email="m@x.com", hashed_password=get_password_hash("x"),
        is_active=True,
    )
    db.add_all([super_admin, member_user]); db.commit()
    db.refresh(super_admin); db.refresh(member_user)

    db.add(OrganizationMember(organization_id=org.id, user_id=member_user.id, role="OWNER"))
    db.commit()

    creator = Creator(organization_id=org.id, display_name="Test Creator", roles=["WRITER"])
    db.add(creator); db.commit(); db.refresh(creator)

    song = Song(
        organization_id=org.id, title="Legacy Song", primary_artist="Test Creator",
        publishing_percentage=33.3, master_percentage=None,
    )
    db.add(song); db.commit(); db.refresh(song)
    db.add(SongCredit(song_id=song.id, creator_id=creator.id, role="ARTIST"))
    db.commit()
    return org, super_admin, member_user, song


def test_endpoint_requires_super_admin(env):
    db, c = env
    _, _, member_user, _ = _seed_org_with_legacy_song(db)
    # A regular org-member user must not be able to trigger the backfill.
    app.dependency_overrides[get_current_user] = lambda: member_user
    r = c.post("/api/internal/backfill/schedule-a-splits?dry_run=true")
    # get_current_super_admin raises 403 for non-super-admin callers.
    assert r.status_code in (401, 403), r.text


def test_dry_run_reports_counts_without_committing(env):
    db, c = env
    org, super_admin, _, song = _seed_org_with_legacy_song(db)
    app.dependency_overrides[get_current_user] = lambda: super_admin

    r = c.post(f"/api/internal/backfill/schedule-a-splits?dry_run=true&org_id={org.id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dry_run"] is True
    assert body["songs_scanned"] == 1
    assert body["songs_backfilled"] == 1
    assert body["skipped_other_contract"] == 0
    assert body["skipped_multi_credit"] == 0

    # Critical: dry run must NOT have created any contract / split rows.
    from backend.models.models import Contract, RightsSplit
    assert db.query(Contract).count() == 0
    assert db.query(RightsSplit).count() == 0


def test_real_run_materializes_split_sheet(env):
    db, c = env
    org, super_admin, _, song = _seed_org_with_legacy_song(db)
    app.dependency_overrides[get_current_user] = lambda: super_admin

    r = c.post(f"/api/internal/backfill/schedule-a-splits?dry_run=false&org_id={org.id}")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dry_run"] is False
    assert body["songs_backfilled"] == 1

    from backend.models.models import Contract, ContractAsset, RightsSplit
    db.expire_all()
    splits = (
        db.query(RightsSplit)
        .join(ContractAsset, ContractAsset.id == RightsSplit.contract_asset_id)
        .join(Contract, Contract.id == ContractAsset.contract_id)
        .filter(
            ContractAsset.asset_type == "SONG",
            ContractAsset.asset_id == song.id,
            Contract.contract_type == "SPLIT_SHEET",
        )
        .all()
    )
    assert len(splits) == 1, f"expected 1 SPLIT_SHEET RightsSplit row, got {len(splits)}"
    assert splits[0].rights_type == "PUBLISHING"
    assert float(splits[0].share_percentage) == pytest.approx(33.3, rel=1e-3)
