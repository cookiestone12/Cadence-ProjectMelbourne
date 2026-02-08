import pytest
from datetime import datetime, date
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from backend.main import app
from backend.models.database import Base
from backend.models.models import (
    User, Organization, OrganizationMember, Creator, Song, Work, WorkTrack,
    WorkCredit, Release, ReleaseTrack, SongCredit
)


SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
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
def test_song(db: Session, test_organization: Organization):
    song = Song(
        organization_id=test_organization.id,
        title="Test Song",
        primary_artist="Test Artist",
        isrc="US1234567890",
        iswc="T-123456789-0",
        project_title="Test Project",
        release_date=date(2024, 1, 15),
        status_health_score=75.0,
        has_contract_sent=True,
        has_contract_executed=True,
        is_registered_with_pro=True,
        is_registered_with_dsp=True,
        is_invoiced=True,
        is_paid=True,
        is_released=True,
        spotify_link="https://spotify.com/track/123",
        label="Test Label",
        publishing_percentage=50.0,
        master_percentage=50.0,
        advance_amount=5000.0,
        recording_code="REC001",
        master_paid="YES",
        soundexchange_registered="YES",
        payment_status="PAID",
        contract_location="/contracts/test.pdf",
        notes="Test notes",
        media_url="https://example.com/song.mp3"
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
        alternative_titles=["Alt Title 1", "Alt Title 2"],
        iswc="T-987654321-0",
        language="en",
        genre="POP",
        notes="Test work notes",
        lyrics="Test lyrics content"
    )
    db.add(work)
    db.commit()
    db.refresh(work)
    return work


@pytest.fixture(scope="function")
def test_release(db: Session, test_organization: Organization):
    release = Release(
        organization_id=test_organization.id,
        title="Test Release",
        release_type="ALBUM",
        status="DRAFT",
        primary_artist="Test Release Artist",
        label="Test Release Label",
        upc="123456789012",
        catalog_number="CAT001",
        release_date=date(2024, 6, 1),
        original_release_date=date(2023, 6, 1),
        genre="POP",
        subgenre="Indie Pop",
        cover_art_url="https://example.com/cover.jpg",
        description="Test release description",
        copyright_line="© 2024 Test Label",
        copyright_year=2024,
        notes="Test release notes",
        spotify_url="https://spotify.com/album/123",
        apple_music_url="https://music.apple.com/album/123"
    )
    db.add(release)
    db.commit()
    db.refresh(release)
    return release


class TestWorkModel:
    def test_work_creation_with_all_fields(self, db: Session, test_organization: Organization):
        work = Work(
            organization_id=test_organization.id,
            title="Complete Work",
            alternative_titles=["Alt 1", "Alt 2", "Alt 3"],
            iswc="T-111111111-1",
            language="en",
            genre="ROCK",
            notes="Comprehensive work notes",
            lyrics="Full lyrics here"
        )
        db.add(work)
        db.commit()
        db.refresh(work)
        
        assert work.id is not None
        assert work.title == "Complete Work"
        assert work.organization_id == test_organization.id
        assert work.iswc == "T-111111111-1"
        assert work.language == "en"
        assert work.genre == "ROCK"
        assert len(work.alternative_titles) == 3
        assert work.notes == "Comprehensive work notes"
        assert work.lyrics == "Full lyrics here"
        assert work.created_at is not None
        assert work.updated_at is not None

    def test_work_with_minimal_fields(self, db: Session, test_organization: Organization):
        work = Work(
            organization_id=test_organization.id,
            title="Minimal Work"
        )
        db.add(work)
        db.commit()
        db.refresh(work)
        
        assert work.id is not None
        assert work.title == "Minimal Work"
        assert work.iswc is None
        assert work.language is None
        assert work.alternative_titles == []


