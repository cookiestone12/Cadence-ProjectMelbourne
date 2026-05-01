from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

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
    status = Column(String, default="PENDING", nullable=False, server_default="PENDING")

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
