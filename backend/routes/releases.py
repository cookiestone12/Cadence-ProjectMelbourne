from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
import csv
import io
import json
from ..models import get_db, Release, ReleaseTrack, Song, SongCredit, Creator, OrganizationMember, User
from ..utils.auth import get_current_user
from .client_sharing import has_shared_access
from ..services.spotify_service import lookup_release_metadata, SpotifyAuthError, SpotifyNotFoundError

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
    creator_id: Optional[int] = None


class ReleaseUpdate(BaseModel):
    title: Optional[str] = None
    release_type: Optional[str] = None
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
    creator_id: Optional[int] = None


class ReleaseTrackAdd(BaseModel):
    song_id: int
    track_number: Optional[int] = None
    disc_number: Optional[int] = 1
    is_bonus: Optional[bool] = False


class ReleaseTrackReorder(BaseModel):
    track_id: int
    track_number: int
    disc_number: Optional[int] = 1


def verify_org_access(user: User, org_id: int, db: Session, creator_id: int = None):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin:
        if creator_id and has_shared_access(db, user.id, creator_id, required_module="catalog"):
            return None
        raise HTTPException(status_code=403, detail="Access denied")
    return membership


DISTRIBUTION_CHECKS = {
    "release": [
        {"field": "upc", "label": "UPC/EAN code", "category": "identifiers", "required": True},
        {"field": "release_date", "label": "Release date", "category": "metadata", "required": True},
        {"field": "primary_artist", "label": "Primary artist", "category": "metadata", "required": True},
        {"field": "label", "label": "Label name", "category": "metadata", "required": True},
        {"field": "cover_art_url", "label": "Cover artwork", "category": "artwork", "required": True},
        {"field": "genre", "label": "Genre", "category": "metadata", "required": True},
        {"field": "copyright_line", "label": "Copyright notice (℗/©)", "category": "legal", "required": True},
        {"field": "copyright_year", "label": "Copyright year", "category": "legal", "required": True},
        {"field": "catalog_number", "label": "Catalog number", "category": "identifiers", "required": False},
    ],
    "track": [
        {"field": "isrc", "label": "ISRC", "category": "identifiers", "required": True},
        {"field": "title", "label": "Track title", "category": "metadata", "required": True},
        {"field": "primary_artist", "label": "Track artist", "category": "metadata", "required": True},
        {"field": "credits", "label": "Credits/contributors", "category": "credits", "required": True},
    ],
}

STATUS_TRANSITIONS = {
    "DRAFT": ["READY"],
    "READY": ["DRAFT", "SUBMITTED"],
    "SUBMITTED": ["READY", "RELEASED"],
    "RELEASED": [],
}


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


