from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
import threading
import logging
from ..models import get_db, SongCredit, SongDSPLink, Song, OrganizationMember, User, ClientShare
from ..utils.auth import get_current_user
from .client_sharing import has_shared_access
from .contracts_mgmt import sync_credit_to_splits

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

router = APIRouter(prefix="/api/songs", tags=["Credits"])

class CreditCreateRequest(BaseModel):
    creator_id: Optional[int] = None
    new_creator_name: Optional[str] = None
    role: str
    share_percentage: Optional[float] = None
    pub_share: Optional[float] = None
    master_share: Optional[float] = None
    edit_notes: Optional[str] = None

class CreditUpdateRequest(BaseModel):
    role: Optional[str] = None
    share_percentage: Optional[float] = None
    pub_share: Optional[float] = None
    master_share: Optional[float] = None
    edit_notes: Optional[str] = None

class DSPLinkCreateRequest(BaseModel):
    platform: str
    url: str

class CreditResponse(BaseModel):
    id: int
    song_id: int
    creator_id: int
    role: str
    share_percentage: Optional[float]
    pub_share: Optional[float] = None
    master_share: Optional[float] = None
    
    class Config:
        from_attributes = True

class DSPLinkResponse(BaseModel):
    id: int
    song_id: int
    platform: str
    url: str
    
    class Config:
        from_attributes = True

@router.post("/{song_id}/credits", response_model=CreditResponse, summary="Add a credit to a song", description="Adds a creator credit (writer / producer / featured / etc.) with a publishing % and master % share.")
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
    
    creator = None
    if request.creator_id:
        creator = db.query(Creator).filter(Creator.id == request.creator_id).first()
        if not creator:
            raise HTTPException(status_code=404, detail="Creator not found")
        if creator.organization_id != song.organization_id:
            raise HTTPException(
                status_code=403,
                detail="Cannot add credits from creators outside this organization"
            )
    elif request.new_creator_name and request.new_creator_name.strip():
        cleaned_name = request.new_creator_name.strip()
        creator = Creator(
            organization_id=song.organization_id,
            display_name=cleaned_name,
            primary_artist=cleaned_name,
        )
        db.add(creator)
        db.flush()
        logger.info(f"Auto-created creator '{creator.display_name}' (id={creator.id}) for org {song.organization_id}")
    else:
        raise HTTPException(status_code=400, detail="Provide creator_id or a non-empty new_creator_name")

    credit = SongCredit(
        song_id=song_id,
        creator_id=creator.id,
        role=request.role,
        share_percentage=request.share_percentage,
        pub_share=request.pub_share,
        master_share=request.master_share
    )
    db.add(credit)
    db.flush()

    if request.pub_share is not None or request.master_share is not None:
        sync_credit_to_splits(db, song, creator.id, request.pub_share, request.master_share, request.role, current_user.id)

    from ..utils.edit_history import record_contributor_add
    record_contributor_add(db, song_id, song.organization_id, current_user.id, creator.display_name, request.role, notes=request.edit_notes)

    db.commit()
    db.refresh(credit)
    
    threading.Thread(
        target=_refresh_creator_credits_async,
        args=(creator.id, song.organization_id),
        daemon=True,
    ).start()
    
    return credit

@router.patch("/{song_id}/credits/{credit_id}", summary="Update a song credit", description="Patches a credit's role, publishing %, master %, or notes.")
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
        if not credit_check or not has_shared_access(db, current_user.id, credit_check.creator_id, required_module="catalog"):
            raise HTTPException(status_code=403, detail="Not authorized to modify this song")
    
    credit = db.query(SongCredit).filter(
        SongCredit.id == credit_id,
        SongCredit.song_id == song_id
    ).first()
    
    if not credit:
        raise HTTPException(status_code=404, detail="Credit not found")
    
    update_data = request.dict(exclude_unset=True)
    edit_notes = update_data.pop("edit_notes", None)

    from ..models import Creator as CreatorModel
    credit_creator = db.query(CreatorModel).filter(CreatorModel.id == credit.creator_id).first()
    creator_name = credit_creator.display_name if credit_creator else str(credit.creator_id)

    from ..utils.edit_history import record_contributor_edit, record_split_change
    for key, value in update_data.items():
        old_val = getattr(credit, key, None)
        if old_val == value:
            continue
        if key in ("pub_share", "master_share", "share_percentage"):
            rtype = {"pub_share": "PUBLISHING", "master_share": "MASTER", "share_percentage": "SHARE"}.get(key, key)
            record_split_change(db, song_id, song.organization_id, current_user.id, creator_name, rtype, old_val, value, notes=edit_notes)
        elif key == "role":
            record_contributor_edit(db, song_id, song.organization_id, current_user.id, creator_name, "role", old_val, value, notes=edit_notes)
        setattr(credit, key, value)

    if "pub_share" in update_data or "master_share" in update_data:
        sync_credit_to_splits(db, song, credit.creator_id, credit.pub_share, credit.master_share, credit.role, current_user.id)

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

