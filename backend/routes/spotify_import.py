import logging
from difflib import SequenceMatcher
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from ..models import get_db, Song, Creator, SongCredit, SongDSPLink, OrganizationMember, User
from ..utils.auth import get_current_user
from ..services import spotify_service

logger = logging.getLogger("rythm")

router = APIRouter(prefix="/api/spotify", tags=["spotify"])


class PlaylistImportRequest(BaseModel):
    playlist_url: str
    creator_id: Optional[int] = None


class SpotifyTrackSelect(BaseModel):
    title: str
    primary_artist: str
    isrc: Optional[str] = None
    release_date: Optional[str] = None
    spotify_url: Optional[str] = None
    album_name: Optional[str] = None
    all_artists: Optional[List[str]] = []
    explicit: Optional[bool] = None
    track_number: Optional[int] = None
    duration_ms: Optional[int] = None
    popularity: Optional[int] = None


class PlaylistImportConfirm(BaseModel):
    tracks: List[SpotifyTrackSelect]
    creator_id: Optional[int] = None


class SpotifySearchRequest(BaseModel):
    query: str
    limit: Optional[int] = 10


def verify_org_access(user: User, org_id: int, db: Session):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    return membership


@router.post("/playlist/preview/{org_id}")
def preview_playlist_import(
    org_id: int,
    data: PlaylistImportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)

    from ..services.spotify_service import SpotifyForbiddenError, SpotifyAuthError

    try:
        tracks = spotify_service.get_playlist_tracks(data.playlist_url)
    except SpotifyForbiddenError as e:
        logger.error(f"Spotify 403 for org {org_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except SpotifyAuthError as e:
        logger.error(f"Spotify auth error for org {org_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Spotify playlist preview error for org {org_id}: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Spotify error: {str(e)}")

    if tracks is None or (isinstance(tracks, list) and len(tracks) == 0):
        token = spotify_service._get_access_token()
        if not token:
            logger.warning(f"Spotify playlist preview: no token available for org {org_id}")
            raise HTTPException(status_code=400, detail="Spotify is not connected. Please reconnect the Spotify integration in your project settings, or set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables.")

        logger.warning(f"Spotify playlist preview: empty result for org {org_id}, playlist URL: {data.playlist_url}")
        raise HTTPException(status_code=400, detail="Could not fetch playlist tracks. Please check that the playlist URL is correct and the playlist is public or accessible.")

    existing_isrcs = set()
    existing_songs = db.query(Song.isrc).filter(
        Song.organization_id == org_id,
        Song.isrc.isnot(None)
    ).all()
    existing_isrcs = {s.isrc for s in existing_songs if s.isrc}

    for track in tracks:
        track["already_exists"] = track.get("isrc") in existing_isrcs if track.get("isrc") else False

    all_songs = db.query(Song).filter(Song.organization_id == org_id).all()
    existing_titles = [(s.id, s.title.lower().strip(), (s.primary_artist or '').lower().strip()) for s in all_songs]

    for track in tracks:
        if track.get("already_exists"):
            continue
        track_title = (track.get("title") or "").lower().strip()
        track_artist = (track.get("primary_artist") or "").lower().strip()

        potential_matches = []
        for sid, etitle, eartist in existing_titles:
            title_sim = SequenceMatcher(None, track_title, etitle).ratio()
            artist_sim = SequenceMatcher(None, track_artist, eartist).ratio()
            combined = (title_sim * 0.7) + (artist_sim * 0.3)
            if combined >= 0.75 and title_sim >= 0.6:
                potential_matches.append({
                    "existing_song_id": sid,
                    "existing_title": etitle,
                    "existing_artist": eartist,
                    "similarity": round(combined, 2),
                })
        if potential_matches:
            potential_matches.sort(key=lambda x: x["similarity"], reverse=True)
            track["potential_duplicate"] = True
            track["duplicate_matches"] = potential_matches[:3]
        else:
            track["potential_duplicate"] = False

    return {
        "tracks": tracks,
        "total": len(tracks),
        "new_tracks": sum(1 for t in tracks if not t.get("already_exists")),
        "existing_tracks": sum(1 for t in tracks if t.get("already_exists")),
    }


@router.post("/playlist/import/{org_id}")
def import_playlist_tracks(
    org_id: int,
    data: PlaylistImportConfirm,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)

    creator = None
    if data.creator_id:
        creator = db.query(Creator).filter(
            Creator.id == data.creator_id,
            Creator.organization_id == org_id
        ).first()

    imported = 0
    skipped = 0
    credits_created = 0
    creators_created = 0

    for track_data in data.tracks:
        if track_data.isrc:
            existing = db.query(Song).filter(
                Song.organization_id == org_id,
                Song.isrc == track_data.isrc
            ).first()
            if existing:
                skipped += 1
                continue

        release_date = None
        if track_data.release_date:
            try:
                from datetime import date as date_type
                parts = track_data.release_date.split("-")
                if len(parts) == 3:
                    release_date = date_type(int(parts[0]), int(parts[1]), int(parts[2]))
                elif len(parts) == 1:
                    release_date = date_type(int(parts[0]), 1, 1)
            except (ValueError, IndexError):
                pass

        song = Song(
            organization_id=org_id,
            title=track_data.title,
            primary_artist=track_data.primary_artist,
            isrc=track_data.isrc,
            release_date=release_date,
            project_title=track_data.album_name,
            spotify_link=track_data.spotify_url,
            is_released=True,
            status_health_score=0.0,
        )
        db.add(song)
        db.flush()

        if track_data.spotify_url:
            dsp_link = SongDSPLink(
                song_id=song.id,
                platform="SPOTIFY",
                url=track_data.spotify_url,
            )
            db.add(dsp_link)

        credited_creator_ids = set()

        if creator:
            credit = SongCredit(
                song_id=song.id,
                creator_id=creator.id,
                role="ARTIST",
            )
            db.add(credit)
            credited_creator_ids.add(creator.id)
            credits_created += 1

        if track_data.all_artists and not creator:
            for idx, artist_name in enumerate(track_data.all_artists):
                if not artist_name:
                    continue
                artist_creator = db.query(Creator).filter(
                    Creator.organization_id == org_id,
                    Creator.display_name == artist_name
                ).first()
                if not artist_creator:
                    artist_creator = Creator(
                        organization_id=org_id,
                        display_name=artist_name,
                        roles=["ARTIST"],
                        contributor_type="ARTIST",
                    )
                    db.add(artist_creator)
                    db.flush()
                    creators_created += 1

                if artist_creator.id not in credited_creator_ids:
                    role = "ARTIST" if idx == 0 else "FEATURED_ARTIST"
                    artist_credit = SongCredit(
                        song_id=song.id,
                        creator_id=artist_creator.id,
                        role=role,
                    )
                    db.add(artist_credit)
                    credited_creator_ids.add(artist_creator.id)
                    credits_created += 1

        imported += 1

    from ..services.audit_service import log_action
    log_action(db, org_id, current_user.id, "IMPORT", "SONG", None, f"Spotify import: {imported} tracks", {"imported": imported, "skipped": skipped})
    db.commit()
    return {
        "message": f"Imported {imported} tracks, skipped {skipped} duplicates",
        "imported": imported,
        "skipped": skipped,
        "credits_created": credits_created,
        "creators_created": creators_created,
    }


@router.post("/search")
def search_spotify(
    data: SpotifySearchRequest,
    current_user: User = Depends(get_current_user)
):
    results = spotify_service.search_tracks(data.query, data.limit or 10)
    return {"results": results, "total": len(results)}