def get_distribution_readiness(release: Release, tracks: list, db: Session) -> dict:
    release_checks = []
    for check in DISTRIBUTION_CHECKS["release"]:
        value = getattr(release, check["field"], None)
        passed = value is not None and value != ""
        release_checks.append({
            "field": check["field"],
            "label": check["label"],
            "category": check["category"],
            "required": check["required"],
            "passed": passed,
            "value": str(value) if passed else None,
        })

    track_checks = []
    songs_data = []
    for rt in tracks:
        song = db.query(Song).filter(Song.id == rt.song_id).first()
        if not song:
            continue
        songs_data.append((rt, song))
        credits = db.query(SongCredit).filter(SongCredit.song_id == song.id).all()
        track_result = {
            "song_id": song.id,
            "title": song.title,
            "track_number": rt.track_number,
            "disc_number": rt.disc_number,
            "checks": [],
        }
        for check in DISTRIBUTION_CHECKS["track"]:
            if check["field"] == "credits":
                passed = len(credits) > 0
                track_result["checks"].append({
                    "field": check["field"],
                    "label": check["label"],
                    "category": check["category"],
                    "required": check["required"],
                    "passed": passed,
                    "value": f"{len(credits)} credits" if passed else None,
                })
            else:
                value = getattr(song, check["field"], None)
                passed = value is not None and value != ""
                track_result["checks"].append({
                    "field": check["field"],
                    "label": check["label"],
                    "category": check["category"],
                    "required": check["required"],
                    "passed": passed,
                    "value": str(value) if passed else None,
                })
        track_checks.append(track_result)

    has_tracks = len(tracks) > 0
    all_required_release = all(c["passed"] for c in release_checks if c["required"])
    all_required_tracks = all(
        all(tc["passed"] for tc in t["checks"] if tc["required"])
        for t in track_checks
    ) if track_checks else False

    total_required = sum(1 for c in release_checks if c["required"])
    total_required += sum(
        sum(1 for tc in t["checks"] if tc["required"])
        for t in track_checks
    )
    passed_required = sum(1 for c in release_checks if c["required"] and c["passed"])
    passed_required += sum(
        sum(1 for tc in t["checks"] if tc["required"] and tc["passed"])
        for t in track_checks
    )
    if not has_tracks:
        total_required += 1

    readiness_score = round((passed_required / total_required) * 100, 1) if total_required > 0 else 0
    is_ready = has_tracks and all_required_release and all_required_tracks

    return {
        "is_ready": is_ready,
        "readiness_score": readiness_score,
        "total_required": total_required,
        "passed_required": passed_required,
        "has_tracks": has_tracks,
        "release_checks": release_checks,
        "track_checks": track_checks,
    }


def _build_track_export_data(release: Release, tracks: list, db: Session) -> list:
    rows = []
    for rt in tracks:
        song = db.query(Song).filter(Song.id == rt.song_id).first()
        if not song:
            continue
        credits = db.query(SongCredit).join(Creator, SongCredit.creator_id == Creator.id).filter(
            SongCredit.song_id == song.id
        ).all()
        credit_names = []
        for c in credits:
            creator = db.query(Creator).filter(Creator.id == c.creator_id).first()
            if creator:
                credit_names.append(f"{creator.display_name} ({c.role})")

        rows.append({
            "release_title": release.title,
            "release_type": release.release_type,
            "release_upc": release.upc or "",
            "release_label": release.label or "",
            "release_date": release.release_date.isoformat() if release.release_date else "",
            "release_genre": release.genre or "",
            "release_copyright": release.copyright_line or "",
            "release_copyright_year": str(release.copyright_year) if release.copyright_year else "",
            "disc_number": str(rt.disc_number),
            "track_number": str(rt.track_number),
            "track_title": song.title,
            "track_artist": song.primary_artist,
            "isrc": song.isrc or "",
            "iswc": song.iswc or "",
            "is_bonus": "Yes" if rt.is_bonus else "No",
            "credits": "; ".join(credit_names),
        })
    return rows


