from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from ..models import get_db, Settings, User
from ..utils.auth import get_current_admin_user

router = APIRouter(prefix="/api/settings", tags=["Settings"])

class SettingRequest(BaseModel):
    key: str
    value: str

class SettingResponse(BaseModel):
    key: str
    value: str
    
    class Config:
        from_attributes = True

@router.get(
    "/",
    response_model=List[SettingResponse],
    summary='List platform-wide settings',
    description='Returns every Setting key/value the platform defines (system feature flags, pricing tiers, rate limits, etc.).\n\n**Auth:** Bearer JWT — platform admin only.\n**Response:** `List[SettingResponse]`.',
)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    settings = db.query(Settings).all()
    return settings

@router.post(
    "/",
    response_model=SettingResponse,
    summary='Create or update a platform setting (upsert)',
    description='Inserts a new Setting or overwrites an existing one keyed by `key`. Values are JSON.\n\n**Body:** `{ key: string, value: any, description?: string }`.\n**Auth:** Bearer JWT — platform admin only.\n**Response:** `SettingResponse` — the persisted row.',
)
def create_or_update_setting(
    request: SettingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    setting = db.query(Settings).filter(Settings.key == request.key).first()
    
    if setting:
        setting.value = request.value
    else:
        setting = Settings(key=request.key, value=request.value)
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    return setting

@router.get("/api-status", summary="Public endpoint to check which APIs are configured", description='Public health probe returning which optional API integrations are configured in this deployment (Spotify, OpenAI, Resend, etc.). Used by the marketing site to indicate live capabilities. **Does not** expose secrets.\n\n**Auth:** None — public.\n**Response:** `{ spotify: bool, openai: bool, resend: bool, dropbox: bool, google_drive: bool }`.')
def get_api_status(db: Session = Depends(get_db)):
    """Public endpoint to check which APIs are configured"""
    import os
    
    return {
        "chartmetric": bool(os.getenv("CHARTMETRIC_API_KEY")),
        "spotify": bool(os.getenv("SPOTIFY_CLIENT_ID") and os.getenv("SPOTIFY_CLIENT_SECRET")),
        "luminate": bool(os.getenv("LUMINATE_API_KEY")),
        "claude": bool(os.getenv("CLAUDE_API_KEY"))
    }
