"""Task #104 — Statement period parser hardening.

Covers the additional period-header phrasings and quarter / half-year /
date-pair / period-ending tokens added so BMI 2024 statements (and other
publisher quirks) no longer fall through silently to a NULL period.
"""
from datetime import date

from backend.utils.pdf_statement_parser import parse_period_from_text


def test_performance_period_jul_dec():
    s, e = parse_period_from_text("Performance Period: Jul - Dec 2023")
    assert s == date(2023, 7, 1)
    assert e == date(2023, 12, 31)


def test_statement_period_full_dates():
    s, e = parse_period_from_text("Statement Period: July 1, 2023 - December 31, 2023")
    assert s == date(2023, 7, 1)
    assert e == date(2023, 12, 31)


def test_royalty_distribution_period_month_range():
    s, e = parse_period_from_text("Royalty Distribution Period: Jan - Jun 2024")
    assert s == date(2024, 1, 1)
    assert e == date(2024, 6, 30)


def test_distribution_period_quarter_q1():
    s, e = parse_period_from_text("Distribution Period: Q1 2024")
    assert s == date(2024, 1, 1)
    assert e == date(2024, 3, 31)


def test_distribution_period_quarter_1q():
    s, e = parse_period_from_text("Distribution Period: 1Q 2024")
    assert s == date(2024, 1, 1)
    assert e == date(2024, 3, 31)


def test_distribution_period_quarter_word():
    s, e = parse_period_from_text("Statement Period: Second Quarter 2024")
    assert s == date(2024, 4, 1)
    assert e == date(2024, 6, 30)


def test_distribution_period_quarter_ordinal():
    s, e = parse_period_from_text("Period: 3rd Quarter 2024")
    assert s == date(2024, 7, 1)
    assert e == date(2024, 9, 30)


def test_half_year_h1():
    s, e = parse_period_from_text("Royalty Distribution Period: H1 2024")
    assert s == date(2024, 1, 1)
    assert e == date(2024, 6, 30)


def test_half_year_2h():
    s, e = parse_period_from_text("Royalty Distribution Period: 2H 2024")
    assert s == date(2024, 7, 1)
    assert e == date(2024, 12, 31)


def test_half_year_word():
    s, e = parse_period_from_text("Statement Period: First Half 2024")
    assert s == date(2024, 1, 1)
    assert e == date(2024, 6, 30)


def test_date_pair_slash():
    s, e = parse_period_from_text("Statement Period: From 01/01/2024 to 06/30/2024")
    assert s == date(2024, 1, 1)
    assert e == date(2024, 6, 30)


def test_date_pair_dash():
    s, e = parse_period_from_text("Period: 01/01/2024 - 06/30/2024")
    assert s == date(2024, 1, 1)
    assert e == date(2024, 6, 30)


def test_period_ending_dec_31_infers_h2():
    """A bare 'Period Ending: 12/31/2023' should infer the *half* ending on
    that date — never silently widen to a multi-year range."""
    s, e = parse_period_from_text("Period Ending: 12/31/2023")
    assert s == date(2023, 7, 1)
    assert e == date(2023, 12, 31)


def test_period_ending_jun_30_infers_h1():
    s, e = parse_period_from_text("Period Ending: 6/30/2024")
    assert s == date(2024, 1, 1)
    assert e == date(2024, 6, 30)


def test_period_ending_quarter_end_infers_q1():
    s, e = parse_period_from_text("Period Ending: 3/31/2024")
    assert s == date(2024, 1, 1)
    assert e == date(2024, 3, 31)


def test_no_match_returns_none():
    s, e = parse_period_from_text("Some random PDF cover sheet with no period info")
    assert s is None
    assert e is None


def test_empty_text_returns_none():
    s, e = parse_period_from_text("")
    assert s is None
    assert e is None


def test_does_not_silently_use_invoice_dates():
    """If the PDF only mentions an invoice date or due date — never a period —
    we must return None so the upload code can leave period_start/end NULL
    rather than fabricating a range."""
    text = "Invoice Date: 03/15/2026\nDue Date: 04/15/2026\nThank you for your business."
    s, e = parse_period_from_text(text)
    assert s is None
    assert e is None


def test_period_beside_statement_number_bmi_variant():
    """BMI sometimes places the period inline with the statement number on
    the same row, with no labeled "Period:" header. We rely on the generic
    'period' fallback in `_PERIOD_HEADER_RE` to still find it."""
    text = "Statement #BMI-2024-001234   Period: Jan - Jun 2024   Distribution: 09/15/2024"
    s, e = parse_period_from_text(text)
    assert s == date(2024, 1, 1)
    assert e == date(2024, 6, 30)


def test_period_buried_after_client_block():
    """Real BMI statements carry a 1-page client/header block before the
    period header. Make sure the parser still finds the period when it's
    not on line 1."""
    text = (
        "BROADCAST MUSIC, INC.\n"
        "WRITER DISTRIBUTION STATEMENT\n"
        "Writer: SMITH, JOHN\n"
        "IPI: 0123456789\n"
        "Affiliation: BMI\n"
        "Address: 123 Main St, Nashville TN\n"
        "\n"
        "Royalty Distribution Period: Jan - Jun 2024\n"
        "Distribution Date: 09/15/2024\n"
    )
    s, e = parse_period_from_text(text)
    assert s == date(2024, 1, 1)
    assert e == date(2024, 6, 30)
