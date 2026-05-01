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

import calendar
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from ..config.statement_formats import (
    canonical_source_type,
    get_format_spec,
)

logger = logging.getLogger(__name__)


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


def normalize_rows_for_amount_format(
    rows: List[Dict[str, Any]],
    column_mapping: Dict[str, Any],
    source_type: Optional[str],
) -> List[Dict[str, Any]]:
    """Pre-divide the revenue cell by 100 when the source's registry
    spec declares ``amount_format='cents'``.

    Returns the rows unchanged for the default ``'dollars'`` case so
    every existing source — every entry in the registry today — keeps
    going through the dollar-style parser without surprise. When the
    source is in cents, we rewrite *only* the revenue column on a
    shallow copy of each row so callers (the upload route, the seed
    loader, and ``parse_statement``) all see normalized values
    regardless of which one drove the ingestion.
    """
    if not rows or not column_mapping:
        return rows
    spec = get_format_spec(source_type) if source_type else None
    amount_format = ((spec or {}).get("amount_format") or "dollars").lower()
    if amount_format != "cents":
        return rows
    rev_col = column_mapping.get("revenue")
    if not rev_col:
        return rows
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict) or rev_col not in row:
            out.append(row)
            continue
        raw = row.get(rev_col)
        if raw is None or raw == "":
            out.append(row)
            continue
        try:
            s = str(raw).strip().replace(",", "").replace("$", "")
            if s.startswith("(") and s.endswith(")"):
                s = "-" + s[1:-1]
            cents_int = int(float(s))
        except (ValueError, TypeError):
            out.append(row)
            continue
        new_row = dict(row)
        new_row[rev_col] = f"{cents_int / 100:.2f}"
        out.append(new_row)
    return out


