from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Songwriter(Base):
    __tablename__ = "songwriters"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    pro_affiliation = Column(String, nullable=True)
    ipi_number = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    songs = relationship("Song", back_populates="songwriter")

class Catalog(Base):
    __tablename__ = "catalogs"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    songs = relationship("Song", back_populates="catalog")

class Song(Base):
    __tablename__ = "songs"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    artist_name = Column(String)
    publishing_percentage = Column(Float, default=0.0)
    master_percentage = Column(Float, default=0.0)
    spotify_link = Column(String, nullable=True)
    songwriter_id = Column(Integer, ForeignKey("songwriters.id"), nullable=True)
    catalog_id = Column(Integer, ForeignKey("catalogs.id"), nullable=True)
    
    isrc = Column(String, nullable=True)
    iswc = Column(String, nullable=True)
    writer_splits = Column(JSON, default=list)
    release_date = Column(DateTime, nullable=True)
    
    valuation_low = Column(Float, default=0.0)
    valuation_base = Column(Float, default=0.0)
    valuation_high = Column(Float, default=0.0)
    estimated_revenue = Column(Float, default=0.0)
    
    score = Column(Float, default=0.0)
    score_breakdown = Column(JSON, default=dict)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    songwriter = relationship("Songwriter", back_populates="songs")
    catalog = relationship("Catalog", back_populates="songs")
    analytics = relationship("Analytics", back_populates="song", uselist=False)

class Analytics(Base):
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    song_id = Column(Integer, ForeignKey("songs.id"), unique=True)
    
    spotify_streams = Column(Integer, default=0)
    spotify_monthly_listeners = Column(Integer, default=0)
    chartmetric_score = Column(Float, default=0.0)
    playlist_count = Column(Integer, default=0)
    top_playlists = Column(JSON, default=list)
    
    regional_data = Column(JSON, default=dict)
    trend_data = Column(JSON, default=dict)
    
    # Stream breakdown by type: {spotify: {premium: int, ad_supported: int}}
    streams_by_type = Column(JSON, default=dict)
    
    # Territory breakdown: {US: {premium: int, ad_supported: int}, UK: {...}, ...}
    territory_streams = Column(JSON, default=dict)
    
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    song = relationship("Song", back_populates="analytics")

class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
