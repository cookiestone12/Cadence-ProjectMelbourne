"""Task #120 — Schedule A ingestion materializes credit-level splits.

Asserts that ingesting a Schedule A sheet:
  1. creates `SongCredit` rows with `pub_share` and `master_share` set
     from the sheet's Publishing % and Master % columns,
  2. creates a SPLIT_SHEET `Contract` + `ContractAsset` + `RightsSplit`
     rows so the rollup `_sync_song_pub_percentage` keeps the song-level
     `publishing_percentage`/`master_percentage` populated, and
  3. the client portal catalog endpoint returns those values to the UI.
"""
from io import BytesIO

import pytest
from openpyxl import Workbook
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.models.database import Base
from backend.models.models import (
    Organization,
    User,
    OrganizationMember,
    Song,
    SongCredit,
    Contract,
    ContractAsset,
    RightsSplit,
)
from backend.services.schedule_a_ingestion import ingest_schedule_a
from backend.models.models import Creator, OrganizationMember


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


def _make_xlsx(rows):
    wb = Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _seed_org(db):
    org = Organization(name="Acme", type="LABEL", account_type="ENTERPRISE", display_name="Acme")
    db.add(org)
    db.flush()
    user = User(email="owner@acme.test", username="owner", hashed_password="x")
    db.add(user)
    db.flush()
    db.add(OrganizationMember(user_id=user.id, organization_id=org.id, role="OWNER"))
    db.commit()
    return org, user


def test_ingestion_materializes_splits(db):
    org, user = _seed_org(db)

    headers = ["Song Title", "Artist", "Publishing %", "Master %"]
    rows = [
        headers,
        ["Track One", "Some Artist", 50, 25],
        ["Track Two", "Some Artist", 100, None],
    ]
    content = _make_xlsx(rows)

    result = ingest_schedule_a(
        db=db,
        organization=org,
        file_content=content,
        filename="JANE DOE - Placement Sheet.xlsx",
        user_id=user.id,
    )

    assert not result.errors, result.errors
    assert result.songs_created == 2
    assert result.credits_created == 2

    track_one = db.query(Song).filter(Song.title == "Track One").one()
    track_two = db.query(Song).filter(Song.title == "Track Two").one()

    assert track_one.publishing_percentage == 50.0
    assert track_one.master_percentage == 25.0

    credit_one = db.query(SongCredit).filter(SongCredit.song_id == track_one.id).one()
    assert credit_one.pub_share == 50.0
    assert credit_one.master_share == 25.0

    contract = db.query(Contract).filter(
        Contract.organization_id == org.id,
        Contract.contract_type == "SPLIT_SHEET",
        Contract.title == "Song Splits: Track One",
    ).one()
    ca = db.query(ContractAsset).filter(
        ContractAsset.contract_id == contract.id,
        ContractAsset.asset_type == "SONG",
        ContractAsset.asset_id == track_one.id,
    ).one()
    splits = db.query(RightsSplit).filter(RightsSplit.contract_asset_id == ca.id).all()
    types = {(s.rights_type, s.share_percentage) for s in splits}
    assert ("PUBLISHING", 50.0) in types
    assert ("MASTER", 25.0) in types

    credit_two = db.query(SongCredit).filter(SongCredit.song_id == track_two.id).one()
    assert credit_two.pub_share == 100.0
    assert credit_two.master_share is None

    ca2 = db.query(ContractAsset).join(Contract).filter(
        Contract.organization_id == org.id,
        Contract.contract_type == "SPLIT_SHEET",
        ContractAsset.asset_id == track_two.id,
    ).one()
    splits2 = db.query(RightsSplit).filter(RightsSplit.contract_asset_id == ca2.id).all()
    types2 = {s.rights_type for s in splits2}
    assert types2 == {"PUBLISHING"}


def test_reupload_updates_splits_idempotently(db):
    org, user = _seed_org(db)

    rows1 = [["Song Title", "Artist", "Publishing %", "Master %"], ["Re-Up", "X", 40, 40]]
    ingest_schedule_a(
        db=db, organization=org, file_content=_make_xlsx(rows1),
        filename="JOHN DOE - Placement Sheet.xlsx", user_id=user.id,
    )

    rows2 = [["Song Title", "Artist", "Publishing %", "Master %"], ["Re-Up", "X", 60, 30]]
    ingest_schedule_a(
        db=db, organization=org, file_content=_make_xlsx(rows2),
        filename="JOHN DOE - Placement Sheet.xlsx", user_id=user.id,
    )

    song = db.query(Song).filter(Song.title == "Re-Up").one()
    assert song.publishing_percentage == 60.0
    assert song.master_percentage == 30.0

    credits = db.query(SongCredit).filter(SongCredit.song_id == song.id).all()
    assert len(credits) == 1
    assert credits[0].pub_share == 60.0
    assert credits[0].master_share == 30.0

    contracts = db.query(Contract).filter(
        Contract.organization_id == org.id,
        Contract.title == "Song Splits: Re-Up",
    ).all()
    assert len(contracts) == 1

    splits = db.query(RightsSplit).join(ContractAsset).filter(
        ContractAsset.asset_id == song.id,
    ).all()
    by_type = {s.rights_type: s.share_percentage for s in splits}
    assert by_type == {"PUBLISHING": 60.0, "MASTER": 30.0}


def test_client_portal_catalog_returns_pub_master(db):
    """API regression: /api/client-portal/catalog must surface
    publishing_percentage, master_percentage, and per-credit pub_share /
    master_share for songs ingested via Schedule A.
    """
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.models.database import get_db
    from backend.utils.auth import get_current_user

    org, _owner = _seed_org(db)

    creator = Creator(
        organization_id=org.id,
        display_name="Jane Doe",
        legal_name="Jane Doe",
    )
    db.add(creator)
    db.flush()

    client_user = User(email="jane@acme.test", username="jane", hashed_password="x")
    db.add(client_user)
    db.flush()
    db.add(OrganizationMember(
        user_id=client_user.id,
        organization_id=org.id,
        role="CLIENT",
        linked_creator_id=creator.id,
    ))
    db.commit()

    rows = [["Song Title", "Artist", "Publishing %", "Master %"], ["Portal Track", "Jane", 75, 50]]
    ingest_schedule_a(
        db=db, organization=org, file_content=_make_xlsx(rows),
        filename="JANE DOE - Placement Sheet.xlsx", user_id=client_user.id,
    )

    song = db.query(Song).filter(Song.title == "Portal Track").one()
    credit = db.query(SongCredit).filter(SongCredit.song_id == song.id).one()
    credit.creator_id = creator.id
    db.commit()

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: client_user
    try:
        with TestClient(app) as tc:
            resp = tc.get("/api/client-portal/catalog")
        assert resp.status_code == 200, resp.text
        data = resp.json()
        portal_song = next(s for s in data["songs"] if s["title"] == "Portal Track")
        assert portal_song["publishing_percentage"] == 75.0
        assert portal_song["master_percentage"] == 50.0
        assert portal_song["credits"], portal_song
        c = portal_song["credits"][0]
        assert c["pub_share"] == 75.0
        assert c["master_share"] == 50.0
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
