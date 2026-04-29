from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from difflib import SequenceMatcher
import csv
import io
import os
import re
import logging

from ..models import (
    get_db, User, OrganizationMember, Song, Creator,
    Contract, ContractAsset, RightsSplit,
    RoyaltyStatement, RoyaltyTransaction, RoyaltyAllocation, Payment,
    Fee, Advance, Placement, RoyaltyStatementLine,
)
from ..utils.auth import get_current_user

try:
    import openpyxl
    EXCEL_SUPPORT = True
except ImportError:
    EXCEL_SUPPORT = False

try:
    import pdfplumber
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/royalties", tags=["Royalties"])


def verify_org_access(user: User, org_id: int, db: Session, creator_id: int = None, required_module: str = None):
    membership = db.query(OrganizationMember).filter(
        OrganizationMember.user_id == user.id,
        OrganizationMember.organization_id == org_id
    ).first()
    if not membership and not user.is_super_admin:
        if creator_id:
            from .client_sharing import has_shared_access, ALL_SHARE_MODULES
            share = has_shared_access(db, user.id, creator_id)
            if share:
                if required_module:
                    modules = getattr(share, 'shared_modules', None) or ALL_SHARE_MODULES
                    if required_module not in modules:
                        raise HTTPException(status_code=403, detail=f"Access to {required_module} is not included in this share")
                return None
        raise HTTPException(status_code=403, detail="Access denied")
    return membership


class PaymentCreate(BaseModel):
    payee_id: int
    contract_id: Optional[int] = None
    amount_cents: int
    currency: str = "USD"
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentUpdate(BaseModel):
    status: Optional[str] = None
    payment_date: Optional[date] = None
    payment_method: Optional[str] = None
    payment_reference: Optional[str] = None
    notes: Optional[str] = None


class ManualMatchRequest(BaseModel):
    song_id: int


# Per-source column-mapping config now lives in
# ``backend/config/statement_formats.py`` so a single registry feeds
# both auto-detection and the parser orchestrator. These aliases keep
# call sites (test suite, royalty_processing.py) working unchanged.
from ..config.statement_formats import (
    BASE_COLUMN_HINTS as COLUMN_HINTS,
    SOURCE_FORMAT_REGISTRY as PRO_SOURCE_TYPES,
    canonical_source_type,
)


KNOWN_SOURCE_NAMES = {
    "bmi": "BMI", "ascap": "ASCAP", "sesac": "SESAC",
    "soundexchange": "SoundExchange", "sound exchange": "SoundExchange",
    "socan": "SOCAN", "prs": "PRS", "prs for music": "PRS",
    "mlc": "MLC", "the mlc": "MLC", "mechanical licensing collective": "MLC",
    "distrokid": "DistroKid", "tunecore": "TuneCore",
    "cd baby": "CD Baby", "cdbaby": "CD Baby",
    "stem": "Stem", "songtrust": "Songtrust",
}


def normalize_source_name(source_name: str) -> str:
    if not source_name:
        return source_name
    lookup = source_name.strip().lower()
    return KNOWN_SOURCE_NAMES.get(lookup, source_name.strip())


def detect_pro_source(headers: List[str], source_name: str = "", filename: str = "") -> Optional[str]:
    all_text = " ".join(headers).lower() + " " + source_name.lower()
    fname_lower = filename.lower() if filename else ""
    for pro_name, config in PRO_SOURCE_TYPES.items():
        for keyword in config["keywords"]:
            if keyword in all_text or keyword in fname_lower:
                return pro_name
    return None


def suggest_column_mapping(headers: List[str], source_type: str = "") -> Dict[str, Optional[str]]:
    hints = {k: list(v) for k, v in COLUMN_HINTS.items()}

    detected_pro = detect_pro_source(headers, source_type)
    if detected_pro and detected_pro in PRO_SOURCE_TYPES:
        for field, extra in PRO_SOURCE_TYPES[detected_pro].get("extra_hints", {}).items():
            if field in hints:
                hints[field] = extra + hints[field]
            else:
                hints[field] = extra

    # Per-field disqualifiers: tokens that, if present in the header,
    # mean the header should NOT be claimed by this field even if a
    # hint matches. Prevents e.g. the artist field greedily claiming
    # a "Writer Share %" column because "writer" appears in both the
    # artist hints and the header.
    field_disqualifiers = {
        "artist": ["share", "%", "percent", "percentage", "ownership", "split"],
        "track_title": ["share", "%", "percent", "percentage"],
        # Reject headers that are clearly a *type/category* column, not
        # an actual money column. e.g. "Revenue Type", "Income Type",
        # "Royalty Type", "Category", "Performance Type". Without this
        # the greedy "revenue" hint claims "Revenue Type" before the
        # real "Amount" column, leaving every row with $0.
        "revenue": [
            "%", "percent", "percentage", "share", "exchange rate",
            "type", "category",
        ],
    }

    # Process share_percentage / publisher BEFORE artist so a column
    # like "Writer Share" gets correctly claimed as a share column.
    # Process revenue_type BEFORE revenue so a "Revenue Type" / "Income
    # Type" header is claimed as revenue_type first, leaving the real
    # money column free to be picked up by revenue.
    field_order = [
        "isrc", "upc", "iswc", "work_id",
        "share_percentage", "publisher",
        "track_title", "artist",
        "revenue_type",
        "revenue", "gross_amount", "quantity",
        "territory", "platform",
    ]
    ordered_fields = [f for f in field_order if f in hints] + [f for f in hints if f not in field_order]

    mapping = {f: None for f in hints}
    used_headers = set()
    for field in ordered_fields:
        field_hints = hints[field]
        disqualifiers = field_disqualifiers.get(field, [])
        best_match = None
        for header in headers:
            if header in used_headers:
                continue
            lower = header.lower().strip()
            lower_clean = re.sub(r'\s+', ' ', lower)
            if any(d in lower_clean for d in disqualifiers):
                continue
            for hint in field_hints:
                if hint == lower_clean or re.search(r'(?:^|[\s_\-/])' + re.escape(hint) + r'(?:[\s_\-/]|$)', lower_clean):
                    best_match = header
                    break
            if best_match:
                break
        mapping[field] = best_match
        if best_match:
            used_headers.add(best_match)
    return mapping


def parse_revenue_to_cents(value: Any) -> int:
    if value is None:
        return 0
    try:
        s = str(value).strip().replace(",", "").replace("$", "").replace("£", "").replace("€", "")
        if not s or s == "-":
            return 0
        if s.startswith("(") and s.endswith(")"):
            s = "-" + s[1:-1]
        return int(round(float(s) * 100))
    except (ValueError, TypeError):
        return 0


def parse_quantity(value: Any) -> int:
    if value is None:
        return 0
    try:
        s = str(value).strip().replace(",", "")
        if not s or s == "-":
            return 0
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def format_excel_cell(cell_value, number_format=None) -> str:
    if cell_value is None:
        return ""
    if isinstance(cell_value, (datetime, date)):
        return cell_value.strftime("%Y-%m-%d") if hasattr(cell_value, 'strftime') else str(cell_value)
    if isinstance(cell_value, (int, float)):
        if number_format and '%' in str(number_format):
            converted = cell_value * 100
            if converted == int(converted):
                return str(int(converted))
            return str(round(converted, 4))
        if isinstance(cell_value, float) and cell_value == int(cell_value):
            return str(int(cell_value))
        return str(cell_value)
    return str(cell_value).strip()


MAX_PDF_SIZE_BYTES = 50 * 1024 * 1024
MAX_PDF_PAGES = 50


def _parse_pdf_with_tables(content: bytes) -> tuple:
    import pdfplumber
    try:
        all_table_rows = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = pdf.pages[:MAX_PDF_PAGES]
            for page in pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        if row and any(cell and str(cell).strip() for cell in row):
                            cleaned = [re.sub(r'\s+', ' ', str(cell).strip()) if cell else "" for cell in row]
                            all_table_rows.append(cleaned)

        if not all_table_rows:
            return None, None

        header_idx = 0
        for idx, row in enumerate(all_table_rows[:5]):
            non_empty = sum(1 for v in row if v.strip())
            if non_empty >= 3:
                text_cells = sum(1 for v in row if v.strip() and not v.replace('.', '').replace(',', '').replace('$', '').replace('-', '').strip().isdigit())
                if text_cells >= 3:
                    header_idx = idx
                    break

        headers = all_table_rows[header_idx]
        headers = [h if h else f"Column_{i}" for i, h in enumerate(headers)]

        header_lower = set(h.lower() for h in headers if h and not h.startswith("Column_"))

        rows = []
        for row_data in all_table_rows[header_idx + 1:]:
            row_lower = set(re.sub(r'\s+', ' ', str(v).strip()).lower() for v in row_data if v and str(v).strip())
            if row_lower and header_lower and len(row_lower & header_lower) >= len(header_lower) * 0.6:
                continue

            row_vals = [str(v).strip().lower() for v in row_data if v and str(v).strip()]
            if any(t in val for val in row_vals for t in ("totals:", "total:", "grand total", "sub-total", "subtotal")):
                continue

            row_dict = {}
            for i, val in enumerate(row_data):
                if i < len(headers):
                    row_dict[headers[i]] = val
            if any(v.strip() for v in row_dict.values()):
                rows.append(row_dict)

        return headers, rows
    except Exception as e:
        logger.warning(f"pdfplumber table extraction failed: {e}")
        return None, None


def _extract_pdf_text(content: bytes) -> str:
    import pdfplumber
    full_text = ""
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        pages = pdf.pages[:MAX_PDF_PAGES]
        for page in pages:
            page_text = page.extract_text()
            if page_text:
                full_text += page_text + "\n"
    return full_text


