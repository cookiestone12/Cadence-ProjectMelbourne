import logging
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from typing import List, Optional
from ..models import ActionItem, Notification, NotificationPreference, User, OrganizationMember, OrgNotificationSetting

logger = logging.getLogger("cadence")


def get_effective_notification_preference(
    db: Session,
    user_id: int,
    organization_id: int,
    notification_type: str
) -> dict:
    org_setting = db.query(OrgNotificationSetting).filter(
        OrgNotificationSetting.organization_id == organization_id,
        OrgNotificationSetting.notification_type == notification_type
    ).first()
    
    defaults = {
        "in_app_enabled": True,
        "email_enabled": False,
        "frequency": org_setting.default_frequency if org_setting else "immediate"
    }
    
    user_pref = db.query(NotificationPreference).filter(
        NotificationPreference.user_id == user_id,
        NotificationPreference.notification_type == notification_type
    ).first()
    
    if not user_pref:
        return defaults
    
    if org_setting and not org_setting.allow_user_override:
        return {
            "in_app_enabled": True,
            "email_enabled": defaults["email_enabled"],
            "frequency": org_setting.default_frequency
        }
    
    return {
        "in_app_enabled": user_pref.in_app_enabled,
        "email_enabled": user_pref.email_enabled,
        "frequency": user_pref.frequency
    }


def create_action_notification(
    db: Session,
    action_item: ActionItem,
    notification_type: str,
    title: str,
    message: str
):
    org_members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == action_item.organization_id
    ).all()
    
    for member in org_members:
        effective_pref = get_effective_notification_preference(
            db,
            member.user_id,
            action_item.organization_id,
            notification_type
        )
        
        if not effective_pref["in_app_enabled"]:
            continue
        
        link = None
        if action_item.creator_id:
            link = f"/roster/{action_item.creator_id}?tab=actions"
        
        notification = Notification(
            user_id=member.user_id,
            organization_id=action_item.organization_id,
            notification_type=notification_type,
            title=title,
            message=message,
            link=link,
            extra_data={
                "action_item_id": action_item.id,
                "action_type": action_item.action_type,
                "creator_id": action_item.creator_id,
                "song_id": action_item.song_id,
                "deadline": action_item.deadline.isoformat() if action_item.deadline else None
            }
        )
        db.add(notification)

        if effective_pref.get("email_enabled"):
            _send_notification_email(db, member.user_id, title, message, notification_type, action_item)
    
    db.commit()


def _send_notification_email(db: Session, user_id: int, title: str, message: str, notification_type: str, action_item: ActionItem):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.email:
            return

        from ..templates.email_templates import notification_alert
        from ..services.email_provider import get_email_provider

        priority_map = {1: "critical", 2: "high", 3: "medium", 4: "low", 5: "low"}
        priority = priority_map.get(action_item.priority, "medium") if action_item.priority else "medium"

        html_body = notification_alert(
            recipient_name=user.username,
            notification_title=title,
            notification_body=message,
            notification_type=notification_type,
            entity_type=action_item.entity_type or "",
            entity_label=action_item.entity_label or "",
            priority=priority,
        )

        provider = get_email_provider()
        provider.send_email(
            to=user.email,
            subject=title,
            html_body=html_body,
        )
    except Exception as e:
        logger.error(f"Failed to send notification email to user {user_id}: {e}")


def check_upcoming_deadlines(db: Session) -> List[dict]:
    now = datetime.utcnow()
    reminders_sent = []
    
    pending_actions = db.query(ActionItem).filter(
        ActionItem.status != "COMPLETED",
        ActionItem.deadline.isnot(None)
    ).all()
    
    for action in pending_actions:
        if not action.deadline:
            continue
        
        days_until = (action.deadline - now).days
        reminder_days = action.reminder_days_before or 3
        
        should_remind = days_until <= reminder_days and days_until >= 0
        
        if action.last_reminder_sent:
            hours_since_reminder = (now - action.last_reminder_sent).total_seconds() / 3600
            if hours_since_reminder < 24:
                continue
        
        if should_remind:
            if days_until == 0:
                title = f"Action Due Today: {action.title}"
                message = f"The action item '{action.title}' is due today!"
            elif days_until == 1:
                title = f"Action Due Tomorrow: {action.title}"
                message = f"The action item '{action.title}' is due tomorrow."
            else:
                title = f"Deadline Approaching: {action.title}"
                message = f"The action item '{action.title}' is due in {days_until} days."
            
            create_action_notification(
                db=db,
                action_item=action,
                notification_type="CUSTOM_DEADLINE",
                title=title,
                message=message
            )
            
            action.last_reminder_sent = now
            reminders_sent.append({
                "action_id": action.id,
                "title": action.title,
                "days_until_deadline": days_until
            })
    
    db.commit()
    return reminders_sent


