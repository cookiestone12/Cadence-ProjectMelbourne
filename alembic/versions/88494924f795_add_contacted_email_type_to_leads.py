"""Add contacted_email_type to leads.

Revision ID: 88494924f795
Revises: b20fd437027c
Create Date: 2026-06-04 14:00:00.000000

Task #222 — outreach history. Records which outreach template was sent to a
lead ("qualify" or "demo_schedule") so admins can see, after the fact, which
email a contacted lead received. Nullable: only set once an outreach email is
sent; existing rows stay NULL.
"""
from alembic import op
import sqlalchemy as sa


revision = '88494924f795'
down_revision = 'b20fd437027c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'leads',
        sa.Column('contacted_email_type', sa.String(), nullable=True),
    )


def downgrade():
    op.drop_column('leads', 'contacted_email_type')
