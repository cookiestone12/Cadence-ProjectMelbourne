from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List
from ..models import (
    get_db, SongChecklistStatus, ChecklistItem, Song,
    OrganizationMember, User
)
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/songs", tags=["Checklist"])

class ChecklistItemResponse(BaseModel):
    id: int
    code: str
    category: str
    description: str
    weight: int
    
    class Config:
        from_attributes = True

class ChecklistStatusUpdateRequest(BaseModel):
    checklist_item_id: int
    status: str

class ChecklistBatchUpdateRequest(BaseModel):
    updates: List[ChecklistStatusUpdateRequest]

@router.get(
    "/checklist-items",
    response_model=List[ChecklistItemResponse],
    summary='List the global catalog of song-checklist items',
    description='Returns every checklist item type the platform defines (with labels, descriptions, due-by rules) — used to render the checklist editor and to validate `PATCH /{song_id}/checklist`.\n\n**Auth:** Bearer JWT.\n**Response:** `List[ChecklistItemResponse]`.',
)
def get_checklist_items(db: Session = Depends(get_db)):
    items = db.query(ChecklistItem).all()
    return items

@router.get(
    "/{song_id}/checklist",
    summary="Get a song's release-readiness checklist",
    description="Returns the ordered set of checklist items the user must tick off for a song before it's ready (lyrics, splits, ISRC, audio, registration, etc.) plus their state.\n\n**Path parameter:** `song_id`.\n**Auth:** Bearer JWT — caller must be a member of the song's org.\n**Response:** `{ items: [{key, label, complete, due_at, completed_at, completed_by}], pct_complete }`.",
)
def get_song_checklist(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    song = db.query(Song).filter(Song.id == song_id).first()
    
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == song.organization_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this song")
    
    checklist_statuses = db.query(SongChecklistStatus, ChecklistItem).join(
        ChecklistItem, SongChecklistStatus.checklist_item_id == ChecklistItem.id
    ).filter(SongChecklistStatus.song_id == song_id).all()
    
    return {
        "song_id": song_id,
        "health_score": song.status_health_score,
        "statuses": [
            {
                "id": status.id,
                "checklist_item_id": item.id,
                "code": item.code,
                "category": item.category,
                "description": item.description,
                "weight": item.weight,
                "status": status.status
            }
            for status, item in checklist_statuses
        ]
    }

@router.patch(
    "/{song_id}/checklist",
    summary="Update a song's checklist items",
    description="Bulk-updates the supplied checklist items' completion state.\n\n**Path parameter:** `song_id`.\n**Body:** `{ items: [{key, complete: bool}] }`.\n**Auth:** Bearer JWT — caller must be a member of the song's org.\n**Response:** the updated checklist (same shape as GET).",
)
def update_song_checklist(
    song_id: int,
    request: ChecklistBatchUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    song = db.query(Song).filter(Song.id == song_id).first()
    
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == song.organization_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to modify this song")
    
    for update in request.updates:
        status = db.query(SongChecklistStatus).filter(
            SongChecklistStatus.song_id == song_id,
            SongChecklistStatus.checklist_item_id == update.checklist_item_id
        ).first()
        
        if status:
            status.status = update.status
        else:
            new_status = SongChecklistStatus(
                song_id=song_id,
                checklist_item_id=update.checklist_item_id,
                status=update.status
            )
            db.add(new_status)
    
    all_items = db.query(ChecklistItem).all()
    total_weight = sum(item.weight for item in all_items) or 1
    
    acknowledged_weight = db.query(func.sum(ChecklistItem.weight)).join(
        SongChecklistStatus,
        ChecklistItem.id == SongChecklistStatus.checklist_item_id
    ).filter(
        SongChecklistStatus.song_id == song_id,
        SongChecklistStatus.status.in_(["COMPLETED", "NOT_APPLICABLE"])
    ).scalar() or 0
    
    health_score = (acknowledged_weight / total_weight) * 100
    song.status_health_score = round(min(health_score, 100.0), 2)
    
    db.commit()
    
    return {
        "message": "Checklist updated",
        "health_score": song.status_health_score
    }
