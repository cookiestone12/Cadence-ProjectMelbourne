from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
from ..models import get_db, Placement, Song, Work, Contract, OrganizationMember, User, Release, ReleaseTrack, Creator, SongCredit, WorkCredit
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/placements", tags=["placements"])

PLACEMENT_TYPES = ["SYNC", "ADVERTISING", "FILM", "TV", "GAMING", "TRAILER", "OTHER"]
PLACEMENT_STATUSES = ["PITCHED", "IN_REVIEW", "IN_NEGOTIATION", "SECURED", "DELIVERED", "AIRED", "PAID", "DECLINED", "CANCELLED"]
MEDIA_TYPES = ["FILM", "TV_SHOW", "COMMERCIAL", "VIDEO_GAME", "TRAILER", "PODCAST", "SOCIAL_MEDIA", "OTHER"]

STATUS_TRANSITIONS = {
    "PITCHED": ["IN_REVIEW", "IN_NEGOTIATION", "DECLINED", "CANCELLED"],
    "IN_REVIEW": ["IN_NEGOTIATION", "PITCHED", "DECLINED", "CANCELLED"],
    "IN_NEGOTIATION": ["SECURED", "IN_REVIEW", "DECLINED", "CANCELLED"],
    "SECURED": ["DELIVERED", "CANCELLED"],
    "DELIVERED": ["AIRED", "PAID"],
    "AIRED": ["PAID"],
    "PAID": [],
    "DECLINED": ["PITCHED"],
    "CANCELLED": ["PITCHED"],
}


class PlacementCreate(BaseModel):
    title: str
    description: Optional[str] = None
    placement_type: str = "SYNC"
    song_id: Optional[int] = None
    work_id: Optional[int] = None
    release_id: Optional[int] = None
    contract_id: Optional[int] = None
    client_name: Optional[str] = None
    project_name: Optional[str] = None
    media_type: Optional[str] = None
    license_fee: Optional[float] = None
    license_currency: str = "USD"
    license_type: Optional[str] = None
    territory: Optional[str] = None
    usage_notes: Optional[str] = None
    pitched_date: Optional[date] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    assigned_to_user_id: Optional[int] = None


class PlacementUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    placement_type: Optional[str] = None
    song_id: Optional[int] = None
    work_id: Optional[int] = None
    release_id: Optional[int] = None
    contract_id: Optional[int] = None
    client_name: Optional[str] = None
    project_name: Optional[str] = None
    media_type: Optional[str] = None
    license_fee: Optional[float] = None
    license_currency: Optional[str] = None
    license_type: Optional[str] = None
    territory: Optional[str] = None
    usage_notes: Optional[str] = None
    pitched_date: Optional[date] = None
    secured_date: Optional[date] = None
    delivery_date: Optional[date] = None
    air_date: Optional[date] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None
    assigned_to_user_id: Optional[int] = None


def verify_org_access(db: Session, user: User, org_id: int):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")
    return membership


def placement_to_dict(p: Placement, db: Session) -> dict:
    song_title = None
    if p.song_id:
        song = db.query(Song).filter(Song.id == p.song_id).first()
        song_title = song.title if song else None

    work_title = None
    if p.work_id:
        work = db.query(Work).filter(Work.id == p.work_id).first()
        work_title = work.title if work else None

    release_title = None
    if p.release_id:
        release = db.query(Release).filter(Release.id == p.release_id).first()
        release_title = release.title if release else None

    contract_title = None
    if p.contract_id:
        contract = db.query(Contract).filter(Contract.id == p.contract_id).first()
        contract_title = contract.title if contract else None

    assigned_to_name = None
    if p.assigned_to_user_id:
        user = db.query(User).filter(User.id == p.assigned_to_user_id).first()
        assigned_to_name = user.username if user else None

    creator_names = []
    if p.song_id:
        credits = db.query(SongCredit).filter(SongCredit.song_id == p.song_id).all()
        for c in credits:
            creator = db.query(Creator).filter(Creator.id == c.creator_id).first()
            if creator and creator.display_name not in creator_names:
                creator_names.append(creator.display_name)
    if p.work_id:
        credits = db.query(WorkCredit).filter(WorkCredit.work_id == p.work_id).all()
        for c in credits:
            creator = db.query(Creator).filter(Creator.id == c.creator_id).first()
            if creator and creator.display_name not in creator_names:
                creator_names.append(creator.display_name)

    return {
        "id": p.id,
        "organization_id": p.organization_id,
        "title": p.title,
        "description": p.description,
        "placement_type": p.placement_type,
        "status": p.status,
        "song_id": p.song_id,
        "song_title": song_title,
        "work_id": p.work_id,
        "work_title": work_title,
        "release_id": p.release_id,
        "release_title": release_title,
        "contract_id": p.contract_id,
        "contract_title": contract_title,
        "client_name": p.client_name,
        "project_name": p.project_name,
        "media_type": p.media_type,
        "license_fee": p.license_fee,
        "license_currency": p.license_currency,
        "license_type": p.license_type,
        "territory": p.territory,
        "usage_notes": p.usage_notes,
        "pitched_date": str(p.pitched_date) if p.pitched_date else None,
        "secured_date": str(p.secured_date) if p.secured_date else None,
        "delivery_date": str(p.delivery_date) if p.delivery_date else None,
        "air_date": str(p.air_date) if p.air_date else None,
        "contact_name": p.contact_name,
        "contact_email": p.contact_email,
        "notes": p.notes,
        "assigned_to_user_id": p.assigned_to_user_id,
        "assigned_to_name": assigned_to_name,
        "creator_names": creator_names,
        "created_at": p.created_at.isoformat() if p.created_at else None,
        "updated_at": p.updated_at.isoformat() if p.updated_at else None,
    }


