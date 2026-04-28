"""add spotify_oauth_tokens singleton table

Revision ID: e4f5a6b7c8d9
Revises: 1d8f3d8a6a4d, d3e4f5a6b7c8
Create Date: 2026-04-27 23:00:00.000000

Backs the project-owned Spotify Authorization-Code OAuth flow that
replaces the Replit Spotify connector for user-authenticated calls.

The table is intended to hold a single row (the platform's connected
Spotify listener account). Multi-row support isn't needed today
because Spotify catalog/playlist reads are platform-wide and not
per-tenant.

Idempotent: ``CREATE TABLE IF NOT EXISTS`` so re-running on environments
that already have the table is safe.
"""
from alembic import op
import sqlalchemy as sa


revision = 'e4f5a6b7c8d9'
down_revision = ('1d8f3d8a6a4d', 'd3e4f5a6b7c8')
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS spotify_oauth_tokens (
            id SERIAL PRIMARY KEY,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            scope VARCHAR,
            token_expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            connected_user_display_name VARCHAR,
            connected_user_email VARCHAR,
            connected_user_spotify_id VARCHAR,
            connected_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT NOW()
        )
    """))
    op.execute(sa.text(
        "CREATE INDEX IF NOT EXISTS ix_spotify_oauth_tokens_id "
        "ON spotify_oauth_tokens (id)"
    ))


def downgrade():
    op.execute(sa.text("DROP TABLE IF EXISTS spotify_oauth_tokens"))