@router.get("/org/{org_id}")
def list_releases(
    org_id: int,
    search: Optional[str] = None,
    status: Optional[str] = None,
    release_type: Optional[str] = None,
    creator_id: Optional[int] = None,
    limit: int = Query(default=100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Cadence staff get cross-org READ access (Task #74); writes still gated.
    if not getattr(current_user, "is_cadence_staff", False):
        verify_org_access(current_user, org_id, db, creator_id=creator_id)
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
    if creator_id:
        query = query.filter(Release.creator_id == creator_id)

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
            "creator_id": r.creator_id,
            "creator_name": r.creator.display_name if r.creator else None,
            "track_count": track_count,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {"releases": results, "total": total}


@router.get("/{release_id}")
def get_release(release_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    # Cadence staff get cross-org READ access (Task #74); writes still gated.
    if not getattr(current_user, "is_cadence_staff", False):
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
                "audio_file_url": getattr(song, 'audio_file_url', None),
                "lyrics": getattr(song, 'lyrics', None),
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
        "creator_id": release.creator_id,
        "creator_name": release.creator.display_name if release.creator else None,
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
        creator_id=data.creator_id,
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


@router.get("/{release_id}/readiness")
def check_distribution_readiness(release_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    release_tracks = db.query(ReleaseTrack).filter(
        ReleaseTrack.release_id == release_id
    ).order_by(ReleaseTrack.disc_number, ReleaseTrack.track_number).all()

    return get_distribution_readiness(release, release_tracks, db)


class StatusTransition(BaseModel):
    new_status: str
    force: Optional[bool] = False


@router.post("/{release_id}/transition")
def transition_release_status(release_id: int, data: StatusTransition, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    current_status = release.status or "DRAFT"
    new_status = data.new_status.upper()

    allowed = STATUS_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {current_status} to {new_status}. Allowed: {', '.join(allowed) if allowed else 'none'}"
        )

    if new_status in ("READY", "SUBMITTED"):
        release_tracks = db.query(ReleaseTrack).filter(ReleaseTrack.release_id == release_id).all()
        readiness = get_distribution_readiness(release, release_tracks, db)

        if new_status == "SUBMITTED" and not readiness["is_ready"] and not data.force:
            missing = []
            for rc in readiness["release_checks"]:
                if rc["required"] and not rc["passed"]:
                    missing.append(rc["label"])
            for tc in readiness["track_checks"]:
                for check in tc["checks"]:
                    if check["required"] and not check["passed"]:
                        missing.append(f"{tc['title']}: {check['label']}")
            raise HTTPException(
                status_code=400,
                detail=f"Release is not distribution-ready. Missing: {', '.join(missing[:10])}"
            )

    release.status = new_status
    db.commit()
    db.refresh(release)

    return {
        "id": release.id,
        "status": release.status,
        "message": f"Release status updated to {new_status}",
    }


@router.get("/{release_id}/export/csv")
def export_release_csv(release_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    release_tracks = db.query(ReleaseTrack).filter(
        ReleaseTrack.release_id == release_id
    ).order_by(ReleaseTrack.disc_number, ReleaseTrack.track_number).all()

    rows = _build_track_export_data(release, release_tracks, db)

    if not rows:
        raise HTTPException(status_code=400, detail="No tracks to export")

    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)

    safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in release.title).strip().replace(" ", "_")
    filename = f"{safe_title}_distribution_{datetime.utcnow().strftime('%Y%m%d')}.csv"

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode("utf-8")),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{release_id}/export/pdf")
def export_release_pdf(release_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    import os

    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    release_tracks = db.query(ReleaseTrack).filter(
        ReleaseTrack.release_id == release_id
    ).order_by(ReleaseTrack.disc_number, ReleaseTrack.track_number).all()

    sage = colors.HexColor("#5B8A72")
    sage_light = colors.HexColor("#E8F0EB")
    dark_text = colors.HexColor("#3D4A44")
    muted = colors.HexColor("#7A8580")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                            topMargin=0.5*inch, bottomMargin=0.5*inch,
                            leftMargin=0.6*inch, rightMargin=0.6*inch)

    styles = getSampleStyleSheet()
    style_title = ParagraphStyle('RTitle', parent=styles['Title'], fontSize=22, textColor=dark_text, spaceAfter=4)
    style_subtitle = ParagraphStyle('RSub', parent=styles['Normal'], fontSize=11, textColor=muted, spaceAfter=12)
    style_heading = ParagraphStyle('RHead', parent=styles['Heading2'], fontSize=14, textColor=sage, spaceBefore=16, spaceAfter=8)
    style_normal = ParagraphStyle('RNorm', parent=styles['Normal'], fontSize=10, textColor=dark_text, leading=14)
    style_small = ParagraphStyle('RSmall', parent=styles['Normal'], fontSize=8, textColor=muted, leading=11)
    style_lyrics = ParagraphStyle('RLyrics', parent=styles['Normal'], fontSize=9, textColor=dark_text, leading=13, leftIndent=12, fontName='Courier')
    style_link = ParagraphStyle('RLink', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor("#2563EB"), leading=12)
    style_center = ParagraphStyle('RCenter', parent=styles['Normal'], fontSize=8, textColor=muted, alignment=TA_CENTER)

    elements = []

    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'cadence-logo.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=2.0*inch, height=1.125*inch)
        logo.hAlign = 'LEFT'
        elements.append(logo)
        elements.append(Spacer(1, 6))

    elements.append(Paragraph(release.title or "Untitled Release", style_title))
    subtitle_parts = []
    if release.primary_artist:
        subtitle_parts.append(release.primary_artist)
    if release.release_type:
        subtitle_parts.append(release.release_type)
    if release.label:
        subtitle_parts.append(release.label)
    elements.append(Paragraph(" · ".join(subtitle_parts), style_subtitle))

    elements.append(HRFlowable(width="100%", thickness=1, color=sage_light, spaceAfter=12))

    elements.append(Paragraph("Release Information", style_heading))
    meta_data = [
        ["UPC", release.upc or "—", "Catalog #", release.catalog_number or "—"],
        ["Release Date", release.release_date.strftime("%B %d, %Y") if release.release_date else "—",
         "Genre", f"{release.genre or '—'}{(' / ' + release.subgenre) if release.subgenre else ''}"],
        ["Copyright", f"{release.copyright_line or '—'} ({release.copyright_year or '—'})",
         "Status", release.status or "—"],
    ]
    meta_table = Table(meta_data, colWidths=[1.2*inch, 2.3*inch, 1.2*inch, 2.3*inch])
    meta_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), muted),
        ('TEXTCOLOR', (2, 0), (2, -1), muted),
        ('TEXTCOLOR', (1, 0), (1, -1), dark_text),
        ('TEXTCOLOR', (3, 0), (3, -1), dark_text),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 8))

    elements.append(Paragraph(f"Track Listing ({len(release_tracks)} tracks)", style_heading))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=sage_light, spaceAfter=6))

    for rt in release_tracks:
        song = db.query(Song).filter(Song.id == rt.song_id).first()
        if not song:
            continue

        track_num = f"{rt.disc_number}-{rt.track_number}" if rt.disc_number and rt.disc_number > 1 else str(rt.track_number)
        bonus_tag = " [Bonus]" if rt.is_bonus else ""
        elements.append(Paragraph(f"<b>{track_num}. {song.title}{bonus_tag}</b>", style_normal))

        detail_parts = []
        if song.primary_artist:
            detail_parts.append(f"Artist: {song.primary_artist}")
        if song.isrc:
            detail_parts.append(f"ISRC: {song.isrc}")
        if getattr(song, 'iswc', None):
            detail_parts.append(f"ISWC: {song.iswc}")
        if detail_parts:
            elements.append(Paragraph(" · ".join(detail_parts), style_small))

        credits = db.query(SongCredit).filter(SongCredit.song_id == song.id).all()
        if credits:
            credit_strs = []
            for c in credits:
                creator = db.query(Creator).filter(Creator.id == c.creator_id).first()
                if creator:
                    share = f" ({c.share_percentage}%)" if c.share_percentage else ""
                    credit_strs.append(f"{creator.display_name} — {c.role}{share}")
            if credit_strs:
                elements.append(Paragraph("Credits: " + ", ".join(credit_strs), style_small))

        audio_url = getattr(song, 'audio_file_url', None)
        if audio_url:
            elements.append(Paragraph(f'Audio: <a href="{audio_url}" color="#2563EB">{audio_url}</a>', style_link))

        lyrics = getattr(song, 'lyrics', None)
        if lyrics:
            elements.append(Spacer(1, 4))
            elements.append(Paragraph("<b>Lyrics:</b>", style_small))
            for line in lyrics.split('\n'):
                elements.append(Paragraph(line or "&nbsp;", style_lyrics))

        elements.append(Spacer(1, 8))
        elements.append(HRFlowable(width="100%", thickness=0.3, color=sage_light, spaceAfter=6))

    health_data = get_release_health(release, release_tracks, db)
    if health_data:
        elements.append(Paragraph("Distribution Readiness", style_heading))
        score = health_data.get("score", 0)
        score_color = sage if score >= 80 else (colors.HexColor("#D97706") if score >= 50 else colors.HexColor("#DC2626"))
        elements.append(Paragraph(f"<b>Readiness Score: {score}%</b>", ParagraphStyle('Score', parent=style_normal, textColor=score_color, fontSize=12)))
        elements.append(Spacer(1, 6))

        issues = health_data.get("issues", [])
        passed = health_data.get("passed", 0)
        total = health_data.get("total_checks", 0)
        elements.append(Paragraph(f"{passed} of {total} checks passed", style_small))
        elements.append(Spacer(1, 4))

        if issues:
            for issue in issues:
                elements.append(Paragraph(
                    f'<font color="#DC2626">✗</font> {issue}',
                    style_normal
                ))
        else:
            elements.append(Paragraph(
                f'<font color="{sage}">✓</font> All checks passed — ready for distribution',
                style_normal
            ))

    elements.append(Spacer(1, 20))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=sage_light, spaceAfter=8))
    elements.append(Paragraph(f"Generated by Cadence Catalog Intelligence · {datetime.utcnow().strftime('%B %d, %Y at %H:%M UTC')}", style_center))

    doc.build(elements)
    buffer.seek(0)

    safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in release.title).strip().replace(" ", "_")
    filename = f"{safe_title}_distribution_{datetime.utcnow().strftime('%Y%m%d')}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{release_id}/export/json")
