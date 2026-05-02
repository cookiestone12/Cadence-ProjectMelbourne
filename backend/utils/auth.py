from datetime import datetime, timedelta
from typing import Optional
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from ..models import get_db, User
from .request_context import set_user_id
import os


def hash_token(token: str) -> str:
    """SHA-256 hex digest used as the storage key for UserSession.
    We never store the raw JWT, just its hash.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

SECRET_KEY = os.environ["SESSION_SECRET"]
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def verify_token(token: str) -> Optional[str]:
    payload = decode_access_token(token)
    if payload is None:
        return None
    username = payload.get("sub")
    if username is None or not isinstance(username, str):
        return None
    return username

def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
):
    # Per-request cache so multiple Depends(get_current_user) usages
    # in the same request don't re-hit the DB for the user + session.
    cached = getattr(request.state, "cached_user", None)
    if cached is not None:
        return cached

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = decode_access_token(token)

    if payload is None:
        raise credentials_exception

    username = payload.get("sub")
    if username is None or not isinstance(username, str):
        raise credentials_exception

    user = db.query(User).filter(sa_func.lower(User.username) == username.lower()).first()
    if user is None:
        raise credentials_exception

    # Session enforcement: every JWT must have a matching, non-revoked
    # UserSession row so deprovisioned staff can't keep using a JWT.
    from ..models import UserSession
    session = db.query(UserSession).filter(
        UserSession.token_hash == hash_token(token)
    ).first()
    if session is None or session.is_revoked:
        raise credentials_exception

    set_user_id(user.id)
    request.state.cached_user = user
    return user


def resolve_active_org_id(
    db: Session,
    user: User,
    *,
    allow_staff_impersonation: bool = False,
) -> Optional[int]:
    """Task #190: single source of truth for "which org is this user
    looking at right now".

    Honors ``users.current_organization_id`` when it points at an org
    the user still belongs to. Otherwise self-heals to the oldest
    membership (lowest ``organization_members.id``) and persists the
    pointer so the next call is stable.

    Returns ``None`` only when the user has no memberships at all.

    ``allow_staff_impersonation`` (default **False**) controls whether
    a non-member pointer is honored for ``is_super_admin`` /
    ``is_cadence_staff`` users:

    * **False (default — used by every write-context helper):** the
      pointer is only valid if there is a real ``OrganizationMember``
      row. This guarantees that changing the pointer can never grant
      cross-tenant write access, mirroring ``user_can_write_org``
      (where ``is_cadence_staff`` is read-only).
    * **True:** opt-in for read-only routes that need to display the
      org a staff user is impersonating (``GET /api/organizations/current``,
      ``/current/membership``, ``/mine``). The pointer is then honored
      as long as the org row still exists.

    Cross-tenant write access by staff would otherwise be possible by
    PATCHing ``/current`` to a non-member org and hitting any helper
    that resolves an org context from this function, which is why the
    default is strict.
    """
    from ..models import OrganizationMember, Organization

    is_staff = getattr(user, "is_super_admin", False) or getattr(user, "is_cadence_staff", False)

    pointed = getattr(user, "current_organization_id", None)
    if pointed is not None:
        valid = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == user.id,
            OrganizationMember.organization_id == pointed,
        ).first()
        if valid is not None:
            return pointed
        # Staff impersonation: a non-member pointer is honored only
        # when the caller has explicitly opted in. Write-context
        # helpers leave the default off so they cannot be tricked
        # into writing into another tenant via PATCH /current.
        if allow_staff_impersonation and is_staff:
            org_exists = db.query(Organization.id).filter(
                Organization.id == pointed,
            ).first()
            if org_exists is not None:
                return pointed

    fallback = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
    ).order_by(OrganizationMember.id.asc()).first()

    # Decide whether to overwrite the persisted pointer. We must NOT
    # clobber a staff-impersonation pointer (a non-member pointer to
    # an existing org) just because a strict-mode caller reached this
    # function — otherwise the very next read-context call would no
    # longer see the impersonation. Only persist a self-heal when the
    # current pointer is genuinely invalid (None, missing org, or the
    # user has been removed from a real org and isn't a staff
    # impersonator).
    pointer_is_intentional_impersonation = False
    if is_staff and pointed is not None:
        org_exists = db.query(Organization.id).filter(
            Organization.id == pointed,
        ).first()
        pointer_is_intentional_impersonation = org_exists is not None

    if fallback is None:
        if pointed is not None and not pointer_is_intentional_impersonation:
            try:
                user.current_organization_id = None
                db.commit()
            except Exception:
                db.rollback()
        return None

    if pointed != fallback.organization_id and not pointer_is_intentional_impersonation:
        try:
            user.current_organization_id = fallback.organization_id
            db.commit()
        except Exception:
            db.rollback()
    return fallback.organization_id


def get_active_membership(db: Session, user: User):
    """Task #190: return the ``OrganizationMember`` row for the user's
    *active* org (per ``current_organization_id``), self-healing to the
    oldest membership when the pointer is stale. Returns ``None`` when
    the user has no memberships at all.

    Replaces the old ``OrganizationMember.filter(user_id=...).first()``
    pattern at every auto-resolution site so that switching orgs is
    consistently respected across the API.
    """
    from ..models import OrganizationMember

    org_id = resolve_active_org_id(db, user)
    if org_id is None:
        return None
    return db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id,
    ).first()


def user_can_read_org(user: User, org_id: int, db: Session) -> bool:
    """Centralized read-access check.
    Read access: master admin OR Cadence staff OR org member.
    """
    if user.is_super_admin or getattr(user, "is_cadence_staff", False):
        return True
    from ..models import OrganizationMember
    return db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id,
    ).first() is not None


def user_can_write_org(user: User, org_id: int, db: Session) -> bool:
    """Centralized write-access check.
    Write access: master admin OR org-scoped OWNER/ADMIN.
    is_cadence_staff is read-only and does NOT confer write.
    """
    if user.is_super_admin:
        return True
    from ..models import OrganizationMember
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id,
    ).first()
    if not membership:
        return False
    role = (membership.role or "").upper()
    return role in ("OWNER", "ADMIN")

def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin and not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def get_current_staff_or_admin(current_user: User = Depends(get_current_user)):
    """Allow Cadence staff (is_cadence_staff) OR master admin (is_super_admin).
    Used by all /api/internal/portal/* endpoints — read-only operational
    surface for the staff portal at /internal."""
    if not (current_user.is_super_admin or getattr(current_user, "is_cadence_staff", False)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cadence staff access required"
        )
    return current_user


# Cookie-or-Bearer dependency for the internal staff portal.
# The /internal frontend authenticates via POST /cookie-login which
# sets cadence_internal_token as an httpOnly cookie. We accept that
# cookie OR a normal Authorization: Bearer header (the latter is
# only used by curl-based smoke tests). Validation matches
# get_current_user (signature + non-revoked UserSession + staff
# role).
_optional_security = HTTPBearer(auto_error=False)


def get_current_staff_from_cookie(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_security),
    db: Session = Depends(get_db),
) -> User:
    cached = getattr(request.state, "cached_user", None)
    if cached is not None:
        if not (cached.is_super_admin or getattr(cached, "is_cadence_staff", False)):
            raise HTTPException(status_code=403, detail="Cadence staff access required")
        return cached

    token: Optional[str] = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    if not token:
        token = request.cookies.get("cadence_internal_token")
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    username = payload.get("sub")
    if not isinstance(username, str):
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(sa_func.lower(User.username) == username.lower()).first()
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")

    from ..models import UserSession
    session = db.query(UserSession).filter(
        UserSession.token_hash == hash_token(token)
    ).first()
    if session is None or session.is_revoked:
        raise HTTPException(status_code=401, detail="Session revoked")

    if not (user.is_super_admin or getattr(user, "is_cadence_staff", False)):
        raise HTTPException(status_code=403, detail="Cadence staff access required")

    set_user_id(user.id)
    request.state.cached_user = user
    return user


def get_current_super_admin(current_user: User = Depends(get_current_user)):
    if not current_user.is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )
    return current_user

def get_current_active_user(current_user: User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled"
        )
    return current_user
