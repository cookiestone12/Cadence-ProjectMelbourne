import logging
import math
from typing import Dict, Any, List, Optional
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

logger = logging.getLogger("cadence")

MARKET_SHARE_RATIOS = {
    "APPLE_MUSIC": 0.40,
    "AMAZON_MUSIC": 0.35,
    "YOUTUBE_MUSIC": 0.31,
    "TIDAL": 0.03,
    "DEEZER": 0.07,
}

PLATFORM_DISPLAY = {
    "SPOTIFY": {"name": "Spotify", "color": "#1DB954"},
    "APPLE_MUSIC": {"name": "Apple Music", "color": "#FC3C44"},
    "YOUTUBE_MUSIC": {"name": "YouTube Music", "color": "#FF0000"},
    "AMAZON_MUSIC": {"name": "Amazon Music", "color": "#00A8E1"},
    "TIDAL": {"name": "Tidal", "color": "#000000"},
    "DEEZER": {"name": "Deezer", "color": "#A238FF"},
}


def estimate_streams_for_song(song_id: int, org_id: int, db: Session) -> Dict[str, Any]:
    from ..models.models import Analytics, StreamEstimate, ChartEntry, Song, SongStreamingMetrics

    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        return {"error": "Song not found", "estimates": {}}

    analytics = db.query(Analytics).filter(Analytics.song_id == song_id).first()
    spotify_streams = 0
    if analytics and analytics.spotify_streams:
        spotify_streams = analytics.spotify_streams

    if spotify_streams == 0:
        latest_metric = db.query(SongStreamingMetrics).filter(
            SongStreamingMetrics.song_id == song_id,
        ).order_by(SongStreamingMetrics.period_date.desc()).first()
        if latest_metric and latest_metric.total_streams:
            spotify_streams = latest_metric.total_streams

    popularity_score = None

    if spotify_streams == 0:
        spotify_url = song.spotify_link
        if not spotify_url:
            from ..models.models import SongDSPLink
            dsp = db.query(SongDSPLink).filter(
                SongDSPLink.song_id == song_id,
                SongDSPLink.platform == "SPOTIFY",
            ).first()
            if dsp:
                spotify_url = dsp.url

        try:
            from .spotify_service import _get_access_token, _spotify_get
            token = _get_access_token()
            if token:
                if spotify_url:
                    track_id = _extract_spotify_id(spotify_url)
                    if track_id:
                        logger.info(f"Spotify API lookup for song {song_id}, track_id={track_id}")
                        data = _spotify_get(f"tracks/{track_id}", token)
                        if data and data.get("popularity") is not None:
                            popularity_score = data["popularity"]
                            spotify_streams = _estimate_from_popularity(popularity_score)
                            logger.info(f"Spotify popularity={popularity_score} -> estimated streams={spotify_streams:,} for song {song_id}")

                if spotify_streams == 0:
                    query_parts = []
                    if song.title:
                        clean_title = song.title.split(" - ")[0].split(" (")[0].strip()
                        query_parts.append(f"track:{clean_title}")
                    if song.primary_artist:
                        clean_artist = song.primary_artist.split(" feat.")[0].split(" ft.")[0].split(",")[0].strip()
                        query_parts.append(f"artist:{clean_artist}")
                    if query_parts:
                        search_query = " ".join(query_parts)
                        logger.info(f"Spotify search fallback for song {song_id}: '{search_query}'")
                        search_data = _spotify_get("search", token, {"q": search_query, "type": "track", "limit": 1})
                        if search_data and search_data.get("tracks", {}).get("items"):
                            track = search_data["tracks"]["items"][0]
                            pop = track.get("popularity", 0)
                            if pop > 0:
                                popularity_score = pop
                                spotify_streams = _estimate_from_popularity(popularity_score)
                                logger.info(f"Spotify search hit: '{track.get('name')}' by {[a.get('name') for a in track.get('artists', [])]} pop={pop} -> est={spotify_streams:,} for song {song_id}")
                        else:
                            logger.info(f"Spotify search returned no results for song {song_id}: '{search_query}'")
            else:
                logger.debug(f"No Spotify access token available for song {song_id}")
        except Exception as e:
            logger.debug(f"Spotify lookup/search failed for song {song_id}: {e}")

    chart_entries = db.query(ChartEntry).filter(ChartEntry.song_id == song_id).all()
    chart_data = {}
    for entry in chart_entries:
        platform = entry.chart_source.platform if entry.chart_source else "UNKNOWN"
        if platform not in chart_data or (entry.chart_date and entry.chart_date > chart_data[platform].get("date", date.min)):
            chart_data[platform] = {
                "position": entry.position,
                "date": entry.chart_date,
                "stream_count": entry.stream_count,
                "view_count": entry.view_count,
                "play_count": entry.play_count,
            }

    estimates = {}
    today = date.today()

    if spotify_streams > 0:
        if popularity_score is not None:
            method = "POPULARITY_ESTIMATE"
            confidence = 0.7
        else:
            method = "DIRECT_DATA"
            confidence = 0.9
        estimates["SPOTIFY"] = {
            "estimated_streams": spotify_streams,
            "actual_streams": spotify_streams if method == "DIRECT_DATA" else None,
            "method": method,
            "confidence": confidence,
        }
    elif "SPOTIFY" in chart_data:
        position = chart_data["SPOTIFY"]["position"]
        estimated = _estimate_from_chart_position(position, "SPOTIFY")
        estimates["SPOTIFY"] = {
            "estimated_streams": estimated,
            "actual_streams": None,
            "method": "CHART_POSITION",
            "confidence": 0.5,
        }

    base_spotify = estimates.get("SPOTIFY", {}).get("estimated_streams", 0)

    if base_spotify > 0:
        for platform, ratio in MARKET_SHARE_RATIOS.items():
            if platform in chart_data:
                chart_info = chart_data.get(platform, {})
                if chart_info.get("stream_count"):
                    estimates[platform] = {
                        "estimated_streams": chart_info["stream_count"],
                        "actual_streams": chart_info["stream_count"],
                        "method": "CHART_POSITION",
                        "confidence": 0.6,
                    }
                    continue

            estimated = int(base_spotify * ratio)
            estimates[platform] = {
                "estimated_streams": estimated,
                "actual_streams": None,
                "method": "MARKET_SHARE",
                "confidence": 0.3,
            }

    db.query(StreamEstimate).filter(
        StreamEstimate.song_id == song_id,
        StreamEstimate.organization_id == org_id,
    ).delete()
    db.flush()

    for platform, est in estimates.items():
        existing = db.query(StreamEstimate).filter(
            StreamEstimate.song_id == song_id,
            StreamEstimate.organization_id == org_id,
            StreamEstimate.platform == platform,
            StreamEstimate.period_date == today,
        ).first()

        if existing:
            existing.estimated_streams = est["estimated_streams"]
            existing.actual_streams = est.get("actual_streams")
            existing.estimation_method = est["method"]
            existing.confidence_score = est["confidence"]
            source = {"base_spotify": base_spotify, "chart_data": {k: {"position": v["position"]} for k, v in chart_data.items()}}
            if popularity_score is not None:
                source["spotify_popularity"] = popularity_score
            existing.source_data = source
            existing.updated_at = datetime.utcnow()
        else:
            source = {"base_spotify": base_spotify, "chart_data": {k: {"position": v["position"]} for k, v in chart_data.items()}}
            if popularity_score is not None:
                source["spotify_popularity"] = popularity_score
            db.add(StreamEstimate(
                song_id=song_id,
                organization_id=org_id,
                period_date=today,
                platform=platform,
                estimated_streams=est["estimated_streams"],
                actual_streams=est.get("actual_streams"),
                estimation_method=est["method"],
                confidence_score=est["confidence"],
                source_data=source,
            ))

    db.commit()

    total_streams = sum(e.get("estimated_streams", 0) for e in estimates.values())

    return {
        "song_id": song_id,
        "title": song.title,
        "artist": song.primary_artist,
        "total_estimated_streams": total_streams,
        "platform_breakdown": estimates,
        "riaa_equivalents": compute_riaa_equivalents(total_streams),
        "chart_appearances": len(chart_data),
        "computed_at": today.isoformat(),
    }


