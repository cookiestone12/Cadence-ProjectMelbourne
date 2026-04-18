"""Database setup script - runs migrations and seeds before app start."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import Base, engine
from backend.models.database import SessionLocal
from backend.models.models import User, ChecklistItem, Song, SongChecklistStatus, RightsSplit, ContractAsset
from backend.utils.logging_config import logger
from sqlalchemy import func


def _validate_sql_identifier(name: str) -> str:
    if not re.match(r'^[a-z][a-z0-9_]*$', name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


# Sentinel: only fire the deprecation warning once per process so a
# noisy startup doesn't bury other useful logs.
_BACKSTOP_WARNED = False


def ensure_schema_updates():
    """No-op shim.

    Historical context: this function used to apply ~390 lines of
    ad-hoc ``ALTER TABLE`` / ``CREATE INDEX`` / ``CREATE TABLE`` /
    data-backfill statements at every boot to defend production
    against drift. As of Alembic revision ``d3e4f5a6b7c8`` (Task
    #83) every one of those statements has been promoted into a
    versioned migration, so the backstop is no longer needed.

    The function is kept (rather than deleted) so that any external
    caller continues to work, and so that future drift can be caught
    here again if ever required. It logs a single deprecation
    warning per process and returns immediately.
    """
    global _BACKSTOP_WARNED
    if not _BACKSTOP_WARNED:
        logger.info(
            "ensure_schema_updates() is now a no-op shim. All historical "
            "DDL drift fixes were consolidated into Alembic revision "
            "d3e4f5a6b7c8 (Task #83). See DEPLOYMENT.md §8."
        )
        _BACKSTOP_WARNED = True
    return


def _generate_access_code():
    import string
    import random
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=8))


def _generate_missing_access_codes():
    from backend.models.models import Organization
    db = SessionLocal()
    try:
        orgs = db.query(Organization).filter(Organization.access_code.is_(None)).all()
        for org in orgs:
            code = _generate_access_code()
            while db.query(Organization).filter(Organization.access_code == code).first():
                code = _generate_access_code()
            org.access_code = code
        if orgs:
            db.commit()
            logger.info(f"Generated access codes for {len(orgs)} organizations")
    except Exception as e:
        db.rollback()
        logger.warning(f"Error generating access codes: {e}")
    finally:
        db.close()


def seed_super_admin():
    from backend.utils.auth import get_password_hash, verify_password
    from backend.models.models import Organization, OrganizationMember
    db = SessionLocal()
    try:
        from sqlalchemy import func
        existing = db.query(User).filter(func.lower(User.username) == 'masterpadmin').first()
        if not existing:
            admin = User(
                username='MasterPAdmin',
                email='admin@cadence-ci.com',
                hashed_password=get_password_hash('Male50Cent'),
                is_admin=True,
                is_super_admin=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            logger.info("MasterPAdmin super admin account created")
            existing = admin
        else:
            try:
                if not verify_password('Male50Cent', existing.hashed_password):
                    existing.hashed_password = get_password_hash('Male50Cent')
                    db.commit()
                    logger.info("MasterPAdmin password reset to documented value")
            except Exception as pw_err:
                logger.error(f"MasterPAdmin password verify/reset failed: {pw_err}")
                db.rollback()

        if existing:
            has_membership = db.query(OrganizationMember).filter(
                OrganizationMember.user_id == existing.id
            ).first()
            if not has_membership:
                first_org = db.query(Organization).order_by(Organization.id).first()
                if not first_org:
                    first_org = Organization(
                        name="Cadence",
                        display_name="Cadence",
                        type="LABEL",
                        account_type="ENTERPRISE",
                    )
                    db.add(first_org)
                    db.commit()
                    db.refresh(first_org)
                    logger.info(f"Created default organization '{first_org.name}'")
                membership = OrganizationMember(
                    organization_id=first_org.id,
                    user_id=existing.id,
                    role="OWNER"
                )
                db.add(membership)
                db.commit()
                logger.info(f"Added MasterPAdmin to organization '{first_org.name}' as OWNER")
    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding super admin: {e}")
    finally:
        db.close()


CHECKLIST_ITEMS_SEED = [
    {"code": "AD-02", "category": "ADMIN", "description": "Contract executed/signed", "weight": 15},
    {"code": "AD-03", "category": "ADMIN", "description": "Invoice submitted", "weight": 10},
    {"code": "LG-02", "category": "LEGAL", "description": "Publishing splits confirmed", "weight": 10},
    {"code": "MD-01", "category": "METADATA", "description": "ISRC assigned", "weight": 5},
    {"code": "MD-02", "category": "METADATA", "description": "ISWC assigned", "weight": 5},
    {"code": "MD-03", "category": "METADATA", "description": "Credits finalized", "weight": 5},
    {"code": "DSP-03", "category": "DSP", "description": "Spotify link verified", "weight": 5},
    {"code": "SY-01", "category": "SYNC", "description": "Registered with PRO", "weight": 10},
    {"code": "SY-03", "category": "SYNC", "description": "MLC registered", "weight": 5},
    {"code": "PY-01", "category": "PAYMENT", "description": "Payment received", "weight": 20},
]

REMOVED_CHECKLIST_CODES = ["AD-01", "LG-01", "DSP-01", "DSP-02", "SY-02"]


def seed_checklist_items():
    db = SessionLocal()
    try:
        removed_items = db.query(ChecklistItem).filter(
            ChecklistItem.code.in_(REMOVED_CHECKLIST_CODES)
        ).all()
        if removed_items:
            removed_ids = [item.id for item in removed_items]
            db.query(SongChecklistStatus).filter(
                SongChecklistStatus.checklist_item_id.in_(removed_ids)
            ).delete(synchronize_session=False)
            for item in removed_items:
                db.delete(item)
            db.commit()
            logger.info(f"Removed {len(removed_items)} deprecated checklist items and their statuses")

        existing_codes = {item.code for item in db.query(ChecklistItem).all()}
        added = 0
        for item_data in CHECKLIST_ITEMS_SEED:
            if item_data["code"] not in existing_codes:
                db.add(ChecklistItem(**item_data))
                added += 1
        if added:
            db.commit()
            logger.info(f"Seeded {added} checklist items")
    except Exception as e:
        db.rollback()
        logger.warning(f"Checklist item seeding error: {e}")
    finally:
        db.close()


def sync_stale_health_scores():
    db = SessionLocal()
    try:
        stale_songs = db.query(Song).filter(
            (Song.status_health_score == None) | (Song.status_health_score == 0.0)
        ).all()
        if not stale_songs:
            return
        from backend.utils.health_sync import sync_song_to_checklist
        for song in stale_songs:
            has_statuses = db.query(SongChecklistStatus).filter(
                SongChecklistStatus.song_id == song.id
            ).first()
            if not has_statuses:
                checklist_items = db.query(ChecklistItem).all()
                for item in checklist_items:
                    db.add(SongChecklistStatus(
                        song_id=song.id,
                        checklist_item_id=item.id,
                        status="NOT_STARTED"
                    ))
                db.flush()
            sync_song_to_checklist(db, song)
        db.commit()
        logger.info(f"Synced health scores for {len(stale_songs)} stale songs")
    except Exception as e:
        db.rollback()
        logger.warning(f"Health score sync error: {e}")
    finally:
        db.close()


def sync_release_status():
    from sqlalchemy import text as sa_text
    db = SessionLocal()
    try:
        spotify_fixed = db.execute(sa_text(
            "UPDATE songs SET is_released = true WHERE spotify_link IS NOT NULL AND spotify_link != '' AND is_released = false"
        ))
        fixed = db.execute(sa_text(
            "UPDATE songs SET release_status = 'released' WHERE is_released = true AND release_status != 'released'"
        ))
        fixed2 = db.execute(sa_text(
            "UPDATE songs SET release_status = 'unreleased' WHERE is_released = false AND release_status != 'unreleased'"
        ))
        total = spotify_fixed.rowcount + fixed.rowcount + fixed2.rowcount
        if total > 0:
            db.commit()
            logger.info(f"Synced release_status for {total} songs")
        else:
            db.rollback()
    except Exception as e:
        db.rollback()
        logger.warning(f"Release status sync error: {e}")
    finally:
        db.close()


def _run_alembic_under_lock():
    """Per Task #73 spec, the order is:
      1. Bootstrap migration_lock table
      2. Acquire lock (retry-poll if held by another process; abort
         startup non-zero if wait exceeds ceiling)
      3. alembic upgrade heads (FATAL on failure — must not fall
         through to backstop with partial state)
      4. Release lock in finally
    The idempotent DDL backstop runs AFTER this, outside the lock.
    """
    from backend.utils.migration_runner import (
        upgrade_to_heads,
        get_alembic_revision_info,
    )
    from backend.utils.migration_lock import (
        bootstrap_migration_lock_table,
        acquire_migration_lock,
        release_migration_lock,
    )
    import time as _time

    bootstrap_migration_lock_table(engine)

    WAIT_CEILING_SECONDS = 600
    POLL_INTERVAL_SECONDS = 2
    deadline = _time.monotonic() + WAIT_CEILING_SECONDS
    acquired = acquire_migration_lock(engine, revision_label="pending")

    if not acquired:
        logger.warning(
            f"Migration lock held; will retry every {POLL_INTERVAL_SECONDS}s "
            f"for up to {WAIT_CEILING_SECONDS}s."
        )
        while not acquired and _time.monotonic() < deadline:
            try:
                info = get_alembic_revision_info(engine)
                if info["is_up_to_date"]:
                    logger.info(
                        "Leader finished; schema at head "
                        f"({','.join(info['head_revisions'])}). Continuing without lock."
                    )
                    return
            except Exception as e:
                logger.warning(f"Wait-poll: revision check failed: {e}")
            _time.sleep(POLL_INTERVAL_SECONDS)
            acquired = acquire_migration_lock(engine, revision_label="pending")
            if acquired:
                logger.info("Lock released by previous owner; this process will migrate.")

        if not acquired:
            logger.error(
                f"Migration lock wait exceeded {WAIT_CEILING_SECONDS}s; aborting "
                "startup so this process does not serve traffic against an "
                "unmigrated schema."
            )
            raise SystemExit(2)

    try:
        upgrade_to_heads(engine)
    finally:
        revision_label = "unknown"
        try:
            post = get_alembic_revision_info(engine)
            revision_label = ",".join(post["current_revisions"]) or "unknown"
        except Exception as e:
            logger.warning(
                f"Could not introspect revision after upgrade: {e}. "
                "Releasing lock with revision_label='unknown'."
            )
        try:
            release_migration_lock(engine, revision_label=revision_label)
        except Exception as e:
            logger.error(
                f"release_migration_lock raised (will auto-clear after stale "
                f"timeout): {e}"
            )


def _run_ddl_backstop():
    """Idempotent DDL backstop — runs OUTSIDE the migration lock per
    Task #73 spec (lock -> alembic -> release -> backstop). Each
    block in ensure_schema_updates() emits a [DDL drift] WARNING so
    operators can pull the drift into Alembic over time.
    """
    try:
        Base.metadata.create_all(bind=engine, checkfirst=True)
        logger.info("Database tables created/verified")
    except Exception as e:
        logger.warning(f"Table creation warning (may be benign): {e}")
        from sqlalchemy import inspect
        inspector = inspect(engine)
        existing = set(inspector.get_table_names())
        logger.info(f"Existing tables: {len(existing)}")
        for table in Base.metadata.sorted_tables:
            if table.name not in existing:
                try:
                    table.create(bind=engine, checkfirst=True)
                    logger.info(f"Created missing table: {table.name}")
                except Exception as te:
                    logger.warning(f"Failed to create table {table.name}: {te}")

    try:
        ensure_schema_updates()
        logger.info("Schema updates completed")
    except Exception as e:
        logger.warning(f"Schema update check: {e}")


def main():
    logger.info("Starting database setup...")
    _run_alembic_under_lock()
    _run_ddl_backstop()
    seed_super_admin()
    seed_checklist_items()
    sync_stale_health_scores()
    sync_release_status()
    backfill_publishing_percentages()
    backfill_clean_statement_line_artists()
    logger.info("Database setup complete")


def backfill_clean_statement_line_artists():
    """Null out RoyaltyStatementLine.artist_name_raw values that are
    obviously not artist names (percentages, digit-only, lone punctuation,
    or anything with no alphabetic characters).

    Some statement parsers — most notably the BMI-style PDF path — used
    to write the writer/publisher share percentage into the artist
    column. Those junk values poison the fuzzy matcher. This backfill
    cleans them up in-place so existing statements behave correctly
    without requiring users to delete and re-upload.
    """
    from sqlalchemy import text
    db = SessionLocal()
    try:
        result = db.execute(text(
            "UPDATE royalty_statement_lines "
            "SET artist_name_raw = NULL "
            "WHERE artist_name_raw IS NOT NULL "
            "AND ("
            "  artist_name_raw !~ '[A-Za-z]' "
            "  OR REPLACE(REPLACE(REPLACE(TRIM(artist_name_raw), ',', ''), '$', ''), '%', '') "
            "     ~ '^-?[0-9]+(\\.[0-9]+)?$'"
            ")"
        ))
        affected = result.rowcount or 0
        if affected > 0:
            db.commit()
            logger.info(f"Cleaned {affected} statement line artist values that were not real names")
    except Exception as e:
        db.rollback()
        logger.warning(f"Statement line artist cleanup: {e}")
    finally:
        db.close()


def backfill_publishing_percentages():
    db = SessionLocal()
    try:
        song_pub_totals = db.query(
            ContractAsset.asset_id,
            func.sum(RightsSplit.share_percentage)
        ).join(
            RightsSplit, RightsSplit.contract_asset_id == ContractAsset.id
        ).filter(
            ContractAsset.asset_type == "SONG",
            RightsSplit.rights_type == "PUBLISHING",
        ).group_by(ContractAsset.asset_id).all()

        updated = 0
        for song_id, total_pub in song_pub_totals:
            song = db.query(Song).filter(Song.id == song_id).first()
            if song and song.publishing_percentage != float(total_pub):
                song.publishing_percentage = float(total_pub)
                updated += 1

        if updated > 0:
            db.commit()
            logger.info(f"Backfilled publishing_percentage for {updated} songs")
    except Exception as e:
        db.rollback()
        logger.warning(f"Publishing percentage backfill: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
