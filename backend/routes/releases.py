from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from ..models import get_db, Release, ReleaseTrack, Song, OrganizationMember, User
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/releases", tags=["releases"])


class ReleaseCreate(BaseModel):
    title: str
    release_type: Optional[str] = "SINGLE"
    primary_artist: Optional[str] = None
    label: Optional[str] = None
    upc: Optional[str] = None
    catalog_number: Optional[str] = None
    release_date: Optional[date] = None
    original_release_date: Optional[date] = None
    genre: Optional[str] = None
    subgenre: Optional[str] = None
    cover_art_url: Optional[str] = None
    description: Optional[str] = None
    copyright_line: Optional[str] = None
    copyright_year: Optional[int] = None
    notes: Optional[str] = None


class ReleaseUpdate(BaseModel):
    title: Optional[str] = None
    release_type: Optional[str] = None
    status: Optional[str] = None
    primary_artist: Optional[str] = None
    label: Optional[str] = None
    upc: Optional[str] = None
    catalog_number: Optional[str] = None
    release_date: Optional[date] = None
    original_release_date: Optional[date] = None
    genre: Optional[str] = None
    subgenre: Optional[str] = None
    cover_art_url: Optional[str] = None
    description: Optional[str] = None
    copyright_line: Optional[str] = None
    copyright_year: Optional[int] = None
    notes: Optional[str] = None
    spotify_url: Optional[str] = None
    apple_music_url: Optional[str] = None


class ReleaseTrackAdd(BaseModel):
    song_id: int
    track_number: Optional[int] = None
    disc_number: Optional[int] = 1
    is_bonus: Optional[bool] = False


class ReleaseTrackReorder(BaseModel):
    track_id: int
    track_number: int
    disc_number: Optional[int] = 1


def verify_org_access(user: User, org_id: int, db: Session):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    return membership


def get_release_health(release: Release, tracks: list, db: Session) -> dict:
    issues = []
    if not release.upc:
        issues.append("Missing UPC/EAN code")
    if not release.release_date:
        issues.append("No release date set")
    if not release.primary_artist:
        issues.append("No primary artist")
    if not release.label:
        issues.append("No label specified")
    if not release.cover_art_url:
        issues.append("No cover art")
    if len(tracks) == 0:
        issues.append("No tracks added")

    for t in tracks:
        song = db.query(Song).filter(Song.id == t.song_id).first()
        if song and not song.isrc:
            issues.append(f"Track '{song.title}' missing ISRC")

    total_checks = 6 + len(tracks)
    passed = total_checks - len(issues)
    score = round((passed / total_checks) * 100, 1) if total_checks > 0 else 0

    return {"score": score, "issues": issues, "total_checks": total_checks, "passed": passed}


