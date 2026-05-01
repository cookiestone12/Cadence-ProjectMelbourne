from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

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


class SpotifyOAuthToken(Base):
    __tablename__ = "spotify_oauth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    scope = Column(String, nullable=True)
    token_expires_at = Column(DateTime, nullable=False)
    connected_user_display_name = Column(String, nullable=True)
    connected_user_email = Column(String, nullable=True)
    connected_user_spotify_id = Column(String, nullable=True)
    connected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
