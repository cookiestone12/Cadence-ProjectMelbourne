from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional, Dict
from ..models import get_db, Creator, CreativeContact, CreatorContact, Organization, OrganizationMember, User, Song, SongCredit, WorkCredit, ClientShare
from ..utils.auth import get_current_user
from .client_sharing import has_shared_access
import os
import uuid
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("cadence")

router = APIRouter(prefix="/api/creators", tags=["creators"])

class CreatorResponse(BaseModel):
    id: int
    organization_id: Optional[int] = None
    display_name: str
    legal_name: Optional[str]
    email: Optional[str]
    roles: List[str]
    primary_territory: Optional[str]
    primary_pro: Optional[str]
    primary_ipi: Optional[str]
    hero_image_url: Optional[str]
    linked_user_id: Optional[int]
    song_count: Optional[int] = 0
    avg_health_score: Optional[float] = 0.0
    bio: Optional[str] = None
    spotify_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    youtube_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    website_url: Optional[str] = None
    custom_links: Optional[List[dict]] = None
    roster_export_fields: Optional[List[str]] = None
    shared: Optional[bool] = None
    shared_from: Optional[str] = None
    
    class Config:
        from_attributes = True

class CreatorCreateRequest(BaseModel):
    display_name: str
    legal_name: Optional[str] = None
    email: Optional[str] = None
    roles: List[str]
    primary_territory: Optional[str] = None
    primary_pro: Optional[str] = None
    primary_ipi: Optional[str] = None
    hero_image_url: Optional[str] = None
    bio: Optional[str] = None
    spotify_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    youtube_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    website_url: Optional[str] = None
    custom_links: Optional[List[dict]] = None
    roster_export_fields: Optional[List[str]] = None

class CreatorUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    legal_name: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[List[str]] = None
    primary_territory: Optional[str] = None
    primary_pro: Optional[str] = None
    primary_ipi: Optional[str] = None
    hero_image_url: Optional[str] = None
    publisher_contact_id: Optional[int] = None
    admin_contact_id: Optional[int] = None
    bio: Optional[str] = None
    spotify_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    youtube_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    website_url: Optional[str] = None
    custom_links: Optional[List[dict]] = None
    roster_export_fields: Optional[List[str]] = None

class CreatorDetailResponse(BaseModel):
    id: int
    organization_id: Optional[int] = None
    display_name: str
    legal_name: Optional[str]
    email: Optional[str]
    roles: List[str]
    primary_territory: Optional[str]
    primary_pro: Optional[str]
    primary_ipi: Optional[str]
    hero_image_url: Optional[str]
    linked_user_id: Optional[int]
    song_count: int
    avg_health_score: float
    placement_count: int
    publisher_contact_id: Optional[int] = None
    publisher_contact: Optional[dict] = None
    admin_contact_id: Optional[int] = None
    admin_contact: Optional[dict] = None
    bio: Optional[str] = None
    spotify_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    youtube_url: Optional[str] = None
    instagram_url: Optional[str] = None
    twitter_url: Optional[str] = None
    custom_links: Optional[List[dict]] = None
    roster_export_fields: Optional[List[str]] = None
    is_shared: Optional[bool] = False
    
    class Config:
        from_attributes = True

