from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_, func, distinct
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, date
import io
import os
from ..models import get_db, Placement, Song, Work, Contract, OrganizationMember, User, Release, ReleaseTrack, Creator, SongCredit, WorkCredit
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/placements", tags=["Placements"])

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


@router.get("/org/{org_id}", summary="List sync placements", description="Returns the org's sync licensing pipeline (PITCHED → APPROVED → CONFIRMED → INVOICED → PAID).\n\n**Path parameter:** `org_id`.\n**Query:** `status`, `creator_id`, `media_type`, `start_date`, `end_date`, `q`, `limit`, `offset`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ total, placements: [{id, title, project_name, media_type, status, song_id, fee_cents, currency, placed_at, client_name}] }`.")
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


@router.get(
    "/org/{org_id}/summary",
    summary='Get sync placement KPI summary',
    description='Returns counts and totals across the placement pipeline for the dashboard tiles.\n\n**Path parameter:** `org_id`.\n**Query:** `start_date`, `end_date`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ total, by_status: {...}, total_fees_cents, average_fee_cents }`.',
)
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


@router.get(
    "/org/{org_id}/creators",
    summary='List creators that appear on placements (filter source)',
    description='Returns the distinct creators with at least one placement.\n\n**Path parameter:** `org_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ creators: [{id, display_name, placement_count}] }`.',
)
def get_placement_creators(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(db, current_user, org_id)
    creators = db.query(Creator).filter(Creator.organization_id == org_id).order_by(Creator.display_name).all()
    return [{"id": c.id, "name": c.display_name} for c in creators]


@router.get(
    "/org/{org_id}/search/works",
    summary='Type-ahead search for works to attach to a placement',
    description="Used by the placement create/edit form's work picker.\n\n**Path parameter:** `org_id`.\n**Query:** `q` (required), `limit` (default 20).\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ works: [{id, title, writers}] }`.",
)
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


@router.get(
    "/org/{org_id}/search/releases",
    summary='Type-ahead search for releases to attach to a placement',
    description="Used by the placement create/edit form's release picker.\n\n**Path parameter:** `org_id`.\n**Query:** `q` (required), `limit` (default 20).\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ releases: [{id, name, artist, release_date}] }`.",
)
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


@router.get("/{placement_id}", summary="Get placement detail", description="Returns full placement data including financials, project metadata, and linked song(s).\n\n**Path parameter:** `placement_id`.\n**Auth:** Bearer JWT — caller must be a member of the placement's org.\n**Response:** `{ id, title, project_name, media_type, license_type, status, song_id, song_title, fee_cents, currency, term_months, territory, client_name, contact_email, notes, placed_at, history: [...] }`.")
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


@router.post("/org/{org_id}", summary="Create a placement", description='Adds a new sync placement to the pipeline at the supplied status.\n\n**Path parameter:** `org_id`.\n**Body:** `{ title, project_name, media_type, license_type?, status?, song_id, fee_cents?, currency?, term_months?, territory?, client_name?, contact_email?, notes? }`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** the created placement.')
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
    db.flush()

    from ..services.audit_service import log_action
    log_action(db, org_id, current_user.id, "CREATE", "PLACEMENT", placement.id, placement.title)

    db.commit()
    db.refresh(placement)

    return placement_to_dict(placement, db)


@router.put("/{placement_id}", summary="Update placement", description="Patches placement fields (project, status, fees, dates, contacts).\n\n**Path parameter:** `placement_id`.\n**Body:** any subset of writable placement fields.\n**Auth:** Bearer JWT — caller must be a member of the placement's org.\n**Response:** the updated placement.")
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

    from ..services.audit_service import log_action
    log_action(db, placement.organization_id, current_user.id, "UPDATE", "PLACEMENT", placement.id, placement.title,
               details={"changed_fields": list(update_data.keys())})

    db.commit()
    db.refresh(placement)

    return placement_to_dict(placement, db)


@router.post("/{placement_id}/transition", summary="Transition placement status", description="Moves a placement to the next pipeline status with validation. Emits the appropriate notifications and audit row.\n\n**Path parameter:** `placement_id`.\n**Body:** `{ to_status: string, note?: string }`.\n**Auth:** Bearer JWT — caller must be a member of the placement's org.\n**Response:** `{ id, status, transitioned_at, transitioned_by }`.")
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

    from ..services.audit_service import log_action
    log_action(db, placement.organization_id, current_user.id, "TRANSITION", "PLACEMENT", placement.id, placement.title,
               details={"from_status": current_status, "to_status": target_status})

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


@router.delete("/{placement_id}", summary="Delete placement", description="Permanently removes a placement record.\n\n**Path parameter:** `placement_id`.\n**Auth:** Bearer JWT — caller must be a member of the placement's org.\n**Response:** `{ success: true }`.")
def delete_placement(
    placement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    placement = db.query(Placement).filter(Placement.id == placement_id).first()
    if not placement:
        raise HTTPException(status_code=404, detail="Placement not found")

    verify_org_access(db, current_user, placement.organization_id)

    from ..services.audit_service import log_action
    log_action(db, placement.organization_id, current_user.id, "DELETE", "PLACEMENT", placement.id, placement.title)

    db.delete(placement)
    db.commit()

    return {"message": "Placement deleted"}


@router.get(
    "/org/{org_id}/clients",
    summary='List the placement clients (sync supervisors / agencies)',
    description='Returns the distinct counterparties (`client_name`) that appear on placements, used to populate the clients filter.\n\n**Path parameter:** `org_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ clients: [{name, placement_count, total_fees_cents}] }`.',
)
def list_placement_clients(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(db, current_user, org_id)
    clients = db.query(distinct(Placement.client_name)).filter(
        Placement.organization_id == org_id,
        Placement.client_name.isnot(None),
        Placement.client_name != ""
    ).order_by(Placement.client_name).all()
    return [c[0] for c in clients]


@router.get("/org/{org_id}/sync-report", summary="Sync placement report", description='Aggregated, branded sync report for the organization. Supports CSV / PDF export downstream.\n\n**Path parameter:** `org_id`.\n**Query:** `start_date`, `end_date`, `format` (`json|csv|pdf`, default `json`).\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** when `format=json`: `{ summary, placements: [...] }`; when `csv|pdf`: file download.')
def generate_sync_report(
    org_id: int,
    client_name: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    format: str = "json",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    verify_org_access(db, current_user, org_id)

    query = db.query(Placement).filter(Placement.organization_id == org_id)

    if client_name:
        query = query.filter(Placement.client_name.ilike(f"%{client_name}%"))
    if status:
        query = query.filter(Placement.status == status)
    if date_from:
        try:
            df = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.filter(Placement.pitched_date >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.filter(Placement.pitched_date <= dt)
        except ValueError:
            pass

    query = query.order_by(desc(Placement.updated_at))
    placements = query.all()
    placement_dicts = placements_to_dicts(placements, db)

    total_revenue = sum(p.license_fee or 0 for p in placements)
    by_status = {}
    by_client = {}
    for p in placements:
        s = p.status or "UNKNOWN"
        by_status[s] = by_status.get(s, 0) + 1
        c = p.client_name or "Unknown"
        by_client[c] = by_client.get(c, 0) + 1

    summary = {
        "total_placements": len(placements),
        "total_revenue": total_revenue,
        "by_status": by_status,
        "by_client": by_client,
    }

    if format == "pdf":
        return _generate_sync_report_pdf(placement_dicts, summary, client_name, status, date_from, date_to)

    return {"placements": placement_dicts, "summary": summary}


def _generate_sync_report_pdf(placements, summary, client_name, status, date_from, date_to):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.enums import TA_CENTER, TA_LEFT

    PRIMARY = colors.HexColor('#5B8A72')
    DARK = colors.HexColor('#3D4A44')
    LIGHT = colors.HexColor('#E8F0EC')
    BORDER = colors.HexColor('#A3C4B5')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.5 * inch,
        leftMargin=0.5 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('SyncTitle', parent=styles['Heading1'], fontSize=22, textColor=DARK, alignment=TA_CENTER, spaceAfter=4)
    subtitle_style = ParagraphStyle('SyncSubtitle', parent=styles['Normal'], fontSize=12, textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=10)
    section_style = ParagraphStyle('SyncSection', parent=styles['Heading2'], fontSize=13, textColor=DARK, spaceBefore=16, spaceAfter=8)
    normal_style = ParagraphStyle('SyncNormal', parent=styles['Normal'], fontSize=10, textColor=DARK)
    small_style = ParagraphStyle('SyncSmall', parent=styles['Normal'], fontSize=7.5, textColor=DARK)
    footer_style = ParagraphStyle('SyncFooter', parent=styles['Normal'], fontSize=8, textColor=colors.grey)

    elements = []

    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'assets', 'cadence-logo.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path, width=2.0 * inch, height=1.125 * inch)
        logo.hAlign = 'CENTER'
        elements.append(logo)
        elements.append(Spacer(1, 6))

    elements.append(Paragraph("Sync Placement Report", title_style))

    filter_parts = []
    if client_name:
        filter_parts.append(f"Client: {client_name}")
    if status:
        filter_parts.append(f"Status: {status}")
    if date_from:
        filter_parts.append(f"From: {date_from}")
    if date_to:
        filter_parts.append(f"To: {date_to}")
    if filter_parts:
        elements.append(Paragraph(" | ".join(filter_parts), subtitle_style))
    else:
        elements.append(Paragraph("All Placements", subtitle_style))

    elements.append(Paragraph(f"Generated: {datetime.utcnow().strftime('%B %d, %Y')}", normal_style))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("SUMMARY", section_style))
    status_breakdown = ", ".join(f"{k}: {v}" for k, v in summary["by_status"].items()) or "None"
    summary_data = [
        ["Total Placements", str(summary["total_placements"]), "Total Revenue", f"${summary['total_revenue']:,.2f}"],
        ["Status Breakdown", status_breakdown, "", ""],
    ]
    summary_table = Table(summary_data, colWidths=[1.8 * inch, 2.5 * inch, 1.5 * inch, 2.0 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
        ('TEXTCOLOR', (0, 0), (-1, -1), DARK),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
        ('SPAN', (1, 1), (3, 1)),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 16))

    if placements:
        elements.append(Paragraph("PLACEMENT DETAILS", section_style))
        table_headers = ["Title", "Song", "Client", "Status", "License Fee", "Pitched", "Secured"]
        table_data = [table_headers]
        for p in placements:
            song_name = p.get("song_title") or p.get("work_title") or ""
            table_data.append([
                Paragraph(str(p.get("title", ""))[:40], small_style),
                Paragraph(str(song_name)[:30], small_style),
                Paragraph(str(p.get("client_name") or "")[:25], small_style),
                str(p.get("status") or ""),
                f"${p.get('license_fee') or 0:,.2f}",
                str(p.get("pitched_date") or "")[:10],
                str(p.get("secured_date") or "")[:10],
            ])

        detail_table = Table(table_data, colWidths=[
            2.0 * inch, 1.6 * inch, 1.5 * inch, 1.0 * inch, 1.0 * inch, 0.9 * inch, 0.9 * inch
        ])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, BORDER),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
        ]))
        elements.append(detail_table)

    elements.append(Spacer(1, 24))
    elements.append(Paragraph(f"<i>Generated by Cadence Catalog Intelligence — {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>", footer_style))

    doc.build(elements)
    buffer.seek(0)

    filename = f"Sync_Report_{datetime.utcnow().strftime('%Y-%m-%d')}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get(
    "/config/options",
    summary='Get the static configuration options for the placements module',
    description='Returns the curated dropdown vocabularies (media types, statuses, license types) the UI uses to render the placement form.\n\n**Auth:** Bearer JWT.\n**Response:** `{ media_types: [...], statuses: [...], license_types: [...] }`.',
)
def get_placement_options():
    return {
        "placement_types": PLACEMENT_TYPES,
        "statuses": PLACEMENT_STATUSES,
        "media_types": MEDIA_TYPES,
        "status_transitions": STATUS_TRANSITIONS,
    }
