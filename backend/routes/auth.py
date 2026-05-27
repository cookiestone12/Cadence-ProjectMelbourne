from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from datetime import datetime, timedelta
from ..models import get_db, User, OrganizationMember, UserSession
from ..utils.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    get_current_user,
    hash_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)


def _record_session(db: Session, user_id: int, token: str, request: Optional[Request] = None) -> None:
    """Insert a UserSession row for an issued JWT so it can be
    revoked mid-flight via the session table.
    """
    ip = None
    ua = None
    if request is not None:
        client = getattr(request, "client", None)
        if client is not None:
            ip = getattr(client, "host", None)
        ua = request.headers.get("user-agent")
        if ua and len(ua) > 512:
            ua = ua[:512]
    # Pull expires_at directly from the JWT 'exp' claim so the
    # session row matches the token even if ACCESS_TOKEN_EXPIRE_MINUTES
    # is changed at runtime or a custom expires_delta was passed.
    payload = decode_access_token(token) or {}
    exp = payload.get("exp")
    if exp:
        expires_at = datetime.utcfromtimestamp(int(exp))
    else:
        expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    db.add(UserSession(
        user_id=user_id,
        token_hash=hash_token(token),
        ip_address=ip,
        user_agent=ua,
        expires_at=expires_at,
    ))


router = APIRouter(prefix="/api/auth", tags=["Auth"])

class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict


class AcceptInviteRequest(BaseModel):
    token: str
    username: str
    password: str

@router.post("/register", response_model=TokenResponse, summary="Register new user", description='Creates a new user account. The very first user in a fresh deployment is automatically promoted to admin. Returns a Bearer JWT plus the user payload so the client can sign the user in immediately.\n\n**Body:** `{ email, password, full_name?, organization_name? }`.\n**Auth:** None — public sign-up.\n**Response:** `{ access_token, token_type: "bearer", user: {id, email, full_name, role, organization_id} }`.')
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    # Check if user exists
    if db.query(User).filter(func.lower(User.username) == payload.username.lower()).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(payload.password)
    
    # First user is admin
    is_admin = db.query(User).count() == 0
    
    user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hashed_password,
        is_admin=is_admin
    )
    db.add(user)
    db.flush()
    
    access_token = create_access_token(data={"sub": user.username})
    _record_session(db, user.id, access_token, request)
    db.commit()
    db.refresh(user)

    # Task #204 — welcome the new self-signup (also covers invite
    # acceptance: the invite email points the recipient at this same
    # /auth/register endpoint to set their password). No temporary
    # password is surfaced because the user just chose their own. If the
    # user is already an OrganizationMember (provisioned before
    # registering), use that org's true role and respect its
    # welcome_email_enabled toggle. Failures log but never break signup.
    try:
        from ..templates.email_templates import welcome_email
        from ..services.email_provider import get_email_provider
        from ..models.models import OrganizationMember, Organization
        import os, logging

        log = logging.getLogger("cadence")

        org_role = ""
        org_name = ""
        send_it = True
        membership = (
            db.query(OrganizationMember)
            .filter(OrganizationMember.user_id == user.id)
            .first()
        )
        if membership:
            org_role = membership.role or ""
            org_obj = (
                db.query(Organization)
                .filter(Organization.id == membership.organization_id)
                .first()
            )
            if org_obj:
                org_name = org_obj.display_name or org_obj.name or ""
                send_it = bool(getattr(org_obj, "welcome_email_enabled", True))
        elif user.is_admin:
            org_role = "OWNER"  # first user in deployment, no org yet

        if send_it:
            platform_url = (
                os.getenv("FRONTEND_URL")
                or os.getenv("PLATFORM_URL")
                or "https://cadence-ci.com"
            ).rstrip("/")
            html_body = welcome_email(
                recipient_name=user.username,
                recipient_username=user.username,
                recipient_email=user.email,
                org_name=org_name,
                org_role=org_role,
                platform_url=platform_url,
            )
            ok = get_email_provider().send_email(
                to=user.email,
                subject=f"Welcome to Cadence, {user.username}",
                html_body=html_body,
            )
            if not ok:
                log.warning(
                    "welcome_email send returned False for user_id=%s", user.id
                )
    except Exception as e:
        import logging
        logging.getLogger("cadence").warning(
            "welcome_email dispatch failed for user_id=%s: %s", user.id, e
        )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin
        }
    }

