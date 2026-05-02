"""Unified branded PDF engine — single source of truth for every Cadence PDF.

Routes call :class:`BrandedPDF`, append cover/section/text/table/KPI blocks,
and call :meth:`BrandedPDF.build` to get bytes. The engine renders the org's
logo on the cover and page header, applies the org's primary color across
table chrome and accent lines, and stamps a small "Powered by Cadence" mark
in every page footer alongside the page number and generation timestamp.

Logo fetch failures degrade to a text-only header so a bad logo URL never
crashes a report.
"""

from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional, Sequence, Tuple, Union

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import LETTER, landscape, letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .branding import OrgTheme, POWERED_BY, theme_from_org

logger = logging.getLogger("cadence")

# Public re-exports so route handlers don't need to import branding directly.
__all__ = [
    "BrandedPDF",
    "OrgTheme",
    "theme_from_org",
    "PageBreak",
    "Spacer",
]


@dataclass
class _PageFooterContext:
    org_name: str
    primary_color: str
    powered_by: str
    generated_at: str


def _hex(c: str):
    return colors.HexColor(c)


class _BrandedDocTemplate(BaseDocTemplate):
    """DocTemplate that paints the branded header + footer on every page."""

    def __init__(self, buffer, theme: OrgTheme, pagesize, margins, header_org: bool = True):
        self._theme = theme
        self._header_org = header_org
        self._logo_bytes = theme.fetch_logo_bytes()
        self._generated_at = datetime.utcnow().strftime("%B %d, %Y %H:%M UTC")

        left, right, top, bottom = margins
        super().__init__(
            buffer,
            pagesize=pagesize,
            leftMargin=left,
            rightMargin=right,
            topMargin=top,
            bottomMargin=bottom,
        )

        frame = Frame(
            self.leftMargin,
            self.bottomMargin,
            self.width,
            self.height,
            leftPadding=0,
            rightPadding=0,
            topPadding=0,
            bottomPadding=0,
            id="content",
        )
        self.addPageTemplates([
            PageTemplate(id="branded", frames=[frame], onPage=self._draw_chrome)
        ])

    # ------------------------------------------------------------------
    # Page chrome
    # ------------------------------------------------------------------
    def _draw_chrome(self, canvas: Canvas, doc: BaseDocTemplate) -> None:
        canvas.saveState()
        try:
            self._draw_header(canvas)
            self._draw_footer(canvas, doc.page)
        finally:
            canvas.restoreState()

    def _draw_header(self, canvas: Canvas) -> None:
        if not self._header_org:
            return
        page_w, page_h = self.pagesize
        primary = _hex(self._theme.primary_color)
        ink = _hex(self._theme.text_color)
        muted = _hex(self._theme.muted_color)

        y = page_h - 0.4 * inch
        canvas.setStrokeColor(primary)
        canvas.setLineWidth(2)
        canvas.line(self.leftMargin, y - 0.05 * inch, page_w - self.rightMargin, y - 0.05 * inch)

        canvas.setFont("Helvetica-Bold", 9)
        canvas.setFillColor(ink)
        canvas.drawString(self.leftMargin, y + 0.08 * inch, self._theme.display_name or self._theme.name)

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(muted)
        canvas.drawRightString(page_w - self.rightMargin, y + 0.08 * inch, self._generated_at)

    def _draw_footer(self, canvas: Canvas, page_num: int) -> None:
        page_w, page_h = self.pagesize
        muted = _hex(self._theme.muted_color)
        primary = _hex(self._theme.primary_color)

        y = self.bottomMargin / 2.0
        canvas.setStrokeColor(_hex(self._theme.divider))
        canvas.setLineWidth(0.5)
        canvas.line(self.leftMargin, y + 0.18 * inch, page_w - self.rightMargin, y + 0.18 * inch)

        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(muted)
        canvas.drawString(self.leftMargin, y, self._theme.display_name or self._theme.name)

        canvas.setFillColor(primary)
        canvas.setFont("Helvetica-Bold", 7.5)
        canvas.drawCentredString(page_w / 2.0, y, self._theme.powered_by_text)

        canvas.setFillColor(muted)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawRightString(page_w - self.rightMargin, y, f"Page {page_num}")


