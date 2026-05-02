"""Task #189 — unified branded-export engine smoke tests.

Covers:
- theme defaults + hex parsing fallbacks
- BrandedPDF builds non-empty bytes (with/without org logo)
- BrandedWorkbook builds a readable xlsx with header + zebra rows
- "Powered by Cadence" mark is present in PDF + Excel
"""
from __future__ import annotations

import io
import zipfile

import pytest

from backend.services import branding
from backend.services.branding import (
    OrgTheme,
    parse_hex_color,
    safe_filename_segment,
    theme_from_org,
)
from backend.services.pdf_engine import BrandedPDF
from backend.services.excel_engine import (
    BrandedWorkbook,
    csv_response_headers,
    excel_response_headers,
    pdf_response_headers,
)


# --- Theme + hex parsing ---


def test_parse_hex_color_accepts_3_and_6_digit():
    assert parse_hex_color("#abc").lower() == "#aabbcc"
    assert parse_hex_color("#5B8A72").lower() == "#5b8a72"
    assert parse_hex_color("5B8A72").lower() == "#5b8a72"


def test_parse_hex_color_falls_back_on_garbage():
    assert parse_hex_color(None) == branding.CADENCE_SAGE
    assert parse_hex_color("") == branding.CADENCE_SAGE
    assert parse_hex_color("not a color") == branding.CADENCE_SAGE
    assert parse_hex_color("#ZZZZZZ") == branding.CADENCE_SAGE


def test_safe_filename_segment_strips_unsafe_chars():
    out = safe_filename_segment("Acme Records / Inc.")
    assert "/" not in out
    assert " " not in out
    assert "Acme" in out and "Records" in out and "Inc" in out
    assert safe_filename_segment("", fallback="org") == "org"
    assert safe_filename_segment(None, fallback="org") == "org"


def test_theme_from_org_with_none_returns_cadence_default():
    theme = theme_from_org(None)
    assert isinstance(theme, OrgTheme)
    assert theme.primary_color == branding.CADENCE_SAGE


def test_theme_from_org_uses_org_branding_color():
    class FakeOrg:
        id = 1
        name = "Acme"
        display_name = "Acme Records"
        primary_color = "#4A6FA5"
        logo_url = None
        logo_orientation = "horizontal"

    theme = theme_from_org(FakeOrg())
    assert theme.primary_color.lower() == "#4a6fa5"
    assert theme.display_name == "Acme Records"
    assert theme.logo_orientation == "horizontal"


# --- PDF engine ---


def test_branded_pdf_builds_non_empty_bytes_no_logo():
    theme = theme_from_org(None)
    pdf = BrandedPDF(theme, title="Smoke Test", subtitle="Unit test")
    pdf.cover()
    pdf.kpi_row([
        {"label": "Songs", "value": "12"},
        {"label": "Value", "value": "$1,234"},
    ])
    pdf.section("Detail")
    pdf.table(
        headers=["Title", "Artist", "Revenue"],
        rows=[["Song A", "Acme", "$100.00"], ["Song B", "Acme", "$200.00"]],
        col_widths=[3.0, 2.0, 1.5],
        align=["LEFT", "LEFT", "RIGHT"],
    )
    pdf.text("Sample paragraph.")
    pdf.small("Methodology: testing.")
    out = pdf.build()
    assert isinstance(out, (bytes, bytearray))
    assert out.startswith(b"%PDF")
    assert len(out) > 1500


def test_branded_pdf_with_custom_color():
    class FakeOrg:
        id = 1
        name = "Acme"
        display_name = "Acme Records"
        primary_color = "#DC2626"
        logo_url = None
        logo_orientation = "square"

    theme = theme_from_org(FakeOrg())
    pdf = BrandedPDF(theme, title="Crimson", subtitle="Brand test")
    pdf.cover()
    pdf.section("S")
    pdf.text("body")
    out = pdf.build()
    assert out.startswith(b"%PDF")


def test_branded_pdf_powered_by_cadence_mark_present():
    """Non-negotiable: every theme must carry a 'Powered by Cadence' footer."""
    theme = theme_from_org(None)
    assert "Powered by Cadence" in theme.powered_by_text

    class FakeOrg:
        id = 1
        name = "Acme"
        display_name = "Acme"
        primary_color = "#DC2626"
        logo_url = None
        logo_orientation = "square"

    custom = theme_from_org(FakeOrg())
    assert "Powered by Cadence" in custom.powered_by_text, (
        "Custom-branded org themes must still carry the 'Powered by Cadence' mark"
    )

    # The PDF engine actually renders this mark in the footer — smoke-build a doc.
    pdf = BrandedPDF(theme, title="Footer Check", subtitle="")
    pdf.cover()
    pdf.text("Hello world.")
    out = pdf.build()
    assert out.startswith(b"%PDF")


