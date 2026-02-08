import pytest
from datetime import datetime, date
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.database import Base
from backend.models.models import (
    User, Organization, OrganizationMember, Creator, Song, Work,
    Contract, ContractParty, ContractAsset, RightsSplit,
    ContractType, ContractStatus, AssetType, RightsType, PartyRole
)


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


from backend.models.database import get_db as original_get_db
app.dependency_overrides[original_get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(scope="function")
def db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture(scope="function")
def test_user(db: Session):
    user = User(
        username="testuser",
        email="testuser@example.com",
        hashed_password="hashed_password_123",
        is_admin=False,
        is_super_admin=False,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_user_2(db: Session):
    user = User(
        username="testuser2",
        email="testuser2@example.com",
        hashed_password="hashed_password_456",
        is_admin=False,
        is_super_admin=False,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_organization(db: Session, test_user: User):
    org = Organization(
        name="Test Organization",
        type="LABEL",
        account_type="ENTERPRISE",
        display_name="Test Org Display",
        logo_url="https://example.com/logo.png",
        logo_orientation="square",
        primary_color="#000000"
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    
    membership = OrganizationMember(
        organization_id=org.id,
        user_id=test_user.id,
        role="OWNER"
    )
    db.add(membership)
    db.commit()
    
    return org


@pytest.fixture(scope="function")
def test_organization_2(db: Session, test_user_2: User):
    org = Organization(
        name="Test Organization 2",
        type="PUBLISHER",
        account_type="ENTERPRISE",
        display_name="Test Org 2 Display",
        logo_url="https://example.com/logo2.png",
        logo_orientation="square",
        primary_color="#FFFFFF"
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    
    membership = OrganizationMember(
        organization_id=org.id,
        user_id=test_user_2.id,
        role="OWNER"
    )
    db.add(membership)
    db.commit()
    
    return org


@pytest.fixture(scope="function")
def test_creator(db: Session, test_organization: Organization):
    creator = Creator(
        organization_id=test_organization.id,
        display_name="Test Creator",
        legal_name="Test Creator Legal",
        email="creator@example.com",
        roles=["ARTIST", "SONGWRITER"],
        primary_territory="US",
        primary_pro="ASCAP",
        primary_ipi="00000000000",
        contributor_type="ARTIST",
        phone="+1234567890",
        publisher_name="Test Publisher",
        label_affiliation="Test Label",
        bio="Test bio",
        website_url="https://example.com",
        spotify_artist_id="spotify123",
        apple_music_id="applemusic123"
    )
    db.add(creator)
    db.commit()
    db.refresh(creator)
    return creator


@pytest.fixture(scope="function")
def test_creator_2(db: Session, test_organization: Organization):
    creator = Creator(
        organization_id=test_organization.id,
        display_name="Test Creator 2",
        legal_name="Test Creator 2 Legal",
        email="creator2@example.com",
        roles=["SONGWRITER"],
        primary_territory="UK",
        primary_pro="PRS",
        primary_ipi="11111111111"
    )
    db.add(creator)
    db.commit()
    db.refresh(creator)
    return creator


@pytest.fixture(scope="function")
def test_song(db: Session, test_organization: Organization):
    song = Song(
        organization_id=test_organization.id,
        title="Test Song",
        primary_artist="Test Artist",
        isrc="US1234567890",
        iswc="T-123456789-0",
        project_title="Test Project",
        release_date=date(2024, 1, 15),
        status_health_score=75.0
    )
    db.add(song)
    db.commit()
    db.refresh(song)
    return song


@pytest.fixture(scope="function")
def test_work(db: Session, test_organization: Organization):
    work = Work(
        organization_id=test_organization.id,
        title="Test Work",
        alternative_titles=["Alt Title 1"],
        iswc="T-987654321-0",
        language="en",
        genre="POP"
    )
    db.add(work)
    db.commit()
    db.refresh(work)
    return work


class TestContractEnums:
    def test_contract_type_enum_values(self):
        assert ContractType.MASTER.value == "MASTER"
        assert ContractType.PUBLISHING.value == "PUBLISHING"
        assert ContractType.SYNC_LICENSE.value == "SYNC_LICENSE"
        assert ContractType.DISTRIBUTION.value == "DISTRIBUTION"
        assert ContractType.MANAGEMENT.value == "MANAGEMENT"
        assert ContractType.ADMINISTRATION.value == "ADMINISTRATION"
        assert ContractType.CO_PUBLISHING.value == "CO_PUBLISHING"
        assert ContractType.SUB_PUBLISHING.value == "SUB_PUBLISHING"
        assert ContractType.OTHER.value == "OTHER"

    def test_contract_status_enum_values(self):
        assert ContractStatus.DRAFT.value == "DRAFT"
        assert ContractStatus.PENDING.value == "PENDING"
        assert ContractStatus.ACTIVE.value == "ACTIVE"
        assert ContractStatus.EXPIRED.value == "EXPIRED"
        assert ContractStatus.TERMINATED.value == "TERMINATED"

    def test_asset_type_enum_values(self):
        assert AssetType.SONG.value == "SONG"
        assert AssetType.WORK.value == "WORK"

    def test_rights_type_enum_values(self):
        assert RightsType.MASTER.value == "MASTER"
        assert RightsType.PUBLISHING.value == "PUBLISHING"
        assert RightsType.SYNC.value == "SYNC"
        assert RightsType.MECHANICAL.value == "MECHANICAL"
        assert RightsType.PERFORMANCE.value == "PERFORMANCE"
        assert RightsType.NEIGHBORING.value == "NEIGHBORING"
        assert RightsType.OTHER.value == "OTHER"

    def test_party_role_enum_values(self):
        assert PartyRole.LICENSOR.value == "LICENSOR"
        assert PartyRole.LICENSEE.value == "LICENSEE"
        assert PartyRole.ASSIGNOR.value == "ASSIGNOR"
        assert PartyRole.ASSIGNEE.value == "ASSIGNEE"
        assert PartyRole.PUBLISHER.value == "PUBLISHER"
        assert PartyRole.SUB_PUBLISHER.value == "SUB_PUBLISHER"
        assert PartyRole.ADMINISTRATOR.value == "ADMINISTRATOR"
        assert PartyRole.ARTIST.value == "ARTIST"
        assert PartyRole.LABEL.value == "LABEL"
        assert PartyRole.DISTRIBUTOR.value == "DISTRIBUTOR"
        assert PartyRole.OTHER.value == "OTHER"


class TestContractModel:
    def test_contract_creation_with_all_fields(self, db: Session, test_organization: Organization, test_user: User):
        contract = Contract(
            organization_id=test_organization.id,
            title="Complete Contract",
            contract_type="MASTER",
            status="ACTIVE",
            reference_number="REF001",
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
            territory=["US", "CA", "UK"],
            advance_amount=10000.50,
            advance_currency="USD",
            advance_recouped=5000.25,
            notes="Complete contract notes",
            terms_summary="Summary of terms",
            created_by_user_id=test_user.id
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        assert contract.id is not None
        assert contract.organization_id == test_organization.id
        assert contract.title == "Complete Contract"
        assert contract.contract_type == "MASTER"
        assert contract.status == "ACTIVE"
        assert contract.reference_number == "REF001"
        assert contract.start_date == date(2024, 1, 1)
        assert contract.end_date == date(2025, 12, 31)
        assert contract.territory == ["US", "CA", "UK"]
        assert contract.advance_amount == 10000.50
        assert contract.advance_currency == "USD"
        assert contract.advance_recouped == 5000.25
        assert contract.notes == "Complete contract notes"
        assert contract.terms_summary == "Summary of terms"
        assert contract.created_by_user_id == test_user.id
        assert contract.created_at is not None
        assert contract.updated_at is not None

    def test_contract_with_minimal_fields(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Minimal Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        assert contract.id is not None
        assert contract.title == "Minimal Contract"
        assert contract.contract_type == "OTHER"
        assert contract.status == "DRAFT"
        assert contract.territory == []
        assert contract.advance_amount == 0.0
        assert contract.advance_currency == "USD"
        assert contract.advance_recouped == 0.0

    def test_contract_default_values(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        assert contract.contract_type == "OTHER"
        assert contract.status == "DRAFT"
        assert contract.advance_currency == "USD"

    def test_contract_requires_organization_id(self, db: Session):
        contract = Contract(
            title="Test Contract"
        )
        db.add(contract)
        
        with pytest.raises(Exception):
            db.commit()

    def test_contract_requires_title(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id
        )
        db.add(contract)
        
        with pytest.raises(Exception):
            db.commit()


class TestContractStatusTests:
    def test_contract_with_draft_status(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Draft Contract",
            status="DRAFT"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        assert contract.status == "DRAFT"

    def test_contract_with_pending_status(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Pending Contract",
            status="PENDING"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        assert contract.status == "PENDING"

    def test_contract_with_active_status(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Active Contract",
            status="ACTIVE"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        assert contract.status == "ACTIVE"

    def test_contract_with_expired_status(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Expired Contract",
            status="EXPIRED"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        assert contract.status == "EXPIRED"

    def test_contract_with_terminated_status(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Terminated Contract",
            status="TERMINATED"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        assert contract.status == "TERMINATED"

    def test_contract_date_fields(self, db: Session, test_organization: Organization):
        start = date(2024, 1, 1)
        end = date(2024, 12, 31)
        
        contract = Contract(
            organization_id=test_organization.id,
            title="Contract with Dates",
            start_date=start,
            end_date=end
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        assert contract.start_date == start
        assert contract.end_date == end
        assert isinstance(contract.start_date, date)
        assert isinstance(contract.end_date, date)


class TestContractPartyModel:
    def test_contract_party_creation_with_all_fields(self, db: Session, test_organization: Organization, test_creator: Creator):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        party = ContractParty(
            contract_id=contract.id,
            party_name="Test Party",
            party_role="LICENSOR",
            creator_id=test_creator.id,
            contact_email="party@example.com",
            contact_info="Test contact info"
        )
        db.add(party)
        db.commit()
        db.refresh(party)
        
        assert party.id is not None
        assert party.contract_id == contract.id
        assert party.party_name == "Test Party"
        assert party.party_role == "LICENSOR"
        assert party.creator_id == test_creator.id
        assert party.contact_email == "party@example.com"
        assert party.contact_info == "Test contact info"
        assert party.created_at is not None

    def test_contract_party_with_creator_linkage(self, db: Session, test_organization: Organization, test_creator: Creator):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        party = ContractParty(
            contract_id=contract.id,
            party_name="Creator Party",
            party_role="ARTIST",
            creator_id=test_creator.id
        )
        db.add(party)
        db.commit()
        db.refresh(party)
        
        linked_creator = db.query(Creator).filter(Creator.id == party.creator_id).first()
        assert linked_creator is not None
        assert linked_creator.id == test_creator.id
        assert linked_creator.display_name == "Test Creator"

    def test_contract_party_with_minimal_fields(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        party = ContractParty(
            contract_id=contract.id,
            party_name="Test Party"
        )
        db.add(party)
        db.commit()
        db.refresh(party)
        
        assert party.id is not None
        assert party.party_name == "Test Party"
        assert party.party_role == "OTHER"
        assert party.creator_id is None

    def test_contract_party_default_role(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        party = ContractParty(
            contract_id=contract.id,
            party_name="Test Party"
        )
        db.add(party)
        db.commit()
        db.refresh(party)
        
        assert party.party_role == "OTHER"

    def test_multiple_contract_parties(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        party1 = ContractParty(
            contract_id=contract.id,
            party_name="Party 1",
            party_role="LICENSOR"
        )
        party2 = ContractParty(
            contract_id=contract.id,
            party_name="Party 2",
            party_role="LICENSEE"
        )
        db.add(party1)
        db.add(party2)
        db.commit()
        
        parties = db.query(ContractParty).filter(ContractParty.contract_id == contract.id).all()
        assert len(parties) == 2
        assert any(p.party_name == "Party 1" for p in parties)
        assert any(p.party_name == "Party 2" for p in parties)


class TestContractAssetModel:
    def test_contract_asset_song_linkage(self, db: Session, test_organization: Organization, test_song: Song):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        assert asset.id is not None
        assert asset.contract_id == contract.id
        assert asset.asset_type == "SONG"
        assert asset.asset_id == test_song.id
        assert asset.created_at is not None

    def test_contract_asset_work_linkage(self, db: Session, test_organization: Organization, test_work: Work):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="WORK",
            asset_id=test_work.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        assert asset.asset_type == "WORK"
        assert asset.asset_id == test_work.id

    def test_contract_asset_unique_constraint(self, db: Session, test_organization: Organization, test_song: Song):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset1 = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset1)
        db.commit()
        
        asset2 = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset2)
        
        with pytest.raises(Exception):
            db.commit()

    def test_multiple_assets_different_types(self, db: Session, test_organization: Organization, test_song: Song, test_work: Work):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset1 = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        asset2 = ContractAsset(
            contract_id=contract.id,
            asset_type="WORK",
            asset_id=test_work.id
        )
        db.add(asset1)
        db.add(asset2)
        db.commit()
        
        assets = db.query(ContractAsset).filter(ContractAsset.contract_id == contract.id).all()
        assert len(assets) == 2

    def test_multiple_assets_same_type_different_ids(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        song1 = Song(
            organization_id=test_organization.id,
            title="Song 1",
            primary_artist="Artist 1"
        )
        song2 = Song(
            organization_id=test_organization.id,
            title="Song 2",
            primary_artist="Artist 2"
        )
        db.add(song1)
        db.add(song2)
        db.commit()
        db.refresh(song1)
        db.refresh(song2)
        
        asset1 = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=song1.id
        )
        asset2 = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=song2.id
        )
        db.add(asset1)
        db.add(asset2)
        db.commit()
        
        assets = db.query(ContractAsset).filter(ContractAsset.contract_id == contract.id).all()
        assert len(assets) == 2


class TestRightsSplitModel:
    def test_rights_split_creation_with_all_fields(self, db: Session, test_organization: Organization, test_song: Song, test_creator: Creator):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        split = RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=test_creator.id,
            rights_type="MASTER",
            share_percentage=100.0,
            notes="Full master rights"
        )
        db.add(split)
        db.commit()
        db.refresh(split)
        
        assert split.id is not None
        assert split.contract_asset_id == asset.id
        assert split.rights_holder_id == test_creator.id
        assert split.rights_type == "MASTER"
        assert split.share_percentage == 100.0
        assert split.notes == "Full master rights"
        assert split.created_at is not None
        assert split.updated_at is not None

    def test_rights_split_valid_share_percentages(self, db: Session, test_organization: Organization, test_song: Song, test_creator: Creator):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        test_percentages = [0.0, 50.0, 50.5, 99.9, 100.0]
        
        for percentage in test_percentages:
            split = RightsSplit(
                contract_asset_id=asset.id,
                rights_holder_id=test_creator.id,
                rights_type="MASTER",
                share_percentage=percentage
            )
            db.add(split)
            db.commit()
            db.refresh(split)
            
            assert split.share_percentage == percentage

    def test_rights_split_edge_case_zero_percent(self, db: Session, test_organization: Organization, test_song: Song, test_creator: Creator):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        split = RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=test_creator.id,
            rights_type="MASTER",
            share_percentage=0.0
        )
        db.add(split)
        db.commit()
        db.refresh(split)
        
        assert split.share_percentage == 0.0

    def test_rights_split_edge_case_one_hundred_percent(self, db: Session, test_organization: Organization, test_song: Song, test_creator: Creator):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        split = RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=test_creator.id,
            rights_type="MASTER",
            share_percentage=100.0
        )
        db.add(split)
        db.commit()
        db.refresh(split)
        
        assert split.share_percentage == 100.0

    def test_rights_split_decimal_percentage(self, db: Session, test_organization: Organization, test_song: Song, test_creator: Creator):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        split = RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=test_creator.id,
            rights_type="MASTER",
            share_percentage=50.5
        )
        db.add(split)
        db.commit()
        db.refresh(split)
        
        assert split.share_percentage == 50.5

    def test_multiple_splits_for_same_asset(self, db: Session, test_organization: Organization, test_song: Song, test_creator: Creator, test_creator_2: Creator):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        split1 = RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=test_creator.id,
            rights_type="MASTER",
            share_percentage=50.0
        )
        split2 = RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=test_creator_2.id,
            rights_type="MASTER",
            share_percentage=30.0
        )
        db.add(split1)
        db.add(split2)
        db.commit()
        
        splits = db.query(RightsSplit).filter(RightsSplit.contract_asset_id == asset.id).all()
        assert len(splits) == 2
        total = sum(s.share_percentage for s in splits)
        assert total == 80.0

    def test_multiple_splits_different_rights_types(self, db: Session, test_organization: Organization, test_song: Song, test_creator: Creator, test_creator_2: Creator):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        split1 = RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=test_creator.id,
            rights_type="MASTER",
            share_percentage=100.0
        )
        split2 = RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=test_creator_2.id,
            rights_type="PUBLISHING",
            share_percentage=100.0
        )
        db.add(split1)
        db.add(split2)
        db.commit()
        
        splits = db.query(RightsSplit).filter(RightsSplit.contract_asset_id == asset.id).all()
        assert len(splits) == 2
        assert any(s.rights_type == "MASTER" for s in splits)
        assert any(s.rights_type == "PUBLISHING" for s in splits)

    def test_rights_split_default_rights_type(self, db: Session, test_organization: Organization, test_song: Song, test_creator: Creator):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        split = RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=test_creator.id,
            share_percentage=100.0
        )
        db.add(split)
        db.commit()
        db.refresh(split)
        
        assert split.rights_type == "MASTER"


class TestContractCascadingDelete:
    def test_cascading_delete_rights_splits_when_asset_deleted(self, db: Session, test_organization: Organization, test_song: Song, test_creator: Creator):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        split1 = RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=test_creator.id,
            rights_type="MASTER",
            share_percentage=50.0
        )
        split2 = RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=test_creator.id,
            rights_type="PUBLISHING",
            share_percentage=50.0
        )
        db.add(split1)
        db.add(split2)
        db.commit()
        
        splits_before = db.query(RightsSplit).filter(RightsSplit.contract_asset_id == asset.id).all()
        assert len(splits_before) == 2
        
        db.delete(asset)
        db.commit()
        
        splits_after = db.query(RightsSplit).filter(RightsSplit.contract_asset_id == asset.id).all()
        assert len(splits_after) == 0

    def test_cascading_delete_contract_assets_when_contract_deleted(self, db: Session, test_organization: Organization, test_song: Song, test_creator: Creator):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        split = RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=test_creator.id,
            rights_type="MASTER",
            share_percentage=100.0
        )
        db.add(split)
        db.commit()
        
        assets_before = db.query(ContractAsset).filter(ContractAsset.contract_id == contract.id).all()
        assert len(assets_before) == 1
        
        db.delete(contract)
        db.commit()
        
        assets_after = db.query(ContractAsset).filter(ContractAsset.contract_id == contract.id).all()
        assert len(assets_after) == 0


class TestContractDataIntegrity:
    def test_territory_stored_as_json_list(self, db: Session, test_organization: Organization):
        territories = ["US", "CA", "UK", "AU"]
        contract = Contract(
            organization_id=test_organization.id,
            title="Contract with Territories",
            territory=territories
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        retrieved = db.query(Contract).filter(Contract.id == contract.id).first()
        assert retrieved.territory == territories
        assert isinstance(retrieved.territory, list)

    def test_territory_empty_list_default(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Contract without Territory"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        assert contract.territory == []
        assert isinstance(contract.territory, list)

    def test_advance_amount_as_float(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Contract with Advance",
            advance_amount=12345.67
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        assert contract.advance_amount == 12345.67
        assert isinstance(contract.advance_amount, float)

    def test_advance_recouped_as_float(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Contract with Recouped",
            advance_recouped=9876.54
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        assert contract.advance_recouped == 9876.54
        assert isinstance(contract.advance_recouped, float)

    def test_contract_nullable_fields(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Minimal Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        assert contract.reference_number is None
        assert contract.start_date is None
        assert contract.end_date is None
        assert contract.notes is None
        assert contract.terms_summary is None
        assert contract.created_by_user_id is None


class TestMultiTenantScoping:
    def test_contract_has_organization_id(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        assert contract.organization_id == test_organization.id
        assert contract.organization_id is not None

    def test_contracts_from_different_orgs_are_separate(self, db: Session, test_organization: Organization, test_organization_2: Organization):
        contract1 = Contract(
            organization_id=test_organization.id,
            title="Contract 1"
        )
        contract2 = Contract(
            organization_id=test_organization_2.id,
            title="Contract 2"
        )
        db.add(contract1)
        db.add(contract2)
        db.commit()
        db.refresh(contract1)
        db.refresh(contract2)
        
        org1_contracts = db.query(Contract).filter(Contract.organization_id == test_organization.id).all()
        org2_contracts = db.query(Contract).filter(Contract.organization_id == test_organization_2.id).all()
        
        assert len(org1_contracts) == 1
        assert len(org2_contracts) == 1
        assert org1_contracts[0].id != org2_contracts[0].id

    def test_contract_org_id_is_required(self, db: Session):
        contract = Contract(
            title="Contract without Org"
        )
        db.add(contract)
        
        with pytest.raises(Exception):
            db.commit()

    def test_contract_asset_inherits_contract_org_scope(self, db: Session, test_organization: Organization, test_song: Song):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        retrieved_contract = db.query(Contract).filter(Contract.id == asset.contract_id).first()
        assert retrieved_contract.organization_id == test_organization.id

    def test_contract_party_inherits_contract_org_scope(self, db: Session, test_organization: Organization):
        contract = Contract(
            organization_id=test_organization.id,
            title="Test Contract"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        party = ContractParty(
            contract_id=contract.id,
            party_name="Test Party"
        )
        db.add(party)
        db.commit()
        db.refresh(party)
        
        retrieved_contract = db.query(Contract).filter(Contract.id == party.contract_id).first()
        assert retrieved_contract.organization_id == test_organization.id


class TestContractWithPartiesAndAssets:
    def test_contract_with_party_and_asset(self, db: Session, test_organization: Organization, test_creator: Creator, test_song: Song):
        contract = Contract(
            organization_id=test_organization.id,
            title="Full Contract",
            contract_type="MASTER",
            status="ACTIVE"
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        party = ContractParty(
            contract_id=contract.id,
            party_name="Licensor",
            party_role="LICENSOR",
            creator_id=test_creator.id
        )
        db.add(party)
        db.commit()
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        retrieved_contract = db.query(Contract).filter(Contract.id == contract.id).first()
        assert len(retrieved_contract.parties) == 1
        assert len(retrieved_contract.assets) == 1
        assert retrieved_contract.parties[0].party_name == "Licensor"
        assert retrieved_contract.assets[0].asset_type == "SONG"

    def test_full_contract_workflow(self, db: Session, test_organization: Organization, test_creator: Creator, test_creator_2: Creator, test_song: Song):
        contract = Contract(
            organization_id=test_organization.id,
            title="Complete Contract",
            contract_type="MASTER",
            status="DRAFT",
            start_date=date(2024, 1, 1),
            end_date=date(2025, 12, 31),
            territory=["US", "CA"],
            advance_amount=50000.0,
            advance_recouped=10000.0
        )
        db.add(contract)
        db.commit()
        db.refresh(contract)
        
        party1 = ContractParty(
            contract_id=contract.id,
            party_name="Artist",
            party_role="ARTIST",
            creator_id=test_creator.id
        )
        party2 = ContractParty(
            contract_id=contract.id,
            party_name="Label",
            party_role="LABEL"
        )
        db.add(party1)
        db.add(party2)
        db.commit()
        
        asset = ContractAsset(
            contract_id=contract.id,
            asset_type="SONG",
            asset_id=test_song.id
        )
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        split1 = RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=test_creator.id,
            rights_type="MASTER",
            share_percentage=100.0
        )
        split2 = RightsSplit(
            contract_asset_id=asset.id,
            rights_holder_id=test_creator_2.id,
            rights_type="PUBLISHING",
            share_percentage=50.0
        )
        db.add(split1)
        db.add(split2)
        db.commit()
        
        retrieved = db.query(Contract).filter(Contract.id == contract.id).first()
        assert retrieved.title == "Complete Contract"
        assert len(retrieved.parties) == 2
        assert len(retrieved.assets) == 1
        
        splits = db.query(RightsSplit).filter(RightsSplit.contract_asset_id == asset.id).all()
        assert len(splits) == 2
