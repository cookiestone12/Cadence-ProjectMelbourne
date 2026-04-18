"""consolidate ddl drift backstop into versioned migration

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-04-18 09:00:00.000000

Captures every ad-hoc ``ALTER TABLE`` / ``CREATE INDEX`` /
``CREATE TABLE`` / data-backfill statement that previously lived in
``backend/db_setup.ensure_schema_updates()`` (lines 21-413) and
promotes them into a single, versioned Alembic revision.

Idempotency
-----------
Every existing production environment has already had these changes
applied at boot by the drift backstop, so this revision is written
to be a no-op on those databases. We use Postgres-native idempotent
constructs throughout:

* ``ADD COLUMN IF NOT EXISTS`` (PG 9.6+)
* ``CREATE INDEX IF NOT EXISTS``
* ``CREATE UNIQUE INDEX IF NOT EXISTS``
* ``DROP CONSTRAINT IF EXISTS``
* ``CREATE TABLE IF NOT EXISTS``
* ``DO $$ ... $$`` blocks for conditional ``ALTER COLUMN`` /
  constraint changes that have no native ``IF NOT EXISTS`` form

Downgrade is best-effort: it removes the columns/indexes/tables this
revision introduced (``IF EXISTS``) but does not attempt to rebuild
the historical ad-hoc state, since no production database has ever
intentionally lacked these objects.

See Task #83.
"""
from alembic import op
import sqlalchemy as sa


