"""Add BMI-rich columns to royalty_statement_lines.

Revision ID: f199a1b2c3d4
Revises: e1f2a3b4c5d6
Create Date: 2026-05-02 12:00:00.000000

Task #199 (BMI Parser & Royalty Engine Optimization) — Phase 1.

Adds nullable, additive columns the dedicated BMI parser populates so
the downstream rate-intelligence, valuation-v2, and trajectory engines
can work directly off line items without re-parsing the PDF. Existing
rows are unaffected; only newly parsed BMI lines (or future re-parses)
fill these.
"""
from alembic import op
import sqlalchemy as sa


revision = 'f199a1b2c3d4'
down_revision = 'e1f2a3b4c5d6'
branch_labels = None
depends_on = None


_NEW_COLUMNS = [
    ('platform_source', sa.String()),         # e.g. "SPOTIFY PREM"
    ('platform_tier', sa.String()),           # e.g. "PREM", "FREE", "FAMILY"
    ('source_t_suffix', sa.Boolean()),        # T-licensing variant flag
    ('writer_share_pct', sa.Float()),         # 0–100, per-line publisher %
    ('bmi_work_number', sa.String()),         # 9-digit BMI work id
    ('period_code', sa.String()),             # e.g. "20251" = 2025 Q1
    ('super_usage_cents', sa.Integer()),      # TV super-usage bonus
    ('country', sa.String()),                 # International only
    ('society', sa.String()),                 # APRA, PRS, SOCAN, ...
    ('is_aggregate', sa.Boolean()),           # work_number == 000000000
    ('is_adjustment', sa.Boolean()),          # "Y" flag in international
    ('section_code', sa.String()),            # us_internet_audio, etc.
    ('parse_quality', sa.Float()),            # 0–1 per-statement quality cached on line
]


def upgrade():
    for name, col_type in _NEW_COLUMNS:
        op.add_column(
            'royalty_statement_lines',
            sa.Column(name, col_type, nullable=True),
        )
    # Helpful index for rate intelligence aggregations.
    op.create_index(
        'ix_rsl_org_platform_source',
        'royalty_statement_lines',
        ['org_id', 'platform_source'],
    )


def downgrade():
    op.drop_index('ix_rsl_org_platform_source', table_name='royalty_statement_lines')
    for name, _ in reversed(_NEW_COLUMNS):
        op.drop_column('royalty_statement_lines', name)
