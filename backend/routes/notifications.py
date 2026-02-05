from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from ..models import get_db, User, Organization
from ..models.models import Notification, NotificationPreference, NotificationType
from ..utils.auth import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

class NotificationResponse(BaseModel):
    id: int
    notification_type: str
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

class NotificationPreferenceRequest(BaseModel):
    notification_type: str
    in_app_enabled: bool = True
    email_enabled: bool = False
    frequency: str = "immediate"

class NotificationPreferenceResponse(BaseModel):
    id: int
    notification_type: str
    in_app_enabled: bool
    email_enabled: bool
    frequency: str
    
    class Config:
        from_attributes = True

class CreateNotificationRequest(BaseModel):
    notification_type: str
    title: str
    message: str
    link: Optional[str] = None
    organization_id: Optional[int] = None

@router.get("", response_model=List[NotificationResponse])
def get_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    notifications = query.order_by(Notification.created_at.desc()).limit(limit).all()
    
    return [NotificationResponse(
        id=n.id,
        notification_type=n.notification_type,
        title=n.title,
        message=n.message,
        link=n.link,
        is_read=n.is_read,
        created_at=n.created_at
    ) for n in notifications]

@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).count()
    
    return {"unread_count": count}

@router.put("/{notification_id}/read")
def mark_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    db.commit()
    
    return {"message": "Notification marked as read"}

@router.put("/read-all")
def mark_all_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True, "read_at": datetime.utcnow()})
    
    db.commit()
    
    return {"message": "All notifications marked as read"}

@router.delete("/{notification_id}")
def delete_notification(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    db.delete(notification)
    db.commit()
    
    return {"message": "Notification deleted"}

@router.get("/preferences", response_model=List[NotificationPreferenceResponse])
def get_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    prefs = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id
    ).all()
    
    existing_types = {p.notification_type for p in prefs}
    all_types = [t.value for t in NotificationType]
    
    result = []
    for pref in prefs:
        result.append(NotificationPreferenceResponse(
            id=pref.id,
            notification_type=pref.notification_type,
            in_app_enabled=pref.in_app_enabled,
            email_enabled=pref.email_enabled,
            frequency=pref.frequency
        ))
    
    for ntype in all_types:
        if ntype not in existing_types:
            result.append(NotificationPreferenceResponse(
                id=0,
                notification_type=ntype,
                in_app_enabled=True,
                email_enabled=False,
                frequency="immediate"
            ))
    
    return result

@router.put("/preferences")
def update_preference(
    request: NotificationPreferenceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == current_user.id,
        NotificationPreference.notification_type == request.notification_type
    ).first()
    
    if pref:
        pref.in_app_enabled = request.in_app_enabled
        pref.email_enabled = request.email_enabled
        pref.frequency = request.frequency
        pref.updated_at = datetime.utcnow()
    else:
        pref = NotificationPreference(
            user_id=current_user.id,
            notification_type=request.notification_type,
            in_app_enabled=request.in_app_enabled,
            email_enabled=request.email_enabled,
            frequency=request.frequency
        )
        db.add(pref)
    
    db.commit()
    
    return {"message": "Preference updated"}


def create_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    link: str = None,
    organization_id: int = None,
    extra_data: dict = None
):
    pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == user_id,
        NotificationPreference.notification_type == notification_type
    ).first()
    
    if pref and not pref.in_app_enabled:
        return None
    
    notification = Notification(
        user_id=user_id,
        organization_id=organization_id,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
        extra_data=extra_data
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    
    return notification