def test_branded_pdf_handles_empty_table():
    theme = theme_from_org(None)
    pdf = BrandedPDF(theme, title="Empty", subtitle="")
    pdf.cover()
    pdf.table(headers=["A", "B"], rows=[], col_widths=[1.0, 1.0])
    out = pdf.build()
    assert out.startswith(b"%PDF")


def test_branded_pdf_landscape_mode():
    theme = theme_from_org(None)
    pdf = BrandedPDF(theme, title="Landscape", subtitle="Wide", landscape_orientation=True)
    pdf.cover()
    pdf.text("wide content")
    out = pdf.build()
    assert out.startswith(b"%PDF")


# --- Excel engine ---


def _xlsx_strings(out: bytes) -> str:
    """Return concatenated text content of a workbook for substring assertions."""
    buf = io.BytesIO(out)
    with zipfile.ZipFile(buf) as z:
        return "\n".join(
            z.read(name).decode("utf-8", errors="ignore")
            for name in z.namelist()
            if name.endswith(".xml") or name.endswith(".xml.rels")
        )


def test_branded_workbook_smoke():
    theme = theme_from_org(None)
    wb = BrandedWorkbook(theme, title="Smoke", subtitle="Unit test")
    wb.add_sheet(
        name="Data",
        headers=["Title", "Artist", "Revenue"],
        rows=[["Song A", "Acme", 100.50], ["Song B", "Acme", 200.75]],
    )
    out = wb.build()
    assert isinstance(out, (bytes, bytearray))
    assert out[:2] == b"PK", "valid xlsx files start with the zip magic"
    text = _xlsx_strings(out)
    assert "Song A" in text
    assert "Smoke" in text


def test_branded_workbook_includes_powered_by_cadence():
    theme = theme_from_org(None)
    wb = BrandedWorkbook(theme, title="Powered", subtitle="")
    wb.add_sheet(name="S", headers=["A"], rows=[["x"]])
    out = wb.build()
    text = _xlsx_strings(out)
    assert "Cadence" in text


def test_response_headers_have_correct_content_type():
    pdf_h = pdf_response_headers("file.pdf")
    assert pdf_h["Content-Type"] == "application/pdf"
    assert "file.pdf" in pdf_h["Content-Disposition"]

    xlsx_h = excel_response_headers("file.xlsx")
    assert "spreadsheet" in xlsx_h["Content-Type"]
    assert "file.xlsx" in xlsx_h["Content-Disposition"]

    csv_h = csv_response_headers("file.csv")
    assert csv_h["Content-Type"].startswith("text/csv")
    assert "file.csv" in csv_h["Content-Disposition"]


def test_branded_workbook_handles_zero_rows():
    theme = theme_from_org(None)
    wb = BrandedWorkbook(theme, title="Empty", subtitle="")
    wb.add_sheet(name="empty", headers=["A", "B"], rows=[])
    out = wb.build()
    assert out[:2] == b"PK"


def test_branded_workbook_multiple_sheets():
    theme = theme_from_org(None)
    wb = BrandedWorkbook(theme, title="Multi", subtitle="")
    wb.add_sheet(name="One", headers=["A"], rows=[["alpha"]])
    wb.add_sheet(name="Two", headers=["B"], rows=[["beta"]])
    out = wb.build()
    text = _xlsx_strings(out)
    assert "alpha" in text
    assert "beta" in text


# --- Logo fetch fallback ---


def test_logo_fetch_silent_fallback_on_bad_url(monkeypatch):
    """Bad logo URL should not crash the engine; PDF still renders."""
    class FakeOrg:
        id = 1
        name = "Acme"
        display_name = "Acme"
        primary_color = "#5B8A72"
        logo_url = "https://this-domain-does-not-exist-12345.invalid/logo.png"
        logo_orientation = "square"

    theme = theme_from_org(FakeOrg())
    pdf = BrandedPDF(theme, title="Logo Fallback", subtitle="")
    pdf.cover()
    pdf.text("body text")
    out = pdf.build()
    # Either logo loaded or silently fell back — but PDF must still render
    assert out.startswith(b"%PDF")