def export_release_json(release_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    release_tracks = db.query(ReleaseTrack).filter(
        ReleaseTrack.release_id == release_id
    ).order_by(ReleaseTrack.disc_number, ReleaseTrack.track_number).all()

    tracks_json = []
    for rt in release_tracks:
        song = db.query(Song).filter(Song.id == rt.song_id).first()
        if not song:
            continue
        credits = db.query(SongCredit).filter(SongCredit.song_id == song.id).all()
        credit_list = []
        for c in credits:
            creator = db.query(Creator).filter(Creator.id == c.creator_id).first()
            if creator:
                credit_list.append({
                    "name": creator.display_name,
                    "role": c.role,
                    "share_percentage": c.share_percentage,
                })
        tracks_json.append({
            "disc_number": rt.disc_number,
            "track_number": rt.track_number,
            "title": song.title,
            "artist": song.primary_artist,
            "isrc": song.isrc,
            "iswc": getattr(song, 'iswc', None),
            "is_bonus": rt.is_bonus,
            "audio_file_url": getattr(song, 'audio_file_url', None),
            "lyrics": getattr(song, 'lyrics', None),
            "credits": credit_list,
        })

    export_data = {
        "schema_version": "1.0",
        "export_date": datetime.utcnow().isoformat(),
        "release": {
            "title": release.title,
            "release_type": release.release_type,
            "status": release.status,
            "primary_artist": release.primary_artist,
            "label": release.label,
            "upc": release.upc,
            "catalog_number": release.catalog_number,
            "release_date": release.release_date.isoformat() if release.release_date else None,
            "genre": release.genre,
            "copyright_line": release.copyright_line,
            "copyright_year": release.copyright_year,
        },
        "tracks": tracks_json,
        "track_count": len(tracks_json),
    }

    safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "" for c in release.title).strip().replace(" ", "_")
    filename = f"{safe_title}_distribution_{datetime.utcnow().strftime('%Y%m%d')}.json"

    json_bytes = json.dumps(export_data, indent=2, ensure_ascii=False).encode("utf-8")

    return StreamingResponse(
        io.BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/{release_id}/artwork")
async def get_release_artwork(
    release_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    if not current_user.is_super_admin:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == release.organization_id
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="Not authorized")
    if release.cover_art_data:
        return Response(
            content=release.cover_art_data,
            media_type=release.cover_art_mime or "image/jpeg",
            headers={"Cache-Control": "private, max-age=3600"}
        )
    raise HTTPException(status_code=404, detail="No artwork uploaded")


@router.post("/{release_id}/artwork")
async def upload_release_artwork(
    release_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")

    if not current_user.is_super_admin:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == release.organization_id
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="Not authorized")

    allowed_types = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"File type {file.content_type} not allowed. Use JPEG, PNG, WebP, or GIF.")

    content = await file.read()
    max_size = 10 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")

    release.cover_art_data = content
    release.cover_art_mime = file.content_type
    release.cover_art_url = f"/api/releases/{release_id}/artwork"
    db.commit()

    return {"cover_art_url": release.cover_art_url}


