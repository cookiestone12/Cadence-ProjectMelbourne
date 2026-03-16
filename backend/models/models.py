from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum as SQLEnum, Date, UniqueConstraint, Index, LargeBinary, text
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base
import enum

class OrganizationType(str, enum.Enum):
    LABEL = "LABEL"
    PUBLISHER = "PUBLISHER"
    PRODUCTION_COMPANY = "PRODUCTION_COMPANY"
    MANAGER = "MANAGER"
    INDIVIDUAL = "INDIVIDUAL"

class OrganizationMemberRole(str, enum.Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    CLIENT = "CLIENT"

class CreatorRole(str, enum.Enum):
    ARTIST = "ARTIST"
    SONGWRITER = "SONGWRITER"
    PRODUCER = "PRODUCER"

class CreditRole(str, enum.Enum):
    ARTIST = "ARTIST"
    FEATURED_ARTIST = "FEATURED_ARTIST"
    SONGWRITER = "SONGWRITER"
    PRODUCER = "PRODUCER"
    MIX_ENGINEER = "MIX_ENGINEER"
    OTHER = "OTHER"

class CreatorContactRole(str, enum.Enum):
    DISTRIBUTION = "DISTRIBUTION"
    LEGAL = "LEGAL"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    PUBLISHER = "PUBLISHER"
    A_AND_R = "A_AND_R"
    MARKETING = "MARKETING"
    OTHER = "OTHER"

class DSPPlatform(str, enum.Enum):
    APPLE_MUSIC = "APPLE_MUSIC"
    SPOTIFY = "SPOTIFY"
    YOUTUBE_MUSIC = "YOUTUBE_MUSIC"
    OTHER = "OTHER"

class ChecklistStatus(str, enum.Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"

class ChecklistCategory(str, enum.Enum):
    ADMIN = "ADMIN"
    LEGAL = "LEGAL"
    METADATA = "METADATA"
    DSP = "DSP"
    SYNC = "SYNC"
    PAYMENT = "PAYMENT"

class ValuationSource(str, enum.Enum):
    MANUAL = "MANUAL"
    LUMINATE = "LUMINATE"
    EXTERNAL = "EXTERNAL"

class PRO(str, enum.Enum):
    ASCAP = "ASCAP"
    BMI = "BMI"
    PRS = "PRS"
    SESAC = "SESAC"
    OTHER = "OTHER"

class AccountType(str, enum.Enum):
    INDIVIDUAL = "INDIVIDUAL"
    ENTERPRISE = "ENTERPRISE"

class AccountLinkStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"

class AccountLinkPermission(str, enum.Enum):
    VIEW_ONLY = "VIEW_ONLY"
    EDIT = "EDIT"
    FULL_ACCESS = "FULL_ACCESS"

class IPAssetType(str, enum.Enum):
    TRACK = "TRACK"
    VIDEO = "VIDEO"
    PODCAST = "PODCAST"
    AUDIOBOOK = "AUDIOBOOK"
    OTHER = "OTHER"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    is_super_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login_at = Column(DateTime, nullable=True)
    
    organization_memberships = relationship("OrganizationMember", back_populates="user")

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String)
    account_type = Column(String, default="ENTERPRISE")
    
    display_name = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    logo_orientation = Column(String, default="square")
    primary_color = Column(String, nullable=True)
    
    access_code = Column(String, unique=True, nullable=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    members = relationship("OrganizationMember", back_populates="organization")
    creators = relationship("Creator", back_populates="organization")
    songs = relationship("Song", back_populates="organization")

class OrganizationMember(Base):
    __tablename__ = "organization_members"
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    can_manage_roster = Column(Boolean, default=False)
    linked_creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    client_access_scope = Column(String, nullable=True, default="OWN")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="organization_memberships")
    linked_creator = relationship("Creator", foreign_keys=[linked_creator_id])

class ContributorType(str, enum.Enum):
    ARTIST = "ARTIST"
    SONGWRITER = "SONGWRITER"
    PRODUCER = "PRODUCER"
    PUBLISHER = "PUBLISHER"
    LABEL = "LABEL"
    MANAGER = "MANAGER"
    ENGINEER = "ENGINEER"
    OTHER = "OTHER"

class ReleaseType(str, enum.Enum):
    SINGLE = "SINGLE"
    EP = "EP"
    ALBUM = "ALBUM"
    COMPILATION = "COMPILATION"
    MIXTAPE = "MIXTAPE"
    OTHER = "OTHER"

class ReleaseStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    READY = "READY"
    SUBMITTED = "SUBMITTED"
    RELEASED = "RELEASED"

class Creator(Base):
    __tablename__ = "creators"
    __table_args__ = (
        Index('ix_creators_organization_id', 'organization_id'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    display_name = Column(String, index=True, nullable=False)
    legal_name = Column(String, nullable=True)
    email = Column(String, nullable=True, index=True)
    roles = Column(JSON, default=list)
    primary_territory = Column(String, nullable=True)
    primary_pro = Column(String, nullable=True)
    primary_ipi = Column(String, nullable=True)
    hero_image_url = Column(String, nullable=True)
    hero_image_data = Column(LargeBinary, nullable=True)
    hero_image_mime = Column(String, nullable=True)
    linked_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    contributor_type = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    publisher_name = Column(String, nullable=True)
    label_affiliation = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    website_url = Column(String, nullable=True)
    spotify_artist_id = Column(String, nullable=True)
    apple_music_id = Column(String, nullable=True)
    spotify_url = Column(String, nullable=True)
    apple_music_url = Column(String, nullable=True)
    youtube_url = Column(String, nullable=True)
    instagram_url = Column(String, nullable=True)
    twitter_url = Column(String, nullable=True)
    custom_links = Column(JSON, default=list)
    roster_export_fields = Column(JSON, default=list)
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    publisher_contact_id = Column(Integer, nullable=True)
    admin_contact_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization", back_populates="creators")
    song_credits = relationship("SongCredit", back_populates="creator")
    work_credits = relationship("WorkCredit", back_populates="creator")
    linked_user = relationship("User", foreign_keys=[linked_user_id])
    assigned_user = relationship("User", foreign_keys=[assigned_to_user_id])
    creator_contacts = relationship("CreatorContact", back_populates="creator", cascade="all, delete-orphan")

class CreatorContact(Base):
    __tablename__ = "creator_contacts"
    __table_args__ = (
        UniqueConstraint('creator_id', 'contact_id', 'role', name='uq_creator_contact_role'),
        Index('ix_creator_contacts_creator_id', 'creator_id'),
        Index('ix_creator_contacts_contact_id', 'contact_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id", ondelete="CASCADE"), nullable=False)
    contact_id = Column(Integer, ForeignKey("creative_contacts.id", ondelete="CASCADE"), nullable=False)
    role = Column(String, nullable=False, default="OTHER")
    is_primary = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("Creator", back_populates="creator_contacts")
    contact = relationship("CreativeContact")

class CreativeContact(Base):
    __tablename__ = "creative_contacts"
    __table_args__ = (
        Index('ix_creative_contacts_organization_id', 'organization_id'),
        Index('ix_creative_contacts_creator_id', 'creator_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    display_name = Column(String, nullable=False, index=True)
    legal_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    pro = Column(String, nullable=True)
    ipi = Column(String, nullable=True)
    isni = Column(String, nullable=True)
    publisher_name = Column(String, nullable=True)
    publisher_ipi = Column(String, nullable=True)
    publisher_pro = Column(String, nullable=True)
    roles = Column(JSON, default=list)
    representation_name = Column(String, nullable=True)
    representation_email = Column(String, nullable=True)
    representation_phone = Column(String, nullable=True)
    territory = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    photo_url = Column(String, nullable=True)
    photo_data = Column(LargeBinary, nullable=True)
    photo_mime = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SharedContactLink(Base):
    __tablename__ = "shared_contact_links"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    contact_ids = Column(JSON, nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Song(Base):
    __tablename__ = "songs"
    __table_args__ = (
        Index('ix_songs_organization_id', 'organization_id'),
        Index('ix_songs_org_health', 'organization_id', 'status_health_score'),
        Index('ix_songs_org_asset_type', 'organization_id', 'asset_type'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    asset_type = Column(String, default="TRACK", nullable=False, index=True)
    title = Column(String, index=True, nullable=False)
    primary_artist = Column(String, nullable=False)
    isrc = Column(String, nullable=True)
    iswc = Column(String, nullable=True)
    project_title = Column(String, nullable=True)
    release_date = Column(Date, nullable=True)
    
    status_health_score = Column(Float, default=0.0)
    has_contract_sent = Column(Boolean, default=False)
    has_contract_executed = Column(Boolean, default=False)
    is_registered_with_pro = Column(Boolean, default=False)
    is_registered_with_dsp = Column(String, default="No", nullable=True)
    is_invoiced = Column(String, default="No", nullable=True)
    is_paid = Column(String, default="No", nullable=True)
    
    is_released = Column(Boolean, default=False)
    spotify_link = Column(String, nullable=True)
    label = Column(String, nullable=True)
    publishing_percentage = Column(Float, nullable=True)
    master_percentage = Column(Float, nullable=True)
    advance_amount = Column(Float, nullable=True)
    recording_code = Column(String, nullable=True)
    
    master_paid = Column(String, nullable=True)
    soundexchange_registered = Column(String, nullable=True)
    mlc_registered = Column(String, nullable=True)
    payment_status = Column(String, nullable=True)
    contract_location = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    
    media_url = Column(String, nullable=True)
    audio_file_url = Column(String, nullable=True)
    lyrics = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization", back_populates="songs")
    credits = relationship("SongCredit", back_populates="song", cascade="all, delete-orphan")
    dsp_links = relationship("SongDSPLink", back_populates="song", cascade="all, delete-orphan")
    checklist_statuses = relationship("SongChecklistStatus", back_populates="song", cascade="all, delete-orphan")
    valuation_snapshots = relationship("SongValuationSnapshot", back_populates="song", cascade="all, delete-orphan")
    analytics = relationship("Analytics", back_populates="song", uselist=False, cascade="all, delete-orphan")
    streaming_metrics = relationship("SongStreamingMetrics", back_populates="song", cascade="all, delete-orphan")
    territory_revenues = relationship("TerritoryRevenue", back_populates="song", cascade="all, delete-orphan")
    valuation_calculations = relationship("ValuationCalculation", back_populates="song", cascade="all, delete-orphan")
    contracts = relationship("SongContract", back_populates="song", cascade="all, delete-orphan")
    work_tracks = relationship("WorkTrack", back_populates="song", cascade="all, delete-orphan")
    release_tracks = relationship("ReleaseTrack", back_populates="song", cascade="all, delete-orphan")


class Work(Base):
    __tablename__ = "works"
    __table_args__ = (
        Index('ix_works_organization_id', 'organization_id'),
        Index('ix_works_iswc', 'iswc'),
        UniqueConstraint('organization_id', 'iswc', name='uq_works_org_iswc'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    asset_type = Column(String, default="TRACK", nullable=False)
    work_type = Column(String, default="TRACK", nullable=False)
    title = Column(String, index=True, nullable=False)
    alternative_titles = Column(JSON, default=list)
    iswc = Column(String, nullable=True)
    language = Column(String, nullable=True)
    genre = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    lyrics = Column(Text, nullable=True)
    folder_id = Column(Integer, ForeignKey("work_folders.id"), nullable=True)
    is_registered_with_pro = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    folder = relationship("WorkFolder", back_populates="works")
    work_tracks = relationship("WorkTrack", back_populates="work", cascade="all, delete-orphan")
    credits = relationship("WorkCredit", back_populates="work", cascade="all, delete-orphan")


class WorkFolder(Base):
    __tablename__ = "work_folders"
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    name = Column(String, nullable=False)
    parent_folder_id = Column(Integer, ForeignKey("work_folders.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    organization = relationship("Organization")
    works = relationship("Work", back_populates="folder")


class WorkTrack(Base):
    __tablename__ = "work_tracks"
    __table_args__ = (
        UniqueConstraint('work_id', 'song_id', name='uq_work_track'),
        Index('ix_work_tracks_work_id', 'work_id'),
        Index('ix_work_tracks_song_id', 'song_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    work_id = Column(Integer, ForeignKey("works.id"), nullable=False)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    is_primary = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    work = relationship("Work", back_populates="work_tracks")
    song = relationship("Song", back_populates="work_tracks")


class WorkCredit(Base):
    __tablename__ = "work_credits"
    __table_args__ = (
        Index('ix_work_credits_work_id', 'work_id'),
        Index('ix_work_credits_creator_id', 'creator_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    work_id = Column(Integer, ForeignKey("works.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    role = Column(String, nullable=False)
    share_percentage = Column(Float, nullable=True)
    publisher_name = Column(String, nullable=True)
    creative_contact_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    work = relationship("Work", back_populates="credits")
    creator = relationship("Creator", back_populates="work_credits")


class Release(Base):
    __tablename__ = "releases"
    __table_args__ = (
        Index('ix_releases_organization_id', 'organization_id'),
        Index('ix_releases_upc', 'upc'),
        UniqueConstraint('organization_id', 'upc', name='uq_releases_org_upc'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    asset_type = Column(String, default="TRACK", nullable=False)
    title = Column(String, index=True, nullable=False)
    release_type = Column(String, default="SINGLE")
    status = Column(String, default="DRAFT")

    primary_artist = Column(String, nullable=True)
    label = Column(String, nullable=True)
    upc = Column(String, nullable=True)
    catalog_number = Column(String, nullable=True)
    release_date = Column(Date, nullable=True)
    original_release_date = Column(Date, nullable=True)
    genre = Column(String, nullable=True)
    subgenre = Column(String, nullable=True)
    cover_art_url = Column(String, nullable=True)
    cover_art_data = Column(LargeBinary, nullable=True)
    cover_art_mime = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    copyright_line = Column(String, nullable=True)
    copyright_year = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True, index=True)

    spotify_url = Column(String, nullable=True)
    apple_music_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    creator = relationship("Creator", backref="releases")
    release_tracks = relationship("ReleaseTrack", back_populates="release", cascade="all, delete-orphan", order_by="ReleaseTrack.disc_number, ReleaseTrack.track_number")


class ReleaseTrack(Base):
    __tablename__ = "release_tracks"
    __table_args__ = (
        UniqueConstraint('release_id', 'song_id', name='uq_release_track'),
        Index('ix_release_tracks_release_id', 'release_id'),
        Index('ix_release_tracks_song_id', 'song_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    release_id = Column(Integer, ForeignKey("releases.id"), nullable=False)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    track_number = Column(Integer, nullable=False, default=1)
    disc_number = Column(Integer, nullable=False, default=1)
    is_bonus = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    release = relationship("Release", back_populates="release_tracks")
    song = relationship("Song", back_populates="release_tracks")


class SongCredit(Base):
    __tablename__ = "song_credits"
    
    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    share_percentage = Column(Float, nullable=True)
    pub_share = Column(Float, nullable=True)
    master_share = Column(Float, nullable=True)
    creative_contact_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    song = relationship("Song", back_populates="credits")
    creator = relationship("Creator", back_populates="song_credits")

class SongDSPLink(Base):
    __tablename__ = "song_dsp_links"
    
    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, index=True)
    platform = Column(String, nullable=False)
    url = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    song = relationship("Song", back_populates="dsp_links")

class ChecklistItem(Base):
    __tablename__ = "checklist_items"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)
    category = Column(String)
    description = Column(Text)
    weight = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    song_statuses = relationship("SongChecklistStatus", back_populates="checklist_item")

class SongChecklistStatus(Base):
    __tablename__ = "song_checklist_status"
    __table_args__ = (
        UniqueConstraint('song_id', 'checklist_item_id', name='uq_song_checklist'),
        Index('ix_song_checklist_song_id', 'song_id'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    checklist_item_id = Column(Integer, ForeignKey("checklist_items.id"), nullable=False)
    status = Column(String, nullable=False, default="NOT_STARTED")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    song = relationship("Song", back_populates="checklist_statuses")
    checklist_item = relationship("ChecklistItem", back_populates="song_statuses")

class SongValuationSnapshot(Base):
    __tablename__ = "song_valuation_snapshots"
    
    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, index=True)
    valuation_cents = Column(Integer, nullable=True)
    source = Column(String, nullable=False, default="MANUAL")
    snapshot_date = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text, nullable=True)
    
    song = relationship("Song", back_populates="valuation_snapshots")

class Analytics(Base):
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), unique=True, nullable=False)
    
    spotify_streams = Column(Integer, default=0)
    spotify_monthly_listeners = Column(Integer, default=0)
    chartmetric_score = Column(Float, default=0.0)
    playlist_count = Column(Integer, default=0)
    top_playlists = Column(JSON, default=list)
    
    regional_data = Column(JSON, default=dict)
    trend_data = Column(JSON, default=dict)
    
    streams_by_type = Column(JSON, default=dict)
    territory_streams = Column(JSON, default=dict)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    song = relationship("Song", back_populates="analytics")

class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Songwriter(Base):
    __tablename__ = "songwriters"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    pro_affiliation = Column(String, nullable=True)
    ipi_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Catalog(Base):
    __tablename__ = "catalogs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class SongStreamingMetrics(Base):
    __tablename__ = "song_streaming_metrics"
    __table_args__ = (
        Index('ix_streaming_metrics_song_id', 'song_id'),
        Index('ix_streaming_metrics_period_date', 'period_date'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    
    period_date = Column(Date, nullable=False)
    
    total_streams = Column(Integer, default=0)
    ad_supported_streams = Column(Integer, default=0)
    premium_streams = Column(Integer, default=0)
    interactive_streams = Column(Integer, default=0)
    on_demand_streams = Column(Integer, default=0)
    programmed_streams = Column(Integer, default=0)
    audio_streams = Column(Integer, default=0)
    video_streams = Column(Integer, default=0)
    
    song_sales = Column(Integer, default=0)
    
    ownership_percentage = Column(Float, default=1.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    song = relationship("Song", back_populates="streaming_metrics")
    organization = relationship("Organization")

class TerritoryRevenue(Base):
    __tablename__ = "territory_revenue"
    __table_args__ = (
        Index('ix_territory_revenue_song_id', 'song_id'),
        Index('ix_territory_revenue_period', 'period_date'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    
    period_date = Column(Date, nullable=False)
    territory_code = Column(String(3), nullable=False)
    territory_name = Column(String, nullable=False)
    
    total_streams = Column(Integer, default=0)
    publishing_revenue_cents = Column(Integer, default=0)
    master_revenue_cents = Column(Integer, default=0)
    total_revenue_cents = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    song = relationship("Song", back_populates="territory_revenues")
    organization = relationship("Organization")

class ValuationCalculation(Base):
    __tablename__ = "valuation_calculations"
    __table_args__ = (
        Index('ix_valuation_calc_song_id', 'song_id'),
        Index('ix_valuation_calc_date', 'calculation_date'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    
    calculation_date = Column(DateTime, default=datetime.utcnow)
    
    streaming_multiple_value_cents = Column(Integer, default=0)
    revenue_multiple_value_cents = Column(Integer, default=0)
    market_comp_value_cents = Column(Integer, default=0)
    black_box_value_cents = Column(Integer, default=0)
    
    final_valuation_cents = Column(Integer, default=0)
    valuation_methodology = Column(String, default="HYBRID")
    
    thirty_day_revenue_cents = Column(Integer, default=0)
    ninety_day_revenue_cents = Column(Integer, default=0)
    annual_revenue_cents = Column(Integer, default=0)
    
    growth_rate = Column(Float, default=0.0)
    risk_score = Column(Float, default=0.5)
    
    calc_metadata = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    song = relationship("Song", back_populates="valuation_calculations")
    organization = relationship("Organization")

class AccountLink(Base):
    __tablename__ = "account_links"
    __table_args__ = (
        Index('ix_account_links_individual', 'individual_org_id'),
        Index('ix_account_links_enterprise', 'enterprise_org_id'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    individual_org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    enterprise_org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    status = Column(String, default="PENDING")
    permission_level = Column(String, default="VIEW_ONLY")
    
    initiated_by = Column(String, nullable=False)
    individual_consent = Column(Boolean, default=False)
    enterprise_consent = Column(Boolean, default=False)
    
    agreement_terms = Column(Text, nullable=True)
    start_date = Column(DateTime, nullable=True)
    expiration_date = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    individual_org = relationship("Organization", foreign_keys=[individual_org_id])
    enterprise_org = relationship("Organization", foreign_keys=[enterprise_org_id])

class SongContract(Base):
    __tablename__ = "song_contracts"
    __table_args__ = (
        Index('ix_song_contracts_song_id', 'song_id'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String, default="application/pdf")
    
    contract_type = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    
    song = relationship("Song", back_populates="contracts")
    organization = relationship("Organization")
    uploaded_by = relationship("User")
    contract = relationship("Contract")


class NotificationType(str, enum.Enum):
    MISSING_ISRC = "MISSING_ISRC"
    MISSING_ISWC = "MISSING_ISWC"
    CONTRACT_PENDING = "CONTRACT_PENDING"
    PRO_INCOMPLETE = "PRO_INCOMPLETE"
    WEEKLY_HEALTH_SUMMARY = "WEEKLY_HEALTH_SUMMARY"
    CUSTOM_DEADLINE = "CUSTOM_DEADLINE"
    SYSTEM_ANNOUNCEMENT = "SYSTEM_ANNOUNCEMENT"
    CATALOG_UPDATE = "CATALOG_UPDATE"
    PLACEMENT_UPDATE = "PLACEMENT_UPDATE"
    CLIENT_SHARE = "CLIENT_SHARE"


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"
    __table_args__ = (
        UniqueConstraint('user_id', 'notification_type', name='uq_user_notification_type'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(String, nullable=False)
    
    in_app_enabled = Column(Boolean, default=True)
    email_enabled = Column(Boolean, default=False)
    
    frequency = Column(String, default="immediate")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User")


class OrgNotificationSetting(Base):
    __tablename__ = "org_notification_settings"
    __table_args__ = (
        UniqueConstraint('organization_id', 'notification_type', name='uq_org_notification_type'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    notification_type = Column(String, nullable=False)
    
    default_frequency = Column(String, default="immediate")
    allow_user_override = Column(Boolean, default=True)
    
    rollup_digest_enabled = Column(Boolean, default=False)
    digest_frequency = Column(String, default="weekly")
    digest_day = Column(Integer, default=1)
    digest_hour = Column(Integer, default=9)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization")


class EmailDigestPreference(Base):
    __tablename__ = "email_digest_preferences"
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_user_email_digest'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    email_digest_enabled = Column(Boolean, default=False)
    schedule_interval = Column(String, default="weekly")
    min_priority_threshold = Column(Integer, default=3)
    preferred_hour = Column(Integer, default=9)

    last_email_sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")


class ActionItem(Base):
    __tablename__ = "action_items"
    __table_args__ = (
        Index('ix_action_items_org_creator', 'organization_id', 'creator_id'),
        Index('ix_action_items_priority', 'organization_id', 'priority', 'deadline'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    
    work_id = Column(Integer, ForeignKey("works.id"), nullable=True)
    release_id = Column(Integer, ForeignKey("releases.id"), nullable=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    placement_id = Column(Integer, ForeignKey("placements.id"), nullable=True)
    
    entity_type = Column(String, nullable=True)
    entity_label = Column(String, nullable=True)
    
    action_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    priority = Column(Integer, default=2)
    status = Column(String, default="PENDING")
    
    deadline = Column(DateTime, nullable=True)
    reminder_days_before = Column(Integer, default=3)
    last_reminder_sent = Column(DateTime, nullable=True)
    
    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    completed_at = Column(DateTime, nullable=True)
    completed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    is_auto_generated = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization")
    creator = relationship("Creator")
    song = relationship("Song")
    work = relationship("Work")
    release = relationship("Release")
    contract = relationship("Contract")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    completed_by = relationship("User", foreign_keys=[completed_by_user_id])


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index('ix_notifications_user_read', 'user_id', 'is_read'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    
    notification_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    
    link = Column(String, nullable=True)
    extra_data = Column(JSON, nullable=True)
    
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User")
    organization = relationship("Organization")

class PlatformIntegration(Base):
    __tablename__ = "platform_integrations"
    
    id = Column(Integer, primary_key=True, index=True)
    integration_id = Column(String(50), unique=True, nullable=False)
    credentials_encrypted = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    last_tested_at = Column(DateTime, nullable=True)
    last_test_success = Column(Boolean, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    
    created_by = relationship("User")


class ContractType(str, enum.Enum):
    MASTER = "MASTER"
    PUBLISHING = "PUBLISHING"
    SYNC_LICENSE = "SYNC_LICENSE"
    DISTRIBUTION = "DISTRIBUTION"
    MANAGEMENT = "MANAGEMENT"
    ADMINISTRATION = "ADMINISTRATION"
    CO_PUBLISHING = "CO_PUBLISHING"
    SUB_PUBLISHING = "SUB_PUBLISHING"
    OTHER = "OTHER"

class ContractStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"

class AssetType(str, enum.Enum):
    SONG = "SONG"
    WORK = "WORK"

class RightsType(str, enum.Enum):
    MASTER = "MASTER"
    PUBLISHING = "PUBLISHING"
    SYNC = "SYNC"
    MECHANICAL = "MECHANICAL"
    PERFORMANCE = "PERFORMANCE"
    NEIGHBORING = "NEIGHBORING"
    OTHER = "OTHER"

class PartyRole(str, enum.Enum):
    LICENSOR = "LICENSOR"
    LICENSEE = "LICENSEE"
    ASSIGNOR = "ASSIGNOR"
    ASSIGNEE = "ASSIGNEE"
    PUBLISHER = "PUBLISHER"
    SUB_PUBLISHER = "SUB_PUBLISHER"
    ADMINISTRATOR = "ADMINISTRATOR"
    ARTIST = "ARTIST"
    LABEL = "LABEL"
    DISTRIBUTOR = "DISTRIBUTOR"
    OTHER = "OTHER"


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (
        Index('ix_contracts_organization_id', 'organization_id'),
        Index('ix_contracts_status', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    title = Column(String, nullable=False, index=True)
    contract_type = Column(String, nullable=False, default="OTHER")
    payment_direction = Column(String, nullable=True, default="INCOMING")
    status = Column(String, nullable=False, default="DRAFT")
    reference_number = Column(String, nullable=True)

    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    territory = Column(JSON, default=list)

    advance_amount = Column(Float, nullable=True, default=0.0)
    advance_currency = Column(String, default="USD")
    advance_recouped = Column(Float, nullable=True, default=0.0)

    notes = Column(Text, nullable=True)
    terms_summary = Column(Text, nullable=True)

    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    organization = relationship("Organization")
    created_by = relationship("User")
    creator = relationship("Creator")
    parties = relationship("ContractParty", back_populates="contract", cascade="all, delete-orphan")
    assets = relationship("ContractAsset", back_populates="contract", cascade="all, delete-orphan")
    documents = relationship("ContractDocument", back_populates="contract", cascade="all, delete-orphan")


class ContractParty(Base):
    __tablename__ = "contract_parties"
    __table_args__ = (
        Index('ix_contract_parties_contract_id', 'contract_id'),
        Index('ix_contract_parties_creator_id', 'creator_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)

    party_name = Column(String, nullable=False)
    party_role = Column(String, nullable=False, default="OTHER")
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)

    contact_email = Column(String, nullable=True)
    contact_info = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="parties")
    creator = relationship("Creator")


class ContractAsset(Base):
    __tablename__ = "contract_assets"
    __table_args__ = (
        UniqueConstraint('contract_id', 'asset_type', 'asset_id', name='uq_contract_asset'),
        Index('ix_contract_assets_contract_id', 'contract_id'),
        Index('ix_contract_assets_asset', 'asset_type', 'asset_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    asset_type = Column(String, nullable=False)
    asset_id = Column(Integer, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="assets")


class ContractDocument(Base):
    __tablename__ = "contract_documents"
    __table_args__ = (
        Index('ix_contract_documents_contract_id', 'contract_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String, nullable=True)
    description = Column(String, nullable=True)

    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    work_id = Column(Integer, ForeignKey("works.id"), nullable=True)
    release_id = Column(Integer, ForeignKey("releases.id"), nullable=True)

    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    contract = relationship("Contract", back_populates="documents")
    organization = relationship("Organization")
    uploaded_by = relationship("User")


class RightsSplit(Base):
    __tablename__ = "rights_splits"
    __table_args__ = (
        Index('ix_rights_splits_contract_asset_id', 'contract_asset_id'),
        Index('ix_rights_splits_rights_holder_id', 'rights_holder_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    contract_asset_id = Column(Integer, ForeignKey("contract_assets.id", ondelete="CASCADE"), nullable=False)
    rights_holder_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    rights_holder_name = Column(String, nullable=True)

    rights_type = Column(String, nullable=False, default="MASTER")
    share_percentage = Column(Float, nullable=False)

    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    contract_asset = relationship("ContractAsset")
    rights_holder = relationship("Creator", foreign_keys=[rights_holder_id])


class LegacyStatementStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"
    PARTIALLY_MATCHED = "PARTIALLY_MATCHED"

class TransactionMatchStatus(str, enum.Enum):
    MATCHED = "MATCHED"
    UNMATCHED = "UNMATCHED"
    MANUAL = "MANUAL"

class PaymentStatus(str, enum.Enum):
    PENDING_PAYMENT = "PENDING"
    APPROVED = "APPROVED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class RoyaltyStatement(Base):
    __tablename__ = "royalty_statements"
    __table_args__ = (
        Index('ix_royalty_statements_org_id', 'organization_id'),
        Index('ix_royalty_statements_status', 'status'),
        Index('ix_royalty_statements_period', 'period_start', 'period_end'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    source_name = Column(String, nullable=False)
    source_type = Column(String, nullable=True)

    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)

    currency = Column(String, default="USD")
    exchange_rate = Column(Float, default=1.0)

    file_name = Column(String, nullable=True)
    file_path = Column(String, nullable=True)

    total_revenue_cents = Column(Integer, default=0)
    total_transactions = Column(Integer, default=0)
    matched_transactions = Column(Integer, default=0)
    unmatched_transactions = Column(Integer, default=0)

    status = Column(String, default="PENDING")
    processing_notes = Column(Text, nullable=True)

    column_mapping = Column(JSON, nullable=True)

    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)

    reported_gross = Column(Float, nullable=True)
    reported_withholding = Column(Float, nullable=True)
    reported_net = Column(Float, nullable=True)
    reconciliation_result = Column(JSON, nullable=True)

    opening_balance = Column(Float, nullable=True)
    closing_balance = Column(Float, nullable=True)
    reconciliation_details = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transactions = relationship("RoyaltyTransaction", back_populates="statement", cascade="all, delete-orphan")
    statement_lines = relationship("RoyaltyStatementLine", back_populates="statement", cascade="all, delete-orphan")
    organization = relationship("Organization")
    uploaded_by = relationship("User")


class RoyaltyTransaction(Base):
    __tablename__ = "royalty_transactions"
    __table_args__ = (
        Index('ix_royalty_tx_statement_id', 'statement_id'),
        Index('ix_royalty_tx_song_id', 'song_id'),
        Index('ix_royalty_tx_match_status', 'match_status'),
        Index('ix_royalty_tx_org_id', 'organization_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    statement_id = Column(Integer, ForeignKey("royalty_statements.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    original_track_title = Column(String, nullable=True)
    original_artist = Column(String, nullable=True)
    original_isrc = Column(String, nullable=True)
    original_upc = Column(String, nullable=True)

    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    match_status = Column(String, default="UNMATCHED")
    match_confidence = Column(Float, nullable=True)

    revenue_cents = Column(Integer, default=0)
    currency = Column(String, default="USD")
    quantity = Column(Integer, default=0)

    territory = Column(String, nullable=True)
    platform = Column(String, nullable=True)
    revenue_type = Column(String, nullable=True)

    raw_data = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    statement = relationship("RoyaltyStatement", back_populates="transactions")
    song = relationship("Song")
    allocations = relationship("RoyaltyAllocation", back_populates="transaction", cascade="all, delete-orphan")


class RoyaltyAllocation(Base):
    __tablename__ = "royalty_allocations"
    __table_args__ = (
        Index('ix_royalty_alloc_tx_id', 'transaction_id'),
        Index('ix_royalty_alloc_contract_id', 'contract_id'),
        Index('ix_royalty_alloc_holder_id', 'rights_holder_id'),
        Index('ix_royalty_alloc_org_id', 'organization_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("royalty_transactions.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    rights_holder_id = Column(Integer, ForeignKey("creators.id"), nullable=False)

    rights_type = Column(String, nullable=False)
    share_percentage = Column(Float, nullable=False)
    allocated_cents = Column(Integer, default=0)

    is_recoupable = Column(Boolean, default=False)
    recouped_cents = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

    transaction = relationship("RoyaltyTransaction", back_populates="allocations")
    contract = relationship("Contract")
    rights_holder = relationship("Creator")


class Payment(Base):
    __tablename__ = "payments"
    __table_args__ = (
        Index('ix_payments_org_id', 'organization_id'),
        Index('ix_payments_payee_id', 'payee_id'),
        Index('ix_payments_status', 'status'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    payee_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)

    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, default="USD")

    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)

    status = Column(String, default="PENDING")

    payment_date = Column(Date, nullable=True)
    payment_method = Column(String, nullable=True)
    payment_reference = Column(String, nullable=True)

    notes = Column(Text, nullable=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    payee = relationship("Creator")
    contract = relationship("Contract")
    created_by = relationship("User")


class FeeType(str, enum.Enum):
    MANAGEMENT_FEE = "MANAGEMENT_FEE"
    ADMIN_FEE = "ADMIN_FEE"
    DISTRIBUTION_FEE = "DISTRIBUTION_FEE"
    SYNC_FEE = "SYNC_FEE"
    LEGAL_FEE = "LEGAL_FEE"
    OTHER = "OTHER"


class Fee(Base):
    __tablename__ = "fees"
    __table_args__ = (
        Index('ix_fees_org_id', 'organization_id'),
        Index('ix_fees_creator_id', 'creator_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    placement_id = Column(Integer, ForeignKey("placements.id"), nullable=True)

    fee_type = Column(String, nullable=False, default="MANAGEMENT_FEE")
    description = Column(String, nullable=True)
    amount_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String, default="USD")
    fee_date = Column(Date, nullable=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    status = Column(String, default="PENDING")
    notes = Column(Text, nullable=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    creator = relationship("Creator")
    contract = relationship("Contract")
    song = relationship("Song")
    placement = relationship("Placement")
    created_by = relationship("User")


class Advance(Base):
    __tablename__ = "advances"
    __table_args__ = (
        Index('ix_advances_org_id', 'organization_id'),
        Index('ix_advances_creator_id', 'creator_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)

    description = Column(String, nullable=True)
    amount_cents = Column(Integer, nullable=False, default=0)
    recouped_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String, default="USD")
    advance_date = Column(Date, nullable=True)
    fully_recouped = Column(Boolean, default=False)
    status = Column(String, default="ACTIVE")
    notes = Column(Text, nullable=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    creator = relationship("Creator")
    contract = relationship("Contract")
    created_by = relationship("User")


class ExpenseCategory(str, enum.Enum):
    PRODUCER_FEE = "PRODUCER_FEE"
    DAY_RATE = "DAY_RATE"
    VIDEO_PRODUCTION = "VIDEO_PRODUCTION"
    CONTENT_CREATION = "CONTENT_CREATION"
    LEGAL = "LEGAL"
    MARKETING = "MARKETING"
    TRAVEL = "TRAVEL"
    STUDIO = "STUDIO"
    MIXING_MASTERING = "MIXING_MASTERING"
    OTHER = "OTHER"

class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index('ix_expenses_org_id', 'organization_id'),
    )
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    category = Column(String, nullable=False, default="OTHER")
    description = Column(String, nullable=False)
    amount_cents = Column(Integer, nullable=False, default=0)
    currency = Column(String, default="USD")
    payee_name = Column(String, nullable=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    placement_id = Column(Integer, ForeignKey("placements.id"), nullable=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    expense_date = Column(Date, nullable=True)
    status = Column(String, default="PENDING")
    payment_method = Column(String, nullable=True)
    invoice_reference = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    budget_source = Column(String, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    organization = relationship("Organization")
    creator = relationship("Creator")
    contract = relationship("Contract")
    placement = relationship("Placement")
    song = relationship("Song")
    created_by = relationship("User")


class Placement(Base):
    __tablename__ = "placements"
    __table_args__ = (
        Index('ix_placements_org_id', 'organization_id'),
        Index('ix_placements_status', 'status'),
        Index('ix_placements_song_id', 'song_id'),
        Index('ix_placements_release_id', 'release_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)

    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    placement_type = Column(String, nullable=False, default="SYNC")
    status = Column(String, nullable=False, default="PITCHED")

    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    work_id = Column(Integer, ForeignKey("works.id"), nullable=True)
    release_id = Column(Integer, ForeignKey("releases.id"), nullable=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)

    client_name = Column(String, nullable=True)
    project_name = Column(String, nullable=True)
    media_type = Column(String, nullable=True)

    license_fee = Column(Float, nullable=True, default=0.0)
    license_currency = Column(String, default="USD")
    license_type = Column(String, nullable=True)
    territory = Column(String, nullable=True)
    usage_notes = Column(Text, nullable=True)

    pitched_date = Column(Date, nullable=True)
    secured_date = Column(Date, nullable=True)
    delivery_date = Column(Date, nullable=True)
    air_date = Column(Date, nullable=True)

    contact_name = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)

    notes = Column(Text, nullable=True)

    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    song = relationship("Song")
    work = relationship("Work")
    release = relationship("Release")
    contract = relationship("Contract")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])


class ClientShareStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"
    CANCELLED = "CANCELLED"

class ClientShareRole(str, enum.Enum):
    COPRIMARY = "COPRIMARY"
    SECONDARY = "SECONDARY"
    READER = "READER"

class ClientShare(Base):
    __tablename__ = "client_shares"
    __table_args__ = (
        Index('ix_client_shares_org', 'primary_org_id'),
        Index('ix_client_shares_recipient', 'recipient_org_id'),
        Index(
            'ix_client_share_active_unique',
            'creator_id', 'recipient_user_email',
            unique=True,
            postgresql_where=text("status IN ('PENDING', 'ACCEPTED')")
        ),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    primary_org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    recipient_org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    
    recipient_user_email = Column(String, nullable=False)
    recipient_org_name_verification = Column(String, nullable=True)
    
    passcode = Column(String(6), nullable=False)
    role = Column(String, nullable=False, default="READER")
    status = Column(String, nullable=False, default="PENDING")
    
    shared_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    accepted_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime, nullable=True)
    revoked_at = Column(DateTime, nullable=True)
    
    creator = relationship("Creator")
    primary_org = relationship("Organization", foreign_keys=[primary_org_id])
    recipient_org = relationship("Organization", foreign_keys=[recipient_org_id])
    shared_by = relationship("User", foreign_keys=[shared_by_user_id])
    accepted_by = relationship("User", foreign_keys=[accepted_by_user_id])


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index('ix_audit_logs_org_id', 'organization_id'),
        Index('ix_audit_logs_created_at', 'created_at'),
        Index('ix_audit_logs_action', 'action'),
        Index('ix_audit_logs_entity_type', 'entity_type'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=True)
    entity_name = Column(String, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization")
    user = relationship("User")


class StorageProvider(str, enum.Enum):
    DROPBOX = "DROPBOX"
    BOX = "BOX"
    GOOGLE_DRIVE = "GOOGLE_DRIVE"

class AudioFileType(str, enum.Enum):
    MAIN = "MAIN"
    INSTRUMENTAL = "INSTRUMENTAL"
    CLEAN = "CLEAN"
    ALT_MIX = "ALT_MIX"
    STEMS = "STEMS"
    OTHER = "OTHER"

class AnalysisStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"

class TagType(str, enum.Enum):
    MOOD = "MOOD"
    TEXTURE = "TEXTURE"
    SYNC = "SYNC"
    GENRE = "GENRE"
    USER = "USER"

class TagSource(str, enum.Enum):
    AI = "AI"
    USER = "USER"


class IntegrationAccount(Base):
    __tablename__ = "integration_accounts"
    __table_args__ = (
        Index('ix_integration_accounts_org_id', 'org_id'),
        UniqueConstraint('org_id', 'provider', name='uq_integration_org_provider'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    provider = Column(String, nullable=False, default="DROPBOX")
    access_token_encrypted = Column(Text, nullable=True)
    refresh_token_encrypted = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    connected_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_email = Column(String, nullable=True)
    account_display_name = Column(String, nullable=True)
    default_folder_path = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    connected_by = relationship("User")


class AudioAsset(Base):
    __tablename__ = "audio_assets"
    __table_args__ = (
        Index('ix_audio_assets_org_id', 'org_id'),
        Index('ix_audio_assets_song_id', 'song_id'),
        Index('ix_audio_assets_release_id', 'release_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    release_id = Column(Integer, ForeignKey("releases.id"), nullable=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True, index=True)
    provider = Column(String, nullable=False, default="DROPBOX")
    provider_file_id = Column(String, nullable=True)
    path_display = Column(String, nullable=True)
    name = Column(String, nullable=False)
    size_bytes = Column(Integer, nullable=True)
    file_type = Column(String, nullable=False, default="MAIN")
    mime_type = Column(String, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    checksum = Column(String, nullable=True)
    last_verified_at = Column(DateTime, nullable=True)
    is_available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    song = relationship("Song")
    release = relationship("Release")
    creator = relationship("Creator")
    analysis = relationship("AudioAnalysis", uselist=False, back_populates="audio_asset")
    tags = relationship("AudioAssetTag", back_populates="audio_asset", cascade="all, delete-orphan")


class AudioAnalysis(Base):
    __tablename__ = "audio_analyses"
    __table_args__ = (
        Index('ix_audio_analyses_org_id', 'org_id'),
        Index('ix_audio_analyses_asset_id', 'audio_asset_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    audio_asset_id = Column(Integer, ForeignKey("audio_assets.id"), nullable=False, index=True, unique=True)
    status = Column(String, nullable=False, default="QUEUED")
    analyzed_at = Column(DateTime, nullable=True)
    bpm = Column(Float, nullable=True)
    bpm_confidence = Column(Float, nullable=True)
    musical_key = Column(String, nullable=True)
    key_confidence = Column(Float, nullable=True)
    time_signature = Column(String, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    lufs = Column(Float, nullable=True)
    peak_db = Column(Float, nullable=True)
    dynamic_range = Column(Float, nullable=True)
    vocal_present = Column(Boolean, nullable=True)
    vocal_confidence = Column(Float, nullable=True)
    energy_level = Column(String, nullable=True)
    features_json = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    audio_asset = relationship("AudioAsset", back_populates="analysis")


class AudioTag(Base):
    __tablename__ = "audio_tags"
    __table_args__ = (
        UniqueConstraint('org_id', 'name', 'tag_type', name='uq_audio_tag_org_name'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    name = Column(String, nullable=False, index=True)
    tag_type = Column(String, nullable=False, default="MOOD")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization")
    created_by = relationship("User")


class AudioAssetTag(Base):
    __tablename__ = "audio_asset_tags"
    __table_args__ = (
        UniqueConstraint('audio_asset_id', 'audio_tag_id', name='uq_asset_tag'),
    )

    id = Column(Integer, primary_key=True, index=True)
    audio_asset_id = Column(Integer, ForeignKey("audio_assets.id", ondelete="CASCADE"), nullable=False, index=True)
    audio_tag_id = Column(Integer, ForeignKey("audio_tags.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String, nullable=False, default="AI")
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    audio_asset = relationship("AudioAsset", back_populates="tags")
    audio_tag = relationship("AudioTag")


class ProviderType(str, enum.Enum):
    PRO = "PRO"
    DSP = "DSP"
    DISTRIBUTOR = "DISTRIBUTOR"
    LABEL = "LABEL"
    PUBLISHER = "PUBLISHER"
    OTHER = "OTHER"

class RevenueType(str, enum.Enum):
    MASTER = "MASTER"
    PUBLISHING = "PUBLISHING"
    MECHANICAL = "MECHANICAL"
    PERFORMANCE = "PERFORMANCE"
    SYNC = "SYNC"
    NEIGHBORING = "NEIGHBORING"
    OTHER = "OTHER"

class MatchStatus(str, enum.Enum):
    UNMATCHED = "UNMATCHED"
    AUTO_MATCHED = "AUTO_MATCHED"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    IGNORED = "IGNORED"

class ProcessingRunStatus(str, enum.Enum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    PARTIAL = "PARTIAL"

class LedgerEntryType(str, enum.Enum):
    EARNING = "EARNING"
    FEE = "FEE"
    RECOUPMENT_APPLIED = "RECOUPMENT_APPLIED"
    PAYABLE_CREATED = "PAYABLE_CREATED"
    PAYMENT = "PAYMENT"
    REVERSAL = "REVERSAL"
    ADJUSTMENT = "ADJUSTMENT"

class PayeeType(str, enum.Enum):
    CREATOR = "CREATOR"
    COMPANY = "COMPANY"
    PUBLISHER = "PUBLISHER"
    LABEL = "LABEL"
    OTHER = "OTHER"

class RecoupmentPool(str, enum.Enum):
    MASTER = "MASTER"
    PUBLISHING = "PUBLISHING"
    BOTH = "BOTH"
    CUSTOM = "CUSTOM"

class PayoutStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    PAID = "PAID"
    VOID = "VOID"

class StatementStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    MAPPING_REQUIRED = "MAPPING_REQUIRED"
    MAPPING_COMPLETE = "MAPPING_COMPLETE"
    MATCHING = "MATCHING"
    READY_TO_PROCESS = "READY_TO_PROCESS"
    PROCESSED = "PROCESSED"
    LOCKED = "LOCKED"


class Payee(Base):
    __tablename__ = "payees"
    __table_args__ = (
        UniqueConstraint('org_id', 'creator_id', name='uq_payee_org_creator'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    payee_type = Column(String, nullable=False)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    company_name = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    payment_details_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("Creator")
    organization = relationship("Organization")


class RoyaltyStatementLine(Base):
    __tablename__ = "royalty_statement_lines"
    __table_args__ = (
        Index('ix_rsl_org_statement', 'org_id', 'statement_id'),
        Index('ix_rsl_org_isrc', 'org_id', 'isrc'),
        Index('ix_rsl_org_match_status', 'org_id', 'match_status'),
        Index('ix_rsl_org_matched_song', 'org_id', 'matched_song_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    statement_id = Column(Integer, ForeignKey("royalty_statements.id", ondelete="CASCADE"), nullable=False)
    line_hash = Column(String, nullable=True, index=True)
    isrc = Column(String, nullable=True)
    upc = Column(String, nullable=True)
    iswc = Column(String, nullable=True)
    track_title_raw = Column(String, nullable=True)
    release_title_raw = Column(String, nullable=True)
    artist_name_raw = Column(String, nullable=True)
    label_raw = Column(String, nullable=True)
    territory = Column(String, nullable=True)
    store = Column(String, nullable=True)
    usage_type = Column(String, nullable=True)
    revenue_type = Column(String, nullable=True)
    unit_count = Column(Float, nullable=True)
    gross_amount = Column(Float, nullable=True)
    deductions_amount = Column(Float, nullable=True)
    net_amount = Column(Float, default=0)
    currency = Column(String, nullable=True)
    fx_rate_to_statement_currency = Column(Float, nullable=True)
    net_amount_statement_currency = Column(Float, default=0)
    matched_song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    matched_work_id = Column(Integer, ForeignKey("works.id"), nullable=True)
    matched_release_id = Column(Integer, ForeignKey("releases.id"), nullable=True)
    match_status = Column(String, default="UNMATCHED")
    match_confidence = Column(Float, nullable=True)
    match_method = Column(String, nullable=True)
    matched_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    matched_at = Column(DateTime, nullable=True)
    canonical_right_category = Column(String, nullable=True)
    canonical_channel = Column(String, nullable=True)
    accounting_flags = Column(JSON, nullable=True)
    territory_iso2 = Column(String, nullable=True)
    territory_confidence = Column(String, nullable=True)
    activity_period_start = Column(Date, nullable=True)
    activity_period_end = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    statement = relationship("RoyaltyStatement", back_populates="statement_lines")
    song = relationship("Song")
    work = relationship("Work")
    release = relationship("Release")


class RoyaltyProcessingRun(Base):
    __tablename__ = "royalty_processing_runs"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    statement_id = Column(Integer, ForeignKey("royalty_statements.id"), nullable=False, index=True)
    run_version = Column(Integer, nullable=False)
    status = Column(String, default="RUNNING")
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    started_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)
    summary_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class RoyaltyLedgerEntry(Base):
    __tablename__ = "royalty_ledger_entries"
    __table_args__ = (
        Index('ix_rle_org_payee_created', 'org_id', 'payee_id', 'created_at'),
        Index('ix_rle_org_contract', 'org_id', 'contract_id'),
        Index('ix_rle_org_entry_type', 'org_id', 'entry_type'),
        Index('ix_rle_org_statement', 'org_id', 'statement_id'),
        Index('ix_rle_org_processing_run', 'org_id', 'processing_run_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    statement_id = Column(Integer, ForeignKey("royalty_statements.id"), nullable=False)
    statement_line_id = Column(Integer, ForeignKey("royalty_statement_lines.id"), nullable=True)
    processing_run_id = Column(Integer, ForeignKey("royalty_processing_runs.id"), nullable=False)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    work_id = Column(Integer, ForeignKey("works.id"), nullable=True)
    release_id = Column(Integer, ForeignKey("releases.id"), nullable=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    payee_id = Column(Integer, ForeignKey("payees.id"), nullable=False)
    entry_type = Column(String, nullable=False)
    revenue_type = Column(String, nullable=True)
    source = Column(String, nullable=True)
    amount_cents = Column(Integer, nullable=False)
    payee_currency = Column(String, nullable=True)
    amount_payee_currency_cents = Column(Integer, nullable=True)
    fx_rate = Column(Float, nullable=True)
    advance_id = Column(Integer, ForeignKey("advance_pools.id"), nullable=True)
    recoupment_pool = Column(String, nullable=True)
    memo = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class AdvanceV2(Base):
    __tablename__ = "advance_pools"
    __table_args__ = (
        Index('ix_adv2_org_payee', 'org_id', 'payee_id'),
        Index('ix_adv2_org_contract', 'org_id', 'contract_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=True)
    payee_id = Column(Integer, ForeignKey("payees.id"), nullable=False)
    advance_name = Column(String, nullable=False)
    advance_date = Column(Date, nullable=False)
    currency = Column(String, default="USD")
    principal_amount_cents = Column(Integer, nullable=False)
    recoupable = Column(Boolean, default=True)
    recoupment_pool = Column(String, nullable=False)
    recoupment_priority = Column(Integer, default=1)
    cross_collateralize = Column(Boolean, default=False)
    start_recouping_on = Column(Date, nullable=True)
    end_recouping_on = Column(Date, nullable=True)
    outstanding_balance_cents = Column(Integer, nullable=False)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    payee = relationship("Payee")
    contract = relationship("Contract")
    organization = relationship("Organization")


class PayoutBatch(Base):
    __tablename__ = "payout_batches"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    currency = Column(String, default="USD")
    status = Column(String, default="DRAFT")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    items = relationship("PayoutItem", back_populates="batch", cascade="all, delete-orphan")
    organization = relationship("Organization")
    created_by = relationship("User")


class PayoutItem(Base):
    __tablename__ = "payout_items"

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    batch_id = Column(Integer, ForeignKey("payout_batches.id"), nullable=False, index=True)
    payee_id = Column(Integer, ForeignKey("payees.id"), nullable=False, index=True)
    amount_cents = Column(Integer, nullable=False)
    memo = Column(Text, nullable=True)
    paid_at = Column(DateTime, nullable=True)
    payment_method = Column(String, nullable=True)
    external_reference = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    batch = relationship("PayoutBatch", back_populates="items")
    payee = relationship("Payee")


RoyaltyStatement.statement_lines = relationship("RoyaltyStatementLine", back_populates="statement", cascade="all, delete-orphan")
RoyaltyStatement.processing_runs = relationship("RoyaltyProcessingRun", backref="statement")


class CreatorStorageLink(Base):
    __tablename__ = "creator_storage_links"
    __table_args__ = (
        Index('ix_creator_storage_links_creator_id', 'creator_id'),
        Index('ix_creator_storage_links_org_id', 'org_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=False)
    provider = Column(String, nullable=False, default="DROPBOX")
    folder_path = Column(String, nullable=False)
    container_name = Column(String, nullable=True)
    scan_recursive = Column(Boolean, default=True)
    auto_scan_enabled = Column(Boolean, default=False)
    auto_scan_frequency = Column(String, nullable=True)
    last_scanned_at = Column(DateTime, nullable=True)
    last_scan_file_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    creator = relationship("Creator")


class ScanStatus(str, enum.Enum):
    PENDING = "PENDING"
    SCANNING = "SCANNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class MatchConfidence(str, enum.Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NONE = "NONE"


class StorageScanResult(Base):
    __tablename__ = "storage_scan_results"
    __table_args__ = (
        Index('ix_storage_scan_results_org_id', 'org_id'),
        Index('ix_storage_scan_results_scan_batch_id', 'scan_batch_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    scan_batch_id = Column(String, nullable=False, index=True)
    creator_storage_link_id = Column(Integer, ForeignKey("creator_storage_links.id"), nullable=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)
    provider = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=True)
    provider_file_id = Column(String, nullable=True)
    matched_song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    matched_work_id = Column(Integer, ForeignKey("works.id"), nullable=True)
    match_confidence = Column(String, nullable=True)
    match_score = Column(Float, nullable=True)
    match_reason = Column(String, nullable=True)
    suggested_title = Column(String, nullable=True)
    suggested_artist = Column(String, nullable=True)
    status = Column(String, nullable=False, default="PENDING")
    reviewed = Column(Boolean, default=False)
    approved = Column(Boolean, nullable=True)
    linked_audio_asset_id = Column(Integer, ForeignKey("audio_assets.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    creator_storage_link = relationship("CreatorStorageLink")
    creator = relationship("Creator")
    matched_song = relationship("Song")
    matched_work = relationship("Work")
    linked_audio_asset = relationship("AudioAsset")


class RegistrationReport(Base):
    __tablename__ = "registration_reports"
    __table_args__ = (
        Index('ix_registration_reports_org_id', 'organization_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    report_type = Column(String, nullable=False, default="SONGS")
    title = Column(String, nullable=False)
    status = Column(String, nullable=False, default="GENERATED")
    filter_creator_id = Column(Integer, nullable=True)
    filter_status = Column(String, nullable=True)
    item_count = Column(Integer, default=0)
    outstanding_count = Column(Integer, default=0)
    ready_count = Column(Integer, default=0)
    needs_attention_count = Column(Integer, default=0)
    report_data = Column(Text, nullable=True)
    pdf_data = Column(LargeBinary, nullable=True)
    pdf_mime = Column(String, nullable=True)
    generated_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    sent_to = Column(String, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    created_by = relationship("User")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    endpoint = Column(Text, nullable=False, unique=True)
    p256dh = Column(String, nullable=False)
    auth = Column(String, nullable=False)
    user_agent = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")


class ClientSharedContact(Base):
    __tablename__ = "client_shared_contacts"
    __table_args__ = (
        UniqueConstraint('creative_contact_id', 'shared_with_user_id', name='uq_client_shared_contact'),
        Index('ix_client_shared_contacts_org_id', 'organization_id'),
        Index('ix_client_shared_contacts_user_id', 'shared_with_user_id'),
        Index('ix_client_shared_contacts_contact_id', 'creative_contact_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    creative_contact_id = Column(Integer, ForeignKey("creative_contacts.id", ondelete="CASCADE"), nullable=False)
    shared_with_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shared_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization")
    creative_contact = relationship("CreativeContact")
    shared_with_user = relationship("User", foreign_keys=[shared_with_user_id])
    shared_by_user = relationship("User", foreign_keys=[shared_by_user_id])


class AccountMergeRequest(Base):
    __tablename__ = "account_merge_requests"
    __table_args__ = (
        Index('ix_merge_requests_status', 'status'),
        Index('ix_merge_requests_requesting_user', 'requesting_user_id'),
        Index('ix_merge_requests_target_user', 'target_user_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    requesting_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    target_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    linked_creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True)

    status = Column(String, default="PENDING_VERIFICATION")
    verification_code = Column(String, nullable=True)
    verification_expires_at = Column(DateTime, nullable=True)
    verified_at = Column(DateTime, nullable=True)
    admin_notes = Column(String, nullable=True)
    resolved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    requesting_user = relationship("User", foreign_keys=[requesting_user_id])
    target_user = relationship("User", foreign_keys=[target_user_id])
    organization = relationship("Organization")
    linked_creator = relationship("Creator")
    resolved_by = relationship("User", foreign_keys=[resolved_by_user_id])


class ChartPlatform(str, enum.Enum):
    SPOTIFY = "SPOTIFY"
    YOUTUBE = "YOUTUBE"
    APPLE = "APPLE"
    DEEZER = "DEEZER"
    LASTFM = "LASTFM"

class ChartType(str, enum.Enum):
    TOP_SONGS = "TOP_SONGS"
    TRENDING = "TRENDING"
    PLAYLIST = "PLAYLIST"

class FetchFrequency(str, enum.Enum):
    HOURLY = "HOURLY"
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"

class EstimationMethod(str, enum.Enum):
    CHART_POSITION = "CHART_POSITION"
    MARKET_SHARE = "MARKET_SHARE"
    DIRECT_API = "DIRECT_API"
    MANUAL = "MANUAL"


class ChartSource(Base):
    __tablename__ = "chart_sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    platform = Column(String, nullable=False)
    chart_type = Column(String, default="TOP_SONGS")
    country_code = Column(String, nullable=True)
    url = Column(String, nullable=True)
    external_playlist_id = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    fetch_frequency = Column(String, default="DAILY")
    last_fetched_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    entries = relationship("ChartEntry", back_populates="chart_source", cascade="all, delete-orphan")


class ChartEntry(Base):
    __tablename__ = "chart_entries"
    __table_args__ = (
        Index('ix_chart_entries_source_date_pos', 'chart_source_id', 'chart_date', 'position'),
        Index('ix_chart_entries_isrc', 'isrc'),
        Index('ix_chart_entries_song_id', 'song_id'),
        Index('ix_chart_entries_chart_date', 'chart_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    chart_source_id = Column(Integer, ForeignKey("chart_sources.id", ondelete="CASCADE"), nullable=False)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    chart_date = Column(Date, nullable=False)
    position = Column(Integer, nullable=False)
    external_track_id = Column(String, nullable=True)
    isrc = Column(String, nullable=True)
    title = Column(String, nullable=False)
    artist_name = Column(String, nullable=False)
    album_name = Column(String, nullable=True)
    stream_count = Column(Integer, nullable=True)
    view_count = Column(Integer, nullable=True)
    play_count = Column(Integer, nullable=True)
    shazam_count = Column(Integer, nullable=True)
    extra_data = Column(JSON, nullable=True)
    matched_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    chart_source = relationship("ChartSource", back_populates="entries")
    song = relationship("Song")


class StreamEstimate(Base):
    __tablename__ = "stream_estimates"
    __table_args__ = (
        Index('ix_stream_estimates_song_org', 'song_id', 'organization_id'),
        Index('ix_stream_estimates_song_platform_date', 'song_id', 'platform', 'period_date'),
        Index('ix_stream_estimates_song_org_date', 'song_id', 'organization_id', 'period_date'),
    )

    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    period_date = Column(Date, nullable=False)
    platform = Column(String, nullable=False)
    estimated_streams = Column(Float, default=0)
    actual_streams = Column(Float, nullable=True)
    estimation_method = Column(String, default="MARKET_SHARE")
    confidence_score = Column(Float, default=0.3)
    source_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    song = relationship("Song")
    organization = relationship("Organization")


class CreatorCreditsProfile(Base):
    __tablename__ = "creator_credits_profiles"
    __table_args__ = (
        UniqueConstraint('creator_id', 'organization_id', name='uq_credits_profile_creator_org'),
        Index('ix_credits_profile_share_token', 'share_token'),
    )

    id = Column(Integer, primary_key=True, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id", ondelete="CASCADE"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    share_token = Column(String(32), unique=True, nullable=True)
    share_passcode = Column(String, nullable=True)
    is_public = Column(Boolean, default=False)
    total_credits = Column(Integer, default=0)
    total_estimated_streams = Column(Float, default=0)
    role_breakdown = Column(JSON, nullable=True)
    top_songs = Column(JSON, nullable=True)
    platform_breakdown = Column(JSON, nullable=True)
    last_computed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("Creator")
    organization = relationship("Organization")


class UnderwritingRun(Base):
    __tablename__ = "underwriting_runs"
    __table_args__ = (
        Index('ix_underwriting_runs_org_id', 'organization_id'),
    )

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    kb_version = Column(String, nullable=False)
    status = Column(String, default="RUNNING")

    scope_creator_id = Column(Integer, nullable=True)

    inputs = Column(JSON, nullable=False)
    outputs = Column(JSON, nullable=True)

    spine_data = Column(JSON, nullable=True)
    decay_data = Column(JSON, nullable=True)
    concentration_data = Column(JSON, nullable=True)
    projection_data = Column(JSON, nullable=True)
    valuation_data = Column(JSON, nullable=True)
    exceptions = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    organization = relationship("Organization")
    created_by = relationship("User")


class AIUsageLog(Base):
    __tablename__ = "ai_usage_logs"
    __table_args__ = (
        Index('ix_ai_usage_logs_org_id', 'org_id'),
        Index('ix_ai_usage_logs_created_at', 'created_at'),
        Index('ix_ai_usage_logs_feature', 'feature'),
    )

    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    feature = Column(String, nullable=False)
    model = Column(String, nullable=False, default="gpt-4o-mini")
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    estimated_cost_cents = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class SharedItemType(str, enum.Enum):
    DOCUMENT = "DOCUMENT"
    CONTACT_CARD = "CONTACT_CARD"
    AUDIO = "AUDIO"
    STATEMENT = "STATEMENT"
    SONG = "SONG"
    CONTRACT = "CONTRACT"

class SharedItemStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"

class SharedItem(Base):
    __tablename__ = "shared_items"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    item_type = Column(String, nullable=False)
    item_id = Column(Integer, nullable=False)
    item_name = Column(String, nullable=True)
    shared_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    shared_with_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    shared_with_email = Column(String, nullable=True)
    shared_with_org_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    message = Column(Text, nullable=True)
    status = Column(String, default="ACTIVE")
    created_at = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", foreign_keys=[organization_id])
    shared_by_user = relationship("User", foreign_keys=[shared_by_user_id])
    shared_with_user = relationship("User", foreign_keys=[shared_with_user_id])


class TicketCategory(str, enum.Enum):
    BUG_REPORT = "BUG_REPORT"
    FEATURE_REQUEST = "FEATURE_REQUEST"
    GENERAL_SUPPORT = "GENERAL_SUPPORT"

class TicketStatus(str, enum.Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"

class SupportTicket(Base):
    __tablename__ = "support_tickets"
    __table_args__ = (
        Index('ix_support_tickets_user_id', 'user_id'),
        Index('ix_support_tickets_org_id', 'organization_id'),
        Index('ix_support_tickets_status', 'status'),
        Index('ix_support_tickets_created_at', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=True)
    category = Column(String, nullable=False, default="GENERAL_SUPPORT")
    subject = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="OPEN")
    admin_notes = Column(Text, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", foreign_keys=[user_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    attachments = relationship("SupportTicketAttachment", back_populates="ticket", cascade="all, delete-orphan")

class SupportTicketAttachment(Base):
    __tablename__ = "support_ticket_attachments"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    mime_type = Column(String, nullable=True)
    file_size = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    ticket = relationship("SupportTicket", back_populates="attachments")
