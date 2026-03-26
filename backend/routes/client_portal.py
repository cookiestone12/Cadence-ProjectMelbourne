from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional, List
from ..models import (
    get_db, User, OrganizationMember, Creator, Organization,
    Song, SongCredit, Work, WorkCredit, Contract, Placement,
    RoyaltyStatement, RoyaltyTransaction, AccountLink,
    ClientSharedContact, CreativeContact
)
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/client-portal", tags=["client-portal"])


def get_client_context(db: Session, current_user: User):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.role == "CLIENT"
    ).first()
    if not membership or not membership.linked_creator_id:
        raise HTTPException(status_code=403, detail="Not a client user or no linked creator")
    creator = db.query(Creator).filter(
        Creator.id == membership.linked_creator_id,
        Creator.organization_id == membership.organization_id
    ).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Linked creator not found in this organization")
    return membership, creator


@router.get("/me")
def get_client_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership, creator = get_client_context(db, current_user)
    org = db.query(Organization).filter(Organization.id == membership.organization_id).first()

    publisher_contact = None
    if creator.publisher_contact_id:
        pc = db.query(CreativeContact).filter(CreativeContact.id == creator.publisher_contact_id).first()
        if pc:
            publisher_contact = {"id": pc.id, "display_name": pc.display_name, "company": pc.publisher_name}

    admin_contact = None
    if creator.admin_contact_id:
        ac = db.query(CreativeContact).filter(CreativeContact.id == creator.admin_contact_id).first()
        if ac:
            admin_contact = {"id": ac.id, "display_name": ac.display_name, "company": ac.publisher_name}

    return {
        "creator_id": creator.id,
        "organization_id": membership.organization_id,
        "organization_name": (org.display_name or org.name) if org else None,
        "role": membership.role,
        "client_access_scope": getattr(membership, 'client_access_scope', 'OWN') or 'OWN',
        "creator": {
            "id": creator.id,
            "display_name": creator.display_name,
            "legal_name": creator.legal_name,
            "email": creator.email,
            "roles": creator.roles or [],
            "primary_territory": creator.primary_territory,
            "primary_pro": creator.primary_pro,
            "primary_ipi": creator.primary_ipi,
            "hero_image_url": creator.hero_image_url,
            "contributor_type": creator.contributor_type,
            "phone": creator.phone,
            "publisher_name": creator.publisher_name,
            "publisher_contact": publisher_contact,
            "admin_contact": admin_contact,
            "label_affiliation": creator.label_affiliation,
            "bio": creator.bio,
            "website_url": creator.website_url,
            "spotify_url": creator.spotify_url,
            "apple_music_url": creator.apple_music_url,
            "youtube_url": creator.youtube_url,
            "instagram_url": creator.instagram_url,
            "twitter_url": creator.twitter_url,
            "custom_links": creator.custom_links or [],
        }
    }


@router.get("/clients")
def list_client_profiles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership, creator = get_client_context(db, current_user)
    scope = getattr(membership, 'client_access_scope', 'OWN') or 'OWN'
    if scope != "ALL":
        raise HTTPException(status_code=403, detail="You do not have access to view other client profiles")

    client_members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == membership.organization_id,
        OrganizationMember.role == "CLIENT",
        OrganizationMember.linked_creator_id.isnot(None),
        OrganizationMember.user_id != current_user.id,
    ).all()

    profiles = []
    for cm in client_members:
        c = db.query(Creator).filter(Creator.id == cm.linked_creator_id).first()
        if c:
            profiles.append({
                "id": c.id,
                "display_name": c.display_name,
                "email": c.email,
                "roles": c.roles or [],
                "primary_territory": c.primary_territory,
                "primary_pro": c.primary_pro,
                "publisher_name": c.publisher_name,
                "hero_image_url": c.hero_image_url,
            })
    return {"clients": profiles}


class UpdateCreatorProfileRequest(BaseModel):
    display_name: Optional[str] = None
    legal_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    website_url: Optional[str] = None
    spotify_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    youtube_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    publisher_name: Optional[str] = None
    label_affiliation: Optional[str] = None
    primary_territory: Optional[str] = None
    primary_pro: Optional[str] = None
    primary_ipi: Optional[str] = None


