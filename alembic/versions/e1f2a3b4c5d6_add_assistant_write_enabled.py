"""Add assistant_write_enabled flag to organizations.

Revision ID: e1f2a3b4c5d6
Revises: d9e0f1a2b3c4
Create Date: 2026-05-02 09:00:00.000000

Task #196 (Cadence Assistant Optimization) — Phase 3A.

Adds an org-scoped feature flag controlling whether the in-app AI
assistant is allowed to propose write actions for that organisation.
Defaults to ``false`` for every existing org (opt-in via the
``Cadence AI Assistant`` toggle on the Settings page).
"""
from alembic import op
import sqlalchemy as sa


revision = 'e1f2a3b4c5d6'
down_revision = 'd9e0f1a2b3c4'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'organizations',
        sa.Column(
            'assistant_write_enabled',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
        ),
    )


def downgrade():
    op.drop_column('organizations', 'assistant_write_enabled')