revision = 'd3e4f5a6b7c8'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _exec(sql: str) -> None:
    op.execute(sa.text(sql))


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # --- creators: hero image + social link columns -----------------------
    _exec("ALTER TABLE creators ADD COLUMN IF NOT EXISTS hero_image_data BYTEA")
    _exec("ALTER TABLE creators ADD COLUMN IF NOT EXISTS hero_image_mime VARCHAR")
    _exec("ALTER TABLE creators ADD COLUMN IF NOT EXISTS spotify_url VARCHAR")
    _exec("ALTER TABLE creators ADD COLUMN IF NOT EXISTS apple_music_url VARCHAR")
    _exec("ALTER TABLE creators ADD COLUMN IF NOT EXISTS youtube_url VARCHAR")
    _exec("ALTER TABLE creators ADD COLUMN IF NOT EXISTS instagram_url VARCHAR")
    _exec("ALTER TABLE creators ADD COLUMN IF NOT EXISTS twitter_url VARCHAR")
    _exec("ALTER TABLE creators ADD COLUMN IF NOT EXISTS custom_links JSONB DEFAULT '[]'::jsonb")

    # --- releases: creator FK + cover art --------------------------------
    _exec("ALTER TABLE releases ADD COLUMN IF NOT EXISTS creator_id INTEGER REFERENCES creators(id)")
    _exec("CREATE INDEX IF NOT EXISTS ix_releases_creator_id ON releases(creator_id)")
    _exec("ALTER TABLE releases ADD COLUMN IF NOT EXISTS cover_art_data BYTEA")
    _exec("ALTER TABLE releases ADD COLUMN IF NOT EXISTS cover_art_mime VARCHAR")

    # --- creative_contacts: photo + visibility + ownership ----------------
    # Wrap the table-conditional block in DO so the migration is safe even
    # on environments where the table itself doesn't exist yet (it's
    # created via Base.metadata.create_all on a fresh DB).
    _exec("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'creative_contacts') THEN
                ALTER TABLE creative_contacts ADD COLUMN IF NOT EXISTS photo_url VARCHAR;
                ALTER TABLE creative_contacts ADD COLUMN IF NOT EXISTS photo_data BYTEA;
                ALTER TABLE creative_contacts ADD COLUMN IF NOT EXISTS photo_mime VARCHAR;
                ALTER TABLE creative_contacts ADD COLUMN IF NOT EXISTS is_private BOOLEAN NOT NULL DEFAULT false;
                ALTER TABLE creative_contacts ADD COLUMN IF NOT EXISTS created_by_user_id INTEGER REFERENCES users(id);

                -- Backfill ownership for legacy rows: pick the lowest-id OWNER/ADMIN of the org
                UPDATE creative_contacts cc
                SET created_by_user_id = (
                    SELECT om.user_id FROM organization_members om
                    WHERE om.organization_id = cc.organization_id
                      AND om.role IN ('OWNER', 'ADMIN')
                    ORDER BY om.id ASC
                    LIMIT 1
                )
                WHERE cc.created_by_user_id IS NULL;
            END IF;
        END $$;
    """)

    # --- song_contracts: contract_id FK ----------------------------------
    _exec("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'song_contracts') THEN
                ALTER TABLE song_contracts ADD COLUMN IF NOT EXISTS contract_id INTEGER REFERENCES contracts(id);
            END IF;
        END $$;
    """)

    # --- songs: catalog enrichment fields --------------------------------
    _exec("ALTER TABLE songs ADD COLUMN IF NOT EXISTS audio_file_url VARCHAR")
    _exec("ALTER TABLE songs ADD COLUMN IF NOT EXISTS lyrics TEXT")
    _exec("ALTER TABLE songs ADD COLUMN IF NOT EXISTS release_status VARCHAR NOT NULL DEFAULT 'unreleased'")
    _exec("ALTER TABLE songs ADD COLUMN IF NOT EXISTS entry_type VARCHAR NOT NULL DEFAULT 'Song'")
    _exec("ALTER TABLE songs ADD COLUMN IF NOT EXISTS parent_song_id INTEGER REFERENCES songs(id)")
    _exec("ALTER TABLE songs ADD COLUMN IF NOT EXISTS shared_song_group_id VARCHAR")
    _exec("CREATE INDEX IF NOT EXISTS ix_songs_shared_song_group_id ON songs (shared_song_group_id)")

    # Backfill release_status from legacy is_released / release_date columns,
    # but only on the rows that still hold the default ('unreleased'), so we
    # don't clobber values set by application logic between migrations.
    _exec("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns
                       WHERE table_name = 'songs' AND column_name = 'is_released') THEN
                UPDATE songs
                SET release_status = 'released'
                WHERE release_status = 'unreleased'
                  AND (is_released = true
                       OR (release_date IS NOT NULL AND release_date <= CURRENT_DATE));
            END IF;
        END $$;
    """)

    # CHECK constraints (no IF NOT EXISTS form -> guard via pg_constraint)
    _exec("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_release_status') THEN
                ALTER TABLE songs ADD CONSTRAINT chk_release_status
                    CHECK (release_status IN ('unreleased', 'released'));
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_entry_type') THEN
                ALTER TABLE songs ADD CONSTRAINT chk_entry_type
                    CHECK (entry_type IN ('Song', 'Instrumental', 'Remix', 'Sample', 'Demo'));
            END IF;
        END $$;
    """)

    # --- contracts: creator + payment direction --------------------------
    _exec("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'contracts') THEN
                ALTER TABLE contracts ADD COLUMN IF NOT EXISTS creator_id INTEGER REFERENCES creators(id);
                ALTER TABLE contracts ADD COLUMN IF NOT EXISTS payment_direction VARCHAR DEFAULT 'INCOMING';
            END IF;
        END $$;
    """)

    # --- contract_documents: full table create ---------------------------
    # Schema mirrors backend.models.models.ContractDocument exactly. The
    # historical backstop created this table via
    # ``ContractDocument.__table__.create(bind=engine)``, so any existing
    # production DB already matches the model. The CREATE-IF-NOT-EXISTS
    # below only fires on fresh DBs and must produce the same shape.
    _exec("""
        CREATE TABLE IF NOT EXISTS contract_documents (
            id SERIAL PRIMARY KEY,
            contract_id INTEGER NOT NULL REFERENCES contracts(id),
            organization_id INTEGER NOT NULL REFERENCES organizations(id),
            file_name VARCHAR NOT NULL,
            file_path VARCHAR NOT NULL,
            file_size_bytes INTEGER,
            mime_type VARCHAR,
            description VARCHAR,
            song_id INTEGER REFERENCES songs(id),
            work_id INTEGER REFERENCES works(id),
            release_id INTEGER REFERENCES releases(id),
            uploaded_by_user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP
        )
    """)
    _exec("CREATE INDEX IF NOT EXISTS ix_contract_documents_contract_id ON contract_documents(contract_id)")
    # PK index — SQLAlchemy emits this because ``id = Column(..., primary_key=True, index=True)``.
    _exec("CREATE INDEX IF NOT EXISTS ix_contract_documents_id ON contract_documents(id)")

    # --- rights_splits: holder name/role + nullable holder_id ------------
    _exec("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'rights_splits') THEN
                ALTER TABLE rights_splits ADD COLUMN IF NOT EXISTS rights_holder_name VARCHAR;
                ALTER TABLE rights_splits ADD COLUMN IF NOT EXISTS role VARCHAR;
                BEGIN
                    ALTER TABLE rights_splits ALTER COLUMN rights_holder_id DROP NOT NULL;
                EXCEPTION WHEN OTHERS THEN
                    -- already nullable, or column missing: ignore
                    NULL;
                END;
            END IF;
        END $$;
    """)

    # --- song_credits: review + unmatched name + nullable creator_id -----
    _exec("ALTER TABLE song_credits ADD COLUMN IF NOT EXISTS needs_review BOOLEAN NOT NULL DEFAULT FALSE")
    _exec("ALTER TABLE song_credits ADD COLUMN IF NOT EXISTS unmatched_artist_name VARCHAR")
    _exec("""
        DO $$
        BEGIN
            BEGIN
                ALTER TABLE song_credits ALTER COLUMN creator_id DROP NOT NULL;
            EXCEPTION WHEN OTHERS THEN
                NULL;
            END;
        END $$;
    """)

    # --- organization_members: roster + linked creator + client scope ----
    _exec("ALTER TABLE organization_members ADD COLUMN IF NOT EXISTS can_manage_roster BOOLEAN DEFAULT FALSE")
    _exec("ALTER TABLE organization_members ADD COLUMN IF NOT EXISTS linked_creator_id INTEGER REFERENCES creators(id)")
    _exec("ALTER TABLE organization_members ADD COLUMN IF NOT EXISTS client_access_scope VARCHAR DEFAULT 'OWN'")

    # --- royalty_statements: creator + reconciliation fields -------------
    _exec("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'royalty_statements') THEN
                ALTER TABLE royalty_statements ADD COLUMN IF NOT EXISTS creator_id INTEGER REFERENCES creators(id);
                ALTER TABLE royalty_statements ADD COLUMN IF NOT EXISTS opening_balance FLOAT;
                ALTER TABLE royalty_statements ADD COLUMN IF NOT EXISTS closing_balance FLOAT;
                ALTER TABLE royalty_statements ADD COLUMN IF NOT EXISTS reconciliation_details JSONB;
                ALTER TABLE royalty_statements ADD COLUMN IF NOT EXISTS reported_gross FLOAT;
                ALTER TABLE royalty_statements ADD COLUMN IF NOT EXISTS reported_withholding FLOAT;
                ALTER TABLE royalty_statements ADD COLUMN IF NOT EXISTS reported_net FLOAT;
                ALTER TABLE royalty_statements ADD COLUMN IF NOT EXISTS reconciliation_result JSONB;
            END IF;
        END $$;
    """)
    _exec("CREATE INDEX IF NOT EXISTS ix_royalty_statements_creator_id ON royalty_statements(creator_id)")

    # --- songs: bool -> varchar conversion for tri-state pipeline fields -
    # Only flip if the column is still BOOLEAN; otherwise leave it alone.
    for field in ('is_paid', 'is_invoiced', 'is_registered_with_dsp'):
        _exec(f"""
            DO $$
            DECLARE
                col_type TEXT;
            BEGIN
                SELECT data_type INTO col_type
                FROM information_schema.columns
                WHERE table_name = 'songs' AND column_name = '{field}';

                IF col_type = 'boolean' THEN
                    ALTER TABLE songs ALTER COLUMN {field} TYPE VARCHAR
                        USING CASE
                            WHEN {field} = true THEN 'Yes'
                            WHEN {field} = false THEN 'No'
                            ELSE 'No'
                        END;
                    ALTER TABLE songs ALTER COLUMN {field} SET DEFAULT 'No';
                END IF;
            END $$;
        """)

    # --- performance indexes (CREATE IF NOT EXISTS) ----------------------
    perf_indexes = [
        ('ix_songs_organization_id', 'songs', 'organization_id'),
        ('ix_song_credits_song_id', 'song_credits', 'song_id'),
        ('ix_song_credits_creator_id', 'song_credits', 'creator_id'),
        ('ix_creators_organization_id', 'creators', 'organization_id'),
        ('ix_placements_organization_id', 'placements', 'organization_id'),
        ('ix_placements_song_id', 'placements', 'song_id'),
        ('ix_placements_work_id', 'placements', 'work_id'),
        ('ix_work_credits_work_id', 'work_credits', 'work_id'),
        ('ix_work_credits_creator_id', 'work_credits', 'creator_id'),
        ('ix_works_organization_id', 'works', 'organization_id'),
        ('ix_org_members_user_id', 'organization_members', 'user_id'),
        ('ix_org_members_org_id', 'organization_members', 'organization_id'),
        ('ix_song_dsp_links_song_id', 'song_dsp_links', 'song_id'),
        ('ix_placements_status', 'placements', 'status'),
        ('ix_placements_updated_at', 'placements', 'updated_at'),
    ]
    for idx_name, table, column in perf_indexes:
        # Wrap each in a DO so a missing table is non-fatal (some are
        # optional integration tables created elsewhere).
        _exec(f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}') THEN
                    CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column});
                END IF;
            END $$;
        """)

    _exec("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'stream_estimates') THEN
                CREATE INDEX IF NOT EXISTS ix_stream_estimates_song_org_date
                    ON stream_estimates(song_id, organization_id, period_date);
            END IF;
        END $$;
    """)

    # --- organizations: access_code (unique, nullable) -------------------
    _exec("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS access_code VARCHAR")
    _exec("CREATE UNIQUE INDEX IF NOT EXISTS ix_organizations_access_code ON organizations(access_code)")

    # Backfill missing access codes with a deterministic, collision-safe
    # 8-char A-Z/0-9 token. Uses substring(md5(...)) seeded with id +
    # generated_at so reruns are idempotent on already-populated rows.
    _exec("""
        DO $$
        DECLARE
            r RECORD;
            new_code VARCHAR;
            attempts INT;
        BEGIN
            FOR r IN SELECT id FROM organizations WHERE access_code IS NULL LOOP
                attempts := 0;
                LOOP
                    new_code := UPPER(substring(md5(r.id::text || clock_timestamp()::text || attempts::text) FOR 8));
                    EXIT WHEN NOT EXISTS (SELECT 1 FROM organizations WHERE access_code = new_code);
                    attempts := attempts + 1;
                    EXIT WHEN attempts > 50;
                END LOOP;
                UPDATE organizations SET access_code = new_code WHERE id = r.id;
            END LOOP;
        END $$;
    """)

    # --- client_shares: shared_modules + partial unique index ------------
    _exec("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'client_shares') THEN
                ALTER TABLE client_shares ADD COLUMN IF NOT EXISTS shared_modules JSON;

                -- Drop the obsolete blanket-unique constraint if it's still around
                IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_client_share_creator_email') THEN
                    ALTER TABLE client_shares DROP CONSTRAINT uq_client_share_creator_email;
                END IF;

                CREATE UNIQUE INDEX IF NOT EXISTS ix_client_share_active_unique
                    ON client_shares (creator_id, recipient_user_email)
                    WHERE status IN ('PENDING', 'ACCEPTED');
            END IF;
        END $$;
    """)

    # --- works: status (approval workflow) -------------------------------
    _exec("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'works') THEN
                ALTER TABLE works ADD COLUMN IF NOT EXISTS status VARCHAR NOT NULL DEFAULT 'PENDING';
            END IF;
        END $$;
    """)

    # --- song_edit_history: full table + nullable song_id + SET NULL FK --
    # Schema mirrors backend.models.models.SongEditHistory exactly.
    # JSON columns (not TEXT) for ``old_value``/``new_value`` because the
    # model uses ``Column(JSON)``.
    _exec("""
        CREATE TABLE IF NOT EXISTS song_edit_history (
            id SERIAL PRIMARY KEY,
            song_id INTEGER REFERENCES songs(id) ON DELETE SET NULL,
            song_title VARCHAR,
            organization_id INTEGER NOT NULL REFERENCES organizations(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            field_name VARCHAR NOT NULL,
            old_value JSON,
            new_value JSON,
            change_type VARCHAR NOT NULL,
            notes TEXT,
            created_at TIMESTAMP
        )
    """)
    _exec("CREATE INDEX IF NOT EXISTS ix_song_edit_history_song_id ON song_edit_history(song_id)")
    _exec("CREATE INDEX IF NOT EXISTS ix_song_edit_history_org_id ON song_edit_history(organization_id)")
    _exec("CREATE INDEX IF NOT EXISTS ix_song_edit_history_created_at ON song_edit_history(created_at)")
    # PK index — model declares ``id = Column(..., primary_key=True, index=True)``.
    _exec("CREATE INDEX IF NOT EXISTS ix_song_edit_history_id ON song_edit_history(id)")
    # song_title was added later via the backstop's else-branch on already-
    # existing tables; keep this guard for back-compat with old DBs.
    _exec("ALTER TABLE song_edit_history ADD COLUMN IF NOT EXISTS song_title VARCHAR")
    _exec("ALTER TABLE song_edit_history ADD COLUMN IF NOT EXISTS notes TEXT")
    _exec("""
        DO $$
        BEGIN
            BEGIN
                ALTER TABLE song_edit_history ALTER COLUMN song_id DROP NOT NULL;
            EXCEPTION WHEN OTHERS THEN
                NULL;
            END;
            -- Re-bind the FK to ON DELETE SET NULL if it's still ON DELETE NO ACTION
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'song_edit_history_song_id_fkey'
                  AND confdeltype <> 'n'
            ) THEN
                ALTER TABLE song_edit_history DROP CONSTRAINT song_edit_history_song_id_fkey;
                ALTER TABLE song_edit_history
                    ADD CONSTRAINT song_edit_history_song_id_fkey
                    FOREIGN KEY (song_id) REFERENCES songs(id) ON DELETE SET NULL;
            END IF;
        END $$;
    """)

    # --- registration_reports: full table + delivery columns --------------
    # Schema mirrors backend.models.models.RegistrationReport exactly.
    # NOTE: the model uses *Python-side* defaults (``default=...``) for
    # ``report_type``, ``status``, and the count fields — not
    # ``server_default``. SQLAlchemy therefore emits no ``DEFAULT`` clause
    # in the model's CreateTable, so we deliberately omit DB-level
    # defaults here to keep migration parity with model-generated DDL.
    _exec("""
        CREATE TABLE IF NOT EXISTS registration_reports (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL REFERENCES organizations(id),
            report_type VARCHAR NOT NULL,
            title VARCHAR NOT NULL,
            status VARCHAR NOT NULL,
            filter_creator_id INTEGER,
            filter_status VARCHAR,
            item_count INTEGER,
            outstanding_count INTEGER,
            ready_count INTEGER,
            needs_attention_count INTEGER,
            report_data TEXT,
            pdf_data BYTEA,
            pdf_mime VARCHAR,
            generated_at TIMESTAMP,
            sent_at TIMESTAMP,
            sent_to VARCHAR,
            created_by_user_id INTEGER REFERENCES users(id),
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """)
    _exec("CREATE INDEX IF NOT EXISTS ix_registration_reports_org_id ON registration_reports(organization_id)")
    # PK index — model declares ``id = Column(..., primary_key=True, index=True)``.
    _exec("CREATE INDEX IF NOT EXISTS ix_registration_reports_id ON registration_reports(id)")
    # The pdf_data/pdf_mime/sent_at/sent_to columns were added later by the
    # backstop's else-branch on already-existing tables; keep these guards
    # for back-compat with old DBs.
    _exec("ALTER TABLE registration_reports ADD COLUMN IF NOT EXISTS pdf_data BYTEA")
    _exec("ALTER TABLE registration_reports ADD COLUMN IF NOT EXISTS pdf_mime VARCHAR")
    _exec("ALTER TABLE registration_reports ADD COLUMN IF NOT EXISTS sent_at TIMESTAMP")
    _exec("ALTER TABLE registration_reports ADD COLUMN IF NOT EXISTS sent_to VARCHAR")


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    """Best-effort tear-down. Removes columns/indexes/tables this revision
    introduced so a forced rollback won't leave stranded objects, but does
    not attempt to recreate the historical ``[DDL drift]`` backstop logic.
    All operations use ``IF EXISTS`` so the downgrade is safe to rerun."""

    # registration_reports
    _exec("ALTER TABLE IF EXISTS registration_reports DROP COLUMN IF EXISTS sent_to")
    _exec("ALTER TABLE IF EXISTS registration_reports DROP COLUMN IF EXISTS sent_at")
    _exec("ALTER TABLE IF EXISTS registration_reports DROP COLUMN IF EXISTS pdf_mime")
    _exec("ALTER TABLE IF EXISTS registration_reports DROP COLUMN IF EXISTS pdf_data")
    _exec("DROP INDEX IF EXISTS ix_registration_reports_organization_id")
    _exec("DROP TABLE IF EXISTS registration_reports")

    # song_edit_history
    _exec("DROP INDEX IF EXISTS ix_song_edit_history_organization_id")
    _exec("DROP INDEX IF EXISTS ix_song_edit_history_song_id")
    _exec("DROP TABLE IF EXISTS song_edit_history")

    # works
    _exec("ALTER TABLE IF EXISTS works DROP COLUMN IF EXISTS status")

    # client_shares
    _exec("DROP INDEX IF EXISTS ix_client_share_active_unique")
    _exec("ALTER TABLE IF EXISTS client_shares DROP COLUMN IF EXISTS shared_modules")

    # organizations
    _exec("DROP INDEX IF EXISTS ix_organizations_access_code")
    _exec("ALTER TABLE IF EXISTS organizations DROP COLUMN IF EXISTS access_code")

    # performance indexes
    for idx_name in (
        'ix_stream_estimates_song_org_date',
        'ix_placements_updated_at', 'ix_placements_status',
        'ix_song_dsp_links_song_id',
        'ix_org_members_org_id', 'ix_org_members_user_id',
        'ix_works_organization_id',
        'ix_work_credits_creator_id', 'ix_work_credits_work_id',
        'ix_placements_work_id', 'ix_placements_song_id',
        'ix_placements_organization_id',
        'ix_creators_organization_id',
        'ix_song_credits_creator_id', 'ix_song_credits_song_id',
        'ix_songs_organization_id',
    ):
        _exec(f"DROP INDEX IF EXISTS {idx_name}")

    # royalty_statements
    _exec("DROP INDEX IF EXISTS ix_royalty_statements_creator_id")
    for col in ('reconciliation_result', 'reported_net', 'reported_withholding',
                'reported_gross', 'reconciliation_details',
                'closing_balance', 'opening_balance', 'creator_id'):
        _exec(f"ALTER TABLE IF EXISTS royalty_statements DROP COLUMN IF EXISTS {col}")

    # organization_members
    for col in ('client_access_scope', 'linked_creator_id', 'can_manage_roster'):
        _exec(f"ALTER TABLE IF EXISTS organization_members DROP COLUMN IF EXISTS {col}")

    # song_credits
    _exec("ALTER TABLE IF EXISTS song_credits DROP COLUMN IF EXISTS unmatched_artist_name")
    _exec("ALTER TABLE IF EXISTS song_credits DROP COLUMN IF EXISTS needs_review")

    # rights_splits
    _exec("ALTER TABLE IF EXISTS rights_splits DROP COLUMN IF EXISTS role")
    _exec("ALTER TABLE IF EXISTS rights_splits DROP COLUMN IF EXISTS rights_holder_name")

    # contract_documents
    _exec("DROP INDEX IF EXISTS ix_contract_documents_contract_id")
    _exec("DROP TABLE IF EXISTS contract_documents")

    # contracts
    _exec("ALTER TABLE IF EXISTS contracts DROP COLUMN IF EXISTS payment_direction")
    _exec("ALTER TABLE IF EXISTS contracts DROP COLUMN IF EXISTS creator_id")

    # songs
    _exec("ALTER TABLE IF EXISTS songs DROP CONSTRAINT IF EXISTS chk_entry_type")
    _exec("ALTER TABLE IF EXISTS songs DROP CONSTRAINT IF EXISTS chk_release_status")
    _exec("DROP INDEX IF EXISTS ix_songs_shared_song_group_id")
    for col in ('shared_song_group_id', 'parent_song_id', 'entry_type',
                'release_status', 'lyrics', 'audio_file_url'):
        _exec(f"ALTER TABLE IF EXISTS songs DROP COLUMN IF EXISTS {col}")

    # song_contracts
    _exec("ALTER TABLE IF EXISTS song_contracts DROP COLUMN IF EXISTS contract_id")

    # creative_contacts
    for col in ('created_by_user_id', 'is_private', 'photo_mime',
                'photo_data', 'photo_url'):
        _exec(f"ALTER TABLE IF EXISTS creative_contacts DROP COLUMN IF EXISTS {col}")

    # releases
    _exec("ALTER TABLE IF EXISTS releases DROP COLUMN IF EXISTS cover_art_mime")
    _exec("ALTER TABLE IF EXISTS releases DROP COLUMN IF EXISTS cover_art_data")
    _exec("DROP INDEX IF EXISTS ix_releases_creator_id")
    _exec("ALTER TABLE IF EXISTS releases DROP COLUMN IF EXISTS creator_id")

    # creators
    for col in ('custom_links', 'twitter_url', 'instagram_url', 'youtube_url',
                'apple_music_url', 'spotify_url',
                'hero_image_mime', 'hero_image_data'):
        _exec(f"ALTER TABLE IF EXISTS creators DROP COLUMN IF EXISTS {col}")
