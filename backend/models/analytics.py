from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text, JSON, Enum, Date, UniqueConstraint, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from .database import Base

class ValuationSource(str, enum.Enum):
    MANUAL = "MANUAL"
    LUMINATE = "LUMINATE"
    EXTERNAL = "EXTERNAL"


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


class SongStreamingMetrics(Base):
    __tablename__ = "song_streaming_metrics"
    __table_args__ = (
        Index('ix_streaming_metrics_song_id', 'song_id'),
        Index('ix_streaming_metrics_period_date', 'period_date'),
        Index('ix_streaming_metrics_org_period', 'organization_id', 'period_date'),
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

    # Task #173 — Luminate-ready columns. ``luminate_total_streams`` is
    # the headline number on a Luminate row (sum of all stream types
    # they report); ``period_start`` / ``period_end`` give an explicit
    # period range (Luminate reports custom date ranges, not just a
    # single point-in-time). ``last_synced`` records the most recent
    # successful pull; ``data_source`` tags the row's provenance
    # ("luminate", "spotify", "manual", "csv-import", ...) so the audit
    # engine can cross-check sources against each other.
    luminate_total_streams = Column(Integer, nullable=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)
    last_synced = Column(DateTime, nullable=True)
    data_source = Column(String, nullable=True)

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

    # Source-typed valuation columns (Task #162). All nullable so legacy
    # rows written by the prior engine remain valid without backfill.
    revenue_performance_cents = Column(Integer, nullable=True)
    revenue_mechanical_cents = Column(Integer, nullable=True)
    revenue_sync_cents = Column(Integer, nullable=True)
    revenue_streaming_cents = Column(Integer, nullable=True)
    revenue_other_cents = Column(Integer, nullable=True)

    multiplier_performance = Column(Float, nullable=True)
    multiplier_mechanical = Column(Float, nullable=True)
    multiplier_sync = Column(Float, nullable=True)
    multiplier_streaming = Column(Float, nullable=True)

    artist_share_pct = Column(Float, nullable=True)
    publisher_share_pct = Column(Float, nullable=True)
    artist_valuation_cents = Column(Integer, nullable=True)
    publisher_valuation_cents = Column(Integer, nullable=True)

    # Discriminator: 'SOURCE_TYPED' vs legacy 'HYBRID' (kept alongside the
    # historical ``valuation_methodology`` text field for back-compat).
    valuation_method = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    
    song = relationship("Song", back_populates="valuation_calculations")
    organization = relationship("Organization")


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
