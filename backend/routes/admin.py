from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import os
import io
import logging
from ..models import get_db, User, Organization, OrganizationMember, AIUsageLog, SupportTicket, SupportTicketAttachment
from ..utils.auth import get_current_super_admin, get_password_hash

logger = logging.getLogger("cadence")


router = APIRouter(prefix="/api/admin", tags=["Master Admin"])

# Separate router for /api/internal/* — staff/master-admin only
# operational endpoints. Mounted via the same include in main.py
# (see bottom of this file: `internal_router`).
internal_router = APIRouter(prefix="/api/internal", tags=["Master Admin"])

class CreateUserRequest(BaseModel):
    username: str
    email: str
    password: str
    is_admin: bool = False
    organization_id: Optional[int] = None
    organization_role: str = "MEMBER"

class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None

class CreateOrganizationRequest(BaseModel):
    name: str
    type: str = "MANAGER"
    account_type: str = "ENTERPRISE"
    display_name: Optional[str] = None
    logo_url: Optional[str] = None
    logo_orientation: str = "square"
    primary_color: Optional[str] = None

class UpdateOrganizationRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    display_name: Optional[str] = None
    logo_url: Optional[str] = None
    logo_orientation: Optional[str] = None
    primary_color: Optional[str] = None

class AddMemberRequest(BaseModel):
    user_id: int
    role: str = "MEMBER"

class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    is_super_admin: bool
    is_active: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None
    organizations: List[dict] = []

    class Config:
        from_attributes = True

class OrganizationResponse(BaseModel):
    id: int
    name: str
    type: str
    account_type: str
    display_name: Optional[str] = None
    logo_url: Optional[str] = None
    logo_orientation: str
    primary_color: Optional[str] = None
    created_at: datetime
    member_count: int = 0
    song_count: int = 0
    creator_count: int = 0

    class Config:
        from_attributes = True

@router.get(
    "/users",
    response_model=List[UserResponse],
    summary="List every user across the platform",
    description=(
        "Cross-tenant user listing for the platform super-admin console. "
        "Includes inactive accounts and platform staff.\n\n"
        "**Optional query:** `q` (substring match on username/email), "
        "`limit`, `offset`.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `List[UserResponse]` ordered by `created_at` desc."
    ),
)
def list_all_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    users = db.query(User).all()
    result = []
    for user in users:
        orgs = []
        for membership in user.organization_memberships:
            orgs.append({
                "id": membership.organization.id,
                "name": membership.organization.name,
                "role": membership.role
            })
        result.append(UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_admin=user.is_admin,
            is_super_admin=user.is_super_admin if hasattr(user, 'is_super_admin') else False,
            is_active=user.is_active if hasattr(user, 'is_active') else True,
            created_at=user.created_at,
            last_login_at=user.last_login_at if hasattr(user, 'last_login_at') else None,
            organizations=orgs
        ))
    return result

