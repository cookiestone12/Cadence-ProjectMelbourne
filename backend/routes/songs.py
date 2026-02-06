from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
from ..models import (
    get_db, Song, SongCredit, SongDSPLink, SongChecklistStatus,
    ChecklistItem, Creator, OrganizationMember, User, SongValuationSnapshot
)
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/songs", tags=["songs"])

class SongResponse(BaseModel):
    id: int
    title: str
    primary_artist: str
    isrc: Optional[str]
    iswc: Optional[str]
    project_title: Optional[str]
    release_date: Optional[str]
    status_health_score: float
    has_contract_sent: bool
    has_contract_executed: bool
    is_registered_with_pro: bool
    is_registered_with_dsp: bool
    is_invoiced: bool
    is_paid: bool
    is_released: bool
    spotify_link: Optional[str] = None
    label: Optional[str]
    publishing_percentage: Optional[float]
    master_percentage: Optional[float]
    advance_amount: Optional[float]
    recording_code: Optional[str]
    master_paid: Optional[str]
    soundexchange_registered: Optional[str]
    payment_status: Optional[str]
    contract_location: Optional[str]
    notes: Optional[str]
    media_url: Optional[str]
    client_name: Optional[str] = None
    client_id: Optional[int] = None
    
    class Config:
        from_attributes = True

class CreditResponse(BaseModel):
    id: int
    creator_id: int
    creator_name: str
    role: str
    share_percentage: Optional[float]
    
    class Config:
        from_attributes = True

class DSPLinkResponse(BaseModel):
    id: int
    platform: str
    url: str
    
    class Config:
        from_attributes = True

class ChecklistStatusResponse(BaseModel):
    id: int
    checklist_item_id: int
    code: str
    category: str
    description: str
    status: str
    weight: int
    
    class Config:
        from_attributes = True

class SongDetailResponse(BaseModel):
    id: int
    title: str
    primary_artist: str
    isrc: Optional[str]
    iswc: Optional[str]
    project_title: Optional[str]
    release_date: Optional[str]
    status_health_score: float
    has_contract_sent: bool
    has_contract_executed: bool
    is_registered_with_pro: bool
    is_registered_with_dsp: bool
    is_invoiced: bool
    is_paid: bool
    is_released: bool
    spotify_link: Optional[str] = None
    label: Optional[str]
    publishing_percentage: Optional[float]
    master_percentage: Optional[float]
    advance_amount: Optional[float]
    recording_code: Optional[str]
    master_paid: Optional[str]
    soundexchange_registered: Optional[str]
    payment_status: Optional[str]
    contract_location: Optional[str]
    notes: Optional[str]
    media_url: Optional[str]
    client_name: Optional[str] = None
    client_id: Optional[int] = None
    credits: List[CreditResponse]
    dsp_links: List[DSPLinkResponse]
    checklist_statuses: List[ChecklistStatusResponse]
    
    class Config:
        from_attributes = True

class SongCreateRequest(BaseModel):
    title: str
    primary_artist: str
    isrc: Optional[str] = None
    iswc: Optional[str] = None
    project_title: Optional[str] = None
    release_date: Optional[date] = None
    label: Optional[str] = None
    publishing_percentage: Optional[float] = None
    master_percentage: Optional[float] = None
    advance_amount: Optional[int] = None
    recording_code: Optional[str] = None
    master_paid: Optional[str] = None
    soundexchange_registered: Optional[str] = None
    payment_status: Optional[str] = None
    contract_location: Optional[str] = None
    notes: Optional[str] = None
    media_url: Optional[str] = None
    has_contract_executed: Optional[bool] = None
    is_registered_with_pro: Optional[bool] = None
    is_registered_with_dsp: Optional[bool] = None

class SongUpdateRequest(BaseModel):
    title: Optional[str] = None
    primary_artist: Optional[str] = None
    isrc: Optional[str] = None
    iswc: Optional[str] = None
    project_title: Optional[str] = None
    release_date: Optional[date] = None
    has_contract_sent: Optional[bool] = None
    has_contract_executed: Optional[bool] = None
    is_registered_with_pro: Optional[bool] = None
    is_registered_with_dsp: Optional[bool] = None
    is_invoiced: Optional[bool] = None
    is_paid: Optional[bool] = None
    is_released: Optional[bool] = None
    spotify_link: Optional[str] = None
    label: Optional[str] = None
    publishing_percentage: Optional[float] = None
    master_percentage: Optional[float] = None
    advance_amount: Optional[int] = None
    soundexchange_registered: Optional[str] = None
    payment_status: Optional[str] = None
    contract_location: Optional[str] = None
    notes: Optional[str] = None
    media_url: Optional[str] = None

