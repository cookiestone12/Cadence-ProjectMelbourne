"""add user_sessions table

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-04-17 22:11:00.000000

Tracks each issued JWT by token-hash so we can revoke active
sessions mid-token (e.g. on staff deprovision). See Task #74.
"""
from alembic import op
import sqlalchemy as sa


revision = 'c2d3e4f5a6b7'
down_revision = 'b1c2d3e4f5a6'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(),
                  sa.ForeignKey('users.id', ondelete='CASCADE'),
                  nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('ip_address', sa.String(length=64), nullable=True),
        sa.Column('user_agent', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_revoked', sa.Boolean(), nullable=False,
                  server_default=sa.false()),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_user_sessions_token_hash', 'user_sessions',
                    ['token_hash'], unique=True)
    op.create_index('ix_user_sessions_user_id', 'user_sessions',
                    ['user_id'])
    op.create_index('ix_user_sessions_expires_at', 'user_sessions',
                    ['expires_at'])


def downgrade():
    op.drop_index('ix_user_sessions_expires_at', table_name='user_sessions')
    op.drop_index('ix_user_sessions_user_id', table_name='user_sessions')
    op.drop_index('ix_user_sessions_token_hash', table_name='user_sessions')
    op.drop_table('user_sessions')
