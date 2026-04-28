import logging
from datetime import datetime, timedelta, date

logger = logging.getLogger("cadence")

DEFAULT_CHART_SOURCES = [
    {"name": "Spotify Top 50 US", "platform": "SPOTIFY", "chart_type": "TOP_SONGS", "country_code": "US", "external_playlist_id": "37i9dQZEVXbLRQDuF5jeBp", "fetch_frequency": "DAILY"},
    {"name": "Spotify Top 50 Global", "platform": "SPOTIFY", "chart_type": "TOP_SONGS", "country_code": "GLOBAL", "external_playlist_id": "37i9dQZEVXbMDoHDwVN2tF", "fetch_frequency": "DAILY"},
    {"name": "Spotify Top 50 UK", "platform": "SPOTIFY", "chart_type": "TOP_SONGS", "country_code": "GB", "external_playlist_id": "37i9dQZEVXbLnolsZ8PSNw", "fetch_frequency": "DAILY"},
    {"name": "YouTube Trending Music US", "platform": "YOUTUBE", "chart_type": "TRENDING", "country_code": "US", "fetch_frequency": "DAILY"},
    {"name": "Apple Top 100 US", "platform": "APPLE", "chart_type": "TOP_SONGS", "country_code": "US", "url": "https://rss.itunes.apple.com/api/v1/us/itunes-music/top-songs/all/100/explicit.json", "fetch_frequency": "DAILY"},
    {"name": "Apple Top 100 Global", "platform": "APPLE", "chart_type": "TOP_SONGS", "country_code": "GLOBAL", "url": "https://rss.itunes.apple.com/api/v1/us/itunes-music/top-songs/all/100/explicit.json", "fetch_frequency": "DAILY"},
    {"name": "Deezer Global Top", "platform": "DEEZER", "chart_type": "TOP_SONGS", "country_code": "GLOBAL", "fetch_frequency": "DAILY"},
    {"name": "Last.fm Global Top", "platform": "LASTFM", "chart_type": "TOP_SONGS", "country_code": "GLOBAL", "fetch_frequency": "WEEKLY"},
]

FREQUENCY_HOURS = {
    "HOURLY": 1,
    "DAILY": 24,
    "WEEKLY": 168,
}


def seed_chart_sources(db):
    from ..models.models import ChartSource

    existing = db.query(ChartSource).count()
    if existing > 0:
        logger.info(f"Chart sources already seeded ({existing} sources)")
        return existing

    for src_data in DEFAULT_CHART_SOURCES:
        source = ChartSource(**src_data)
        db.add(source)

    db.commit()
    logger.info(f"Seeded {len(DEFAULT_CHART_SOURCES)} default chart sources")
    return len(DEFAULT_CHART_SOURCES)


def _is_fetch_due(source) -> bool:
    if not source.last_fetched_at:
        return True

    freq_hours = FREQUENCY_HOURS.get(source.fetch_frequency, 24)
    next_fetch = source.last_fetched_at + timedelta(hours=freq_hours)
    return datetime.utcnow() >= next_fetch


def _ingest_entries(source, entries: list, db):
    from ..models.models import ChartEntry

    today = date.today()
    added = 0
    skipped = 0

    for entry_data in entries:
        existing = db.query(ChartEntry).filter(
            ChartEntry.chart_source_id == source.id,
            ChartEntry.chart_date == today,
            ChartEntry.position == entry_data["position"],
        ).first()

        if existing:
            skipped += 1
            continue

        entry = ChartEntry(
            chart_source_id=source.id,
            chart_date=entry_data.get("chart_date", today),
            position=entry_data["position"],
            title=entry_data["title"],
            artist_name=entry_data["artist"],
            album_name=entry_data.get("album_name"),
            isrc=entry_data.get("isrc"),
            external_track_id=entry_data.get("external_id"),
            stream_count=entry_data.get("stream_count"),
            view_count=entry_data.get("view_count"),
            play_count=entry_data.get("play_count"),
            extra_data=entry_data.get("extra_data"),
        )
        db.add(entry)
        added += 1

    db.commit()
    return added, skipped


def fetch_source(source, db) -> dict:
    from .chart_fetcher import fetch_for_source

    kwargs = {}
    if source.platform == "SPOTIFY" and source.external_playlist_id:
        kwargs["playlist_id"] = source.external_playlist_id
    elif source.platform == "YOUTUBE":
        kwargs["region_code"] = source.country_code or "US"
    elif source.platform == "APPLE":
        kwargs["country"] = (source.country_code or "us").lower()
    elif source.platform == "LASTFM":
        if source.country_code and source.country_code != "GLOBAL":
            kwargs["country"] = source.country_code

    try:
        entries = fetch_for_source(source.platform, **kwargs)
        if not entries:
            source.last_error = "No entries returned"
            db.commit()
            return {"source": source.name, "status": "empty", "added": 0}

        added, skipped = _ingest_entries(source, entries, db)

        source.last_fetched_at = datetime.utcnow()
        source.last_error = None
        db.commit()

        logger.info(f"Chart source '{source.name}': {added} added, {skipped} skipped")
        return {"source": source.name, "status": "success", "added": added, "skipped": skipped}

    except Exception as e:
        logger.error(f"Chart fetch error for '{source.name}': {e}")
        source.last_error = str(e)[:500]
        db.commit()
        return {"source": source.name, "status": "error", "error": str(e)[:200]}


def run_chart_ingestion():
    from ..models.database import SessionLocal
    from ..models.models import ChartSource
    from .track_matcher import match_chart_entries
    from . import spotify_oauth

    db = SessionLocal()
    try:
        seed_chart_sources(db)

        sources = db.query(ChartSource).filter(ChartSource.is_active == True).all()
        results = []

        # Resolve once per run whether a listener Spotify OAuth token is
        # available. If not, every Spotify chart source is skipped with a
        # single warning so we don't spam the production log with 403s
        # every 4 hours (the dev-app owner doesn't have Premium, which
        # is what client-credentials needs).
        spotify_token_checked = False
        spotify_token_available = False
        spotify_skip_warned = False

        for source in sources:
            if not _is_fetch_due(source):
                continue

            if source.platform == "SPOTIFY":
                if not spotify_token_checked:
                    try:
                        spotify_token_available = bool(
                            spotify_oauth.get_valid_access_token()
                        )
                    except Exception as e:
                        logger.warning(
                            f"Spotify OAuth token lookup failed: {e}"
                        )
                        spotify_token_available = False
                    spotify_token_checked = True

                if not spotify_token_available:
                    if not spotify_skip_warned:
                        logger.warning(
                            "Skipping Spotify chart sources: no listener "
                            "OAuth token connected. Connect a Spotify "
                            "account in the Integrations panel to enable "
                            "chart ingestion."
                        )
                        spotify_skip_warned = True
                    continue

            result = fetch_source(source, db)
            results.append(result)

        if results:
            try:
                match_chart_entries(db)
            except Exception as e:
                logger.error(f"Track matching error during chart ingestion: {e}")

        logger.info(f"Chart ingestion complete: {len(results)} sources processed")

    except Exception as e:
        logger.error(f"Chart ingestion error: {e}")
    finally:
        db.close()
