"""Unit tests for the BMI Writer Distribution Statement parser.

These tests exercise `_parse_bmi_writer_text` directly so the regex/loop
logic can be verified without a real PDF on disk. The companion file
`test_bmi_ingestion.py` covers the route-level flow with a synthesized
PDF.
"""
import re

import pytest

from backend.utils.pdf_statement_parser import (
    BMI_FIRST_ROW_RE,
    BMI_CONT_ROW_RE,
    BMI_SUBTOTAL_RE,
    BMI_GRAND_TOTAL_RE,
    BMI_WRITER_NAME_RE,
    BMI_PERIOD_RE,
    BMI_CATEGORY_FULL_NAMES,
    _parse_bmi_writer_text,
)


SAMPLE_TEXT = """WRITER DISTRIBUTION STATEMENT
BROADCAST MUSIC, INC.
BMI (R) 7 World Trade Center Performance Period: Jul - Dec 2023
250 Greenwich Street
WRITER INFORMATION
Writer Name: Marcus Jordan Address: 1847 Cascade Road SW, Atlanta, GA 30311
CAE/IPI #: 00847291035 Affiliation: BMI
STATEMENT SUMMARY
TOTAL CURRENT PERIOD 2,685,402 $15,999.99
DETAILED PERFORMANCE ROYALTIES BY WORK
WORK TITLE WORK # PERF. CATEGORY PERFORMANCES WRITER % ROYALTY AMT
Deja Vu W-10806201 Digital - Audio Streaming 155,437 50.0% $517.77
Radio 36,795 50.0% $158.25
Digital - Audio Visual St 50,943 50.0% $211.61
Television - Network 31,644 50.0% $115.70
Subtotal: $1,003.33
Montero W-10513037 Digital - Audio Streaming 59,595 33.3% $659.87
Radio 89,448 33.3% $275.52
Subtotal: $935.39
BROADCAST MUSIC, INC. - CONFIDENTIAL Page 1 of 8 BMI Writer Distribution Statement
WORK TITLE WORK # PERF. CATEGORY PERFORMANCES WRITER % ROYALTY AMT
Heat Waves W-10439746 International 25,377 20.0% $113.15
General Licensing 6,656 20.0% $48.50
Subtotal: $161.65
"""


def test_first_row_regex_extracts_title_workno_and_amount():
    m = BMI_FIRST_ROW_RE.match("Deja Vu W-10806201 Digital - Audio Streaming 155,437 50.0% $517.77")
    assert m is not None
    assert m.group("title") == "Deja Vu"
    assert m.group("work_no") == "W-10806201"
    assert m.group("category") == "Digital - Audio Streaming"
    assert m.group("performances") == "155,437"
    assert m.group("writer_pct") == "50.0%"
    assert m.group("amount") == "517.77"


def test_first_row_regex_handles_multiword_title():
    m = BMI_FIRST_ROW_RE.match("Save Your Tears W-10879492 Radio 18,077 25.0% $101.87")
    assert m is not None
    assert m.group("title") == "Save Your Tears"
    assert m.group("work_no") == "W-10879492"


def test_first_row_regex_supports_negative_amounts():
    m = BMI_FIRST_ROW_RE.match("Foo W-1 Television - Cable 100 50.0% $-8.60")
    assert m is not None
    assert m.group("amount") == "-8.60"


def test_cont_row_regex_extracts_continuation_line():
    m = BMI_CONT_ROW_RE.match("Radio 36,795 50.0% $158.25")
    assert m is not None
    assert m.group("category") == "Radio"
    assert m.group("amount") == "158.25"


def test_cont_row_regex_does_not_match_subtotal():
    assert BMI_CONT_ROW_RE.match("Subtotal: $1,495.89") is None


def test_subtotal_regex_extracts_amount():
    m = BMI_SUBTOTAL_RE.match("Subtotal: $1,495.89")
    assert m and m.group(1) == "1,495.89"


