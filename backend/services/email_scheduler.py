import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger("rythm")

INTERVAL_HOURS = {
    "daily": 24,
    "every_3_days": 72,
    "weekly": 168,
    "biweekly": 336,
    "monthly": 720,
}

_scheduler = None


def check_and_send_digests():
    from ..models.database import SessionLocal
    from ..models import OrganizationMember, ActionItem
    from ..utils.priority_engine import sort_by_urgency, group_by_priority, filter_by_minimum_priority
    from .email_provider import get_email_provider

    db = SessionLocal()
    try:
        from ..models.models import EmailDigestPreference
        preferences = db.query(EmailDigestPreference).filter(
            EmailDigestPreference.email_digest_enabled == True
        ).all()

        now = datetime.utcnow()
        provider = get_email_provider()

        for pref in preferences:
            try:
                if pref.preferred_hour is not None and now.hour != pref.preferred_hour:
                    continue

                interval_hours = INTERVAL_HOURS.get(pref.schedule_interval, 168)
                if pref.last_email_sent_at:
                    next_send = pref.last_email_sent_at + timedelta(hours=interval_hours)
                    if now < next_send:
                        continue

                memberships = db.query(OrganizationMember).filter(
                    OrganizationMember.user_id == pref.user_id
                ).all()
                org_ids = [m.organization_id for m in memberships]

                if not org_ids:
                    continue

                min_priority = pref.min_priority_threshold or 4
                actions = db.query(ActionItem).filter(
                    ActionItem.organization_id.in_(org_ids),
                    ActionItem.status.in_(["PENDING", "IN_PROGRESS"]),
                    ActionItem.priority <= min_priority,
                ).all()

                if not actions:
                    continue

                sorted_actions = sort_by_urgency(actions)
                grouped = group_by_priority(sorted_actions)

                from ..models import User
                from ..templates.email_digest import generate_digest_html
                from ..utils.priority_engine import calculate_priority_score

                user_record = db.query(User).filter(User.id == pref.user_id).first()
                if not user_record or not user_record.email:
                    continue

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

                overdue_count = sum(
                    1 for a in actions
                    if a.deadline and a.deadline < now
                )
                summary_stats = {
                    "total_items": len(actions),
                    "overdue_count": overdue_count,
                    "critical_count": len(grouped.get("critical", [])),
                    "high_count": len(grouped.get("high", [])),
                }

                user_name = user_record.username or "User"
                html_body = generate_digest_html(user_name, grouped_items, summary_stats)

                success = provider.send_email(
                    to=user_record.email,
                    subject="Rythm Action Items Digest",
                    html_body=html_body,
                )

                if success:
                    pref.last_email_sent_at = now
                    db.commit()
                    logger.info(f"Digest email sent to user {pref.user_id}")

            except Exception as e:
                logger.error(f"Failed to process digest for user {pref.user_id}: {e}")
                db.rollback()
                continue
    except Exception as e:
        logger.error(f"Email digest scheduler error: {e}")
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return

    _scheduler = BackgroundScheduler()
    _scheduler.add_job(
        check_and_send_digests,
        "interval",
        minutes=15,
        id="email_digest_check",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Email digest scheduler started (15-minute interval)")


def shutdown_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Email digest scheduler shut down")
