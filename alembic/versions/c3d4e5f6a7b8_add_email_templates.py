"""Add email_templates table for admin-editable outreach emails.

Revision ID: c3d4e5f6a7b8
Revises: b20fd437027c
Create Date: 2026-06-04 14:30:00.000000

Adds the `email_templates` table that stores the subject, header, and body for
the lead-outreach emails (waitlist qualifier + demo confirmation) so platform
admins can edit the wording from the admin UI without a code change. The two
default templates are seeded with the previously-hardcoded copy so existing
behaviour is preserved.
"""
from alembic import op
import sqlalchemy as sa


revision = 'c3d4e5f6a7b8'
down_revision = 'b20fd437027c'
branch_labels = None
depends_on = None


_QUALIFY_BODY = (
    "Hi {first_name},\n\n"
    "Thank you for joining the Cadence waitlist. We are glad you are here.\n\n"
    "Cadence is a catalog management and royalty intelligence platform built "
    "for music companies that are serious about their rights data. We help "
    "labels, publishers, and creators keep their catalog, royalties, and "
    "rights organized and working harder.\n\n"
    "Before we reach out to schedule a call, we want to make sure Cadence is "
    "the right fit for you. Two quick questions:\n\n"
    "1. What best describes your organization (label, publisher, production "
    "company, independent artist, or other)?\n"
    "2. Roughly how many songs or works are in your active catalog?\n\n"
    "Hit reply and let us know. We read every response.\n\n"
    "The Cadence Team"
)

_DEMO_BODY = (
    "Hi {first_name},\n\n"
    "Thank you for requesting a demo of Cadence. We have your information and "
    "you are next on the list.\n\n"
    "Expect an email from our team shortly with a link to book your "
    "walkthrough. The session runs about 30 minutes and covers catalog "
    "management, royalty processing, and rights administration, tailored to "
    "your organization type.\n\n"
    "If you have any questions in the meantime, just reply to this email.\n\n"
    "The Cadence Team"
)


def upgrade():
    op.create_table(
        'email_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('template_key', sa.String(), nullable=False),
        sa.Column('lead_type', sa.String(), nullable=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('subject', sa.String(), nullable=False),
        sa.Column('header', sa.String(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_email_templates_id', 'email_templates', ['id'])
    op.create_index('ix_email_templates_template_key', 'email_templates', ['template_key'], unique=True)

    email_templates = sa.table(
        'email_templates',
        sa.column('template_key', sa.String),
        sa.column('lead_type', sa.String),
        sa.column('name', sa.String),
        sa.column('subject', sa.String),
        sa.column('header', sa.String),
        sa.column('body', sa.Text),
        sa.column('is_active', sa.Boolean),
    )
    op.bulk_insert(email_templates, [
        {
            'template_key': 'qualify',
            'lead_type': 'WAITLIST',
            'name': 'Waitlist qualifier',
            'subject': "You're on the Cadence waitlist",
            'header': "You're on the list",
            'body': _QUALIFY_BODY,
            'is_active': True,
        },
        {
            'template_key': 'demo_schedule',
            'lead_type': 'DEMO_REQUEST',
            'name': 'Demo confirmation',
            'subject': 'We received your Cadence demo request',
            'header': 'Your demo request is in',
            'body': _DEMO_BODY,
            'is_active': True,
        },
    ])


def downgrade():
    op.drop_index('ix_email_templates_template_key', table_name='email_templates')
    op.drop_index('ix_email_templates_id', table_name='email_templates')
    op.drop_table('email_templates')
