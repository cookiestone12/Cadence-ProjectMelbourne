"""Task #204 — add ondelete behavior to organization_invites foreign keys.

Drops and recreates the FK constraints on organization_invites so that:
  - organization_id -> organizations.id ON DELETE CASCADE
  - invited_by_user_id -> users.id ON DELETE SET NULL

Idempotent: works whether the table was created by the (now-fixed)
a204c2d3e4f5 migration (with ondelete already inline) or by the
historical version (without ondelete).

Revision ID: a204d3e4f5a6
Revises: a204c2d3e4f5
"""
from alembic import op


revision = "a204d3e4f5a6"
down_revision = "a204c2d3e4f5"
branch_labels = None
depends_on = None


def _reset_invite_fks(ondelete_org: str, ondelete_user: str):
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    # Drop ALL FKs on organization_invites that reference organizations/users.
    # DISTINCT + IF EXISTS makes this safe against JOIN fanout in
    # information_schema and against partial prior runs.
    op.execute(
        """
        DO $$
        DECLARE r record;
        BEGIN
          FOR r IN
            SELECT DISTINCT tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.constraint_column_usage ccu
              ON tc.constraint_name = ccu.constraint_name
             AND tc.constraint_schema = ccu.constraint_schema
            WHERE tc.table_name = 'organization_invites'
              AND tc.constraint_type = 'FOREIGN KEY'
              AND ccu.table_name IN ('organizations', 'users')
          LOOP
            EXECUTE format(
              'ALTER TABLE organization_invites DROP CONSTRAINT IF EXISTS %I',
              r.constraint_name
            );
          END LOOP;
        END$$;
        """
    )
    _ = bind  # bind kept for dialect gate only
    op.create_foreign_key(
        "fk_org_invites_org",
        "organization_invites", "organizations",
        ["organization_id"], ["id"],
        ondelete=ondelete_org or None,
    )
    op.create_foreign_key(
        "fk_org_invites_inviter",
        "organization_invites", "users",
        ["invited_by_user_id"], ["id"],
        ondelete=ondelete_user or None,
    )


def upgrade():
    _reset_invite_fks("CASCADE", "SET NULL")


def downgrade():
    _reset_invite_fks("", "")