class TestReleaseModel:
    def test_release_creation_with_all_fields(self, db: Session, test_organization: Organization):
        release = Release(
            organization_id=test_organization.id,
            title="Complete Release",
            release_type="ALBUM",
            status="RELEASED",
            primary_artist="Release Artist",
            label="Release Label",
            upc="999999999999",
            catalog_number="CAT999",
            release_date=date(2024, 3, 15),
            original_release_date=date(2020, 3, 15),
            genre="HIP_HOP",
            subgenre="Trap",
            cover_art_url="https://example.com/full_cover.jpg",
            description="Full release description",
            copyright_line="© 2024 All Rights Reserved",
            copyright_year=2024,
            notes="Complete release notes",
            spotify_url="https://spotify.com/album/complete",
            apple_music_url="https://music.apple.com/album/complete"
        )
        db.add(release)
        db.commit()
        db.refresh(release)
        
        assert release.id is not None
        assert release.title == "Complete Release"
        assert release.release_type == "ALBUM"
        assert release.status == "RELEASED"
        assert release.upc == "999999999999"
        assert release.release_date == date(2024, 3, 15)
        assert release.original_release_date == date(2020, 3, 15)
        assert release.copyright_year == 2024
        assert release.spotify_url == "https://spotify.com/album/complete"
        assert release.apple_music_url == "https://music.apple.com/album/complete"

    def test_release_with_default_values(self, db: Session, test_organization: Organization):
        release = Release(
            organization_id=test_organization.id,
            title="Default Release"
        )
        db.add(release)
        db.commit()
        db.refresh(release)
        
        assert release.release_type == "SINGLE"
        assert release.status == "DRAFT"
        assert release.primary_artist is None
        assert release.upc is None


class TestWorkTrackLinking:
    def test_work_track_creation(self, db: Session, test_work: Work, test_song: Song):
        work_track = WorkTrack(
            work_id=test_work.id,
            song_id=test_song.id,
            is_primary=True
        )
        db.add(work_track)
        db.commit()
        db.refresh(work_track)
        
        assert work_track.id is not None
        assert work_track.work_id == test_work.id
        assert work_track.song_id == test_song.id
        assert work_track.is_primary is True
        assert work_track.created_at is not None

    def test_work_track_linking_multiple_songs(self, db: Session, test_organization: Organization, test_work: Work):
        songs = []
        for i in range(3):
            song = Song(
                organization_id=test_organization.id,
                title=f"Song {i+1}",
                primary_artist=f"Artist {i+1}"
            )
            db.add(song)
            db.commit()
            db.refresh(song)
            songs.append(song)
        
        tracks = []
        for idx, song in enumerate(songs):
            is_primary = idx == 0
            track = WorkTrack(
                work_id=test_work.id,
                song_id=song.id,
                is_primary=is_primary
            )
            db.add(track)
            tracks.append(track)
        
        db.commit()
        
        linked_tracks = db.query(WorkTrack).filter(WorkTrack.work_id == test_work.id).all()
        assert len(linked_tracks) == 3
        assert any(t.is_primary for t in linked_tracks)

    def test_work_track_defaults_to_primary(self, db: Session, test_work: Work, test_song: Song):
        work_track = WorkTrack(
            work_id=test_work.id,
            song_id=test_song.id
        )
        db.add(work_track)
        db.commit()
        db.refresh(work_track)
        
        assert work_track.is_primary is True


