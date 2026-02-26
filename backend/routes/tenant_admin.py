from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
import uuid
import base64
from ..models import get_db, User, Organization, OrganizationMember, Creator
from ..utils.auth import get_current_user, get_password_hash

router = APIRouter(prefix="/api/tenant-admin", tags=["tenant-admin"])


def get_org_admin(db: Session, current_user: User):
    if current_user.is_super_admin:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id
        ).first()
        if membership:
            return membership.organization_id, "OWNER"
        raise HTTPException(status_code=404, detail="No organization context")

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="Not a member of any organization")

    if membership.role not in ("OWNER", "ADMIN"):
        raise HTTPException(status_code=403, detail="Admin access required")

    return membership.organization_id, membership.role


class TenantUserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    can_manage_roster: bool = False
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    assigned_creators: List[dict] = []

    class Config:
        from_attributes = True


class UpdatePermissionsRequest(BaseModel):
    can_manage_roster: Optional[bool] = None


class CreateTenantUserRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "MEMBER"


class UpdateTenantUserRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class ResetPasswordRequest(BaseModel):
    new_password: str


class AssignCreatorRequest(BaseModel):
    creator_ids: List[int]


class UpdateBrandingRequest(BaseModel):
    display_name: Optional[str] = None
    logo_url: Optional[str] = None
    logo_orientation: Optional[str] = None
    primary_color: Optional[str] = None
    secondary_color: Optional[str] = None
    tagline: Optional[str] = None


@router.get("/members", response_model=List[TenantUserResponse])
def list_tenant_members(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org_id, _ = get_org_admin(db, current_user)

    members = db.query(OrganizationMember, User).join(
        User, OrganizationMember.user_id == User.id
    ).filter(
        OrganizationMember.organization_id == org_id
    ).all()

    result = []
    for member, user in members:
        creators = db.query(Creator).filter(
            Creator.organization_id == org_id,
            Creator.assigned_to_user_id == user.id
        ).all()

        result.append(TenantUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=member.role,
            is_active=user.is_active if hasattr(user, 'is_active') else True,
            can_manage_roster=getattr(member, 'can_manage_roster', False) or False,
            created_at=user.created_at,
            last_login_at=user.last_login_at if hasattr(user, 'last_login_at') else None,
            assigned_creators=[{"id": c.id, "name": c.name} for c in creators]
        ))

    return result


@router.post("/members", response_model=TenantUserResponse)
def create_tenant_member(
    request: CreateTenantUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org_id, caller_role = get_org_admin(db, current_user)

    if request.role == "OWNER" and caller_role != "OWNER" and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Only owners can assign the OWNER role")

    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")

    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        username=request.username,
        email=request.email,
        hashed_password=get_password_hash(request.password),
        is_admin=False,
        is_super_admin=False,
        is_active=True
    )
    db.add(user)
    db.flush()

    membership = OrganizationMember(
        organization_id=org_id,
        user_id=user.id,
        role=request.role
    )
    db.add(membership)
    db.commit()
    db.refresh(user)

    return TenantUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=request.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=None,
        assigned_creators=[]
    )


@router.put("/members/{user_id}", response_model=TenantUserResponse)
def update_tenant_member(
    user_id: int,
    request: UpdateTenantUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org_id, caller_role = get_org_admin(db, current_user)

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="User not found in this organization")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if request.username and request.username != user.username:
        if db.query(User).filter(User.username == request.username).first():
            raise HTTPException(status_code=400, detail="Username already exists")
        user.username = request.username

    if request.email and request.email != user.email:
        if db.query(User).filter(User.email == request.email).first():
            raise HTTPException(status_code=400, detail="Email already exists")
        user.email = request.email

    if request.role:
        if request.role == "OWNER" and caller_role != "OWNER" and not current_user.is_super_admin:
            raise HTTPException(status_code=403, detail="Only owners can assign the OWNER role")
        membership.role = request.role

    if request.is_active is not None:
        user.is_active = request.is_active

    db.commit()
    db.refresh(user)
    db.refresh(membership)

    assigned = db.query(Creator).filter(
        Creator.organization_id == org_id,
        Creator.assigned_to_user_id == user_id
    ).all()
    creators = [{"id": c.id, "name": c.name} for c in assigned]

    return TenantUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=membership.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at if hasattr(user, 'last_login_at') else None,
        assigned_creators=creators
    )


@router.post("/members/{user_id}/reset-password")
def reset_member_password(
    user_id: int,
    request: ResetPasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org_id, _ = get_org_admin(db, current_user)

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="User not found in this organization")

    if len(request.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = get_password_hash(request.new_password)
    db.commit()

    return {"message": f"Password reset successfully for {user.username}"}


@router.delete("/members/{user_id}")
def remove_tenant_member(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org_id, caller_role = get_org_admin(db, current_user)

    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="User not found in this organization")

    if membership.role == "OWNER" and caller_role != "OWNER":
        raise HTTPException(status_code=403, detail="Only owners can remove other owners")

    db.query(Creator).filter(
        Creator.organization_id == org_id,
        Creator.assigned_to_user_id == user_id
    ).update({Creator.assigned_to_user_id: None})

    db.delete(membership)
    db.commit()

    return {"message": "Member removed from organization"}


@router.patch("/members/{user_id}/permissions")
def update_member_permissions(
    user_id: int,
    request: UpdatePermissionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org_id, _ = get_org_admin(db, current_user)

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="User not found in this organization")

    if request.can_manage_roster is not None:
        membership.can_manage_roster = request.can_manage_roster

    db.commit()
    db.refresh(membership)

    user = db.query(User).filter(User.id == user_id).first()

    assigned = db.query(Creator).filter(
        Creator.organization_id == org_id,
        Creator.assigned_to_user_id == user_id
    ).all()
    creators_list = [{"id": c.id, "name": c.name} for c in assigned]

    return TenantUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=membership.role,
        is_active=user.is_active if hasattr(user, 'is_active') else True,
        can_manage_roster=getattr(membership, 'can_manage_roster', False) or False,
        created_at=user.created_at,
        last_login_at=user.last_login_at if hasattr(user, 'last_login_at') else None,
        assigned_creators=creators_list
    )


