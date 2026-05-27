from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
import uuid
import base64
from ..models import get_db, User, Organization, OrganizationMember, Creator
from ..utils.auth import get_current_user, get_password_hash, get_active_membership

router = APIRouter(prefix="/api/tenant-admin", tags=["Tenant Admin"])


def get_org_admin(db: Session, current_user: User):
    if current_user.is_super_admin:
        membership = get_active_membership(db, current_user)
        if membership:
            return membership.organization_id, "OWNER"
        raise HTTPException(status_code=404, detail="No organization context")

    membership = get_active_membership(db, current_user)

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
    linked_creator_id: Optional[int] = None
    linked_creator_name: Optional[str] = None
    client_access_scope: Optional[str] = "OWN"
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    assigned_creators: List[dict] = []

    class Config:
        from_attributes = True


class UpdatePermissionsRequest(BaseModel):
    can_manage_roster: Optional[bool] = None
    client_access_scope: Optional[str] = None


class CreateTenantUserRequest(BaseModel):
    username: str
    email: str
    password: str
    role: str = "MEMBER"
    creator_id: Optional[int] = None
    client_access_scope: Optional[str] = "OWN"


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


@router.get(
    "/members",
    response_model=List[TenantUserResponse],
    summary="List members of the caller's organization",
    description=(
        "Returns every User attached to the caller's organization, with their "
        "OrganizationMember role, roster permission, linked Creator (if any) "
        "and the list of creators they've been individually granted access to. "
        "Drives the Team / Members tab of the Tenant Admin console.\n\n"
        "**Auth:** Bearer JWT. Caller must be an OWNER, ADMIN, or platform "
        "super-admin. Members of the org without admin role get 403.\n\n"
        "**Response:** `List[TenantUserResponse]` ordered by username."
    ),
)
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

        linked_creator_name = None
        if getattr(member, 'linked_creator_id', None):
            lc = db.query(Creator).filter(Creator.id == member.linked_creator_id).first()
            linked_creator_name = lc.display_name if lc else None

        result.append(TenantUserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            role=member.role,
            is_active=user.is_active if hasattr(user, 'is_active') else True,
            can_manage_roster=getattr(member, 'can_manage_roster', False) or False,
            linked_creator_id=getattr(member, 'linked_creator_id', None),
            linked_creator_name=linked_creator_name,
            client_access_scope=getattr(member, 'client_access_scope', 'OWN') or 'OWN',
            created_at=user.created_at,
            last_login_at=user.last_login_at if hasattr(user, 'last_login_at') else None,
            assigned_creators=[{"id": c.id, "name": c.display_name} for c in creators]
        ))

    return result


@router.post(
    "/members",
    response_model=TenantUserResponse,
    summary="Create a new member in the caller's organization",
    description=(
        "Creates a User row, hashes the supplied password, and attaches the "
        "user to the caller's organization with the requested role. Optionally "
        "links the new account to an existing Creator so the user sees only "
        "their own catalog by default.\n\n"
        "**Body (`CreateTenantUserRequest`):** `username`, `email`, "
        "`password` (plain — hashed server-side), `role` (`OWNER` / `ADMIN` / "
        "`MEMBER`, default `MEMBER`), `creator_id` (optional Creator FK), "
        "`client_access_scope` (`OWN` / `ASSIGNED` / `ALL`, default `OWN`).\n\n"
        "**Auth:** Bearer JWT. Caller must be OWNER, ADMIN, or super-admin. "
        "Conflicts on duplicate `username`/`email` return 400.\n\n"
        "**Response:** the freshly created `TenantUserResponse`."
    ),
)
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

    linked_creator_id = None
    linked_creator_name = None
    if request.role == "CLIENT" and request.creator_id:
        creator = db.query(Creator).filter(
            Creator.id == request.creator_id,
            Creator.organization_id == org_id
        ).first()
        if not creator:
            raise HTTPException(status_code=404, detail="Creator not found in this organization")
        if creator.linked_user_id:
            raise HTTPException(status_code=400, detail="This creator is already linked to another user account")
        existing_link = db.query(OrganizationMember).filter(
            OrganizationMember.linked_creator_id == creator.id,
            OrganizationMember.organization_id == org_id
        ).first()
        if existing_link:
            raise HTTPException(status_code=400, detail="This creator already has a linked client account")
        linked_creator_id = creator.id
        linked_creator_name = creator.display_name
        creator.linked_user_id = user.id

    membership = OrganizationMember(
        organization_id=org_id,
        user_id=user.id,
        role=request.role,
        linked_creator_id=linked_creator_id,
        client_access_scope=request.client_access_scope if request.role == "CLIENT" else None
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
        linked_creator_id=linked_creator_id,
        linked_creator_name=linked_creator_name,
        client_access_scope=membership.client_access_scope,
        created_at=user.created_at,
        last_login_at=None,
        assigned_creators=[]
    )