@router.delete("/{release_id}/artwork")
async def delete_release_artwork(
    release_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")

    if not current_user.is_super_admin:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == release.organization_id
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="Not authorized")

    release.cover_art_data = None
    release.cover_art_mime = None
    release.cover_art_url = None
    db.commit()

    return {"message": "Artwork removed"}


class SendToDistributionRequest(BaseModel):
    recipient_email: Optional[str] = None
    recipient_name: Optional[str] = None
    notes: Optional[str] = None
    subject: Optional[str] = None
    message: Optional[str] = None


@router.post("/{release_id}/send-to-distribution")
def send_release_to_distribution(
    release_id: int,
    data: SendToDistributionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from ..models import CreatorContact, CreativeContact
    from ..templates.email_templates import release_distribution as release_dist_template
    from ..services.email_provider import get_email_provider

    release = db.query(Release).filter(Release.id == release_id).first()
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    verify_org_access(current_user, release.organization_id, db)

    to_email = data.recipient_email
    to_name = data.recipient_name or "Distribution Contact"

    if not to_email and release.creator_id:
        dist_contact = db.query(CreatorContact).filter(
            CreatorContact.creator_id == release.creator_id,
            CreatorContact.role == "DISTRIBUTION",
        ).first()
        if dist_contact:
            contact = db.query(CreativeContact).filter(CreativeContact.id == dist_contact.contact_id).first()
            if contact and contact.email:
                to_email = contact.email
                to_name = contact.display_name or to_name

    if not to_email:
        raise HTTPException(status_code=400, detail="No distribution contact email found. Please provide a recipient email or assign a DISTRIBUTION contact to this creator.")

    release_tracks = db.query(ReleaseTrack).filter(
        ReleaseTrack.release_id == release_id
    ).order_by(ReleaseTrack.disc_number, ReleaseTrack.track_number).all()

    tracks_list = []
    for rt in release_tracks:
        song = db.query(Song).filter(Song.id == rt.song_id).first()
        if song:
            tracks_list.append({"title": song.title, "isrc": song.isrc or ""})

    sender_name = getattr(current_user, 'full_name', None) or current_user.username

    html_body = release_dist_template(
        recipient_name=to_name,
        release_title=release.title,
        artist_name=release.primary_artist or "",
        release_date=release.release_date.isoformat() if release.release_date else "",
        upc=release.upc or "",
        label=release.label or "",
        track_count=len(tracks_list),
        tracks=tracks_list,
        notes=data.notes or data.message or "",
        sender_name=sender_name,
    )

    email_subject = data.subject or f"Release Delivery: {release.title} by {release.primary_artist or 'Unknown'}"
    provider = get_email_provider()
    success = provider.send_email(
        to=to_email,
        subject=email_subject,
        html_body=html_body,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send email")

    return {"success": True, "message": f"Release info sent to {to_email}", "recipient": to_email}


class SpotifyLookupRequest(BaseModel):
    spotify_url: str


@router.post("/spotify-lookup")
async def spotify_lookup(
    body: SpotifyLookupRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        metadata = lookup_release_metadata(body.spotify_url)
        return metadata
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except SpotifyNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except SpotifyAuthError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to look up Spotify data: {str(e)}")
