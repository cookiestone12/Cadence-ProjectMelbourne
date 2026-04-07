"""add_resume_data_columns_to_leads

Revision ID: 1d8f3d8a6a4d
Revises: 27cf62498320
Create Date: 2026-04-07 04:18:17.566038

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '1d8f3d8a6a4d'
down_revision: Union[str, Sequence[str], None] = '27cf62498320'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('leads', sa.Column('resume_data', sa.LargeBinary(), nullable=True))
    op.add_column('leads', sa.Column('resume_filename', sa.String(), nullable=True))
    op.add_column('leads', sa.Column('resume_mime', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('leads', 'resume_mime')
    op.drop_column('leads', 'resume_filename')
    op.drop_column('leads', 'resume_data')
