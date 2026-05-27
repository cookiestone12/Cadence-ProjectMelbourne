"""Task #204 — add organizations.welcome_email_enabled

Revision ID: a204b1c2d3e4
Revises: f199a1b2c3d4
Create Date: 2026-05-27
"""
from alembic import op
import sqlalchemy as sa


revision = "a204b1c2d3e4"
down_revision = "f199a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "organizations",
        sa.Column(
            "welcome_email_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade():
    op.drop_column("organizations", "welcome_email_enabled")