@router.get("/org/{org_id}", response_model=List[CreatorResponse])
def get_organization_creators(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        user_membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id
        ).first()
        has_share = False
        if user_membership:
            has_share = db.query(ClientShare).filter(
                ClientShare.recipient_org_id == user_membership.organization_id,
                ClientShare.primary_org_id == org_id,
                ClientShare.status == "ACCEPTED"
            ).first() is not None
        if not has_share:
            raise HTTPException(status_code=403, detail="Not authorized to access this organization")
    
    creators = db.query(Creator).filter(Creator.organization_id == org_id).all()
    
    all_shares_for_org = db.query(ClientShare).filter(
        ClientShare.recipient_org_id == org_id
    ).all()
    logger.info(f"[ROSTER DEBUG] org_id={org_id}, local_creators={len(creators)}, all_shares_for_org={len(all_shares_for_org)}")
    for s in all_shares_for_org:
        logger.info(f"[ROSTER DEBUG]   share id={s.id} creator_id={s.creator_id} primary_org={s.primary_org_id} recipient_org={s.recipient_org_id} status={s.status}")

    shared_shares = [s for s in all_shares_for_org if s.status == "ACCEPTED"]
    shared_creator_ids = [s.creator_id for s in shared_shares]
    logger.info(f"[ROSTER DEBUG] accepted_shares={len(shared_shares)}, shared_creator_ids={shared_creator_ids}")
    shared_creators = []
    if shared_creator_ids:
        own_ids = {c.id for c in creators}
        shared_creators = db.query(Creator).filter(
            Creator.id.in_(shared_creator_ids),
            ~Creator.id.in_(own_ids) if own_ids else True
        ).all()
        logger.info(f"[ROSTER DEBUG] shared_creators_loaded={len(shared_creators)}, names={[c.display_name for c in shared_creators]}")
    
    all_creators = creators + shared_creators
    shared_id_set = set(shared_creator_ids)
    
    shared_org_names = {}
    if shared_shares:
        primary_org_ids = {s.primary_org_id for s in shared_shares}
        orgs = db.query(Organization).filter(Organization.id.in_(primary_org_ids)).all()
        org_name_map = {o.id: o.name for o in orgs}
        for s in shared_shares:
            shared_org_names[s.creator_id] = org_name_map.get(s.primary_org_id)
    
    creator_ids = [creator.id for creator in all_creators]
    
    creator_org_map = {c.id: c.organization_id for c in all_creators}

    local_creator_ids = [c.id for c in creators]
    shared_creator_ids_in_list = [c.id for c in shared_creators]

    count_map = {}
    if local_creator_ids:
        local_counts = db.query(SongCredit.creator_id, func.count(SongCredit.id)).join(
            Song, Song.id == SongCredit.song_id
        ).filter(
            SongCredit.creator_id.in_(local_creator_ids),
            Song.organization_id == org_id
        ).group_by(SongCredit.creator_id).all()
        for cid, cnt in local_counts:
            count_map[cid] = cnt

    if shared_creator_ids_in_list:
        for sc in shared_creators:
            sc_count = db.query(func.count(SongCredit.id)).join(
                Song, Song.id == SongCredit.song_id
            ).filter(
                SongCredit.creator_id == sc.id,
                Song.organization_id == sc.organization_id
            ).scalar() or 0
            count_map[sc.id] = sc_count
    
    avgs = db.query(SongCredit.creator_id, func.avg(Song.status_health_score)).join(
        Song, Song.id == SongCredit.song_id
    ).filter(
        SongCredit.creator_id.in_(creator_ids)
    ).group_by(SongCredit.creator_id).all()
    avg_map = {cid: float(avg) if avg else 0.0 for cid, avg in avgs}
    
    shared_names = {c.display_name.strip().lower() for c in shared_creators} if shared_creators else set()

    result = []
    for creator in all_creators:
        song_count = count_map.get(creator.id, 0)
        avg_health = avg_map.get(creator.id, 0.0)
        is_shared = creator.id in shared_id_set

        if not is_shared and song_count == 0 and creator.display_name.strip().lower() in shared_names:
            continue
        
        entry = {
            "id": creator.id,
            "organization_id": creator.organization_id,
            "display_name": creator.display_name,
            "legal_name": creator.legal_name,
            "email": creator.email,
            "roles": creator.roles,
            "primary_territory": creator.primary_territory,
            "primary_pro": creator.primary_pro,
            "primary_ipi": creator.primary_ipi,
            "hero_image_url": creator.hero_image_url,
            "linked_user_id": creator.linked_user_id,
            "song_count": song_count,
            "avg_health_score": float(avg_health) if avg_health else 0.0,
            "bio": creator.bio,
            "spotify_url": creator.spotify_url,
            "apple_music_url": creator.apple_music_url,
            "youtube_url": creator.youtube_url,
            "instagram_url": creator.instagram_url,
            "twitter_url": creator.twitter_url,
            "website_url": creator.website_url,
            "custom_links": creator.custom_links or [],
            "roster_export_fields": creator.roster_export_fields or [],
        }
        if is_shared:
            entry["shared"] = True
            entry["shared_from"] = shared_org_names.get(creator.id)
        result.append(entry)
    
    return result

def check_roster_permission(membership):
    if membership.role in ("OWNER", "ADMIN"):
        return True
    return getattr(membership, 'can_manage_roster', False) or False

