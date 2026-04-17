"""add is_cadence_staff to users

Revision ID: b1c2d3e4f5a6
Revises: a7b9c2d4e5f6
Create Date: 2026-04-17 22:10:00.000000

Adds the staff-tier flag for Cadence employees (engineers, support,
ops). Staff get read access to all organizations; write access still
requires master admin or org-scoped OWNER/ADMIN. See Task #74.
"""
from alembic import op
import sqlalchemy as sa


revision = 'b1c2d3e4f5a6'
down_revision = 'a7b9c2d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column(
            'is_cadence_staff', sa.Boolean(), nullable=False,
            server_default=sa.false(),
        ))


def downgrade():
    with op.batch_alter_table('users') as batch:
        batch.drop_column('is_cadence_staff')
