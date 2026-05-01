from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum, Date, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

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
    is_registered_with_dsp = Column(String, nullable=True)
    is_invoiced = Column(String, nullable=True)
    is_paid = Column(String, nullable=True)
    
    is_released = Column(Boolean, default=False)
    release_status = Column(String, default="unreleased", nullable=False)
    entry_type = Column(String, default="Song", nullable=False)
    parent_song_id = Column(Integer, ForeignKey("songs.id"), nullable=True)
    shared_song_group_id = Column(String, nullable=True, index=True)
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

    spotify_popularity = Column(Integer, nullable=True)
    spotify_popularity_fetched_at = Column(DateTime, nullable=True)

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
    parent_song = relationship("Song", remote_side="Song.id", foreign_keys=[parent_song_id])


class SongCredit(Base):
    __tablename__ = "song_credits"
    
    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), nullable=False, index=True)
    creator_id = Column(Integer, ForeignKey("creators.id"), nullable=True, index=True)
    role = Column(String, nullable=False)
    share_percentage = Column(Float, nullable=True)
    pub_share = Column(Float, nullable=True)
    master_share = Column(Float, nullable=True)
    creative_contact_id = Column(Integer, nullable=True)
    needs_review = Column(Boolean, default=False, nullable=False)
    unmatched_artist_name = Column(String, nullable=True)
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


class SongEditHistory(Base):
    __tablename__ = "song_edit_history"
    __table_args__ = (
        Index('ix_song_edit_history_song_id', 'song_id'),
        Index('ix_song_edit_history_org_id', 'organization_id'),
        Index('ix_song_edit_history_created_at', 'created_at'),
    )

    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id", ondelete="SET NULL"), nullable=True)
    song_title = Column(String, nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    field_name = Column(String, nullable=False)
    old_value = Column(JSON, nullable=True)
    new_value = Column(JSON, nullable=True)
    change_type = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    song = relationship("Song", foreign_keys=[song_id])
    user = relationship("User", foreign_keys=[user_id])