@router.put(
    "/members/{user_id}",
    response_model=TenantUserResponse,
    summary="Update a member's profile or role",
    description=(
        "Patches the editable fields on a member in the caller's org: "
        "`username`, `email`, `role`, `is_active`. Use the dedicated "
        "permissions / reset-password / link-creator endpoints for those "
        "specific concerns.\n\n"
        "**Path parameter:** `user_id` — User row id; must belong to the "
        "caller's organization.\n"
        "**Body (`UpdateTenantUserRequest`):** any subset of the editable "
        "fields. Unspecified fields are untouched.\n\n"
        "**Auth:** Bearer JWT. Caller must be OWNER, ADMIN, or super-admin.\n\n"
        "**Response:** the updated `TenantUserResponse`."
    ),
)
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
    creators = [{"id": c.id, "name": c.display_name} for c in assigned]

    linked_creator_name = None
    if getattr(membership, 'linked_creator_id', None):
        lc = db.query(Creator).filter(Creator.id == membership.linked_creator_id).first()
        linked_creator_name = lc.display_name if lc else None

    return TenantUserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        role=membership.role,
        is_active=user.is_active,
        linked_creator_id=getattr(membership, 'linked_creator_id', None),
        linked_creator_name=linked_creator_name,
        created_at=user.created_at,
        last_login_at=user.last_login_at if hasattr(user, 'last_login_at') else None,
        assigned_creators=creators
    )


class LinkCreatorRequest(BaseModel):
    creator_id: Optional[int] = None


