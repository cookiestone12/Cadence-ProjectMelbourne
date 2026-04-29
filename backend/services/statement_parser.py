"""Royalty statement parser orchestrator.

Thin facade over the existing parsing helpers in
``backend/routes/royalties.py`` plus the format registry in
``backend/config/statement_formats.py``. Centralizes the
file-bytes → headers/rows → detected source → suggested mapping
pipeline so any caller (HTTP upload route, seed loader, future
re-parse / drop-in replay tooling) can call into one place rather
than re-stringing the helpers together.

Returns a ``ParsedStatement`` dataclass. None of the database
writes happen here — that's still the job of
``royalty_processing_engine.parse_statement_to_lines``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..config.statement_formats import (
    canonical_source_type,
    get_format_spec,
)


@dataclass
class ParsedStatement:
    """Result of running an uploaded statement file through the parser.

    Attributes:
        headers: Column names from the file (after header-row detection).
        rows: List of row dicts (header → cell value).
        pdf_metadata: Optional dict carrying parser-side hints
            (e.g. ``grand_total_net``, ``suggested_mapping`` from
            specialized PDF parsers like the BMI one).
        detected_source_type: Canonical source-type value if the
            auto-detector recognized the file, else ``None``.
        resolved_source_type: Source type the caller should write to
            ``RoyaltyStatement.source_type``: explicit caller value
            wins, then detected, else ``None``.
        suggested_mapping: Header → internal-field mapping the parser
            recommends. PDF parser hints win over registry-based
            suggestion.
        format_spec: Registry entry for ``resolved_source_type`` if
            one is registered, else ``None``. Includes
            ``period_cadence`` and ``default_currency`` operators may
            want to surface in the UI.
    """

    headers: List[str]
    rows: List[Dict[str, Any]]
    pdf_metadata: Dict[str, Any] = field(default_factory=dict)
    detected_source_type: Optional[str] = None
    resolved_source_type: Optional[str] = None
    suggested_mapping: Dict[str, Optional[str]] = field(default_factory=dict)
    format_spec: Optional[Dict[str, Any]] = None


def parse_statement_file(
    content: bytes,
    filename: str,
    *,
    source_name: str = "",
    source_type: Optional[str] = None,
    org_id: Optional[int] = None,
) -> ParsedStatement:
    """Parse uploaded statement bytes → ParsedStatement (headers, rows,
    detected/resolved source type, suggested column mapping). Explicit
    source_type takes precedence over auto-detection."""
    # Imported lazily to avoid the heavy import chain (FastAPI,
    # pdfplumber, openpyxl, openai) when this module is imported by
    # a CLI / test that doesn't actually parse a file.
    from ..routes.royalties import (
        parse_uploaded_file,
        detect_pro_source,
        suggest_column_mapping,
    )

    headers, rows, pdf_metadata = parse_uploaded_file(
        content, filename, org_id=org_id
    )
    pdf_metadata = pdf_metadata or {}

    # Auto-detection runs against headers + caller-supplied
    # source_name + filename. Returns a canonical registry key.
    detected = detect_pro_source(headers, source_name or "", filename or "")
    detected_canonical = canonical_source_type(detected) if detected else None

    explicit_canonical = canonical_source_type(source_type) if source_type else None
    resolved = explicit_canonical or detected_canonical

    # PDF parser suggestions (e.g. is_bmi_writer_statement) are most
    # accurate; fall back to registry-based suggestion otherwise.
    suggested_from_pdf = pdf_metadata.get("suggested_mapping") if pdf_metadata else None
    if suggested_from_pdf:
        mapping = suggested_from_pdf
    else:
        # ``suggest_column_mapping`` keys off source_name keywords.
        # Pass the canonical source-type back through to bias the
        # registry overlay onto the right source's extra_hints.
        mapping = suggest_column_mapping(headers, resolved or source_name or "")

    return ParsedStatement(
        headers=headers,
        rows=rows,
        pdf_metadata=pdf_metadata,
        detected_source_type=detected_canonical,
        resolved_source_type=resolved,
        suggested_mapping=mapping,
        format_spec=get_format_spec(resolved) if resolved else None,
    )


__all__ = ["ParsedStatement", "parse_statement_file"]