def _parse_pdf_with_ai(content: bytes, org_id: int = None) -> tuple:
    import os
    import json

    try:
        full_text = _extract_pdf_text(content)
    except Exception as e:
        logger.error(f"pdfplumber text extraction failed: {e}")
        raise HTTPException(status_code=400, detail="Could not read text from the PDF. The file may be corrupted or image-only.")

    if not full_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract any text from the PDF. It may be a scanned/image-only document.")

    text_excerpt = full_text[:12000]

    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"), base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL"))

        prompt = f"""You are a royalty statement parser. Extract the tabular data from this royalty statement text into structured JSON.

The text below is from a music royalty statement (e.g., from a PRO like BMI/ASCAP, a distributor like DistroKid/TuneCore, or a DSP). Extract ALL line items into rows.

Look for columns like: Track Title, Artist, ISRC, UPC, Revenue/Earnings/Amount, Territory/Country, Platform/Store, Streams/Quantity, Revenue Type/Income Type, etc.

Return JSON with:
- "headers": list of column name strings
- "rows": list of lists (each inner list = one data row, matching headers order)

Include as many columns as you can identify. If a value is missing for a row, use empty string.

TEXT:
{text_excerpt}

Respond ONLY with valid JSON."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            response_format={"type": "json_object"},
        )

        try:
            usage = response.usage
            if usage:
                from ..services.ai_usage import log_ai_usage_standalone
                log_ai_usage_standalone(
                    feature="royalty_pdf_parsing",
                    model="gpt-4o-mini",
                    input_tokens=usage.prompt_tokens or 0,
                    output_tokens=usage.completion_tokens or 0,
                    org_id=org_id,
                )
        except Exception as ai_log_err:
            logger.warning(f"Failed to log AI usage for royalty PDF parsing: {ai_log_err}")

        result = json.loads(response.choices[0].message.content)
        headers = result.get("headers", [])
        raw_rows = result.get("rows", [])

        if not headers or not raw_rows:
            raise HTTPException(status_code=400, detail="AI could not extract tabular data from the PDF")

        rows = []
        for row_data in raw_rows:
            row_dict = {}
            for i, val in enumerate(row_data):
                if i < len(headers):
                    row_dict[headers[i]] = str(val) if val is not None else ""
            rows.append(row_dict)

        return headers, rows

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"AI PDF parsing failed: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse PDF with AI: {str(e)}")


def parse_uploaded_file(content: bytes, filename: str, org_id: int = None) -> tuple:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "pdf":
        if not PDF_SUPPORT:
            raise HTTPException(status_code=400, detail="PDF support not available")
        if len(content) > MAX_PDF_SIZE_BYTES:
            raise HTTPException(status_code=400, detail=f"PDF file is too large (max {MAX_PDF_SIZE_BYTES // (1024*1024)}MB)")
        try:
            from ..utils.pdf_statement_parser import (
                is_publishing_statement, parse_publishing_statement,
                is_vanguard_statement, parse_vanguard_statement,
                is_bmi_writer_statement, parse_bmi_writer_statement,
            )
            if is_bmi_writer_statement(content):
                bresult = parse_bmi_writer_statement(content)
                if bresult and bresult.get("rows"):
                    logger.info(f"BMI parser: {len(bresult['rows'])} rows extracted")
                    bmeta = bresult.get("metadata", {})
                    bmeta["suggested_mapping"] = {
                        "track_title": "Track Title",
                        "artist": "Writer/Artist",
                        "revenue": "Net Amount",
                        "quantity": "Units",
                        "territory": "Territory",
                        "platform": "Source/Collector",
                        "revenue_type": "Income Type",
                        "gross_amount": "Gross Amount",
                        "release_title": "Source Detail",
                    }
                    return bresult["headers"], bresult["rows"], bmeta
            if is_vanguard_statement(content):
                vresult = parse_vanguard_statement(content)
                if vresult and vresult.get("rows"):
                    logger.info(f"Vanguard parser: {len(vresult['rows'])} rows extracted")
                    vmeta = vresult.get("metadata", {})
                    vmeta["suggested_mapping"] = {
                        "track_title": "Track Title",
                        "artist": "Writer/Artist",
                        "isrc": "ISRC",
                        "revenue": "Net Amount",
                        "quantity": "Units",
                        "platform": "Source/Collector",
                        "revenue_type": "Income Type",
                        "gross_amount": "Gross Amount",
                        "release_title": "Source Detail",
                    }
                    return vresult["headers"], vresult["rows"], vmeta
            if is_publishing_statement(content):
                result = parse_publishing_statement(content)
                if result and result.get("rows"):
                    logger.info(f"Publishing statement parser: {len(result['rows'])} rows extracted")
                    metadata = result.get("metadata", {})
                    metadata["suggested_mapping"] = {
                        "track_title": "Track Title",
                        "artist": "Writer/Artist",
                        "revenue": "Net Amount",
                        "quantity": "Units",
                        "territory": "Territory",
                        "platform": "Source/Collector",
                        "revenue_type": "Income Type",
                        "gross_amount": "Gross Amount",
                        "release_title": "Source Detail",
                    }
                    return result["headers"], result["rows"], metadata
        except Exception as e:
            logger.warning(f"Publishing statement parser failed, falling back: {e}")
        headers, rows = _parse_pdf_with_tables(content)
        if headers and rows:
            pdf_meta = {}
            try:
                full_text = _extract_pdf_text(content)
                grand_match = re.search(r'(?i)grand\s+totals?[:\s]+\$?([\d,]+\.?\d*)', full_text)
                if grand_match:
                    total_str = grand_match.group(1).replace(",", "")
                    pdf_meta["grand_total_net"] = float(total_str)
                else:
                    all_totals = re.findall(r'(?i)totals?:\s*[\d,]+\s+\$?([\d,]+\.?\d*)', full_text)
                    if all_totals:
                        total_str = all_totals[-1].replace(",", "")
                        extracted = float(total_str)
                        row_sum = 0.0
                        rev_col = suggest_column_mapping(headers, "").get("revenue")
                        if rev_col:
                            for r in rows:
                                val = r.get(rev_col, "").replace("$", "").replace(",", "").strip()
                                try:
                                    row_sum += float(val) if val else 0
                                except (ValueError, TypeError):
                                    pass
                        if row_sum > 0 and abs(extracted - row_sum) / row_sum < 0.05:
                            pdf_meta["grand_total_net"] = extracted
                        elif row_sum == 0:
                            pdf_meta["grand_total_net"] = extracted
                if "grand_total_net" in pdf_meta:
                    logger.info(f"Extracted PDF grand total: ${pdf_meta['grand_total_net']:.2f}")
            except Exception as e:
                logger.warning(f"Grand total extraction failed: {e}")
            return headers, rows, pdf_meta
        result = _parse_pdf_with_ai(content, org_id=org_id)
        if isinstance(result, tuple) and len(result) == 2:
            return result[0], result[1], {}
        return result
    elif ext in ("xlsx", "xls"):
        if not EXCEL_SUPPORT:
            raise HTTPException(status_code=400, detail="Excel support not available")
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True)
        ws = wb.active
        all_rows = list(ws.iter_rows(values_only=False))
        if not all_rows:
            wb.close()
            raise HTTPException(status_code=400, detail="File has no data")
        header_idx = 0
        for idx, row in enumerate(all_rows[:10]):
            vals = [c.value for c in row]
            non_empty = sum(1 for v in vals if v is not None and str(v).strip())
            text_count = sum(1 for v in vals if isinstance(v, str) and not v.replace('.', '').replace('-', '').isdigit())
            if non_empty >= 2 and text_count >= 1:
                header_idx = idx
                break
        header_cells = all_rows[header_idx]
        headers = [str(c.value).strip() if c.value else f"Column_{i}" for i, c in enumerate(header_cells)]
        rows = []
        for row in all_rows[header_idx + 1:]:
            if any(c.value is not None for c in row):
                row_dict = {}
                for i, cell in enumerate(row):
                    if i < len(headers):
                        row_dict[headers[i]] = format_excel_cell(cell.value, cell.number_format)
                rows.append(row_dict)
        wb.close()
        return headers, rows, {}
    else:
        try:
            text = content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                text = content.decode('latin-1')
            except Exception:
                raise HTTPException(status_code=400, detail="Unable to decode file")
        reader = csv.DictReader(io.StringIO(text))
        headers = reader.fieldnames or []
        if not headers:
            raise HTTPException(status_code=400, detail="File has no headers")
        rows = list(reader)
        return headers, rows, {}


def match_transaction_to_song(tx: RoyaltyTransaction, songs: List[Song]) -> tuple:
    if tx.original_isrc:
        isrc_clean = tx.original_isrc.strip().upper().replace("-", "")
        for song in songs:
            if song.isrc:
                song_isrc = song.isrc.strip().upper().replace("-", "")
                if song_isrc == isrc_clean:
                    return song.id, 1.0, "MATCHED"

    if tx.original_track_title:
        best_score = 0.0
        best_song_id = None
        tx_title = (tx.original_track_title or "").lower().strip()
        tx_artist = (tx.original_artist or "").lower().strip()

        for song in songs:
            song_title = (song.title or "").lower().strip()
            title_ratio = SequenceMatcher(None, tx_title, song_title).ratio()

            if tx_artist and song.primary_artist:
                song_artist = song.primary_artist.lower().strip()
                artist_ratio = SequenceMatcher(None, tx_artist, song_artist).ratio()
                combined = (title_ratio * 0.6) + (artist_ratio * 0.4)
            else:
                combined = title_ratio

            if combined > best_score:
                best_score = combined
                best_song_id = song.id

        if best_score >= 0.8 and best_song_id is not None:
            return best_song_id, best_score, "MATCHED"

    return None, None, "UNMATCHED"


@router.post(
    "/statements/{org_id}/preview",
    summary='Preview Statement',
    description='Parses an uploaded statement file in-memory (without persisting anything) and returns the detected source type, suggested column mapping, headers, and the first N rows so the operator can confirm before committing via `/upload`.\n\n**Path parameter:** `org_id`.\n**Body (multipart/form-data):** `file` — the statement (CSV/XLSX); `preview_rows?` (default 50).\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ success, detected_source_type, headers, columns, mapping, preview_rows: [...], row_count }`.',
)
async def preview_statement(
    org_id: int,
    file: UploadFile = File(...),
    source_name: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    content = await file.read()
    headers, rows, pdf_metadata = parse_uploaded_file(content, file.filename or "data.csv", org_id=org_id)
    detected_source = detect_pro_source(headers, source_name or "", file.filename or "")
    suggested = pdf_metadata.get("suggested_mapping") if pdf_metadata else None
    mapping = suggested if suggested else suggest_column_mapping(headers, source_name or "")
    preview = rows[:10]
    return {
        "headers": headers,
        "columns": headers,
        "mapping": mapping,
        "preview_rows": preview,
        "row_count": len(rows),
        "detected_source_type": detected_source,
        "success": True,
    }


@router.get(
    "/creators-summary/{org_id}",
    summary='Get Creators Royalty Summary',
    description="Per-creator earnings rollup across the org's statements: lifetime gross, paid-out total, outstanding balance, and the amount of revenue still floating in unassigned statements. Drives the creators table on the royalties dashboard.\n\n**Path parameter:** `org_id`.\n**Query:** `start_date`, `end_date`, `currency`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ creators: [{creator_id, name, gross_dollars, paid_dollars, balance_dollars, statement_count}], unassigned_count, unassigned_revenue_dollars }`.",
)
def get_creators_royalty_summary(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    creators = db.query(Creator).filter(Creator.organization_id == org_id).order_by(Creator.display_name).all()

    from sqlalchemy import func
    stmt_stats = db.query(
        RoyaltyStatement.creator_id,
        func.count(RoyaltyStatement.id).label("statement_count"),
        func.sum(RoyaltyStatement.total_revenue_cents).label("total_revenue_cents"),
        func.max(RoyaltyStatement.created_at).label("latest_statement"),
        func.sum(RoyaltyStatement.matched_transactions).label("matched"),
        func.sum(RoyaltyStatement.total_transactions).label("total_lines"),
    ).filter(
        RoyaltyStatement.organization_id == org_id,
        RoyaltyStatement.creator_id.isnot(None),
    ).group_by(RoyaltyStatement.creator_id).all()

    stats_map = {}
    for row in stmt_stats:
        stats_map[row.creator_id] = {
            "statement_count": row.statement_count or 0,
            "total_revenue_cents": row.total_revenue_cents or 0,
            "latest_statement": row.latest_statement.isoformat() if row.latest_statement else None,
            "matched_lines": row.matched or 0,
            "total_lines": row.total_lines or 0,
        }

    unassigned = db.query(
        func.count(RoyaltyStatement.id).label("count"),
        func.sum(RoyaltyStatement.total_revenue_cents).label("rev"),
    ).filter(
        RoyaltyStatement.organization_id == org_id,
        RoyaltyStatement.creator_id.is_(None),
    ).first()

    result = []
    for c in creators:
        s = stats_map.get(c.id, {})
        result.append({
            "creator_id": c.id,
            "display_name": c.display_name,
            "roles": c.roles if hasattr(c, 'roles') else None,
            "statement_count": s.get("statement_count", 0),
            "total_revenue_dollars": (s.get("total_revenue_cents", 0) or 0) / 100.0,
            "latest_statement": s.get("latest_statement"),
            "matched_lines": s.get("matched_lines", 0),
            "total_lines": s.get("total_lines", 0),
        })

    return {
        "creators": result,
        "unassigned_count": unassigned.count if unassigned else 0,
        "unassigned_revenue_dollars": ((unassigned.rev or 0) / 100.0) if unassigned else 0,
    }


@router.post(
    "/statements/{org_id}/assign-unassigned",
    summary='Assign Unassigned Statements',
    description='Bulk-assigns every RoyaltyStatement that currently has no creator attached to a single target creator. Used after import when a batch was uploaded without the creator id set.\n\n**Path parameter:** `org_id`.\n**Body:** `{ creator_id: int, statement_ids?: int[] }`. When `statement_ids` is omitted, every unassigned statement in the org is reassigned.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ assigned, creator_id, creator_name }`.',
)
def assign_unassigned_statements(
    org_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    creator_id = body.get("creator_id")
    if not creator_id:
        raise HTTPException(status_code=400, detail="creator_id is required")

    creator = db.query(Creator).filter(Creator.id == creator_id, Creator.organization_id == org_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found in this organization")

    updated = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.organization_id == org_id,
        RoyaltyStatement.creator_id.is_(None),
    ).update({"creator_id": creator_id}, synchronize_session="fetch")

    db.commit()
    return {"assigned": updated, "creator_id": creator_id, "creator_name": creator.display_name}


@router.get("/statements/{org_id}", summary="List royalty statements", description='Returns every royalty statement ingested for the organization with paging and status filters.\n\n**Path parameter:** `org_id`.\n**Query:** `status`, `source_type` (`dsp|label|publisher|sync|other`), `period_start`, `period_end`, `limit`, `offset`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ total, statements: [{id, source_name, source_type, period_start, period_end, total_amount_cents, currency, status, uploaded_at}] }`.')
def list_statements(
    org_id: int,
    status: Optional[str] = None,
    source: Optional[str] = None,
    creator_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(RoyaltyStatement).filter(RoyaltyStatement.organization_id == org_id)
    if status:
        query = query.filter(RoyaltyStatement.status == status)
    if source:
        query = query.filter(RoyaltyStatement.source_name.ilike(f"%{source}%"))
    if creator_id is not None:
        query = query.filter(RoyaltyStatement.creator_id == creator_id)
    total = query.count()
    statements = query.order_by(desc(RoyaltyStatement.created_at)).offset(skip).limit(limit).all()

    creator_ids = set(s.creator_id for s in statements if s.creator_id)
    creator_map = {}
    if creator_ids:
        creators = db.query(Creator).filter(Creator.id.in_(creator_ids)).all()
        creator_map = {c.id: c.display_name for c in creators}

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "statements": [
            {
                "id": s.id,
                "source_name": s.source_name,
                "source_type": s.source_type,
                "period_start": s.period_start.isoformat() if s.period_start else None,
                "period_end": s.period_end.isoformat() if s.period_end else None,
                "currency": s.currency,
                "total_revenue_cents": s.total_revenue_cents,
                "total_revenue_dollars": (s.total_revenue_cents or 0) / 100.0,
                "total_transactions": s.total_transactions,
                "matched_transactions": s.matched_transactions,
                "unmatched_transactions": s.unmatched_transactions,
                "status": s.status,
                "file_name": s.file_name,
                "creator_id": s.creator_id,
                "creator_name": creator_map.get(s.creator_id) if s.creator_id else None,
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in statements
        ],
    }


@router.get("/statements/{org_id}/{statement_id}", summary="Get royalty statement detail", description='Returns the statement header plus a paged view of its transactions.\n\n**Path parameters:** `org_id`, `statement_id`.\n**Query:** `limit` (default 50), `offset`, `unmatched_only?: bool`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ statement: {...}, transactions: {total, items: [{id, title, artist, isrc, units, amount_cents, matched_song_id}]} }`.')
def get_statement(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    alloc_total = db.query(func.coalesce(func.sum(RoyaltyAllocation.allocated_cents), 0)).join(
        RoyaltyTransaction, RoyaltyAllocation.transaction_id == RoyaltyTransaction.id
    ).filter(RoyaltyTransaction.statement_id == statement_id).scalar()

    return {
        "id": stmt.id,
        "organization_id": stmt.organization_id,
        "source_name": stmt.source_name,
        "source_type": stmt.source_type,
        "period_start": stmt.period_start.isoformat() if stmt.period_start else None,
        "period_end": stmt.period_end.isoformat() if stmt.period_end else None,
        "currency": stmt.currency,
        "exchange_rate": stmt.exchange_rate,
        "file_name": stmt.file_name,
        "total_revenue_cents": stmt.total_revenue_cents,
        "total_revenue_dollars": stmt.total_revenue_cents / 100.0,
        "total_transactions": stmt.total_transactions,
        "matched_transactions": stmt.matched_transactions,
        "unmatched_transactions": stmt.unmatched_transactions,
        "status": stmt.status,
        "processing_notes": stmt.processing_notes,
        "column_mapping": stmt.column_mapping,
        "total_allocated_cents": alloc_total,
        "total_allocated_dollars": alloc_total / 100.0,
        "total_unallocated_cents": stmt.total_revenue_cents - alloc_total,
        "total_unallocated_dollars": (stmt.total_revenue_cents - alloc_total) / 100.0,
        "created_at": stmt.created_at.isoformat() if stmt.created_at else None,
        "updated_at": stmt.updated_at.isoformat() if stmt.updated_at else None,
    }


class StatementMetaUpdate(BaseModel):
    source_name: Optional[str] = None
    source_type: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    currency: Optional[str] = None
    # Allow re-assigning the statement to a different client/creator
    # within the same org (or clearing it with `null`). Used to fix
    # mis-assigned uploads (e.g. duplicate row in the wrong org).
    creator_id: Optional[int] = None


@router.patch(
    "/statements/{org_id}/{statement_id}",
    summary="Edit royalty statement metadata",
    description=(
        "Patches editable metadata on an uploaded `RoyaltyStatement` — most "
        "commonly to fix `period_start` / `period_end` when the parser couldn't "
        "extract them from the PDF header (BMI / publisher quirks). Also "
        "supports correcting `source_name`, `source_type`, and `currency`. "
        "Does NOT change the underlying file or any line / ledger amounts.\n\n"
        "**Path parameters:** `org_id`, `statement_id`.\n"
        "**Body:** any subset of `{ source_name, source_type, period_start, "
        "period_end, currency }`.\n"
        "**Auth:** Bearer JWT — caller must be an OWNER, ADMIN, or have "
        "royalties write permission on the org.\n"
        "**Audit:** Writes a `STATEMENT_UPDATE` row to `audit_logs` with the "
        "field-level diff."
    ),
)
def update_statement_meta(
    org_id: int,
    statement_id: int,
    body: StatementMetaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Owner / Admin / Member can correct statement metadata (a "royalty
    # write" capability — there is no granular permission flag in this
    # codebase yet, so MEMBER is treated as the equivalent role).
    # CLIENT-tier members and external viewers are blocked.
    membership = verify_org_access(current_user, org_id, db)
    role = (getattr(membership, "role", "") or "").upper()
    if not current_user.is_super_admin and role not in ("OWNER", "ADMIN", "MEMBER"):
        raise HTTPException(
            status_code=403,
            detail="Editing statement metadata requires royalty-write access (Owner, Admin, or Member role).",
        )

    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    # Build a field-level diff for the audit log so reconciliation reviewers
    # can see exactly what was corrected and by whom.
    changes: dict = {}

    if body.source_name is not None:
        new_name = normalize_source_name(body.source_name)
        if new_name and new_name != stmt.source_name:
            changes["source_name"] = {"old": stmt.source_name, "new": new_name}
            stmt.source_name = new_name

    if body.source_type is not None:
        # Same canonical-registry gate as the upload routes — reject
        # unknown types up front so the metadata PATCH can't sneak a
        # garbage source_type past the API boundary.
        canonical_st = canonical_source_type(body.source_type)
        if not canonical_st:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_source_type",
                    "message": (
                        f"Unknown source_type {body.source_type!r}. "
                        f"Accepted values: {sorted(PRO_SOURCE_TYPES.keys())}"
                    ),
                    "value": body.source_type,
                    "accepted": sorted(PRO_SOURCE_TYPES.keys()),
                },
            )
        if canonical_st != stmt.source_type:
            changes["source_type"] = {"old": stmt.source_type, "new": canonical_st}
            stmt.source_type = canonical_st

    if body.currency is not None:
        new_cur = body.currency.strip().upper()[:3]
        if new_cur and new_cur != stmt.currency:
            changes["currency"] = {"old": stmt.currency, "new": new_cur}
            stmt.currency = new_cur

    # Period validation: if both supplied, start must be ≤ end. Returns
    # 400 (per task spec) so the frontend treats it as an actionable
    # form-validation error rather than a Pydantic schema rejection.
    new_start = body.period_start if body.period_start is not None else stmt.period_start
    new_end = body.period_end if body.period_end is not None else stmt.period_end
    if new_start and new_end and new_start > new_end:
        raise HTTPException(
            status_code=400,
            detail="period_start must be on or before period_end",
        )

    # creator_id: validate the target creator exists in this org (or
    # explicitly clear with null). Treats `0` as "no change" because
    # some HTML form serializations coerce blank → 0.
    if "creator_id" in body.model_fields_set:
        new_creator_id = body.creator_id  # may be None to unassign
        if new_creator_id is not None:
            from ..models.models import Creator
            target = db.query(Creator).filter(
                Creator.id == new_creator_id,
                Creator.organization_id == org_id,
            ).first()
            if not target:
                raise HTTPException(
                    status_code=400,
                    detail="creator_id does not belong to this organization",
                )
        if new_creator_id != stmt.creator_id:
            changes["creator_id"] = {"old": stmt.creator_id, "new": new_creator_id}
            stmt.creator_id = new_creator_id

    if body.period_start is not None and body.period_start != stmt.period_start:
        changes["period_start"] = {
            "old": stmt.period_start.isoformat() if stmt.period_start else None,
            "new": body.period_start.isoformat(),
        }
        stmt.period_start = body.period_start

    if body.period_end is not None and body.period_end != stmt.period_end:
        changes["period_end"] = {
            "old": stmt.period_end.isoformat() if stmt.period_end else None,
            "new": body.period_end.isoformat(),
        }
        stmt.period_end = body.period_end

    if not changes:
        # Nothing actually changed — return current state without an audit row.
        return {
            "id": stmt.id,
            "source_name": stmt.source_name,
            "source_type": stmt.source_type,
            "period_start": stmt.period_start.isoformat() if stmt.period_start else None,
            "period_end": stmt.period_end.isoformat() if stmt.period_end else None,
            "currency": stmt.currency,
            "changed": False,
        }

    # Audit the change in the SAME transaction as the metadata mutation. If
    # the audit insert fails, we MUST roll the metadata change back too — a
    # silent unaudited correction to a financial statement is a worse
    # outcome than rejecting the request.
    try:
        from ..services.audit_service import log_action
        log_action(
            db=db,
            organization_id=org_id,
            user_id=current_user.id,
            action="STATEMENT_UPDATE",
            entity_type="RoyaltyStatement",
            entity_id=stmt.id,
            entity_name=stmt.source_name or stmt.file_name,
            details={"changes": changes},
        )
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"update_statement_meta: audit log failed, rolling back: {e}")
        raise HTTPException(
            status_code=500,
            detail="Could not record audit entry; statement was not modified.",
        )

    db.refresh(stmt)

    return {
        "id": stmt.id,
        "source_name": stmt.source_name,
        "source_type": stmt.source_type,
        "period_start": stmt.period_start.isoformat() if stmt.period_start else None,
        "period_end": stmt.period_end.isoformat() if stmt.period_end else None,
        "currency": stmt.currency,
        "changed": True,
        "changes": changes,
    }


@router.post("/statements/{org_id}/upload", summary="Upload royalty statement", description='Ingests a CSV / XLSX / PDF royalty statement, normalizes columns, and stages it for matching. Supports DSP, label, publisher, and sync statement formats.\n\n**Path parameter:** `org_id`.\n**Body (multipart/form-data):** `file`; `source_name`; `source_type` (`dsp|label|publisher|sync|other`); `period_start?`; `period_end?`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ statement_id, status, total_rows, total_amount_cents, currency }`.')
async def upload_statement(
    org_id: int,
    file: UploadFile = File(...),
    source_name: str = Form(...),
    source_type: Optional[str] = Form(None),
    period_start: Optional[str] = Form(None),
    period_end: Optional[str] = Form(None),
    currency: str = Form("USD"),
    column_mapping: Optional[str] = Form(None),
    creator_id: Optional[int] = Form(None),
    force: bool = Form(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    source_name = normalize_source_name(source_name)

    # Canonicalize source_type at the API boundary against the
    # central StatementSourceType registry. Unknown values are a
    # client bug — fail fast with the list of accepted values rather
    # than silently persisting a garbage type that breaks the
    # downstream registry-aware mapping suggestions.
    if source_type:
        canonical = canonical_source_type(source_type)
        if not canonical:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "invalid_source_type",
                    "message": (
                        f"Unknown source_type {source_type!r}. "
                        f"Accepted values: {sorted(PRO_SOURCE_TYPES.keys())}"
                    ),
                    "value": source_type,
                    "accepted": sorted(PRO_SOURCE_TYPES.keys()),
                },
            )
        source_type = canonical

    content = await file.read()

    # Duplicate detection: same org + same file_name + same byte size = same upload.
    # Pass `force=true` to override (e.g. legitimate re-upload of an updated file
    # that happens to share a name). Returns 409 with the existing statement id.
    if file.filename and not force:
        existing_dup = db.query(RoyaltyStatement).filter(
            RoyaltyStatement.organization_id == org_id,
            RoyaltyStatement.file_name == file.filename,
        ).first()
        if existing_dup is not None:
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "duplicate_statement",
                    "message": (
                        f"A statement with file name '{file.filename}' was already "
                        f"uploaded (id={existing_dup.id}, status={existing_dup.status}). "
                        f"Re-submit with force=true to override."
                    ),
                    "existing_statement_id": existing_dup.id,
                    "existing_status": existing_dup.status,
                    "existing_uploaded_at": existing_dup.created_at.isoformat() if existing_dup.created_at else None,
                },
            )

    # Single-call orchestrator: parse file → resolve source-type →
    # registry-aware column-mapping suggestion (biased by the
    # canonical source-type, so per-source extra_hints win over the
    # generic baseline). Mirrors what /royalty-processing/.../upload
    # does so both upload paths share one parser surface.
    from ..services.statement_parser import parse_statement_file
    parsed = parse_statement_file(
        content,
        file.filename or "data.csv",
        source_name=source_name or "",
        source_type=source_type,
        org_id=org_id,
    )
    headers = parsed.headers
    rows = parsed.rows
    pdf_metadata = parsed.pdf_metadata
    if parsed.resolved_source_type and not source_type:
        source_type = parsed.resolved_source_type

    suggested = pdf_metadata.get("suggested_mapping") if pdf_metadata else None
    if suggested:
        mapping = suggested
    elif column_mapping:
        import json
        try:
            mapping = json.loads(column_mapping)
        except Exception:
            mapping = parsed.suggested_mapping
    else:
        mapping = parsed.suggested_mapping

    # Defensive: if the resolved mapping references headers that don't actually
    # appear in the parsed row dictionaries, the row.get(col) lookups silently
    # return None and we end up persisting empty transactions. Fall back to
    # auto-detecting column mappings against the actual row keys we got.
    if rows:
        row_keys = set(rows[0].keys())
        mapped_headers = {v for v in (mapping or {}).values() if v}
        if mapped_headers and not (mapped_headers & row_keys):
            logger.warning(
                f"Resolved mapping headers {mapped_headers} not found in row keys {row_keys}; "
                f"falling back to header-based column suggestion"
            )
            mapping = suggest_column_mapping(list(row_keys), source_name or "")

    logger.info(
        f"upload_statement: parsed {len(rows)} rows from {file.filename!r}; "
        f"suggested_mapping={'yes' if suggested else 'no'}; resolved mapping={mapping}"
    )

    p_start = None
    p_end = None
    if period_start:
        try:
            p_start = date.fromisoformat(period_start)
        except ValueError:
            pass
    if period_end:
        try:
            p_end = date.fromisoformat(period_end)
        except ValueError:
            pass

    # Auto-extract period from PDF header if the caller didn't supply one.
    # Recognizes "Performance Period: Jul - Dec 2023" / "Statement Period: ..."
    # patterns common to BMI, ASCAP, and most publisher statements.
    if (p_start is None or p_end is None) and (file.filename or "").lower().endswith(".pdf"):
        try:
            from ..utils.pdf_statement_parser import parse_period_from_pdf
            auto_start, auto_end = parse_period_from_pdf(content, file_name=file.filename)
            if p_start is None and auto_start is not None:
                p_start = auto_start
            if p_end is None and auto_end is not None:
                p_end = auto_end
            if auto_start or auto_end:
                logger.info(f"upload_statement: auto-parsed period {auto_start} - {auto_end} from PDF header")
        except Exception as e:
            logger.warning(f"upload_statement: period auto-parse failed: {e}")

    statement = RoyaltyStatement(
        organization_id=org_id,
        source_name=source_name,
        source_type=source_type,
        period_start=p_start,
        period_end=p_end,
        currency=currency,
        file_name=file.filename,
        status="PROCESSING",
        column_mapping=mapping,
        uploaded_by_user_id=current_user.id,
        creator_id=creator_id,
    )
    db.add(statement)
    db.flush()

    org_songs = db.query(Song).filter(Song.organization_id == org_id).all()

    total_rev = 0
    matched_count = 0
    unmatched_count = 0
    transactions = []

    isrc_col = mapping.get("isrc")
    upc_col = mapping.get("upc")
    title_col = mapping.get("track_title")
    artist_col = mapping.get("artist")
    rev_col = mapping.get("revenue")
    qty_col = mapping.get("quantity")
    territory_col = mapping.get("territory")
    platform_col = mapping.get("platform")
    rev_type_col = mapping.get("revenue_type")

    for row in rows:
        rev_cents = parse_revenue_to_cents(row.get(rev_col) if rev_col else None)
        qty = parse_quantity(row.get(qty_col) if qty_col else None)

        tx = RoyaltyTransaction(
            statement_id=statement.id,
            organization_id=org_id,
            original_isrc=row.get(isrc_col, "").strip() if isrc_col else None,
            original_upc=row.get(upc_col, "").strip() if upc_col else None,
            original_track_title=row.get(title_col, "").strip() if title_col else None,
            original_artist=row.get(artist_col, "").strip() if artist_col else None,
            revenue_cents=rev_cents,
            currency=currency,
            quantity=qty,
            territory=row.get(territory_col, "").strip() if territory_col else None,
            platform=row.get(platform_col, "").strip() if platform_col else None,
            revenue_type=row.get(rev_type_col, "").strip() if rev_type_col else None,
            raw_data=row,
        )

        song_id, confidence, status = match_transaction_to_song(tx, org_songs)
        tx.song_id = song_id
        tx.match_confidence = confidence
        tx.match_status = status

        if status == "MATCHED":
            matched_count += 1
        else:
            unmatched_count += 1

        total_rev += rev_cents
        transactions.append(tx)

    db.add_all(transactions)

    grand_total_net = pdf_metadata.get("grand_total_net") if pdf_metadata else None
    if grand_total_net is not None:
        logger.info(f"Using PDF Grand Total for revenue: ${grand_total_net:.2f} (parsed sum: ${total_rev / 100:.2f})")

    line_parse_warning = None
    try:
        from ..services.royalty_processing_engine import parse_statement_to_lines, auto_match_lines
        line_count = parse_statement_to_lines(db, statement.id, org_id, mapping, rows, pdf_metadata=pdf_metadata)
        if line_count > 0:
            auto_match_lines(db, statement.id, org_id)
            logger.info(f"Created {line_count} statement lines for statement {statement.id}")
    except Exception as e:
        line_parse_warning = str(e)
        logger.warning(f"Failed to create statement lines: {e}")

    # parse_statement_to_lines writes statement.total_transactions with its own
    # line count. For the basic Statements upload flow we want the success dialog
    # and Statements table to reflect the RoyaltyTransaction rows we actually
    # persisted (the source of truth for this view), so set everything AFTER the
    # lines call.
    statement.total_transactions = len(transactions)
    statement.matched_transactions = matched_count
    statement.unmatched_transactions = unmatched_count
    if grand_total_net is not None:
        statement.total_revenue_cents = int(round(grand_total_net * 100))
    else:
        statement.total_revenue_cents = total_rev
    statement.status = "PROCESSED" if unmatched_count == 0 else "PARTIALLY_MATCHED"

    logger.info(
        f"upload_statement: persisted {len(transactions)} transactions "
        f"({matched_count} matched, {unmatched_count} unmatched), "
        f"total_revenue=${statement.total_revenue_cents / 100:.2f}, statement_id={statement.id}"
    )

    from ..services.audit_service import log_action
    log_action(db, org_id, current_user.id, "UPLOAD", "STATEMENT", statement.id, source_name,
               details={"file_name": file.filename, "source_type": source_type, "currency": currency,
                        "total_transactions": statement.total_transactions, "creator_id": creator_id})

    db.commit()
    db.refresh(statement)

    result = {
        "id": statement.id,
        "status": statement.status,
        "total_transactions": statement.total_transactions,
        "matched_transactions": statement.matched_transactions,
        "unmatched_transactions": statement.unmatched_transactions,
        "total_revenue_cents": statement.total_revenue_cents,
        "total_revenue_dollars": statement.total_revenue_cents / 100.0,
    }
    if line_parse_warning:
        result["warning"] = f"Statement uploaded but line parsing failed: {line_parse_warning}"
    return result


def _build_statement_delete_summary(db: Session, stmt: "RoyaltyStatement") -> Dict[str, Any]:
    """Build a non-mutating summary of everything that will be removed
    (and balances that will be restored) when this statement is deleted.

    Used by both the delete endpoint (to write into the audit log and
    drive the actual cleanup) and the delete-preview endpoint (so the
    frontend can show a confirmation dialog with real numbers).
    """
    from ..models.models import (
        RoyaltyLedgerEntry, RoyaltyProcessingRun, RoyaltyStatementLine,
        AdvanceV2, ActionItem, PayoutItem,
    )
    from datetime import timedelta

    statement_id = stmt.id
    org_id = stmt.organization_id

    tx_count = db.query(func.count(RoyaltyTransaction.id)).filter(
        RoyaltyTransaction.statement_id == statement_id
    ).scalar() or 0
    line_count = db.query(func.count(RoyaltyStatementLine.id)).filter(
        RoyaltyStatementLine.statement_id == statement_id
    ).scalar() or 0
    run_count = db.query(func.count(RoyaltyProcessingRun.id)).filter(
        RoyaltyProcessingRun.statement_id == statement_id
    ).scalar() or 0

    tx_ids = [t.id for t in db.query(RoyaltyTransaction.id).filter(
        RoyaltyTransaction.statement_id == statement_id
    ).all()]
    alloc_count = 0
    if tx_ids:
        alloc_count = db.query(func.count(RoyaltyAllocation.id)).filter(
            RoyaltyAllocation.transaction_id.in_(tx_ids)
        ).scalar() or 0

    # Per-advance restore amounts (RECOUPMENT_APPLIED entries only).
    recoup_rows = db.query(
        RoyaltyLedgerEntry.advance_id,
        func.sum(func.abs(RoyaltyLedgerEntry.amount_cents)),
    ).filter(
        RoyaltyLedgerEntry.statement_id == statement_id,
        RoyaltyLedgerEntry.entry_type == "RECOUPMENT_APPLIED",
        RoyaltyLedgerEntry.advance_id.isnot(None),
    ).group_by(RoyaltyLedgerEntry.advance_id).all()

    advance_restores = []
    for adv_id, restore_cents in recoup_rows:
        adv = db.query(AdvanceV2).filter(AdvanceV2.id == adv_id).first()
        advance_restores.append({
            "advance_id": adv_id,
            "advance_name": adv.advance_name if adv else None,
            "restore_cents": int(restore_cents or 0),
            "restore_dollars": int(restore_cents or 0) / 100.0,
        })

    # PAYMENT ledger entries that reference this statement. We use
    # the deterministic FK RoyaltyLedgerEntry.payout_item_id (set by
    # record_payment_ledger). For legacy ledger entries written before
    # that column existed, fall back to a (payee_id, amount, paid_at
    # ±5min) heuristic so historic data still unwinds correctly.
    payment_rows = db.query(RoyaltyLedgerEntry).filter(
        RoyaltyLedgerEntry.statement_id == statement_id,
        RoyaltyLedgerEntry.entry_type == "PAYMENT",
    ).all()
    payments = []
    for p in payment_rows:
        candidate = None
        if p.payout_item_id:
            candidate = db.query(PayoutItem).filter(
                PayoutItem.id == p.payout_item_id,
                PayoutItem.org_id == org_id,
            ).first()
        if candidate is None:
            positive_cents = abs(p.amount_cents or 0)
            match_window = timedelta(minutes=5)
            candidate = db.query(PayoutItem).filter(
                PayoutItem.org_id == org_id,
                PayoutItem.payee_id == p.payee_id,
                PayoutItem.amount_cents == positive_cents,
                PayoutItem.paid_at.isnot(None),
                PayoutItem.paid_at >= (p.created_at - match_window) if p.created_at else PayoutItem.paid_at.isnot(None),
                PayoutItem.paid_at <= (p.created_at + match_window) if p.created_at else PayoutItem.paid_at.isnot(None),
            ).order_by(PayoutItem.paid_at.desc()).first()
        payments.append({
            "ledger_entry_id": p.id,
            "payee_id": p.payee_id,
            "amount_cents": p.amount_cents,
            "amount_dollars": (p.amount_cents or 0) / 100.0,
            "memo": p.memo,
            "payout_item_id": candidate.id if candidate else None,
            "payout_batch_id": candidate.batch_id if candidate else None,
            "linkage": "fk" if (p.payout_item_id and candidate) else ("heuristic" if candidate else "none"),
        })

    ledger_count = db.query(func.count(RoyaltyLedgerEntry.id)).filter(
        RoyaltyLedgerEntry.statement_id == statement_id
    ).scalar() or 0

    # Auto-generated action items pointing at this statement, plus any
    # action items pointing at one of the statement's lines.
    line_ids = [r[0] for r in db.query(RoyaltyStatementLine.id).filter(
        RoyaltyStatementLine.statement_id == statement_id
    ).all()]

    # Action items pointing at this statement. We use the new
    # deterministic ActionItem.entity_id column (populated by
    # generate_statement_action_items). For rows written before that
    # column existed, fall back to anchored title patterns so we
    # still catch legacy auto-generated items without false-matching
    # neighboring statement ids (#1 vs #10).
    title_pattern_colon = f"Statement #{statement_id}:%"
    title_pattern_space = f"Statement #{statement_id} %"
    from sqlalchemy import or_ as _or, and_ as _and
    action_q = db.query(ActionItem).filter(
        ActionItem.organization_id == org_id,
        ActionItem.entity_type == "STATEMENT",
        _or(
            ActionItem.entity_id == statement_id,
            _and(
                ActionItem.entity_id.is_(None),
                _or(
                    ActionItem.title.like(title_pattern_colon),
                    ActionItem.title.like(title_pattern_space),
                ),
            ),
        ),
    )
    action_items_to_remove = action_q.count()
    line_action_items_to_remove = 0
    if line_ids:
        line_action_items_to_remove = db.query(func.count(ActionItem.id)).filter(
            ActionItem.organization_id == org_id,
            ActionItem.entity_type == "STATEMENT_LINE",
            _or(
                ActionItem.entity_id.in_(line_ids),
                ActionItem.entity_label.in_([str(i) for i in line_ids]),
            ),
        ).scalar() or 0

    file_path = stmt.file_path
    file_will_be_deleted = bool(file_path) and _safe_under_uploads(file_path) and os.path.exists(file_path)

    return {
        "statement_id": statement_id,
        "source_name": stmt.source_name,
        "transaction_count": int(tx_count),
        "line_count": int(line_count),
        "allocation_count": int(alloc_count),
        "processing_run_count": int(run_count),
        "ledger_entry_count": int(ledger_count),
        "total_revenue_cents": int(stmt.total_revenue_cents or 0),
        "total_revenue_dollars": int(stmt.total_revenue_cents or 0) / 100.0,
        "advance_restores": advance_restores,
        "payments_unwound": payments,
        "action_items_to_remove": int(action_items_to_remove + line_action_items_to_remove),
        "file_path": file_path if file_will_be_deleted else None,
        "file_will_be_deleted": file_will_be_deleted,
    }


def _safe_under_uploads(path: str) -> bool:
    """Path-traversal guard: only allow removing files that resolve
    inside the project's uploads directory."""
    if not path:
        return False
    try:
        # Project layout: backend/uploads/ (created by upload routes
        # that persist files). Use realpath to resolve any symlinks.
        project_root = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
        uploads_root = os.path.realpath(os.path.join(project_root, "backend", "uploads"))
        target = os.path.realpath(path)
        return target.startswith(uploads_root + os.sep) or target == uploads_root
    except Exception:
        return False


