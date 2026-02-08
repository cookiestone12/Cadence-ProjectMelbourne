from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from ..models import get_db, Organization, OrganizationMember, User, Creator, Song
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/organizations", tags=["organizations"])

class OrganizationResponse(BaseModel):
    id: int
    name: str
    type: str
    creator_count: int
    song_count: int
    created_at: str
    display_name: Optional[str] = None
    logo_url: Optional[str] = None
    logo_orientation: str = "square"
    primary_color: Optional[str] = None
    account_type: Optional[str] = None
    
    class Config:
        from_attributes = True

class OrganizationCreateRequest(BaseModel):
    name: str
    type: str

class OrganizationMemberResponse(BaseModel):
    id: int
    user_id: int
    role: str
    username: str
    email: str
    
    class Config:
        from_attributes = True

@router.get("/current", response_model=OrganizationResponse)
def get_current_organization(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=404, detail="User is not a member of any organization")
    
    org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    creator_count = db.query(func.count(Creator.id)).filter(Creator.organization_id == org.id).scalar()
    song_count = db.query(func.count(Song.id)).filter(Song.organization_id == org.id).scalar()
    
    return {
        "id": org.id,
        "name": org.name,
        "type": org.type,
        "creator_count": creator_count or 0,
        "song_count": song_count or 0,
        "created_at": org.created_at.isoformat() if org.created_at else "",
        "display_name": org.display_name,
        "logo_url": org.logo_url,
        "logo_orientation": org.logo_orientation or "square",
        "primary_color": org.primary_color,
        "account_type": org.account_type,
    }

@router.get("/current/membership")
def get_current_membership(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=404, detail="User is not a member of any organization")
    
    return {
        "organization_id": membership.organization_id,
        "user_id": membership.user_id,
        "role": membership.role
    }

@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
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
    
    org = db.query(Organization).filter(Organization.id == org_id).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    creator_count = db.query(func.count(Creator.id)).filter(Creator.organization_id == org.id).scalar()
    song_count = db.query(func.count(Song.id)).filter(Song.organization_id == org.id).scalar()
    
    return {
        "id": org.id,
        "name": org.name,
        "type": org.type,
        "creator_count": creator_count or 0,
        "song_count": song_count or 0,
        "created_at": org.created_at.isoformat() if org.created_at else ""
    }

@router.post("/", response_model=OrganizationResponse)
def create_organization(
    request: OrganizationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org = Organization(
        name=request.name,
        type=request.type
    )
    db.add(org)
    db.flush()
    
    member = OrganizationMember(
        organization_id=org.id,
        user_id=current_user.id,
        role="OWNER"
    )
    db.add(member)
    db.commit()
    db.refresh(org)
    
    return {
        "id": org.id,
        "name": org.name,
        "type": org.type,
        "creator_count": 0,
        "song_count": 0,
        "created_at": org.created_at.isoformat() if org.created_at else ""
    }

@router.get("/{org_id}/members", response_model=List[OrganizationMemberResponse])
def get_organization_members(
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
    
    members = db.query(OrganizationMember, User).join(
        User, OrganizationMember.user_id == User.id
    ).filter(
        OrganizationMember.organization_id == org_id
    ).all()
    
    return [
        {
            "id": member.id,
            "user_id": user.id,
            "role": member.role,
            "username": user.username,
            "email": user.email
        }
        for member, user in members
    ]
