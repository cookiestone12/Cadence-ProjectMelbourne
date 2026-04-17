"""Internal staff-management endpoints. Master-admin only.

Lives at /api/internal/* alongside admin.internal_router (which
hosts the migration-status endpoint from Task #73).
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from ..models import get_db, User, UserSession, Organization
from ..utils.auth import get_current_super_admin, get_password_hash
from ..services.audit_service import log_action
from ..services.email_provider import get_email_provider

router = APIRouter(prefix="/api/internal", tags=["internal"])


class ProvisionStaffRequest(BaseModel):
    username: str
    email: str
    password: str
    role_note: Optional[str] = None


class DeprovisionStaffRequest(BaseModel):
    user_id: int
    role_note: Optional[str] = None


class StaffUserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_cadence_staff: bool
    is_active: bool

    class Config:
        from_attributes = True


def _audit_org_id(db: Session, actor: User) -> Optional[int]:
    """AuditLog.organization_id is non-nullable with FK to
    organizations. Staff provision/deprovision is platform-level,
    so use the actor's first org if present, otherwise fall back to
    any org in the database. If there are no orgs at all, return
    None and the caller skips audit logging.
    """
    if actor.organization_memberships:
        return actor.organization_memberships[0].organization_id
    fallback = db.query(Organization.id).order_by(Organization.id).first()
    return fallback[0] if fallback else None


@router.post("/provision-staff-user", response_model=StaffUserResponse, status_code=201)
def provision_staff_user(
    payload: ProvisionStaffRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_super_admin),
):
    if db.query(User).filter(sa_func.lower(User.username) == payload.username.lower()).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already exists")

    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        is_cadence_staff=True,
        is_active=True,
    )
    db.add(user)
    db.flush()

    audit_org = _audit_org_id(db, actor)
    if audit_org is not None:
        log_action(
            db,
            organization_id=audit_org,
            user_id=actor.id,
            action="STAFF_PROVISIONED",
            entity_type="USER",
            entity_id=user.id,
            entity_name=user.username,
            details={"role_note": payload.role_note, "email": user.email},
        )
    db.commit()
    db.refresh(user)

    # Welcome email — failure must not roll back the provisioning.
    try:
        provider = get_email_provider()
        provider.send_email(
            to=user.email,
            subject="Welcome to Cadence — your staff account is ready",
            html_body=(
                f"<p>Hi {user.username},</p>"
                f"<p>Your Cadence staff account has been provisioned. "
                f"Sign in with your username and the temporary password "
                f"shared with you separately.</p>"
                + (f"<p><strong>Role note:</strong> {payload.role_note}</p>" if payload.role_note else "")
                + "<p>— The Cadence team</p>"
            ),
        )
    except Exception:
        pass

    return user


@router.post("/deprovision-staff-user", response_model=StaffUserResponse)
def deprovision_staff_user(
    payload: DeprovisionStaffRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_super_admin),
):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_cadence_staff = False

    # Cut every active token for this user. Setting is_revoked=True
    # makes get_current_user reject them on the very next request.
    now = datetime.utcnow()
    revoked = db.query(UserSession).filter(
        UserSession.user_id == user.id,
        UserSession.is_revoked == False,
    ).update(
        {"is_revoked": True, "revoked_at": now},
        synchronize_session=False,
    )

    audit_org = _audit_org_id(db, actor)
    if audit_org is not None:
        log_action(
            db,
            organization_id=audit_org,
            user_id=actor.id,
            action="STAFF_DEPROVISIONED",
            entity_type="USER",
            entity_id=user.id,
            entity_name=user.username,
            details={"role_note": payload.role_note, "sessions_revoked": revoked},
        )
    db.commit()
    db.refresh(user)
    return user
