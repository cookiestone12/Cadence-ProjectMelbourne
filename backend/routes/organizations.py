import string
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import List, Optional
from ..models import get_db, Organization, OrganizationMember, User, Creator, Song
from ..utils.auth import get_current_user, resolve_active_org_id


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


class SwitchOrganizationRequest(BaseModel):
    organization_id: int

class OrganizationMemberResponse(BaseModel):
    id: int
    user_id: int
    role: str
    username: str
    email: str
    
    class Config:
        from_attributes = True

@router.get("/current", response_model=OrganizationResponse, summary="Get the current user's organization", description="Returns the organization the authenticated user is currently scoped to. Cadence staff and master admin see the organization they're impersonating.\n\n**Auth:** Bearer JWT.\n**Response:** `{ id, name, plan, account_type, created_at, owner_user_id }`.")
def get_current_organization(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Task #190: honor users.current_organization_id (with self-heal)
    # so multi-org users see whichever org they last switched to,
    # instead of whichever membership a no-order .first() returned.
    # Read-only context — staff/super-admin can impersonate.
    active_org_id = resolve_active_org_id(db, current_user, allow_staff_impersonation=True)

    if active_org_id is None:
        if current_user.is_super_admin or getattr(current_user, "is_cadence_staff", False):
            org = db.query(Organization).order_by(Organization.id).first()
            if not org:
                raise HTTPException(status_code=404, detail="No organizations exist yet")
        else:
            raise HTTPException(status_code=404, detail="User is not a member of any organization")
    else:
        org = db.query(Organization).filter(Organization.id == active_org_id).first()

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

@router.get("/current/membership", summary="Get current user's role in their org", description='Returns the role of the current user inside their current organization (`OWNER` / `ADMIN` / `MEMBER`).\n\n**Auth:** Bearer JWT.\n**Response:** `{ org_id, role, joined_at }`.')
def get_current_membership(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Task #190: align with /current — return the membership for the
    # active org pointer, not whichever row .first() picked. Read-only
    # context, so staff impersonation is honored here.
    active_org_id = resolve_active_org_id(db, current_user, allow_staff_impersonation=True)

    if active_org_id is not None:
        membership = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.organization_id == active_org_id,
        ).first()
    else:
        membership = None

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


@router.get(
    "/mine",
    summary="List every organization the current user belongs to",
    description="Returns one entry per `organization_members` row for the calling user, with the org's display fields and a flag marking which one is currently active.\n\n**Auth:** Bearer JWT.\n**Response:** `{ active_organization_id, organizations: [{id, name, display_name, type, role, is_active}] }`.",
)
def list_my_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.query(OrganizationMember, Organization).join(
        Organization, Organization.id == OrganizationMember.organization_id,
    ).filter(
        OrganizationMember.user_id == current_user.id,
    ).order_by(OrganizationMember.id.asc()).all()

    # Read-only listing — staff impersonation honored so the active
    # flag matches what /current is showing.
    active_org_id = resolve_active_org_id(db, current_user, allow_staff_impersonation=True)

    return {
        "active_organization_id": active_org_id,
        "organizations": [
            {
                "id": org.id,
                "name": org.name,
                "display_name": org.display_name,
                "type": org.type,
                "logo_url": org.logo_url,
                "role": member.role,
                "is_active": (org.id == active_org_id),
            }
            for member, org in rows
        ],
    }


@router.patch(
    "/current",
    summary="Switch the current user's active organization",
    description="Persists `users.current_organization_id` so all subsequent `/api/organizations/current*` reads, and any other helper that resolves an org from the calling user, return the chosen org. Membership is enforced — switching to an org the caller is not a member of returns 403.\n\n**Body:** `{ organization_id }`.\n**Auth:** Bearer JWT.\n**Response:** the new active organization (`OrganizationResponse` shape).",
)
def switch_current_organization(
    request: SwitchOrganizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == request.organization_id,
    ).first()

    # Cadence staff and master admins can switch into any org for
    # cross-tenant impersonation, mirroring the read access semantics
    # of `GET /api/organizations/{org_id}`.
    is_staff = current_user.is_super_admin or getattr(current_user, "is_cadence_staff", False)
    if not membership and not is_staff:
        raise HTTPException(
            status_code=403,
            detail="You are not a member of that organization",
        )

    org = db.query(Organization).filter(
        Organization.id == request.organization_id,
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    previous_org_id = getattr(current_user, "current_organization_id", None)
    current_user.current_organization_id = org.id

    # Task #190: tenant-scope the audit entry to the *new* org so it
    # surfaces in the audit log of the org the user is now operating
    # under.
    try:
        from ..services.audit_service import log_action
        log_action(
            db,
            organization_id=org.id,
            user_id=current_user.id,
            action="organization.switch",
            entity_type="organization",
            entity_id=org.id,
            entity_name=org.name,
            details={
                "previous_organization_id": previous_org_id,
                "new_organization_id": org.id,
            },
        )
    except Exception:
        pass

    db.commit()

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

@router.get("/{org_id}", response_model=OrganizationResponse, summary="Get organization by id", description='Fetches an organization the caller is a member of. Master admin and `is_cadence_staff` users have cross-org read.\n\n**Path parameter:** `org_id`.\n**Auth:** Bearer JWT — caller must be a member, or a Cadence staff/admin.\n**Response:** `{ id, name, plan, account_type, created_at, member_count }`.')
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

@router.post("/", response_model=OrganizationResponse, summary="Create a new organization", description='Creates an organization owned by the current user. The caller is added as the OWNER member.\n\n**Body:** `{ name, account_type?: "PUBLISHER"|"INDIVIDUAL"|"LABEL", plan? }`.\n**Auth:** Bearer JWT.\n**Response:** the created organization.')
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
    # Task #190: switch the creator into the new org by default so they
    # don't keep seeing their old org's data on the dashboard right
    # after creating a new one.
    current_user.current_organization_id = org.id
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

@router.get("/{org_id}/access-code", summary="Get the org's join access code", description='Returns the access code other users can redeem to join this organization.\n\n**Path parameter:** `org_id`.\n**Auth:** Bearer JWT — caller must be Owner or Admin of the org.\n**Response:** `{ access_code, regenerated_at, regenerated_by }`.')
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


@router.post("/{org_id}/regenerate-access-code", summary="Regenerate the org access code", description="Rotates the organization's join code, invalidating the previous one.\n\n**Path parameter:** `org_id`.\n**Auth:** Bearer JWT — caller must be Owner or Admin of the org.\n**Response:** `{ access_code, regenerated_at }`.")
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


@router.get("/{org_id}/members", response_model=List[OrganizationMemberResponse], summary="List organization members", description='Returns every user attached to the organization with their role and join time.\n\n**Path parameter:** `org_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ members: [{user_id, email, full_name, role, joined_at, last_seen_at}] }`.')
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


# ---------------------------------------------------------------------------
# Assistant settings (Task #196 Phase 3A)
# ---------------------------------------------------------------------------

class AssistantSettingsResponse(BaseModel):
    assistant_write_enabled: bool


class AssistantSettingsRequest(BaseModel):
    assistant_write_enabled: bool


@router.get(
    "/{org_id}/assistant-settings",
    response_model=AssistantSettingsResponse,
    summary="Get this org's AI-assistant settings",
    description=(
        "Returns whether the in-app AI assistant is allowed to propose "
        "write actions for this organization. Any member can read this.\n\n"
        "**Auth:** Bearer JWT — caller must be a member of the org.\n"
        "**Response:** `{ assistant_write_enabled: bool }`."
    ),
)
def get_assistant_settings(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id,
    ).first()
    if not membership and not getattr(current_user, "is_super_admin", False):
        raise HTTPException(status_code=403,
                            detail="Not authorized to access this organization")
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return AssistantSettingsResponse(
        assistant_write_enabled=bool(getattr(org, "assistant_write_enabled", False)),
    )


@router.put(
    "/{org_id}/assistant-settings",
    response_model=AssistantSettingsResponse,
    summary="Update this org's AI-assistant settings (admin only)",
    description=(
        "Flips the org-level `assistant_write_enabled` toggle. When OFF "
        "(the default), the in-app assistant is read-only for this org. "
        "When ON, write tools (mark_song_registered, add_fee_to_song, "
        "update_*_status, etc.) become callable — every mutation still "
        "requires the user to confirm the proposed action.\n\n"
        "**Auth:** Bearer JWT — caller must be OWNER or ADMIN of the org.\n"
        "**Body:** `{ assistant_write_enabled: bool }`.\n"
        "**Response:** the updated settings."
    ),
)
def update_assistant_settings(
    org_id: int,
    payload: AssistantSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id,
    ).first()
    is_super = getattr(current_user, "is_super_admin", False)
    if not is_super and (not membership or membership.role not in ("OWNER", "ADMIN")):
        raise HTTPException(status_code=403,
                            detail="Only org Owners or Admins can change assistant settings.")
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    org.assistant_write_enabled = bool(payload.assistant_write_enabled)
    db.commit()
    db.refresh(org)

    try:
        from ..services.audit_service import log_action
        log_action(
            db=db,
            organization_id=org_id,
            user_id=current_user.id,
            action="ORG_ASSISTANT_WRITE_TOGGLE",
            entity_type="ORGANIZATION",
            entity_id=org_id,
            entity_name=org.name,
            details={"assistant_write_enabled": org.assistant_write_enabled},
        )
        db.commit()
    except Exception:
        pass

    return AssistantSettingsResponse(
        assistant_write_enabled=bool(org.assistant_write_enabled),
    )


# ---------------------------------------------------------------------------
# Welcome-email settings (Task #204)
# ---------------------------------------------------------------------------

class WelcomeEmailSettingsResponse(BaseModel):
    welcome_email_enabled: bool


class WelcomeEmailSettingsRequest(BaseModel):
    welcome_email_enabled: bool


@router.get(
    "/{org_id}/welcome-email-settings",
    response_model=WelcomeEmailSettingsResponse,
    summary="Get this org's welcome-email setting",
    description=(
        "Returns whether Cadence automatically sends a welcome email to "
        "newly provisioned users in this organization.\n\n"
        "**Auth:** Bearer JWT — caller must be a member of the org.\n"
        "**Response:** `{ welcome_email_enabled: bool }`."
    ),
)
def get_welcome_email_settings(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id,
    ).first()
    if not membership and not getattr(current_user, "is_super_admin", False):
        raise HTTPException(status_code=403,
                            detail="Not authorized to access this organization")
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return WelcomeEmailSettingsResponse(
        welcome_email_enabled=bool(getattr(org, "welcome_email_enabled", True)),
    )


@router.put(
    "/{org_id}/welcome-email-settings",
    response_model=WelcomeEmailSettingsResponse,
    summary="Update this org's welcome-email setting (admin only)",
    description=(
        "Flips the org-level `welcome_email_enabled` toggle. When ON "
        "(the default), Cadence sends a polished welcome email with "
        "sign-in details to every new user added to this org. When OFF, "
        "no welcome email is sent — you onboard users manually.\n\n"
        "**Auth:** Bearer JWT — caller must be OWNER or ADMIN of the org.\n"
        "**Body:** `{ welcome_email_enabled: bool }`.\n"
        "**Response:** the updated setting."
    ),
)
def update_welcome_email_settings(
    org_id: int,
    payload: WelcomeEmailSettingsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id,
    ).first()
    is_super = getattr(current_user, "is_super_admin", False)
    if not is_super and (not membership or membership.role not in ("OWNER", "ADMIN")):
        raise HTTPException(status_code=403,
                            detail="Only org Owners or Admins can change welcome-email settings.")
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    org.welcome_email_enabled = bool(payload.welcome_email_enabled)
    db.commit()
    db.refresh(org)

    try:
        from ..services.audit_service import log_action
        log_action(
            db=db,
            organization_id=org_id,
            user_id=current_user.id,
            action="ORG_WELCOME_EMAIL_TOGGLE",
            entity_type="ORGANIZATION",
            entity_id=org_id,
            entity_name=org.name,
            details={"welcome_email_enabled": org.welcome_email_enabled},
        )
        db.commit()
    except Exception:
        pass

    return WelcomeEmailSettingsResponse(
        welcome_email_enabled=bool(org.welcome_email_enabled),
    )
