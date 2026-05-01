"""Drop legacy ``advance_pools`` table left behind in production.

Revision ID: d9e0f1a2b3c4
Revises: c6dddf556d5f
Create Date: 2026-05-01 12:10:00.000000

Background — Task #173 publish cleanup
--------------------------------------
The first production publish (2026-04-30) snapshot-shipped a database that
still contained the legacy ``advance_pools`` table with the v1 column shape
(``creator_id``, ``description``, ``amount_cents``, ``recouped_cents``,
``fully_recouped``, ``status``). The Task #169 consolidation
(``b7c8d9e0f1a2_consolidate_advance_models``) was meant to migrate that data
into the new ``advances`` table and drop ``advance_pools``, but that migration
never reached production through the publish flow — Replit's schema-diff UI
proposed an incompatible column-by-column rename plan instead, blocking the
next publish on a table containing a single throwaway test row.

Rather than run that bad rename plan and either corrupt the row or stall on
``NOT NULL`` adds without defaults, this migration drops the orphaned
``advance_pools`` table outright. The new ``advances`` table is created
fresh by the model auto-create logic that runs after Alembic on boot
(``backend/main.py`` deferred startup). The 1 stray test row is acceptable
data loss — confirmed empty of real customer data on 2026-05-01.

The migration is idempotent: ``IF EXISTS`` guards mean it is safe to run
against environments that already completed the proper consolidation and no
longer have ``advance_pools``.
"""
from alembic import op


revision = 'd9e0f1a2b3c4'
down_revision = 'c6dddf556d5f'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("DROP TABLE IF EXISTS advance_pools CASCADE")


def downgrade():
    # No downgrade — the legacy ``advance_pools`` v1 schema is dead and
    # any rows that lived in it have been consciously discarded.
    pass