def _extract_spotify_id(spotify_link: str) -> Optional[str]:
    if not spotify_link:
        return None
    if "open.spotify.com/track/" in spotify_link:
        track_id = spotify_link.split("open.spotify.com/track/")[1].split("?")[0].split("/")[0]
        return track_id if track_id else None
    if len(spotify_link) == 22 and spotify_link.isalnum():
        return spotify_link
    return None


def _estimate_from_popularity(popularity: int) -> int:
    pop = max(0, min(100, popularity))
    return max(1000, int(48000 * math.exp(0.1288 * pop)))


def _estimate_from_chart_position(position: int, platform: str) -> int:
    if platform == "SPOTIFY":
        if position <= 5:
            return 5_000_000
        elif position <= 10:
            return 3_000_000
        elif position <= 25:
            return 1_500_000
        elif position <= 50:
            return 500_000
        else:
            return 100_000
    return 100_000


def compute_riaa_equivalents(total_streams: int) -> Dict[str, float]:
    return {
        "single_units": round(total_streams / 150, 1) if total_streams else 0,
        "album_units": round(total_streams / 1500, 1) if total_streams else 0,
    }


def estimate_all_songs(org_id: int, db: Session) -> Dict[str, Any]:
    from ..models.models import Song

    songs = db.query(Song).filter(
        Song.organization_id == org_id,
    ).all()
    results = {"total": len(songs), "estimated": 0, "errors": 0}

    for song in songs:
        try:
            result = estimate_streams_for_song(song.id, org_id, db)
            if result.get("total_estimated_streams", 0) > 0:
                results["estimated"] += 1
        except Exception as e:
            logger.error(f"Stream estimation error for song {song.id}: {e}")
            results["errors"] += 1

    logger.info(f"Batch stream estimation for org {org_id}: {results['estimated']}/{results['total']} songs estimated")
    return results


def get_song_stream_summary(song_id: int, org_id: int, db: Session) -> Dict[str, Any]:
    from ..models.models import StreamEstimate

    estimates = db.query(StreamEstimate).filter(
        StreamEstimate.song_id == song_id,
        StreamEstimate.organization_id == org_id,
    ).order_by(StreamEstimate.period_date.desc()).all()

    if not estimates:
        return {"total_streams": 0, "platforms": {}, "confidence": 0}

    latest_date = estimates[0].period_date if estimates else None
    latest = [e for e in estimates if e.period_date == latest_date]

    platforms = {}
    total = 0
    avg_confidence = 0

    for est in latest:
        streams = est.estimated_streams or 0
        platforms[est.platform] = {
            "streams": int(streams),
            "method": est.estimation_method,
            "confidence": est.confidence_score,
            "display": PLATFORM_DISPLAY.get(est.platform, {"name": est.platform, "color": "#666"}),
        }
        total += streams
        avg_confidence += est.confidence_score

    if latest:
        avg_confidence /= len(latest)

    return {
        "total_streams": int(total),
        "platforms": platforms,
        "confidence": round(avg_confidence, 2),
        "last_updated": latest_date.isoformat() if latest_date else None,
        "riaa_equivalents": compute_riaa_equivalents(int(total)),
    }