class TestReleaseTrackLinking:
    def test_release_track_creation(self, db: Session, test_release: Release, test_song: Song):
        release_track = ReleaseTrack(
            release_id=test_release.id,
            song_id=test_song.id,
            track_number=1,
            disc_number=1,
            is_bonus=False
        )
        db.add(release_track)
        db.commit()
        db.refresh(release_track)
        
        assert release_track.id is not None
        assert release_track.release_id == test_release.id
        assert release_track.song_id == test_song.id
        assert release_track.track_number == 1
        assert release_track.disc_number == 1
        assert release_track.is_bonus is False

    def test_release_track_bonus_track(self, db: Session, test_release: Release, test_song: Song):
        release_track = ReleaseTrack(
            release_id=test_release.id,
            song_id=test_song.id,
            track_number=99,
            disc_number=2,
            is_bonus=True
        )
        db.add(release_track)
        db.commit()
        db.refresh(release_track)
        
        assert release_track.is_bonus is True
        assert release_track.disc_number == 2

    def test_release_track_multiple_discs(self, db: Session, test_organization: Organization, test_release: Release):
        songs = []
        for i in range(4):
            song = Song(
                organization_id=test_organization.id,
                title=f"Album Song {i+1}",
                primary_artist="Album Artist"
            )
            db.add(song)
            db.commit()
            db.refresh(song)
            songs.append(song)
        
        tracks = []
        for idx, song in enumerate(songs):
            disc = 1 if idx < 2 else 2
            track_num = (idx % 2) + 1
            track = ReleaseTrack(
                release_id=test_release.id,
                song_id=song.id,
                track_number=track_num,
                disc_number=disc
            )
            db.add(track)
            tracks.append(track)
        
        db.commit()
        
        disc1_tracks = db.query(ReleaseTrack).filter(
            ReleaseTrack.release_id == test_release.id,
            ReleaseTrack.disc_number == 1
        ).all()
        disc2_tracks = db.query(ReleaseTrack).filter(
            ReleaseTrack.release_id == test_release.id,
            ReleaseTrack.disc_number == 2
        ).all()
        
        assert len(disc1_tracks) == 2
        assert len(disc2_tracks) == 2


class TestWorkCreditCreation:
    def test_work_credit_with_all_fields(self, db: Session, test_work: Work, test_creator: Creator):
        credit = WorkCredit(
            work_id=test_work.id,
            creator_id=test_creator.id,
            role="SONGWRITER",
            share_percentage=50.0,
            publisher_name="Test Publisher Inc"
        )
        db.add(credit)
        db.commit()
        db.refresh(credit)
        
        assert credit.id is not None
        assert credit.work_id == test_work.id
        assert credit.creator_id == test_creator.id
        assert credit.role == "SONGWRITER"
        assert credit.share_percentage == 50.0
        assert credit.publisher_name == "Test Publisher Inc"
        assert credit.created_at is not None

    def test_work_credit_without_optional_fields(self, db: Session, test_work: Work, test_creator: Creator):
        credit = WorkCredit(
            work_id=test_work.id,
            creator_id=test_creator.id,
            role="PRODUCER"
        )
        db.add(credit)
        db.commit()
        db.refresh(credit)
        
        assert credit.role == "PRODUCER"
        assert credit.share_percentage is None
        assert credit.publisher_name is None

    def test_work_credit_multiple_creators(self, db: Session, test_organization: Organization, test_work: Work):
        creators = []
        for i in range(2):
            creator = Creator(
                organization_id=test_organization.id,
                display_name=f"Creator {i+1}"
            )
            db.add(creator)
            db.commit()
            db.refresh(creator)
            creators.append(creator)
        
        credits = []
        for creator in creators:
            credit = WorkCredit(
                work_id=test_work.id,
                creator_id=creator.id,
                role="SONGWRITER",
                share_percentage=50.0
            )
            db.add(credit)
            credits.append(credit)
        
        db.commit()
        
        work_credits = db.query(WorkCredit).filter(WorkCredit.work_id == test_work.id).all()
        assert len(work_credits) == 2
        total_share = sum(c.share_percentage for c in work_credits)
        assert total_share == 100.0