def parse_statement(
    file_path: str,
    source_type: Optional[str] = None,
    org_id: Optional[int] = None,
    column_mapping: Optional[Dict[str, str]] = None,
    db_session=None,
    *,
    source_name: Optional[str] = None,
    period_start: Optional[date] = None,
    period_end: Optional[date] = None,
    currency: Optional[str] = None,
    uploaded_by_user_id: Optional[int] = None,
    creator_id: Optional[int] = None,
    auto_match: bool = True,
) -> Dict[str, Any]:
    """High-level "parse one file end-to-end" entry point used by
    seed loaders, batch ingestion CLIs, and tests.

    Reads ``file_path`` from disk, runs the same parser orchestrator
    the HTTP upload route uses, optionally persists into a
    ``RoyaltyStatement`` + ``RoyaltyStatementLine`` rows when a
    ``db_session`` is provided, and runs auto-match.

    Args:
        file_path: filesystem path to the statement file (CSV / XLSX
            / PDF). The filename is also fed to the source detector.
        source_type: optional canonical source type. If omitted the
            detector tries to infer it from headers / filename.
        org_id: organization the statement belongs to. Required when
            ``db_session`` is provided.
        column_mapping: optional override for the auto-mapper. When
            falsy the new ``statement_column_mapper.auto_map_columns``
            is used (which itself falls back to the legacy
            ``suggest_column_mapping`` if confidence is low).
        db_session: SQLAlchemy session. When provided, persistence
            runs and ``statement_id`` is included in the response.
        source_name, period_start, period_end, currency,
        uploaded_by_user_id, creator_id: only used when persisting.
        auto_match: when True (default) run track auto-matching
            after persisting lines.

    Returns:
        ``{statement_id?: int, total_lines: int, matched: int,
        unmatched: int, total_revenue_cents: int, errors: [str],
        column_mapping: dict, detected_source_type: str|None,
        confident: bool}``
    """
    from .statement_column_mapper import auto_map_columns

    errors: List[str] = []

    if not os.path.isfile(file_path):
        return {
            "statement_id": None,
            "total_lines": 0,
            "matched": 0,
            "unmatched": 0,
            "total_revenue_cents": 0,
            "column_mapping": {},
            "detected_source_type": None,
            "confident": False,
            "errors": [f"file_not_found: {file_path}"],
        }

    with open(file_path, "rb") as f:
        content = f.read()
    filename = os.path.basename(file_path)

    parsed = parse_statement_file(
        content,
        filename,
        source_name=source_name or "",
        source_type=source_type,
        org_id=org_id,
    )

    # Pick the column mapping: explicit override > auto-mapper >
    # parsed.suggested_mapping (legacy registry-based).
    if column_mapping:
        resolved_mapping: Dict[str, Any] = dict(column_mapping)
        confident = True  # caller-provided mappings are assumed correct
        unmapped: List[str] = []
        confidence_score: float = 1.0
    else:
        auto = auto_map_columns(parsed.headers, parsed.resolved_source_type)
        confident = bool(auto.get("_confident"))
        unmapped = list(auto.get("_unmapped") or [])
        confidence_score = float(auto.get("_confidence") or 0.0)
        # Only keep canonical-field keys (drop the leading-underscore
        # metadata) so the mapping is wire-compatible with the
        # existing ``parse_statement_to_lines`` consumer.
        resolved_mapping = {
            k: v for k, v in auto.items()
            if v and not k.startswith("_")
        }
        # If the new mapper found nothing usable, fall back to the
        # legacy registry-based suggester so we never regress on
        # already-supported formats.
        if not resolved_mapping:
            resolved_mapping = {
                k: v for k, v in (parsed.suggested_mapping or {}).items() if v
            }
            if resolved_mapping:
                confidence_score = 0.5  # legacy suggester, no per-field score

    # Pre-divide cents-format revenue cells once so the summary path
    # (db_session is None) AND the persistence path (db_session set)
    # both see the same normalized values.
    parsed_rows = normalize_rows_for_amount_format(
        parsed.rows,
        resolved_mapping,
        parsed.resolved_source_type,
    )

    # Compute parse-summary metrics from the normalized rows so callers
    # who don't want persistence (CLIs, dry-run validators, the
    # frontend wizard's "preview" step) still get an accurate
    # total_lines / total_revenue_cents / unmatched count. Without a
    # session there's no catalog to match against, so every parsed
    # row is reported as ``unmatched``.
    rev_col = resolved_mapping.get("revenue") if resolved_mapping else None
    summary_total_lines = 0
    summary_total_revenue_cents = 0
    if rev_col:
        for row in parsed_rows:
            if not isinstance(row, dict):
                continue
            raw = row.get(rev_col)
            if raw is None or raw == "":
                continue
            try:
                s = str(raw).strip().replace(",", "").replace("$", "").replace("£", "").replace("€", "")
                if not s or s == "-":
                    continue
                if s.startswith("(") and s.endswith(")"):
                    s = "-" + s[1:-1]
                summary_total_revenue_cents += int(round(float(s) * 100))
                summary_total_lines += 1
            except (ValueError, TypeError):
                continue
    else:
        summary_total_lines = len([r for r in parsed_rows if isinstance(r, dict)])

    response: Dict[str, Any] = {
        "statement_id": None,
        "total_lines": summary_total_lines,
        "matched": 0,
        "unmatched": summary_total_lines,
        "total_revenue_cents": summary_total_revenue_cents,
        "column_mapping": resolved_mapping,
        "detected_source_type": parsed.resolved_source_type,
        "confident": confident,
        "confidence": confidence_score,
        "unmapped_headers": unmapped,
        "errors": errors,
    }

    if db_session is None:
        return response

    if org_id is None:
        errors.append("org_id_required_for_persistence")
        return response

    # Persist: create the RoyaltyStatement, parse rows into lines,
    # auto-match. Mirrors load_sample_statements_for_org so seed and
    # ad-hoc CLI ingestion go through identical machinery.
    from ..models.models import RoyaltyStatement
    from .royalty_processing_engine import (
        parse_statement_to_lines,
        auto_match_lines,
    )

    spec = get_format_spec(parsed.resolved_source_type) or {}
    resolved_currency = currency or spec.get("default_currency") or "USD"

    # ``parsed_rows`` was already normalized above so the
    # summary-only branch and the persistence branch see identical
    # cents-vs-dollars handling — see ``normalize_rows_for_amount_format``.

    statement = RoyaltyStatement(
        organization_id=org_id,
        source_name=source_name or (parsed.resolved_source_type or "Statement"),
        source_type=parsed.resolved_source_type,
        period_start=period_start,
        period_end=period_end,
        currency=resolved_currency,
        file_name=filename,
        status="PROCESSING",
        column_mapping=resolved_mapping,
        uploaded_by_user_id=uploaded_by_user_id,
        creator_id=creator_id,
    )
    db_session.add(statement)
    db_session.flush()

    try:
        line_count = parse_statement_to_lines(
            db_session,
            statement.id,
            org_id,
            resolved_mapping,
            parsed_rows,
            pdf_metadata=parsed.pdf_metadata,
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("parse_statement_to_lines failed for %s", filename)
        errors.append(f"parse_lines_failed: {exc}")
        line_count = 0

    match_stats: Dict[str, Any] = {}
    if auto_match and line_count > 0:
        try:
            match_stats = auto_match_lines(db_session, statement.id, org_id) or {}
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("auto_match_lines failed for %s", filename)
            errors.append(f"auto_match_failed: {exc}")

    matched = (match_stats.get("auto_matched") or 0) + (match_stats.get("review_required") or 0)
    unmatched = match_stats.get("unmatched") or 0
    if not match_stats and line_count > 0:
        # auto_match disabled: every line is unmatched-by-default.
        unmatched = line_count

    if line_count == 0:
        statement.status = "EMPTY"
    elif unmatched == 0 and (match_stats.get("review_required") or 0) == 0:
        statement.status = "FULLY_MATCHED"
    elif unmatched == 0:
        statement.status = "REVIEW_REQUIRED"
    else:
        statement.status = "PARTIALLY_MATCHED"

    statement.matched_transactions = matched
    statement.unmatched_transactions = unmatched
    db_session.flush()

    response.update({
        "statement_id": statement.id,
        "total_lines": line_count,
        "matched": matched,
        "unmatched": unmatched,
        "total_revenue_cents": statement.total_revenue_cents or 0,
    })
    return response


_MONTH_TOKENS = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def _last_day(year: int, month: int) -> int:
    return calendar.monthrange(year, month)[1]


def infer_period_from_filename(
    filename: str,
    source_type: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Extract (period_start, period_end, cadence) from a statement
    filename using common naming patterns the industry uses.

    Recognized cadences and example filenames:

    - **monthly**:   ``mlc_dec_2025.csv``, ``dsp_2024_03.csv``,
                     ``platform_2025-07_payout.csv``
    - **quarterly**: ``bmi_q4_2025.csv``, ``ascap_2024_q1.csv``
    - **semi-annual**: ``label_h2_2025.csv``, ``warner_h1_2024.csv``
    - **annual**:    ``soundexchange_2024.csv``,
                     ``annual_statement_2023.csv``

    Falls back to the registry's ``period_cadence`` for the source so
    callers always know which kind of period to expect even when the
    filename is uninformative.

    Returns ``None`` only when no year can be located at all.
    """
    if not filename:
        return None
    name = filename.rsplit(".", 1)[0].lower()
    # normalize separators so "label-h2-2025" and "label_h2_2025" parse identically
    name = re.sub(r"[-./]", "_", name)
    name = re.sub(r"_+", "_", name)

    # 1. Quarter pattern:  q1..q4 + 4-digit year (any order)
    m = re.search(r"(?:^|_)q([1-4])_?(\d{4})(?:_|$)", name)
    if not m:
        m = re.search(r"(?:^|_)(\d{4})_?q([1-4])(?:_|$)", name)
        if m:
            year, q = int(m.group(1)), int(m.group(2))
        else:
            year, q = None, None
    else:
        q, year = int(m.group(1)), int(m.group(2))
    if year is not None:
        start_month = (q - 1) * 3 + 1
        end_month = start_month + 2
        return {
            "period_start": date(year, start_month, 1),
            "period_end": date(year, end_month, _last_day(year, end_month)),
            "cadence": "quarterly",
        }

    # 2. Half-year pattern: h1/h2 + 4-digit year
    m = re.search(r"(?:^|_)h([12])_?(\d{4})(?:_|$)", name) or \
        re.search(r"(?:^|_)(\d{4})_?h([12])(?:_|$)", name)
    if m:
        a, b = m.group(1), m.group(2)
        if a.isdigit() and len(a) == 4:
            year, half = int(a), int(b)
        else:
            half, year = int(a), int(b)
        start_month = 1 if half == 1 else 7
        end_month = 6 if half == 1 else 12
        return {
            "period_start": date(year, start_month, 1),
            "period_end": date(year, end_month, _last_day(year, end_month)),
            "cadence": "semi-annual",
        }

    # 3. Monthly pattern A: month name + year (e.g. ``dec_2025``)
    for token, month in _MONTH_TOKENS.items():
        m = re.search(rf"(?:^|_){token}_?(\d{{4}})(?:_|$)", name)
        if not m:
            m = re.search(rf"(?:^|_)(\d{{4}})_?{token}(?:_|$)", name)
        if m:
            year = int(m.group(1))
            return {
                "period_start": date(year, month, 1),
                "period_end": date(year, month, _last_day(year, month)),
                "cadence": "monthly",
            }

    # 4. Monthly pattern B: numeric YYYY_MM or MM_YYYY
    m = re.search(r"(?:^|_)(\d{4})_(\d{2})(?:_|$)", name)
    if m and 1 <= int(m.group(2)) <= 12:
        year, month = int(m.group(1)), int(m.group(2))
        return {
            "period_start": date(year, month, 1),
            "period_end": date(year, month, _last_day(year, month)),
            "cadence": "monthly",
        }
    m = re.search(r"(?:^|_)(\d{2})_(\d{4})(?:_|$)", name)
    if m and 1 <= int(m.group(1)) <= 12:
        month, year = int(m.group(1)), int(m.group(2))
        return {
            "period_start": date(year, month, 1),
            "period_end": date(year, month, _last_day(year, month)),
            "cadence": "monthly",
        }

    # 5. Annual fallback: bare 4-digit year
    m = re.search(r"(?:^|_)(\d{4})(?:_|$)", name)
    if m:
        year = int(m.group(1))
        spec = get_format_spec(source_type) if source_type else None
        cadence = (spec or {}).get("period_cadence") or "annual"
        return {
            "period_start": date(year, 1, 1),
            "period_end": date(year, 12, 31),
            "cadence": cadence,
        }

    return None


__all__ = [
    "ParsedStatement",
    "parse_statement_file",
    "parse_statement",
    "normalize_rows_for_amount_format",
    "infer_period_from_filename",
]
