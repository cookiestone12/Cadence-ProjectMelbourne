import string
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from ..models import get_db, Organization, OrganizationMember, User, Creator, Song
from ..utils.auth import get_current_user


def _generate_access_code():
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=8))

router = APIRouter(prefix="/api/organizations", tags=["Organizations"])

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

@router.get("/current", response_model=OrganizationResponse, summary="Get the current user's organization", description="Returns the organization the authenticated user is currently scoped to. Cadence staff and master admin see organization 1 by default if they are not a member of any org.")
def get_current_organization(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not membership:
        if current_user.is_super_admin or getattr(current_user, "is_cadence_staff", False):
            org = db.query(Organization).order_by(Organization.id).first()
            if not org:
                raise HTTPException(status_code=404, detail="No organizations exist yet")
        else:
            raise HTTPException(status_code=404, detail="User is not a member of any organization")
    else:
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

@router.get("/current/membership", summary="Get current user's role in their org", description="Returns the role (OWNER/ADMIN/MEMBER) of the current user inside their current organization.")
def get_current_membership(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not membership:
        if current_user.is_super_admin or getattr(current_user, "is_cadence_staff", False):
            org = db.query(Organization).order_by(Organization.id).first()
            if org:
                return {
                    "organization_id": org.id,
                    "user_id": current_user.id,
                    "role": "OWNER" if current_user.is_super_admin else "STAFF_VIEWER",
                }
        raise HTTPException(status_code=404, detail="User is not a member of any organization")
    
    return {
        "organization_id": membership.organization_id,
        "user_id": membership.user_id,
        "role": membership.role,
        "can_manage_roster": getattr(membership, 'can_manage_roster', False) or False,
        "linked_creator_id": getattr(membership, 'linked_creator_id', None),
    }

@router.get("/{org_id}", response_model=OrganizationResponse, summary="Get organization by id", description="Fetch an organization the caller is a member of. Master admin and is_cadence_staff users have cross-org read.")
def get_organization(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    # Cadence staff and master admins get read access to any org.
    if not membership and not current_user.is_super_admin and not getattr(current_user, "is_cadence_staff", False):
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

@router.post("/", response_model=OrganizationResponse, summary="Create a new organization", description="Creates an organization owned by the current user. The caller is added as the OWNER member.")
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

@router.get("/{org_id}/access-code", summary="Get the org's join access code", description="Returns the access code other users can redeem to join this organization. Owner/admin only.")
def get_access_code(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    is_staff = current_user.is_super_admin or getattr(current_user, "is_cadence_staff", False)
    if not is_staff:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == org_id
        ).first()
        if not membership or membership.role not in ("OWNER", "ADMIN"):
            raise HTTPException(status_code=403, detail="Only admins can view the access code")
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    if not org.access_code:
        code = _generate_access_code()
        while db.query(Organization).filter(Organization.access_code == code).first():
            code = _generate_access_code()
        org.access_code = code
        db.commit()
        db.refresh(org)
    return {"access_code": org.access_code}


class _AccessCodeSetRequest(BaseModel):
    access_code: str


@router.post(
    "/{org_id}/access-code",
    summary="Set the org's join access code to a custom value",
    description="Sets the organization's join code to the supplied value. Owner/admin "
                "of the org OR Cadence staff/master admin.",
)
def set_access_code(
    org_id: int,
    payload: _AccessCodeSetRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    is_staff = current_user.is_super_admin or getattr(current_user, "is_cadence_staff", False)
    if not is_staff:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == org_id
        ).first()
        if not membership or membership.role not in ("OWNER", "ADMIN"):
            raise HTTPException(status_code=403, detail="Only admins can set the access code")
    code = (payload.access_code or "").strip().upper()
    if len(code) < 4 or len(code) > 32 or not code.isalnum():
        raise HTTPException(status_code=400, detail="Access code must be 4-32 alphanumeric chars")
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    clash = db.query(Organization).filter(
        Organization.access_code == code, Organization.id != org_id
    ).first()
    if clash:
        raise HTTPException(status_code=409, detail="Access code already in use")
    org.access_code = code
    db.commit()
    db.refresh(org)
    return {"access_code": org.access_code}


@router.post("/{org_id}/regenerate-access-code", summary="Regenerate the org access code", description="Rotates the organization's join code, invalidating the previous one. Owner/admin only.")
def regenerate_access_code(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    is_staff = current_user.is_super_admin or getattr(current_user, "is_cadence_staff", False)
    if not is_staff:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == org_id
        ).first()
        if not membership or membership.role not in ("OWNER", "ADMIN"):
            raise HTTPException(status_code=403, detail="Only admins can regenerate the access code")
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    code = _generate_access_code()
    while db.query(Organization).filter(Organization.access_code == code).first():
        code = _generate_access_code()
    org.access_code = code
    db.commit()
    db.refresh(org)
    return {"access_code": org.access_code}


@router.get("/{org_id}/members", response_model=List[OrganizationMemberResponse], summary="List organization members", description="Returns every user attached to the organization with their role.")
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
