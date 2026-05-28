"""Add must_change_password flag to users.

Revision ID: a3b4c5d6e7f8
Revises: a204d3e4f5a6
Create Date: 2026-05-27 10:00:00.000000

Task #207 — Force users to change a temporary password before they
can use the app. Admin-provisioned accounts have this flag set; the
user is locked to the change-password screen on login until they
rotate the credential, at which point the flag clears.
"""
from alembic import op
import sqlalchemy as sa


revision = "a3b4c5d6e7f8"
down_revision = "a204d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade():
    op.drop_column("users", "must_change_password")
