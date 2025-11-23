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
    
    return [
        {
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
            "is_paid": song.is_paid
        }
        for song in songs
    ]

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
    ).filter(SongCredit.song_id == song.id).all()
    
    dsp_links = db.query(SongDSPLink).filter(SongDSPLink.song_id == song.id).all()
    
    checklist_statuses = db.query(SongChecklistStatus, ChecklistItem).join(
        ChecklistItem, SongChecklistStatus.checklist_item_id == ChecklistItem.id
    ).filter(SongChecklistStatus.song_id == song.id).all()
    
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
        release_date=request.release_date
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
        "is_paid": song.is_paid
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
        "is_paid": song.is_paid
    }
