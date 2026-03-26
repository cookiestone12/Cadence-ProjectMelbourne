"""add_leads_table

Revision ID: 27cf62498320
Revises: 006e24381f33
Create Date: 2026-03-26 06:32:10.301144

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '27cf62498320'
down_revision: Union[str, Sequence[str], None] = '006e24381f33'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('leads',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('company', sa.String(), nullable=True),
    sa.Column('message', sa.Text(), nullable=True),
    sa.Column('lead_type', sa.String(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_leads_email'), 'leads', ['email'], unique=False)
    op.create_index(op.f('ix_leads_id'), 'leads', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_leads_id'), table_name='leads')
    op.drop_index(op.f('ix_leads_email'), table_name='leads')
    op.drop_table('leads')
