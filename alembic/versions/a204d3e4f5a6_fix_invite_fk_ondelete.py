"""Task #204 — add ondelete behavior to organization_invites foreign keys.

Drops and recreates the FK constraints on organization_invites so that:
  - organization_id -> organizations.id ON DELETE CASCADE
  - invited_by_user_id -> users.id ON DELETE SET NULL

Revision ID: a204d3e4f5a6
Revises: a204c2d3e4f5
"""
from alembic import op


revision = "a204d3e4f5a6"
down_revision = "a204c2d3e4f5"
branch_labels = None
depends_on = None


def _drop_fks_by_referenced_table(table: str, referenced: str):
    """Drop every FK on `table` that references `referenced` (Postgres only)."""
    bind = op.get_bind()
    rows = bind.exec_driver_sql(
        """
        SELECT tc.constraint_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.constraint_column_usage ccu
          ON tc.constraint_name = ccu.constraint_name
         AND tc.constraint_schema = ccu.constraint_schema
        WHERE tc.table_name = %s
          AND tc.constraint_type = 'FOREIGN KEY'
          AND ccu.table_name = %s
        """,
        (table, referenced),
    ).fetchall()
    for (name,) in rows:
        op.drop_constraint(name, table, type_="foreignkey")


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    _drop_fks_by_referenced_table("organization_invites", "organizations")
    _drop_fks_by_referenced_table("organization_invites", "users")
    op.create_foreign_key(
        "fk_org_invites_org",
        "organization_invites", "organizations",
        ["organization_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_org_invites_inviter",
        "organization_invites", "users",
        ["invited_by_user_id"], ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    _drop_fks_by_referenced_table("organization_invites", "organizations")
    _drop_fks_by_referenced_table("organization_invites", "users")
    op.create_foreign_key(
        "fk_org_invites_org",
        "organization_invites", "organizations",
        ["organization_id"], ["id"],
    )
    op.create_foreign_key(
        "fk_org_invites_inviter",
        "organization_invites", "users",
        ["invited_by_user_id"], ["id"],
    )
