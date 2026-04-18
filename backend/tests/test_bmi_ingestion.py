"""Route-level integration test for the BMI Writer Distribution Statement
parser. We synthesize a tiny BMI-format PDF in-memory with reportlab so
the test does not depend on any real customer document on disk.
"""
import io

import pytest

reportlab = pytest.importorskip("reportlab")

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from backend.routes.royalties import parse_uploaded_file
from backend.utils.pdf_statement_parser import (
    is_bmi_writer_statement,
    parse_bmi_writer_statement,
)


def _build_bmi_pdf() -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 9)
    y = 750
    lines = [
        "WRITER DISTRIBUTION STATEMENT",
        "BROADCAST MUSIC, INC.",
        "BMI (R) 7 World Trade Center  Performance Period: Jul - Dec 2023",
        "Writer Name: Marcus Jordan  Address: 1847 Cascade Road SW",
        "STATEMENT SUMMARY",
        "TOTAL CURRENT PERIOD 2,685,402 $1,003.33",
        "DETAILED PERFORMANCE ROYALTIES BY WORK",
        "WORK TITLE WORK # PERF. CATEGORY PERFORMANCES WRITER % ROYALTY AMT",
        "Deja Vu W-10806201 Digital - Audio Streaming 155,437 50.0% $517.77",
        "Radio 36,795 50.0% $158.25",
        "Digital - Audio Visual St 50,943 50.0% $211.61",
        "Television - Network 31,644 50.0% $115.70",
        "Subtotal: $1,003.33",
    ]
    for ln in lines:
        c.drawString(40, y, ln)
        y -= 14
    c.save()
    return buf.getvalue()


def test_bmi_pdf_is_detected_and_parsed():
    pdf = _build_bmi_pdf()
    assert is_bmi_writer_statement(pdf) is True
    out = parse_bmi_writer_statement(pdf)
    assert out is not None
    assert len(out["rows"]) == 4
    assert all(r["Track Title"] == "Deja Vu" for r in out["rows"])
    assert out["metadata"]["client_name"] == "Marcus Jordan"
    assert out["metadata"]["period"] == "Jul - Dec 2023"
    assert out["metadata"]["grand_total_net"] == 1003.33


def test_parse_uploaded_file_routes_bmi_pdf_through_dedicated_parser():
    pdf = _build_bmi_pdf()
    headers, rows, metadata = parse_uploaded_file(pdf, "BMI_Statement.pdf")

    # The BMI parser provides this header order and a known suggested
    # mapping; the generic table extractor and AI parser do not.
    assert "Track Title" in headers
    assert "Net Amount" in headers
    assert metadata.get("suggested_mapping", {}).get("revenue") == "Net Amount"
    assert metadata.get("suggested_mapping", {}).get("track_title") == "Track Title"

    assert len(rows) == 4
    sum_amt = sum(float(r["Net Amount"]) for r in rows)
    assert round(sum_amt, 2) == 1003.33


def test_parse_uploaded_file_does_not_route_non_bmi_pdf_to_bmi_parser():
    """Reverse guard: a PDF with the BMI grand-total phrase but no BMI
    header should NOT be routed through the BMI parser.
    """
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 9)
    c.drawString(40, 750, "Some Other Royalty Statement")
    c.drawString(40, 736, "Not the BMI format at all")
    c.drawString(40, 722, "Just a plain table of numbers below")
    c.save()

    assert is_bmi_writer_statement(buf.getvalue()) is False