@router.get("/statements/{org_id}/{statement_id}/delete-preview", summary="Return a non-mutating summary of what `DELETE` would remove", description='Returns a non-mutating summary of what `DELETE /statements/.../{statement_id}` would remove (matched transactions, advances to restore, payments to unwind, actions to clear).\n\n**Path parameters:** `org_id`, `statement_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ statement_id, transactions: int, allocations: int, advances_restored_cents: int, payments_unwound: int, action_items_cleared: int }`.')
def delete_statement_preview(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return a non-mutating summary of what `DELETE` would remove.

    The frontend uses this to populate the confirmation dialog so the
    user knows exactly what's about to disappear (transactions, lines,
    advance balances that will be restored, payment links that will
    be unwound, action items, file on disk).
    """
    verify_org_access(current_user, org_id, db)
    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")
    return _build_statement_delete_summary(db, stmt)


def _notify_payouts_unwound(
    db: Session,
    org_id: int,
    stmt,
    deleted_by: User,
    affected_payouts: list,
):
    """Notify users that paid payouts were unwound by a statement
    delete. Recipients:
      - The user who created each affected PayoutBatch (PayoutItem
        has no direct created_by; the batch is the closest proxy).
      - All org OWNER and ADMIN members.
    The user who performed the delete is excluded.
    Each recipient gets an in-app notification; users with
    email_enabled for this notification type also get an email.
    """
    from .notifications import create_notification
    from ..models.models import (
        PayoutBatch, NotificationPreference, NotificationType,
    )

    batch_ids = sorted({p.batch_id for p in affected_payouts if p.batch_id})
    payout_ids = sorted({p.id for p in affected_payouts})

    creator_user_ids: set[int] = set()
    if batch_ids:
        rows = db.query(PayoutBatch.created_by_user_id).filter(
            PayoutBatch.org_id == org_id,
            PayoutBatch.id.in_(batch_ids),
            PayoutBatch.created_by_user_id.isnot(None),
        ).all()
        creator_user_ids = {r[0] for r in rows if r[0] is not None}

    admin_rows = db.query(OrganizationMember.user_id).filter(
        OrganizationMember.organization_id == org_id,
        OrganizationMember.role.in_(["OWNER", "ADMIN"]),
    ).all()
    admin_user_ids = {r[0] for r in admin_rows}

    recipient_ids = (creator_user_ids | admin_user_ids) - {deleted_by.id}
    if not recipient_ids:
        return

    deleter_label = deleted_by.username or deleted_by.email or f"User #{deleted_by.id}"
    source_name = stmt.source_name or f"Statement #{stmt.id}"
    n_payouts = len(payout_ids)
    payout_word = "payout" if n_payouts == 1 else "payouts"
    title = "Paid payout undone by statement delete"
    message = (
        f"{deleter_label} deleted statement \u201C{source_name}\u201D, "
        f"undoing {n_payouts} paid {payout_word}. The payout record "
        f"is preserved but is no longer marked paid."
    )
    if batch_ids:
        link = f"/royalties?tab=payouts&batch_id={batch_ids[0]}"
    else:
        link = "/royalties?tab=payouts"
    extra = {
        "statement_id": stmt.id,
        "statement_source_name": source_name,
        "deleted_by_user_id": deleted_by.id,
        "deleted_by_username": deleter_label,
        "payout_item_ids": payout_ids,
        "payout_batch_ids": batch_ids,
    }
    ntype = NotificationType.PAYOUT_UNWOUND_BY_STATEMENT_DELETE.value

    email_provider = None
    for uid in recipient_ids:
        try:
            create_notification(
                db=db,
                user_id=uid,
                notification_type=ntype,
                title=title,
                message=message,
                link=link,
                organization_id=org_id,
                extra_data=extra,
            )
        except Exception as e:
            logger.warning(f"in-app payout-unwind notify failed for user {uid}: {e}")

        try:
            pref = db.query(NotificationPreference).filter(
                NotificationPreference.user_id == uid,
                NotificationPreference.notification_type == ntype,
            ).first()
            if not pref or not pref.email_enabled:
                continue
            recipient = db.query(User).filter(User.id == uid).first()
            if not recipient or not recipient.email:
                continue
            if email_provider is None:
                from ..services.email_provider import get_email_provider
                email_provider = get_email_provider()
            html = (
                f"<p>Hi {recipient.username or 'there'},</p>"
                f"<p><strong>{deleter_label}</strong> deleted the royalty "
                f"statement <strong>{source_name}</strong>, which undid "
                f"<strong>{n_payouts}</strong> paid {payout_word} in your "
                f"organization.</p>"
                f"<p>The payout record itself is preserved, but its paid "
                f"status has been cleared so it will reappear as unpaid "
                f"in your payout history.</p>"
                f"<p><a href=\"{link}\">View affected payout(s)</a></p>"
                f"<p>You're getting this because you created the payout "
                f"batch or you're an OWNER/ADMIN of the organization.</p>"
            )
            email_provider.send_email(
                to=recipient.email,
                subject=f"Cadence: paid payout undone ({source_name})",
                html_body=html,
            )
        except Exception as e:
            logger.warning(f"email payout-unwind notify failed for user {uid}: {e}")


def _perform_statement_delete(
    db: Session,
    stmt: "RoyaltyStatement",
    org_id: int,
    current_user: User,
) -> Dict[str, Any]:
    """Run the exhaustive per-statement delete (steps 1-5 + audit log
    + ORM delete) without committing. Returns the summary dict that
    was computed and audit-logged. Callers are responsible for the
    final ``db.commit()`` so this can run alongside other deletes
    inside a single transaction (used by bulk delete).
    """
    from ..models.models import (
        RoyaltyLedgerEntry, RoyaltyProcessingRun, RoyaltyStatementLine,
        AdvanceV2, ActionItem,
    )
    from ..services.audit_service import log_action

    statement_id = stmt.id
    summary = _build_statement_delete_summary(db, stmt)

    # 1. Restore advance balances for every RECOUPMENT_APPLIED entry
    #    on this statement BEFORE the ledger entry is deleted. This
    #    mirrors the reprocess-reversal logic in
    #    royalty_processing_engine.py and is the gap that was causing
    #    advance balances to "stick" after a duplicate was deleted.
    for restore in summary["advance_restores"]:
        adv = db.query(AdvanceV2).filter(
            AdvanceV2.id == restore["advance_id"],
            AdvanceV2.org_id == org_id,
        ).first()
        if adv:
            adv.outstanding_balance_cents = (adv.outstanding_balance_cents or 0) + restore["restore_cents"]

    # 2. Unwind PayoutItem.paid_at for every payout linked (FK or
    #    legacy heuristic) to a PAYMENT ledger entry on this
    #    statement, and audit-log each affected payout under the
    #    single contract action PAYOUT_UNWOUND_BY_STATEMENT_DELETE
    #    (entity_type=PAYOUT_ITEM, entity_id=payout.id, details
    #    include statement_id, payee_id, amount_cents, batch_id,
    #    ledger_entry_id, linkage). Payments with no resolvable
    #    PayoutItem still get an audit row (entity_id=None) so the
    #    ledger-only history is preserved.
    from ..models.models import PayoutItem, PayoutBatch
    affected_payouts = []
    for pmt in summary["payments_unwound"]:
        po_id = pmt.get("payout_item_id")
        po = None
        if po_id:
            po = db.query(PayoutItem).filter(
                PayoutItem.id == po_id,
                PayoutItem.org_id == org_id,
            ).first()
        if po is not None:
            po.paid_at = None
            affected_payouts.append(po)
        log_action(
            db, org_id, current_user.id,
            "PAYOUT_UNWOUND_BY_STATEMENT_DELETE",
            "PAYOUT_ITEM" if po else "STATEMENT",
            po.id if po else statement_id,
            f"Payout item {po.id}" if po else stmt.source_name,
            details={
                "statement_id": statement_id,
                "ledger_entry_id": pmt["ledger_entry_id"],
                "payee_id": pmt["payee_id"],
                "amount_cents": pmt["amount_cents"],
                "payout_item_id": po.id if po else None,
                "batch_id": po.batch_id if po else None,
                "memo": pmt["memo"],
                "linkage": pmt.get("linkage", "none"),
            },
        )

    # 2b. Notify affected users that their paid payouts have been
    #     unwound. Recipients = the user who created each affected
    #     PayoutBatch (closest available proxy for "who created the
    #     payout") plus all org OWNERs/ADMINs. The user performing
    #     the delete is excluded so they don't ping themselves.
    if affected_payouts:
        try:
            _notify_payouts_unwound(
                db, org_id, stmt, current_user, affected_payouts,
            )
        except Exception as e:
            logger.warning(f"Failed to send payout-unwind notifications: {e}")

    # 3. Delete ActionItems pointing at this statement or its lines.
    #    Prefer the deterministic entity_id column; for legacy rows
    #    written before that column existed, fall back to anchored
    #    title patterns ("Statement #{id}:" / "Statement #{id} ")
    #    so #1 doesn't accidentally match #10/#100.
    from sqlalchemy import or_ as _or, and_ as _and
    line_ids = [r[0] for r in db.query(RoyaltyStatementLine.id).filter(
        RoyaltyStatementLine.statement_id == statement_id
    ).all()]
    db.query(ActionItem).filter(
        ActionItem.organization_id == org_id,
        ActionItem.entity_type == "STATEMENT",
        _or(
            ActionItem.entity_id == statement_id,
            _and(
                ActionItem.entity_id.is_(None),
                _or(
                    ActionItem.title.like(f"Statement #{statement_id}:%"),
                    ActionItem.title.like(f"Statement #{statement_id} %"),
                ),
            ),
        ),
    ).delete(synchronize_session=False)
    if line_ids:
        db.query(ActionItem).filter(
            ActionItem.organization_id == org_id,
            ActionItem.entity_type == "STATEMENT_LINE",
            ActionItem.entity_label.in_([str(i) for i in line_ids]),
        ).delete(synchronize_session=False)

    # 4. Delete ledger entries (this removes both PAYMENT and
    #    RECOUPMENT_APPLIED entries we just audited / restored from).
    db.query(RoyaltyLedgerEntry).filter(
        RoyaltyLedgerEntry.statement_id == statement_id
    ).delete(synchronize_session=False)

    db.query(RoyaltyProcessingRun).filter(
        RoyaltyProcessingRun.statement_id == statement_id
    ).delete(synchronize_session=False)

    db.query(RoyaltyStatementLine).filter(
        RoyaltyStatementLine.statement_id == statement_id
    ).delete(synchronize_session=False)

    tx_ids = [t.id for t in db.query(RoyaltyTransaction.id).filter(
        RoyaltyTransaction.statement_id == statement_id
    ).all()]
    if tx_ids:
        db.query(RoyaltyAllocation).filter(
            RoyaltyAllocation.transaction_id.in_(tx_ids)
        ).delete(synchronize_session=False)

    db.query(RoyaltyTransaction).filter(
        RoyaltyTransaction.statement_id == statement_id
    ).delete(synchronize_session=False)

    # 5. Remove the uploaded file from disk if it lives under the
    #    uploads directory. Path-traversal guard prevents removing
    #    arbitrary paths if file_path was somehow tampered with.
    if summary["file_will_be_deleted"]:
        try:
            os.remove(summary["file_path"])
        except OSError as e:
            logger.warning(f"Could not remove statement file {summary['file_path']}: {e}")

    log_action(
        db, org_id, current_user.id, "DELETE", "STATEMENT", stmt.id, stmt.source_name,
        details=summary,
    )

    db.delete(stmt)
    return summary


class BulkDeleteStatementsRequest(BaseModel):
    statement_ids: List[int]


@router.delete("/statements/{org_id}/{statement_id}", summary="Delete a royalty statement", description='Hard-deletes the statement and all linked transactions, allocations, advance applications, and payment links. Call `/delete-preview` first to confirm the blast radius.\n\n**Path parameters:** `org_id`, `statement_id`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** same shape as `/delete-preview` with `success: true` added.')
def delete_statement(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")
    summary = _perform_statement_delete(db, stmt, org_id, current_user)
    db.commit()
    return {"detail": "Statement deleted", "summary": summary}


def _aggregate_delete_summaries(summaries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Combine per-statement delete summaries into a single dict the
    bulk-delete confirmation dialog can render."""
    adv_map: Dict[int, Dict[str, Any]] = {}
    for s in summaries:
        for a in s.get("advance_restores", []):
            key = a["advance_id"]
            if key not in adv_map:
                adv_map[key] = {
                    "advance_id": key,
                    "advance_name": a.get("advance_name"),
                    "restore_cents": 0,
                }
            adv_map[key]["restore_cents"] += int(a.get("restore_cents") or 0)
    advance_restores = sorted(
        adv_map.values(), key=lambda x: -x["restore_cents"]
    )
    payments: List[Dict[str, Any]] = []
    for s in summaries:
        payments.extend(s.get("payments_unwound", []) or [])
    return {
        "statement_count": len(summaries),
        "transaction_count": sum(int(s.get("transaction_count") or 0) for s in summaries),
        "line_count": sum(int(s.get("line_count") or 0) for s in summaries),
        "allocation_count": sum(int(s.get("allocation_count") or 0) for s in summaries),
        "processing_run_count": sum(int(s.get("processing_run_count") or 0) for s in summaries),
        "ledger_entry_count": sum(int(s.get("ledger_entry_count") or 0) for s in summaries),
        "total_revenue_cents": sum(int(s.get("total_revenue_cents") or 0) for s in summaries),
        "action_items_to_remove": sum(int(s.get("action_items_to_remove") or 0) for s in summaries),
        "files_to_delete": sum(1 for s in summaries if s.get("file_will_be_deleted")),
        "advance_restores": advance_restores,
        "payments_unwound": payments,
        "statements": [
            {
                "statement_id": s["statement_id"],
                "source_name": s.get("source_name"),
                "transaction_count": s.get("transaction_count", 0),
                "total_revenue_cents": s.get("total_revenue_cents", 0),
            }
            for s in summaries
        ],
    }


