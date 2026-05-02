"""Task #199 Phase 1 — Unit tests for the new BMI quarterly parser.

These tests target the multi-section "Diego-style" BMI quarterly
distribution statement format. Legacy single-section coverage lives in
``test_bmi_parser.py`` (Marcus Jordan flow, ``pdf_statement_parser``).
"""
from decimal import Decimal

import pytest

from backend.services.bmi_parser import (
    BMILineItem,
    BMIParsedStatement,
    SECTION_PATTERNS,
    SECTION_TO_BUCKET,
    KNOWN_SOURCES,
    normalize_source,
    parse_amount,
    parse_bmi_quarterly_text,
    to_metadata,
    to_row_dicts,
)


# ---------------------------------------------------------------------------
# Section vocabulary — all 9 sections are recognized.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name,sample", [
    ("us_commercial_radio",   "U.S. Performances - Commercial Radio"),
    ("us_cable_tv",           "U.S. Performances - Cable Television"),
    ("us_local_tv",           "U.S. Performances - Local Television"),
    ("us_internet_audio",     "U.S. Performances - Internet Audio"),
    ("us_internet_av",        "U.S. Performances - Internet Audiovisual"),
    ("us_other",              "U.S. Performances - Other Sources"),
    ("admin_services",        "Admin Services"),
    ("intl_audio",            "International Performances - Audio"),
    ("intl_av",               "International Performances - Audiovisual"),
])
def test_all_nine_section_patterns_match(name, sample):
    assert SECTION_PATTERNS[name].search(sample), (
        f"section pattern {name!r} did not match {sample!r}"
    )


def test_section_to_bucket_covers_every_section():
    missing = set(SECTION_PATTERNS.keys()) - set(SECTION_TO_BUCKET.keys())
    assert not missing, f"sections without a bucket mapping: {missing}"
    for bucket in SECTION_TO_BUCKET.values():
        assert bucket in {
            "performance", "sync_adjacent", "streaming", "international"
        }


# ---------------------------------------------------------------------------
# Source vocabulary — 65+ tier names recognized; T-suffix detection.
# ---------------------------------------------------------------------------

def test_known_sources_count_meets_spec():
    # Spec calls for at least 65 source/tier names.
    assert len(KNOWN_SOURCES) >= 65


@pytest.mark.parametrize("raw,expected_norm,expected_t", [
    ("SPOTIFY PREM",      "SPOTIFY PREM", False),
    ("SPOTIFY PREM T",    "SPOTIFY PREM", True),
    ("APPLE FAMILY T",    "APPLE FAMILY", True),
    ("AMAZON UNLIMITED",  "AMAZON UNLIMITED", False),
    ("BET HER",           "BET HER", False),
])
def test_normalize_source_strips_t_suffix(raw, expected_norm, expected_t):
    norm, t_suffix = normalize_source(raw)
    assert norm == expected_norm
    assert t_suffix is expected_t


# ---------------------------------------------------------------------------
# Amount parsing — parens-as-negative, currency strip, blank handling.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("$517.77",          Decimal("517.77")),
    ("517.77",           Decimal("517.77")),
    ("$1,234.56",        Decimal("1234.56")),
    ("(123.45)",         Decimal("-123.45")),
    ("($45.00)",         Decimal("-45.00")),
    ("-$10.00",          Decimal("-10.00")),
    ("",                 Decimal("0")),
    ("  ",               Decimal("0")),
])
def test_parse_amount_handles_currency_and_parens_negative(raw, expected):
    assert parse_amount(raw) == expected


# ---------------------------------------------------------------------------
# Multi-period parsing — period codes like 20243 (2024 Q3) are tracked.
# ---------------------------------------------------------------------------

def test_period_code_year_and_quarter_extraction():
    li = BMILineItem(title="x", work_number="W1", period_code="20243")
    assert li.period_year == 2024
    assert li.period_quarter == 3

    # 2025Q1
    li2 = BMILineItem(title="y", work_number="W2", period_code="20251")
    assert li2.period_year == 2025
    assert li2.period_quarter == 1

    # Bad / missing → None
    li3 = BMILineItem(title="z", work_number="W3", period_code="")
    assert li3.period_year is None
    assert li3.period_quarter is None


# ---------------------------------------------------------------------------
# Aggregate-line case — work_number == "000000000" identifies an aggregate.
# ---------------------------------------------------------------------------

def test_aggregate_work_number_flag():
    agg = BMILineItem(title="Aggregate Royalties", work_number="000000000")
    assert agg.is_aggregate is True

    normal = BMILineItem(title="Real Song", work_number="W-12345678")
    assert normal.is_aggregate is False


