from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from ..models import get_db, User, Organization, OrganizationMember, OrgNotificationSetting
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

class OrgNotificationSettingRequest(BaseModel):
    notification_type: str
    default_frequency: str = "immediate"
    allow_user_override: bool = True
    rollup_digest_enabled: bool = False
    digest_frequency: str = "weekly"
    digest_day: int = 1
    digest_hour: int = 9

class OrgNotificationSettingResponse(BaseModel):
    id: int
    organization_id: int
    notification_type: str
    default_frequency: str
    allow_user_override: bool
    rollup_digest_enabled: bool
    digest_frequency: str
    digest_day: int
    digest_hour: int
    
    class Config:
        from_attributes = True

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


class EmailDigestPreferenceRequest(BaseModel):
    email_digest_enabled: bool = False
    schedule_interval: str = "weekly"
    min_priority_threshold: int = 3
    preferred_hour: int = 9

class EmailDigestPreferenceResponse(BaseModel):
    id: int
    email_digest_enabled: bool
    schedule_interval: str
    min_priority_threshold: int
    preferred_hour: int
    last_email_sent_at: Optional[datetime] = None

    class Config:
        from_attributes = True


@router.get("/email-digest")
def get_email_digest_preference(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models.models import EmailDigestPreference
    pref = db.query(EmailDigestPreference).filter(
        EmailDigestPreference.user_id == current_user.id
    ).first()

    if not pref:
        return {
            "id": 0,
            "email_digest_enabled": False,
            "schedule_interval": "weekly",
            "min_priority_threshold": 3,
            "preferred_hour": 9,
            "last_email_sent_at": None,
        }

    return {
        "id": pref.id,
        "email_digest_enabled": pref.email_digest_enabled,
        "schedule_interval": pref.schedule_interval,
        "min_priority_threshold": pref.min_priority_threshold,
        "preferred_hour": pref.preferred_hour,
        "last_email_sent_at": pref.last_email_sent_at,
    }


@router.put("/email-digest")
def update_email_digest_preference(
    request: EmailDigestPreferenceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models.models import EmailDigestPreference
    pref = db.query(EmailDigestPreference).filter(
        EmailDigestPreference.user_id == current_user.id
    ).first()

    if pref:
        pref.email_digest_enabled = request.email_digest_enabled
        pref.schedule_interval = request.schedule_interval
        pref.min_priority_threshold = request.min_priority_threshold
        pref.preferred_hour = request.preferred_hour
        pref.updated_at = datetime.utcnow()
    else:
        pref = EmailDigestPreference(
            user_id=current_user.id,
            email_digest_enabled=request.email_digest_enabled,
            schedule_interval=request.schedule_interval,
            min_priority_threshold=request.min_priority_threshold,
            preferred_hour=request.preferred_hour,
        )
        db.add(pref)

    db.commit()
    return {"message": "Email digest preference updated"}


@router.post("/email-digest/send-test")
def send_test_digest(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from ..models import OrganizationMember, ActionItem
    from ..utils.priority_engine import sort_by_urgency, group_by_priority, calculate_priority_score
    from ..templates.email_digest import generate_digest_html
    from ..services.email_provider import get_email_provider

    if not current_user.email:
        raise HTTPException(status_code=400, detail="No email address on your account")

    from ..models.models import EmailDigestPreference
    digest_pref = db.query(EmailDigestPreference).filter(
        EmailDigestPreference.user_id == current_user.id
    ).first()
    min_priority = digest_pref.min_priority_threshold if digest_pref else 4

    memberships = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id
    ).all()
    org_ids = [m.organization_id for m in memberships]

    actions = db.query(ActionItem).filter(
        ActionItem.organization_id.in_(org_ids),
        ActionItem.status.in_(["PENDING", "IN_PROGRESS"]),
        ActionItem.priority <= min_priority,
    ).all() if org_ids else []

    sorted_actions = sort_by_urgency(actions)
    grouped = group_by_priority(sorted_actions)

    now = datetime.utcnow()
    grouped_items = {}
    for level, items in grouped.items():
        grouped_items[level] = [{
            "title": a.title,
            "description": a.description,
            "deadline": a.deadline,
            "entity_type": a.entity_type,
            "entity_label": a.entity_label,
            "action_type": a.action_type,
            "priority_score": calculate_priority_score(a),
        } for a in items]

    overdue_count = sum(1 for a in actions if a.deadline and a.deadline < now)
    summary_stats = {
        "total_items": len(actions),
        "overdue_count": overdue_count,
        "critical_count": len(grouped.get("critical", [])),
        "high_count": len(grouped.get("high", [])),
    }

    user_name = current_user.username or "User"
    html_body = generate_digest_html(user_name, grouped_items, summary_stats)

    provider = get_email_provider()
    success = provider.send_email(
        to=current_user.email,
        subject="[Test] Rythm Action Items Digest",
        html_body=html_body,
    )

    if not success:
        raise HTTPException(status_code=500, detail="Failed to send test email")

    return {"message": f"Test digest email sent to {current_user.email}"}


@router.get("/org/{org_id}/settings", response_model=List[OrgNotificationSettingResponse])
def get_org_notification_settings(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    settings = db.query(OrgNotificationSetting).filter(
        OrgNotificationSetting.organization_id == org_id
    ).all()
    
    existing_types = {s.notification_type for s in settings}
    all_types = [t.value for t in NotificationType]
    
    result = []
    for setting in settings:
        result.append(OrgNotificationSettingResponse(
            id=setting.id,
            organization_id=setting.organization_id,
            notification_type=setting.notification_type,
            default_frequency=setting.default_frequency,
            allow_user_override=setting.allow_user_override,
            rollup_digest_enabled=setting.rollup_digest_enabled,
            digest_frequency=setting.digest_frequency,
            digest_day=setting.digest_day,
            digest_hour=setting.digest_hour
        ))
    
    for ntype in all_types:
        if ntype not in existing_types:
            result.append(OrgNotificationSettingResponse(
                id=0,
                organization_id=org_id,
                notification_type=ntype,
                default_frequency="immediate",
                allow_user_override=True,
                rollup_digest_enabled=False,
                digest_frequency="weekly",
                digest_day=1,
                digest_hour=9
            ))
    
    return result


@router.put("/org/{org_id}/settings")
def update_org_notification_setting(
    org_id: int,
    request: OrgNotificationSettingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == current_user.id,
        OrganizationMember.organization_id == org_id,
        OrganizationMember.role.in_(["OWNER", "ADMIN"])
    ).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    setting = db.query(OrgNotificationSetting).filter(
        OrgNotificationSetting.organization_id == org_id,
        OrgNotificationSetting.notification_type == request.notification_type
    ).first()
    
    if setting:
        setting.default_frequency = request.default_frequency
        setting.allow_user_override = request.allow_user_override
        setting.rollup_digest_enabled = request.rollup_digest_enabled
        setting.digest_frequency = request.digest_frequency
        setting.digest_day = request.digest_day
        setting.digest_hour = request.digest_hour
        setting.updated_at = datetime.utcnow()
    else:
        setting = OrgNotificationSetting(
            organization_id=org_id,
            notification_type=request.notification_type,
            default_frequency=request.default_frequency,
            allow_user_override=request.allow_user_override,
            rollup_digest_enabled=request.rollup_digest_enabled,
            digest_frequency=request.digest_frequency,
            digest_day=request.digest_day,
            digest_hour=request.digest_hour
        )
        db.add(setting)
    
    db.commit()
    
    return {"message": "Organization notification setting updated"}
