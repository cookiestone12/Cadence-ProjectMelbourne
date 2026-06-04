"""Add demo_qualifications table.

Revision ID: g1h2i3j4k5l6
Revises: 88494924f795, a227b1c2d3e4
Create Date: 2026-06-04 20:00:00.000000

Stores inbound /qualify form submissions for the demo-qualification flow.
"""
from alembic import op
import sqlalchemy as sa


revision = 'g1h2i3j4k5l6'
down_revision = ('88494924f795', 'a227b1c2d3e4')
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'demo_qualifications',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('work_email', sa.String(), nullable=False),
        sa.Column('company', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('catalog_coverage', sa.JSON(), nullable=True),
        sa.Column('catalog_size', sa.String(), nullable=True),
        sa.Column('current_management', sa.String(), nullable=True),
        sa.Column('goals', sa.JSON(), nullable=True),
        sa.Column('reason_now', sa.Text(), nullable=True),
        sa.Column('timeline', sa.String(), nullable=True),
        sa.Column('demo_notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_demo_qualifications_created_at', 'demo_qualifications', ['created_at'])
    op.create_index('ix_demo_qualifications_work_email', 'demo_qualifications', ['work_email'])


def downgrade():
    op.drop_index('ix_demo_qualifications_work_email', table_name='demo_qualifications')
    op.drop_index('ix_demo_qualifications_created_at', table_name='demo_qualifications')
    op.drop_table('demo_qualifications')