@router.post("/org/{org_id}", response_model=CreatorResponse)
def create_creator(
    org_id: int,
    request: CreatorCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this organization")

    if not check_roster_permission(membership):
        raise HTTPException(status_code=403, detail="You do not have permission to manage the roster")
    
    creator = Creator(
        organization_id=org_id,
        display_name=request.display_name,
        legal_name=request.legal_name,
        email=request.email,
        roles=request.roles,
        primary_territory=request.primary_territory,
        primary_pro=request.primary_pro,
        primary_ipi=request.primary_ipi,
        hero_image_url=request.hero_image_url,
        bio=request.bio,
        spotify_url=request.spotify_url,
        apple_music_url=request.apple_music_url,
        youtube_url=request.youtube_url,
        instagram_url=request.instagram_url,
        twitter_url=request.twitter_url,
        website_url=request.website_url,
        custom_links=request.custom_links or [],
        roster_export_fields=request.roster_export_fields or [],
    )
    db.add(creator)
    db.flush()
    from ..services.audit_service import log_action
    log_action(db, org_id, current_user.id, "CREATE", "CREATOR", creator.id, creator.display_name)
    db.commit()
    db.refresh(creator)

    creative_contact = CreativeContact(
        organization_id=org_id,
        creator_id=creator.id,
        display_name=creator.display_name,
        legal_name=creator.legal_name,
        email=creator.email,
        pro=creator.primary_pro,
        ipi=creator.primary_ipi,
        publisher_name=creator.publisher_name,
        roles=creator.roles or [],
        phone=creator.phone,
        territory=creator.primary_territory,
    )
    db.add(creative_contact)
    db.commit()
    
    return {
        "id": creator.id,
        "display_name": creator.display_name,
        "legal_name": creator.legal_name,
        "email": creator.email,
        "roles": creator.roles,
        "primary_territory": creator.primary_territory,
        "primary_pro": creator.primary_pro,
        "primary_ipi": creator.primary_ipi,
        "hero_image_url": creator.hero_image_url,
        "linked_user_id": creator.linked_user_id,
        "song_count": 0,
        "avg_health_score": 0.0,
        "roster_export_fields": creator.roster_export_fields or [],
    }

@router.get("/{creator_id}", response_model=CreatorDetailResponse)
def get_creator(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == creator.organization_id
    ).first()
    
    is_shared = False
    if not membership:
        share = has_shared_access(db, current_user.id, creator_id)
        logger.info(f"[CREATOR DEBUG] creator_id={creator_id}, org={creator.organization_id}, user_org=?, shared_access={share is not None}")
        if not share:
            raise HTTPException(status_code=403, detail="Not authorized to access this creator")
        is_shared = True
    else:
        logger.info(f"[CREATOR DEBUG] creator_id={creator_id}, org={creator.organization_id}, user_org={membership.organization_id}, is_own=True")
    
    song_count = db.query(func.count(SongCredit.id)).join(
        Song, Song.id == SongCredit.song_id
    ).filter(
        SongCredit.creator_id == creator.id,
        Song.organization_id == creator.organization_id
    ).scalar() or 0
    
    creator_songs = db.query(Song).join(
        SongCredit, Song.id == SongCredit.song_id
    ).filter(
        SongCredit.creator_id == creator.id,
        Song.organization_id == creator.organization_id
    ).all()
    try:
        from ..utils.health_sync import ensure_songs_health
        ensure_songs_health(db, creator_songs)
    except Exception:
        pass
    avg_health = sum(s.status_health_score or 0 for s in creator_songs) / len(creator_songs) if creator_songs else 0.0
    
    placement_count = db.query(func.count(Song.id)).join(
        SongCredit, Song.id == SongCredit.song_id
    ).filter(
        SongCredit.creator_id == creator.id,
        Song.organization_id == creator.organization_id,
        Song.is_paid == "Yes"
    ).scalar() or 0
    
    publisher_contact = None
    if creator.publisher_contact_id:
        pc = db.query(CreativeContact).filter(CreativeContact.id == creator.publisher_contact_id).first()
        if pc:
            publisher_contact = {"id": pc.id, "display_name": pc.display_name, "company": pc.publisher_name, "primary_role": (pc.roles or [None])[0] if pc.roles else None}
    
    admin_contact = None
    if creator.admin_contact_id:
        ac = db.query(CreativeContact).filter(CreativeContact.id == creator.admin_contact_id).first()
        if ac:
            admin_contact = {"id": ac.id, "display_name": ac.display_name, "company": ac.publisher_name, "primary_role": (ac.roles or [None])[0] if ac.roles else None}
    
    return {
        "id": creator.id,
        "organization_id": creator.organization_id,
        "display_name": creator.display_name,
        "legal_name": creator.legal_name,
        "email": creator.email,
        "roles": creator.roles,
        "primary_territory": creator.primary_territory,
        "primary_pro": creator.primary_pro,
        "primary_ipi": creator.primary_ipi,
        "hero_image_url": creator.hero_image_url,
        "linked_user_id": creator.linked_user_id,
        "song_count": song_count,
        "avg_health_score": float(avg_health) if avg_health else 0.0,
        "placement_count": placement_count,
        "publisher_contact_id": creator.publisher_contact_id,
        "publisher_contact": publisher_contact,
        "admin_contact_id": creator.admin_contact_id,
        "admin_contact": admin_contact,
        "bio": creator.bio,
        "spotify_url": creator.spotify_url,
        "apple_music_url": creator.apple_music_url,
        "youtube_url": creator.youtube_url,
        "instagram_url": creator.instagram_url,
        "twitter_url": creator.twitter_url,
        "website_url": creator.website_url,
        "custom_links": creator.custom_links or [],
        "roster_export_fields": creator.roster_export_fields or [],
        "is_shared": is_shared,
    }

@router.put("/{creator_id}", response_model=CreatorResponse)
def update_creator(
    creator_id: int,
    request: CreatorUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == creator.organization_id
    ).first()
    
    if not membership:
        if not has_shared_access(db, current_user.id, creator_id):
            raise HTTPException(status_code=403, detail="Not authorized to update this creator")

    if membership and not check_roster_permission(membership):
        raise HTTPException(status_code=403, detail="You do not have permission to manage the roster")
    
    if request.display_name is not None:
        creator.display_name = request.display_name
    if request.legal_name is not None:
        creator.legal_name = request.legal_name
    if request.email is not None:
        creator.email = request.email
    if request.roles is not None:
        creator.roles = request.roles
    if request.primary_territory is not None:
        creator.primary_territory = request.primary_territory
    if request.primary_pro is not None:
        creator.primary_pro = request.primary_pro
    if request.primary_ipi is not None:
        creator.primary_ipi = request.primary_ipi
    if request.hero_image_url is not None:
        creator.hero_image_url = request.hero_image_url
    if request.publisher_contact_id is not None:
        creator.publisher_contact_id = request.publisher_contact_id if request.publisher_contact_id != 0 else None
    if request.admin_contact_id is not None:
        creator.admin_contact_id = request.admin_contact_id if request.admin_contact_id != 0 else None
    if request.bio is not None:
        creator.bio = request.bio
    if request.spotify_url is not None:
        creator.spotify_url = request.spotify_url
    if request.apple_music_url is not None:
        creator.apple_music_url = request.apple_music_url
    if request.youtube_url is not None:
        creator.youtube_url = request.youtube_url
    if request.instagram_url is not None:
        creator.instagram_url = request.instagram_url
    if request.twitter_url is not None:
        creator.twitter_url = request.twitter_url
    if request.website_url is not None:
        creator.website_url = request.website_url
    if request.custom_links is not None:
        creator.custom_links = request.custom_links
    if request.roster_export_fields is not None:
        creator.roster_export_fields = request.roster_export_fields
    
    from ..services.audit_service import log_action
    log_action(db, creator.organization_id, current_user.id, "UPDATE", "CREATOR", creator.id, creator.display_name)

    linked_contact = db.query(CreativeContact).filter(
        CreativeContact.creator_id == creator.id,
        CreativeContact.organization_id == creator.organization_id
    ).first()
    if linked_contact:
        sync_fields = {
            'display_name': 'display_name',
            'legal_name': 'legal_name',
            'email': 'email',
            'roles': 'roles',
            'primary_pro': 'pro',
            'primary_ipi': 'ipi',
            'primary_territory': 'territory',
        }
        for creator_field, contact_field in sync_fields.items():
            val = getattr(request, creator_field, None)
            if val is not None:
                setattr(linked_contact, contact_field, val)

    db.commit()
    db.refresh(creator)
    
    song_count = db.query(func.count(SongCredit.id)).filter(
        SongCredit.creator_id == creator.id
    ).scalar() or 0
    
    avg_health = db.query(func.avg(Song.status_health_score)).join(
        SongCredit, Song.id == SongCredit.song_id
    ).filter(
        SongCredit.creator_id == creator.id
    ).scalar() or 0.0
    
    return {
        "id": creator.id,
        "display_name": creator.display_name,
        "legal_name": creator.legal_name,
        "email": creator.email,
        "roles": creator.roles,
        "primary_territory": creator.primary_territory,
        "primary_pro": creator.primary_pro,
        "primary_ipi": creator.primary_ipi,
        "hero_image_url": creator.hero_image_url,
        "linked_user_id": creator.linked_user_id,
        "song_count": song_count,
        "avg_health_score": float(avg_health) if avg_health else 0.0,
        "roster_export_fields": creator.roster_export_fields or [],
    }


@router.delete("/{creator_id}")
def delete_creator(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == creator.organization_id
    ).first()
    if not membership and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not check_roster_permission(membership):
        raise HTTPException(status_code=403, detail="You do not have permission to manage the roster")

    db.query(SongCredit).filter(SongCredit.creator_id == creator_id).delete()
    db.query(WorkCredit).filter(WorkCredit.creator_id == creator_id).delete()

    db.query(CreativeContact).filter(
        CreativeContact.creator_id == creator_id,
        CreativeContact.organization_id == creator.organization_id
    ).delete()

    from ..services.audit_service import log_action
    log_action(db, creator.organization_id, current_user.id, "DELETE", "CREATOR", creator.id, creator.display_name)
    db.delete(creator)
    db.commit()
    return {"message": "Creator deleted successfully"}


UPLOADS_DIR = Path(__file__).parent.parent / "uploads" / "creators"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


@router.get("/{creator_id}/image")
def serve_creator_image(
    creator_id: int,
    db: Session = Depends(get_db),
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    if creator.hero_image_data:
        return Response(
            content=creator.hero_image_data,
            media_type=creator.hero_image_mime or "image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"}
        )

    if creator.hero_image_url and creator.hero_image_url.startswith("/uploads/"):
        filename = creator.hero_image_url.split("/")[-1]
        filepath = UPLOADS_DIR / filename
        if filepath.exists():
            mime = "image/jpeg"
            if filename.endswith(".png"):
                mime = "image/png"
            elif filename.endswith(".webp"):
                mime = "image/webp"
            elif filename.endswith(".gif"):
                mime = "image/gif"
            return Response(
                content=filepath.read_bytes(),
                media_type=mime,
                headers={"Cache-Control": "public, max-age=3600"}
            )

    raise HTTPException(status_code=404, detail="No image found")


@router.post("/{creator_id}/image")
async def upload_creator_image(
    creator_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == creator.organization_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")

    if not check_roster_permission(membership):
        raise HTTPException(status_code=403, detail="You do not have permission to manage the roster")

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Invalid image type. Use JPEG, PNG, WebP, or GIF.")

    content = await file.read()
    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(status_code=400, detail="Image too large. Maximum size is 5MB.")

    creator.hero_image_data = content
    creator.hero_image_mime = file.content_type
    creator.hero_image_url = f"/api/creators/{creator_id}/image"
    db.commit()
    db.refresh(creator)

    return {"hero_image_url": creator.hero_image_url}


class RosterPDFRequest(BaseModel):
    creator_ids: List[int]
    field_overrides: Optional[Dict[str, List[str]]] = None


@router.post("/org/{org_id}/roster-pdf")
def export_roster_pdf(
    org_id: int,
    request: RosterPDFRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    org_name = org.display_name or org.name if org else "Organization"

    creators = db.query(Creator).filter(
        Creator.id.in_(request.creator_ids),
        Creator.organization_id == org_id
    ).all()
    if not creators:
        raise HTTPException(status_code=404, detail="No creators found")
    
    try:
        return _build_roster_pdf(creators, org_name, request)
    except Exception as e:
        logger.error(f"Failed to generate roster PDF: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


def _build_roster_pdf(creators, org_name, request):

    import io
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, KeepTogether, Table, TableStyle
    from reportlab.graphics.shapes import Drawing, Circle, String

    buffer = io.BytesIO()
    page_w, page_h = letter

    sage = colors.HexColor("#5B8A72")
    dark_text = colors.HexColor("#3D4A44")
    muted_text = colors.HexColor("#7A8580")
    light_bg = colors.HexColor("#F5F7F4")
    border_color = colors.HexColor("#E0E5E2")

    class RosterTemplate:
        def on_page(self, canvas, doc):
            canvas.saveState()
            grad_steps = 20
            for i in range(grad_steps):
                frac = i / grad_steps
                r = 0.357 + frac * (0.961 - 0.357)
                g = 0.541 + frac * (0.969 - 0.541)
                b = 0.447 + frac * (0.957 - 0.447)
                step_h = (1.6*inch) / grad_steps
                y = page_h - (i+1) * step_h
                canvas.setFillColor(colors.Color(r, g, b))
                canvas.rect(0, y, page_w, step_h + 1, fill=True, stroke=False)

            canvas.setFillColor(colors.white)
            canvas.setFont("Helvetica-Bold", 22)
            canvas.drawString(0.75*inch, page_h - 0.8*inch, f"{org_name}")
            canvas.setFont("Helvetica", 11)
            canvas.drawString(0.75*inch, page_h - 1.1*inch, "Roster Brief")
            canvas.setFont("Helvetica", 8)
            canvas.drawRightString(page_w - 0.75*inch, page_h - 0.5*inch, f"{len(creators)} Creator{'s' if len(creators) != 1 else ''}")

            canvas.setFillColor(muted_text)
            canvas.setFont("Helvetica", 7)
            canvas.drawCentredString(page_w/2, 0.4*inch, f"Generated by {org_name} via Cadence Catalog Intelligence | {datetime.utcnow().strftime('%B %d, %Y')}")
            canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=1.8*inch, bottomMargin=0.8*inch,
        leftMargin=0.75*inch, rightMargin=0.75*inch
    )

    name_style = ParagraphStyle('Name', fontName='Helvetica-Bold', fontSize=16, textColor=dark_text, spaceAfter=2, leading=20)
    bio_style = ParagraphStyle('Bio', fontName='Helvetica', fontSize=9, textColor=muted_text, spaceAfter=6, leading=13)
    label_style = ParagraphStyle('Label', fontName='Helvetica', fontSize=7, textColor=muted_text, spaceAfter=1, leading=9)
    link_style = ParagraphStyle('Link', fontName='Helvetica', fontSize=9, textColor=sage, spaceAfter=4, leading=12)
    role_style = ParagraphStyle('Role', fontName='Helvetica', fontSize=8, textColor=sage, spaceAfter=4, leading=10)
    pill_style = ParagraphStyle('Pill', fontName='Helvetica-Bold', fontSize=7, textColor=colors.white, leading=9, alignment=1)

    elements = []

    id_order = {cid: idx for idx, cid in enumerate(request.creator_ids)}
    creators.sort(key=lambda c: id_order.get(c.id, 999))

    link_colors = {
        'spotify_url': ('#1DB954', 'Spotify'),
        'apple_music_url': ('#FA233B', 'Apple Music'),
        'youtube_url': ('#FF0000', 'YouTube'),
        'instagram_url': ('#E1306C', 'Instagram'),
        'twitter_url': ('#000000', 'X'),
        'website_url': ('#5B8A72', 'Website'),
    }

    for idx, creator in enumerate(creators):
        card_elements = []
        if request.field_overrides and str(creator.id) in request.field_overrides:
            export_fields = request.field_overrides[str(creator.id)]
            show_all = False
        else:
            export_fields = creator.roster_export_fields or []
            show_all = len(export_fields) == 0

        if idx > 0:
            card_elements.append(Spacer(1, 16))

        photo_cell = None
        if creator.hero_image_data:
            try:
                img_buf = io.BytesIO(creator.hero_image_data)
                from PIL import Image as PILImage
                pil_img = PILImage.open(img_buf)
                pil_img.verify()
                img_buf.seek(0)
                photo_cell = RLImage(img_buf, width=0.9*inch, height=0.9*inch)
            except Exception:
                photo_cell = None
        if not photo_cell and creator.hero_image_url:
            try:
                import os
                url = creator.hero_image_url
                if url.startswith('/uploads/'):
                    file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), url.lstrip('/'))
                    if os.path.exists(file_path):
                        photo_cell = RLImage(file_path, width=0.9*inch, height=0.9*inch)
            except Exception:
                photo_cell = None

        if not photo_cell:
            d = Drawing(65, 65)
            d.add(Circle(32.5, 32.5, 30, fillColor=sage, strokeColor=colors.transparent, strokeWidth=0))
            initials = ""
            parts = creator.display_name.split()
            if len(parts) >= 2:
                initials = parts[0][0].upper() + parts[-1][0].upper()
            elif parts:
                initials = parts[0][0].upper()
            d.add(String(32.5, 25, initials, fontSize=22, fillColor=colors.white, textAnchor='middle', fontName='Helvetica-Bold'))
            photo_cell = d

        info_parts = []
        info_parts.append(Paragraph(creator.display_name, name_style))

        if creator.roles:
            role_text = " · ".join(creator.roles)
            info_parts.append(Paragraph(role_text, role_style))

        if (show_all or 'bio' in export_fields) and creator.bio:
            bio_text = creator.bio[:215] + ("..." if len(creator.bio) > 215 else "")
            info_parts.append(Paragraph(bio_text, bio_style))

        pill_cells = []
        pill_bg_colors = []

        for field_key, (bg_hex, label) in link_colors.items():
            url_val = getattr(creator, field_key, None)
            if url_val and (show_all or field_key in export_fields):
                pill_para = Paragraph(f'<a href="{url_val}" color="#FFFFFF">{label}</a>', pill_style)
                pill_cells.append(pill_para)
                pill_bg_colors.append(colors.HexColor(bg_hex))

        custom = creator.custom_links or []
        for ci, cl in enumerate(custom):
            cl_name = cl.get("name", "Link")
            cl_url = cl.get("url", "")
            cl_key = f"custom_link_{ci}"
            if cl_url and (show_all or 'custom_links' in export_fields or cl_key in export_fields):
                pill_para = Paragraph(f'<a href="{cl_url}" color="#FFFFFF">{cl_name}</a>', pill_style)
                pill_cells.append(pill_para)
                pill_bg_colors.append(colors.HexColor("#7A8580"))

        if pill_cells:
            max_per_row = 5
            rows = []
            row_colors = []
            for i in range(0, len(pill_cells), max_per_row):
                row = pill_cells[i:i+max_per_row]
                rc = pill_bg_colors[i:i+max_per_row]
                while len(row) < max_per_row:
                    row.append('')
                    rc.append(colors.transparent)
                rows.append(row)
                row_colors.append(rc)

            col_w = (page_w - 2.5*inch - 1.1*inch - 12) / max_per_row
            pill_table_style = [
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TOPPADDING', (0, 0), (-1, -1), 4),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('ROUNDEDCORNERS', [4, 4, 4, 4]),
            ]
            for ri, rc in enumerate(row_colors):
                for ci_idx, bg_c in enumerate(rc):
                    if bg_c != colors.transparent:
                        pill_table_style.append(('BACKGROUND', (ci_idx, ri), (ci_idx, ri), bg_c))

            pill_table = Table(rows, colWidths=[col_w]*max_per_row, style=TableStyle(pill_table_style))
            info_parts.append(Spacer(1, 4))
            info_parts.append(pill_table)

        from reportlab.platypus import TableStyle as TS
        info_cell = []
        for p in info_parts:
            info_cell.append(p)

        card_table = Table(
            [[photo_cell, info_cell]],
            colWidths=[1.1*inch, page_w - 2.5*inch - 1.1*inch],
            style=TS([
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (0, 0), 0),
                ('LEFTPADDING', (1, 0), (1, 0), 12),
                ('RIGHTPADDING', (-1, -1), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ])
        )
        card_elements.append(card_table)

        if idx < len(creators) - 1:
            from reportlab.graphics.shapes import Drawing as D, Line
            sep = D(page_w - 1.5*inch, 1)
            sep.add(Line(0, 0, page_w - 1.5*inch, 0, strokeColor=border_color, strokeWidth=0.5))
            card_elements.append(sep)

        elements.append(KeepTogether(card_elements))

    tmpl = RosterTemplate()
    doc.build(elements, onFirstPage=tmpl.on_page, onLaterPages=tmpl.on_page)

    buffer.seek(0)
    from starlette.responses import Response
    filename = f"{org_name.replace(' ', '_')}_Roster_Brief.pdf"
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


class CreatorContactCreate(BaseModel):
    contact_id: int
    role: str = "OTHER"
    is_primary: bool = False
    notes: Optional[str] = None

class CreatorContactResponse(BaseModel):
    id: int
    creator_id: int
    contact_id: int
    role: str
    is_primary: bool
    notes: Optional[str]
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_roles: Optional[list] = None

    class Config:
        from_attributes = True


@router.get("/{creator_id}/contacts")
async def get_creator_contacts(
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    if not current_user.is_super_admin:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == creator.organization_id
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="Not authorized")

    contacts = db.query(CreatorContact).filter(
        CreatorContact.creator_id == creator_id
    ).all()

    result = []
    for cc in contacts:
        contact = db.query(CreativeContact).filter(CreativeContact.id == cc.contact_id).first()
        result.append({
            "id": cc.id,
            "creator_id": cc.creator_id,
            "contact_id": cc.contact_id,
            "role": cc.role,
            "is_primary": cc.is_primary,
            "notes": cc.notes,
            "contact_name": contact.display_name if contact else None,
            "contact_email": contact.email if contact else None,
            "contact_phone": contact.phone if contact else None,
            "contact_roles": contact.roles if contact else None,
        })
    return result


@router.post("/{creator_id}/contacts")
async def add_creator_contact(
    creator_id: int,
    data: CreatorContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    if not current_user.is_super_admin:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == creator.organization_id
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="Not authorized")

    contact = db.query(CreativeContact).filter(CreativeContact.id == data.contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    existing = db.query(CreatorContact).filter(
        CreatorContact.creator_id == creator_id,
        CreatorContact.contact_id == data.contact_id,
        CreatorContact.role == data.role,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="This contact is already assigned with this role")

    if data.is_primary:
        db.query(CreatorContact).filter(
            CreatorContact.creator_id == creator_id,
            CreatorContact.role == data.role,
            CreatorContact.is_primary == True,
        ).update({"is_primary": False})

    cc = CreatorContact(
        creator_id=creator_id,
        contact_id=data.contact_id,
        role=data.role,
        is_primary=data.is_primary,
        notes=data.notes,
    )
    db.add(cc)
    db.commit()
    db.refresh(cc)

    return {
        "id": cc.id,
        "creator_id": cc.creator_id,
        "contact_id": cc.contact_id,
        "role": cc.role,
        "is_primary": cc.is_primary,
        "notes": cc.notes,
        "contact_name": contact.display_name,
        "contact_email": contact.email,
        "contact_phone": contact.phone,
        "contact_roles": contact.roles,
    }


@router.delete("/{creator_id}/contacts/{contact_link_id}")
async def remove_creator_contact(
    creator_id: int,
    contact_link_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    if not current_user.is_super_admin:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == creator.organization_id
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="Not authorized")

    cc = db.query(CreatorContact).filter(
        CreatorContact.id == contact_link_id,
        CreatorContact.creator_id == creator_id,
    ).first()
    if not cc:
        raise HTTPException(status_code=404, detail="Contact assignment not found")

    db.delete(cc)
    db.commit()
    return {"detail": "Contact removed"}


@router.get("/{creator_id}/contacts/by-role/{role}")
async def get_creator_contact_by_role(
    creator_id: int,
    role: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    creator = db.query(Creator).filter(Creator.id == creator_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")
    if not current_user.is_super_admin:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == creator.organization_id
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="Not authorized")

    contacts = db.query(CreatorContact).filter(
        CreatorContact.creator_id == creator_id,
        CreatorContact.role == role.upper(),
    ).all()

    result = []
    for cc in contacts:
        contact = db.query(CreativeContact).filter(CreativeContact.id == cc.contact_id).first()
        result.append({
            "id": cc.id,
            "creator_id": cc.creator_id,
            "contact_id": cc.contact_id,
            "role": cc.role,
            "is_primary": cc.is_primary,
            "notes": cc.notes,
            "contact_name": contact.display_name if contact else None,
            "contact_email": contact.email if contact else None,
            "contact_phone": contact.phone if contact else None,
        })
    return result