@router.get("/org/{org_id}", response_model=List[SongResponse])
def get_organization_songs(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    creator_id: Optional[int] = Query(None),
    role: Optional[str] = Query(None),
    min_health: Optional[float] = Query(None),
    max_health: Optional[float] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this organization")
    
    query = db.query(Song).filter(Song.organization_id == org_id)
    
    if creator_id:
        query = query.join(SongCredit).filter(SongCredit.creator_id == creator_id)
    
    if role:
        if not creator_id:
            query = query.join(SongCredit)
        query = query.filter(SongCredit.role == role)
    
    if min_health is not None:
        query = query.filter(Song.status_health_score >= min_health)
    
    if max_health is not None:
        query = query.filter(Song.status_health_score <= max_health)
    
    if status == "paid":
        query = query.filter(Song.is_paid == True)
    elif status == "invoiced":
        query = query.filter(Song.is_invoiced == True)
    elif status == "registered":
        query = query.filter(Song.is_registered_with_dsp == True)
    elif status == "contract_executed":
        query = query.filter(Song.has_contract_executed == True)
    elif status == "contract_sent":
        query = query.filter(Song.has_contract_sent == True)
    
    songs = query.distinct().offset(offset).limit(limit).all()
    
    result = []
    for song in songs:
        client_name = None
        client_id = None
        credit = db.query(SongCredit).filter(SongCredit.song_id == song.id).order_by(SongCredit.id).first()
        if credit:
            creator = db.query(Creator).filter(Creator.id == credit.creator_id).first()
            if creator:
                client_name = creator.display_name
                client_id = creator.id
        
        result.append({
            "id": song.id,
            "title": song.title,
            "primary_artist": song.primary_artist,
            "isrc": song.isrc,
            "iswc": song.iswc,
            "project_title": song.project_title,
            "release_date": song.release_date.isoformat() if song.release_date else None,
            "status_health_score": song.status_health_score,
            "has_contract_sent": song.has_contract_sent,
            "has_contract_executed": song.has_contract_executed,
            "is_registered_with_pro": song.is_registered_with_pro,
            "is_registered_with_dsp": song.is_registered_with_dsp,
            "is_invoiced": song.is_invoiced,
            "is_paid": song.is_paid,
            "is_released": song.is_released,
            "spotify_link": song.spotify_link,
            "label": song.label,
            "publishing_percentage": song.publishing_percentage,
            "master_percentage": song.master_percentage,
            "advance_amount": song.advance_amount,
            "recording_code": song.recording_code,
            "master_paid": song.master_paid,
            "soundexchange_registered": song.soundexchange_registered,
            "payment_status": song.payment_status,
            "contract_location": song.contract_location,
            "notes": song.notes,
            "media_url": song.media_url,
            "client_name": client_name,
            "client_id": client_id
        })
    return result

@router.get("/{song_id}", response_model=SongDetailResponse)
def get_song(
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
    
    credits = db.query(SongCredit, Creator).join(
        Creator, SongCredit.creator_id == Creator.id
    ).filter(SongCredit.song_id == song.id).order_by(SongCredit.id).all()
    
    dsp_links = db.query(SongDSPLink).filter(SongDSPLink.song_id == song.id).all()
    
    checklist_statuses = db.query(SongChecklistStatus, ChecklistItem).join(
        ChecklistItem, SongChecklistStatus.checklist_item_id == ChecklistItem.id
    ).filter(SongChecklistStatus.song_id == song.id).all()
    
    client_name = None
    client_id = None
    if credits:
        first_credit, first_creator = credits[0]
        client_name = first_creator.display_name
        client_id = first_creator.id
    
    return {
        "id": song.id,
        "title": song.title,
        "primary_artist": song.primary_artist,
        "isrc": song.isrc,
        "iswc": song.iswc,
        "project_title": song.project_title,
        "release_date": song.release_date.isoformat() if song.release_date else None,
        "status_health_score": song.status_health_score,
        "has_contract_sent": song.has_contract_sent,
        "has_contract_executed": song.has_contract_executed,
        "is_registered_with_pro": song.is_registered_with_pro,
        "is_registered_with_dsp": song.is_registered_with_dsp,
        "is_invoiced": song.is_invoiced,
        "is_paid": song.is_paid,
        "is_released": song.is_released,
        "spotify_link": song.spotify_link,
        "label": song.label,
        "publishing_percentage": song.publishing_percentage,
        "master_percentage": song.master_percentage,
        "advance_amount": song.advance_amount,
        "recording_code": song.recording_code,
        "master_paid": song.master_paid,
        "soundexchange_registered": song.soundexchange_registered,
        "payment_status": song.payment_status,
        "contract_location": song.contract_location,
        "notes": song.notes,
        "media_url": song.media_url,
        "client_name": client_name,
        "client_id": client_id,
        "credits": [
            {
                "id": credit.id,
                "creator_id": creator.id,
                "creator_name": creator.display_name,
                "role": credit.role,
                "share_percentage": credit.share_percentage
            }
            for credit, creator in credits
        ],
        "dsp_links": [
            {
                "id": link.id,
                "platform": link.platform,
                "url": link.url
            }
            for link in dsp_links
        ],
        "checklist_statuses": [
            {
                "id": status.id,
                "checklist_item_id": item.id,
                "code": item.code,
                "category": item.category,
                "description": item.description,
                "status": status.status,
                "weight": item.weight
            }
            for status, item in checklist_statuses
        ]
    }

class BulkDeleteRequest(BaseModel):
    song_ids: List[int]

@router.post("/bulk-delete")
def bulk_delete_songs(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not request.song_ids:
        raise HTTPException(status_code=400, detail="No song IDs provided")

    songs = db.query(Song).filter(Song.id.in_(request.song_ids)).all()

    if not songs:
        raise HTTPException(status_code=404, detail="No songs found")

    org_ids = set(s.organization_id for s in songs)
    for org_id in org_ids:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == org_id
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="Not authorized to delete songs from this organization")

    deleted_count = 0
    for song in songs:
        db.delete(song)
        deleted_count += 1

    db.commit()
    return {"deleted": deleted_count}

@router.post("/org/{org_id}", response_model=SongResponse)
def create_song(
    org_id: int,
    request: SongCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this organization")
    
    song = Song(
        organization_id=org_id,
        title=request.title,
        primary_artist=request.primary_artist,
        isrc=request.isrc,
        iswc=request.iswc,
        project_title=request.project_title,
        release_date=request.release_date,
        is_released=(request.release_date is not None),
        label=request.label,
        publishing_percentage=request.publishing_percentage,
        master_percentage=request.master_percentage,
        advance_amount=request.advance_amount,
        recording_code=request.recording_code,
        master_paid=request.master_paid,
        soundexchange_registered=request.soundexchange_registered,
        payment_status=request.payment_status,
        contract_location=request.contract_location,
        notes=request.notes,
        media_url=request.media_url,
        has_contract_executed=request.has_contract_executed or False,
        is_registered_with_pro=request.is_registered_with_pro or False,
        is_registered_with_dsp=request.is_registered_with_dsp or False
    )
    db.add(song)
    db.flush()
    
    checklist_items = db.query(ChecklistItem).all()
    for item in checklist_items:
        status = SongChecklistStatus(
            song_id=song.id,
            checklist_item_id=item.id,
            status="NOT_STARTED"
        )
        db.add(status)
    
    db.commit()
    db.refresh(song)
    
    return {
        "id": song.id,
        "title": song.title,
        "primary_artist": song.primary_artist,
        "isrc": song.isrc,
        "iswc": song.iswc,
        "project_title": song.project_title,
        "release_date": song.release_date.isoformat() if song.release_date else None,
        "status_health_score": song.status_health_score,
        "has_contract_sent": song.has_contract_sent,
        "has_contract_executed": song.has_contract_executed,
        "is_registered_with_pro": song.is_registered_with_pro,
        "is_registered_with_dsp": song.is_registered_with_dsp,
        "is_invoiced": song.is_invoiced,
        "is_paid": song.is_paid,
        "is_released": song.is_released,
        "label": song.label,
        "publishing_percentage": song.publishing_percentage,
        "master_percentage": song.master_percentage,
        "advance_amount": song.advance_amount,
        "recording_code": song.recording_code,
        "master_paid": song.master_paid,
        "soundexchange_registered": song.soundexchange_registered,
        "payment_status": song.payment_status,
        "contract_location": song.contract_location,
        "notes": song.notes,
        "media_url": song.media_url
    }

@router.patch("/{song_id}", response_model=SongResponse)
def update_song(
    song_id: int,
    request: SongUpdateRequest,
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
    
    update_data = request.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(song, key, value)
    
    # Auto-update is_released if release_date changes
    if 'release_date' in update_data:
        song.is_released = (song.release_date is not None)
    
    db.commit()
    db.refresh(song)
    
    return {
        "id": song.id,
        "title": song.title,
        "primary_artist": song.primary_artist,
        "isrc": song.isrc,
        "iswc": song.iswc,
        "project_title": song.project_title,
        "release_date": song.release_date.isoformat() if song.release_date else None,
        "status_health_score": song.status_health_score,
        "has_contract_sent": song.has_contract_sent,
        "has_contract_executed": song.has_contract_executed,
        "is_registered_with_pro": song.is_registered_with_pro,
        "is_registered_with_dsp": song.is_registered_with_dsp,
        "is_invoiced": song.is_invoiced,
        "is_paid": song.is_paid,
        "is_released": song.is_released,
        "label": song.label,
        "publishing_percentage": song.publishing_percentage,
        "master_percentage": song.master_percentage,
        "advance_amount": song.advance_amount,
        "recording_code": song.recording_code,
        "master_paid": song.master_paid,
        "soundexchange_registered": song.soundexchange_registered,
        "payment_status": song.payment_status,
        "contract_location": song.contract_location,
        "notes": song.notes,
        "media_url": song.media_url
    }
