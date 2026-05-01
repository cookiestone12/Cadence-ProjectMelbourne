from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Enum, Date, UniqueConstraint, Index, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

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
