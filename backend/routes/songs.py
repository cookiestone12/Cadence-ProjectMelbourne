from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
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
    is_registered_with_dsp: Optional[str] = None
    is_invoiced: Optional[str] = None
    is_paid: Optional[str] = None
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
    audio_file_url: Optional[str] = None
    lyrics: Optional[str] = None
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
    is_registered_with_dsp: Optional[str] = None
    is_invoiced: Optional[str] = None
    is_paid: Optional[str] = None
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
    is_registered_with_dsp: Optional[str] = None
    is_invoiced: Optional[str] = None
    is_paid: Optional[str] = None

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
    is_registered_with_dsp: Optional[str] = None
    is_invoiced: Optional[str] = None
    is_paid: Optional[str] = None
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
    audio_file_url: Optional[str] = None
    lyrics: Optional[str] = None

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
        query = query.filter(Song.is_paid == "Yes")
    elif status == "invoiced":
        query = query.filter(Song.is_invoiced == "Yes")
    elif status == "registered":
        query = query.filter(Song.is_registered_with_dsp == "Yes")
    elif status == "contract_executed":
        query = query.filter(Song.has_contract_executed == True)
    elif status == "contract_sent":
        query = query.filter(Song.has_contract_sent == True)
    
    songs = query.distinct().offset(offset).limit(limit).all()
    
    # Batch-load client info to avoid N+1 queries
    song_ids = [song.id for song in songs]
    song_client_map = {}
    
    if song_ids:
        # Step 1: Get the first SongCredit per song using a subquery
        # Using min(SongCredit.id) to get the first credit
        subquery = db.query(
            func.min(SongCredit.id).label("min_id")
        ).filter(
            SongCredit.song_id.in_(song_ids)
        ).group_by(SongCredit.song_id).subquery()
        
        first_credits = db.query(SongCredit).filter(
            SongCredit.id.in_(db.query(subquery.c.min_id))
        ).all()
        
        # Step 2: Collect all creator IDs from first credits
        creator_ids = [credit.creator_id for credit in first_credits]
        
        # Step 3: Fetch all relevant creators in one query
        creators_map = {}
        if creator_ids:
            creators = db.query(Creator).filter(Creator.id.in_(creator_ids)).all()
            creators_map = {creator.id: creator for creator in creators}
        
        # Step 4: Build lookup dictionary: song_id -> (client_name, client_id)
        for credit in first_credits:
            creator = creators_map.get(credit.creator_id)
            if creator:
                song_client_map[credit.song_id] = (creator.display_name, creator.id)
    
    result = []
    for song in songs:
        client_name = None
        client_id = None
        if song.id in song_client_map:
            client_name, client_id = song_client_map[song.id]
        
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
        if not membership and not current_user.is_super_admin:
            raise HTTPException(status_code=403, detail="Not authorized to delete songs from this organization")

    from ..models import Placement, RoyaltyTransaction, ContractAsset
    db.query(Placement).filter(Placement.song_id.in_(request.song_ids)).update(
        {Placement.song_id: None}, synchronize_session=False
    )
    db.query(RoyaltyTransaction).filter(RoyaltyTransaction.song_id.in_(request.song_ids)).update(
        {RoyaltyTransaction.song_id: None}, synchronize_session=False
    )
    db.query(ContractAsset).filter(ContractAsset.song_id.in_(request.song_ids)).update(
        {ContractAsset.song_id: None}, synchronize_session=False
    )

    deleted_count = 0
    for song in songs:
        from ..services.audit_service import log_action
        log_action(db, song.organization_id, current_user.id, "DELETE", "SONG", song.id, song.title)
        db.delete(song)
        deleted_count += 1

    db.commit()
    return {"deleted": deleted_count}

@router.delete("/{song_id}")
def delete_song(
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
    if not membership and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized to delete this song")

    from ..models import Placement, RoyaltyTransaction, ContractAsset
    db.query(Placement).filter(Placement.song_id == song_id).update(
        {Placement.song_id: None}, synchronize_session=False
    )
    db.query(RoyaltyTransaction).filter(RoyaltyTransaction.song_id == song_id).update(
        {RoyaltyTransaction.song_id: None}, synchronize_session=False
    )
    db.query(ContractAsset).filter(ContractAsset.song_id == song_id).update(
        {ContractAsset.song_id: None}, synchronize_session=False
    )

    from ..services.audit_service import log_action
    log_action(db, song.organization_id, current_user.id, "DELETE", "SONG", song.id, song.title)
    db.delete(song)
    db.commit()
    return {"message": "Song deleted successfully"}

@router.get("/org/{org_id}/duplicates")
def find_duplicates(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from difflib import SequenceMatcher
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    songs = db.query(Song).filter(Song.organization_id == org_id).order_by(Song.title).all()
    
    duplicate_groups = []
    processed = set()
    
    for i, song_a in enumerate(songs):
        if song_a.id in processed:
            continue
        group = []
        title_a = (song_a.title or "").lower().strip()
        artist_a = (song_a.primary_artist or "").lower().strip()
        
        for j in range(i + 1, len(songs)):
            song_b = songs[j]
            if song_b.id in processed:
                continue
            title_b = (song_b.title or "").lower().strip()
            artist_b = (song_b.primary_artist or "").lower().strip()
            
            title_sim = SequenceMatcher(None, title_a, title_b).ratio()
            artist_sim = SequenceMatcher(None, artist_a, artist_b).ratio()
            combined = (title_sim * 0.7) + (artist_sim * 0.3)
            
            if combined >= 0.75 and title_sim >= 0.6:
                if not group:
                    group.append({
                        "id": song_a.id,
                        "title": song_a.title,
                        "primary_artist": song_a.primary_artist,
                        "isrc": song_a.isrc,
                        "is_released": song_a.is_released,
                        "release_date": str(song_a.release_date) if song_a.release_date else None,
                        "status_health_score": song_a.status_health_score,
                        "has_contract_executed": song_a.has_contract_executed,
                        "is_registered_with_pro": song_a.is_registered_with_pro,
                    })
                group.append({
                    "id": song_b.id,
                    "title": song_b.title,
                    "primary_artist": song_b.primary_artist,
                    "isrc": song_b.isrc,
                    "is_released": song_b.is_released,
                    "release_date": str(song_b.release_date) if song_b.release_date else None,
                    "status_health_score": song_b.status_health_score,
                    "has_contract_executed": song_b.has_contract_executed,
                    "is_registered_with_pro": song_b.is_registered_with_pro,
                    "similarity": round(combined, 2),
                })
                processed.add(song_b.id)
        
        if group:
            processed.add(song_a.id)
            duplicate_groups.append(group)
    
    return {"groups": duplicate_groups, "total_groups": len(duplicate_groups)}

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
        is_registered_with_dsp=request.is_registered_with_dsp or "No",
        is_invoiced=request.is_invoiced or "No",
        is_paid=request.is_paid or "No"
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
    
    from ..services.audit_service import log_action
    log_action(db, org_id, current_user.id, "CREATE", "SONG", song.id, song.title)
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