# ---------------------------------------------------------------------------
# Totals validation + parse-quality scoring.
# ---------------------------------------------------------------------------

def test_validation_delta_zero_when_totals_match():
    stmt = BMIParsedStatement()
    stmt.line_items.append(BMILineItem(
        title="A", work_number="W1", royalty_amount=Decimal("100.00"),
    ))
    stmt.line_items.append(BMILineItem(
        title="B", work_number="W2", royalty_amount=Decimal("50.00"),
    ))
    stmt.grand_total = Decimal("150.00")
    assert stmt.computed_total == Decimal("150.00")
    assert stmt.validation_delta == Decimal("0")
    # Perfect match + no unparsed lines → quality 1.0
    assert stmt.parse_quality == 1.0


def test_validation_delta_nonzero_when_totals_diverge():
    stmt = BMIParsedStatement()
    stmt.line_items.append(BMILineItem(
        title="A", work_number="W1", royalty_amount=Decimal("100.00"),
    ))
    stmt.grand_total = Decimal("105.00")
    assert stmt.validation_delta == Decimal("-5.00")
    # 5/105 ≈ 4.76% → just under 5% threshold; total_score in (0, 1)
    assert 0.0 < stmt.parse_quality < 1.0


def test_parse_quality_drops_with_unparsed_lines():
    stmt = BMIParsedStatement()
    stmt.line_items.append(BMILineItem(
        title="A", work_number="W1", royalty_amount=Decimal("10.00"),
    ))
    stmt.unparsed_lines.append("Mystery garbage row")
    stmt.grand_total = Decimal("10.00")
    # 1 parsed + 1 unparsed = line_score 0.5, total_score 1.0 -> 0.75.
    assert stmt.parse_quality == 0.75


# ---------------------------------------------------------------------------
# Adapter — to_row_dicts / to_metadata produce ingestion-ready shape.
# ---------------------------------------------------------------------------

def test_to_row_dicts_emits_bmi_extras():
    stmt = BMIParsedStatement()
    stmt.line_items.append(BMILineItem(
        title="Heat Waves",
        work_number="W-12345678",
        count=1500,
        period_code="20243",
        writer_share_pct=Decimal("33.33"),
        royalty_amount=Decimal("12.50"),
        section="us_internet_audio",
        source="SPOTIFY PREM",
        source_t_suffix=False,
    ))
    rows = to_row_dicts(stmt)
    assert rows, "to_row_dicts produced no rows"
    row = rows[0]
    # Must carry the keys the ingestion engine reads.
    assert row.get("Work Number") == "W-12345678"
    assert "Platform Source" in row
    assert "Period Code" in row


def test_to_metadata_includes_parse_quality():
    stmt = BMIParsedStatement(grand_total=Decimal("100.00"))
    stmt.line_items.append(BMILineItem(
        title="A", work_number="W1", royalty_amount=Decimal("100.00"),
    ))
    meta = to_metadata(stmt)
    assert "parse_quality" in meta
    assert 0.0 <= meta["parse_quality"] <= 1.0


# ---------------------------------------------------------------------------
# End-to-end: parse a synthetic multi-section statement text.
# ---------------------------------------------------------------------------

# Fixture mirrors the real BMI quarterly statement layout the v2 parser
# was hardened against: multi-section, T-suffixed sources, parens-negative
# international adjustment, multi-period codes, and per-section subtotals.
SAMPLE_BMI_TEXT = """BMI BROADCAST MUSIC, INC.
Account No: 123456789
IP No: 12345.67
Affiliate: TEST PUBLISHER LLC
Distribution Date: November 15, 2024
Performance Period: THIRD QUARTER 2024
International: 3RD QUARTER ACCOUNTING
Page 1 of 1

Total Earnings $80.00 $0.00 $20.00 $100.00

U.S. Performances - Internet Audio
SPOTIFY PREM
HEAT WAVES 104397460 BR 1500 20243 33.33% $12.50
HEAT WAVES 104397460 BR 800 20242 33.33% $7.50
APPLE FAMILY T
HEAT WAVES 104397460 BR 600 20243 33.33% $9.00
SUMMERTIME 200000001 BR 5000 20243 50.00% $51.00
Section Total $80.00

International Performances - Audio
UNITED KINGDOM - PRS
HEAT WAVES 104397460 PRS 20243 $23.50
HEAT WAVES 104397460 PRS 20242 Y ($3.50)
Section Total $20.00

Grand Total $100.00
"""


