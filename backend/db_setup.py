"""Database setup script - runs migrations and seeds before app start."""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import Base, engine
from backend.models.database import SessionLocal
from backend.models.models import User
from backend.utils.logging_config import logger


def _validate_sql_identifier(name: str) -> str:
    if not re.match(r'^[a-z][a-z0-9_]*$', name):
        raise ValueError(f"Invalid SQL identifier: {name}")
    return name


def ensure_schema_updates():
    from sqlalchemy import text, inspect
    with engine.connect() as conn:
        inspector = inspect(engine)
        cols = [c['name'] for c in inspector.get_columns('creators')]
        if 'hero_image_data' not in cols:
            conn.execute(text("ALTER TABLE creators ADD COLUMN hero_image_data BYTEA"))
            conn.commit()
            logger.info("Added hero_image_data column to creators")
        if 'hero_image_mime' not in cols:
            conn.execute(text("ALTER TABLE creators ADD COLUMN hero_image_mime VARCHAR"))
            conn.commit()
            logger.info("Added hero_image_mime column to creators")

        release_cols = [c['name'] for c in inspector.get_columns('releases')]
        if 'creator_id' not in release_cols:
            conn.execute(text("ALTER TABLE releases ADD COLUMN creator_id INTEGER REFERENCES creators(id)"))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_releases_creator_id ON releases(creator_id)"))
            conn.commit()
            logger.info("Added creator_id column to releases")
        if 'cover_art_data' not in release_cols:
            conn.execute(text("ALTER TABLE releases ADD COLUMN cover_art_data BYTEA"))
            conn.execute(text("ALTER TABLE releases ADD COLUMN cover_art_mime VARCHAR"))
            conn.commit()
            logger.info("Added cover_art_data/cover_art_mime columns to releases")

        if 'creative_contacts' in inspector.get_table_names():
            cc_cols = [c['name'] for c in inspector.get_columns('creative_contacts')]
            cc_added = []
            if 'photo_url' not in cc_cols:
                conn.execute(text("ALTER TABLE creative_contacts ADD COLUMN photo_url VARCHAR"))
                cc_added.append('photo_url')
            if 'photo_data' not in cc_cols:
                conn.execute(text("ALTER TABLE creative_contacts ADD COLUMN photo_data BYTEA"))
                cc_added.append('photo_data')
            if 'photo_mime' not in cc_cols:
                conn.execute(text("ALTER TABLE creative_contacts ADD COLUMN photo_mime VARCHAR"))
                cc_added.append('photo_mime')
            if cc_added:
                conn.commit()
                logger.info(f"Added {'/'.join(cc_added)} columns to creative_contacts")

        if 'song_contracts' in inspector.get_table_names():
            sc_cols = [c['name'] for c in inspector.get_columns('song_contracts')]
            if 'contract_id' not in sc_cols:
                conn.execute(text("ALTER TABLE song_contracts ADD COLUMN contract_id INTEGER REFERENCES contracts(id)"))
                conn.commit()
                logger.info("Added contract_id column to song_contracts")

        song_cols = {c['name']: c for c in inspector.get_columns('songs')}
        if 'audio_file_url' not in song_cols:
            conn.execute(text("ALTER TABLE songs ADD COLUMN audio_file_url VARCHAR"))
            conn.commit()
            logger.info("Added audio_file_url column to songs")
        if 'lyrics' not in song_cols:
            conn.execute(text("ALTER TABLE songs ADD COLUMN lyrics TEXT"))
            conn.commit()
            logger.info("Added lyrics column to songs")
        if 'contract_documents' not in inspector.get_table_names():
            from backend.models.models import ContractDocument
            ContractDocument.__table__.create(bind=engine)
            logger.info("Created contract_documents table")

        if 'contracts' in inspector.get_table_names():
            contract_cols = [c['name'] for c in inspector.get_columns('contracts')]
            if 'creator_id' not in contract_cols:
                conn.execute(text("ALTER TABLE contracts ADD COLUMN creator_id INTEGER REFERENCES creators(id)"))
                conn.commit()
                logger.info("Added creator_id column to contracts")
            if 'payment_direction' not in contract_cols:
                conn.execute(text("ALTER TABLE contracts ADD COLUMN payment_direction VARCHAR DEFAULT 'INCOMING'"))
                conn.commit()
                logger.info("Added payment_direction column to contracts")

        if 'rights_splits' in inspector.get_table_names():
            rs_cols = [c['name'] for c in inspector.get_columns('rights_splits')]
            if 'rights_holder_name' not in rs_cols:
                conn.execute(text("ALTER TABLE rights_splits ADD COLUMN rights_holder_name VARCHAR"))
                conn.commit()
                logger.info("Added rights_holder_name column to rights_splits")
            if 'role' not in rs_cols:
                conn.execute(text("ALTER TABLE rights_splits ADD COLUMN role VARCHAR"))
                conn.commit()
                logger.info("Added role column to rights_splits")
            constraints = inspector.get_foreign_keys('rights_splits')
            for fk in constraints:
                if 'rights_holder_id' in fk.get('constrained_columns', []):
                    fk_name = fk.get('name')
                    if fk_name:
                        try:
                            conn.execute(text("ALTER TABLE rights_splits ALTER COLUMN rights_holder_id DROP NOT NULL"))
                            conn.commit()
                            logger.info("Made rights_holder_id nullable in rights_splits")
                        except Exception:
                            pass
                    break

        creator_new_fields = {
            'spotify_url': 'VARCHAR',
            'apple_music_url': 'VARCHAR',
            'youtube_url': 'VARCHAR',
            'instagram_url': 'VARCHAR',
            'twitter_url': 'VARCHAR',
            'custom_links': 'JSONB DEFAULT \'[]\'::jsonb',
        }
        for field, col_type in creator_new_fields.items():
            if field not in cols:
                conn.execute(text(f"ALTER TABLE creators ADD COLUMN {field} {col_type}"))
                conn.commit()
                logger.info(f"Added {field} column to creators")

        om_cols = [c['name'] for c in inspector.get_columns('organization_members')]
        if 'can_manage_roster' not in om_cols:
            conn.execute(text("ALTER TABLE organization_members ADD COLUMN can_manage_roster BOOLEAN DEFAULT FALSE"))
            conn.commit()
            logger.info("Added can_manage_roster column to organization_members")
        if 'linked_creator_id' not in om_cols:
            conn.execute(text("ALTER TABLE organization_members ADD COLUMN linked_creator_id INTEGER REFERENCES creators(id)"))
            conn.commit()
            logger.info("Added linked_creator_id column to organization_members")

        if 'royalty_statements' in inspector.get_table_names():
            rs_cols = [c['name'] for c in inspector.get_columns('royalty_statements')]
            if 'creator_id' not in rs_cols:
                conn.execute(text("ALTER TABLE royalty_statements ADD COLUMN creator_id INTEGER REFERENCES creators(id)"))
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_royalty_statements_creator_id ON royalty_statements(creator_id)"))
                conn.commit()
                logger.info("Added creator_id column to royalty_statements")

        bool_to_string_fields = ['is_paid', 'is_invoiced', 'is_registered_with_dsp']
        for field in bool_to_string_fields:
            safe_field = _validate_sql_identifier(field)
            if safe_field in song_cols:
                col_type = str(song_cols[safe_field]['type'])
                if 'BOOLEAN' in col_type.upper() or 'BOOL' in col_type.upper():
                    alter_type_sql = (
                        f"ALTER TABLE songs ALTER COLUMN {safe_field} TYPE VARCHAR "
                        f"USING CASE "
                        f"WHEN {safe_field} = true THEN 'Yes' "
                        f"WHEN {safe_field} = false THEN 'No' "
                        f"ELSE 'No' END"
                    )  # safe: safe_field is from a hardcoded list, validated by _validate_sql_identifier (DDL identifiers cannot be parameterized)
                    conn.execute(text(alter_type_sql))
                    alter_default_sql = f"ALTER TABLE songs ALTER COLUMN {safe_field} SET DEFAULT 'No'"  # safe: same as above
                    conn.execute(text(alter_default_sql))
                    conn.commit()
                    logger.info(f"Converted songs.{safe_field} from BOOLEAN to VARCHAR")

        perf_indexes = [
            ("ix_songs_organization_id", "songs", "organization_id"),
            ("ix_song_credits_song_id", "song_credits", "song_id"),
            ("ix_song_credits_creator_id", "song_credits", "creator_id"),
            ("ix_creators_organization_id", "creators", "organization_id"),
            ("ix_placements_organization_id", "placements", "organization_id"),
            ("ix_placements_song_id", "placements", "song_id"),
            ("ix_placements_work_id", "placements", "work_id"),
            ("ix_work_credits_work_id", "work_credits", "work_id"),
            ("ix_work_credits_creator_id", "work_credits", "creator_id"),
            ("ix_works_organization_id", "works", "organization_id"),
            ("ix_org_members_user_id", "organization_members", "user_id"),
            ("ix_org_members_org_id", "organization_members", "organization_id"),
            ("ix_song_dsp_links_song_id", "song_dsp_links", "song_id"),
            ("ix_placements_status", "placements", "status"),
            ("ix_placements_updated_at", "placements", "updated_at"),
        ]
        existing_indexes = {idx['name'] for idx in inspector.get_indexes('songs')}
        for tbl in ['song_credits', 'creators', 'placements', 'work_credits', 'works', 'organization_members', 'song_dsp_links', 'stream_estimates']:
            if tbl in inspector.get_table_names():
                existing_indexes.update(idx['name'] for idx in inspector.get_indexes(tbl))

        for idx_name, table, column in perf_indexes:
            if idx_name not in existing_indexes and table in inspector.get_table_names():
                try:
                    safe_idx = _validate_sql_identifier(idx_name)
                    safe_tbl = _validate_sql_identifier(table)
                    safe_col = _validate_sql_identifier(column)
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {safe_idx} ON {safe_tbl}({safe_col})"))
                    conn.commit()
                    logger.info(f"Created performance index {idx_name}")
                except Exception as e:
                    logger.warning(f"Could not create index {idx_name}: {e}")

        if 'stream_estimates' in inspector.get_table_names():
            composite_idx = "ix_stream_estimates_song_org_date"
            if composite_idx not in existing_indexes:
                try:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {composite_idx} ON stream_estimates(song_id, organization_id, period_date)"))
                    conn.commit()
                    logger.info(f"Created composite index {composite_idx}")
                except Exception as e:
                    logger.warning(f"Could not create composite index: {e}")

        om_cols = [c['name'] for c in inspector.get_columns('organization_members')]
        if 'client_access_scope' not in om_cols:
            conn.execute(text("ALTER TABLE organization_members ADD COLUMN client_access_scope VARCHAR DEFAULT 'OWN'"))
            conn.commit()
            logger.info("Added client_access_scope column to organization_members")

        org_cols = [c['name'] for c in inspector.get_columns('organizations')]
        if 'access_code' not in org_cols:
            conn.execute(text("ALTER TABLE organizations ADD COLUMN access_code VARCHAR"))
            conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_organizations_access_code ON organizations(access_code)"))
            conn.commit()
            logger.info("Added access_code column to organizations")

        _generate_missing_access_codes()

        try:
            existing_constraints = inspector.get_unique_constraints('client_shares')
            has_old_constraint = any(c['name'] == 'uq_client_share_creator_email' for c in existing_constraints)
            if has_old_constraint:
                conn.execute(text("ALTER TABLE client_shares DROP CONSTRAINT uq_client_share_creator_email"))
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_client_share_active_unique "
                    "ON client_shares (creator_id, recipient_user_email) "
                    "WHERE status IN ('PENDING', 'ACCEPTED')"
                ))
                conn.commit()
                logger.info("Replaced uq_client_share_creator_email with partial unique index ix_client_share_active_unique")
            else:
                conn.execute(text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS ix_client_share_active_unique "
                    "ON client_shares (creator_id, recipient_user_email) "
                    "WHERE status IN ('PENDING', 'ACCEPTED')"
                ))
                conn.commit()
        except Exception as e:
            logger.warning(f"Client share constraint migration note: {e}")

        if 'royalty_statements' in inspector.get_table_names():
            rs_cols = [c['name'] for c in inspector.get_columns('royalty_statements')]
            rs_new_fields = {
                'opening_balance': 'FLOAT',
                'closing_balance': 'FLOAT',
                'reconciliation_details': 'JSONB',
                'reported_gross': 'FLOAT',
                'reported_withholding': 'FLOAT',
                'reported_net': 'FLOAT',
                'reconciliation_result': 'JSONB',
            }
            for field, col_type in rs_new_fields.items():
                if field not in rs_cols:
                    safe_field = _validate_sql_identifier(field)
                    conn.execute(text(f"ALTER TABLE royalty_statements ADD COLUMN {safe_field} {col_type}"))
                    conn.commit()
                    logger.info(f"Added {field} column to royalty_statements")

        if 'registration_reports' not in inspector.get_table_names():
            try:
                from backend.models.models import RegistrationReport
                RegistrationReport.__table__.create(bind=engine, checkfirst=True)
                logger.info("Created registration_reports table")
            except Exception as e:
                logger.warning(f"Could not create registration_reports table: {e}")
        else:
            rr_cols = {c['name'] for c in inspector.get_columns('registration_reports')}
            for col_name, col_type in [('pdf_data', 'BYTEA'), ('pdf_mime', 'VARCHAR'), ('sent_at', 'TIMESTAMP'), ('sent_to', 'VARCHAR')]:
                if col_name not in rr_cols:
                    try:
                        with engine.connect() as conn:
                            conn.execute(text(f"ALTER TABLE registration_reports ADD COLUMN {col_name} {col_type}"))
                            conn.commit()
                        logger.info(f"Added {col_name} to registration_reports")
                    except Exception as e:
                        logger.warning(f"Could not add {col_name} to registration_reports: {e}")


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
    from backend.utils.auth import get_password_hash
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


def main():
    logger.info("Starting database setup...")
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

    seed_super_admin()
    logger.info("Database setup complete")


if __name__ == "__main__":
    main()
