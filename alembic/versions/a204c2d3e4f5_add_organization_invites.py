"""Task #204 — add organization_invites table for tokenised invite acceptance

Revision ID: a204c2d3e4f5
Revises: a204b1c2d3e4
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa


revision = "a204c2d3e4f5"
down_revision = "a204b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "organization_invites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("organization_id", sa.Integer(),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="MEMBER"),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("invited_by_user_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("ix_org_invites_token", "organization_invites", ["token"], unique=True)
    op.create_index("ix_org_invites_email", "organization_invites", ["email"])
    op.create_index("ix_org_invites_org", "organization_invites", ["organization_id"])


def downgrade():
    op.drop_index("ix_org_invites_org", table_name="organization_invites")
    op.drop_index("ix_org_invites_email", table_name="organization_invites")
    op.drop_index("ix_org_invites_token", table_name="organization_invites")
    op.drop_table("organization_invites")