def test_parse_bmi_quarterly_text_returns_real_line_items():
    """End-to-end fixture parse — assert real parsed content covering
    multi-section, T-suffix, multi-period, parens-negative, and
    cross-section totals reconciliation."""
    result = parse_bmi_quarterly_text(SAMPLE_BMI_TEXT)
    assert isinstance(result, BMIParsedStatement)
    # 4 audio rows + 2 international rows.
    assert len(result.line_items) == 6
    # Sections present in the parsed output.
    sections = {li.section for li in result.line_items}
    assert sections == {"us_internet_audio", "intl_audio"}
    # Sources captured from standalone source-header lines.
    sources = {li.source for li in result.line_items if li.source}
    assert "SPOTIFY PREM" in sources
    assert "APPLE FAMILY" in sources  # T-suffix stripped
    # T-suffix correctly carried only on the APPLE FAMILY rows.
    apple_rows = [li for li in result.line_items if li.source == "APPLE FAMILY"]
    assert apple_rows and all(li.source_t_suffix for li in apple_rows)
    spotify_rows = [li for li in result.line_items if li.source == "SPOTIFY PREM"]
    assert spotify_rows and all(not li.source_t_suffix for li in spotify_rows)


def test_parse_bmi_quarterly_text_handles_parens_negative_intl():
    """Adjustments printed as ($3.50) must parse as -$3.50 and the
    section total must reconcile against the header summary."""
    result = parse_bmi_quarterly_text(SAMPLE_BMI_TEXT)
    assert result is not None
    intl_rows = [li for li in result.line_items if li.section == "intl_audio"]
    assert len(intl_rows) == 2
    intl_sum = sum((li.royalty_amount for li in intl_rows), Decimal("0"))
    assert intl_sum == Decimal("20.00")  # 23.50 + (-3.50)
    # The negative row is flagged.
    neg_rows = [li for li in intl_rows if li.royalty_amount < 0]
    assert len(neg_rows) == 1
    assert neg_rows[0].royalty_amount == Decimal("-3.50")


def test_parse_bmi_quarterly_text_preserves_intl_source_per_row():
    """International rows must persist the per-row source token (PRS,
    GEMA, etc.) on ``BMILineItem.source`` so downstream ingestion keeps
    society-level fidelity instead of falling back to a blank/BMI label.
    """
    result = parse_bmi_quarterly_text(SAMPLE_BMI_TEXT)
    assert result is not None
    intl_rows = [li for li in result.line_items if li.section == "intl_audio"]
    assert intl_rows, "expected at least one international row"
    sources = {(li.source or "").upper() for li in intl_rows}
    assert "PRS" in sources, (
        f"intl row source token lost; got {sources!r}"
    )
    for li in intl_rows:
        assert li.source, (
            f"intl row {li.title!r} has empty source — fidelity dropped"
        )


def test_parse_bmi_quarterly_text_captures_multiperiod_codes():
    """Both 20243 and 20242 codes coexist in the same section; parser
    keeps the original code per row so per-period reporting works."""
    result = parse_bmi_quarterly_text(SAMPLE_BMI_TEXT)
    assert result is not None
    periods = {li.period_code for li in result.line_items if li.period_code}
    assert "20243" in periods
    assert "20242" in periods


def test_parse_bmi_quarterly_text_reconciles_totals():
    """Header grand total + computed line total must reconcile within
    parser tolerance, yielding a high parse_quality score."""
    result = parse_bmi_quarterly_text(SAMPLE_BMI_TEXT)
    assert result is not None
    assert result.grand_total == Decimal("100.00")
    assert result.computed_total == Decimal("100.00")
    assert result.validation_delta == Decimal("0")
    assert result.parse_quality == 1.0
    # Header summary fields populated.
    assert result.us_total == Decimal("80.00")
    assert result.intl_total == Decimal("20.00")


def test_parse_bmi_quarterly_text_records_section_subtotals():
    """Section Total lines must be captured into ``section_totals``
    keyed by the active section."""
    result = parse_bmi_quarterly_text(SAMPLE_BMI_TEXT)
    assert result is not None
    keys = list(result.section_totals.keys())
    # Both sections produced a Section Total row.
    assert any(k.startswith("us_internet_audio:") for k in keys)
    assert any(k.startswith("intl_audio:") for k in keys)
    # Values match the fixture.
    us_key = next(k for k in keys if k.startswith("us_internet_audio:"))
    intl_key = next(k for k in keys if k.startswith("intl_audio:"))
    assert result.section_totals[us_key] == Decimal("80.00")
    assert result.section_totals[intl_key] == Decimal("20.00")
