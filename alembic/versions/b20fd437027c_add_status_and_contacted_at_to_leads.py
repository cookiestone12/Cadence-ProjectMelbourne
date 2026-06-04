"""Add status and contacted_at to leads.

Revision ID: b20fd437027c
Revises: f3b4c5d6e7a8
Create Date: 2026-06-04 13:00:00.000000

Task #220 — Lead outreach. Adds outreach tracking to the leads table:
`status` ("new" -> "contacted") so admins can see who has been emailed, and
`contacted_at` recording when the outbound email was sent. `status` defaults
to "new" server-side so existing rows backfill cleanly.
"""
from alembic import op
import sqlalchemy as sa


revision = 'b20fd437027c'
down_revision = 'f3b4c5d6e7a8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'leads',
        sa.Column(
            'status',
            sa.String(),
            nullable=False,
            server_default='new',
        ),
    )
    op.add_column(
        'leads',
        sa.Column('contacted_at', sa.DateTime(), nullable=True),
    )


def downgrade():
    op.drop_column('leads', 'contacted_at')
    op.drop_column('leads', 'status')
