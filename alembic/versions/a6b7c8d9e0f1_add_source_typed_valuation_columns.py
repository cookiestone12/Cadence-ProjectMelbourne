"""add source-typed valuation columns to valuation_calculations

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-04-30 00:30:00.000000

Adds nullable columns to ``valuation_calculations`` so the new
source-typed valuation engine (Task #162) can persist:

- per-bucket annualized revenue (performance / mechanical / sync /
  streaming / other) in cents,
- the multiplier applied to each bucket,
- artist (MASTER) vs publisher (PUBLISHING) share percentages
  derived from RightsSplit rows,
- artist / publisher dollar valuations,
- a ``valuation_method`` discriminator so the API can distinguish
  source-typed rows from legacy hybrid rows without renaming the
  existing ``valuation_methodology`` column (kept for back-compat).

All columns are nullable so legacy rows written by the old engine
remain valid without backfill.
"""
from alembic import op
import sqlalchemy as sa


revision = 'a6b7c8d9e0f1'
down_revision = 'f5a6b7c8d9e0'
branch_labels = None
depends_on = None


_NEW_INT_COLUMNS = [
    'revenue_performance_cents',
    'revenue_mechanical_cents',
    'revenue_sync_cents',
    'revenue_streaming_cents',
    'revenue_other_cents',
    'artist_valuation_cents',
    'publisher_valuation_cents',
]

_NEW_FLOAT_COLUMNS = [
    'multiplier_performance',
    'multiplier_mechanical',
    'multiplier_sync',
    'multiplier_streaming',
    'artist_share_pct',
    'publisher_share_pct',
]


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    existing = {col['name'] for col in insp.get_columns('valuation_calculations')}

    for name in _NEW_INT_COLUMNS:
        if name not in existing:
            op.add_column(
                'valuation_calculations',
                sa.Column(name, sa.Integer(), nullable=True),
            )

    for name in _NEW_FLOAT_COLUMNS:
        if name not in existing:
            op.add_column(
                'valuation_calculations',
                sa.Column(name, sa.Float(), nullable=True),
            )

    if 'valuation_method' not in existing:
        op.add_column(
            'valuation_calculations',
            sa.Column('valuation_method', sa.String(), nullable=True),
        )


def downgrade() -> None:
    for name in _NEW_INT_COLUMNS + _NEW_FLOAT_COLUMNS + ['valuation_method']:
        try:
            op.drop_column('valuation_calculations', name)
        except Exception:
            pass