class TestCreatorNewFields:
    def test_creator_with_contributor_type(self, db: Session, test_organization: Organization):
        creator = Creator(
            organization_id=test_organization.id,
            display_name="Contributor Creator",
            contributor_type="PUBLISHER"
        )
        db.add(creator)
        db.commit()
        db.refresh(creator)
        
        assert creator.contributor_type == "PUBLISHER"

    def test_creator_with_publisher_name(self, db: Session, test_organization: Organization):
        creator = Creator(
            organization_id=test_organization.id,
            display_name="Publisher Creator",
            publisher_name="My Publishing Company"
        )
        db.add(creator)
        db.commit()
        db.refresh(creator)
        
        assert creator.publisher_name == "My Publishing Company"

    def test_creator_with_all_new_fields(self, db: Session, test_organization: Organization):
        creator = Creator(
            organization_id=test_organization.id,
            display_name="Full Featured Creator",
            legal_name="Legal Name Inc",
            email="creator@test.com",
            roles=["SONGWRITER", "PRODUCER"],
            primary_territory="UK",
            primary_pro="PRS",
            primary_ipi="123456789000",
            contributor_type="LABEL",
            phone="+44123456789",
            publisher_name="Global Publishing",
            label_affiliation="Independent",
            bio="Experienced music professional",
            website_url="https://creator.example.com",
            spotify_artist_id="spotify_xyz",
            apple_music_id="applemusic_xyz"
        )
        db.add(creator)
        db.commit()
        db.refresh(creator)
        
        assert creator.display_name == "Full Featured Creator"
        assert creator.contributor_type == "LABEL"
        assert creator.publisher_name == "Global Publishing"
        assert creator.phone == "+44123456789"
        assert creator.bio == "Experienced music professional"
        assert creator.spotify_artist_id == "spotify_xyz"
        assert creator.apple_music_id == "applemusic_xyz"


class TestISRCValidation:
    def validate_isrc(self, isrc: str) -> bool:
        if not isrc:
            return False
        
        isrc_clean = isrc.replace('-', '')
        
        if len(isrc_clean) != 12:
            return False
        
        country_code = isrc_clean[:2]
        registrant = isrc_clean[2:5]
        year = isrc_clean[5:7]
        serial = isrc_clean[7:12]
        
        if not country_code.isalpha():
            return False
        
        if not registrant.isalnum():
            return False
        
        if not year.isdigit():
            return False
        
        if not serial.isdigit():
            return False
        
        return True

    def test_valid_isrc_format(self):
        assert self.validate_isrc("US-ABC-12-12345") is True
        assert self.validate_isrc("GB-XYZ-99-99999") is True
        assert self.validate_isrc("FR-DEF-00-00001") is True

    def test_invalid_isrc_too_short(self):
        assert self.validate_isrc("US-ABC-12-1234") is False

    def test_invalid_isrc_wrong_separators(self):
        assert self.validate_isrc("US_ABC_12_12345") is False

    def test_invalid_isrc_non_alpha_country(self):
        assert self.validate_isrc("12-ABC-12-12345") is False

    def test_invalid_isrc_non_numeric_year(self):
        assert self.validate_isrc("US-ABC-AB-12345") is False

    def test_invalid_isrc_non_numeric_serial(self):
        assert self.validate_isrc("US-ABC-12-1234A") is False


class TestISWCValidation:
    def validate_iswc(self, iswc: str) -> bool:
        if not iswc:
            return False
        
        iswc_clean = iswc.replace('-', '')
        
        if len(iswc_clean) != 11:
            return False
        
        if iswc_clean[0] != 'T':
            return False
        
        number = iswc_clean[1:10]
        check = iswc_clean[10]
        
        if not number.isdigit():
            return False
        
        if not check.isalnum():
            return False
        
        return True

    def test_valid_iswc_format(self):
        assert self.validate_iswc("T-123456789-0") is True
        assert self.validate_iswc("T-999999999-Z") is True
        assert self.validate_iswc("T-000000001-A") is True

    def test_invalid_iswc_wrong_prefix(self):
        assert self.validate_iswc("S-123456789-0") is False
        assert self.validate_iswc("U-123456789-0") is False

    def test_invalid_iswc_wrong_length(self):
        assert self.validate_iswc("T-12345678-0") is False
        assert self.validate_iswc("T-1234567890-0") is False

    def test_invalid_iswc_non_numeric_number(self):
        assert self.validate_iswc("T-12345678A-0") is False

    def test_invalid_iswc_wrong_separators(self):
        assert self.validate_iswc("T_123456789_0") is False