@router.post("/statements/{org_id}/bulk-delete-preview", summary="Combined non-mutating preview for deleting many statements at once", description='Combined non-mutating preview for deleting many statements at once. Returns the same shape as the single-statement preview, summed.\n\n**Path parameter:** `org_id`.\n**Body:** `{ statement_ids: int[] }`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ statements: int, transactions: int, allocations: int, advances_restored_cents: int, payments_unwound: int, action_items_cleared: int }`.')
def bulk_delete_statement_preview(
    org_id: int,
    body: BulkDeleteStatementsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Combined non-mutating preview for deleting many statements at
    once. Returns the same shape as the single-statement preview but
    with totals summed and per-advance restores aggregated, so the
    bulk confirmation dialog can show real numbers."""
    verify_org_access(current_user, org_id, db)
    ids = list(dict.fromkeys(body.statement_ids))
    if not ids:
        raise HTTPException(status_code=400, detail="No statement IDs provided")
    stmts = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.organization_id == org_id,
        RoyaltyStatement.id.in_(ids),
    ).all()
    found = {s.id for s in stmts}
    missing = [i for i in ids if i not in found]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Statements not found in this organization: {missing}",
        )
    stmts.sort(key=lambda s: ids.index(s.id))
    summaries = [_build_statement_delete_summary(db, s) for s in stmts]
    return _aggregate_delete_summaries(summaries)


@router.post("/statements/{org_id}/bulk-delete", summary="Bulk Delete Statements", description='Deletes several statements in one transaction, running the same exhaustive cleanup (advance restore, payment unwind, action-item clearance).\n\n**Path parameter:** `org_id`.\n**Body:** `{ statement_ids: int[] }`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ deleted: int, transactions: int, allocations: int, advances_restored_cents: int, payments_unwound: int, action_items_cleared: int }`.')
def bulk_delete_statements(
    org_id: int,
    body: BulkDeleteStatementsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete several statements in one transaction, running the same
    exhaustive cleanup (advance restore, payment unwind, action item
    removal, file removal, audit log) per statement that the
    single-statement endpoint runs. Either all deletions commit or
    none do."""
    verify_org_access(current_user, org_id, db)
    ids = list(dict.fromkeys(body.statement_ids))
    if not ids:
        raise HTTPException(status_code=400, detail="No statement IDs provided")
    stmts = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.organization_id == org_id,
        RoyaltyStatement.id.in_(ids),
    ).all()
    found = {s.id for s in stmts}
    missing = [i for i in ids if i not in found]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Statements not found in this organization: {missing}",
        )
    stmts.sort(key=lambda s: ids.index(s.id))
    summaries: List[Dict[str, Any]] = []
    try:
        for stmt in stmts:
            summaries.append(_perform_statement_delete(db, stmt, org_id, current_user))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {
        "detail": f"Deleted {len(summaries)} statements",
        "deleted_count": len(summaries),
        "summary": _aggregate_delete_summaries(summaries),
    }


