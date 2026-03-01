import re
import logging
from typing import Optional, Tuple
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger("cadence")


def _normalize_title(title: str) -> str:
    if not title:
        return ""
    t = title.lower().strip()
    t = re.sub(r'\s*\(feat\.?[^)]*\)', '', t)
    t = re.sub(r'\s*\[feat\.?[^]]*\]', '', t)
    t = re.sub(r'\s*ft\.?\s+.*$', '', t)
    t = re.sub(r'\s*\(.*?(remix|version|edit|mix|remaster|deluxe|live|acoustic|radio).*?\)', '', t, flags=re.IGNORECASE)
    t = re.sub(r'\s*\[.*?(remix|version|edit|mix|remaster|deluxe|live|acoustic|radio).*?\]', '', t, flags=re.IGNORECASE)
    t = re.sub(r'[^\w\s]', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _normalize_artist(artist: str) -> str:
    if not artist:
        return ""
    a = artist.lower().strip()
    a = re.sub(r'\s*,\s*', ' ', a)
    a = re.sub(r'\s*&\s*', ' ', a)
    a = re.sub(r'\s*and\s*', ' ', a)
    a = re.sub(r'\s*x\s+', ' ', a)
    a = re.sub(r'[^\w\s]', '', a)
    a = re.sub(r'\s+', ' ', a).strip()
    return a


def _similarity(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    words_a = set(a.split())
    words_b = set(b.split())
    if not words_a or not words_b:
        return 0.0

    intersection = words_a & words_b
    union = words_a | words_b
    return len(intersection) / len(union) if union else 0.0


def match_chart_entry_to_song(entry_title: str, entry_artist: str, entry_isrc: str = None,
                                entry_external_id: str = None, entry_platform: str = None,
                                db: Session = None, org_id: int = None) -> Tuple[Optional[int], float, str]:
    from ..models.models import Song, SongDSPLink

    if not db:
        return None, 0.0, "NO_DB"

    query = db.query(Song)
    if org_id:
        query = query.filter(Song.organization_id == org_id)

    if entry_isrc:
        song = query.filter(Song.isrc == entry_isrc).first()
        if song:
            return song.id, 0.95, "ISRC_MATCH"

    if entry_external_id and entry_platform == "SPOTIFY":
        dsp_link = db.query(SongDSPLink).filter(
            SongDSPLink.platform == "SPOTIFY",
            SongDSPLink.url.contains(entry_external_id)
        ).first()
        if dsp_link:
            return dsp_link.song_id, 0.9, "SPOTIFY_ID_MATCH"

        song = query.filter(Song.spotify_link.isnot(None), Song.spotify_link.contains(entry_external_id)).first()
        if song:
            return song.id, 0.9, "SPOTIFY_LINK_MATCH"

    norm_title = _normalize_title(entry_title)
    norm_artist = _normalize_artist(entry_artist)

    if not norm_title:
        return None, 0.0, "NO_TITLE"

    songs = query.all()
    best_match = None
    best_score = 0.0

    for song in songs:
        song_title = _normalize_title(song.title or "")
        song_artist = _normalize_artist(song.primary_artist or "")

        title_sim = _similarity(norm_title, song_title)
        if title_sim < 0.7:
            continue

        artist_sim = _similarity(norm_artist, song_artist) if norm_artist and song_artist else 0.5
        combined = (title_sim * 0.6) + (artist_sim * 0.4)

        if combined > best_score:
            best_score = combined
            best_match = song.id

    if best_match and best_score >= 0.75:
        return best_match, round(min(best_score * 0.8, 0.7), 2), "FUZZY_MATCH"

    return None, 0.0, "NO_MATCH"


def match_chart_entries(db: Session, entries: list = None, org_id: int = None) -> dict:
    from ..models.models import ChartEntry

    if entries is None:
        query = db.query(ChartEntry).filter(ChartEntry.song_id.is_(None))
        entries_to_match = query.all()
    else:
        entries_to_match = entries

    stats = {"total": len(entries_to_match), "matched": 0, "unmatched": 0, "methods": {}}

    for entry in entries_to_match:
        if isinstance(entry, dict):
            continue

        if entry.song_id is not None:
            stats["matched"] += 1
            continue

        song_id, confidence, method = match_chart_entry_to_song(
            entry_title=entry.title,
            entry_artist=entry.artist_name,
            entry_isrc=entry.isrc,
            entry_external_id=entry.external_track_id,
            entry_platform=entry.chart_source.platform if entry.chart_source else None,
            db=db,
            org_id=org_id,
        )

        if song_id:
            entry.song_id = song_id
            entry.matched_at = datetime.utcnow()
            if entry.extra_data is None:
                entry.extra_data = {}
            entry.extra_data = {**entry.extra_data, "match_confidence": confidence, "match_method": method}
            stats["matched"] += 1
            stats["methods"][method] = stats["methods"].get(method, 0) + 1
        else:
            stats["unmatched"] += 1

    db.commit()
    logger.info(f"Track matching complete: {stats['matched']}/{stats['total']} matched, methods: {stats['methods']}")
    return stats
