from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from ..models.models import (
    Song, User, OrganizationMember, Notification, 
    NotificationPreference, SongChecklistStatus, ChecklistItem
)

def check_missing_isrc(db: Session, organization_id: int = None):
    query = db.query(Song).filter(
        (Song.isrc == None) | (Song.isrc == '')
    )
    if organization_id:
        query = query.filter(Song.organization_id == organization_id)
    return query.all()

def check_missing_iswc(db: Session, organization_id: int = None):
    query = db.query(Song).filter(
        (Song.iswc == None) | (Song.iswc == '')
    )
    if organization_id:
        query = query.filter(Song.organization_id == organization_id)
    return query.all()

def get_low_health_songs(db: Session, organization_id: int = None, threshold: int = 50):
    query = db.query(Song).filter(Song.health_score < threshold)
    if organization_id:
        query = query.filter(Song.organization_id == organization_id)
    return query.all()

def generate_health_summary(db: Session, organization_id: int):
    from sqlalchemy import func
    
    total_songs = db.query(Song).filter(Song.organization_id == organization_id).count()
    
    if total_songs == 0:
        return None
    
    avg_health = db.query(func.avg(Song.health_score)).filter(
        Song.organization_id == organization_id
    ).scalar() or 0
    
    missing_isrc = len(check_missing_isrc(db, organization_id))
    missing_iswc = len(check_missing_iswc(db, organization_id))
    low_health = len(get_low_health_songs(db, organization_id, 50))
    
    return {
        "total_songs": total_songs,
        "average_health": round(avg_health, 1),
        "missing_isrc": missing_isrc,
        "missing_iswc": missing_iswc,
        "low_health_count": low_health
    }

def create_user_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    link: str = None,
    organization_id: int = None
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
        link=link
    )
    db.add(notification)
    return notification

def run_missing_isrc_reminders(db: Session):
    from ..models.models import Organization
    
    orgs = db.query(Organization).all()
    notifications_created = 0
    
    for org in orgs:
        missing_songs = check_missing_isrc(db, org.id)
        if not missing_songs:
            continue
            
        members = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.role.in_(['OWNER', 'ADMIN'])
        ).all()
        
        for member in members:
            existing = db.query(Notification).filter(
                Notification.user_id == member.user_id,
                Notification.notification_type == "MISSING_ISRC",
                Notification.organization_id == org.id,
                Notification.created_at > datetime.utcnow() - timedelta(days=7)
            ).first()
            
            if existing:
                continue
            
            notif = create_user_notification(
                db=db,
                user_id=member.user_id,
                notification_type="MISSING_ISRC",
                title=f"{len(missing_songs)} songs missing ISRC",
                message=f"Your catalog has {len(missing_songs)} songs without ISRC codes. Add ISRC codes to ensure proper tracking and royalty collection.",
                link="/catalog?filter=missing_isrc",
                organization_id=org.id
            )
            if notif:
                notifications_created += 1
    
    db.commit()
    return notifications_created

def run_missing_iswc_reminders(db: Session):
    from ..models.models import Organization
    
    orgs = db.query(Organization).all()
    notifications_created = 0
    
    for org in orgs:
        missing_songs = check_missing_iswc(db, org.id)
        if not missing_songs:
            continue
            
        members = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.role.in_(['OWNER', 'ADMIN'])
        ).all()
        
        for member in members:
            existing = db.query(Notification).filter(
                Notification.user_id == member.user_id,
                Notification.notification_type == "MISSING_ISWC",
                Notification.organization_id == org.id,
                Notification.created_at > datetime.utcnow() - timedelta(days=7)
            ).first()
            
            if existing:
                continue
            
            notif = create_user_notification(
                db=db,
                user_id=member.user_id,
                notification_type="MISSING_ISWC",
                title=f"{len(missing_songs)} songs missing ISWC",
                message=f"Your catalog has {len(missing_songs)} songs without ISWC codes. Add ISWC codes for proper publishing rights tracking.",
                link="/catalog?filter=missing_iswc",
                organization_id=org.id
            )
            if notif:
                notifications_created += 1
    
    db.commit()
    return notifications_created

def run_weekly_health_summary(db: Session):
    from ..models.models import Organization
    
    orgs = db.query(Organization).all()
    notifications_created = 0
    
    for org in orgs:
        summary = generate_health_summary(db, org.id)
        if not summary:
            continue
            
        members = db.query(OrganizationMember).filter(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.role.in_(['OWNER', 'ADMIN'])
        ).all()
        
        for member in members:
            existing = db.query(Notification).filter(
                Notification.user_id == member.user_id,
                Notification.notification_type == "WEEKLY_HEALTH_SUMMARY",
                Notification.organization_id == org.id,
                Notification.created_at > datetime.utcnow() - timedelta(days=6)
            ).first()
            
            if existing:
                continue
            
            message = f"Catalog Health: {summary['average_health']}% average. "
            if summary['missing_isrc'] > 0:
                message += f"{summary['missing_isrc']} missing ISRC. "
            if summary['missing_iswc'] > 0:
                message += f"{summary['missing_iswc']} missing ISWC. "
            if summary['low_health_count'] > 0:
                message += f"{summary['low_health_count']} songs need attention."
            
            notif = create_user_notification(
                db=db,
                user_id=member.user_id,
                notification_type="WEEKLY_HEALTH_SUMMARY",
                title=f"Weekly Catalog Health Report",
                message=message,
                link="/reports",
                organization_id=org.id
            )
            if notif:
                notifications_created += 1
    
    db.commit()
    return notifications_created

def run_all_reminders(db: Session):
    results = {
        "missing_isrc": run_missing_isrc_reminders(db),
        "missing_iswc": run_missing_iswc_reminders(db),
        "weekly_summary": run_weekly_health_summary(db)
    }
    return results