@router.post(
    "/accept-invite",
    response_model=TokenResponse,
    summary="Accept an org invite and create your Cadence account",
    description=(
        "Consumes a tokenised invite issued by `POST /api/tenant/org/{org_id}/invite`. "
        "Atomically creates the User row, adds an OrganizationMember row with the "
        "role recorded on the invite, marks the invite accepted, issues a JWT, "
        "and fires the welcome email (gated on the target org's "
        "`welcome_email_enabled`).\n\n"
        "**Auth:** None — bearer of the invite token authenticates the call.\n"
        "**Body:** `{ token, username, password }`.\n"
        "**Response:** `{ access_token, token_type, user }`."
    ),
)
def accept_invite(
    payload: AcceptInviteRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    from ..models.organizations import OrganizationInvite, Organization
    from ..templates.email_templates import welcome_email
    from ..services.email_provider import get_email_provider
    import os, logging

    log = logging.getLogger("cadence")

    invite = db.query(OrganizationInvite).filter(
        OrganizationInvite.token == payload.token
    ).first()
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid or unknown invite token")
    if invite.accepted_at is not None:
        raise HTTPException(status_code=400, detail="This invite has already been used")
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="This invite has expired")

    if db.query(User).filter(func.lower(User.username) == payload.username.lower()).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    if db.query(User).filter(func.lower(User.email) == invite.email.lower()).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if len(payload.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    org = db.query(Organization).filter(Organization.id == invite.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Inviting organization no longer exists")

    user = User(
        username=payload.username,
        email=invite.email,
        hashed_password=get_password_hash(payload.password),
        is_admin=False,
    )
    db.add(user)
    db.flush()

    db.add(OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=invite.role or "MEMBER",
    ))
    invite.accepted_at = datetime.utcnow()
    db.flush()

    access_token = create_access_token(data={"sub": user.username})
    _record_session(db, user.id, access_token, request)
    db.commit()
    db.refresh(user)

    # Task #204 — fire welcome email with the real org name + invite role.
    try:
        if bool(getattr(org, "welcome_email_enabled", True)):
            platform_url = (
                os.getenv("FRONTEND_URL")
                or os.getenv("PLATFORM_URL")
                or "https://cadence-ci.com"
            ).rstrip("/")
            html_body = welcome_email(
                recipient_name=user.username,
                recipient_username=user.username,
                recipient_email=user.email,
                org_name=org.display_name or org.name or "",
                org_role=invite.role or "MEMBER",
                platform_url=platform_url,
            )
            ok = get_email_provider().send_email(
                to=user.email,
                subject=f"Welcome to Cadence, {user.username}",
                html_body=html_body,
            )
            if not ok:
                log.warning(
                    "welcome_email send returned False for user_id=%s", user.id
                )
    except Exception as e:
        log.warning(
            "welcome_email dispatch failed for user_id=%s: %s", user.id, e
        )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
        },
    }


@router.post("/login", response_model=TokenResponse, summary="Log in (username + password)", description='Username login is case-insensitive. Returns a Bearer JWT plus the user payload. Use the token in the `Authorization: Bearer ...` header on subsequent calls. Supports OAuth2 password-flow form encoding for the OpenAPI playground.\n\n**Body (form-encoded):** `username, password`.\n**Auth:** None.\n**Response:** `{ access_token, token_type: "bearer", user: {id, email, full_name, role, organization_id} }`. Returns 401 on bad credentials.')
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.username) == payload.username.lower()).first()
    
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    if hasattr(user, 'is_active') and not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact your administrator."
        )
    
    user.last_login_at = datetime.utcnow()
    
    access_token = create_access_token(data={"sub": user.username})
    _record_session(db, user.id, access_token, request)
    db.commit()
    
    # Task #190: respect the user's active-org pointer so the role
    # surfaced in the login response matches whatever the rest of the
    # API will resolve for them.
    from ..utils.auth import get_active_membership
    membership = get_active_membership(db, user)

    user_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": user.is_admin,
        "is_super_admin": getattr(user, 'is_super_admin', False),
        "role": membership.role if membership else None,
        "linked_creator_id": getattr(membership, 'linked_creator_id', None) if membership else None,
    }
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_data
    }


@router.put("/change-password", summary="Change current user's password", description='Verifies the supplied `current_password` before rotating to `new_password`. Existing sessions are not invalidated by a password change — call `/auth/logout-all` after if you want to force re-login on every device.\n\n**Body:** `{ current_password, new_password }`.\n**Auth:** Bearer JWT.\n**Response:** `{ success: true }`. Returns 401 if `current_password` is wrong.')
def change_password(
    request: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not verify_password(request.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    if len(request.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters"
        )
    
    current_user.hashed_password = get_password_hash(request.new_password)
    db.commit()
    
    return {"message": "Password changed successfully"}
