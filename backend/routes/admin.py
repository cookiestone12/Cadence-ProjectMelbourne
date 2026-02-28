from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import os
from ..models import get_db, User, Organization, OrganizationMember
from ..utils.auth import get_current_super_admin, get_password_hash


router = APIRouter(prefix="/api/admin", tags=["admin"])

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

@router.get("/users", response_model=List[UserResponse])
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

@router.post("/users", response_model=UserResponse)
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

@router.get("/users/{user_id}", response_model=UserResponse)
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

@router.put("/users/{user_id}", response_model=UserResponse)
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

@router.delete("/users/{user_id}")
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

@router.get("/organizations", response_model=List[OrganizationResponse])
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

@router.post("/organizations", response_model=OrganizationResponse)
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

@router.put("/organizations/{org_id}", response_model=OrganizationResponse)
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

@router.delete("/organizations/{org_id}")
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

@router.post("/organizations/{org_id}/members")
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

@router.delete("/organizations/{org_id}/members/{user_id}")
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

@router.get("/stats")
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

@router.post("/impersonate/{org_id}")
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

@router.post("/run-reminders")
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

@router.post("/sync-health-scores")
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

@router.post("/sync-health-scores/{org_id}")
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


@router.post("/run-action-reminders")
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


@router.post("/send-org-digest/{org_id}")
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

@router.get("/integrations")
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

@router.post("/integrations/{integration_id}/test")
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
