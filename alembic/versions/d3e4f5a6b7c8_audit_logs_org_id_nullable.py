"""make audit_logs.organization_id nullable for platform-level events

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-04-17

"""
from alembic import op
import sqlalchemy as sa


revision = 'd3e4f5a6b7c8'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column(
        'audit_logs', 'organization_id',
        existing_type=sa.Integer(),
        nullable=True,
    )


def downgrade():
    op.alter_column(
        'audit_logs', 'organization_id',
        existing_type=sa.Integer(),
        nullable=False,
    )
