"""Regression tests for Task #96 — Vanguard publisher statement parser.

Statement #19 in production showed 18 lines, every one of them $0, even
though the PDF cover sheet said $15,484.03. Root cause: the Vanguard PDF
is text-only (pdfplumber finds 0 tables) AND its detail rows have
`$rate $amount` columns instead of the percentage-rate format expected by
the existing publishing parser, so it fell through to the AI parser, which
returned rows with empty amount fields.

These tests pin down the new parser's behaviour so the regression cannot
silently come back.
"""
from backend.utils.pdf_statement_parser import (
    VANGUARD_DETAIL_RE,
    VANGUARD_GRAND_TOTAL_RE,
    VANGUARD_ISRC_RE,
    _split_vanguard_prefix,
    _parse_vanguard_text,
)


# Mini-fixture: a sanitized excerpt of the real Vanguard layout that
# exercises every tricky case (work title carryover, revenue type
# carryover, truncated rev-type names that disambiguate by their full
# prefix, "--" placeholders for units/rate, multiple works).
VANGUARD_TEXT_FIXTURE = """\
VANGUARD ROYALTY STATEMENT
MUSIC PUBLISHING Statement Period: Jul - Dec 2023
Writer: Marcus Jordan p/k/a MJ Jordan Publisher: Vanguard Music Publishing
WORK TITLE ISRC REVENUE TYPE SOURCE UNITS/PLAYS RATE AMOUNT
Break My Soul USSM12202365 Performance Royalties (Do Pandora 9,766 $6.1253 $59.82
TikTok 7,167 $3.4087 $24.43
Performance Royalties (In Facebook/Meta 3,540 $2.0282 $7.18
Mechanical Royalties - St SoundCloud 10,185 $1.8841 $19.19
Mechanical Royalties - Do iTunes 29 $0.1062 $3.08
Synchronization Fees Direct License -- -- $1,800.00
Print Royalties Sheet Music Digita -- -- $1.78
Micro-Sync / User Generat Direct License -- -- $14.15
Work Total: $1,929.63
Deja Vu USUG12100660 Performance Royalties (Do Deezer 64,677 $2.6993 $174.58
Mechanical Royalties - Ph Cassette 17 $1.1541 $19.62
Work Total: $194.20
PAYMENT SUMMARY
Gross Royalties Earned: $2,123.83 Payment Method: ACH Direct Deposit
"""


def test_detail_re_matches_dollar_rate_and_amount():
    m = VANGUARD_DETAIL_RE.match("Pandora 9,766 $6.1253 $59.82")
    assert m
    assert m.group("prefix") == "Pandora"
    assert m.group("units") == "9,766"
    assert m.group("rate") == "$6.1253"
    assert m.group("amount") == "59.82"


def test_detail_re_matches_double_dash_units_and_rate():
    m = VANGUARD_DETAIL_RE.match("Synchronization Fees Direct License -- -- $1,800.00")
    assert m
    assert m.group("prefix") == "Synchronization Fees Direct License"
    assert m.group("units") == "--"
    assert m.group("rate") == "--"
    assert m.group("amount") == "1,800.00"


def test_detail_re_rejects_work_total_line():
    assert VANGUARD_DETAIL_RE.match("Work Total: $1,929.63") is None


def test_isrc_regex_extracts_standard_isrc():
    m = VANGUARD_ISRC_RE.search("Break My Soul USSM12202365 Performance Royalties (Do")
    assert m
    assert m.group(1) == "USSM12202365"


def test_grand_total_regex_extracts_dollars():
    m = VANGUARD_GRAND_TOTAL_RE.search("Gross Royalties Earned: $15,484.03 Payment Method: ACH")
    assert m
    assert m.group(1) == "15,484.03"


def test_split_prefix_resolves_truncated_domestic():
    rt, source = _split_vanguard_prefix("Performance Royalties (Do Pandora", "")
    assert rt == "Performance Royalties (Domestic)"
    assert source == "Pandora"


