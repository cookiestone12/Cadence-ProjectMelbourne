from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from ..models import get_db, Song, Creator, SongCredit, SongDSPLink, OrganizationMember, User
from ..utils.auth import get_current_user
from ..services import spotify_service

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

    tracks = spotify_service.get_playlist_tracks(data.playlist_url)
    if not tracks:
        raise HTTPException(status_code=400, detail="Could not fetch playlist tracks. Check the playlist URL and ensure Spotify is connected.")

    existing_isrcs = set()
    existing_songs = db.query(Song.isrc).filter(
        Song.organization_id == org_id,
        Song.isrc.isnot(None)
    ).all()
    existing_isrcs = {s.isrc for s in existing_songs if s.isrc}

    for track in tracks:
        track["already_exists"] = track.get("isrc") in existing_isrcs if track.get("isrc") else False

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

        if creator:
            credit = SongCredit(
                song_id=song.id,
                creator_id=creator.id,
                role="ARTIST",
            )
            db.add(credit)

        imported += 1

    db.commit()
    return {
        "message": f"Imported {imported} tracks, skipped {skipped} duplicates",
        "imported": imported,
        "skipped": skipped,
    }


@router.post("/search")
def search_spotify(
    data: SpotifySearchRequest,
    current_user: User = Depends(get_current_user)
):
    results = spotify_service.search_tracks(data.query, data.limit or 10)
    return {"results": results, "total": len(results)}
