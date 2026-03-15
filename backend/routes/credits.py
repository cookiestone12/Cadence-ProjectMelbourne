from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import threading
import logging
from ..models import get_db, SongCredit, SongDSPLink, Song, OrganizationMember, User, ClientShare
from ..utils.auth import get_current_user
from .client_sharing import has_shared_access

logger = logging.getLogger("cadence")


def _refresh_creator_credits_async(creator_id: int, org_id: int):
    from ..models.database import SessionLocal
    from ..services.credits_service import compute_creator_credits
    try:
        db = SessionLocal()
        compute_creator_credits(creator_id, org_id, db)
        db.close()
    except Exception as e:
        logger.warning(f"Background credits refresh failed for creator {creator_id}: {e}")

router = APIRouter(prefix="/api/songs", tags=["credits"])

class CreditCreateRequest(BaseModel):
    creator_id: int
    role: str
    share_percentage: Optional[float] = None
    pub_share: Optional[float] = None
    master_share: Optional[float] = None

class CreditUpdateRequest(BaseModel):
    role: Optional[str] = None
    share_percentage: Optional[float] = None
    pub_share: Optional[float] = None
    master_share: Optional[float] = None

class DSPLinkCreateRequest(BaseModel):
    platform: str
    url: str

class CreditResponse(BaseModel):
    id: int
    song_id: int
    creator_id: int
    role: str
    share_percentage: Optional[float]
    
    class Config:
        from_attributes = True

class DSPLinkResponse(BaseModel):
    id: int
    song_id: int
    platform: str
    url: str
    
    class Config:
        from_attributes = True

@router.post("/{song_id}/credits", response_model=CreditResponse)
def create_credit(
    song_id: int,
    request: CreditCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import Creator
    
    from ..models import ClientShare
    
    song = db.query(Song).filter(Song.id == song_id).first()
    
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == song.organization_id
    ).first()
    
    if not membership:
        user_membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id
        ).first()
        has_share = False
        if user_membership:
            has_share = db.query(ClientShare).filter(
                ClientShare.recipient_org_id == user_membership.organization_id,
                ClientShare.primary_org_id == song.organization_id,
                ClientShare.status == "ACCEPTED"
            ).first() is not None
        if not has_share:
            raise HTTPException(status_code=403, detail="Not authorized to modify this song")
    
    creator = db.query(Creator).filter(Creator.id == request.creator_id).first()
    
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    if creator.organization_id != song.organization_id:
        raise HTTPException(
            status_code=403,
            detail="Cannot add credits from creators outside this organization"
        )
    
    credit = SongCredit(
        song_id=song_id,
        creator_id=request.creator_id,
        role=request.role,
        share_percentage=request.share_percentage,
        pub_share=request.pub_share,
        master_share=request.master_share
    )
    db.add(credit)
    db.commit()
    db.refresh(credit)
    
    threading.Thread(
        target=_refresh_creator_credits_async,
        args=(request.creator_id, song.organization_id),
        daemon=True,
    ).start()
    
    return credit

@router.patch("/{song_id}/credits/{credit_id}")
def update_credit(
    song_id: int,
    credit_id: int,
    request: CreditUpdateRequest,
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
        credit_check = db.query(SongCredit).filter(
            SongCredit.id == credit_id,
            SongCredit.song_id == song_id
        ).first()
        if not credit_check or not has_shared_access(db, current_user.id, credit_check.creator_id):
            raise HTTPException(status_code=403, detail="Not authorized to modify this song")
    
    credit = db.query(SongCredit).filter(
        SongCredit.id == credit_id,
        SongCredit.song_id == song_id
    ).first()
    
    if not credit:
        raise HTTPException(status_code=404, detail="Credit not found")
    
    update_data = request.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(credit, key, value)
    
    db.commit()
    db.refresh(credit)
    
    threading.Thread(
        target=_refresh_creator_credits_async,
        args=(credit.creator_id, song.organization_id),
        daemon=True,
    ).start()
    
    return {
        "id": credit.id,
        "song_id": credit.song_id,
        "creator_id": credit.creator_id,
        "role": credit.role,
        "share_percentage": credit.share_percentage,
        "pub_share": credit.pub_share,
        "master_share": credit.master_share
    }

@router.delete("/{song_id}/credits/{credit_id}")
def delete_credit(
    song_id: int,
    credit_id: int,
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
        credit_check = db.query(SongCredit).filter(
            SongCredit.id == credit_id,
            SongCredit.song_id == song_id
        ).first()
        if not credit_check or not has_shared_access(db, current_user.id, credit_check.creator_id):
            raise HTTPException(status_code=403, detail="Not authorized to modify this song")
    
    credit = db.query(SongCredit).filter(
        SongCredit.id == credit_id,
        SongCredit.song_id == song_id
    ).first()
    
    if not credit:
        raise HTTPException(status_code=404, detail="Credit not found")
    
    creator_id = credit.creator_id
    db.delete(credit)
    db.commit()
    
    threading.Thread(
        target=_refresh_creator_credits_async,
        args=(creator_id, song.organization_id),
        daemon=True,
    ).start()
    
    return {"message": "Credit deleted"}

@router.post("/{song_id}/dsp-links", response_model=DSPLinkResponse)
def create_dsp_link(
    song_id: int,
    request: DSPLinkCreateRequest,
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
    
    dsp_link = SongDSPLink(
        song_id=song_id,
        platform=request.platform,
        url=request.url
    )
    db.add(dsp_link)
    db.commit()
    db.refresh(dsp_link)
    
    return dsp_link

@router.delete("/{song_id}/dsp-links/{link_id}")
def delete_dsp_link(
    song_id: int,
    link_id: int,
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
    
    dsp_link = db.query(SongDSPLink).filter(
        SongDSPLink.id == link_id,
        SongDSPLink.song_id == song_id
    ).first()
    
    if not dsp_link:
        raise HTTPException(status_code=404, detail="DSP link not found")
    
    db.delete(dsp_link)
    db.commit()
    
    return {"message": "DSP link deleted"}
