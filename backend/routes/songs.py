import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from pydantic import BaseModel, validator
from typing import Any, List, Optional
from datetime import date
from ..models import (
    get_db, Song, SongCredit, SongDSPLink, SongChecklistStatus,
    ChecklistItem, Creator, OrganizationMember, User, SongValuationSnapshot,
    Placement, ContractAsset, AudioAsset, RoyaltyTransaction, RightsSplit,
)
from ..utils.auth import get_current_user
from .client_sharing import has_shared_access


def _cleanup_song_dependencies(db: Session, song_ids: list):
    from sqlalchemy import text

    id_list = list(song_ids)
    if not id_list:
        return

    db.execute(text("UPDATE placements SET song_id = NULL WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("UPDATE royalty_transactions SET song_id = NULL WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("UPDATE audio_assets SET song_id = NULL WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("UPDATE action_items SET song_id = NULL WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("UPDATE songs SET parent_song_id = NULL WHERE parent_song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("UPDATE contract_documents SET song_id = NULL WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("UPDATE expenses SET song_id = NULL WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("UPDATE fees SET song_id = NULL WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("UPDATE royalty_ledger_entries SET song_id = NULL WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("UPDATE royalty_statement_lines SET matched_song_id = NULL WHERE matched_song_id = ANY(:ids)"), {"ids": id_list})

    db.execute(text("DELETE FROM song_credits WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("DELETE FROM song_dsp_links WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("DELETE FROM song_checklist_status WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("DELETE FROM song_valuation_snapshots WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("DELETE FROM analytics WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("DELETE FROM song_streaming_metrics WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("DELETE FROM territory_revenue WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("DELETE FROM valuation_calculations WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("DELETE FROM song_contracts WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("DELETE FROM work_tracks WHERE song_id = ANY(:ids)"), {"ids": id_list})
    db.execute(text("DELETE FROM release_tracks WHERE song_id = ANY(:ids)"), {"ids": id_list})

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
    release_status: Optional[str] = "unreleased"
    entry_type: Optional[str] = "Song"
    parent_song_id: Optional[int] = None
    parent_song_title: Optional[str] = None
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
    credit_role: Optional[str] = None
    credit_id: Optional[int] = None
    client_name: Optional[str] = None
    client_id: Optional[int] = None
    
    class Config:
        from_attributes = True


def _song_to_response(song) -> dict:
    parent_title = None
    if song.parent_song_id and song.parent_song:
        parent_title = song.parent_song.title
    return {
        "id": song.id,
        "title": song.title,
        "primary_artist": song.primary_artist,
        "isrc": song.isrc,
        "iswc": song.iswc,
        "project_title": song.project_title,
        "release_date": song.release_date.isoformat() if song.release_date else None,
        "status_health_score": song.status_health_score or 0.0,
        "has_contract_sent": song.has_contract_sent or False,
        "has_contract_executed": song.has_contract_executed or False,
        "is_registered_with_pro": song.is_registered_with_pro or False,
        "is_registered_with_dsp": song.is_registered_with_dsp,
        "is_invoiced": song.is_invoiced,
        "is_paid": song.is_paid,
        "is_released": song.is_released or False,
        "release_status": getattr(song, 'release_status', None) or "unreleased",
        "entry_type": getattr(song, 'entry_type', None) or "Song",
        "parent_song_id": song.parent_song_id,
        "parent_song_title": parent_title,
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
        "audio_file_url": song.audio_file_url,
        "lyrics": song.lyrics,
        "credit_role": None,
        "credit_id": None,
        "client_name": None,
        "client_id": None,
    }


class CreditResponse(BaseModel):
    id: int
    creator_id: Optional[int] = None
    creator_name: Optional[str] = None
    role: str
    share_percentage: Optional[float]
    pub_share: Optional[float] = None
    master_share: Optional[float] = None
    needs_review: bool = False
    unmatched_artist_name: Optional[str] = None
    
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
    release_status: Optional[str] = "unreleased"
    entry_type: Optional[str] = "Song"
    parent_song_id: Optional[int] = None
    parent_song_title: Optional[str] = None
    spotify_link: Optional[str] = None
    label: Optional[str]
    publishing_percentage: Optional[float]
    master_percentage: Optional[float]
    advance_amount: Optional[float]
    recording_code: Optional[str]
    master_paid: Optional[str]
    soundexchange_registered: Optional[str]
    mlc_registered: Optional[str] = None
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
    entry_type: Optional[str] = "Song"
    label: Optional[str] = None
    publishing_percentage: Optional[float] = None
    master_percentage: Optional[float] = None
    advance_amount: Optional[int] = None
    recording_code: Optional[str] = None
    master_paid: Optional[str] = None
    soundexchange_registered: Optional[str] = None
    mlc_registered: Optional[str] = None
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
    entry_type: Optional[str] = None
    has_contract_sent: Optional[Any] = None
    has_contract_executed: Optional[Any] = None
    is_registered_with_pro: Optional[Any] = None
    is_registered_with_dsp: Optional[Any] = None
    is_invoiced: Optional[Any] = None
    is_paid: Optional[Any] = None
    is_released: Optional[bool] = None
    spotify_link: Optional[str] = None
    label: Optional[str] = None
    publishing_percentage: Optional[float] = None
    master_percentage: Optional[float] = None
    advance_amount: Optional[Any] = None
    soundexchange_registered: Optional[Any] = None
    mlc_registered: Optional[Any] = None
    payment_status: Optional[str] = None
    contract_location: Optional[str] = None
    notes: Optional[str] = None
    media_url: Optional[str] = None
    audio_file_url: Optional[str] = None
    lyrics: Optional[str] = None

    @validator('release_date', pre=True)
    def parse_release_date(cls, v):
        if v == '' or v is None:
            return None
        return v

    @validator('advance_amount', pre=True)
    def parse_advance_amount(cls, v):
        if v is None or v == '' or v == 'N/A':
            return None
        try:
            return int(float(str(v)))
        except (ValueError, TypeError):
            return None

    @validator('is_registered_with_dsp', 'is_invoiced', 'is_paid', 'soundexchange_registered', 'mlc_registered', pre=True)
    def coerce_to_str(cls, v):
        if v is None:
            return None
        return str(v)

    @validator('has_contract_sent', 'has_contract_executed', 'is_registered_with_pro', pre=True)
    def coerce_bool_fields(cls, v):
        if v is None:
            return None
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            low = v.lower()
            if low in ('yes', 'true', '1'):
                return True
            if low in ('no', 'false', '0'):
                return False
        return v

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
        if creator_id and has_shared_access(db, current_user.id, creator_id, required_module="catalog"):
            pass
        else:
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
    
    song_ids = [song.id for song in songs]
    song_client_map = {}
    
    if song_ids:
        if creator_id:
            relevant_credits = db.query(SongCredit).filter(
                SongCredit.song_id.in_(song_ids),
                SongCredit.creator_id == creator_id,
            ).all()
            creator_obj = db.query(Creator).filter(Creator.id == creator_id).first()
            for credit in relevant_credits:
                if creator_obj:
                    song_client_map[credit.song_id] = (creator_obj.display_name, creator_obj.id, credit.role, credit.id)
        else:
            subquery = db.query(
                func.min(SongCredit.id).label("min_id")
            ).filter(
                SongCredit.song_id.in_(song_ids)
            ).group_by(SongCredit.song_id).subquery()
            
            first_credits = db.query(SongCredit).filter(
                SongCredit.id.in_(db.query(subquery.c.min_id))
            ).all()
            
            creator_ids = [credit.creator_id for credit in first_credits]
            creators_map = {}
            if creator_ids:
                creators = db.query(Creator).filter(Creator.id.in_(creator_ids)).all()
                creators_map = {creator.id: creator for creator in creators}
            
            for credit in first_credits:
                creator_obj = creators_map.get(credit.creator_id)
                if creator_obj:
                    song_client_map[credit.song_id] = (creator_obj.display_name, creator_obj.id, credit.role, credit.id)
    
    creator_pub_map = {}
    creator_master_map = {}
    creator_credit_map = {}
    if creator_id and song_ids:
        creator_splits = db.query(
            ContractAsset.asset_id,
            RightsSplit.rights_type,
            func.sum(RightsSplit.share_percentage),
        ).join(
            RightsSplit, RightsSplit.contract_asset_id == ContractAsset.id
        ).filter(
            ContractAsset.asset_type == "SONG",
            ContractAsset.asset_id.in_(song_ids),
            RightsSplit.rights_holder_id == creator_id,
            RightsSplit.rights_type.in_(["PUBLISHING", "MASTER"]),
        ).group_by(ContractAsset.asset_id, RightsSplit.rights_type).all()

        for sid, rtype, total in creator_splits:
            if rtype == "PUBLISHING":
                creator_pub_map[sid] = float(total)
            elif rtype == "MASTER":
                creator_master_map[sid] = float(total)

        credits_for_creator = db.query(SongCredit).filter(
            SongCredit.song_id.in_(song_ids),
            SongCredit.creator_id == creator_id,
        ).all()
        for c in credits_for_creator:
            creator_credit_map[c.song_id] = c

    result = []
    for song in songs:
        client_name = None
        client_id = None
        credit_role = None
        credit_id = None
        if song.id in song_client_map:
            client_name, client_id, credit_role, credit_id = song_client_map[song.id]
        
        if creator_id:
            pub_pct = creator_pub_map.get(song.id)
            master_pct = creator_master_map.get(song.id)
            credit = creator_credit_map.get(song.id)
            if credit:
                if pub_pct is None and credit.pub_share is not None:
                    pub_pct = credit.pub_share
                if master_pct is None and credit.master_share is not None:
                    master_pct = credit.master_share
        else:
            pub_pct = song.publishing_percentage
            master_pct = song.master_percentage

        song_data = _song_to_response(song)
        song_data["publishing_percentage"] = pub_pct
        song_data["master_percentage"] = master_pct
        song_data["client_name"] = client_name
        song_data["client_id"] = client_id
        song_data["credit_role"] = credit_role
        song_data["credit_id"] = credit_id
        result.append(song_data)
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
    
    credits = db.query(SongCredit, Creator).outerjoin(
        Creator, SongCredit.creator_id == Creator.id
    ).filter(SongCredit.song_id == song.id).order_by(SongCredit.id).all()
    
    dsp_links = db.query(SongDSPLink).filter(SongDSPLink.song_id == song.id).all()
    
    checklist_statuses = db.query(SongChecklistStatus, ChecklistItem).join(
        ChecklistItem, SongChecklistStatus.checklist_item_id == ChecklistItem.id
    ).filter(SongChecklistStatus.song_id == song.id).all()
    
    client_name = None
    client_id = None
    for credit, creator in credits:
        if creator:
            client_name = creator.display_name
            client_id = creator.id
            break
    
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
        "release_status": getattr(song, 'release_status', None) or "unreleased",
        "entry_type": getattr(song, 'entry_type', None) or "Song",
        "parent_song_id": song.parent_song_id,
        "parent_song_title": song.parent_song.title if song.parent_song_id and song.parent_song else None,
        "spotify_link": song.spotify_link,
        "label": song.label,
        "publishing_percentage": song.publishing_percentage,
        "master_percentage": song.master_percentage,
        "advance_amount": song.advance_amount,
        "recording_code": song.recording_code,
        "master_paid": song.master_paid,
        "soundexchange_registered": song.soundexchange_registered,
        "mlc_registered": song.mlc_registered,
        "payment_status": song.payment_status,
        "contract_location": song.contract_location,
        "notes": song.notes,
        "media_url": song.media_url,
        "client_name": client_name,
        "client_id": client_id,
        "credits": [
            {
                "id": credit.id,
                "creator_id": creator.id if creator else None,
                "creator_name": creator.display_name if creator else None,
                "role": credit.role,
                "share_percentage": credit.share_percentage,
                "pub_share": credit.pub_share,
                "master_share": credit.master_share,
                "needs_review": credit.needs_review,
                "unmatched_artist_name": credit.unmatched_artist_name,
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

@router.get("/{song_id}/streaming")
def get_song_streaming(
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
    if not membership and not getattr(current_user, 'is_super_admin', False):
        raise HTTPException(status_code=403, detail="Not authorized")

    from ..services.stream_estimator import estimate_streams_for_song, get_song_stream_summary, PLATFORM_DISPLAY

    import logging
    logger = logging.getLogger("cadence")
    try:
        estimate_result = estimate_streams_for_song(song.id, song.organization_id, db)
    except Exception as e:
        logger.debug(f"Stream estimation failed for song {song.id}: {e}")
        estimate_result = {"total_estimated_streams": 0, "platform_breakdown": {}, "riaa_equivalents": {}}

    summary = get_song_stream_summary(song.id, song.organization_id, db)

    platform_breakdown = estimate_result.get("platform_breakdown", {})

    platforms = {}
    for platform_key, display_info in PLATFORM_DISPLAY.items():
        est = platform_breakdown.get(platform_key, {})
        summ = summary.get("platforms", {}).get(platform_key, {})
        streams = 0
        if isinstance(summ, dict):
            streams = summ.get("streams", 0)
        elif isinstance(summ, (int, float)):
            streams = int(summ)
        if streams == 0 and isinstance(est, dict):
            streams = int(est.get("estimated_streams", 0))
        method = None
        confidence = 0
        if isinstance(est, dict):
            method = est.get("method")
            confidence = est.get("confidence", 0)
        platforms[platform_key] = {
            "name": display_info["name"],
            "color": display_info["color"],
            "streams": streams,
            "method": method,
            "confidence": confidence,
        }

    total_streams = estimate_result.get("total_estimated_streams", 0)
    if total_streams == 0:
        total_streams = summary.get("total_streams", 0)
    if total_streams == 0:
        total_streams = sum(p["streams"] for p in platforms.values())

    dsp_links = db.query(SongDSPLink).filter(SongDSPLink.song_id == song.id).all()

    return {
        "song_id": song.id,
        "title": song.title,
        "primary_artist": song.primary_artist,
        "total_streams": total_streams,
        "confidence": summary.get("confidence", 0),
        "last_updated": summary.get("last_updated") or estimate_result.get("computed_at"),
        "riaa_equivalents": summary.get("riaa_equivalents") or estimate_result.get("riaa_equivalents", {}),
        "platforms": platforms,
        "dsp_links": [{"id": l.id, "platform": l.platform, "url": l.url} for l in dsp_links],
        "has_spotify_link": bool(song.spotify_link or any(l.platform == "SPOTIFY" for l in dsp_links)),
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

    try:
        from ..services.audit_service import log_action
        for song in songs:
            log_action(db, song.organization_id, current_user.id, "DELETE", "SONG", song.id, song.title)

        _cleanup_song_dependencies(db, request.song_ids)

        from sqlalchemy import text
        db.execute(text("DELETE FROM songs WHERE id = ANY(:ids)"), {"ids": list(request.song_ids)})
        db.commit()
        return {"deleted": len(songs)}
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger("cadence").error(f"Failed to delete songs {request.song_ids}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete songs: {str(e)}")

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

    try:
        from ..services.audit_service import log_action
        log_action(db, song.organization_id, current_user.id, "DELETE", "SONG", song.id, song.title)

        _cleanup_song_dependencies(db, [song_id])

        from sqlalchemy import text
        db.execute(text("DELETE FROM songs WHERE id = :id"), {"id": song_id})
        db.commit()
        return {"message": "Song deleted successfully"}
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger("cadence").error(f"Failed to delete song {song_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete song: {str(e)}")

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
    logger = logging.getLogger("cadence")
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this organization")
    
    try:
        song = Song(
            organization_id=org_id,
            title=request.title,
            primary_artist=request.primary_artist,
            isrc=request.isrc,
            iswc=request.iswc,
            project_title=request.project_title,
            release_date=request.release_date,
            is_released=False,
            release_status="unreleased",
            entry_type=request.entry_type or "Song",
            label=request.label,
            publishing_percentage=request.publishing_percentage,
            master_percentage=request.master_percentage,
            advance_amount=request.advance_amount,
            recording_code=request.recording_code,
            master_paid=request.master_paid,
            soundexchange_registered=request.soundexchange_registered,
            mlc_registered=request.mlc_registered,
            payment_status=request.payment_status,
            contract_location=request.contract_location,
            notes=request.notes,
            media_url=request.media_url,
            has_contract_executed=request.has_contract_executed or False,
            is_registered_with_pro=request.is_registered_with_pro or False,
            is_registered_with_dsp=request.is_registered_with_dsp,
            is_invoiced=request.is_invoiced,
            is_paid=request.is_paid
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
        db.flush()
        
        from ..utils.health_sync import sync_song_to_checklist
        sync_song_to_checklist(db, song)

        from ..services.audit_service import log_action
        log_action(db, org_id, current_user.id, "CREATE", "SONG", song.id, song.title)
        db.commit()
        db.refresh(song)
        
        return _song_to_response(song)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create song for org {org_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to create song. Please try again.")

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
        song_credits = db.query(SongCredit).filter(SongCredit.song_id == song_id).all()
        has_access = any(has_shared_access(db, current_user.id, c.creator_id, required_module="catalog") for c in song_credits)
        if not has_access:
            raise HTTPException(status_code=403, detail="Not authorized to access this song")
    
    update_data = request.dict(exclude_unset=True)

    bool_fields = {"has_contract_sent", "has_contract_executed", "is_registered_with_pro"}
    for key in bool_fields:
        if key in update_data:
            v = update_data[key]
            if isinstance(v, str):
                low = v.lower()
                if low in ("yes", "true"):
                    update_data[key] = True
                elif low in ("no", "false"):
                    update_data[key] = False
                else:
                    update_data[key] = None

    for key, value in update_data.items():
        setattr(song, key, value)
    
    if 'release_date' in update_data:
        song.is_released = (song.release_date is not None and song.release_date <= date.today())
        if song.release_date is not None and song.release_date <= date.today():
            song.release_status = "released"
        else:
            song.release_status = "unreleased"

    if 'is_released' in update_data and 'release_date' not in update_data:
        if song.is_released:
            song.release_status = "released"
        else:
            song.release_status = "unreleased"

    if 'release_status' in update_data and 'is_released' not in update_data and 'release_date' not in update_data:
        song.is_released = (song.release_status == "released")

    # Cross-field sync: payment_status <-> is_paid / master_paid
    if 'payment_status' in update_data:
        ps = (update_data['payment_status'] or '').strip().upper()
        if ps == 'PAID':
            song.payment_status = 'PAID'
            song.is_paid = 'Yes'
            song.master_paid = 'Yes'
        else:
            song.payment_status = ps if ps else None
            song.is_paid = 'No'
            song.master_paid = 'No'
        update_data['is_paid'] = song.is_paid
        update_data['master_paid'] = song.master_paid
        update_data['payment_status'] = song.payment_status
    elif 'is_paid' in update_data:
        val = update_data['is_paid']
        if isinstance(val, str):
            paid = val.strip().lower() in ('yes', 'true')
        else:
            paid = bool(val)
        if paid:
            song.payment_status = 'PAID'
            song.is_paid = 'Yes'
            song.master_paid = 'Yes'
        else:
            song.payment_status = 'PENDING'
            song.is_paid = 'No'
            song.master_paid = 'No'
        update_data['payment_status'] = song.payment_status
        update_data['is_paid'] = song.is_paid
        update_data['master_paid'] = song.master_paid

    from ..services.audit_service import log_action
    changed_fields = list(update_data.keys())
    log_action(db, song.organization_id, current_user.id, "UPDATE", "SONG", song.id, song.title,
               details={"changed_fields": changed_fields})

    health_fields = {"isrc", "iswc", "has_contract_sent", "has_contract_executed",
                     "is_registered_with_pro", "is_registered_with_dsp", "is_invoiced", "is_paid",
                     "soundexchange_registered", "mlc_registered"}
    if health_fields & set(changed_fields):
        from ..utils.health_sync import sync_song_to_checklist
        sync_song_to_checklist(db, song)

    db.commit()
    db.refresh(song)
    
    return _song_to_response(song)


class MergeSongsRequest(BaseModel):
    primary_song_id: int
    merge_song_ids: List[int]


@router.post("/org/{org_id}/merge")
def merge_songs(
    org_id: int,
    request: MergeSongsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from sqlalchemy import text
    from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY
    import sqlalchemy

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")

    primary = db.query(Song).filter(Song.id == request.primary_song_id, Song.organization_id == org_id).first()
    if not primary:
        raise HTTPException(status_code=404, detail="Primary song not found")

    merge_songs_list = db.query(Song).filter(
        Song.id.in_(request.merge_song_ids),
        Song.organization_id == org_id
    ).all()
    if len(merge_songs_list) != len(request.merge_song_ids):
        raise HTTPException(status_code=404, detail="One or more merge songs not found")

    if request.primary_song_id in request.merge_song_ids:
        raise HTTPException(status_code=400, detail="Primary song cannot be in the merge list")

    merge_ids = list(request.merge_song_ids)
    ids_param = {"ids": merge_ids}
    pid_ids_param = {"pid": primary.id, "ids": merge_ids}
    arr_type = sqlalchemy.ARRAY(sqlalchemy.Integer)

    try:
        existing_credits = db.query(SongCredit).filter(SongCredit.song_id == primary.id).all()
        existing_credit_keys = {(c.creator_id, c.role) for c in existing_credits}

        for merge_song in merge_songs_list:
            merge_credits = db.query(SongCredit).filter(SongCredit.song_id == merge_song.id).all()
            for credit in merge_credits:
                if (credit.creator_id, credit.role) not in existing_credit_keys:
                    new_credit = SongCredit(
                        song_id=primary.id,
                        creator_id=credit.creator_id,
                        role=credit.role,
                        share_percentage=credit.share_percentage,
                        pub_share=credit.pub_share,
                        master_share=credit.master_share,
                    )
                    db.add(new_credit)
                    existing_credit_keys.add((credit.creator_id, credit.role))

        update_stmt = text("UPDATE placements SET song_id = :pid WHERE song_id = ANY(CAST(:ids AS INTEGER[]))")
        db.execute(update_stmt, pid_ids_param)
        db.execute(text("UPDATE royalty_transactions SET song_id = :pid WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), pid_ids_param)
        db.execute(text("UPDATE audio_assets SET song_id = :pid WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), pid_ids_param)
        db.execute(text("UPDATE action_items SET song_id = :pid WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), pid_ids_param)
        db.execute(text("UPDATE contract_documents SET song_id = :pid WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), pid_ids_param)
        db.execute(text("UPDATE expenses SET song_id = :pid WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), pid_ids_param)
        db.execute(text("UPDATE fees SET song_id = :pid WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), pid_ids_param)
        db.execute(text("UPDATE royalty_ledger_entries SET song_id = :pid WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), pid_ids_param)
        db.execute(text("UPDATE royalty_statement_lines SET matched_song_id = :pid WHERE matched_song_id = ANY(CAST(:ids AS INTEGER[]))"), pid_ids_param)

        contract_assets = db.query(ContractAsset).filter(
            ContractAsset.asset_type == "SONG",
            ContractAsset.asset_id.in_(merge_ids)
        ).all()
        for ca in contract_assets:
            existing_ca = db.query(ContractAsset).filter(
                ContractAsset.contract_id == ca.contract_id,
                ContractAsset.asset_type == "SONG",
                ContractAsset.asset_id == primary.id
            ).first()
            if existing_ca:
                db.delete(ca)
            else:
                ca.asset_id = primary.id

        metadata_fields = [
            'isrc', 'iswc', 'project_title', 'release_date', 'label',
            'publishing_percentage', 'master_percentage', 'advance_amount',
            'recording_code', 'media_url', 'spotify_link', 'notes'
        ]
        for field in metadata_fields:
            primary_val = getattr(primary, field, None)
            if not primary_val:
                for merge_song in merge_songs_list:
                    merge_val = getattr(merge_song, field, None)
                    if merge_val:
                        setattr(primary, field, merge_val)
                        break

        if not primary.is_released:
            for merge_song in merge_songs_list:
                if merge_song.is_released:
                    primary.is_released = True
                    break

        if not primary.is_registered_with_pro:
            for merge_song in merge_songs_list:
                if merge_song.is_registered_with_pro:
                    primary.is_registered_with_pro = True
                    break

        del_stmt = text("DELETE FROM song_credits WHERE song_id = ANY(CAST(:ids AS INTEGER[]))")
        db.execute(del_stmt, ids_param)
        db.execute(text("DELETE FROM song_dsp_links WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), ids_param)
        db.execute(text("DELETE FROM song_checklist_status WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), ids_param)
        db.execute(text("DELETE FROM song_valuation_snapshots WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), ids_param)
        db.execute(text("DELETE FROM analytics WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), ids_param)
        db.execute(text("DELETE FROM song_streaming_metrics WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), ids_param)
        db.execute(text("DELETE FROM territory_revenue WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), ids_param)
        db.execute(text("DELETE FROM valuation_calculations WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), ids_param)
        db.execute(text("DELETE FROM song_contracts WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), ids_param)
        db.execute(text("DELETE FROM work_tracks WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), ids_param)
        db.execute(text("DELETE FROM release_tracks WHERE song_id = ANY(CAST(:ids AS INTEGER[]))"), ids_param)
        db.execute(text("UPDATE songs SET parent_song_id = NULL WHERE parent_song_id = ANY(CAST(:ids AS INTEGER[]))"), ids_param)

        for merge_song in merge_songs_list:
            db.delete(merge_song)

        from ..services.audit_service import log_action
        log_action(db, org_id, current_user.id, "MERGE", "SONG", primary.id,
                   f"Merged songs {merge_ids} into {primary.title}")

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Merge failed: {str(e)}")

    db.refresh(primary)

    final_credits = db.query(SongCredit).filter(SongCredit.song_id == primary.id).all()
    credit_list = []
    for c in final_credits:
        creator = db.query(Creator).filter(Creator.id == c.creator_id).first()
        credit_list.append({
            "id": c.id,
            "creator_id": c.creator_id,
            "creator_name": creator.display_name if creator else None,
            "role": c.role,
            "share_percentage": c.share_percentage,
        })

    return {
        "message": f"Successfully merged {len(merge_ids)} song(s) into '{primary.title}'",
        "primary_song": {
            "id": primary.id,
            "title": primary.title,
            "primary_artist": primary.primary_artist,
            "isrc": primary.isrc,
        },
        "credits": credit_list,
        "merged_count": len(merge_ids),
    }

@router.post("/{song_id}/duplicate")
def duplicate_song(
    song_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    source = db.query(Song).filter(Song.id == song_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Song not found")

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == source.organization_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")

    new_song = Song(
        organization_id=source.organization_id,
        title=f"{source.title} (Copy)",
        asset_type=source.asset_type,
        primary_artist=source.primary_artist,
        project_title=source.project_title,
        release_date=None,
        is_released=False,
        release_status="unreleased",
        entry_type=getattr(source, 'entry_type', None) or "Song",
        parent_song_id=source.id,
        label=source.label,
        publishing_percentage=source.publishing_percentage,
        master_percentage=source.master_percentage,
        advance_amount=source.advance_amount,
        recording_code=source.recording_code,
        master_paid=source.master_paid,
        soundexchange_registered=source.soundexchange_registered,
        mlc_registered=source.mlc_registered,
        payment_status=source.payment_status,
        contract_location=source.contract_location,
        notes=source.notes,
        media_url=source.media_url,
        audio_file_url=source.audio_file_url,
        has_contract_sent=source.has_contract_sent,
        has_contract_executed=source.has_contract_executed,
        is_registered_with_pro=source.is_registered_with_pro,
        is_registered_with_dsp=source.is_registered_with_dsp,
        is_invoiced=source.is_invoiced,
        is_paid=source.is_paid,
    )
    db.add(new_song)
    db.flush()

    source_credits = db.query(SongCredit).filter(SongCredit.song_id == song_id).all()
    for credit in source_credits:
        new_credit = SongCredit(
            song_id=new_song.id,
            creator_id=credit.creator_id,
            role=credit.role,
            share_percentage=credit.share_percentage,
            pub_share=credit.pub_share,
            master_share=credit.master_share,
            creative_contact_id=credit.creative_contact_id,
        )
        db.add(new_credit)

    checklist_items = db.query(ChecklistItem).all()
    for item in checklist_items:
        status = SongChecklistStatus(
            song_id=new_song.id,
            checklist_item_id=item.id,
            status="NOT_STARTED"
        )
        db.add(status)
    db.flush()

    from ..utils.health_sync import sync_song_to_checklist
    sync_song_to_checklist(db, new_song)

    from ..services.audit_service import log_action
    log_action(db, source.organization_id, current_user.id, "DUPLICATE", "SONG", new_song.id, new_song.title)
    db.commit()
    db.refresh(new_song)

    return _song_to_response(new_song)


@router.post("/{song_id}/mark-released")
def mark_song_released(
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
        raise HTTPException(status_code=403, detail="Not authorized")

    song.release_status = "released"
    song.is_released = True

    from ..services.audit_service import log_action
    log_action(db, song.organization_id, current_user.id, "MARK_RELEASED", "SONG", song.id, song.title)
    db.commit()
    db.refresh(song)

    return _song_to_response(song)
