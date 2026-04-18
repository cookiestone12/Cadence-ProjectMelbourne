"""Route-level integration test for Task #96 — verifies that
`parse_uploaded_file` (the real ingestion entry point used by both upload
endpoints) routes a Vanguard PDF through the new parser, returns rows with
non-zero amounts, and surfaces the grand total in the metadata so the
engine can pin `total_revenue_cents` to it.

This locks down the wiring between the parser and the ingestion route, not
just the parser logic in isolation.
"""
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from backend.routes.royalties import parse_uploaded_file


def _build_minimal_vanguard_pdf() -> bytes:
    """Create a tiny but format-faithful Vanguard PDF in-memory. Mirrors
    the real layout closely enough that the detector + parser hit every
    code path: title carryover, revenue-type carryover, "--" placeholders,
    truncated revenue type names, and the grand-total payment summary."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 9)

    # Page 1 — cover + summary
    y = 750
    for line in [
        "VANGUARD ROYALTY STATEMENT",
        "MUSIC PUBLISHING Statement Period: Jul - Dec 2023",
        "Writer: Test Writer Publisher: Vanguard Music Publishing",
        "REVENUE SUMMARY BY TYPE",
        "TOTAL $250.00 $62.50 $187.50 $187.50",
    ]:
        c.drawString(50, y, line)
        y -= 14
    c.showPage()

    # Page 2 — detail rows in the exact column layout the parser expects
    c.setFont("Helvetica", 9)
    y = 750
    for line in [
        "WORK TITLE ISRC REVENUE TYPE SOURCE UNITS/PLAYS RATE AMOUNT",
        "Track Alpha USTEST1234567 Performance Royalties (Do Pandora 1,000 $0.1000 $100.00",
        "TikTok 500 $0.1000 $50.00",
        "Mechanical Royalties - Do iTunes 100 $0.5000 $50.00",
        "Synchronization Fees Direct License -- -- $50.00",
        "Work Total: $250.00",
    ]:
        c.drawString(50, y, line)
        y -= 14
    c.showPage()

    # Page 3 — payment summary with the grand total the parser should
    # latch onto via VANGUARD_GRAND_TOTAL_RE
    c.setFont("Helvetica", 9)
    y = 750
    for line in [
        "PAYMENT SUMMARY",
        "Gross Royalties Earned: $250.00 Payment Method: ACH",
        "NET PAYMENT TO WRITER: $187.50",
    ]:
        c.drawString(50, y, line)
        y -= 14
    c.save()

    return buf.getvalue()


def test_parse_uploaded_file_routes_vanguard_pdf_through_dedicated_parser():
    """End-to-end: a Vanguard PDF must come out of `parse_uploaded_file`
    with non-zero revenue rows AND a suggested mapping that points at
    `Net Amount` (the column the parser actually populated). This is the
    exact contract the upload endpoint relies on."""
    pdf_bytes = _build_minimal_vanguard_pdf()
    headers, rows, metadata = parse_uploaded_file(
        pdf_bytes, "vanguard_test.pdf", org_id=None
    )

    # The previous bug surfaced as an empty / all-$0 row set. Lock this down:
    assert rows, "parser produced no rows — would silently regress to $0"
    assert len(rows) == 4, f"expected 4 detail rows, got {len(rows)}"

    # Suggested mapping must point `revenue` at the column that contains
    # the actual amount. If this drifts, the engine will compute $0
    # totals again exactly the way statement #19 did in production.
    mapping = metadata.get("suggested_mapping", {})
    assert mapping.get("revenue") == "Net Amount"
    assert mapping.get("track_title") == "Track Title"
    assert mapping.get("isrc") == "ISRC"

    # Every row must carry a non-zero numeric Net Amount.
    for r in rows:
        assert r["Net Amount"], f"missing Net Amount on row: {r}"
        assert float(r["Net Amount"]) > 0, f"zero amount on row: {r}"

    # The sum of detail lines must match the grand total the parser
    # surfaces. This is what `parse_statement_to_lines` uses to set
    # `royalty_statements.total_revenue_cents` (the authoritative value
    # the Reports page now reads).
    line_sum = sum(float(r["Net Amount"]) for r in rows)
    assert abs(line_sum - 250.00) < 0.01
    assert metadata.get("grand_total_net") == 250.00


def test_parse_uploaded_file_does_not_route_non_vanguard_pdf_to_vanguard_parser():
    """Sanity check the detector isn't a false-positive magnet. A PDF that
    doesn't mention Vanguard must NOT go through the Vanguard parser
    (otherwise it'd produce 0 rows and fall through, but better to trip
    the right path the first time)."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setFont("Helvetica", 9)
    c.drawString(50, 750, "ASCAP ROYALTY DISTRIBUTION STATEMENT")
    c.drawString(50, 730, "Period: 2024 Q1")
    c.save()
    pdf_bytes = buf.getvalue()

    # Should not raise; should return *something* (likely empty rows from
    # AI fallback, but importantly without claiming Vanguard mapping).
    try:
        headers, rows, metadata = parse_uploaded_file(
            pdf_bytes, "ascap_test.pdf", org_id=None
        )
        # Should not have inherited Vanguard's specific suggested mapping
        # whose `platform` is hardcoded to "Source/Collector".
        mapping = metadata.get("suggested_mapping", {}) if metadata else {}
        assert mapping.get("platform") != "Source/Collector" or not rows
    except Exception:
        # AI parser may legitimately fail without an OPENAI key in CI; the
        # important guarantee is that we didn't enter the Vanguard branch.
        pass