class TestBulkUpdateWhitelist:
    def get_allowed_bulk_fields(self) -> set:
        return {
            "label", "publishing_percentage", "master_percentage",
            "is_released", "notes", "project_title",
            "is_registered_with_pro", "is_registered_with_dsp",
            "has_contract_sent", "has_contract_executed",
            "is_invoiced", "is_paid", "soundexchange_registered",
            "payment_status", "master_paid",
        }

    def test_allowed_field_label(self):
        allowed = self.get_allowed_bulk_fields()
        assert "label" in allowed

    def test_allowed_field_publishing_percentage(self):
        allowed = self.get_allowed_bulk_fields()
        assert "publishing_percentage" in allowed

    def test_allowed_field_notes(self):
        allowed = self.get_allowed_bulk_fields()
        assert "notes" in allowed

    def test_disallowed_field_title(self):
        allowed = self.get_allowed_bulk_fields()
        assert "title" not in allowed

    def test_disallowed_field_primary_artist(self):
        allowed = self.get_allowed_bulk_fields()
        assert "primary_artist" not in allowed

    def test_disallowed_field_isrc(self):
        allowed = self.get_allowed_bulk_fields()
        assert "isrc" not in allowed

    def test_disallowed_field_iswc(self):
        allowed = self.get_allowed_bulk_fields()
        assert "iswc" not in allowed

    def test_check_invalid_fields_in_update(self):
        allowed = self.get_allowed_bulk_fields()
        update_fields = {"label", "title", "primary_artist"}
        invalid = update_fields - allowed
        
        assert len(invalid) == 2
        assert "title" in invalid
        assert "primary_artist" in invalid


class TestReleaseHealthScoreCalculation:
    def calculate_release_health(self, release: Release, tracks: list) -> dict:
        issues = []
        
        if not release.upc:
            issues.append("Missing UPC/EAN code")
        if not release.release_date:
            issues.append("No release date set")
        if not release.primary_artist:
            issues.append("No primary artist")
        if not release.label:
            issues.append("No label specified")
        if not release.cover_art_url:
            issues.append("No cover art")
        if len(tracks) == 0:
            issues.append("No tracks added")
        
        total_checks = 6 + len(tracks)
        passed = total_checks - len(issues)
        score = round((passed / total_checks) * 100, 1) if total_checks > 0 else 0
        
        return {"score": score, "issues": issues, "total_checks": total_checks, "passed": passed}

    def test_release_health_score_complete(self, db: Session, test_organization: Organization):
        release = Release(
            organization_id=test_organization.id,
            title="Complete Release",
            upc="123456789012",
            release_date=date(2024, 6, 1),
            primary_artist="Artist",
            label="Label",
            cover_art_url="https://example.com/cover.jpg"
        )
        db.add(release)
        db.commit()
        
        song = Song(
            organization_id=test_organization.id,
            title="Track 1",
            primary_artist="Artist",
            isrc="US1234567890"
        )
        db.add(song)
        db.commit()
        db.refresh(song)
        
        track = ReleaseTrack(
            release_id=release.id,
            song_id=song.id,
            track_number=1
        )
        db.add(track)
        db.commit()
        
        tracks = [track]
        health = self.calculate_release_health(release, tracks)
        
        assert health["score"] == 100.0
        assert len(health["issues"]) == 0
        assert health["passed"] == 7

    def test_release_health_score_missing_upc(self):
        release = Release(
            organization_id=1,
            title="No UPC",
            release_date=date(2024, 6, 1),
            primary_artist="Artist",
            label="Label",
            cover_art_url="https://example.com/cover.jpg"
        )
        
        health = self.calculate_release_health(release, [])
        
        assert health["score"] < 100.0
        assert "Missing UPC/EAN code" in health["issues"]

    def test_release_health_score_missing_multiple_fields(self):
        release = Release(
            organization_id=1,
            title="Incomplete"
        )
        
        health = self.calculate_release_health(release, [])
        
        assert health["score"] == 0.0
        assert len(health["issues"]) == 6
        assert "Missing UPC/EAN code" in health["issues"]
        assert "No release date set" in health["issues"]
        assert "No primary artist" in health["issues"]

    def test_release_health_score_with_multiple_tracks(self):
        release = Release(
            organization_id=1,
            title="Multi-track",
            upc="123456789012",
            release_date=date(2024, 6, 1),
            primary_artist="Artist",
            label="Label",
            cover_art_url="https://example.com/cover.jpg"
        )
        
        tracks = [MagicMock(), MagicMock(), MagicMock()]
        health = self.calculate_release_health(release, tracks)
        
        assert health["score"] == 100.0
        assert health["total_checks"] == 9
        assert health["passed"] == 9