def test_split_prefix_resolves_truncated_downloads_not_domestic():
    # "Mechanical Royalties - Do" (Downloads) shares the "(Do" tail with
    # Performance Domestic, but the Mechanical prefix disambiguates.
    rt, source = _split_vanguard_prefix("Mechanical Royalties - Do iTunes", "")
    assert rt == "Mechanical Royalties - Downloads"
    assert source == "iTunes"


def test_split_prefix_carries_current_when_no_match():
    rt, source = _split_vanguard_prefix(
        "Pandora", "Performance Royalties (Domestic)"
    )
    assert rt == "Performance Royalties (Domestic)"
    assert source == "Pandora"


def test_parse_vanguard_text_extracts_all_lines_with_nonzero_amounts():
    result = _parse_vanguard_text(VANGUARD_TEXT_FIXTURE)
    assert result is not None
    rows = result["rows"]
    # 8 detail lines from "Break My Soul" + 2 from "Deja Vu" = 10 rows
    assert len(rows) == 10, f"expected 10 rows, got {len(rows)}"
    # Every row must have a non-zero amount — this is the core regression.
    for r in rows:
        assert r["Net Amount"], f"row missing Net Amount: {r}"
        assert float(r["Net Amount"]) > 0, f"row has zero amount: {r}"


def test_parse_vanguard_text_sum_matches_grand_total():
    result = _parse_vanguard_text(VANGUARD_TEXT_FIXTURE)
    line_sum = sum(float(r["Net Amount"]) for r in result["rows"])
    # Sum of every detail line in the fixture should equal $2,123.83.
    assert abs(line_sum - 2123.83) < 0.01, f"sum mismatch: {line_sum}"
    assert result["metadata"]["grand_total_net"] == 2123.83


def test_parse_vanguard_text_carries_work_title_across_rows():
    result = _parse_vanguard_text(VANGUARD_TEXT_FIXTURE)
    rows = result["rows"]
    # First 8 rows belong to "Break My Soul"; the last 2 to "Deja Vu".
    assert all(r["Track Title"] == "Break My Soul" for r in rows[:8])
    assert all(r["Track Title"] == "Deja Vu" for r in rows[8:])
    assert all(r["ISRC"] == "USSM12202365" for r in rows[:8])
    assert all(r["ISRC"] == "USUG12100660" for r in rows[8:])


def test_parse_vanguard_text_carries_revenue_type_across_rows():
    result = _parse_vanguard_text(VANGUARD_TEXT_FIXTURE)
    rows = result["rows"]
    # Row 0: Pandora -> Domestic; Row 1: TikTok also Domestic (carried)
    assert rows[0]["Income Type"] == "Performance Royalties (Domestic)"
    assert rows[1]["Income Type"] == "Performance Royalties (Domestic)"
    # Row 2: switches to International
    assert rows[2]["Income Type"] == "Performance Royalties (International)"
    # Row 4: Mechanical Downloads (the "(Do" disambiguation case)
    assert rows[4]["Income Type"] == "Mechanical Royalties - Downloads"


def test_parse_vanguard_text_extracts_writer_and_period():
    result = _parse_vanguard_text(VANGUARD_TEXT_FIXTURE)
    assert result["metadata"]["client_name"] == "Marcus Jordan p/k/a MJ Jordan"
    assert result["metadata"]["period"] == "Jul - Dec 2023"


def test_parse_vanguard_text_returns_none_for_empty_input():
    assert _parse_vanguard_text("") is None
    assert _parse_vanguard_text(None) is None


def test_parse_vanguard_text_stops_at_payment_summary():
    # Anything after "PAYMENT SUMMARY" must not be parsed as a data row,
    # otherwise a malformed dollar string from the summary block could
    # leak into the row set.
    text = VANGUARD_TEXT_FIXTURE + (
        "Less: Publisher Share (25%): ($530.96) Bank: ****7291\n"
        "NET PAYMENT TO WRITER: $1,560.65\n"
    )
    result = _parse_vanguard_text(text)
    assert len(result["rows"]) == 10