@router.get(
    "/statements/{org_id}/{statement_id}/transactions",
    summary='List Transactions',
    description='Returns the per-track RoyaltyTransaction rows that were created from a statement (the v1 transaction model — see royalty-processing for the v2 statement-line model). Supports the transactions table on the statement detail page.\n\n**Path parameters:** `org_id`, `statement_id`.\n**Query:** `q` (search), `matched` (`true|false|null`), `limit` (default 100), `skip`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ total, limit, skip, transactions: [{id, track_title, artist, isrc, period, territory, amount_cents, currency, song_id, song_title, matched_at}] }`.',
)
def list_transactions(
    org_id: int,
    statement_id: int,
    match_status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    query = db.query(RoyaltyTransaction).filter(RoyaltyTransaction.statement_id == statement_id)
    if match_status:
        query = query.filter(RoyaltyTransaction.match_status == match_status)
    total = query.count()
    txs = query.order_by(RoyaltyTransaction.id).offset(skip).limit(limit).all()

    results = []
    for tx in txs:
        song_title = None
        song_artist = None
        if tx.song_id:
            song = db.query(Song).filter(Song.id == tx.song_id).first()
            if song:
                song_title = song.title
                song_artist = song.primary_artist
        results.append({
            "id": tx.id,
            "original_track_title": tx.original_track_title,
            "original_artist": tx.original_artist,
            "original_isrc": tx.original_isrc,
            "original_upc": tx.original_upc,
            "song_id": tx.song_id,
            "matched_song_title": song_title,
            "matched_song_artist": song_artist,
            "match_status": tx.match_status,
            "match_confidence": tx.match_confidence,
            "revenue_cents": tx.revenue_cents,
            "revenue_dollars": tx.revenue_cents / 100.0,
            "quantity": tx.quantity,
            "territory": tx.territory,
            "platform": tx.platform,
            "revenue_type": tx.revenue_type,
        })

    return {"total": total, "skip": skip, "limit": limit, "transactions": results}


@router.post(
    "/statements/{org_id}/{statement_id}/match/{transaction_id}",
    summary='Manual Match',
    description='Manually attaches a single RoyaltyTransaction to a song so it will participate in royalty calculation. Overrides any prior auto-match.\n\n**Path parameters:** `org_id`, `statement_id`, `transaction_id`.\n**Body:** `{ song_id: int }`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ song_id, song_title, detail }`.',
)
def manual_match(
    org_id: int,
    statement_id: int,
    transaction_id: int,
    body: ManualMatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    tx = db.query(RoyaltyTransaction).filter(
        RoyaltyTransaction.id == transaction_id,
        RoyaltyTransaction.statement_id == statement_id,
        RoyaltyTransaction.organization_id == org_id,
    ).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")

    song = db.query(Song).filter(Song.id == body.song_id, Song.organization_id == org_id).first()
    if not song:
        raise HTTPException(status_code=404, detail="Song not found in this organization")

    was_unmatched = tx.match_status == "UNMATCHED"
    tx.song_id = song.id
    tx.match_status = "MANUAL"
    tx.match_confidence = 1.0

    stmt = db.query(RoyaltyStatement).filter(RoyaltyStatement.id == statement_id).first()
    if stmt and was_unmatched:
        stmt.matched_transactions = (stmt.matched_transactions or 0) + 1
        stmt.unmatched_transactions = max((stmt.unmatched_transactions or 0) - 1, 0)
        if stmt.unmatched_transactions == 0:
            stmt.status = "PROCESSED"

    db.commit()
    return {"detail": "Transaction matched", "song_id": song.id, "song_title": song.title}


@router.post(
    "/statements/{org_id}/{statement_id}/rematch",
    summary='Rematch Transactions',
    description='Re-runs the auto-matcher across every unmatched RoyaltyTransaction on a statement (useful after editing the catalog or fixing ISRCs). Confirmed/manual matches are preserved.\n\n**Path parameters:** `org_id`, `statement_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ status, newly_matched, remaining_unmatched }`.',
)
def rematch_transactions(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    unmatched = db.query(RoyaltyTransaction).filter(
        RoyaltyTransaction.statement_id == statement_id,
        RoyaltyTransaction.match_status == "UNMATCHED",
    ).all()

    org_songs = db.query(Song).filter(Song.organization_id == org_id).all()
    newly_matched = 0

    for tx in unmatched:
        song_id, confidence, status = match_transaction_to_song(tx, org_songs)
        if status == "MATCHED":
            tx.song_id = song_id
            tx.match_confidence = confidence
            tx.match_status = "MATCHED"
            newly_matched += 1

    stmt.matched_transactions = (stmt.matched_transactions or 0) + newly_matched
    stmt.unmatched_transactions = max((stmt.unmatched_transactions or 0) - newly_matched, 0)
    if stmt.unmatched_transactions == 0:
        stmt.status = "PROCESSED"
    elif newly_matched > 0:
        stmt.status = "PARTIALLY_MATCHED"

    db.commit()
    return {
        "newly_matched": newly_matched,
        "remaining_unmatched": stmt.unmatched_transactions,
        "status": stmt.status,
    }


@router.post("/calculate/{org_id}/{statement_id}", summary="Calculate royalties for a statement", description='Runs the royalty engine: matches transactions to assets, applies rights splits and contract terms, and produces creator allocations + recoupment applications.\n\n**Path parameters:** `org_id`, `statement_id`.\n**Body:** `{ recalculate?: bool }` — set true to wipe and recompute.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ statement_id, matched, unmatched, allocations_created, gross_cents, net_to_creators_cents }`.')
def calculate_royalties(
    org_id: int,
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    stmt = db.query(RoyaltyStatement).filter(
        RoyaltyStatement.id == statement_id,
        RoyaltyStatement.organization_id == org_id,
    ).first()
    if not stmt:
        raise HTTPException(status_code=404, detail="Statement not found")

    db.query(RoyaltyAllocation).filter(
        RoyaltyAllocation.transaction_id.in_(
            db.query(RoyaltyTransaction.id).filter(RoyaltyTransaction.statement_id == statement_id)
        )
    ).delete(synchronize_session=False)

    matched_txs = db.query(RoyaltyTransaction).filter(
        RoyaltyTransaction.statement_id == statement_id,
        RoyaltyTransaction.match_status.in_(["MATCHED", "MANUAL"]),
        RoyaltyTransaction.song_id.isnot(None),
    ).all()

    allocations_created = 0
    total_allocated = 0
    total_recouped = 0

    for tx in matched_txs:
        contract_assets = db.query(ContractAsset).filter(
            ContractAsset.asset_type == "SONG",
            ContractAsset.asset_id == tx.song_id,
        ).all()

        for ca in contract_assets:
            contract = db.query(Contract).filter(
                Contract.id == ca.contract_id,
                Contract.organization_id == org_id,
            ).first()
            if not contract:
                continue

            splits = db.query(RightsSplit).filter(
                RightsSplit.contract_asset_id == ca.id
            ).all()

            for split in splits:
                share_cents = int(round(tx.revenue_cents * (split.share_percentage / 100.0)))
                recouped_cents = 0
                is_recoupable = False

                if contract.advance_amount and contract.advance_amount > 0:
                    advance_cents = int(round(contract.advance_amount * 100))
                    recouped_so_far_cents = int(round((contract.advance_recouped or 0) * 100))
                    remaining = advance_cents - recouped_so_far_cents

                    if remaining > 0:
                        is_recoupable = True
                        recoup_amount = min(share_cents, remaining)
                        recouped_cents = recoup_amount
                        contract.advance_recouped = (contract.advance_recouped or 0) + (recoup_amount / 100.0)

                alloc = RoyaltyAllocation(
                    transaction_id=tx.id,
                    organization_id=org_id,
                    contract_id=contract.id,
                    rights_holder_id=split.rights_holder_id,
                    rights_type=split.rights_type,
                    share_percentage=split.share_percentage,
                    allocated_cents=share_cents,
                    is_recoupable=is_recoupable,
                    recouped_cents=recouped_cents,
                )
                db.add(alloc)
                allocations_created += 1
                total_allocated += share_cents
                total_recouped += recouped_cents

    db.commit()

    return {
        "statement_id": statement_id,
        "allocations_created": allocations_created,
        "total_allocated_cents": total_allocated,
        "total_allocated_dollars": total_allocated / 100.0,
        "total_recouped_cents": total_recouped,
        "total_recouped_dollars": total_recouped / 100.0,
    }


@router.get(
    "/allocations/{org_id}",
    summary='List Allocations',
    description='Returns the RightsSplit-driven allocations computed from calculated statements: who owes how much to whom and from which underlying transaction. Drives the allocations explorer and feeds the payments workflow.\n\n**Path parameter:** `org_id`.\n**Query:** `creator_id`, `contract_id`, `song_id`, `statement_id`, `start_date`, `end_date`, `limit` (default 100), `skip`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ total, limit, skip, allocations: [{id, rights_holder_id, rights_holder_name, song_id, song_title, statement_id, contract_id, amount_cents, currency, share_pct, created_at}] }`.',
)
def list_allocations(
    org_id: int,
    contract_id: Optional[int] = None,
    rights_holder_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(RoyaltyAllocation).filter(RoyaltyAllocation.organization_id == org_id)

    if contract_id:
        query = query.filter(RoyaltyAllocation.contract_id == contract_id)
    if rights_holder_id:
        query = query.filter(RoyaltyAllocation.rights_holder_id == rights_holder_id)
    if start_date:
        try:
            sd = date.fromisoformat(start_date)
            query = query.filter(RoyaltyAllocation.created_at >= datetime.combine(sd, datetime.min.time()))
        except ValueError:
            pass
    if end_date:
        try:
            ed = date.fromisoformat(end_date)
            query = query.filter(RoyaltyAllocation.created_at <= datetime.combine(ed, datetime.max.time()))
        except ValueError:
            pass

    total = query.count()
    allocs = query.order_by(desc(RoyaltyAllocation.created_at)).offset(skip).limit(limit).all()

    results = []
    for a in allocs:
        holder = db.query(Creator).filter(Creator.id == a.rights_holder_id).first()
        contract = db.query(Contract).filter(Contract.id == a.contract_id).first() if a.contract_id else None
        results.append({
            "id": a.id,
            "transaction_id": a.transaction_id,
            "contract_id": a.contract_id,
            "contract_title": contract.title if contract else None,
            "rights_holder_id": a.rights_holder_id,
            "rights_holder_name": holder.display_name if holder else None,
            "rights_type": a.rights_type,
            "share_percentage": a.share_percentage,
            "allocated_cents": a.allocated_cents,
            "allocated_dollars": a.allocated_cents / 100.0,
            "is_recoupable": a.is_recoupable,
            "recouped_cents": a.recouped_cents,
            "recouped_dollars": a.recouped_cents / 100.0,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        })

    return {"total": total, "skip": skip, "limit": limit, "allocations": results}


@router.get("/dashboard/{org_id}", summary="Royalties dashboard summary", description='Aggregate financial overview: gross revenue, net to creators, fees, advances, and outstanding balances.\n\n**Path parameter:** `org_id`.\n**Query:** `period_start`, `period_end`, `currency`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ gross_cents, net_to_creators_cents, fees_cents, advances_outstanding_cents, paid_cents, balance_cents, by_source: [...] }`.')
def royalties_dashboard(
    org_id: int,
    creator_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    stmt_filter = [RoyaltyStatement.organization_id == org_id]
    if creator_id:
        stmt_filter.append(RoyaltyStatement.creator_id == creator_id)

    total_revenue = db.query(func.coalesce(func.sum(RoyaltyStatement.total_revenue_cents), 0)).filter(
        *stmt_filter
    ).scalar()

    total_allocated = db.query(func.coalesce(func.sum(RoyaltyAllocation.allocated_cents), 0)).filter(
        RoyaltyAllocation.organization_id == org_id
    ).scalar()

    total_unallocated = total_revenue - total_allocated

    matched_tracks_query = db.query(
        Song.id, Song.title, Song.primary_artist,
        func.sum(RoyaltyTransaction.revenue_cents).label("total_cents"),
        func.sum(RoyaltyTransaction.quantity).label("total_quantity"),
    ).join(
        RoyaltyTransaction, RoyaltyTransaction.song_id == Song.id
    ).filter(
        RoyaltyTransaction.organization_id == org_id,
    )
    if creator_id:
        matched_tracks_query = matched_tracks_query.join(
            RoyaltyStatement, RoyaltyStatement.id == RoyaltyTransaction.statement_id
        ).filter(RoyaltyStatement.creator_id == creator_id)
    matched_tracks = matched_tracks_query.group_by(
        Song.id, Song.title, Song.primary_artist
    ).order_by(desc("total_cents")).limit(10).all()

    unmatched_tracks_query = db.query(
        RoyaltyTransaction.original_track_title,
        RoyaltyTransaction.original_artist,
        func.sum(RoyaltyTransaction.revenue_cents).label("total_cents"),
        func.sum(RoyaltyTransaction.quantity).label("total_quantity"),
    ).filter(
        RoyaltyTransaction.organization_id == org_id,
        RoyaltyTransaction.song_id.is_(None),
        RoyaltyTransaction.original_track_title.isnot(None),
    )
    if creator_id:
        unmatched_tracks_query = unmatched_tracks_query.join(
            RoyaltyStatement, RoyaltyStatement.id == RoyaltyTransaction.statement_id
        ).filter(RoyaltyStatement.creator_id == creator_id)
    unmatched_tracks = unmatched_tracks_query.group_by(
        RoyaltyTransaction.original_track_title,
        RoyaltyTransaction.original_artist,
    ).order_by(desc("total_cents")).limit(10).all()

    all_tracks = []
    for t in matched_tracks:
        all_tracks.append({
            "song_id": t.id,
            "title": t.title,
            "artist": t.primary_artist,
            "total_revenue_cents": t.total_cents,
            "total_revenue_dollars": t.total_cents / 100.0,
            "total_quantity": t.total_quantity or 0,
        })
    for t in unmatched_tracks:
        if t.total_cents and t.total_cents > 0:
            all_tracks.append({
                "song_id": None,
                "title": t.original_track_title,
                "artist": t.original_artist,
                "total_revenue_cents": t.total_cents,
                "total_revenue_dollars": t.total_cents / 100.0,
                "total_quantity": t.total_quantity or 0,
                "unmatched": True,
            })
    all_tracks.sort(key=lambda x: x.get("total_revenue_cents", 0) or 0, reverse=True)
    top_tracks = all_tracks[:10]

    revenue_by_source = db.query(
        RoyaltyStatement.source_name,
        func.sum(RoyaltyStatement.total_revenue_cents).label("total_cents"),
    ).filter(
        *stmt_filter
    ).group_by(RoyaltyStatement.source_name).all()

    revenue_by_period = db.query(
        RoyaltyStatement.period_start,
        RoyaltyStatement.period_end,
        RoyaltyStatement.source_name,
        RoyaltyStatement.total_revenue_cents,
    ).filter(
        *stmt_filter
    ).order_by(RoyaltyStatement.period_start).all()

    recent_stmts = db.query(
        RoyaltyStatement.id,
        RoyaltyStatement.source_name,
        RoyaltyStatement.period_start,
        RoyaltyStatement.period_end,
        RoyaltyStatement.currency,
        RoyaltyStatement.total_revenue_cents,
        RoyaltyStatement.status,
        RoyaltyStatement.created_at,
    ).filter(
        *stmt_filter
    ).order_by(RoyaltyStatement.created_at.desc()).limit(20).all()

    contract_filter = [Contract.organization_id == org_id, Contract.advance_amount > 0]
    if creator_id:
        contract_filter.append(Contract.creator_id == creator_id)
    contracts_with_advances = db.query(Contract).filter(*contract_filter).all()

    recoupment_status = []
    for c in contracts_with_advances:
        advance = c.advance_amount or 0
        recouped = c.advance_recouped or 0
        recoupment_status.append({
            "contract_id": c.id,
            "contract_title": c.title,
            "advance_amount": advance,
            "advance_recouped": recouped,
            "remaining": max(advance - recouped, 0),
            "percentage_recouped": round((recouped / advance) * 100, 2) if advance > 0 else 0,
        })

    return {
        "total_revenue_cents": total_revenue,
        "total_revenue_dollars": total_revenue / 100.0,
        "total_allocated_cents": total_allocated,
        "total_allocated_dollars": total_allocated / 100.0,
        "total_unallocated_cents": total_unallocated,
        "total_unallocated_dollars": total_unallocated / 100.0,
        "top_earning_tracks": top_tracks,
        "revenue_by_source": [
            {"source": r.source_name, "total_cents": r.total_cents, "total_dollars": r.total_cents / 100.0}
            for r in revenue_by_source
        ],
        "revenue_by_period": [
            {
                "period_start": r.period_start.isoformat() if r.period_start else None,
                "period_end": r.period_end.isoformat() if r.period_end else None,
                "source": r.source_name,
                "total_cents": r.total_revenue_cents,
                "total_dollars": r.total_revenue_cents / 100.0,
            }
            for r in revenue_by_period
        ],
        "recoupment_status": recoupment_status,
        "recent_statements": [
            {
                "id": s.id,
                "source": s.source_name,
                "period_start": s.period_start.isoformat() if s.period_start else None,
                "period_end": s.period_end.isoformat() if s.period_end else None,
                "currency": s.currency or "USD",
                "total_cents": s.total_revenue_cents,
                "total_dollars": (s.total_revenue_cents or 0) / 100.0,
                "status": s.status,
            }
            for s in recent_stmts
        ],
    }


@router.get(
    "/earnings/{org_id}/by-holder",
    summary='Earnings By Holder',
    description="Aggregates allocation totals grouped by rights-holder (creator or company). One row per holder with their share of the org's total earnings over the period.\n\n**Path parameter:** `org_id`.\n**Query:** `start_date`, `end_date`, `currency`, `min_amount_cents`, `limit`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ earnings: [{holder_id, holder_name, holder_type, amount_cents, currency, allocation_count, pct_of_total}] }` sorted by `amount_cents desc`.",
)
def earnings_by_holder(
    org_id: int,
    creator_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    alloc_query = db.query(
        Creator.id, Creator.display_name,
        func.sum(RoyaltyAllocation.allocated_cents).label("total_cents"),
        func.sum(RoyaltyAllocation.recouped_cents).label("total_recouped"),
    ).join(
        RoyaltyAllocation, RoyaltyAllocation.rights_holder_id == Creator.id
    ).filter(
        RoyaltyAllocation.organization_id == org_id,
    )
    if creator_id is not None:
        alloc_query = alloc_query.join(
            RoyaltyTransaction, RoyaltyTransaction.id == RoyaltyAllocation.transaction_id
        ).join(
            RoyaltyStatement, RoyaltyStatement.id == RoyaltyTransaction.statement_id
        ).filter(RoyaltyStatement.creator_id == creator_id)
    alloc_results = alloc_query.group_by(
        Creator.id, Creator.display_name
    ).order_by(desc("total_cents")).all()

    alloc_map = {}
    for r in alloc_results:
        alloc_map[r.id] = {
            "allocated_cents": r.total_cents or 0,
            "recouped_cents": r.total_recouped or 0,
        }

    stmt_filters = [RoyaltyStatement.organization_id == org_id]
    if creator_id is not None:
        stmt_filters.append(RoyaltyStatement.creator_id == creator_id)
    stmt_results = db.query(
        Creator.id, Creator.display_name,
        func.sum(RoyaltyStatement.total_revenue_cents).label("total_revenue"),
        func.count(RoyaltyStatement.id).label("stmt_count"),
    ).join(
        RoyaltyStatement, RoyaltyStatement.creator_id == Creator.id
    ).filter(
        *stmt_filters
    ).group_by(Creator.id, Creator.display_name).all()

    holders = {}
    for r in stmt_results:
        alloc = alloc_map.get(r.id, {"allocated_cents": 0, "recouped_cents": 0})
        total_rev = r.total_revenue or 0
        holders[r.id] = {
            "rights_holder_id": r.id,
            "rights_holder_name": r.display_name,
            "total_revenue_cents": total_rev,
            "total_revenue_dollars": total_rev / 100.0,
            "total_allocated_cents": alloc["allocated_cents"],
            "total_allocated_dollars": alloc["allocated_cents"] / 100.0,
            "total_recouped_cents": alloc["recouped_cents"],
            "total_recouped_dollars": alloc["recouped_cents"] / 100.0,
            "net_earned_cents": total_rev - alloc["recouped_cents"],
            "net_earned_dollars": (total_rev - alloc["recouped_cents"]) / 100.0,
            "statement_count": r.stmt_count,
        }

    for r in alloc_results:
        if r.id not in holders:
            holders[r.id] = {
                "rights_holder_id": r.id,
                "rights_holder_name": r.display_name,
                "total_revenue_cents": r.total_cents or 0,
                "total_revenue_dollars": (r.total_cents or 0) / 100.0,
                "total_allocated_cents": r.total_cents or 0,
                "total_allocated_dollars": (r.total_cents or 0) / 100.0,
                "total_recouped_cents": r.total_recouped or 0,
                "total_recouped_dollars": (r.total_recouped or 0) / 100.0,
                "net_earned_cents": (r.total_cents or 0) - (r.total_recouped or 0),
                "net_earned_dollars": ((r.total_cents or 0) - (r.total_recouped or 0)) / 100.0,
                "statement_count": 0,
            }

    # New-pipeline statement lines are attributed to the parent statement's
    # creator. RoyaltyStatement.total_revenue_cents (used above for
    # total_revenue) already includes these line dollars, so the holder's
    # revenue-basis totals already reflect them. We additionally surface
    # any holder that exists only via new-pipeline statements (no legacy
    # allocations and no statement total yet aggregated above) so they
    # aren't dropped from the listing.
    line_filters = [RoyaltyStatementLine.org_id == org_id]
    if creator_id is not None:
        line_filters.append(RoyaltyStatement.creator_id == creator_id)
    line_holder_results = db.query(
        Creator.id, Creator.display_name,
        func.sum(RoyaltyStatementLine.net_amount_statement_currency).label("total_dollars"),
    ).join(
        RoyaltyStatement, RoyaltyStatement.creator_id == Creator.id
    ).join(
        RoyaltyStatementLine, RoyaltyStatementLine.statement_id == RoyaltyStatement.id
    ).filter(*line_filters).group_by(Creator.id, Creator.display_name).all()

    for r in line_holder_results:
        if r.id in holders:
            continue
        cents = int(round((r.total_dollars or 0) * 100))
        if cents <= 0:
            continue
        holders[r.id] = {
            "rights_holder_id": r.id,
            "rights_holder_name": r.display_name,
            "total_revenue_cents": cents,
            "total_revenue_dollars": cents / 100.0,
            "total_allocated_cents": 0,
            "total_allocated_dollars": 0.0,
            "total_recouped_cents": 0,
            "total_recouped_dollars": 0.0,
            "net_earned_cents": cents,
            "net_earned_dollars": cents / 100.0,
            "statement_count": 0,
        }

    earnings = sorted(holders.values(), key=lambda x: x.get("total_revenue_cents", 0), reverse=True)
    return {"earnings": earnings}


@router.get(
    "/earnings/{org_id}/by-contract",
    summary='Earnings By Contract',
    description='Aggregates allocation totals grouped by Contract — useful for evaluating whether a deal is recouping or how a publishing agreement is performing.\n\n**Path parameter:** `org_id`.\n**Query:** `start_date`, `end_date`, `currency`, `holder_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ earnings: [{contract_id, contract_name, amount_cents, currency, allocation_count}] }`.',
)
def earnings_by_contract(
    org_id: int,
    creator_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    filters = [RoyaltyAllocation.organization_id == org_id]
    if creator_id is not None:
        filters.append(Contract.creator_id == creator_id)
    results = db.query(
        Contract.id, Contract.title, Contract.advance_amount, Contract.advance_recouped,
        func.sum(RoyaltyAllocation.allocated_cents).label("total_cents"),
        func.sum(RoyaltyAllocation.recouped_cents).label("total_recouped"),
    ).join(
        RoyaltyAllocation, RoyaltyAllocation.contract_id == Contract.id
    ).filter(
        *filters
    ).group_by(Contract.id, Contract.title, Contract.advance_amount, Contract.advance_recouped).order_by(desc("total_cents")).all()

    contracts_map = {}
    for r in results:
        contracts_map[r.id] = {
            "contract_id": r.id,
            "contract_title": r.title,
            "advance_amount": r.advance_amount or 0,
            "advance_recouped": r.advance_recouped or 0,
            "remaining_advance": max((r.advance_amount or 0) - (r.advance_recouped or 0), 0),
            "recoupment_percentage": round(((r.advance_recouped or 0) / r.advance_amount) * 100, 2) if r.advance_amount and r.advance_amount > 0 else 0,
            "total_allocated_cents": r.total_cents or 0,
            "total_allocated_dollars": (r.total_cents or 0) / 100.0,
            "total_recouped_cents": r.total_recouped or 0,
            "net_earned_cents": (r.total_cents or 0) - (r.total_recouped or 0),
            "net_earned_dollars": ((r.total_cents or 0) - (r.total_recouped or 0)) / 100.0,
        }

    # Attribute new-pipeline statement lines to a contract only when the
    # parent statement's creator has exactly one contract — the only
    # deterministic 1:1 mapping available. New-pipeline statements don't
    # carry a contract_id and don't produce per-contract allocations, so
    # for creators with multiple contracts we leave lines unattributed at
    # the contract level (mirroring how legacy unallocated transactions
    # don't appear under contracts).
    line_filters = [RoyaltyStatementLine.org_id == org_id]
    if creator_id is not None:
        line_filters.append(RoyaltyStatement.creator_id == creator_id)
    line_by_creator = db.query(
        RoyaltyStatement.creator_id,
        func.sum(RoyaltyStatementLine.net_amount_statement_currency).label("total_dollars"),
    ).join(
        RoyaltyStatementLine, RoyaltyStatementLine.statement_id == RoyaltyStatement.id
    ).filter(*line_filters).group_by(RoyaltyStatement.creator_id).all()

    for r in line_by_creator:
        if r.creator_id is None:
            continue
        cents = int(round((r.total_dollars or 0) * 100))
        if cents <= 0:
            continue
        creator_contracts = db.query(Contract).filter(
            Contract.organization_id == org_id,
            Contract.creator_id == r.creator_id,
        ).all()
        if len(creator_contracts) != 1:
            continue
        contract = creator_contracts[0]
        if contract.id in contracts_map:
            entry = contracts_map[contract.id]
            entry["total_allocated_cents"] = (entry.get("total_allocated_cents") or 0) + cents
            entry["total_allocated_dollars"] = entry["total_allocated_cents"] / 100.0
            entry["net_earned_cents"] = entry["total_allocated_cents"] - (entry.get("total_recouped_cents") or 0)
            entry["net_earned_dollars"] = entry["net_earned_cents"] / 100.0
        else:
            contracts_map[contract.id] = {
                "contract_id": contract.id,
                "contract_title": contract.title,
                "advance_amount": contract.advance_amount or 0,
                "advance_recouped": contract.advance_recouped or 0,
                "remaining_advance": max((contract.advance_amount or 0) - (contract.advance_recouped or 0), 0),
                "recoupment_percentage": round(((contract.advance_recouped or 0) / contract.advance_amount) * 100, 2) if contract.advance_amount and contract.advance_amount > 0 else 0,
                "total_allocated_cents": cents,
                "total_allocated_dollars": cents / 100.0,
                "total_recouped_cents": 0,
                "net_earned_cents": cents,
                "net_earned_dollars": cents / 100.0,
            }

    earnings = sorted(
        contracts_map.values(),
        key=lambda x: x.get("total_allocated_cents", 0) or 0,
        reverse=True,
    )
    return {"earnings": earnings}


@router.get(
    "/earnings/{org_id}/by-track",
    summary='Earnings By Track',
    description='Aggregates allocation totals grouped by Song. Powers the "top tracks" leaderboard.\n\n**Path parameter:** `org_id`.\n**Query:** `start_date`, `end_date`, `currency`, `creator_id`, `contract_id`, `limit` (default 50).\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ earnings: [{song_id, song_title, artist, amount_cents, currency, allocation_count}] }`.',
)
def earnings_by_track(
    org_id: int,
    creator_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    matched_query = db.query(
        Song.id, Song.title, Song.primary_artist, Song.isrc,
        func.sum(RoyaltyTransaction.revenue_cents).label("total_revenue_cents"),
        func.sum(RoyaltyTransaction.quantity).label("total_quantity"),
    ).join(
        RoyaltyTransaction, RoyaltyTransaction.song_id == Song.id
    ).filter(
        RoyaltyTransaction.organization_id == org_id,
    )
    if creator_id is not None:
        matched_query = matched_query.join(
            RoyaltyStatement, RoyaltyStatement.id == RoyaltyTransaction.statement_id
        ).filter(RoyaltyStatement.creator_id == creator_id)
    matched_results = matched_query.group_by(
        Song.id, Song.title, Song.primary_artist, Song.isrc
    ).order_by(desc("total_revenue_cents")).all()

    earnings = [
        {
            "song_id": r.id,
            "title": r.title,
            "artist": r.primary_artist,
            "isrc": r.isrc,
            "total_revenue_cents": r.total_revenue_cents,
            "total_revenue_dollars": r.total_revenue_cents / 100.0,
            "total_quantity": r.total_quantity,
        }
        for r in matched_results
    ]

    unmatched_query = db.query(
        RoyaltyTransaction.original_track_title,
        RoyaltyTransaction.original_artist,
        func.sum(RoyaltyTransaction.revenue_cents).label("total_revenue_cents"),
        func.sum(RoyaltyTransaction.quantity).label("total_quantity"),
    ).filter(
        RoyaltyTransaction.organization_id == org_id,
        RoyaltyTransaction.song_id.is_(None),
        RoyaltyTransaction.original_track_title.isnot(None),
    )
    if creator_id is not None:
        unmatched_query = unmatched_query.join(
            RoyaltyStatement, RoyaltyStatement.id == RoyaltyTransaction.statement_id
        ).filter(RoyaltyStatement.creator_id == creator_id)
    unmatched_results = unmatched_query.group_by(
        RoyaltyTransaction.original_track_title,
        RoyaltyTransaction.original_artist,
    ).order_by(desc("total_revenue_cents")).limit(100).all()

    for r in unmatched_results:
        if r.total_revenue_cents and r.total_revenue_cents > 0:
            earnings.append({
                "song_id": None,
                "title": r.original_track_title,
                "artist": r.original_artist,
                "isrc": None,
                "total_revenue_cents": r.total_revenue_cents,
                "total_revenue_dollars": r.total_revenue_cents / 100.0,
                "total_quantity": r.total_quantity,
                "unmatched": True,
            })

    # Aggregate from new-pipeline statement lines and merge with legacy results
    line_matched_q = db.query(
        Song.id, Song.title, Song.primary_artist, Song.isrc,
        func.sum(RoyaltyStatementLine.net_amount_statement_currency).label("total_dollars"),
        func.sum(RoyaltyStatementLine.unit_count).label("total_quantity"),
    ).join(
        RoyaltyStatementLine, RoyaltyStatementLine.matched_song_id == Song.id
    ).filter(
        RoyaltyStatementLine.org_id == org_id,
    )
    if creator_id is not None:
        line_matched_q = line_matched_q.join(
            RoyaltyStatement, RoyaltyStatement.id == RoyaltyStatementLine.statement_id
        ).filter(RoyaltyStatement.creator_id == creator_id)
    line_matched = line_matched_q.group_by(
        Song.id, Song.title, Song.primary_artist, Song.isrc
    ).all()

    by_song = {e["song_id"]: e for e in earnings if e.get("song_id") is not None}
    for r in line_matched:
        cents = int(round((r.total_dollars or 0) * 100))
        qty = r.total_quantity or 0
        if r.id in by_song:
            existing = by_song[r.id]
            existing["total_revenue_cents"] = (existing.get("total_revenue_cents") or 0) + cents
            existing["total_revenue_dollars"] = existing["total_revenue_cents"] / 100.0
            existing["total_quantity"] = (existing.get("total_quantity") or 0) + qty
        else:
            entry = {
                "song_id": r.id,
                "title": r.title,
                "artist": r.primary_artist,
                "isrc": r.isrc,
                "total_revenue_cents": cents,
                "total_revenue_dollars": cents / 100.0,
                "total_quantity": qty,
            }
            earnings.append(entry)
            by_song[r.id] = entry

    line_unmatched_q = db.query(
        RoyaltyStatementLine.track_title_raw,
        RoyaltyStatementLine.artist_name_raw,
        func.sum(RoyaltyStatementLine.net_amount_statement_currency).label("total_dollars"),
        func.sum(RoyaltyStatementLine.unit_count).label("total_quantity"),
    ).filter(
        RoyaltyStatementLine.org_id == org_id,
        RoyaltyStatementLine.matched_song_id.is_(None),
        RoyaltyStatementLine.track_title_raw.isnot(None),
    )
    if creator_id is not None:
        line_unmatched_q = line_unmatched_q.join(
            RoyaltyStatement, RoyaltyStatement.id == RoyaltyStatementLine.statement_id
        ).filter(RoyaltyStatement.creator_id == creator_id)
    line_unmatched = line_unmatched_q.group_by(
        RoyaltyStatementLine.track_title_raw,
        RoyaltyStatementLine.artist_name_raw,
    ).all()

    by_unmatched = {
        (e.get("title"), e.get("artist")): e
        for e in earnings if e.get("song_id") is None and e.get("unmatched")
    }
    for r in line_unmatched:
        cents = int(round((r.total_dollars or 0) * 100))
        if cents <= 0:
            continue
        qty = r.total_quantity or 0
        key = (r.track_title_raw, r.artist_name_raw)
        if key in by_unmatched:
            existing = by_unmatched[key]
            existing["total_revenue_cents"] = (existing.get("total_revenue_cents") or 0) + cents
            existing["total_revenue_dollars"] = existing["total_revenue_cents"] / 100.0
            existing["total_quantity"] = (existing.get("total_quantity") or 0) + qty
        else:
            entry = {
                "song_id": None,
                "title": r.track_title_raw,
                "artist": r.artist_name_raw,
                "isrc": None,
                "total_revenue_cents": cents,
                "total_revenue_dollars": cents / 100.0,
                "total_quantity": qty,
                "unmatched": True,
            }
            earnings.append(entry)
            by_unmatched[key] = entry

    earnings.sort(key=lambda x: x.get("total_revenue_cents", 0) or 0, reverse=True)

    return {"earnings": earnings}


@router.get("/payments/{org_id}", summary="List royalty payments", description='Returns recorded payments out to creators with status and amounts.\n\n**Path parameter:** `org_id`.\n**Query:** `creator_id`, `status`, `period_start`, `period_end`, `limit`, `offset`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ total, payments: [{id, creator_id, creator_name, amount_cents, currency, paid_at, method, reference}] }`.')
def list_payments(
    org_id: int,
    status: Optional[str] = None,
    payee_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(Payment).filter(Payment.organization_id == org_id)
    if status:
        query = query.filter(Payment.status == status)
    if payee_id:
        query = query.filter(Payment.payee_id == payee_id)
    total = query.count()
    payments = query.order_by(desc(Payment.created_at)).offset(skip).limit(limit).all()

    results = []
    for p in payments:
        payee = db.query(Creator).filter(Creator.id == p.payee_id).first()
        contract = db.query(Contract).filter(Contract.id == p.contract_id).first() if p.contract_id else None
        results.append({
            "id": p.id,
            "payee_id": p.payee_id,
            "payee_name": payee.display_name if payee else None,
            "contract_id": p.contract_id,
            "contract_title": contract.title if contract else None,
            "amount_cents": p.amount_cents,
            "amount_dollars": p.amount_cents / 100.0,
            "currency": p.currency,
            "period_start": p.period_start.isoformat() if p.period_start else None,
            "period_end": p.period_end.isoformat() if p.period_end else None,
            "status": p.status,
            "payment_date": p.payment_date.isoformat() if p.payment_date else None,
            "payment_method": p.payment_method,
            "payment_reference": p.payment_reference,
            "notes": p.notes,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None,
        })

    return {"total": total, "skip": skip, "limit": limit, "payments": results}


@router.post("/payments/{org_id}", summary="Record a royalty payment", description='Records a cash disbursement to a creator. Updates outstanding balances accordingly and creates an audit entry.\n\n**Path parameter:** `org_id`.\n**Body:** `{ creator_id, amount_cents, currency, paid_at?: date, method?: string, reference?: string, note?: string }`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** the created payment.')
def create_payment(
    org_id: int,
    body: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    payee = db.query(Creator).filter(Creator.id == body.payee_id, Creator.organization_id == org_id).first()
    if not payee:
        raise HTTPException(status_code=404, detail="Payee not found in this organization")

    if body.contract_id:
        contract = db.query(Contract).filter(Contract.id == body.contract_id, Contract.organization_id == org_id).first()
        if not contract:
            raise HTTPException(status_code=404, detail="Contract not found in this organization")

    payment = Payment(
        organization_id=org_id,
        payee_id=body.payee_id,
        contract_id=body.contract_id,
        amount_cents=body.amount_cents,
        currency=body.currency,
        period_start=body.period_start,
        period_end=body.period_end,
        status="PENDING",
        payment_method=body.payment_method,
        payment_reference=body.payment_reference,
        notes=body.notes,
        created_by_user_id=current_user.id,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)

    return {
        "id": payment.id,
        "status": payment.status,
        "amount_cents": payment.amount_cents,
        "amount_dollars": payment.amount_cents / 100.0,
    }


@router.patch(
    "/payments/{org_id}/{payment_id}",
    summary='Update Payment',
    description='Patches editable fields on a recorded RoyaltyPayment — most commonly to update `status` (pending → paid → cleared) or fix a wrong `amount_cents` / `payment_date` after entry.\n\n**Path parameters:** `org_id`, `payment_id`.\n**Body:** any subset of `{ status, amount_cents, payment_date, memo, reference }`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ id, status, amount_cents, amount_dollars, payment_date }`.',
)
def update_payment(
    org_id: int,
    payment_id: int,
    body: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    payment = db.query(Payment).filter(
        Payment.id == payment_id,
        Payment.organization_id == org_id,
    ).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    if body.status is not None:
        payment.status = body.status
    if body.payment_date is not None:
        payment.payment_date = body.payment_date
    if body.payment_method is not None:
        payment.payment_method = body.payment_method
    if body.payment_reference is not None:
        payment.payment_reference = body.payment_reference
    if body.notes is not None:
        payment.notes = body.notes

    db.commit()
    db.refresh(payment)

    return {
        "id": payment.id,
        "status": payment.status,
        "amount_cents": payment.amount_cents,
        "amount_dollars": payment.amount_cents / 100.0,
        "payment_date": payment.payment_date.isoformat() if payment.payment_date else None,
    }


class FeeCreate(BaseModel):
    creator_id: int
    contract_id: Optional[int] = None
    song_id: Optional[int] = None
    placement_id: Optional[int] = None
    fee_type: str = "MANAGEMENT_FEE"
    description: Optional[str] = None
    amount_cents: int = 0
    currency: str = "USD"
    fee_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    notes: Optional[str] = None


class FeeUpdate(BaseModel):
    fee_type: Optional[str] = None
    description: Optional[str] = None
    amount_cents: Optional[int] = None
    fee_date: Optional[date] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class AdvanceCreate(BaseModel):
    creator_id: int
    contract_id: Optional[int] = None
    description: Optional[str] = None
    amount_cents: int = 0
    currency: str = "USD"
    advance_date: Optional[date] = None
    notes: Optional[str] = None


class AdvanceUpdate(BaseModel):
    description: Optional[str] = None
    recouped_cents: Optional[int] = None
    advance_date: Optional[date] = None
    fully_recouped: Optional[bool] = None
    status: Optional[str] = None
    notes: Optional[str] = None


def fee_to_dict(f: Fee, db: Session) -> dict:
    creator = db.query(Creator).filter(Creator.id == f.creator_id).first()
    contract = db.query(Contract).filter(Contract.id == f.contract_id).first() if f.contract_id else None
    song = db.query(Song).filter(Song.id == f.song_id).first() if f.song_id else None
    return {
        "id": f.id,
        "creator_id": f.creator_id,
        "creator_name": creator.display_name if creator else None,
        "contract_id": f.contract_id,
        "contract_title": contract.title if contract else None,
        "song_id": f.song_id,
        "song_title": song.title if song else None,
        "placement_id": f.placement_id,
        "fee_type": f.fee_type,
        "description": f.description,
        "amount_cents": f.amount_cents,
        "amount_dollars": f.amount_cents / 100.0,
        "currency": f.currency,
        "fee_date": f.fee_date.isoformat() if f.fee_date else None,
        "period_start": f.period_start.isoformat() if f.period_start else None,
        "period_end": f.period_end.isoformat() if f.period_end else None,
        "status": f.status,
        "notes": f.notes,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


def advance_to_dict(a: Advance, db: Session) -> dict:
    creator = db.query(Creator).filter(Creator.id == a.creator_id).first()
    contract = db.query(Contract).filter(Contract.id == a.contract_id).first() if a.contract_id else None
    return {
        "id": a.id,
        "creator_id": a.creator_id,
        "creator_name": creator.display_name if creator else None,
        "contract_id": a.contract_id,
        "contract_title": contract.title if contract else None,
        "description": a.description,
        "amount_cents": a.amount_cents,
        "amount_dollars": a.amount_cents / 100.0,
        "recouped_cents": a.recouped_cents,
        "recouped_dollars": a.recouped_cents / 100.0,
        "remaining_cents": a.amount_cents - a.recouped_cents,
        "remaining_dollars": (a.amount_cents - a.recouped_cents) / 100.0,
        "recoupment_pct": round((a.recouped_cents / a.amount_cents * 100), 1) if a.amount_cents > 0 else 0,
        "currency": a.currency,
        "advance_date": a.advance_date.isoformat() if a.advance_date else None,
        "fully_recouped": a.fully_recouped,
        "status": a.status,
        "notes": a.notes,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.get(
    "/fees/{org_id}",
    summary='List Fees',
    description="Returns the org's RoyaltyFee configurations — admin/processing fees that are subtracted from gross before allocation. Each fee has a scope (org-wide, contract, or creator) and a type (percentage or flat).\n\n**Path parameter:** `org_id`.\n**Query:** `creator_id`, `contract_id`, `active` (bool).\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ total, fees: [{id, name, fee_type, rate_pct, flat_amount_cents, scope, creator_id, contract_id, active, effective_from, effective_to}] }`.",
)
def list_fees(
    org_id: int,
    creator_id: Optional[int] = None,
    fee_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(Fee).filter(Fee.organization_id == org_id)
    if creator_id:
        query = query.filter(Fee.creator_id == creator_id)
    if fee_type:
        query = query.filter(Fee.fee_type == fee_type)
    fees = query.order_by(desc(Fee.created_at)).all()
    return {"fees": [fee_to_dict(f, db) for f in fees], "total": len(fees)}


@router.post(
    "/fees/{org_id}",
    summary='Create Fee',
    description='Defines a new processing fee that future statement calculations will deduct.\n\n**Path parameter:** `org_id`.\n**Body:** `{ name, fee_type: "percentage"|"flat", rate_pct?, flat_amount_cents?, scope: "org"|"contract"|"creator", creator_id?, contract_id?, effective_from?, effective_to? }`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** the created fee object.',
)
def create_fee(
    org_id: int,
    body: FeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    creator = db.query(Creator).filter(Creator.id == body.creator_id, Creator.organization_id == org_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    fee = Fee(
        organization_id=org_id,
        creator_id=body.creator_id,
        contract_id=body.contract_id,
        song_id=body.song_id,
        placement_id=body.placement_id,
        fee_type=body.fee_type,
        description=body.description,
        amount_cents=body.amount_cents,
        currency=body.currency,
        fee_date=body.fee_date,
        period_start=body.period_start,
        period_end=body.period_end,
        notes=body.notes,
        created_by_user_id=current_user.id,
    )
    db.add(fee)
    db.commit()
    db.refresh(fee)
    return fee_to_dict(fee, db)


@router.patch(
    "/fees/{org_id}/{fee_id}",
    summary='Update Fee',
    description='Patches an existing fee. Does **not** retroactively recompute already-calculated statements.\n\n**Path parameters:** `org_id`, `fee_id`.\n**Body:** any subset of writable fields from create.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** the updated fee object.',
)
def update_fee(
    org_id: int,
    fee_id: int,
    body: FeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    fee = db.query(Fee).filter(Fee.id == fee_id, Fee.organization_id == org_id).first()
    if not fee:
        raise HTTPException(status_code=404, detail="Fee not found")
    for field, value in body.dict(exclude_unset=True).items():
        setattr(fee, field, value)
    db.commit()
    db.refresh(fee)
    return fee_to_dict(fee, db)


@router.delete(
    "/fees/{org_id}/{fee_id}",
    summary='Delete Fee',
    description='Hard-deletes a fee. Allocations that previously applied this fee keep their historical numbers; only future calculations are affected.\n\n**Path parameters:** `org_id`, `fee_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ status: "deleted" }`.',
)
def delete_fee(
    org_id: int,
    fee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    fee = db.query(Fee).filter(Fee.id == fee_id, Fee.organization_id == org_id).first()
    if not fee:
        raise HTTPException(status_code=404, detail="Fee not found")
    db.delete(fee)
    db.commit()
    return {"status": "deleted"}


@router.get(
    "/advances/{org_id}",
    summary='List Advances',
    description='Returns the legacy v1 Advance records for the org (see `/api/royalty-processing/.../advances` for the v2 model). Each advance has a principal, recouped amount, and remaining balance against a creator or contract.\n\n**Path parameter:** `org_id`.\n**Query:** `creator_id`, `contract_id`, `recouped` (bool).\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ total, advances: [{id, name, principal_cents, recouped_cents, outstanding_cents, currency, creator_id, contract_id, advance_date, recoupable}] }`.',
)
def list_advances(
    org_id: int,
    creator_id: Optional[int] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    query = db.query(Advance).filter(Advance.organization_id == org_id)
    if creator_id:
        query = query.filter(Advance.creator_id == creator_id)
    if status:
        query = query.filter(Advance.status == status)
    advances = query.order_by(desc(Advance.created_at)).all()
    return {"advances": [advance_to_dict(a, db) for a in advances], "total": len(advances)}


@router.post(
    "/advances/{org_id}",
    summary='Create Advance',
    description='Records a new advance against a creator or contract that future allocations will recoup against.\n\n**Path parameter:** `org_id`.\n**Body:** `{ name, principal_cents, currency?, creator_id?, contract_id?, advance_date?, recoupable? (default true), notes? }`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** the created advance object.',
)
def create_advance(
    org_id: int,
    body: AdvanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    creator = db.query(Creator).filter(Creator.id == body.creator_id, Creator.organization_id == org_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    advance = Advance(
        organization_id=org_id,
        creator_id=body.creator_id,
        contract_id=body.contract_id,
        description=body.description,
        amount_cents=body.amount_cents,
        currency=body.currency,
        advance_date=body.advance_date,
        notes=body.notes,
        created_by_user_id=current_user.id,
    )
    db.add(advance)
    db.commit()
    db.refresh(advance)
    return advance_to_dict(advance, db)


@router.patch(
    "/advances/{org_id}/{advance_id}",
    summary='Update Advance',
    description='Patches editable fields on an advance. Does not retroactively rewrite recouped amounts.\n\n**Path parameters:** `org_id`, `advance_id`.\n**Body:** any subset of writable fields from create.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** the updated advance object.',
)
def update_advance(
    org_id: int,
    advance_id: int,
    body: AdvanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    advance = db.query(Advance).filter(Advance.id == advance_id, Advance.organization_id == org_id).first()
    if not advance:
        raise HTTPException(status_code=404, detail="Advance not found")
    for field, value in body.dict(exclude_unset=True).items():
        setattr(advance, field, value)
    if advance.recouped_cents >= advance.amount_cents and advance.amount_cents > 0:
        advance.fully_recouped = True
    db.commit()
    db.refresh(advance)
    return advance_to_dict(advance, db)


@router.delete(
    "/advances/{org_id}/{advance_id}",
    summary='Delete Advance',
    description='Hard-deletes an advance. Use with care — historical allocations that recouped against it stay numerically intact but lose the back-link.\n\n**Path parameters:** `org_id`, `advance_id`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ status: "deleted" }`.',
)
def delete_advance(
    org_id: int,
    advance_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    advance = db.query(Advance).filter(Advance.id == advance_id, Advance.organization_id == org_id).first()
    if not advance:
        raise HTTPException(status_code=404, detail="Advance not found")
    db.delete(advance)
    db.commit()
    return {"status": "deleted"}


@router.post(
    "/confirm-contract-payment/{org_id}/{contract_id}",
    summary='Confirm Contract Payment',
    description="Marks a contract-scoped advance/payment as confirmed — flips the contract's payment state to paid, posts the corresponding RoyaltyPayment, and records the audit trail. Used when an advance check has cleared.\n\n**Path parameters:** `org_id`, `contract_id`.\n**Body:** `{ amount_cents, payment_date, reference?, memo? }`.\n\n**Auth:** Bearer JWT. Caller must be a member of the org.\n\n**Response:** `{ contract_id, payment_id, status, amount_cents }`.",
)
def confirm_contract_payment(
    org_id: int,
    contract_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.organization_id == org_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    advance_amount = contract.advance_amount or 0
    if advance_amount <= 0:
        raise HTTPException(status_code=400, detail="No advance amount on this contract")

    existing_advance = db.query(Advance).filter(
        Advance.organization_id == org_id,
        Advance.contract_id == contract_id,
    ).first()

    if existing_advance:
        return {"status": "already_confirmed", "contract_id": contract_id}

    contract.advance_recouped = advance_amount
    if contract.status in ("DRAFT", "PENDING"):
        contract.status = "ACTIVE"

    if contract.creator_id:
        direction = contract.payment_direction or "INCOMING"
        new_advance = Advance(
            organization_id=org_id,
            creator_id=contract.creator_id,
            contract_id=contract_id,
            description=f"Advance from {contract.title}",
            amount_cents=int(advance_amount * 100),
            recouped_cents=0,
            currency=contract.advance_currency or "USD",
            advance_date=contract.start_date or datetime.utcnow().date(),
            fully_recouped=False,
            status="ACTIVE" if direction == "OUTGOING" else "RECEIVED",
            notes=f"Auto-created from contract confirmation. Direction: {direction}",
            created_by_user_id=current_user.id,
        )
        db.add(new_advance)

    db.commit()
    return {"status": "confirmed", "contract_id": contract_id}


@router.get("/creator-accounting/{org_id}/{creator_id}", summary="Per-creator accounting view", description='Full earnings + payments + advances + fees rollup for a single creator across all statements.\n\n**Path parameters:** `org_id`, `creator_id`.\n**Query:** `period_start`, `period_end`, `currency`.\n**Auth:** Bearer JWT — caller must be a member of the org.\n**Response:** `{ creator_id, gross_cents, net_cents, paid_cents, balance_cents, advances: [...], by_period: [...], by_source: [...] }`.')
def get_creator_accounting(
    org_id: int,
    creator_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db, creator_id=creator_id)

    creator = db.query(Creator).filter(Creator.id == creator_id, Creator.organization_id == org_id).first()
    if not creator:
        raise HTTPException(status_code=404, detail="Creator not found")

    allocations = db.query(RoyaltyAllocation).filter(
        RoyaltyAllocation.organization_id == org_id,
        RoyaltyAllocation.rights_holder_id == creator_id,
    ).all()
    total_royalties_cents = sum(a.allocated_cents for a in allocations)

    if total_royalties_cents == 0:
        creator_statements = db.query(RoyaltyStatement).filter(
            RoyaltyStatement.organization_id == org_id,
            RoyaltyStatement.creator_id == creator_id,
            RoyaltyStatement.status.in_(["PROCESSED", "PARTIALLY_MATCHED", "FULLY_MATCHED"]),
        ).all()
        statement_revenue_cents = sum(s.total_revenue_cents or 0 for s in creator_statements)

        creator_songs = db.query(Song).filter(
            Song.organization_id == org_id,
            Song.creator_id == creator_id,
        ).all()
        creator_song_ids_set = {s.id for s in creator_songs}
        if creator_song_ids_set:
            from sqlalchemy import func as sa_func
            matched_revenue = db.query(sa_func.coalesce(sa_func.sum(RoyaltyTransaction.revenue_cents), 0)).filter(
                RoyaltyTransaction.organization_id == org_id,
                RoyaltyTransaction.song_id.in_(creator_song_ids_set),
            ).scalar() or 0
            statement_revenue_cents = max(statement_revenue_cents, matched_revenue)

        total_royalties_cents = statement_revenue_cents

    payments = db.query(Payment).filter(
        Payment.organization_id == org_id,
        Payment.payee_id == creator_id,
    ).order_by(desc(Payment.created_at)).all()
    total_paid_cents = sum(p.amount_cents for p in payments if p.status == "PAID")
    total_pending_cents = sum(p.amount_cents for p in payments if p.status == "PENDING")

    fees = db.query(Fee).filter(Fee.organization_id == org_id, Fee.creator_id == creator_id).order_by(desc(Fee.created_at)).all()
    total_fees_cents = sum(f.amount_cents for f in fees)

    advances = db.query(Advance).filter(Advance.organization_id == org_id, Advance.creator_id == creator_id).order_by(desc(Advance.created_at)).all()
    total_advances_cents = sum(a.amount_cents for a in advances)
    total_recouped_cents = sum(a.recouped_cents for a in advances)
    outstanding_advances_cents = total_advances_cents - total_recouped_cents

    placements = db.query(Placement).filter(Placement.organization_id == org_id).all()
    creator_song_ids = [s.id for s in db.query(Song).filter(Song.organization_id == org_id).all()]

    placement_revenue_cents = 0
    for p in placements:
        if p.song_id and p.song_id in creator_song_ids and p.status == "PAID" and p.license_fee:
            placement_revenue_cents += int(p.license_fee * 100)

    contracts = db.query(Contract).filter(
        Contract.organization_id == org_id,
        Contract.creator_id == creator_id,
    ).order_by(desc(Contract.created_at)).all()

    contract_items = []
    contract_incoming_pending_cents = 0
    contract_outgoing_pending_cents = 0
    contract_incoming_confirmed_cents = 0
    contract_outgoing_confirmed_cents = 0

    for c in contracts:
        advance_cents = int((c.advance_amount or 0) * 100)
        recouped_cents_val = int((c.advance_recouped or 0) * 100)
        direction = c.payment_direction or "INCOMING"

        has_linked_advance = db.query(Advance).filter(
            Advance.organization_id == org_id,
            Advance.contract_id == c.id,
        ).first() is not None
        is_confirmed = has_linked_advance

        if advance_cents > 0:
            if direction == "INCOMING":
                if is_confirmed:
                    contract_incoming_confirmed_cents += advance_cents
                else:
                    contract_incoming_pending_cents += advance_cents
            else:
                if is_confirmed:
                    contract_outgoing_confirmed_cents += advance_cents
                else:
                    contract_outgoing_pending_cents += advance_cents

        contract_items.append({
            "id": c.id,
            "title": c.title,
            "contract_type": c.contract_type,
            "payment_direction": direction,
            "status": c.status,
            "advance_amount": c.advance_amount or 0,
            "advance_amount_cents": advance_cents,
            "advance_currency": c.advance_currency or "USD",
            "advance_recouped": c.advance_recouped or 0,
            "advance_recouped_cents": recouped_cents_val,
            "is_confirmed": is_confirmed,
            "start_date": c.start_date.isoformat() if c.start_date else None,
            "end_date": c.end_date.isoformat() if c.end_date else None,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    net_balance_cents = total_royalties_cents + placement_revenue_cents - total_fees_cents - total_paid_cents

    payment_list = []
    for p in payments:
        contract = db.query(Contract).filter(Contract.id == p.contract_id).first() if p.contract_id else None
        payment_list.append({
            "id": p.id,
            "amount_cents": p.amount_cents,
            "amount_dollars": p.amount_cents / 100.0,
            "currency": p.currency,
            "status": p.status,
            "payment_date": p.payment_date.isoformat() if p.payment_date else None,
            "payment_method": p.payment_method,
            "contract_title": contract.title if contract else None,
            "notes": p.notes,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })

    return {
        "creator_id": creator_id,
        "creator_name": creator.display_name,
        "summary": {
            "total_royalties_cents": total_royalties_cents,
            "total_royalties_dollars": total_royalties_cents / 100.0,
            "total_paid_cents": total_paid_cents,
            "total_paid_dollars": total_paid_cents / 100.0,
            "total_pending_cents": total_pending_cents,
            "total_pending_dollars": total_pending_cents / 100.0,
            "total_fees_cents": total_fees_cents,
            "total_fees_dollars": total_fees_cents / 100.0,
            "total_advances_cents": total_advances_cents,
            "total_advances_dollars": total_advances_cents / 100.0,
            "total_recouped_cents": total_recouped_cents,
            "total_recouped_dollars": total_recouped_cents / 100.0,
            "outstanding_advances_cents": outstanding_advances_cents,
            "outstanding_advances_dollars": outstanding_advances_cents / 100.0,
            "placement_revenue_cents": placement_revenue_cents,
            "placement_revenue_dollars": placement_revenue_cents / 100.0,
            "net_balance_cents": net_balance_cents,
            "net_balance_dollars": net_balance_cents / 100.0,
            "contract_incoming_pending_cents": contract_incoming_pending_cents,
            "contract_incoming_pending_dollars": contract_incoming_pending_cents / 100.0,
            "contract_outgoing_pending_cents": contract_outgoing_pending_cents,
            "contract_outgoing_pending_dollars": contract_outgoing_pending_cents / 100.0,
            "contract_incoming_confirmed_cents": contract_incoming_confirmed_cents,
            "contract_incoming_confirmed_dollars": contract_incoming_confirmed_cents / 100.0,
            "contract_outgoing_confirmed_cents": contract_outgoing_confirmed_cents,
            "contract_outgoing_confirmed_dollars": contract_outgoing_confirmed_cents / 100.0,
        },
        "contracts": contract_items,
        "payments": payment_list,
        "fees": [fee_to_dict(f, db) for f in fees],
        "advances": [advance_to_dict(a, db) for a in advances],
    }
