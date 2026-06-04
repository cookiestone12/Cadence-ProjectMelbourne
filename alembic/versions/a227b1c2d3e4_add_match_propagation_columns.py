"""Add match-propagation columns to royalty_statement_lines.

Revision ID: a227b1c2d3e4
Revises: c3d4e5f6a7b8
Create Date: 2026-06-04 16:00:00.000000

Task #227 (Propagate a manual line match to all matching lines in a catalog).

When a user manually matches a statement line to a song, the decision cascades
to every other same-key line in the same organization. Cascaded lines are
tagged so the cascade is reversible:

- ``propagation_batch_id``     groups all lines linked by one cascade event.
- ``propagation_source_line_id`` points back to the line the user matched.
- ``propagation_prev``         snapshots each line's prior match state so an
                               undo restores it exactly.

All columns are nullable and additive; existing rows are unaffected.
"""
from alembic import op
import sqlalchemy as sa


revision = 'a227b1c2d3e4'
down_revision = 'c3d4e5f6a7b8'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('royalty_statement_lines', sa.Column('propagation_batch_id', sa.String(), nullable=True))
    op.add_column('royalty_statement_lines', sa.Column('propagation_source_line_id', sa.Integer(), nullable=True))
    op.add_column('royalty_statement_lines', sa.Column('propagation_prev', sa.JSON(), nullable=True))
    op.create_index(
        'ix_rsl_org_propagation_batch',
        'royalty_statement_lines',
        ['org_id', 'propagation_batch_id'],
    )


def downgrade():
    op.drop_index('ix_rsl_org_propagation_batch', table_name='royalty_statement_lines')
    op.drop_column('royalty_statement_lines', 'propagation_prev')
    op.drop_column('royalty_statement_lines', 'propagation_source_line_id')
    op.drop_column('royalty_statement_lines', 'propagation_batch_id')
