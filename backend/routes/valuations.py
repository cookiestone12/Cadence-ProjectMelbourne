from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from ..models import get_db, SongValuationSnapshot, Song, OrganizationMember, User
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/songs", tags=["valuations"])

class ValuationResponse(BaseModel):
    id: int
    song_id: int
    valuation_cents: Optional[int]
    source: str
    snapshot_date: str
    notes: Optional[str]
    
    class Config:
        from_attributes = True

class ValuationCreateRequest(BaseModel):
    valuation_cents: int
    source: str = "MANUAL"
    notes: Optional[str] = None

@router.get("/{song_id}/valuation", response_model=Optional[ValuationResponse])
def get_song_valuation(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the latest valuation snapshot for a song.
    TODO: This will later integrate with Luminate/Ampersound for automated valuations.
    """
    
    song = db.query(Song).filter(Song.id == song_id).first()
    
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == song.organization_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this song")
    
    valuation = db.query(SongValuationSnapshot).filter(
        SongValuationSnapshot.song_id == song_id
    ).order_by(SongValuationSnapshot.snapshot_date.desc()).first()
    
    if not valuation:
        return None
    
    return {
        "id": valuation.id,
        "song_id": valuation.song_id,
        "valuation_cents": valuation.valuation_cents,
        "source": valuation.source,
        "snapshot_date": valuation.snapshot_date.isoformat() if valuation.snapshot_date else "",
        "notes": valuation.notes
    }

@router.post("/{song_id}/valuation", response_model=ValuationResponse)
def create_song_valuation(
    song_id: int,
    request: ValuationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually create a valuation snapshot for a song.
    TODO: This endpoint will later trigger automated valuation via Luminate/Ampersound API.
    For now, it only accepts manual valuations from admin users.
    """
    
    song = db.query(Song).filter(Song.id == song_id).first()
    
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == song.organization_id
    ).first()
    
    if not membership or membership.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(
            status_code=403,
            detail="Only organization owners and admins can create valuations"
        )
    
    valuation = SongValuationSnapshot(
        song_id=song_id,
        valuation_cents=request.valuation_cents,
        source=request.source,
        notes=request.notes
    )
    db.add(valuation)
    db.commit()
    db.refresh(valuation)
    
    return {
        "id": valuation.id,
        "song_id": valuation.song_id,
        "valuation_cents": valuation.valuation_cents,
        "source": valuation.source,
        "snapshot_date": valuation.snapshot_date.isoformat() if valuation.snapshot_date else "",
        "notes": valuation.notes
    }

@router.get("/{song_id}/valuations", response_model=List[ValuationResponse])
def get_song_valuation_history(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all valuation snapshots for a song"""
    
    song = db.query(Song).filter(Song.id == song_id).first()
    
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == song.organization_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this song")
    
    valuations = db.query(SongValuationSnapshot).filter(
        SongValuationSnapshot.song_id == song_id
    ).order_by(SongValuationSnapshot.snapshot_date.desc()).all()
    
    return [
        {
            "id": v.id,
            "song_id": v.song_id,
            "valuation_cents": v.valuation_cents,
            "source": v.source,
            "snapshot_date": v.snapshot_date.isoformat() if v.snapshot_date else "",
            "notes": v.notes
        }
        for v in valuations
    ]