def check_overdue_actions(db: Session) -> List[dict]:
    now = datetime.utcnow()
    overdue_notifications = []
    
    overdue_actions = db.query(ActionItem).filter(
        ActionItem.status != "COMPLETED",
        ActionItem.deadline < now
    ).all()
    
    for action in overdue_actions:
        if action.last_reminder_sent:
            hours_since_reminder = (now - action.last_reminder_sent).total_seconds() / 3600
            if hours_since_reminder < 24:
                continue
        
        days_overdue = (now - action.deadline).days
        
        create_action_notification(
            db=db,
            action_item=action,
            notification_type="CUSTOM_DEADLINE",
            title=f"Overdue: {action.title}",
            message=f"The action item '{action.title}' is {days_overdue} day(s) overdue!"
        )
        
        action.last_reminder_sent = now
        overdue_notifications.append({
            "action_id": action.id,
            "title": action.title,
            "days_overdue": days_overdue
        })
    
    db.commit()
    return overdue_notifications


def generate_org_digest(db: Session, organization_id: int) -> Optional[dict]:
    now = datetime.utcnow()
    
    pending_actions = db.query(ActionItem).filter(
        ActionItem.organization_id == organization_id,
        ActionItem.status != "COMPLETED"
    ).all()
    
    if not pending_actions:
        return None
    
    overdue = [a for a in pending_actions if a.deadline and a.deadline < now]
    due_this_week = [a for a in pending_actions if a.deadline and now <= a.deadline <= now + timedelta(days=7)]
    high_priority = [a for a in pending_actions if a.priority == 1]
    
    digest = {
        "organization_id": organization_id,
        "generated_at": now.isoformat(),
        "summary": {
            "total_pending": len(pending_actions),
            "overdue_count": len(overdue),
            "due_this_week_count": len(due_this_week),
            "high_priority_count": len(high_priority)
        },
        "overdue_items": [{"id": a.id, "title": a.title, "deadline": a.deadline.isoformat() if a.deadline else None} for a in overdue[:5]],
        "due_soon_items": [{"id": a.id, "title": a.title, "deadline": a.deadline.isoformat() if a.deadline else None} for a in due_this_week[:5]],
        "high_priority_items": [{"id": a.id, "title": a.title} for a in high_priority[:5]]
    }
    
    return digest


def send_org_digest_notifications(db: Session, organization_id: int):
    digest = generate_org_digest(db, organization_id)
    if not digest:
        return
    
    summary = digest["summary"]
    message_parts = []
    
    if summary["overdue_count"] > 0:
        message_parts.append(f"{summary['overdue_count']} overdue")
    if summary["due_this_week_count"] > 0:
        message_parts.append(f"{summary['due_this_week_count']} due this week")
    if summary["high_priority_count"] > 0:
        message_parts.append(f"{summary['high_priority_count']} high priority")
    
    if not message_parts:
        message_parts.append(f"{summary['total_pending']} pending actions")
    
    title = "Weekly Action Items Digest"
    message = f"Summary: {', '.join(message_parts)}. Total pending: {summary['total_pending']}"
    
    org_members = db.query(OrganizationMember).filter(
        OrganizationMember.organization_id == organization_id
    ).all()
    
    for member in org_members:
        user_pref = db.query(NotificationPreference).filter(
            NotificationPreference.user_id == member.user_id,
            NotificationPreference.notification_type == "WEEKLY_HEALTH_SUMMARY"
        ).first()
        
        if user_pref and not user_pref.in_app_enabled:
            continue
        
        notification = Notification(
            user_id=member.user_id,
            organization_id=organization_id,
            notification_type="WEEKLY_HEALTH_SUMMARY",
            title=title,
            message=message,
            link="/dashboard",
            extra_data=digest
        )
        db.add(notification)
    
    db.commit()