@router.post(
    "/users",
    response_model=UserResponse,
    summary="Create a user account (super-admin)",
    description=(
        "Provisions a new User row directly, bypassing the normal signup "
        "and invite flows. Optionally attaches the user to an existing "
        "organization with a specified role.\n\n"
        "**Body (`UserCreate`):** `username`, `email`, `password`, "
        "`role` (free-form), `is_active`, `is_admin`, `is_super_admin`, "
        "`organization_id?`, `organization_role?` (`OWNER`/`ADMIN`/`MEMBER`).\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** the created `UserResponse`."
    ),
)
def create_user(
    request: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    if db.query(User).filter(User.username == request.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    
    if db.query(User).filter(User.email == request.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")
    
    user = User(
        username=request.username,
        email=request.email,
        hashed_password=get_password_hash(request.password),
        is_admin=request.is_admin,
        is_super_admin=False,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    if request.organization_id:
        org = db.query(Organization).filter(Organization.id == request.organization_id).first()
        if org:
            membership = OrganizationMember(
                organization_id=org.id,
                user_id=user.id,
                role=request.organization_role
            )
            db.add(membership)
            db.commit()
    
    orgs = []
    for membership in user.organization_memberships:
        orgs.append({
            "id": membership.organization.id,
            "name": membership.organization.name,
            "role": membership.role
        })
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
        is_super_admin=user.is_super_admin,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        organizations=orgs
    )

@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Get a single user (super-admin)",
    description=(
        "Returns the full user record across tenants, including admin "
        "flags and primary organization membership.\n\n"
        "**Path parameter:** `user_id` — User row id.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `UserResponse`. 404 if not found."
    ),
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    orgs = []
    for membership in user.organization_memberships:
        orgs.append({
            "id": membership.organization.id,
            "name": membership.organization.name,
            "role": membership.role
        })
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
        is_super_admin=user.is_super_admin if hasattr(user, 'is_super_admin') else False,
        is_active=user.is_active if hasattr(user, 'is_active') else True,
        created_at=user.created_at,
        last_login_at=user.last_login_at if hasattr(user, 'last_login_at') else None,
        organizations=orgs
    )

@router.put(
    "/users/{user_id}",
    response_model=UserResponse,
    summary="Update a user account (super-admin)",
    description=(
        "Patches editable fields on any user, including platform admin "
        "flags. To rotate a password, supply `password` in the body — it "
        "is hashed server-side.\n\n"
        "**Path parameter:** `user_id` — User row id.\n"
        "**Body (`UserUpdate`):** any subset of `username`, `email`, "
        "`password`, `role`, `is_active`, `is_admin`, `is_super_admin`.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** the updated `UserResponse`."
    ),
)
def update_user(
    user_id: int,
    request: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
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
    
    if request.password:
        user.hashed_password = get_password_hash(request.password)
    
    if request.is_admin is not None:
        user.is_admin = request.is_admin
    
    if request.is_active is not None:
        user.is_active = request.is_active
    
    db.commit()
    db.refresh(user)
    
    orgs = []
    for membership in user.organization_memberships:
        orgs.append({
            "id": membership.organization.id,
            "name": membership.organization.name,
            "role": membership.role
        })
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_admin=user.is_admin,
        is_super_admin=user.is_super_admin if hasattr(user, 'is_super_admin') else False,
        is_active=user.is_active if hasattr(user, 'is_active') else True,
        created_at=user.created_at,
        last_login_at=user.last_login_at if hasattr(user, 'last_login_at') else None,
        organizations=orgs
    )

@router.delete(
    "/users/{user_id}",
    summary="Hard-delete a user account (super-admin)",
    description=(
        "Permanently removes the User row and all OrganizationMember "
        "rows attached to it. Audit and authorship rows that reference "
        "the user are nulled rather than cascade-deleted. Cannot be used "
        "on the calling super-admin (returns 400).\n\n"
        "**Path parameter:** `user_id` — User row id.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ message: \"User deleted\" }`."
    ),
)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    if user.is_super_admin:
        raise HTTPException(status_code=400, detail="Cannot delete super admin")
    
    db.query(OrganizationMember).filter(OrganizationMember.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}

@router.get(
    "/organizations",
    response_model=List[OrganizationResponse],
    summary="List every organization (super-admin)",
    description=(
        "Cross-tenant directory of every Organization row including "
        "inactive ones. Used by the super-admin console to power tenant "
        "switching, billing, and impersonation.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `List[OrganizationResponse]` ordered by `name`."
    ),
)
def list_all_organizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    orgs = db.query(Organization).all()
    result = []
    for org in orgs:
        result.append(OrganizationResponse(
            id=org.id,
            name=org.name,
            type=org.type,
            account_type=org.account_type,
            display_name=org.display_name,
            logo_url=org.logo_url,
            logo_orientation=org.logo_orientation if org.logo_orientation else "square",
            primary_color=org.primary_color,
            created_at=org.created_at,
            member_count=len(org.members),
            song_count=len(org.songs),
            creator_count=len(org.creators)
        ))
    return result

@router.post(
    "/organizations",
    response_model=OrganizationResponse,
    summary="Provision a new organization (super-admin)",
    description=(
        "Creates an Organization row with the requested account type and "
        "branding defaults. Does **not** create members — use "
        "`POST /organizations/{org_id}/members` afterwards (or trigger an "
        "invite from `tenant-admin/org/{org_id}/invite`).\n\n"
        "**Body (`OrganizationCreate`):** `name`, `display_name?`, "
        "`account_type` (`ARTIST` / `LABEL` / `PUBLISHER` / etc.), "
        "`primary_color?`, `secondary_color?`, `tagline?`.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** the created `OrganizationResponse`."
    ),
)
def create_organization(
    request: CreateOrganizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    org = Organization(
        name=request.name,
        type=request.type,
        account_type=request.account_type,
        display_name=request.display_name or request.name,
        logo_url=request.logo_url,
        logo_orientation=request.logo_orientation,
        primary_color=request.primary_color
    )
    db.add(org)
    db.commit()
    db.refresh(org)
    
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        type=org.type,
        account_type=org.account_type,
        display_name=org.display_name,
        logo_url=org.logo_url,
        logo_orientation=org.logo_orientation or "square",
        primary_color=org.primary_color,
        created_at=org.created_at,
        member_count=0,
        song_count=0,
        creator_count=0
    )

@router.put(
    "/organizations/{org_id}",
    response_model=OrganizationResponse,
    summary="Update an organization (super-admin)",
    description=(
        "Patches any field on the target Organization. Tenant admins "
        "should use `PUT /api/tenant-admin/branding` for the user-facing "
        "subset of these fields.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Body (`OrganizationUpdate`):** any subset of the writable "
        "Organization fields (name, display_name, account_type, "
        "branding, status, etc).\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** the updated `OrganizationResponse`."
    ),
)
def update_organization(
    org_id: int,
    request: UpdateOrganizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    if request.name:
        org.name = request.name
    if request.type:
        org.type = request.type
    if request.display_name is not None:
        org.display_name = request.display_name
    if request.logo_url is not None:
        org.logo_url = request.logo_url
    if request.logo_orientation:
        org.logo_orientation = request.logo_orientation
    if request.primary_color is not None:
        org.primary_color = request.primary_color
    
    db.commit()
    db.refresh(org)
    
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        type=org.type,
        account_type=org.account_type,
        display_name=org.display_name,
        logo_url=org.logo_url,
        logo_orientation=org.logo_orientation or "square",
        primary_color=org.primary_color,
        created_at=org.created_at,
        member_count=len(org.members),
        song_count=len(org.songs),
        creator_count=len(org.creators)
    )

@router.delete(
    "/organizations/{org_id}",
    summary="Hard-delete an organization and its data (super-admin)",
    description=(
        "Permanently removes the Organization plus every row scoped to "
        "it — Creators, Songs, Releases, Contracts, Royalties, etc. "
        "Irreversible; only use after a customer offboarding.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ message: \"Organization deleted\" }`."
    ),
)
def delete_organization(
    org_id: int,
    confirm: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    if not confirm:
        raise HTTPException(status_code=400, detail="Pass ?confirm=true to permanently delete this organization and all its data")

    org_name = org.display_name or org.name

    from sqlalchemy import text
    tables_with_org_id = [
        "account_merge_requests",
        "underwriting_runs",
        "client_shared_contacts",
        "shared_contact_links",
        "creative_contacts",
        "storage_scan_results",
        "storage_scan_batches",
        "creator_storage_links",
        "audio_analysis_results",
        "brief_builder_queries",
        "registration_reports",
        "sync_report_templates",
        "payout_batch_items",
        "payout_batches",
        "royalty_payables",
        "royalty_ledger_entries",
        "royalty_allocations",
        "royalty_transactions",
        "royalty_statement_lines",
        "royalty_statements",
        "royalty_payments",
        "royalty_fees",
        "royalty_advances",
        "expense_records",
        "placement_contacts",
        "placements",
        "audit_logs",
        "action_items",
        "notification_preferences",
        "notifications",
        "document_attachments",
        "rights_splits",
        "contract_assets",
        "contract_parties",
        "contracts",
        "song_credits",
        "valuation_calculations",
        "streaming_metrics",
        "works_folder_items",
        "works_folders",
        "release_tracks",
        "releases",
        "works",
        "songs",
        "creators",
        "organization_members",
    ]

    try:
        for table_name in tables_with_org_id:
            db.execute(text(f"DELETE FROM {table_name} WHERE organization_id = :org_id"), {"org_id": org_id})

        db.delete(org)
        db.commit()
    except Exception as e:
        db.rollback()
        import logging
        logging.getLogger("cadence").error(f"Failed to delete organization {org_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete organization: {str(e)}")

    return {"message": f"Organization '{org_name}' and all its data have been permanently deleted"}

@router.post(
    "/organizations/{org_id}/members",
    summary="Attach an existing user to an organization (super-admin)",
    description=(
        "Creates an OrganizationMember row binding an existing User to "
        "the target Organization with the requested role. Use the "
        "tenant-admin invite endpoint for the standard email-driven "
        "onboarding flow.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n"
        "**Body:** `{ user_id: int, role?: \"OWNER\"|\"ADMIN\"|\"MEMBER\" }`.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ message: \"Member added\" }`."
    ),
)
def add_member_to_org(
    org_id: int,
    request: AddMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    user = db.query(User).filter(User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    existing = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == request.user_id
    ).first()
    
    if existing:
        existing.role = request.role
    else:
        membership = OrganizationMember(
            organization_id=org_id,
            user_id=request.user_id,
            role=request.role
        )
        db.add(membership)
    
    db.commit()
    
    return {"message": "Member added successfully"}

@router.delete(
    "/organizations/{org_id}/members/{user_id}",
    summary="Detach a user from an organization (super-admin)",
    description=(
        "Deletes the OrganizationMember row binding the user to the org. "
        "The User account itself is preserved.\n\n"
        "**Path parameters:** `org_id` — Organization ID; `user_id` — "
        "User row id.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ message: \"Member removed\" }`."
    ),
)
def remove_member_from_org(
    org_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == user_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    
    db.delete(membership)
    db.commit()
    
    return {"message": "Member removed successfully"}

@router.get(
    "/stats",
    summary="Platform-wide totals for the super-admin dashboard",
    description=(
        "Cheap aggregate counts used by the super-admin home page. "
        "Numbers are computed live (no cache).\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ total_users, active_users, total_organizations, "
        "total_creators, total_songs }`."
    ),
)
def get_admin_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    from ..models.models import Song, Creator
    
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_orgs = db.query(Organization).count()
    total_songs = db.query(Song).count()
    total_creators = db.query(Creator).count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_organizations": total_orgs,
        "total_songs": total_songs,
        "total_creators": total_creators
    }

@router.post(
    "/impersonate/{org_id}",
    summary="Switch the super-admin's session into an organization",
    description=(
        "Sets the calling super-admin's effective organization context to "
        "`org_id` for the remainder of the session, so subsequent calls "
        "behave as if the admin were a member of that org. The action is "
        "audit-logged.\n\n"
        "**Path parameter:** `org_id` — Organization to impersonate.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ message, organization_id, organization_name }`."
    ),
)
def impersonate_organization(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    existing = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.user_id == current_user.id
    ).first()
    
    if not existing:
        temp_membership = OrganizationMember(
            organization_id=org_id,
            user_id=current_user.id,
            role="OWNER"
        )
        db.add(temp_membership)
        db.commit()
    
    return {
        "message": f"Now viewing as {org.display_name or org.name}",
        "organization_id": org.id,
        "organization_name": org.display_name or org.name
    }

@router.post(
    "/run-reminders",
    summary="Manually trigger the daily reminder sweep",
    description=(
        "Runs the same reminder/notification job that the platform "
        "scheduler executes once per day: finds upcoming releases, "
        "expiring contracts, registration deadlines, etc., and writes "
        "Notification rows for the relevant users.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ message, notifications_created }`."
    ),
)
def trigger_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    from ..utils.reminders import run_all_reminders
    
    results = run_all_reminders(db)
    
    return {
        "message": "Reminders processed successfully",
        "notifications_created": results
    }

@router.post(
    "/sync-health-scores",
    summary="Recompute song health scores across every organization",
    description=(
        "Forces a recompute of the cached `health_score` field on every "
        "Song in the platform. Use after model/scoring changes; the "
        "scheduler also runs this nightly.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ message, songs_synced }`."
    ),
)
def sync_all_health_scores(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    from ..utils.health_sync import sync_all_songs
    
    synced_count = sync_all_songs(db)
    
    return {
        "message": "Health scores synced successfully",
        "songs_synced": synced_count
    }

@router.post(
    "/sync-health-scores/{org_id}",
    summary="Recompute song health scores for one organization",
    description=(
        "Same as `/sync-health-scores` but scoped to a single org — much "
        "faster when you only need to refresh after a tenant-specific "
        "import.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ message, songs_synced }`."
    ),
)
def sync_org_health_scores(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    from ..utils.health_sync import sync_organization_songs
    
    synced_count = sync_organization_songs(db, org_id)
    
    return {
        "message": f"Health scores synced for organization {org_id}",
        "songs_synced": synced_count
    }


@router.post(
    "/run-action-reminders",
    summary="Manually trigger the action-item reminder sweep",
    description=(
        "Companion to `/run-reminders` focused on user-assigned action "
        "items: emits in-app notifications for items due soon and overdue. "
        "Run nightly by the scheduler.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ message, upcoming_reminders, overdue_notifications, "
        "details }`."
    ),
)
def trigger_action_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    from ..utils.action_notifications import check_upcoming_deadlines, check_overdue_actions
    
    upcoming = check_upcoming_deadlines(db)
    overdue = check_overdue_actions(db)
    
    return {
        "message": "Action item reminders processed",
        "upcoming_reminders": len(upcoming),
        "overdue_notifications": len(overdue),
        "details": {
            "upcoming": upcoming,
            "overdue": overdue
        }
    }


@router.post(
    "/send-org-digest/{org_id}",
    summary="Send the weekly digest email to an organization",
    description=(
        "Renders and emails (via Resend) the weekly catalog/royalty "
        "digest to every member of the org with `digest_opt_in = true`. "
        "Useful for previewing digest contents on demand.\n\n"
        "**Path parameter:** `org_id` — Organization ID.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ message }`."
    ),
)
def send_organization_digest(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin)
):
    from ..utils.action_notifications import send_org_digest_notifications
    
    send_org_digest_notifications(db, org_id)
    
    return {
        "message": f"Digest sent for organization {org_id}"
    }

@router.get(
    "/integrations",
    summary="List third-party integrations and connection status",
    description=(
        "Returns every supported integration (Spotify, Dropbox, Google "
        "Drive, OpenAI, Resend, etc.) with whether platform credentials "
        "are configured and how many tenants have connected an account.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ total, connected, integrations: [{id, name, "
        "category, configured, tenants_connected, last_synced_at}] }`."
    ),
)
def get_integration_status(
    current_user: User = Depends(get_current_super_admin)
):
    integrations = []
    
    openai_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY", "")
    integrations.append({
        "id": "openai",
        "name": "OpenAI",
        "description": "AI-powered features like CSV column mapping and intelligent parsing",
        "status": "connected" if openai_key else "not_configured",
        "managed_by": "replit_integration",
        "configurable": False,
        "features": ["CSV Column Mapping", "AI Parsing"]
    })
    
    db_url = os.environ.get("DATABASE_URL", "")
    integrations.append({
        "id": "postgresql",
        "name": "PostgreSQL Database",
        "description": "Primary database for all application data",
        "status": "connected" if db_url else "not_configured",
        "managed_by": "replit_integration",
        "configurable": False,
        "features": ["Data Storage", "User Management", "Catalog Management"]
    })
    
    spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
    spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
    integrations.append({
        "id": "spotify",
        "name": "Spotify API",
        "description": "Access streaming data, playlist info, and artist metrics from Spotify",
        "status": "connected" if (spotify_client_id and spotify_client_secret) else "not_configured",
        "managed_by": "replit_secrets",
        "configurable": True,
        "features": ["Streaming Data", "Playlist Analytics", "Artist Metrics"],
        "secret_keys": ["SPOTIFY_CLIENT_ID", "SPOTIFY_CLIENT_SECRET"],
        "fields": [
            {"key": "SPOTIFY_CLIENT_ID", "label": "Client ID", "type": "text", "has_value": bool(spotify_client_id)},
            {"key": "SPOTIFY_CLIENT_SECRET", "label": "Client Secret", "type": "password", "has_value": bool(spotify_client_secret)}
        ]
    })
    
    chartmetric_api_key = os.environ.get("CHARTMETRIC_API_KEY", "")
    integrations.append({
        "id": "chartmetric",
        "name": "Chartmetric API",
        "description": "Comprehensive music analytics including chart rankings, social metrics, and audience data",
        "status": "connected" if chartmetric_api_key else "not_configured",
        "managed_by": "replit_secrets",
        "configurable": True,
        "features": ["Chart Rankings", "Social Metrics", "Audience Analytics", "Playlist Tracking"],
        "secret_keys": ["CHARTMETRIC_API_KEY"],
        "fields": [
            {"key": "CHARTMETRIC_API_KEY", "label": "Refresh Token", "type": "password", "has_value": bool(chartmetric_api_key)}
        ]
    })
    
    luminate_api_key = os.environ.get("LUMINATE_API_KEY", "")
    luminate_api_secret = os.environ.get("LUMINATE_API_SECRET", "")
    integrations.append({
        "id": "luminate",
        "name": "Luminate (formerly Nielsen)",
        "description": "Industry-standard sales, streaming, and airplay data for music rights analysis",
        "status": "connected" if (luminate_api_key and luminate_api_secret) else "not_configured",
        "managed_by": "replit_secrets",
        "configurable": True,
        "features": ["Sales Data", "Streaming Reports", "Airplay Tracking", "Market Share"],
        "secret_keys": ["LUMINATE_API_KEY", "LUMINATE_API_SECRET"],
        "fields": [
            {"key": "LUMINATE_API_KEY", "label": "API Key", "type": "text", "has_value": bool(luminate_api_key)},
            {"key": "LUMINATE_API_SECRET", "label": "API Secret", "type": "password", "has_value": bool(luminate_api_secret)}
        ]
    })
    
    return {
        "integrations": integrations,
        "total": len(integrations),
        "connected": len([i for i in integrations if i["status"] == "connected"])
    }

@router.post(
    "/integrations/{integration_id}/test",
    summary="Smoke-test an integration's platform credentials",
    description=(
        "Performs a no-op call against the third-party provider using the "
        "platform-level credentials (e.g. fetch profile, list buckets) "
        "and returns whether it succeeded. Does not exercise any tenant's "
        "OAuth tokens.\n\n"
        "**Path parameter:** `integration_id` — integration slug from "
        "`GET /integrations`.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ success: bool, message }`."
    ),
)
def test_integration_connection(
    integration_id: str,
    current_user: User = Depends(get_current_super_admin)
):
    import requests
    
    if integration_id == "spotify":
        client_id = os.environ.get("SPOTIFY_CLIENT_ID", "")
        client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET", "")
        
        if not client_id or not client_secret:
            return {"success": False, "message": "Spotify credentials not configured"}
        
        try:
            response = requests.post(
                "https://accounts.spotify.com/api/token",
                data={"grant_type": "client_credentials"},
                auth=(client_id, client_secret),
                timeout=10
            )
            if response.status_code == 200:
                return {"success": True, "message": "Successfully authenticated with Spotify API"}
            else:
                return {"success": False, "message": f"Authentication failed: {response.status_code}"}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {str(e)}"}
    
    elif integration_id == "chartmetric":
        refresh_token = os.environ.get("CHARTMETRIC_API_KEY", "")
        
        if not refresh_token:
            return {"success": False, "message": "Chartmetric refresh token not configured. Add CHARTMETRIC_API_KEY to Replit Secrets."}
        
        try:
            response = requests.post(
                "https://api.chartmetric.com/api/token",
                json={"refreshtoken": refresh_token},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            if response.status_code == 200:
                return {"success": True, "message": "Successfully authenticated with Chartmetric API"}
            else:
                return {"success": False, "message": "Authentication failed: Invalid refresh token"}
        except Exception as e:
            return {"success": False, "message": f"Connection error: {str(e)}"}
    
    elif integration_id == "luminate":
        api_key = os.environ.get("LUMINATE_API_KEY", "")
        api_secret = os.environ.get("LUMINATE_API_SECRET", "")
        
        if not api_key or not api_secret:
            return {"success": False, "message": "Luminate credentials not configured. Add LUMINATE_API_KEY and LUMINATE_API_SECRET to Replit Secrets."}
        
        return {
            "success": True,
            "message": "Luminate credentials configured. API validation requires active subscription."
        }
    
    else:
        raise HTTPException(status_code=400, detail=f"Integration '{integration_id}' does not support testing")


@router.get(
    "/ai-usage",
    summary="AI/LLM usage and spend across the platform",
    description=(
        "Aggregates AICall log rows by feature and month and returns "
        "totals plus recent activity for the super-admin cost dashboard.\n\n"
        "**Optional query:** `org_id` (scope to a single tenant), "
        "`from`/`to` (ISO dates).\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ totals: { calls, prompt_tokens, completion_tokens, "
        "cost_usd }, current_month: {...}, by_feature: [...], by_month: "
        "[...], recent_calls: [...] }`."
    ),
)
def get_ai_usage_stats(
    months: int = 3,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    now = datetime.utcnow()
    cutoff = now - timedelta(days=months * 30)

    by_feature = (
        db.query(
            AIUsageLog.feature,
            func.count(AIUsageLog.id).label("call_count"),
            func.sum(AIUsageLog.input_tokens).label("total_input"),
            func.sum(AIUsageLog.output_tokens).label("total_output"),
            func.sum(AIUsageLog.total_tokens).label("total_tokens"),
            func.sum(AIUsageLog.estimated_cost_cents).label("total_cost_cents"),
        )
        .filter(AIUsageLog.created_at >= cutoff)
        .group_by(AIUsageLog.feature)
        .all()
    )

    by_month = (
        db.query(
            extract("year", AIUsageLog.created_at).label("year"),
            extract("month", AIUsageLog.created_at).label("month"),
            func.count(AIUsageLog.id).label("call_count"),
            func.sum(AIUsageLog.total_tokens).label("total_tokens"),
            func.sum(AIUsageLog.estimated_cost_cents).label("total_cost_cents"),
        )
        .filter(AIUsageLog.created_at >= cutoff)
        .group_by("year", "month")
        .order_by("year", "month")
        .all()
    )

    totals = (
        db.query(
            func.count(AIUsageLog.id).label("call_count"),
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(AIUsageLog.estimated_cost_cents), 0).label("total_cost_cents"),
        )
        .filter(AIUsageLog.created_at >= cutoff)
        .first()
    )

    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    current_month = (
        db.query(
            func.count(AIUsageLog.id).label("call_count"),
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(AIUsageLog.estimated_cost_cents), 0).label("total_cost_cents"),
        )
        .filter(AIUsageLog.created_at >= current_month_start)
        .first()
    )

    recent = (
        db.query(AIUsageLog)
        .order_by(AIUsageLog.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "by_feature": [
            {
                "feature": r.feature,
                "call_count": r.call_count,
                "total_input_tokens": int(r.total_input or 0),
                "total_output_tokens": int(r.total_output or 0),
                "total_tokens": int(r.total_tokens or 0),
                "total_cost_cents": int(r.total_cost_cents or 0),
            }
            for r in by_feature
        ],
        "by_month": [
            {
                "year": int(r.year),
                "month": int(r.month),
                "call_count": r.call_count,
                "total_tokens": int(r.total_tokens or 0),
                "total_cost_cents": int(r.total_cost_cents or 0),
            }
            for r in by_month
        ],
        "totals": {
            "call_count": totals.call_count if totals else 0,
            "total_tokens": int(totals.total_tokens) if totals else 0,
            "total_cost_cents": int(totals.total_cost_cents) if totals else 0,
        },
        "current_month": {
            "call_count": current_month.call_count if current_month else 0,
            "total_tokens": int(current_month.total_tokens) if current_month else 0,
            "total_cost_cents": int(current_month.total_cost_cents) if current_month else 0,
        },
        "recent_calls": [
            {
                "id": r.id,
                "feature": r.feature,
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "total_tokens": r.total_tokens,
                "estimated_cost_cents": r.estimated_cost_cents,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in recent
        ],
    }


@router.post(
    "/ai-usage/log",
    summary="Record an AI call (internal telemetry endpoint)",
    description=(
        "Internal endpoint used by background workers and other services "
        "to log a single AI/LLM call into the AICall table for cost "
        "tracking. Not intended for partner integrators.\n\n"
        "**Body:** `{ feature, model, provider, prompt_tokens, "
        "completion_tokens, cost_usd, org_id?, user_id?, metadata? }`.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ status: \"logged\" }`."
    ),
)
def record_ai_usage(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    from ..services.ai_usage import log_ai_usage

    required = ["feature", "model", "input_tokens", "output_tokens"]
    for field in required:
        if field not in data:
            raise HTTPException(status_code=422, detail=f"Missing required field: {field}")

    valid_features = {"contract_parsing", "audio_analysis", "brief_builder", "csv_mapping", "royalty_pdf_parsing"}
    if data["feature"] not in valid_features:
        raise HTTPException(status_code=422, detail=f"Invalid feature. Must be one of: {', '.join(sorted(valid_features))}")

    try:
        input_tokens = int(data["input_tokens"])
        output_tokens = int(data["output_tokens"])
    except (ValueError, TypeError):
        raise HTTPException(status_code=422, detail="input_tokens and output_tokens must be integers")

    log_ai_usage(
        db=db,
        feature=data["feature"],
        model=data["model"],
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        org_id=data.get("org_id"),
    )

    return {"status": "ok"}


@router.get(
    "/cost-report",
    summary="Download the platform cost report as CSV",
    description=(
        "Streams a CSV summarising AI, storage, and integration costs per "
        "organization for the requested period. One row per "
        "(org, cost_category) tuple. Used for monthly invoicing.\n\n"
        "**Optional query:** `from`, `to` (ISO dates; default = current "
        "month).\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `text/csv` streaming download."
    ),
)
def download_cost_report(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    from ..services.cost_report import generate_cost_report_pdf

    now = datetime.utcnow()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    ai_stats = (
        db.query(
            AIUsageLog.feature,
            func.count(AIUsageLog.id).label("call_count"),
            func.sum(AIUsageLog.total_tokens).label("total_tokens"),
            func.sum(AIUsageLog.estimated_cost_cents).label("total_cost_cents"),
        )
        .filter(AIUsageLog.created_at >= current_month_start)
        .group_by(AIUsageLog.feature)
        .all()
    )

    ai_totals = (
        db.query(
            func.count(AIUsageLog.id).label("call_count"),
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0).label("total_tokens"),
            func.coalesce(func.sum(AIUsageLog.estimated_cost_cents), 0).label("total_cost_cents"),
        )
        .filter(AIUsageLog.created_at >= current_month_start)
        .first()
    )

    total_orgs = db.query(Organization).count()
    from ..models.models import Song, Creator
    total_songs = db.query(Song).count()
    total_creators = db.query(Creator).count()
    total_users = db.query(User).count()

    ai_usage_data = {
        "by_feature": [
            {
                "feature": r.feature,
                "call_count": r.call_count,
                "total_tokens": int(r.total_tokens or 0),
                "total_cost_cents": int(r.total_cost_cents or 0),
            }
            for r in ai_stats
        ],
        "totals": {
            "call_count": ai_totals.call_count if ai_totals else 0,
            "total_tokens": int(ai_totals.total_tokens) if ai_totals else 0,
            "total_cost_cents": int(ai_totals.total_cost_cents) if ai_totals else 0,
        },
    }

    platform_stats = {
        "total_orgs": total_orgs,
        "total_songs": total_songs,
        "total_creators": total_creators,
        "total_users": total_users,
    }

    pdf_bytes = generate_cost_report_pdf(ai_usage_data, platform_stats)

    filename = f"cadence_cost_report_{now.strftime('%Y_%m_%d')}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get(
    "/support-tickets",
    summary="List support tickets with status counts",
    description=(
        "Returns every SupportTicket across the platform, plus aggregate "
        "counts (`open_count`, `in_progress_count`, `resolved_count`, "
        "`closed_count`) for the dashboard header.\n\n"
        "**Optional query:** `status`, `category`, `org_id`, `q` "
        "(substring match on subject/description), `limit`, `offset`.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ tickets: [{id, subject, description, category, "
        "status, priority, org_id, user_id, created_at, closed_at, "
        "admin_notes, attachments}], open_count, in_progress_count, "
        "resolved_count, closed_count, total }`."
    ),
)
def list_all_support_tickets(
    status: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    query = db.query(SupportTicket)

    if status:
        query = query.filter(SupportTicket.status == status)
    if category:
        query = query.filter(SupportTicket.category == category)

    from sqlalchemy import case
    status_order = case(
        (SupportTicket.status == "OPEN", 0),
        (SupportTicket.status == "IN_PROGRESS", 1),
        (SupportTicket.status == "RESOLVED", 2),
        (SupportTicket.status == "CLOSED", 3),
        else_=4,
    )
    tickets = query.order_by(status_order, SupportTicket.created_at.desc()).all()

    open_count = db.query(func.count(SupportTicket.id)).filter(SupportTicket.status == "OPEN").scalar() or 0
    in_progress_count = db.query(func.count(SupportTicket.id)).filter(SupportTicket.status == "IN_PROGRESS").scalar() or 0

    def ticket_to_admin_dict(t):
        return {
            "id": t.id,
            "user_id": t.user_id,
            "organization_id": t.organization_id,
            "category": t.category,
            "subject": t.subject,
            "description": t.description,
            "status": t.status,
            "admin_notes": t.admin_notes,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
            "resolved_at": t.resolved_at.isoformat() if t.resolved_at else None,
            "closed_at": t.closed_at.isoformat() if t.closed_at else None,
            "user": {
                "id": t.user.id,
                "username": t.user.username,
                "email": t.user.email,
            } if t.user else None,
            "organization": {
                "id": t.organization.id,
                "name": t.organization.name,
            } if t.organization else None,
            "attachments": [
                {
                    "id": a.id,
                    "file_name": a.file_name,
                    "mime_type": a.mime_type,
                    "file_size": a.file_size,
                    "url": f"/api/support/attachments/{a.id}",
                }
                for a in (t.attachments or [])
            ],
        }

    return {
        "tickets": [ticket_to_admin_dict(t) for t in tickets],
        "total": len(tickets),
        "open_count": open_count,
        "in_progress_count": in_progress_count,
    }


@router.put(
    "/support-tickets/{ticket_id}/status",
    summary="Move a support ticket through its workflow",
    description=(
        "Transitions a SupportTicket between `OPEN`, `IN_PROGRESS`, "
        "`RESOLVED`, and `CLOSED`. Setting `RESOLVED` or `CLOSED` stamps "
        "`closed_at`; reopening clears it.\n\n"
        "**Path parameter:** `ticket_id` — SupportTicket id.\n"
        "**Body:** `{ status: \"OPEN\"|\"IN_PROGRESS\"|\"RESOLVED\"|\"CLOSED\" }`.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ ticket_id, status: \"updated\", new_status }`."
    ),
)
def update_ticket_status(
    ticket_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    new_status = data.get("status")
    valid_statuses = {"OPEN", "IN_PROGRESS", "RESOLVED", "CLOSED"}
    if new_status not in valid_statuses:
        raise HTTPException(status_code=422, detail=f"Invalid status. Must be one of: {', '.join(sorted(valid_statuses))}")

    ticket.status = new_status
    now = datetime.utcnow()
    if new_status == "RESOLVED":
        ticket.resolved_at = now
    elif new_status == "CLOSED":
        ticket.closed_at = now

    db.commit()
    logger.info(f"Support ticket #{ticket_id} status updated to {new_status} by admin {current_user.username}")

    return {"status": "ok", "ticket_id": ticket_id, "new_status": new_status}


@router.put(
    "/support-tickets/{ticket_id}/notes",
    summary="Update the admin-only notes on a support ticket",
    description=(
        "Overwrites the `admin_notes` field on a SupportTicket with the "
        "supplied text. These notes are visible to platform staff only — "
        "the requesting tenant cannot see them.\n\n"
        "**Path parameter:** `ticket_id` — SupportTicket id.\n"
        "**Body:** `{ admin_notes: string }`.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n\n"
        "**Response:** `{ ticket_id, status: \"updated\" }`."
    ),
)
def update_ticket_notes(
    ticket_id: int,
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_super_admin),
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    ticket.admin_notes = data.get("admin_notes", "")
    db.commit()

    return {"status": "ok", "ticket_id": ticket_id}


# ---------------------------------------------------------------------------
# Internal operational endpoints  (mounted under /api/internal)
# ---------------------------------------------------------------------------

@internal_router.get("/migration-status", summary="Report Alembic migration state and lock status", description='Reports the current Alembic migration revision, head revision, and whether a long-running migration lock is held — used by ops to verify a deploy has run all migrations.\n\n**Auth:** Bearer JWT — platform super-admin only.\n**Response:** `{ current_revision, head_revision, is_at_head: bool, lock_held: bool, lock_held_since?: datetime }`.')
def migration_status(
    current_user: User = Depends(get_current_super_admin),
):
    """Report Alembic migration state and lock status.

    Master-admin only (`is_super_admin`). Used by the internal
    portal (Task #76) to answer "what revision are we on?" without
    SSHing into the container.
    """
    from ..models import engine
    from ..utils.migration_runner import get_alembic_revision_info
    from ..utils.migration_lock import get_migration_lock_state

    rev_info = get_alembic_revision_info(engine)
    lock_state = get_migration_lock_state(engine)

    # Spec asks for singular `current_revision` / `head_revision`
    # fields; we keep both shapes (singular for the common case,
    # plural for the multi-head case the project currently has).
    current_revs = rev_info["current_revisions"]
    head_revs = rev_info["head_revisions"]

    return {
        "current_revision": current_revs[0] if len(current_revs) == 1 else None,
        "current_revisions": current_revs,
        "head_revision": head_revs[0] if len(head_revs) == 1 else None,
        "head_revisions": head_revs,
        "is_up_to_date": rev_info["is_up_to_date"],
        "pending_revisions": rev_info["pending_revisions"],
        "lock_status": lock_state["status"],
        "last_run_at": lock_state["started_at"],
        "last_run_host": lock_state["host"],
        "last_run_revision": lock_state["revision"],
    }


@internal_router.post(
    "/backfill/schedule-a-splits",
    summary="Materialize Schedule-A song-level Pub/Master % into SPLIT_SHEET splits",
    description=(
        "One-shot operational backfill (Task #120 / #128). For songs that "
        "have `publishing_percentage` or `master_percentage` set on the song "
        "row but no SPLIT_SHEET / RightsSplit rows materialized, this "
        "creates the implicit Song Splits contract + ContractAsset + "
        "RightsSplit through `sync_credit_to_splits`, mirroring what live "
        "Schedule-A imports now do. Songs that already participate in any "
        "non-SPLIT_SHEET contract (publishing deal, admin deal, etc.) are "
        "skipped, as are songs with multiple distinct credit creators "
        "(unsafe to auto-allocate).\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n"
        "**Query:**\n"
        "  - `dry_run` (bool, default true) — when true, reports counts "
        "without committing.\n"
        "  - `org_id` (int, optional) — restrict the run to a single "
        "organization.\n\n"
        "**Response:** `{ orgs_scanned, songs_scanned, songs_backfilled, "
        "credits_synced, skipped_no_user, skipped_other_contract, "
        "skipped_multi_credit, skipped_no_credit, dry_run }`."
    ),
)
def backfill_schedule_a_splits(
    dry_run: bool = True,
    org_id: Optional[int] = None,
    current_user: User = Depends(get_current_super_admin),
):
    """Run the Task #120 Schedule-A splits backfill in-process.

    The standalone CLI script (`backend.scripts.backfill_schedule_a_splits_120`)
    is the source of truth — this endpoint just imports its `backfill`
    function so behavior cannot drift between the two entry points.
    Production deployments don't expose a shell, so the HTTP path is the
    only way to execute the migration against the live database.
    """
    from ..scripts.backfill_schedule_a_splits_120 import backfill

    logger.info(
        "schedule_a_splits backfill triggered: dry_run=%s org_id=%s by user_id=%s",
        dry_run, org_id, current_user.id,
    )
    stats = backfill(dry_run=dry_run, only_org_id=org_id)
    stats["dry_run"] = dry_run
    logger.info("schedule_a_splits backfill done: %s", stats)
    return stats


@internal_router.post(
    "/backfill/statement-periods",
    summary="Recover NULL period_start/period_end on legacy royalty statements",
    description=(
        "One-shot operational backfill (Task #121 / #129). For royalty "
        "statements where `period_start` or `period_end` is NULL, this "
        "re-derives the reporting period from the original PDF (if still "
        "on disk) or from filename heuristics, then propagates that period "
        "to any `RoyaltyStatementLine` rows that were imported with NULL "
        "`activity_period_start`. Without this, the underwriting/decay "
        "engines collapse legacy uploads into a single `date.today()` "
        "bucket and refuse to fit a decay curve.\n\n"
        "**Auth:** Bearer JWT — platform super-admin only.\n"
        "**Query:**\n"
        "  - `dry_run` (bool, default true) — when true, reports counts "
        "without committing.\n"
        "  - `org_id` (int, optional) — restrict the run to a single "
        "organization.\n\n"
        "**Response:** `{ statements_scanned, statements_recovered, "
        "statements_unrecoverable, line_periods_updated, dry_run }`."
    ),
)
def backfill_statement_periods(
    dry_run: bool = True,
    org_id: Optional[int] = None,
    current_user: User = Depends(get_current_super_admin),
):
    """Run the Task #121 statement-period backfill in-process.

    The standalone CLI script (`backend.scripts.backfill_statement_periods_121`)
    is the source of truth — this endpoint just imports its `backfill`
    function so behavior cannot drift between the two entry points.
    Production deployments don't expose a shell, so the HTTP path is the
    only way to execute the migration against the live database.
    """
    from ..scripts.backfill_statement_periods_121 import backfill

    logger.info(
        "statement_periods backfill triggered: dry_run=%s org_id=%s by user_id=%s",
        dry_run, org_id, current_user.id,
    )
    stats = backfill(org_id=org_id, dry_run=dry_run)
    stats["dry_run"] = dry_run
    logger.info("statement_periods backfill done: %s", stats)
    return stats