class TestBulkEditFieldValidation:
    def validate_bulk_update_fields(self, fields_to_update: dict, allowed_fields: set) -> dict:
        invalid_fields = set(fields_to_update.keys()) - allowed_fields
        
        return {
            "is_valid": len(invalid_fields) == 0,
            "invalid_fields": list(invalid_fields),
            "valid_fields": list(set(fields_to_update.keys()) - invalid_fields)
        }

    def test_bulk_edit_rejects_title_change(self):
        allowed = {
            "label", "publishing_percentage", "master_percentage",
            "is_released", "notes", "project_title"
        }
        
        update_fields = {"title": "New Title"}
        result = self.validate_bulk_update_fields(update_fields, allowed)
        
        assert result["is_valid"] is False
        assert "title" in result["invalid_fields"]

    def test_bulk_edit_rejects_isrc_change(self):
        allowed = {
            "label", "publishing_percentage", "master_percentage",
            "is_released", "notes", "project_title"
        }
        
        update_fields = {"isrc": "US9876543210"}
        result = self.validate_bulk_update_fields(update_fields, allowed)
        
        assert result["is_valid"] is False
        assert "isrc" in result["invalid_fields"]

    def test_bulk_edit_allows_notes(self):
        allowed = {
            "label", "publishing_percentage", "master_percentage",
            "is_released", "notes", "project_title"
        }
        
        update_fields = {"notes": "Updated notes"}
        result = self.validate_bulk_update_fields(update_fields, allowed)
        
        assert result["is_valid"] is True
        assert len(result["invalid_fields"]) == 0
        assert "notes" in result["valid_fields"]

    def test_bulk_edit_allows_multiple_valid_fields(self):
        allowed = {
            "label", "publishing_percentage", "master_percentage",
            "is_released", "notes", "project_title"
        }
        
        update_fields = {
            "label": "New Label",
            "publishing_percentage": 60.0,
            "notes": "Updated"
        }
        result = self.validate_bulk_update_fields(update_fields, allowed)
        
        assert result["is_valid"] is True
        assert len(result["valid_fields"]) == 3

    def test_bulk_edit_mixed_valid_invalid(self):
        allowed = {
            "label", "publishing_percentage", "master_percentage",
            "is_released", "notes", "project_title"
        }
        
        update_fields = {
            "label": "New Label",
            "title": "New Title",
            "primary_artist": "New Artist"
        }
        result = self.validate_bulk_update_fields(update_fields, allowed)
        
        assert result["is_valid"] is False
        assert len(result["invalid_fields"]) == 2
        assert "title" in result["invalid_fields"]
        assert "primary_artist" in result["invalid_fields"]
        assert "label" in result["valid_fields"]