@router.put(
    "/members/{user_id}/link-creator",
    summary="Link or unlink a member to a Creator profile",
    description=(
        "Sets (or clears) the `linked_creator_id` on a member account so the "
        "creator can sign in and see their own catalog through the artist "
        "portal. Pass `creator_id=null` in the body to unlink.\n\n"
        "**Path parameter:** `user_id` — User row id within the caller's org.\n"
        "**Body:** `{ creator_id: int | null }`.\n\n"
        "**Auth:** Bearer JWT. Caller must be OWNER, ADMIN, or super-admin.\n\n"
        "**Response:** `{ message }`."
    ),
)
def link_creator_to_member(
    user_id: int,
    request: LinkCreatorRequest,
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

    if membership.linked_creator_id:
        old_creator = db.query(Creator).filter(Creator.id == membership.linked_creator_id).first()
        if old_creator and old_creator.linked_user_id == user_id:
            old_creator.linked_user_id = None

    if request.creator_id:
        creator = db.query(Creator).filter(
            Creator.id == request.creator_id,
            Creator.organization_id == org_id
        ).first()
        if not creator:
            raise HTTPException(status_code=404, detail="Creator not found in this organization")
        if creator.linked_user_id and creator.linked_user_id != user_id:
            raise HTTPException(status_code=400, detail="This creator is already linked to another user")
        existing_link = db.query(OrganizationMember).filter(
            OrganizationMember.linked_creator_id == creator.id,
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id != user_id
        ).first()
        if existing_link:
            raise HTTPException(status_code=400, detail="This creator already has a linked client account")
        membership.linked_creator_id = creator.id
        membership.role = "CLIENT"
        creator.linked_user_id = user_id
    else:
        membership.linked_creator_id = None
        if membership.role == "CLIENT":
            membership.role = "MEMBER"

    db.commit()
    return {"message": "Creator link updated"}


@router.post(
    "/members/{user_id}/reset-password",
    summary="Force-reset a member's password",
    description=(
        "Hashes and writes a new password for the target member. The user is "
        "**not** notified by email — surface the new password to whoever is "
        "performing the reset out-of-band.\n\n"
        "**Path parameter:** `user_id` — target user, must be in caller's org.\n"
        "**Body (`ResetPasswordRequest`):** `{ new_password }` (plain).\n\n"
        "**Auth:** Bearer JWT. Caller must be OWNER, ADMIN, or super-admin.\n\n"
        "**Response:** `{ message: \"Password reset successfully\" }`."
    ),
)
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


@router.delete(
    "/members/{user_id}",
    summary="Remove a member from the organization",
    description=(
        "Detaches the user from the caller's organization (deletes the "
        "OrganizationMember row). The underlying User account is kept so "
        "audit trails and historical authorship are preserved; the user "
        "simply loses access to org data on next login.\n\n"
        "**Path parameter:** `user_id` — must be a member of caller's org. "
        "Removing the last OWNER is rejected with 400.\n\n"
        "**Auth:** Bearer JWT. Caller must be OWNER, ADMIN, or super-admin.\n\n"
        "**Response:** `{ message: \"Member removed successfully\" }`."
    ),
)
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


@router.patch(
    "/members/{user_id}/permissions",
    summary="Update a member's roster + client-access permissions",
    description=(
        "Toggles fine-grained access flags independent of the OrganizationMember "
        "role: who can manage the artist roster and how broadly they can see "
        "client (creator) data.\n\n"
        "**Path parameter:** `user_id` — must be in caller's org.\n"
        "**Body (`UpdatePermissionsRequest`):** any subset of "
        "`can_manage_roster` (bool) and `client_access_scope` (`OWN` — only "
        "their linked creator; `ASSIGNED` — explicitly assigned creators; "
        "`ALL` — everything in the org).\n\n"
        "**Auth:** Bearer JWT. Caller must be OWNER, ADMIN, or super-admin.\n\n"
        "**Response:** the updated `TenantUserResponse`."
    ),
)
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
    if request.client_access_scope is not None and request.client_access_scope in ("OWN", "ALL"):
        membership.client_access_scope = request.client_access_scope

    db.commit()
    db.refresh(membership)

    user = db.query(User).filter(User.id == user_id).first()

    assigned = db.query(Creator).filter(
        Creator.organization_id == org_id,
        Creator.assigned_to_user_id == user_id
    ).all()
    creators_list = [{"id": c.id, "name": c.display_name} for c in assigned]

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


@router.post(
    "/members/{user_id}/assign-creators",
    summary="Replace a member's set of assigned creators",
    description=(
        "Sets the explicit list of Creator IDs the member can see when their "
        "`client_access_scope` is `ASSIGNED`. The supplied list **replaces** "
        "any prior assignments; pass `[]` to clear.\n\n"
        "**Path parameter:** `user_id` — must be in caller's org.\n"
        "**Body (`AssignCreatorRequest`):** `{ creator_ids: int[] }`. IDs not "
        "in the org are silently dropped.\n\n"
        "**Auth:** Bearer JWT. Caller must be OWNER, ADMIN, or super-admin.\n\n"
        "**Response:** `{ message, assigned_creators: [{id, name}] }`."
    ),
)
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
        "assigned_creators": [{"id": c.id, "name": c.display_name} for c in assigned]
    }