@router.put("/profile")
def update_client_profile(
    request: UpdateCreatorProfileRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    _, creator = get_client_context(db, current_user)

    update_data = request.dict(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(creator, key):
            setattr(creator, key, value)

    db.commit()
    db.refresh(creator)
    return {"message": "Profile updated", "creator_id": creator.id}


@router.get("/catalog")
def get_client_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership, creator = get_client_context(db, current_user)
    org_id = membership.organization_id

    song_credits = db.query(SongCredit).filter(SongCredit.creator_id == creator.id).all()
    song_ids = [sc.song_id for sc in song_credits]

    songs = []
    if song_ids:
        song_rows = db.query(Song).filter(
            Song.id.in_(song_ids),
            Song.organization_id == org_id
        ).all()

        all_credits = db.query(SongCredit).filter(SongCredit.song_id.in_(song_ids)).all()
        creator_ids = list(set(c.creator_id for c in all_credits if c.creator_id))
        creators_map = {}
        if creator_ids:
            creators = db.query(Creator).filter(Creator.id.in_(creator_ids)).all()
            creators_map = {c.id: c.display_name for c in creators}

        credits_by_song = {}
        for c in all_credits:
            credits_by_song.setdefault(c.song_id, []).append({
                "id": c.id,
                "creator_id": c.creator_id,
                "creator_name": creators_map.get(c.creator_id, "Unknown"),
                "role": c.role,
                "share_percentage": c.share_percentage,
            })

        for s in song_rows:
            songs.append({
                "id": s.id,
                "title": s.title,
                "artist": s.primary_artist,
                "isrc": s.isrc,
                "release_date": str(s.release_date) if s.release_date else None,
                "status": getattr(s, 'status', None),
                "credits": credits_by_song.get(s.id, []),
            })

    work_credits = db.query(WorkCredit).filter(WorkCredit.creator_id == creator.id).all()
    work_ids = [wc.work_id for wc in work_credits]

    works = []
    if work_ids:
        work_rows = db.query(Work).filter(
            Work.id.in_(work_ids),
            Work.organization_id == org_id
        ).all()
        for w in work_rows:
            works.append({
                "id": w.id,
                "title": w.title,
                "work_type": getattr(w, 'work_type', None),
                "iswc": getattr(w, 'iswc', None),
            })

    return {"songs": songs, "works": works}


@router.get("/placements")
def get_client_placements(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership, creator = get_client_context(db, current_user)
    org_id = membership.organization_id

    song_credits = db.query(SongCredit).filter(SongCredit.creator_id == creator.id).all()
    song_ids = [sc.song_id for sc in song_credits]

    work_credits = db.query(WorkCredit).filter(WorkCredit.creator_id == creator.id).all()
    work_ids = [wc.work_id for wc in work_credits]

    placements = db.query(Placement).filter(
        Placement.organization_id == org_id
    ).all()

    result = []
    for p in placements:
        if p.song_id in song_ids or p.work_id in work_ids:
            result.append({
                "id": p.id,
                "title": p.title,
                "description": p.description,
                "placement_type": p.placement_type,
                "status": p.status,
                "client_name": p.client_name,
                "project_name": p.project_name,
                "media_type": p.media_type,
                "license_fee": p.license_fee,
                "license_currency": p.license_currency,
                "created_at": str(p.created_at) if p.created_at else None,
            })

    return result


@router.get("/contracts")
def get_client_contracts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership, creator = get_client_context(db, current_user)
    org_id = membership.organization_id

    contracts = db.query(Contract).filter(
        Contract.organization_id == org_id,
        Contract.creator_id == creator.id
    ).all()

    result = []
    for c in contracts:
        result.append({
            "id": c.id,
            "title": c.title,
            "contract_type": c.contract_type,
            "status": c.status,
            "start_date": str(c.start_date) if c.start_date else None,
            "end_date": str(c.end_date) if c.end_date else None,
            "advance_amount": c.advance_amount,
            "advance_currency": c.advance_currency,
            "advance_recouped": c.advance_recouped,
            "notes": c.notes,
        })

    return result


@router.get("/accounting")
def get_client_accounting(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership, creator = get_client_context(db, current_user)
    org_id = membership.organization_id

    song_credits = db.query(SongCredit).filter(SongCredit.creator_id == creator.id).all()
    song_ids = [sc.song_id for sc in song_credits]

    transactions = []
    if song_ids:
        tx_rows = db.query(RoyaltyTransaction).filter(
            RoyaltyTransaction.organization_id == org_id,
            RoyaltyTransaction.song_id.in_(song_ids)
        ).all()
        for tx in tx_rows:
            transactions.append({
                "id": tx.id,
                "original_track_title": tx.original_track_title,
                "original_artist": tx.original_artist,
                "song_id": tx.song_id,
                "match_status": tx.match_status,
                "match_confidence": tx.match_confidence,
                "revenue_amount_cents": tx.revenue_cents or 0,
                "platform": tx.platform,
            })

    contracts = db.query(Contract).filter(
        Contract.organization_id == org_id,
        Contract.creator_id == creator.id
    ).all()

    advances = []
    for c in contracts:
        if c.advance_amount and c.advance_amount > 0:
            advances.append({
                "contract_id": c.id,
                "contract_title": c.title,
                "advance_amount": c.advance_amount,
                "advance_recouped": c.advance_recouped or 0,
                "currency": c.advance_currency,
                "remaining": (c.advance_amount or 0) - (c.advance_recouped or 0),
            })

    total_tx_revenue = sum(t.get("revenue_amount_cents", 0) or 0 for t in transactions)

    if total_tx_revenue == 0:
        creator_statements = db.query(RoyaltyStatement).filter(
            RoyaltyStatement.organization_id == org_id,
            RoyaltyStatement.creator_id == creator.id,
            RoyaltyStatement.status.in_(["PROCESSED", "PARTIALLY_MATCHED", "FULLY_MATCHED"]),
        ).all()
        statement_revenue = sum(s.total_revenue_cents or 0 for s in creator_statements)
        total_tx_revenue = max(total_tx_revenue, statement_revenue)

    return {
        "transactions": transactions,
        "advances": advances,
        "total_revenue_cents": total_tx_revenue,
    }


class GrantAccessRequest(BaseModel):
    access_code: str
    permission_level: str = "VIEW_ONLY"


@router.get("/managed-access")
def get_managed_access(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership, creator = get_client_context(db, current_user)
    org_id = membership.organization_id

    links = db.query(AccountLink).filter(
        AccountLink.individual_org_id == org_id,
        AccountLink.status.in_(["ACTIVE", "PENDING"])
    ).all()

    result = []
    for link in links:
        enterprise_org = db.query(Organization).filter(Organization.id == link.enterprise_org_id).first()
        result.append({
            "id": link.id,
            "enterprise_org_id": link.enterprise_org_id,
            "enterprise_org_name": enterprise_org.name if enterprise_org else "Unknown",
            "permission_level": link.permission_level,
            "status": link.status,
            "created_at": str(link.created_at) if link.created_at else None,
        })

    return result


@router.post("/grant-access")
def grant_access(
    request: GrantAccessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership, creator = get_client_context(db, current_user)
    org_id = membership.organization_id

    if request.permission_level not in ["VIEW_ONLY", "EDIT", "FULL_ACCESS"]:
        raise HTTPException(status_code=400, detail="Invalid permission level")

    enterprise_org = db.query(Organization).filter(
        func.upper(Organization.access_code) == request.access_code.strip().upper()
    ).first()
    if not enterprise_org:
        raise HTTPException(status_code=404, detail="Invalid access code")

    if enterprise_org.id == org_id:
        raise HTTPException(status_code=400, detail="Cannot grant access to your own organization")

    existing = db.query(AccountLink).filter(
        AccountLink.individual_org_id == org_id,
        AccountLink.enterprise_org_id == enterprise_org.id,
        AccountLink.status.in_(["ACTIVE", "PENDING"])
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Access already granted to this organization")

    link = AccountLink(
        individual_org_id=org_id,
        enterprise_org_id=enterprise_org.id,
        status="PENDING",
        permission_level=request.permission_level,
        initiated_by="INDIVIDUAL",
        individual_consent=True,
        enterprise_consent=False,
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    return {"message": "Access request sent — pending company approval", "link_id": link.id}


@router.put("/revoke-access/{link_id}")
def revoke_access(
    link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership, creator = get_client_context(db, current_user)
    org_id = membership.organization_id

    link = db.query(AccountLink).filter(
        AccountLink.id == link_id,
        AccountLink.individual_org_id == org_id
    ).first()
    if not link:
        raise HTTPException(status_code=404, detail="Access link not found")

    link.status = "REVOKED"
    db.commit()

    return {"message": "Access revoked"}


@router.get("/shared-contacts")
def get_shared_contacts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership, creator = get_client_context(db, current_user)
    org_id = membership.organization_id

    shares = db.query(ClientSharedContact).filter(
        ClientSharedContact.organization_id == org_id,
        ClientSharedContact.shared_with_user_id == current_user.id,
    ).all()

    contact_ids = [s.creative_contact_id for s in shares]
    if not contact_ids:
        return {"contacts": [], "total": 0}

    contacts = db.query(CreativeContact).filter(
        CreativeContact.id.in_(contact_ids),
    ).order_by(CreativeContact.display_name).all()

    def contact_to_dict(contact):
        return {
            "id": contact.id,
            "organization_id": contact.organization_id,
            "creator_id": contact.creator_id,
            "display_name": contact.display_name,
            "legal_name": contact.legal_name,
            "email": contact.email,
            "phone": contact.phone,
            "pro": contact.pro,
            "ipi": contact.ipi,
            "isni": contact.isni,
            "publisher_name": contact.publisher_name,
            "publisher_ipi": contact.publisher_ipi,
            "publisher_pro": contact.publisher_pro,
            "roles": contact.roles or [],
            "representation_name": contact.representation_name,
            "representation_email": contact.representation_email,
            "representation_phone": contact.representation_phone,
            "territory": contact.territory,
            "notes": contact.notes,
            "created_at": contact.created_at.isoformat() if contact.created_at else None,
            "updated_at": contact.updated_at.isoformat() if contact.updated_at else None,
        }

    return {"contacts": [contact_to_dict(c) for c in contacts], "total": len(contacts)}
