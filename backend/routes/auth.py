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


router = APIRouter(prefix="/api/auth", tags=["auth"])

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

@router.post("/register", response_model=TokenResponse)
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

@router.post("/login", response_model=TokenResponse)
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
    
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id
    ).first()
    
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


@router.put("/change-password")
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
