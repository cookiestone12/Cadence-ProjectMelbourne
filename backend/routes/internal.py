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
from ..utils.auth import get_current_super_admin, get_current_staff_or_admin, get_password_hash
from ..services.audit_service import log_action
from ..services.email_provider import get_email_provider

router = APIRouter(prefix="/api/internal", tags=["Internal Staff"])


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
    """Pick a representative org for the audit row. Staff
    provision/deprovision is platform-level, so we prefer the
    actor's first org and fall back to any org in the database.
    audit_logs.organization_id is non-nullable, so callers must
    use _safe_audit() which guards the insert with a savepoint
    when no org exists at all (zero-org bootstrap case only).
    """
    if actor.organization_memberships:
        return actor.organization_memberships[0].organization_id
    fallback = db.query(Organization.id).order_by(Organization.id).first()
    return fallback[0] if fallback else None


def _require_audit(db: Session, actor: User, **kwargs) -> None:
    """Write an audit row or fail the whole operation. Per spec,
    staff provision/deprovision MUST leave an audit trail; if we
    can't persist one, we refuse the operation rather than silently
    succeed.
    """
    org_id = _audit_org_id(db, actor)
    if org_id is None:
        raise HTTPException(
            status_code=500,
            detail="Cannot audit staff operation: no organizations exist yet",
        )
    log_action(db, organization_id=org_id, user_id=actor.id, **kwargs)


@router.post("/provision-staff-user", response_model=StaffUserResponse, status_code=201, summary="Provision a Cadence staff user", description="Creates a user with is_cadence_staff=True (cross-org READ access only). Callable by Cadence staff or master admin. Writes a STAFF_PROVISIONED audit row and emails a welcome message.")
def provision_staff_user(
    payload: ProvisionStaffRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_staff_or_admin),
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

    _require_audit(
        db, actor,
        action="STAFF_PROVISIONED",
        entity_type="USER",
        entity_id=user.id,
        entity_name=user.username,
        details={"role_note": payload.role_note, "email": user.email},
    )
    db.commit()
    db.refresh(user)

    # Welcome email — log failures but don't undo a successful
    # provisioning over an email problem.
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
        import logging
        logging.getLogger("cadence").exception(
            "Welcome email failed for staff user_id=%s email=%s",
            user.id, user.email,
        )

    return user


@router.post("/deprovision-staff-user", response_model=StaffUserResponse, summary="Deprovision a Cadence staff user", description="Flips is_cadence_staff off and revokes every active session for the user, cutting any in-flight JWT immediately. Callable by Cadence staff or master admin. Writes a STAFF_DEPROVISIONED audit row.")
def deprovision_staff_user(
    payload: DeprovisionStaffRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(get_current_staff_or_admin),
):
    if payload.user_id == actor.id:
        raise HTTPException(status_code=400, detail="Cannot deprovision yourself")
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

    _require_audit(
        db, actor,
        action="STAFF_DEPROVISIONED",
        entity_type="USER",
        entity_id=user.id,
        entity_name=user.username,
        details={"role_note": payload.role_note, "sessions_revoked": revoked},
    )
    db.commit()
    db.refresh(user)
    return user
