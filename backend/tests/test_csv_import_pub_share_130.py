"""Task #130 — CSV/PDF import must materialize Pub %/Master % everywhere.

The Schedule A re-upload UI hits POST /api/csv/import. Before this fix,
that path wrote Song.publishing_percentage but left SongCredit.pub_share
NULL and never created the SPLIT_SHEET / RightsSplit rows that the
creator-scoped catalog/roster/song-detail views read from. This test
pins that the fix is in place.
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
    Contract, ContractAsset, RightsSplit, ChecklistItem,
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
    try:
        yield db, TestClient(app)
    finally:
        app.dependency_overrides.clear()
        db.close()


def _seed(db):
    org = Organization(name="O", type="LABEL", account_type="ENTERPRISE", display_name="O")
    db.add(org); db.commit(); db.refresh(org)

    user = User(
        username="u", email="u@x.com", hashed_password=get_password_hash("x"),
        is_active=True,
    )
    db.add(user); db.commit(); db.refresh(user)
    db.add(OrganizationMember(organization_id=org.id, user_id=user.id, role="OWNER"))

    creator = Creator(organization_id=org.id, display_name="MJ Jordan", roles=["WRITER"])
    db.add(creator); db.commit(); db.refresh(creator)
    return org, user, creator


def test_csv_import_writes_credit_pub_share_and_split_sheet(env):
    """The full /api/csv/import flow must populate SongCredit.pub_share
    and create the SPLIT_SHEET Contract + ContractAsset + RightsSplit rows."""
    db, c = env
    org, user, creator = _seed(db)
    app.dependency_overrides[get_current_user] = lambda: user

    # Hit the real /api/csv/import route — it pulls rows + mapping from
    # the request body, runs the same validation, and writes through the
    # exact code path the Schedule A re-upload UI uses.
    body = {
        "mapping": {
            "Title": "title",
            "Artist": "primary_artist",
            "Pub": "publishing_percentage",
        },
        "rows": [
            {"Title": "Blinding Lights", "Artist": "MJ Jordan", "Pub": "33.3"},
        ],
        "creator_id": creator.id,
    }
    r = c.post(f"/api/csv/import/{org.id}", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["songs_created"] == 1

    song = db.query(Song).filter(Song.organization_id == org.id).one()

    # Song-level legacy field still set (back-compat).
    assert song.publishing_percentage == pytest.approx(33.3, rel=1e-3)

    # NEW: SongCredit.pub_share must be populated — the creator-scoped
    # catalog/roster/song-detail views read from this column.
    credit = db.query(SongCredit).filter(SongCredit.song_id == song.id).one()
    assert credit.pub_share == pytest.approx(33.3, rel=1e-3), \
        "SongCredit.pub_share must be set so creator-filtered views render Pub %"
    assert credit.master_share is None
    assert credit.creator_id == creator.id

    # NEW: SPLIT_SHEET contract / asset link / RightsSplit must exist —
    # the Rights & Splits modal tab reads from these tables, and the
    # 'Legacy value — add credit-level splits' warning hides only when
    # they exist.
    split_sheets = db.query(Contract).filter(
        Contract.organization_id == org.id,
        Contract.contract_type == "SPLIT_SHEET",
    ).all()
    assert len(split_sheets) == 1, \
        f"expected exactly 1 SPLIT_SHEET contract, got {len(split_sheets)}"

    rights_splits = (
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
    assert len(rights_splits) == 1, \
        f"expected 1 PUBLISHING RightsSplit row, got {len(rights_splits)}"
    rs = rights_splits[0]
    assert rs.rights_type == "PUBLISHING"
    assert rs.rights_holder_id == creator.id
    assert float(rs.share_percentage) == pytest.approx(33.3, rel=1e-3)


def test_csv_import_no_split_when_song_has_no_percentage(env):
    """If the imported row has no Pub/Master %, we should still create the
    SongCredit (existing behavior), but skip the split-sheet materialization
    and not crash."""
    db, c = env
    org, user, creator = _seed(db)
    app.dependency_overrides[get_current_user] = lambda: user

    body = {
        "mapping": {"Title": "title", "Artist": "primary_artist"},
        "rows": [{"Title": "No Percentages Song", "Artist": "MJ Jordan"}],
        "creator_id": creator.id,
    }
    r = c.post(f"/api/csv/import/{org.id}", json=body)
    assert r.status_code == 200, r.text

    song = db.query(Song).filter(Song.organization_id == org.id).one()
    credit = db.query(SongCredit).filter(SongCredit.song_id == song.id).one()
    assert credit.pub_share is None
    assert credit.master_share is None
    assert db.query(Contract).count() == 0
    assert db.query(RightsSplit).count() == 0
