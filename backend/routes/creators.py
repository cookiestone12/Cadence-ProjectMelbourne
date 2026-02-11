from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from ..models import get_db, Creator, OrganizationMember, User, Song, SongCredit
from ..utils.auth import get_current_user
import os
import uuid
from pathlib import Path

router = APIRouter(prefix="/api/creators", tags=["creators"])

class CreatorResponse(BaseModel):
    id: int
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

class CreatorUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    legal_name: Optional[str] = None
    email: Optional[str] = None
    roles: Optional[List[str]] = None
    primary_territory: Optional[str] = None
    primary_pro: Optional[str] = None
    primary_ipi: Optional[str] = None
    hero_image_url: Optional[str] = None

class CreatorDetailResponse(BaseModel):
    id: int
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
        raise HTTPException(status_code=403, detail="Not authorized to access this organization")
    
    creators = db.query(Creator).filter(Creator.organization_id == org_id).all()
    
    result = []
    for creator in creators:
        song_count = db.query(func.count(SongCredit.id)).filter(
            SongCredit.creator_id == creator.id
        ).scalar() or 0
        
        avg_health = db.query(func.avg(Song.status_health_score)).join(
            SongCredit, Song.id == SongCredit.song_id
        ).filter(
            SongCredit.creator_id == creator.id
        ).scalar() or 0.0
        
        result.append({
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
            "avg_health_score": float(avg_health) if avg_health else 0.0
        })
    
    return result

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
    
    creator = Creator(
        organization_id=org_id,
        display_name=request.display_name,
        legal_name=request.legal_name,
        email=request.email,
        roles=request.roles,
        primary_territory=request.primary_territory,
        primary_pro=request.primary_pro,
        primary_ipi=request.primary_ipi,
        hero_image_url=request.hero_image_url
    )
    db.add(creator)
    db.commit()
    db.refresh(creator)
    
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
        "avg_health_score": 0.0
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
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized to access this creator")
    
    song_count = db.query(func.count(SongCredit.id)).filter(
        SongCredit.creator_id == creator.id
    ).scalar() or 0
    
    avg_health = db.query(func.avg(Song.status_health_score)).join(
        SongCredit, Song.id == SongCredit.song_id
    ).filter(
        SongCredit.creator_id == creator.id
    ).scalar() or 0.0
    
    placement_count = db.query(func.count(Song.id)).join(
        SongCredit, Song.id == SongCredit.song_id
    ).filter(
        SongCredit.creator_id == creator.id,
        Song.is_paid == True
    ).scalar() or 0
    
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
        "placement_count": placement_count
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
        raise HTTPException(status_code=403, detail="Not authorized to update this creator")
    
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
        "avg_health_score": float(avg_health) if avg_health else 0.0
    }


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
