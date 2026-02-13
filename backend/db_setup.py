"""Database setup script - runs migrations and seeds before app start."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.models import Base, engine
from backend.models.database import SessionLocal
from backend.models.models import User
from backend.utils.logging_config import logger


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
            constraints = inspector.get_foreign_keys('rights_splits')
            for fk in constraints:
                if 'rights_holder_id' in fk.get('constrained_columns', []):
                    fk_name = fk.get('name')
                    if fk_name:
                        try:
                            conn.execute(text(f"ALTER TABLE rights_splits ALTER COLUMN rights_holder_id DROP NOT NULL"))
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

        bool_to_string_fields = ['is_paid', 'is_invoiced', 'is_registered_with_dsp']
        for field in bool_to_string_fields:
            if field in song_cols:
                col_type = str(song_cols[field]['type'])
                if 'BOOLEAN' in col_type.upper() or 'BOOL' in col_type.upper():
                    conn.execute(text(f"""
                        ALTER TABLE songs ALTER COLUMN {field} TYPE VARCHAR
                        USING CASE
                            WHEN {field} = true THEN 'Yes'
                            WHEN {field} = false THEN 'No'
                            ELSE 'No'
                        END
                    """))
                    conn.execute(text(f"ALTER TABLE songs ALTER COLUMN {field} SET DEFAULT 'No'"))
                    conn.commit()
                    logger.info(f"Converted songs.{field} from BOOLEAN to VARCHAR")

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
        for tbl in ['song_credits', 'creators', 'placements', 'work_credits', 'works', 'organization_members', 'song_dsp_links']:
            if tbl in inspector.get_table_names():
                existing_indexes.update(idx['name'] for idx in inspector.get_indexes(tbl))

        for idx_name, table, column in perf_indexes:
            if idx_name not in existing_indexes and table in inspector.get_table_names():
                try:
                    conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})"))
                    conn.commit()
                    logger.info(f"Created performance index {idx_name}")
                except Exception as e:
                    logger.warning(f"Could not create index {idx_name}: {e}")


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
                email='admin@rythm.app',
                hashed_password=get_password_hash('Male50Cent!'),
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
                        name="Rythm",
                        display_name="Rythm",
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
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    try:
        ensure_schema_updates()
        logger.info("Schema updates completed")
    except Exception as e:
        logger.warning(f"Schema update check: {e}")

    seed_super_admin()
    logger.info("Database setup complete")


if __name__ == "__main__":
    main()
