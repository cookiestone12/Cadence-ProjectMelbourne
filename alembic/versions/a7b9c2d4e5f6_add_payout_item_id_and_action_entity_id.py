"""add payout_item_id to royalty_ledger_entries and entity_id to action_items

Revision ID: a7b9c2d4e5f6
Revises: 006e24381f33
Create Date: 2026-04-17 12:00:00.000000

Adds two deterministic linkage columns used by the exhaustive
statement-delete flow:

- royalty_ledger_entries.payout_item_id  → payout_items.id
  Lets `delete_statement` resolve a PAYMENT ledger entry back to its
  originating PayoutItem by FK instead of by (payee, amount, time)
  heuristic. Populated going forward by record_payment_ledger().

- action_items.entity_id
  Lets `delete_statement` find STATEMENT-typed action items by id
  instead of by anchored title pattern. Populated going forward by
  generate_statement_action_items().

Both columns are NULLABLE so existing rows stay valid; the delete
flow falls back to the legacy heuristic / title-pattern only when
these columns are NULL.
"""
from alembic import op
import sqlalchemy as sa


revision = 'a7b9c2d4e5f6'
down_revision = '006e24381f33'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('royalty_ledger_entries') as batch:
        batch.add_column(sa.Column('payout_item_id', sa.Integer(), nullable=True))
        batch.create_foreign_key(
            'fk_royalty_ledger_entries_payout_item_id',
            'payout_items', ['payout_item_id'], ['id'],
        )
        batch.create_index(
            'ix_royalty_ledger_entries_payout_item_id',
            ['payout_item_id'],
        )

    with op.batch_alter_table('action_items') as batch:
        batch.add_column(sa.Column('entity_id', sa.Integer(), nullable=True))
        batch.create_index('ix_action_items_entity_id', ['entity_id'])


def downgrade():
    with op.batch_alter_table('action_items') as batch:
        batch.drop_index('ix_action_items_entity_id')
        batch.drop_column('entity_id')

    with op.batch_alter_table('royalty_ledger_entries') as batch:
        batch.drop_index('ix_royalty_ledger_entries_payout_item_id')
        batch.drop_constraint('fk_royalty_ledger_entries_payout_item_id', type_='foreignkey')
        batch.drop_column('payout_item_id')