@router.post("/members/{user_id}/assign-creators")
def assign_creators_to_member(
    user_id: int,
    request: AssignCreatorRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org_id, _ = get_org_admin(db, current_user)

    membership = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == user_id
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="User not found in this organization")

    db.query(Creator).filter(
        Creator.organization_id == org_id,
        Creator.assigned_to_user_id == user_id
    ).update({Creator.assigned_to_user_id: None})

    for creator_id in request.creator_ids:
        creator = db.query(Creator).filter(
            Creator.id == creator_id,
            Creator.organization_id == org_id
        ).first()
        if creator:
            creator.assigned_to_user_id = user_id

    db.commit()

    assigned = db.query(Creator).filter(
        Creator.organization_id == org_id,
        Creator.assigned_to_user_id == user_id
    ).all()

    return {
        "message": f"Assigned {len(assigned)} creators to user",
        "assigned_creators": [{"id": c.id, "name": c.name} for c in assigned]
    }


@router.get("/branding")
def get_org_branding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).first()

    if not membership:
        raise HTTPException(status_code=404, detail="Not a member of any organization")

    org = db.query(Organization).filter(Organization.id == membership.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return {
        "id": org.id,
        "name": org.name,
        "display_name": org.display_name,
        "logo_url": org.logo_url,
        "logo_orientation": org.logo_orientation or "square",
        "primary_color": org.primary_color,
        "secondary_color": getattr(org, 'secondary_color', None),
        "tagline": getattr(org, 'tagline', None),
        "type": org.type,
        "account_type": org.account_type,
    }


@router.put("/branding")
def update_org_branding(
    request: UpdateBrandingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org_id, _ = get_org_admin(db, current_user)

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if request.display_name is not None:
        org.display_name = request.display_name
    if request.logo_url is not None:
        org.logo_url = request.logo_url
    if request.logo_orientation is not None:
        org.logo_orientation = request.logo_orientation
    if request.primary_color is not None:
        org.primary_color = request.primary_color
    if request.secondary_color is not None and hasattr(org, 'secondary_color'):
        org.secondary_color = request.secondary_color
    if request.tagline is not None and hasattr(org, 'tagline'):
        org.tagline = request.tagline

    db.commit()
    db.refresh(org)

    return {
        "message": "Branding updated successfully",
        "branding": {
            "display_name": org.display_name,
            "logo_url": org.logo_url,
            "logo_orientation": org.logo_orientation or "square",
            "primary_color": org.primary_color,
        }
    }


@router.post("/branding/logo")
async def upload_org_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org_id, _ = get_org_admin(db, current_user)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    max_size = 2 * 1024 * 1024
    contents = await file.read()
    if len(contents) > max_size:
        raise HTTPException(status_code=400, detail="Image must be under 2MB")

    ext = file.filename.split(".")[-1] if file.filename and "." in file.filename else "png"
    b64 = base64.b64encode(contents).decode("utf-8")
    data_url = f"data:{file.content_type};base64,{b64}"

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    org.logo_url = data_url
    db.commit()

    return {
        "message": "Logo uploaded successfully",
        "logo_url": data_url
    }


class InviteUserRequest(BaseModel):
    email: str
    name: Optional[str] = None
    role: str = "MEMBER"
    subject: Optional[str] = None
    message: Optional[str] = None


@router.post("/org/{org_id}/invite")
def invite_user(
    org_id: int,
    request: InviteUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id,
    ).first()
    if not membership and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Access denied")
    if membership and membership.role not in ("OWNER", "ADMIN") and not current_user.is_super_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    from ..templates.email_templates import app_invite
    from ..services.email_provider import get_email_provider

    inviter_name = getattr(current_user, 'full_name', None) or current_user.username
    recipient_name = request.name or request.email.split("@")[0]

    html_body = app_invite(
        recipient_name=recipient_name,
        recipient_email=request.email,
        org_name=org.display_name or org.name,
        inviter_name=inviter_name,
        role=request.role,
    )

    email_subject = request.subject or f"Invitation to join {org.display_name or org.name} on Cadence"
    provider = get_email_provider()
    success = provider.send_email(
        to=request.email,
        subject=email_subject,
        html_body=html_body,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send invitation email")

    return {"success": True, "message": f"Invitation sent to {request.email}"}


@router.get("/creators")
def list_org_creators(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org_id, _ = get_org_admin(db, current_user)

    creators = db.query(Creator).filter(Creator.organization_id == org_id).all()

    return [
        {
            "id": c.id,
            "name": c.name,
            "assigned_to_user_id": getattr(c, 'assigned_to_user_id', None)
        }
        for c in creators
    ]
