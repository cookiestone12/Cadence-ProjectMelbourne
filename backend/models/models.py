from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum as SQLEnum, Date, UniqueConstraint, Index
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
    created_at = Column(DateTime, default=datetime.utcnow)
    
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="organization_memberships")

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
    linked_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    contributor_type = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    publisher_name = Column(String, nullable=True)
    label_affiliation = Column(String, nullable=True)
    bio = Column(Text, nullable=True)
    website_url = Column(String, nullable=True)
    spotify_artist_id = Column(String, nullable=True)
    apple_music_id = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization", back_populates="creators")
    song_credits = relationship("SongCredit", back_populates="creator")
    work_credits = relationship("WorkCredit", back_populates="creator")
    linked_user = relationship("User", foreign_keys=[linked_user_id])

class Song(Base):
    __tablename__ = "songs"
    __table_args__ = (
        Index('ix_songs_organization_id', 'organization_id'),
        Index('ix_songs_org_health', 'organization_id', 'status_health_score'),
    )
    
    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
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
    is_registered_with_dsp = Column(Boolean, default=False)
    is_invoiced = Column(Boolean, default=False)
    is_paid = Column(Boolean, default=False)
    
    is_released = Column(Boolean, default=False)
    spotify_link = Column(String, nullable=True)
    label = Column(String, nullable=True)
    publishing_percentage = Column(Float, nullable=True)
    master_percentage = Column(Float, nullable=True)
    advance_amount = Column(Float, nullable=True)
    recording_code = Column(String, nullable=True)
    
    master_paid = Column(String, nullable=True)
    soundexchange_registered = Column(String, nullable=True)
    payment_status = Column(String, nullable=True)
    contract_location = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    
    media_url = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    organization = relationship("Organization", back_populates="songs")
    credits = relationship("SongCredit", back_populates="song", cascade="all, delete-orphan")
    dsp_links = relationship("SongDSPLink", back_populates="song", cascade="all, delete-orphan")
    checklist_statuses = relationship("SongChecklistStatus", back_populates="song", cascade="all, delete-orphan")
    valuation_snapshots = relationship("SongValuationSnapshot", back_populates="song", cascade="all, delete-orphan")
    analytics = relationship("Analytics", back_populates="song", uselist=False)
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
    title = Column(String, index=True, nullable=False)
    alternative_titles = Column(JSON, default=list)
    iswc = Column(String, nullable=True)
    language = Column(String, nullable=True)
    genre = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    lyrics = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
    work_tracks = relationship("WorkTrack", back_populates="work", cascade="all, delete-orphan")
    credits = relationship("WorkCredit", back_populates="work", cascade="all, delete-orphan")


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
    description = Column(Text, nullable=True)
    copyright_line = Column(String, nullable=True)
    copyright_year = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    spotify_url = Column(String, nullable=True)
    apple_music_url = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization")
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
    
    song = relationship("Song", back_populates="contracts")
    organization = relationship("Organization")
    uploaded_by = relationship("User")


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
