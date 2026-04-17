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

_optional_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
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

    # Accept either a Bearer header (apps, mobile, smoke tests) or
    # the internal portal's httpOnly cookie. The cookie is scoped to
    # /api so it covers tenant endpoints reused by the staff portal.
    token: Optional[str] = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    if not token:
        token = request.cookies.get("cadence_internal_token")
    if not token:
        raise credentials_exception
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