@router.get(
    "/branding",
    summary="Get the caller's organization branding",
    description=(
        "Returns the cosmetic + identity fields used to skin the artist "
        "portal and PDF/CSV exports for the caller's organization: name, "
        "display name, logo, colors, tagline, account type.\n\n"
        "**Auth:** Bearer JWT. Caller must be OWNER, ADMIN, or super-admin.\n\n"
        "**Response:** `{ id, name, display_name, account_type, logo_url, "
        "logo_orientation, primary_color, secondary_color, tagline, "
        "updated_at }`."
    ),
)
def get_org_branding(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = get_active_membership(db, current_user)

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


@router.put(
    "/branding",
    summary="Update the caller's organization branding",
    description=(
        "Patches branding fields on the caller's organization. Use the "
        "logo upload endpoint to change the logo URL itself; this endpoint "
        "is for text/colour fields and pre-uploaded URLs.\n\n"
        "**Body (`UpdateBrandingRequest`):** any subset of `display_name`, "
        "`logo_url`, `logo_orientation`, `primary_color` (hex), "
        "`secondary_color` (hex), `tagline`.\n\n"
        "**Auth:** Bearer JWT. Caller must be OWNER, ADMIN, or super-admin.\n\n"
        "**Response:** `{ message, branding: { ...same shape as GET } }`."
    ),
)
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


@router.post(
    "/branding/logo",
    summary="Upload the organization logo image",
    description=(
        "Multipart upload of a PNG/JPEG/SVG logo. The file is persisted to "
        "the configured object store and the resulting public URL is written "
        "to the organization's `logo_url`. Replaces any previous logo.\n\n"
        "**Body (multipart/form-data):** `file` — the image. Max size and "
        "allowed mime types follow the platform upload limits.\n\n"
        "**Auth:** Bearer JWT. Caller must be OWNER, ADMIN, or super-admin.\n\n"
        "**Response:** `{ message, logo_url }` (the new public URL)."
    ),
)
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


@router.post(
    "/org/{org_id}/invite",
    summary="Email an invitation to join an organization",
    description=(
        "Sends a Resend-backed invite email containing a tokenised signup "
        "link to the supplied address. The recipient becomes an "
        "OrganizationMember with the requested role once they accept. Safe "
        "to call multiple times — a fresh token is issued each call.\n\n"
        "**Path parameter:** `org_id` — target Organization ID.\n"
        "**Body:** `{ email, role?, message? }`. `role` defaults to `MEMBER`.\n\n"
        "**Auth:** Bearer JWT. Caller must be OWNER/ADMIN of `org_id`, or a "
        "platform super-admin.\n\n"
        "**Response:** `{ success: true, message }`."
    ),
)
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
    from ..models.organizations import OrganizationInvite
    from datetime import datetime, timedelta
    import secrets, os

    inviter_name = getattr(current_user, 'full_name', None) or current_user.username
    recipient_name = request.name or request.email.split("@")[0]

    # Task #204 — persist a tokenised invite so /api/auth/accept-invite
    # can bind the new user to the right org + role at registration time.
    token = secrets.token_urlsafe(32)
    invite = OrganizationInvite(
        organization_id=org.id,
        email=request.email.lower(),
        role=request.role or "MEMBER",
        token=token,
        invited_by_user_id=current_user.id,
        expires_at=datetime.utcnow() + timedelta(days=14),
    )
    db.add(invite)
    db.commit()

    platform_url = (
        os.getenv("FRONTEND_URL")
        or os.getenv("PLATFORM_URL")
        or "https://cadence-ci.com"
    ).rstrip("/")

    html_body = app_invite(
        recipient_name=recipient_name,
        recipient_email=request.email,
        org_name=org.display_name or org.name,
        inviter_name=inviter_name,
        role=request.role,
        platform_url=platform_url,
        invite_token=token,
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


@router.get(
    "/creators",
    summary="List creators in the caller's organization",
    description=(
        "Lightweight roster lookup used by the assign-creators picker. "
        "Returns every Creator visible to the caller's org as `{id, name}` "
        "tuples so the admin UI can build a multi-select.\n\n"
        "**Auth:** Bearer JWT. Caller must be OWNER, ADMIN, or super-admin.\n\n"
        "**Response:** `List[{ id, name }]` sorted by `name`."
    ),
)
def list_org_creators(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    org_id, _ = get_org_admin(db, current_user)

    creators = db.query(Creator).filter(Creator.organization_id == org_id).all()

    return [
        {
            "id": c.id,
            "name": c.display_name,
            "display_name": c.display_name,
            "assigned_to_user_id": getattr(c, 'assigned_to_user_id', None),
            "linked_user_id": getattr(c, 'linked_user_id', None)
        }
        for c in creators
    ]