class BrandedPDF:
    """Fluent builder for branded Cadence PDFs.

    Usage::

        pdf = BrandedPDF(theme, title="Schedule A", subtitle="Q3 2025", landscape=True)
        pdf.cover()
        pdf.section("Released catalog")
        pdf.kpi_row([{"label": "Songs", "value": "42"}, ...])
        pdf.table(headers=[...], rows=[...])
        pdf.text("Footnote about how the data was sourced.")
        bytes_ = pdf.build()
    """

    DEFAULT_MARGINS = (0.6 * inch, 0.6 * inch, 0.85 * inch, 0.7 * inch)  # L, R, T, B
    LANDSCAPE_MARGINS = (0.5 * inch, 0.5 * inch, 0.85 * inch, 0.7 * inch)

    def __init__(
        self,
        theme: OrgTheme,
        title: str,
        subtitle: Optional[str] = None,
        landscape_orientation: bool = False,
        page_size: Tuple[float, float] = LETTER,
        margins: Optional[Tuple[float, float, float, float]] = None,
        page_header: bool = True,
    ) -> None:
        self.theme = theme
        self.title = title
        self.subtitle = subtitle
        self.landscape = landscape_orientation
        size = landscape(page_size) if landscape_orientation else page_size
        self.page_size = size
        self.margins = margins or (
            self.LANDSCAPE_MARGINS if landscape_orientation else self.DEFAULT_MARGINS
        )
        self.page_header = page_header

        self._buffer = io.BytesIO()
        self._doc = _BrandedDocTemplate(
            self._buffer, theme, size, self.margins, header_org=page_header
        )
        self._story: List[Any] = []
        self._styles = self._build_styles()

    # ------------------------------------------------------------------
    # Style factory
    # ------------------------------------------------------------------
    def _build_styles(self):
        base = getSampleStyleSheet()
        primary = _hex(self.theme.primary_color)
        ink = _hex(self.theme.text_color)
        muted = _hex(self.theme.muted_color)

        return {
            "title": ParagraphStyle(
                "BrandedTitle", parent=base["Title"],
                fontName="Helvetica-Bold", fontSize=22,
                textColor=primary, spaceAfter=4, leading=26,
            ),
            "subtitle": ParagraphStyle(
                "BrandedSubtitle", parent=base["Normal"],
                fontName="Helvetica", fontSize=12,
                textColor=muted, spaceAfter=14, leading=15,
            ),
            "section": ParagraphStyle(
                "BrandedSection", parent=base["Heading2"],
                fontName="Helvetica-Bold", fontSize=14,
                textColor=ink, spaceBefore=14, spaceAfter=6, leading=16,
            ),
            "subsection": ParagraphStyle(
                "BrandedSubSection", parent=base["Heading3"],
                fontName="Helvetica-Bold", fontSize=11,
                textColor=primary, spaceBefore=8, spaceAfter=4, leading=14,
            ),
            "body": ParagraphStyle(
                "BrandedBody", parent=base["Normal"],
                fontName="Helvetica", fontSize=10,
                textColor=ink, spaceAfter=6, leading=14,
            ),
            "small": ParagraphStyle(
                "BrandedSmall", parent=base["Normal"],
                fontName="Helvetica", fontSize=8,
                textColor=muted, spaceAfter=4, leading=10,
            ),
            "kpi_label": ParagraphStyle(
                "BrandedKPILabel", parent=base["Normal"],
                fontName="Helvetica", fontSize=8,
                textColor=muted, alignment=TA_CENTER, spaceAfter=2, leading=10,
            ),
            "kpi_value": ParagraphStyle(
                "BrandedKPIValue", parent=base["Normal"],
                fontName="Helvetica-Bold", fontSize=14,
                textColor=primary, alignment=TA_CENTER, leading=16,
            ),
            "table_header": ParagraphStyle(
                "BrandedTableHead", parent=base["Normal"],
                fontName="Helvetica-Bold", fontSize=9,
                textColor=colors.white, alignment=TA_LEFT, leading=11,
            ),
            "table_cell": ParagraphStyle(
                "BrandedTableCell", parent=base["Normal"],
                fontName="Helvetica", fontSize=8.5,
                textColor=ink, alignment=TA_LEFT, leading=11,
            ),
        }

    # ------------------------------------------------------------------
    # Block builders
    # ------------------------------------------------------------------
    def cover(self) -> "BrandedPDF":
        """Render a logo + title + subtitle block at the top of the document."""
        logo_bytes = self.theme.fetch_logo_bytes()
        page_w = self.page_size[0] - self.margins[0] - self.margins[1]
        if logo_bytes:
            try:
                max_w = 1.6 * inch
                max_h = 1.0 * inch
                w, h = self.theme.logo_dimensions(max_w, max_h)
                img = Image(io.BytesIO(logo_bytes), width=w, height=h)
                img.hAlign = "LEFT"
                self._story.append(img)
                self._story.append(Spacer(1, 8))
            except Exception as exc:
                logger.warning("Logo render failed (theme=%s): %s", self.theme.display_name, exc)

        self._story.append(Paragraph(self.title, self._styles["title"]))
        if self.subtitle:
            self._story.append(Paragraph(self.subtitle, self._styles["subtitle"]))
        self._story.append(HRFlowable(
            width=page_w, thickness=1.2, color=_hex(self.theme.primary_color),
            spaceBefore=2, spaceAfter=12,
        ))
        return self

    def section(self, heading: str) -> "BrandedPDF":
        self._story.append(Paragraph(heading, self._styles["section"]))
        return self

    def subsection(self, heading: str) -> "BrandedPDF":
        self._story.append(Paragraph(heading, self._styles["subsection"]))
        return self

    def text(self, body: str, style: str = "body") -> "BrandedPDF":
        self._story.append(Paragraph(body, self._styles[style]))
        return self

    def small(self, body: str) -> "BrandedPDF":
        return self.text(body, style="small")

    def spacer(self, height: float = 8) -> "BrandedPDF":
        self._story.append(Spacer(1, height))
        return self

    def page_break(self) -> "BrandedPDF":
        self._story.append(PageBreak())
        return self

    def hr(self) -> "BrandedPDF":
        page_w = self.page_size[0] - self.margins[0] - self.margins[1]
        self._story.append(HRFlowable(
            width=page_w, thickness=0.5,
            color=_hex(self.theme.divider), spaceBefore=4, spaceAfter=8,
        ))
        return self

    def kpi_row(self, kpis: Sequence[dict]) -> "BrandedPDF":
        """Render a horizontal row of KPI tiles.

        Each entry is ``{"label": "...", "value": "...", "sub": "..."}``.
        ``sub`` is optional. The row uses the org's primary color for the
        value and a muted gray for label + sub.
        """
        if not kpis:
            return self
        page_w = self.page_size[0] - self.margins[0] - self.margins[1]
        n = len(kpis)
        col_w = page_w / n
        cells = []
        for k in kpis:
            inner = []
            inner.append(Paragraph(str(k.get("label", "")), self._styles["kpi_label"]))
            inner.append(Paragraph(str(k.get("value", "")), self._styles["kpi_value"]))
            if k.get("sub"):
                inner.append(Spacer(1, 2))
                inner.append(Paragraph(str(k["sub"]), self._styles["kpi_label"]))
            cells.append(inner)

        tbl = Table([cells], colWidths=[col_w] * n)
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), _hex(self.theme.zebra_color)),
            ("BOX", (0, 0), (-1, -1), 0.5, _hex(self.theme.divider)),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, _hex(self.theme.divider)),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 10),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
        ]))
        self._story.append(tbl)
        self._story.append(Spacer(1, 10))
        return self

    def table(
        self,
        headers: Optional[Sequence[str]],
        rows: Sequence[Sequence[Any]],
        col_widths: Optional[Sequence[float]] = None,
        align: Optional[Sequence[str]] = None,
        zebra: bool = True,
        wrap_cells: bool = False,
    ) -> "BrandedPDF":
        """Render a branded data table.

        Pass ``headers=None`` (or an empty list) for a headerless layout —
        useful for label/value metadata grids and signature blocks. The
        body is still themed (zebra, ink, divider) but no header band is
        rendered.
        ``align`` is an optional list (one per column) of ``"LEFT" | "RIGHT" | "CENTER"``.
        ``wrap_cells`` re-renders every cell as a Paragraph so long strings wrap;
        leave ``False`` for compact tabular numeric data.
        """
        has_header = bool(headers)
        if not rows and not has_header:
            return self
        # Determine column count: from headers, then col_widths, then first row.
        if has_header:
            num_cols = len(headers)
        elif col_widths:
            num_cols = len(col_widths)
        elif rows:
            num_cols = max((len(r) for r in rows), default=0)
        else:
            num_cols = 0
        if num_cols == 0:
            return self

        primary = _hex(self.theme.primary_color)
        zebra_color = _hex(self.theme.zebra_color)
        ink = _hex(self.theme.text_color)
        divider = _hex(self.theme.divider)

        header_style = self._styles["table_header"]
        cell_style = self._styles["table_cell"]
        header_row = [Paragraph(str(h), header_style) for h in headers] if has_header else None

        body_rows = []
        for r in rows:
            row = []
            for cell in r:
                if cell is None:
                    val = ""
                else:
                    val = cell if isinstance(cell, str) else str(cell)
                if wrap_cells:
                    row.append(Paragraph(val, cell_style))
                else:
                    row.append(val)
            # Pad short rows
            while len(row) < num_cols:
                row.append("")
            body_rows.append(row)

        page_w = self.page_size[0] - self.margins[0] - self.margins[1]
        if col_widths is None:
            col_widths = [page_w / num_cols] * num_cols
        else:
            # Scale to fit page width if caller passed relative weights
            total = sum(col_widths)
            if total > 0 and abs(total - page_w) > 1.0:
                col_widths = [w * page_w / total for w in col_widths]

        data = ([header_row] + body_rows) if has_header else body_rows
        repeat = 1 if has_header else 0
        tbl = Table(data, colWidths=col_widths, repeatRows=repeat)
        body_start = 1 if has_header else 0
        ts = [
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("FONTNAME", (0, body_start), (-1, -1), "Helvetica"),
            ("TEXTCOLOR", (0, body_start), (-1, -1), ink),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("GRID", (0, 0), (-1, -1), 0.4, divider),
        ]
        if has_header:
            ts.extend([
                ("BACKGROUND", (0, 0), (-1, 0), primary),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (0, 0), (-1, 0), "LEFT"),
            ])
        if align:
            for col_idx, a in enumerate(align):
                if a:
                    ts.append(("ALIGN", (col_idx, body_start), (col_idx, -1), a.upper()))
        if zebra and len(body_rows) > 1:
            ts.append(("ROWBACKGROUNDS", (0, body_start), (-1, -1), [colors.white, zebra_color]))
        tbl.setStyle(TableStyle(ts))
        self._story.append(tbl)
        self._story.append(Spacer(1, 10))
        return self

    def keep_together(self, *flowables) -> "BrandedPDF":
        """Wrap a sequence of flowables in a KeepTogether so they don't split."""
        self._story.append(KeepTogether(list(flowables)))
        return self

    def append(self, flowable) -> "BrandedPDF":
        """Escape hatch — append a raw ReportLab flowable when needed."""
        self._story.append(flowable)
        return self

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    def build(self) -> bytes:
        """Render the document and return the PDF bytes."""
        try:
            self._doc.build(self._story)
        except Exception as exc:
            logger.error("PDF build failed: %s", exc, exc_info=True)
            raise
        return self._buffer.getvalue()
