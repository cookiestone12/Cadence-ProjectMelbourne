from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
from ..models import get_db, Settings, User
from ..utils.auth import get_current_admin_user

router = APIRouter(prefix="/api/settings", tags=["settings"])

class SettingRequest(BaseModel):
    key: str
    value: str

class SettingResponse(BaseModel):
    key: str
    value: str
    
    class Config:
        from_attributes = True

@router.get("/", response_model=List[SettingResponse])
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    settings = db.query(Settings).all()
    return settings

@router.post("/", response_model=SettingResponse)
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

@router.get("/api-status")
def get_api_status(db: Session = Depends(get_db)):
    """Public endpoint to check which APIs are configured"""
    import os
    
    return {
        "chartmetric": bool(os.getenv("CHARTMETRIC_API_KEY")),
        "spotify": bool(os.getenv("SPOTIFY_CLIENT_ID") and os.getenv("SPOTIFY_CLIENT_SECRET")),
        "luminate": bool(os.getenv("LUMINATE_API_KEY")),
        "claude": bool(os.getenv("CLAUDE_API_KEY"))
    }
