"""Add catalog_addon_packs column to organizations.

Revision ID: f3b4c5d6e7a8
Revises: f2a3b4c5d6e7
Create Date: 2026-06-04 12:00:00.000000

Task #213 — Enterprise vs Professional plans. Enterprise catalog capacity
scales in add-on packs of 5 above a base of 10 (10 -> 15 -> 20 -> ...). This
column stores how many add-on packs an org has. Defaults to 0 so existing
Enterprise orgs keep the base limit of 10; Professional orgs ignore it
(hard limit of 1 catalog).
"""
from alembic import op
import sqlalchemy as sa


revision = 'f3b4c5d6e7a8'
down_revision = 'f2a3b4c5d6e7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'organizations',
        sa.Column(
            'catalog_addon_packs',
            sa.Integer(),
            nullable=False,
            server_default='0',
        ),
    )


def downgrade():
    op.drop_column('organizations', 'catalog_addon_packs')
