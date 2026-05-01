"""consolidate Advance models: migrate v1 advances into advance_pools, drop v1 table, rename v2

Revision ID: b7c8d9e0f1a2
Revises: a6b7c8d9e0f1
Create Date: 2026-05-01 05:30:00.000000

Task #169 Phase 2 (Clean House) — finishes the long-running Advance v1 → v2 migration:

1. For every row in the legacy ``advances`` table:
   - look up (or create) a ``payees`` row keyed by ``(org_id, payee_type='CREATOR', creator_id)``,
   - INSERT a corresponding row into ``advance_pools`` mapping the v1 fields to the v2 schema
     (``description`` → ``advance_name``, ``amount_cents`` → ``principal_amount_cents``,
     ``amount_cents - recouped_cents`` → ``outstanding_balance_cents``, etc.).

2. Drop the FK from ``royalty_ledger_entries.advance_id`` that pointed at the old ``advances``
   table (this was the pre-existing alembic drift — the SQLAlchemy model already declared the
   target as ``advance_pools.id``).

3. Drop the legacy ``advances`` table and its indexes / sequence.

4. Rename ``advance_pools`` → ``advances`` (and rename its PK, indexes, sequence, FK constraints).

5. Re-add ``royalty_ledger_entries.advance_id`` FK pointing at the renamed ``advances`` table.

The downgrade re-creates the v1 ``advances`` table empty and renames ``advances`` back to
``advance_pools``. Data is *not* unmigrated — this is a one-way consolidation.
"""
from alembic import op
import sqlalchemy as sa
from datetime import date