@router.delete("/{song_id}/credits/{credit_id}", summary="Delete a song credit", description="Removes a credit from the song. Splits totals are recomputed.")
def delete_credit(
    song_id: int,
    credit_id: int,
    notes: str = None,
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
        if not credit_check or not has_shared_access(db, current_user.id, credit_check.creator_id, required_module="catalog"):
            raise HTTPException(status_code=403, detail="Not authorized to modify this song")
    
    credit = db.query(SongCredit).filter(
        SongCredit.id == credit_id,
        SongCredit.song_id == song_id
    ).first()
    
    if not credit:
        raise HTTPException(status_code=404, detail="Credit not found")
    
    creator_id = credit.creator_id
    had_splits = credit.pub_share is not None or credit.master_share is not None
    was_unmatched = credit.needs_review

    from ..models import Creator as CreatorModel
    credit_creator = db.query(CreatorModel).filter(CreatorModel.id == credit.creator_id).first()
    creator_name = credit_creator.display_name if credit_creator else str(credit.creator_id)
    from ..utils.edit_history import record_contributor_remove
    record_contributor_remove(db, song_id, song.organization_id, current_user.id, creator_name, credit.role, notes=notes)

    db.delete(credit)
    db.flush()

    if had_splits:
        from .contracts_mgmt import _sync_song_pub_percentage
        _sync_song_pub_percentage(db, song_id)

    if was_unmatched:
        from ..models import ActionItem
        remaining_unmatched = db.query(SongCredit).filter(
            SongCredit.song_id == song_id,
            SongCredit.needs_review == True,
        ).count()
        if remaining_unmatched == 0:
            unmatched_actions = db.query(ActionItem).filter(
                ActionItem.song_id == song_id,
                ActionItem.action_type == "UNMATCHED_CREDIT",
                ActionItem.status != "COMPLETED",
            ).all()
            for action in unmatched_actions:
                action.status = "COMPLETED"

    db.commit()
    
    threading.Thread(
        target=_refresh_creator_credits_async,
        args=(creator_id, song.organization_id),
        daemon=True,
    ).start()
    
    return {"message": "Credit deleted"}


class ResolveCreditRequest(BaseModel):
    creator_id: Optional[int] = None
    new_creator_name: Optional[str] = None

@router.post("/{song_id}/credits/{credit_id}/resolve")
def resolve_credit(
    song_id: int,
    credit_id: int,
    request: ResolveCreditRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import Creator, ActionItem

    song = db.query(Song).filter(Song.id == song_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found")

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == song.organization_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")

    credit = db.query(SongCredit).filter(
        SongCredit.id == credit_id,
        SongCredit.song_id == song_id
    ).first()
    if not credit:
        raise HTTPException(status_code=404, detail="Credit not found")

    if not credit.needs_review:
        raise HTTPException(status_code=400, detail="Credit is not flagged for review")

    if request.creator_id:
        creator = db.query(Creator).filter(Creator.id == request.creator_id).first()
        if not creator or creator.organization_id != song.organization_id:
            raise HTTPException(status_code=404, detail="Creator not found in this organization")
        credit.creator_id = creator.id
    elif request.new_creator_name:
        new_creator = Creator(
            organization_id=song.organization_id,
            display_name=request.new_creator_name,
            roles=["ARTIST"],
            contributor_type="ARTIST",
        )
        db.add(new_creator)
        db.flush()
        credit.creator_id = new_creator.id
    else:
        raise HTTPException(status_code=400, detail="Provide creator_id or new_creator_name")

    credit.needs_review = False
    credit.unmatched_artist_name = None

    remaining_unmatched = db.query(SongCredit).filter(
        SongCredit.song_id == song_id,
        SongCredit.needs_review == True,
        SongCredit.id != credit_id,
    ).count()

    if remaining_unmatched == 0:
        unmatched_actions = db.query(ActionItem).filter(
            ActionItem.song_id == song_id,
            ActionItem.action_type == "UNMATCHED_CREDIT",
            ActionItem.status != "COMPLETED",
        ).all()
        for action in unmatched_actions:
            action.status = "COMPLETED"

    db.commit()

    threading.Thread(
        target=_refresh_creator_credits_async,
        args=(credit.creator_id, song.organization_id),
        daemon=True,
    ).start()

    return {
        "id": credit.id,
        "creator_id": credit.creator_id,
        "needs_review": credit.needs_review,
        "message": "Credit resolved successfully"
    }


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

    from ..utils.health_sync import sync_song_to_checklist
    sync_song_to_checklist(db, song)

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
    db.flush()

    from ..utils.health_sync import sync_song_to_checklist
    sync_song_to_checklist(db, song)

    db.commit()
    
    return {"message": "DSP link deleted"}
