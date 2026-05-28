"""Add onboarding_completed_at column to users.

Revision ID: f2a3b4c5d6e7
Revises: a3b4c5d6e7f8
Create Date: 2026-05-28 12:00:00.000000

Task #206 — Show every user a one-time onboarding tour after their first
login. Persist completion (or dismissal) timestamp on the users row so
the tour never reappears once the user has finished or skipped it.
"""
from alembic import op
import sqlalchemy as sa


revision = 'f2a3b4c5d6e7'
down_revision = 'a3b4c5d6e7f8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'users',
        sa.Column('onboarding_completed_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column('users', 'onboarding_completed_at')
