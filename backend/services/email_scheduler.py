import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler

logger = logging.getLogger("cadence")

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
                    subject="Cadence Action Items Digest",
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


def run_scheduled_scans():
    from ..models.database import SessionLocal
    from ..models import CreatorStorageLink, IntegrationAccount
    from . import scan_service

    db = SessionLocal()
    try:
        now = datetime.utcnow()
        links = db.query(CreatorStorageLink).filter(
            CreatorStorageLink.auto_scan_enabled == True,
        ).all()

        link_data = [(l.id, l.org_id, l.provider, l.auto_scan_frequency, l.last_scanned_at) for l in links]
    except Exception as e:
        logger.error(f"Scheduled scan query error: {e}")
        return
    finally:
        db.close()

    for link_id, org_id, provider, freq, last_scanned in link_data:
        try:
            hours = INTERVAL_HOURS.get(freq or "daily", 24)
            if last_scanned and (now - last_scanned) < timedelta(hours=hours):
                continue

            link_db = SessionLocal()
            try:
                integration = link_db.query(IntegrationAccount).filter(
                    IntegrationAccount.org_id == org_id,
                    IntegrationAccount.provider == provider,
                    IntegrationAccount.is_active == True,
                ).first()
                if not integration:
                    logger.warning(f"Skipping scan for link {link_id}: no active {provider} integration for org {org_id}")
                    continue

                result = scan_service.scan_creator_storage(org_id, link_id, link_db)
                logger.info(f"Scheduled scan for link {link_id}: {result['new_files']} new files found")
            finally:
                link_db.close()
        except Exception as e:
            logger.error(f"Scheduled scan failed for link {link_id}: {e}")


def flip_released_songs():
    from ..models.database import SessionLocal
    from ..models.models import Song
    from .audit_service import log_action
    from datetime import date as date_type

    db = SessionLocal()
    try:
        today = date_type.today()
        songs = db.query(Song).filter(
            Song.release_date <= today,
            Song.release_status == "unreleased",
        ).all()

        for song in songs:
            song.release_status = "released"
            song.is_released = True
            try:
                from ..models.models import AuditLog
                entry = AuditLog(
                    organization_id=song.organization_id,
                    user_id=None,
                    action="AUTO_RELEASED",
                    entity_type="SONG",
                    entity_id=song.id,
                    entity_name=song.title,
                    details={"trigger": "scheduled_release_date"},
                )
                db.add(entry)
            except Exception as e:
                logger.warning(f"Audit log failed for auto-release song {song.id}: {e}")

        if songs:
            db.commit()
            logger.info(f"Auto-released {len(songs)} songs based on release_date")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to flip released songs: {e}")
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
    _scheduler.add_job(
        run_scheduled_scans,
        "interval",
        hours=1,
        id="storage_scan_check",
        replace_existing=True,
    )
    from .chart_scheduler import run_chart_ingestion
    _scheduler.add_job(
        run_chart_ingestion,
        "interval",
        hours=4,
        id="chart_ingestion_check",
        replace_existing=True,
        next_run_time=datetime.now() + timedelta(minutes=5),
    )
    _scheduler.add_job(
        flip_released_songs,
        "cron",
        hour=0,
        minute=5,
        timezone="UTC",
        id="daily_release_flip",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("Email digest scheduler started (15-minute interval)")
    logger.info("Storage scan scheduler started (hourly check)")
    logger.info("Chart ingestion scheduler started (4-hour interval)")
    logger.info("Daily release flip scheduler started (00:05 UTC)")


def shutdown_scheduler():
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Email digest scheduler shut down")