def test_grand_total_regex_extracts_total_current_period():
    m = BMI_GRAND_TOTAL_RE.search("TOTAL CURRENT PERIOD 2,685,402 $15,999.99")
    assert m and m.group(1) == "15,999.99"


def test_writer_name_regex_stops_at_address():
    m = BMI_WRITER_NAME_RE.search(
        "Writer Name: Marcus Jordan Address: 1847 Cascade Road SW"
    )
    assert m is not None
    assert m.group(1).strip() == "Marcus Jordan"


def test_writer_name_regex_handles_no_address_field():
    m = BMI_WRITER_NAME_RE.search("Writer Name: Jane Doe\n")
    assert m and m.group(1).strip() == "Jane Doe"


def test_period_regex_extracts_period_string():
    m = BMI_PERIOD_RE.search("Performance Period: Jul - Dec 2023")
    assert m and m.group(1).strip() == "Jul - Dec 2023"


def test_truncated_category_maps_to_full_name():
    assert BMI_CATEGORY_FULL_NAMES["Digital - Audio Visual St"] == "Digital - Audio Visual Streaming"
    assert BMI_CATEGORY_FULL_NAMES["Radio"] == "Radio"


def test_parse_bmi_writer_text_returns_none_for_empty_input():
    assert _parse_bmi_writer_text("") is None


def test_parse_bmi_writer_text_extracts_metadata_and_rows():
    out = _parse_bmi_writer_text(SAMPLE_TEXT)
    assert out is not None
    assert out["metadata"]["grand_total_net"] == 15999.99
    assert out["metadata"]["client_name"] == "Marcus Jordan"
    assert out["metadata"]["period"] == "Jul - Dec 2023"
    assert len(out["rows"]) == 8


def test_parse_bmi_writer_text_carries_title_across_continuation_rows():
    out = _parse_bmi_writer_text(SAMPLE_TEXT)
    titles = [r["Track Title"] for r in out["rows"]]
    assert titles[:4] == ["Deja Vu"] * 4
    assert titles[4:6] == ["Montero"] * 2
    assert titles[6:8] == ["Heat Waves"] * 2


def test_parse_bmi_writer_text_normalizes_truncated_category():
    out = _parse_bmi_writer_text(SAMPLE_TEXT)
    rows_with_av = [r for r in out["rows"] if r["Income Type"] == "Digital - Audio Visual Streaming"]
    assert len(rows_with_av) == 1
    assert rows_with_av[0]["Track Title"] == "Deja Vu"


def test_parse_bmi_writer_text_skips_subtotal_rows():
    out = _parse_bmi_writer_text(SAMPLE_TEXT)
    # 9 detail rows in sample (4+2+3); 3 subtotal rows must be excluded.
    assert len(out["rows"]) == 8
    assert all(not r["Income Type"].lower().startswith("subtotal") for r in out["rows"])


def test_parse_bmi_writer_text_skips_repeated_page_headers():
    out = _parse_bmi_writer_text(SAMPLE_TEXT)
    # The "WORK TITLE WORK # ..." header repeats on page 2 in the sample
    # and must not be parsed as a data row.
    assert all(r["Track Title"] != "WORK TITLE" for r in out["rows"])


def test_parse_bmi_writer_text_sum_matches_subtotals():
    out = _parse_bmi_writer_text(SAMPLE_TEXT)
    parsed_sum = sum(float(r["Net Amount"]) for r in out["rows"])
    # Sample subtotals: 1003.33 + 935.39 + 161.65 = 2100.37
    assert round(parsed_sum, 2) == 2100.37


def test_parse_bmi_writer_text_writer_share_preserved():
    out = _parse_bmi_writer_text(SAMPLE_TEXT)
    deja_vu_rows = [r for r in out["rows"] if r["Track Title"] == "Deja Vu"]
    assert all(r["Writer Share"] == "50.0%" for r in deja_vu_rows)


def test_parse_bmi_writer_text_units_strips_thousands_separator():
    out = _parse_bmi_writer_text(SAMPLE_TEXT)
    first = out["rows"][0]
    assert first["Units"] == "155437"