def placements_to_dicts(placements: List[Placement], db: Session) -> List[dict]:
    """
    Batch-load related data for multiple placements to avoid N+1 queries.
    This function performs bulk queries for all related data and constructs result dicts
    using in-memory lookups instead of individual queries per placement.
    """
    if not placements:
        return []
    
    # Collect unique IDs from all placements
    song_ids = set()
    work_ids = set()
    release_ids = set()
    contract_ids = set()
    user_ids = set()
    
    for p in placements:
        if p.song_id:
            song_ids.add(p.song_id)
        if p.work_id:
            work_ids.add(p.work_id)
        if p.release_id:
            release_ids.add(p.release_id)
        if p.contract_id:
            contract_ids.add(p.contract_id)
        if p.assigned_to_user_id:
            user_ids.add(p.assigned_to_user_id)
    
    # Batch load all related data with single queries
    songs_map = {}
    if song_ids:
        songs = db.query(Song).filter(Song.id.in_(song_ids)).all()
        songs_map = {s.id: s.title for s in songs}
    
    works_map = {}
    if work_ids:
        works = db.query(Work).filter(Work.id.in_(work_ids)).all()
        works_map = {w.id: w.title for w in works}
    
    releases_map = {}
    if release_ids:
        releases = db.query(Release).filter(Release.id.in_(release_ids)).all()
        releases_map = {r.id: r.title for r in releases}
    
    contracts_map = {}
    if contract_ids:
        contracts = db.query(Contract).filter(Contract.id.in_(contract_ids)).all()
        contracts_map = {c.id: c.title for c in contracts}
    
    users_map = {}
    if user_ids:
        users = db.query(User).filter(User.id.in_(user_ids)).all()
        users_map = {u.id: u.username for u in users}
    
    # Build creator names mappings
    song_creators_map = {}
    work_creators_map = {}
    
    if song_ids:
        song_credits = db.query(SongCredit).filter(SongCredit.song_id.in_(song_ids)).all()
        song_creator_ids = {c.creator_id for c in song_credits}
        
        if song_creator_ids:
            creators = db.query(Creator).filter(Creator.id.in_(song_creator_ids)).all()
            creator_names = {c.id: c.display_name for c in creators}
            
            for credit in song_credits:
                if credit.song_id not in song_creators_map:
                    song_creators_map[credit.song_id] = []
                creator_name = creator_names.get(credit.creator_id)
                if creator_name and creator_name not in song_creators_map[credit.song_id]:
                    song_creators_map[credit.song_id].append(creator_name)
    
    if work_ids:
        work_credits = db.query(WorkCredit).filter(WorkCredit.work_id.in_(work_ids)).all()
        work_creator_ids = {c.creator_id for c in work_credits}
        
        if work_creator_ids:
            creators = db.query(Creator).filter(Creator.id.in_(work_creator_ids)).all()
            creator_names = {c.id: c.display_name for c in creators}
            
            for credit in work_credits:
                if credit.work_id not in work_creators_map:
                    work_creators_map[credit.work_id] = []
                creator_name = creator_names.get(credit.creator_id)
                if creator_name and creator_name not in work_creators_map[credit.work_id]:
                    work_creators_map[credit.work_id].append(creator_name)
    
    # Build result list using dictionary lookups
    result = []
    for p in placements:
        creator_names = []
        creator_names.extend(song_creators_map.get(p.song_id, []))
        creator_names.extend(work_creators_map.get(p.work_id, []))
        
        result.append({
            "id": p.id,
            "organization_id": p.organization_id,
            "title": p.title,
            "description": p.description,
            "placement_type": p.placement_type,
            "status": p.status,
            "song_id": p.song_id,
            "song_title": songs_map.get(p.song_id) if p.song_id else None,
            "work_id": p.work_id,
            "work_title": works_map.get(p.work_id) if p.work_id else None,
            "release_id": p.release_id,
            "release_title": releases_map.get(p.release_id) if p.release_id else None,
            "contract_id": p.contract_id,
            "contract_title": contracts_map.get(p.contract_id) if p.contract_id else None,
            "client_name": p.client_name,
            "project_name": p.project_name,
            "media_type": p.media_type,
            "license_fee": p.license_fee,
            "license_currency": p.license_currency,
            "license_type": p.license_type,
            "territory": p.territory,
            "usage_notes": p.usage_notes,
            "pitched_date": str(p.pitched_date) if p.pitched_date else None,
            "secured_date": str(p.secured_date) if p.secured_date else None,
            "delivery_date": str(p.delivery_date) if p.delivery_date else None,
            "air_date": str(p.air_date) if p.air_date else None,
            "contact_name": p.contact_name,
            "contact_email": p.contact_email,
            "notes": p.notes,
            "assigned_to_user_id": p.assigned_to_user_id,
            "assigned_to_name": users_map.get(p.assigned_to_user_id) if p.assigned_to_user_id else None,
            "creator_names": creator_names,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        })
    
    return result


