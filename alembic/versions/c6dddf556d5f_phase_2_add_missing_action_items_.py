"""phase 2 add missing action_items.placement_id FK

Revision ID: c6dddf556d5f
Revises: b7c8d9e0f1a2
Create Date: 2026-05-01 05:35:49.325751

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c6dddf556d5f'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_foreign_key(
        'action_items_placement_id_fkey',
        'action_items', 'placements',
        ['placement_id'], ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        'action_items_placement_id_fkey',
        'action_items',
        type_='foreignkey',
    )
