from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from ..models import (
    get_db, Song, Work, Release, Creator, SongCredit,
    OrganizationMember, User
)
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/bulk", tags=["bulk"])


class BulkSongUpdate(BaseModel):
    song_ids: List[int]
    updates: Dict[str, Any]


class BulkAssignCredit(BaseModel):
    song_ids: List[int]
    creator_id: int
    role: str
    share_percentage: Optional[float] = None


ALLOWED_BULK_FIELDS = {
    "label",
    "is_released", "notes", "project_title",
    "is_registered_with_pro", "is_registered_with_dsp",
    "has_contract_sent", "has_contract_executed",
    "is_invoiced", "is_paid", "soundexchange_registered",
    "payment_status", "master_paid",
}


def verify_org_access(user: User, org_id: int, db: Session):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    return membership


@router.put("/songs/{org_id}")
def bulk_update_songs(
    org_id: int,
    data: BulkSongUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)

    invalid_fields = set(data.updates.keys()) - ALLOWED_BULK_FIELDS
    if invalid_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Fields not allowed for bulk update: {', '.join(invalid_fields)}"
        )

    songs = db.query(Song).filter(
        Song.id.in_(data.song_ids),
        Song.organization_id == org_id
    ).all()

    if not songs:
        raise HTTPException(status_code=404, detail="No matching songs found")

    updated_count = 0
    for song in songs:
        for field, value in data.updates.items():
            if hasattr(song, field):
                setattr(song, field, value)
        updated_count += 1

    db.commit()
    return {"message": f"Updated {updated_count} songs", "updated_count": updated_count}


@router.post("/songs/{org_id}/credits")
def bulk_assign_credits(
    org_id: int,
    data: BulkAssignCredit,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)

    creator = db.query(Creator).filter(
        Creator.id == data.creator_id,
        Creator.organization_id == org_id
    ).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found in this organization")

    songs = db.query(Song).filter(
        Song.id.in_(data.song_ids),
        Song.organization_id == org_id
    ).all()

    if not songs:
        raise HTTPException(status_code=404, detail="No matching songs found")

    added = 0
    skipped = 0
    for song in songs:
        existing = db.query(SongCredit).filter(
            SongCredit.song_id == song.id,
            SongCredit.creator_id == data.creator_id,
            SongCredit.role == data.role
        ).first()
        if existing:
            skipped += 1
            continue

        credit = SongCredit(
            song_id=song.id,
            creator_id=data.creator_id,
            role=data.role,
            share_percentage=data.share_percentage,
        )
        db.add(credit)
        added += 1

    db.commit()
    return {"message": f"Added {added} credits, skipped {skipped} duplicates", "added": added, "skipped": skipped}


@router.get("/search/{org_id}")
def global_search(
    org_id: int,
    q: str = Query(..., min_length=1),
    entity_types: Optional[str] = None,
    limit: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(current_user, org_id, db)

    types = entity_types.split(",") if entity_types else ["songs", "works", "releases", "creators"]
    results = {}
    search_pattern = f"%{q}%"

    if "songs" in types:
        songs = db.query(Song).filter(
            Song.organization_id == org_id,
            or_(
                Song.title.ilike(search_pattern),
                Song.primary_artist.ilike(search_pattern),
                Song.isrc.ilike(search_pattern),
                Song.iswc.ilike(search_pattern),
                Song.label.ilike(search_pattern),
            )
        ).limit(limit).all()
        results["songs"] = [{
            "id": s.id, "title": s.title, "primary_artist": s.primary_artist,
            "isrc": s.isrc, "type": "song"
        } for s in songs]

    if "works" in types:
        works = db.query(Work).filter(
            Work.organization_id == org_id,
            or_(
                Work.title.ilike(search_pattern),
                Work.iswc.ilike(search_pattern),
            )
        ).limit(limit).all()
        results["works"] = [{
            "id": w.id, "title": w.title, "iswc": w.iswc, "type": "work"
        } for w in works]

    if "releases" in types:
        releases = db.query(Release).filter(
            Release.organization_id == org_id,
            or_(
                Release.title.ilike(search_pattern),
                Release.primary_artist.ilike(search_pattern),
                Release.upc.ilike(search_pattern),
            )
        ).limit(limit).all()
        results["releases"] = [{
            "id": r.id, "title": r.title, "primary_artist": r.primary_artist,
            "upc": r.upc, "type": "release"
        } for r in releases]

    if "creators" in types:
        creators = db.query(Creator).filter(
            Creator.organization_id == org_id,
            or_(
                Creator.display_name.ilike(search_pattern),
                Creator.legal_name.ilike(search_pattern),
                Creator.email.ilike(search_pattern),
                Creator.primary_ipi.ilike(search_pattern),
            )
        ).limit(limit).all()
        results["creators"] = [{
            "id": c.id, "display_name": c.display_name, "email": c.email,
            "roles": c.roles, "type": "creator"
        } for c in creators]

    return results
