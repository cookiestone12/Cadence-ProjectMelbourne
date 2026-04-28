"""add spotify_popularity cache columns to songs

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-04-28 21:00:00.000000

Adds two persistent columns on the ``songs`` table so popularity
lookups survive Spotify's daily Development-Mode quota window:

- ``spotify_popularity`` (smallint 0..100, nullable)
- ``spotify_popularity_fetched_at`` (timestamp, nullable)

Cadence's Credits-tab compute path was re-fetching popularity from
Spotify on every refresh. With ~100-credit creators (e.g. creator 98)
that fan-out exhausts the project-owned dev app's daily Web API
quota in a single page load, after which every subsequent
``/v1/tracks/{id}`` call returns HTTP 429 with a multi-hour
``Retry-After`` header and credits_service falls through to
``popularity = 0`` -> ``Total Estimated Streams: 0``.

With this cache, ``credits_service._batch_fetch_spotify_popularity``
prefers a fresh (<7 day) cached popularity per song and skips the
API call entirely. On Spotify failures (throttle, null, network)
it can also fall back to a stale cached value -- showing real
numbers rather than zero.

Both columns are nullable: existing rows simply have no cache yet
and will be populated on the next successful lookup.

Idempotent: ``ADD COLUMN IF NOT EXISTS`` so re-running on
environments that already have the columns is safe.
"""
from alembic import op
import sqlalchemy as sa


revision = 'f5a6b7c8d9e0'
down_revision = 'e4f5a6b7c8d9'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text(
        "ALTER TABLE songs "
        "ADD COLUMN IF NOT EXISTS spotify_popularity SMALLINT"
    ))
    op.execute(sa.text(
        "ALTER TABLE songs "
        "ADD COLUMN IF NOT EXISTS spotify_popularity_fetched_at "
        "TIMESTAMP WITHOUT TIME ZONE"
    ))


def downgrade():
    op.execute(sa.text(
        "ALTER TABLE songs DROP COLUMN IF EXISTS spotify_popularity_fetched_at"
    ))
    op.execute(sa.text(
        "ALTER TABLE songs DROP COLUMN IF EXISTS spotify_popularity"
    ))