revision = 'b7c8d9e0f1a2'
down_revision = 'a6b7c8d9e0f1'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()

    # ---------------------------------------------------------------
    # 1. Copy any rows from legacy `advances` into `advance_pools`,
    #    auto-creating a Payee per (org, creator) where missing.
    # ---------------------------------------------------------------
    legacy_rows = bind.execute(sa.text("""
        SELECT id, organization_id, creator_id, contract_id, description,
               amount_cents, recouped_cents, currency, advance_date,
               fully_recouped, status, notes, created_by_user_id,
               created_at, updated_at
        FROM advances
        ORDER BY id
    """)).mappings().all()

    for row in legacy_rows:
        # Find or create a Payee for this (org, creator).
        payee_id_row = bind.execute(sa.text("""
            SELECT id FROM payees
            WHERE org_id = :org_id AND creator_id = :creator_id
            LIMIT 1
        """), {"org_id": row["organization_id"], "creator_id": row["creator_id"]}).first()

        if payee_id_row:
            payee_id = payee_id_row[0]
        else:
            payee_id = bind.execute(sa.text("""
                INSERT INTO payees (org_id, payee_type, creator_id, created_at, updated_at)
                VALUES (:org_id, 'CREATOR', :creator_id, NOW(), NOW())
                RETURNING id
            """), {"org_id": row["organization_id"], "creator_id": row["creator_id"]}).scalar()

        outstanding = max((row["amount_cents"] or 0) - (row["recouped_cents"] or 0), 0)
        advance_name = row["description"] or f"Legacy advance #{row['id']}"
        # Fall back to today when the legacy row has a NULL advance_date — the
        # v2 schema requires a non-null value.
        advance_date = row["advance_date"] or date.today()

        bind.execute(sa.text("""
            INSERT INTO advance_pools (
                org_id, contract_id, payee_id,
                advance_name, advance_date, currency,
                principal_amount_cents, recoupable, recoupment_pool, recoupment_priority,
                cross_collateralize, outstanding_balance_cents,
                notes, created_by_user_id, created_at, updated_at
            ) VALUES (
                :org_id, :contract_id, :payee_id,
                :advance_name, :advance_date, :currency,
                :principal_amount_cents, TRUE, 'ALL', 1,
                FALSE, :outstanding_balance_cents,
                :notes, :created_by_user_id, COALESCE(:created_at, NOW()), COALESCE(:updated_at, NOW())
            )
        """), {
            "org_id": row["organization_id"],
            "contract_id": row["contract_id"],
            "payee_id": payee_id,
            "advance_name": advance_name,
            "advance_date": advance_date,
            "currency": row["currency"] or "USD",
            "principal_amount_cents": row["amount_cents"] or 0,
            "outstanding_balance_cents": outstanding,
            "notes": row["notes"],
            "created_by_user_id": row["created_by_user_id"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        })

    # ---------------------------------------------------------------
    # 2. Drop FK from royalty_ledger_entries.advance_id (legacy → advances).
    #    The SQLAlchemy model already declares advance_pools.id as the target,
    #    so this corrects pre-existing drift.
    # ---------------------------------------------------------------
    op.execute(
        "ALTER TABLE royalty_ledger_entries "
        "DROP CONSTRAINT IF EXISTS royalty_ledger_entries_advance_id_fkey"
    )

    # ---------------------------------------------------------------
    # 3. Drop the legacy `advances` table.
    # ---------------------------------------------------------------
    op.drop_index('ix_advances_creator_id', table_name='advances', if_exists=True)
    op.drop_index('ix_advances_id', table_name='advances', if_exists=True)
    op.drop_index('ix_advances_org_id', table_name='advances', if_exists=True)
    op.drop_table('advances')

    # ---------------------------------------------------------------
    # 4. Rename advance_pools → advances (and sequence / PK / indexes / FKs).
    # ---------------------------------------------------------------
    op.rename_table('advance_pools', 'advances')
    op.execute("ALTER SEQUENCE advance_pools_id_seq RENAME TO advances_id_seq")
    op.execute("ALTER INDEX advance_pools_pkey RENAME TO advances_pkey")
    op.execute("ALTER INDEX ix_advance_pools_id RENAME TO ix_advances_id")
    op.execute("ALTER INDEX ix_adv2_org_payee RENAME TO ix_advances_org_payee")
    op.execute("ALTER INDEX ix_adv2_org_contract RENAME TO ix_advances_org_contract")

    # Rename FK constraint names to match the new table.
    op.execute(
        "ALTER TABLE advances RENAME CONSTRAINT advance_pools_contract_id_fkey "
        "TO advances_contract_id_fkey"
    )
    op.execute(
        "ALTER TABLE advances RENAME CONSTRAINT advance_pools_payee_id_fkey "
        "TO advances_payee_id_fkey"
    )
    op.execute(
        "ALTER TABLE advances RENAME CONSTRAINT advance_pools_org_id_fkey "
        "TO advances_org_id_fkey"
    )
    op.execute(
        "ALTER TABLE advances RENAME CONSTRAINT advance_pools_created_by_user_id_fkey "
        "TO advances_created_by_user_id_fkey"
    )

    # ---------------------------------------------------------------
    # 5. Re-add FK from royalty_ledger_entries.advance_id → advances.id
    # ---------------------------------------------------------------
    op.create_foreign_key(
        'royalty_ledger_entries_advance_id_fkey',
        'royalty_ledger_entries',
        'advances',
        ['advance_id'],
        ['id'],
    )


def downgrade():
    # Drop FK then rename advances → advance_pools.
    op.execute(
        "ALTER TABLE royalty_ledger_entries "
        "DROP CONSTRAINT IF EXISTS royalty_ledger_entries_advance_id_fkey"
    )

    op.rename_table('advances', 'advance_pools')
    op.execute("ALTER SEQUENCE advances_id_seq RENAME TO advance_pools_id_seq")
    op.execute("ALTER INDEX advances_pkey RENAME TO advance_pools_pkey")
    op.execute("ALTER INDEX ix_advances_id RENAME TO ix_advance_pools_id")
    op.execute("ALTER INDEX ix_advances_org_payee RENAME TO ix_adv2_org_payee")
    op.execute("ALTER INDEX ix_advances_org_contract RENAME TO ix_adv2_org_contract")
    op.execute(
        "ALTER TABLE advance_pools RENAME CONSTRAINT advances_contract_id_fkey "
        "TO advance_pools_contract_id_fkey"
    )
    op.execute(
        "ALTER TABLE advance_pools RENAME CONSTRAINT advances_payee_id_fkey "
        "TO advance_pools_payee_id_fkey"
    )
    op.execute(
        "ALTER TABLE advance_pools RENAME CONSTRAINT advances_org_id_fkey "
        "TO advance_pools_org_id_fkey"
    )
    op.execute(
        "ALTER TABLE advance_pools RENAME CONSTRAINT advances_created_by_user_id_fkey "
        "TO advance_pools_created_by_user_id_fkey"
    )

    # Recreate empty legacy `advances` table for rollback compatibility.
    op.create_table(
        'advances',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('organization_id', sa.Integer(), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('creator_id', sa.Integer(), sa.ForeignKey('creators.id'), nullable=False),
        sa.Column('contract_id', sa.Integer(), sa.ForeignKey('contracts.id'), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('amount_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('recouped_cents', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(), server_default='USD'),
        sa.Column('advance_date', sa.Date(), nullable=True),
        sa.Column('fully_recouped', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('status', sa.String(), server_default='ACTIVE'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by_user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_advances_org_id', 'advances', ['organization_id'])
    op.create_index('ix_advances_creator_id', 'advances', ['creator_id'])

    op.create_foreign_key(
        'royalty_ledger_entries_advance_id_fkey',
        'royalty_ledger_entries',
        'advance_pools',
        ['advance_id'],
        ['id'],
    )