@router.get("/org/{org_id}")
def list_releases(
    org_id: int,
    search: Optional[str] = None,
    status: Optional[str] = None,
    release_type: Optional[str] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)
    query = db.query(Release).filter(Release.organization_id == org_id)

    if search:
        query = query.filter(
            or_(
                Release.title.ilike(f"%{search}%"),
                Release.primary_artist.ilike(f"%{search}%"),
                Release.upc.ilike(f"%{search}%")
            )
        )
    if status:
        query = query.filter(Release.status == status)
    if release_type:
        query = query.filter(Release.release_type == release_type)

    total = query.count()
    releases = query.order_by(Release.created_at.desc()).offset(offset).limit(limit).all()

    results = []
    for r in releases:
        track_count = db.query(ReleaseTrack).filter(ReleaseTrack.release_id == r.id).count()
        results.append({
            "id": r.id,
            "title": r.title,
            "release_type": r.release_type,
            "status": r.status,
            "primary_artist": r.primary_artist,
            "label": r.label,
            "upc": r.upc,
            "release_date": r.release_date.isoformat() if r.release_date else None,
            "genre": r.genre,
            "cover_art_url": r.cover_art_url,
            "track_count": track_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {"releases": results, "total": total}


@router.get("/{release_id}")
def get_release(release_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    release_tracks = db.query(ReleaseTrack).filter(
        ReleaseTrack.release_id == release_id
    ).order_by(ReleaseTrack.disc_number, ReleaseTrack.track_number).all()

    tracks = []
    for rt in release_tracks:
        song = db.query(Song).filter(Song.id == rt.song_id).first()
        if song:
            tracks.append({
                "id": rt.id,
                "song_id": song.id,
                "title": song.title,
                "primary_artist": song.primary_artist,
                "isrc": song.isrc,
                "track_number": rt.track_number,
                "disc_number": rt.disc_number,
                "is_bonus": rt.is_bonus,
                "duration": None,
            })

    health = get_release_health(release, release_tracks, db)

    return {
        "id": release.id,
        "title": release.title,
        "release_type": release.release_type,
        "status": release.status,
        "primary_artist": release.primary_artist,
        "label": release.label,
        "upc": release.upc,
        "catalog_number": release.catalog_number,
        "release_date": release.release_date.isoformat() if release.release_date else None,
        "original_release_date": release.original_release_date.isoformat() if release.original_release_date else None,
        "genre": release.genre,
        "subgenre": release.subgenre,
        "cover_art_url": release.cover_art_url,
        "description": release.description,
        "copyright_line": release.copyright_line,
        "copyright_year": release.copyright_year,
        "notes": release.notes,
        "spotify_url": release.spotify_url,
        "apple_music_url": release.apple_music_url,
        "tracks": tracks,
        "health": health,
        "created_at": release.created_at.isoformat() if release.created_at else None,
        "updated_at": release.updated_at.isoformat() if release.updated_at else None,
    }


@router.post("/org/{org_id}")
def create_release(org_id: int, data: ReleaseCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    verify_org_access(current_user, org_id, db)

    release = Release(
        organization_id=org_id,
        title=data.title,
        release_type=data.release_type or "SINGLE",
        primary_artist=data.primary_artist,
        label=data.label,
        upc=data.upc,
        catalog_number=data.catalog_number,
        release_date=data.release_date,
        original_release_date=data.original_release_date,
        genre=data.genre,
        subgenre=data.subgenre,
        cover_art_url=data.cover_art_url,
        description=data.description,
        copyright_line=data.copyright_line,
        copyright_year=data.copyright_year,
        notes=data.notes,
    )
    db.add(release)
    db.commit()
    db.refresh(release)
    return {"id": release.id, "title": release.title, "message": "Release created successfully"}


@router.put("/{release_id}")
def update_release(release_id: int, data: ReleaseUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    for field, value in data.dict(exclude_unset=True).items():
        setattr(release, field, value)

    db.commit()
    db.refresh(release)
    return {"id": release.id, "title": release.title, "message": "Release updated successfully"}


@router.delete("/{release_id}")
def delete_release(release_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    db.delete(release)
    db.commit()
    return {"message": "Release deleted successfully"}


@router.post("/{release_id}/tracks")
def add_track_to_release(release_id: int, data: ReleaseTrackAdd, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    song = db.query(Song).filter(Song.id == data.song_id, Song.organization_id == release.organization_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Track not found in this organization")

    existing = db.query(ReleaseTrack).filter(ReleaseTrack.release_id == release_id, ReleaseTrack.song_id == data.song_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Track already in this release")

    if data.track_number is None:
        max_track = db.query(ReleaseTrack).filter(
            ReleaseTrack.release_id == release_id,
            ReleaseTrack.disc_number == (data.disc_number or 1)
        ).count()
        track_number = max_track + 1
    else:
        track_number = data.track_number

    rt = ReleaseTrack(
        release_id=release_id,
        song_id=data.song_id,
        track_number=track_number,
        disc_number=data.disc_number or 1,
        is_bonus=data.is_bonus or False,
    )
    db.add(rt)
    db.commit()
    return {"message": "Track added to release", "track_number": track_number}


@router.delete("/{release_id}/tracks/{song_id}")
def remove_track_from_release(release_id: int, song_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    rt = db.query(ReleaseTrack).filter(ReleaseTrack.release_id == release_id, ReleaseTrack.song_id == song_id).first()
    if not rt:
        raise HTTPException(status_code=404, detail="Track not in this release")

    db.delete(rt)
    db.commit()

    remaining = db.query(ReleaseTrack).filter(
        ReleaseTrack.release_id == release_id
    ).order_by(ReleaseTrack.disc_number, ReleaseTrack.track_number).all()
    for i, track in enumerate(remaining, 1):
        track.track_number = i
    db.commit()

    return {"message": "Track removed from release"}


@router.put("/{release_id}/tracks/reorder")
def reorder_tracks(release_id: int, tracks: List[ReleaseTrackReorder], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    for item in tracks:
        rt = db.query(ReleaseTrack).filter(ReleaseTrack.id == item.track_id, ReleaseTrack.release_id == release_id).first()
        if rt:
            rt.track_number = item.track_number
            rt.disc_number = item.disc_number or 1

    db.commit()
    return {"message": "Tracks reordered successfully"}


@router.get("/{release_id}/health")
def check_release_health(release_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    release_tracks = db.query(ReleaseTrack).filter(ReleaseTrack.release_id == release_id).all()
    return get_release_health(release, release_tracks, db)