@router.get("/org/{org_id}")
def get_placements(
    org_id: int,
    status: Optional[str] = None,
    placement_type: Optional[str] = None,
    song_id: Optional[int] = None,
    client_name: Optional[str] = None,
    creator_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(db, current_user, org_id)

    query = db.query(Placement).filter(Placement.organization_id == org_id)

    if status:
        query = query.filter(Placement.status == status)
    if placement_type:
        query = query.filter(Placement.placement_type == placement_type)
    if song_id:
        query = query.filter(Placement.song_id == song_id)
    if client_name:
        query = query.filter(Placement.client_name.ilike(f"%{client_name}%"))
    if creator_id:
        creator_song_ids = [r[0] for r in db.query(SongCredit.song_id).filter(SongCredit.creator_id == creator_id).all()]
        creator_work_ids = [r[0] for r in db.query(WorkCredit.work_id).filter(WorkCredit.creator_id == creator_id).all()]
        conditions = []
        if creator_song_ids:
            conditions.append(Placement.song_id.in_(creator_song_ids))
        if creator_work_ids:
            conditions.append(Placement.work_id.in_(creator_work_ids))
        if conditions:
            query = query.filter(or_(*conditions))
        else:
            return []

    query = query.order_by(desc(Placement.updated_at))
    placements = query.all()

    return placements_to_dicts(placements, db)


@router.get("/org/{org_id}/summary")
def get_placement_summary(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(db, current_user, org_id)

    from sqlalchemy import func

    status_counts = db.query(
        Placement.status, func.count(Placement.id)
    ).filter(
        Placement.organization_id == org_id
    ).group_by(Placement.status).all()

    total_fees = db.query(func.sum(Placement.license_fee)).filter(
        Placement.organization_id == org_id,
        Placement.status.in_(["SECURED", "DELIVERED", "AIRED", "PAID"])
    ).scalar() or 0

    paid_fees = db.query(func.sum(Placement.license_fee)).filter(
        Placement.organization_id == org_id,
        Placement.status == "PAID"
    ).scalar() or 0

    return {
        "status_counts": {s: c for s, c in status_counts},
        "total_pipeline_value": total_fees,
        "total_paid": paid_fees,
        "total_placements": sum(c for _, c in status_counts),
    }


@router.get("/org/{org_id}/creators")
def get_placement_creators(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(db, current_user, org_id)
    creators = db.query(Creator).filter(Creator.organization_id == org_id).order_by(Creator.display_name).all()
    return [{"id": c.id, "name": c.display_name} for c in creators]


@router.get("/org/{org_id}/search/works")
def search_works(
    org_id: int,
    search: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import Work
    verify_org_access(db, current_user, org_id)
    query = db.query(Work).filter(Work.organization_id == org_id)
    if search:
        query = query.filter(Work.title.ilike(f"%{search}%"))
    works = query.order_by(Work.title).limit(20).all()
    return [{"id": w.id, "title": w.title, "iswc": w.iswc} for w in works]


@router.get("/org/{org_id}/search/releases")
def search_releases(
    org_id: int,
    search: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import Release
    verify_org_access(db, current_user, org_id)
    query = db.query(Release).filter(Release.organization_id == org_id)
    if search:
        query = query.filter(Release.title.ilike(f"%{search}%"))
    releases = query.order_by(Release.title).limit(20).all()
    return [{"id": r.id, "title": r.title, "primary_artist": r.primary_artist, "upc": r.upc} for r in releases]


@router.get("/{placement_id}")
def get_placement(
    placement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    placement = db.query(Placement).filter(Placement.id == placement_id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    verify_org_access(db, current_user, placement.organization_id)

    return placement_to_dict(placement, db)


@router.post("/org/{org_id}")
def create_placement(
    org_id: int,
    data: PlacementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(db, current_user, org_id)

    if data.placement_type and data.placement_type not in PLACEMENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid placement type. Must be one of: {PLACEMENT_TYPES}")

    placement = Placement(
        organization_id=org_id,
        title=data.title,
        description=data.description,
        placement_type=data.placement_type,
        status="PITCHED",
        song_id=data.song_id,
        work_id=data.work_id,
        release_id=data.release_id,
        contract_id=data.contract_id,
        client_name=data.client_name,
        project_name=data.project_name,
        media_type=data.media_type,
        license_fee=data.license_fee,
        license_currency=data.license_currency,
        license_type=data.license_type,
        territory=data.territory,
        usage_notes=data.usage_notes,
        pitched_date=data.pitched_date or datetime.utcnow().date(),
        contact_name=data.contact_name,
        contact_email=data.contact_email,
        notes=data.notes,
        assigned_to_user_id=data.assigned_to_user_id,
        created_by_user_id=current_user.id,
    )
    db.add(placement)
    db.commit()
    db.refresh(placement)

    return placement_to_dict(placement, db)


@router.put("/{placement_id}")
def update_placement(
    placement_id: int,
    data: PlacementUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    placement = db.query(Placement).filter(Placement.id == placement_id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    verify_org_access(db, current_user, placement.organization_id)

    update_data = data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(placement, key, value)

    db.commit()
    db.refresh(placement)

    return placement_to_dict(placement, db)


@router.post("/{placement_id}/transition")
def transition_placement(
    placement_id: int,
    target_status: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    placement = db.query(Placement).filter(Placement.id == placement_id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    verify_org_access(db, current_user, placement.organization_id)

    current_status = placement.status or "PITCHED"
    allowed = STATUS_TRANSITIONS.get(current_status, [])

    if target_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {current_status} to {target_status}. Allowed: {allowed}"
        )

    placement.status = target_status
    now = datetime.utcnow()

    if target_status == "SECURED" and not placement.secured_date:
        placement.secured_date = now.date()
    elif target_status == "DELIVERED" and not placement.delivery_date:
        placement.delivery_date = now.date()
    elif target_status == "AIRED" and not placement.air_date:
        placement.air_date = now.date()

    if target_status == "PAID" and placement.license_fee and placement.license_fee > 0 and placement.song_id:
        from ..models import RoyaltyStatement, RoyaltyTransaction
        from sqlalchemy import func

        stmt = RoyaltyStatement(
            organization_id=placement.organization_id,
            source_name=f"Sync Placement: {placement.title}",
            source_type="SYNC_PLACEMENT",
            period_start=placement.pitched_date,
            period_end=now.date(),
            currency=placement.license_currency or "USD",
            total_revenue_cents=int(placement.license_fee * 100),
            total_transactions=1,
            matched_transactions=1 if placement.song_id else 0,
            unmatched_transactions=0 if placement.song_id else 1,
            status="PROCESSED",
            processing_notes=f"Auto-generated from placement #{placement.id}: {placement.title}",
            uploaded_by_user_id=current_user.id,
        )
        db.add(stmt)
        db.flush()

        tx = RoyaltyTransaction(
            statement_id=stmt.id,
            organization_id=placement.organization_id,
            original_track_title=placement.title,
            song_id=placement.song_id,
            match_status="MATCHED" if placement.song_id else "UNMATCHED",
            match_confidence=1.0 if placement.song_id else 0.0,
            revenue_cents=int(placement.license_fee * 100),
            currency=placement.license_currency or "USD",
            quantity=1,
            territory=placement.territory,
            platform=f"Sync: {placement.client_name or 'Unknown'}",
            revenue_type="SYNC_FEE",
        )
        db.add(tx)

    db.commit()
    db.refresh(placement)

    return placement_to_dict(placement, db)


@router.delete("/{placement_id}")
def delete_placement(
    placement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    placement = db.query(Placement).filter(Placement.id == placement_id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    verify_org_access(db, current_user, placement.organization_id)

    db.delete(placement)
    db.commit()

    return {"message": "Placement deleted"}


@router.get("/config/options")
def get_placement_options():
    return {
        "placement_types": PLACEMENT_TYPES,
        "statuses": PLACEMENT_STATUSES,
        "media_types": MEDIA_TYPES,
        "status_transitions": STATUS_TRANSITIONS,
    }
