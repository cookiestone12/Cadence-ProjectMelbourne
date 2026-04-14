from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from difflib import SequenceMatcher
import csv
import io
import re
import logging

from ..models import (
    get_db, User, OrganizationMember, Song, Creator,
    Contract, ContractAsset, RightsSplit,
    RoyaltyStatement, RoyaltyTransaction, RoyaltyAllocation, Payment,
    Fee, Advance, Placement,
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

router = APIRouter(prefix="/api/royalties", tags=["royalties"])


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


COLUMN_HINTS = {
    "isrc": ["isrc"],
    "upc": ["upc", "barcode"],
    "track_title": [
        "title", "track", "song", "track_title", "song_title", "track name", "song name",
        "work title", "composition", "composition title", "work", "musical work",
    ],
    "artist": [
        "artist", "performer", "band", "artist name", "primary artist",
        "writer", "writer name", "composer", "author", "songwriter",
        "interested party", "ip name", "affiliate name", "member name",
    ],
    "revenue": [
        "revenue", "amount", "earnings", "net", "royalty", "payment", "gross", "total", "payout",
        "royalty amount", "net amount", "gross amount", "total earned", "net royalty",
        "domestic amount", "foreign amount", "total amount", "license fee",
        "accrued amount", "accrual amount",
    ],
    "quantity": [
        "quantity", "streams", "plays", "downloads", "units", "count",
        "performances", "performance count", "feature performances", "total performances",
        "credits", "detections", "spins",
    ],
    "territory": ["territory", "country", "region", "market"],
    "platform": [
        "platform", "store", "service", "dsp", "source",
        "licensee", "music user", "station", "network", "broadcaster",
        "survey type", "medium", "use type",
    ],
    "revenue_type": [
        "type", "revenue_type", "sale type", "transaction type", "usage type",
        "right type", "rights type", "royalty type", "income type", "license type",
        "performance type", "category",
    ],
    "publisher": [
        "publisher", "publisher name", "original publisher", "sub-publisher",
        "admin publisher", "pub name",
    ],
    "iswc": ["iswc", "work code", "work id"],
    "work_id": [
        "work id", "work #", "work number", "song code", "song number", "internal id",
        "bmi work#", "ascap work id", "sesac work id", "bmi work id",
    ],
    "share_percentage": [
        "share", "share %", "ownership", "ownership %", "percentage",
        "writer share", "publisher share", "split", "pro rata",
    ],
}

PRO_SOURCE_TYPES = {
    "BMI": {
        "keywords": ["bmi", "broadcast music"],
        "extra_hints": {
            "track_title": ["work title", "song title"],
            "artist": ["writer", "writer name", "affiliated writer"],
            "revenue": ["current activity royalty", "royalty amount", "total earned", "accrued amount"],
            "quantity": ["performances", "performance count", "credits", "total performances"],
            "work_id": ["bmi work#", "work #", "bmi work id", "song number"],
            "platform": ["source", "survey type", "medium"],
        }
    },
    "ASCAP": {
        "keywords": ["ascap", "american society"],
        "extra_hints": {
            "track_title": ["title", "work title"],
            "artist": ["writer/publisher", "interested party", "writer name"],
            "revenue": ["dollars", "amount", "domestic amount", "foreign amount", "total earned"],
            "quantity": ["credits", "performances"],
            "work_id": ["ascap work id", "work id"],
        }
    },
    "SESAC": {
        "keywords": ["sesac"],
        "extra_hints": {
            "track_title": ["composition", "title"],
            "artist": ["affiliate", "writer"],
            "revenue": ["royalty", "amount", "net amount"],
            "quantity": ["performances", "detections"],
            "work_id": ["sesac work id", "song code"],
        }
    },
    "SoundExchange": {
        "keywords": ["soundexchange", "sound exchange"],
        "extra_hints": {
            "track_title": ["featured title", "track title", "sound recording"],
            "artist": ["featured artist", "artist"],
            "revenue": ["royalty", "amount"],
            "quantity": ["performances", "plays"],
        }
    },
    "SOCAN": {
        "keywords": ["socan"],
        "extra_hints": {
            "track_title": ["work title", "title"],
            "artist": ["member", "writer"],
            "revenue": ["distribution amount", "amount"],
        }
    },
    "PRS": {
        "keywords": ["prs", "prs for music"],
        "extra_hints": {
            "track_title": ["work title", "title"],
            "artist": ["writer", "member"],
            "revenue": ["royalty", "amount", "net"],
        }
    },
    "MLC": {
        "keywords": ["mlc", "mechanical licensing collective", "the mlc"],
        "extra_hints": {
            "track_title": ["song title", "track title", "title", "work title"],
            "artist": ["performer", "artist", "writer"],
            "revenue": ["royalty", "amount", "net amount", "total earned", "payment amount"],
            "isrc": ["isrc"],
            "iswc": ["iswc", "hfa song code"],
            "quantity": ["streams", "plays", "uses"],
            "platform": ["service", "dsp", "licensee"],
        }
    },
}


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

    mapping = {}
    used_headers = set()
    for field, field_hints in hints.items():
        best_match = None
        for header in headers:
            if header in used_headers:
                continue
            lower = header.lower().strip()
            lower_clean = re.sub(r'\s+', ' ', lower)
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
            from ..utils.pdf_statement_parser import is_publishing_statement, parse_publishing_statement
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


@router.post("/statements/{org_id}/preview")
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


@router.get("/creators-summary/{org_id}")
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


@router.post("/statements/{org_id}/assign-unassigned")
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


@router.get("/statements/{org_id}")
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


@router.get("/statements/{org_id}/{statement_id}")
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


@router.post("/statements/{org_id}/upload")
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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)
    source_name = normalize_source_name(source_name)
    content = await file.read()
    headers, rows, pdf_metadata = parse_uploaded_file(content, file.filename or "data.csv", org_id=org_id)

    detected_pro = detect_pro_source(headers, source_name or "", file.filename or "")
    if detected_pro and not source_type:
        source_type = detected_pro

    suggested = pdf_metadata.get("suggested_mapping") if pdf_metadata else None
    if suggested:
        mapping = suggested
    elif column_mapping:
        import json
        try:
            mapping = json.loads(column_mapping)
        except Exception:
            mapping = suggest_column_mapping(headers, source_name or "")
    else:
        mapping = suggest_column_mapping(headers, source_name or "")

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
        statement.total_revenue_cents = int(round(grand_total_net * 100))
        logger.info(f"Using PDF Grand Total for revenue: ${grand_total_net:.2f} (parsed sum: ${total_rev / 100:.2f})")
    else:
        statement.total_revenue_cents = total_rev
    statement.total_transactions = len(transactions)
    statement.matched_transactions = matched_count
    statement.unmatched_transactions = unmatched_count
    statement.status = "PROCESSED" if unmatched_count == 0 else "PARTIALLY_MATCHED"

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


@router.delete("/statements/{org_id}/{statement_id}")
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

    from ..models.models import RoyaltyLedgerEntry, RoyaltyProcessingRun, RoyaltyStatementLine

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

    from ..services.audit_service import log_action
    log_action(db, org_id, current_user.id, "DELETE", "STATEMENT", stmt.id, stmt.source_name)

    db.delete(stmt)
    db.commit()
    return {"detail": "Statement deleted"}


@router.get("/statements/{org_id}/{statement_id}/transactions")
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


@router.post("/statements/{org_id}/{statement_id}/match/{transaction_id}")
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


@router.post("/statements/{org_id}/{statement_id}/rematch")
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


@router.post("/calculate/{org_id}/{statement_id}")
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


@router.get("/allocations/{org_id}")
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


@router.get("/dashboard/{org_id}")
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

    matched_tracks = db.query(
        Song.id, Song.title, Song.primary_artist,
        func.sum(RoyaltyTransaction.revenue_cents).label("total_cents"),
        func.sum(RoyaltyTransaction.quantity).label("total_quantity"),
    ).join(
        RoyaltyTransaction, RoyaltyTransaction.song_id == Song.id
    ).filter(
        RoyaltyTransaction.organization_id == org_id,
    ).group_by(Song.id, Song.title, Song.primary_artist).order_by(
        desc("total_cents")
    ).limit(10).all()

    unmatched_tracks = db.query(
        RoyaltyTransaction.original_track_title,
        RoyaltyTransaction.original_artist,
        func.sum(RoyaltyTransaction.revenue_cents).label("total_cents"),
        func.sum(RoyaltyTransaction.quantity).label("total_quantity"),
    ).filter(
        RoyaltyTransaction.organization_id == org_id,
        RoyaltyTransaction.song_id.is_(None),
        RoyaltyTransaction.original_track_title.isnot(None),
    ).group_by(
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


@router.get("/earnings/{org_id}/by-holder")
def earnings_by_holder(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    alloc_results = db.query(
        Creator.id, Creator.display_name,
        func.sum(RoyaltyAllocation.allocated_cents).label("total_cents"),
        func.sum(RoyaltyAllocation.recouped_cents).label("total_recouped"),
    ).join(
        RoyaltyAllocation, RoyaltyAllocation.rights_holder_id == Creator.id
    ).filter(
        RoyaltyAllocation.organization_id == org_id,
    ).group_by(Creator.id, Creator.display_name).order_by(desc("total_cents")).all()

    alloc_map = {}
    for r in alloc_results:
        alloc_map[r.id] = {
            "allocated_cents": r.total_cents or 0,
            "recouped_cents": r.total_recouped or 0,
        }

    stmt_results = db.query(
        Creator.id, Creator.display_name,
        func.sum(RoyaltyStatement.total_revenue_cents).label("total_revenue"),
        func.count(RoyaltyStatement.id).label("stmt_count"),
    ).join(
        RoyaltyStatement, RoyaltyStatement.creator_id == Creator.id
    ).filter(
        RoyaltyStatement.organization_id == org_id,
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

    earnings = sorted(holders.values(), key=lambda x: x.get("total_revenue_cents", 0), reverse=True)
    return {"earnings": earnings}


@router.get("/earnings/{org_id}/by-contract")
def earnings_by_contract(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    results = db.query(
        Contract.id, Contract.title, Contract.advance_amount, Contract.advance_recouped,
        func.sum(RoyaltyAllocation.allocated_cents).label("total_cents"),
        func.sum(RoyaltyAllocation.recouped_cents).label("total_recouped"),
    ).join(
        RoyaltyAllocation, RoyaltyAllocation.contract_id == Contract.id
    ).filter(
        RoyaltyAllocation.organization_id == org_id,
    ).group_by(Contract.id, Contract.title, Contract.advance_amount, Contract.advance_recouped).order_by(desc("total_cents")).all()

    return {
        "earnings": [
            {
                "contract_id": r.id,
                "contract_title": r.title,
                "advance_amount": r.advance_amount or 0,
                "advance_recouped": r.advance_recouped or 0,
                "remaining_advance": max((r.advance_amount or 0) - (r.advance_recouped or 0), 0),
                "recoupment_percentage": round(((r.advance_recouped or 0) / r.advance_amount) * 100, 2) if r.advance_amount and r.advance_amount > 0 else 0,
                "total_allocated_cents": r.total_cents,
                "total_allocated_dollars": r.total_cents / 100.0,
                "total_recouped_cents": r.total_recouped,
                "net_earned_cents": r.total_cents - r.total_recouped,
                "net_earned_dollars": (r.total_cents - r.total_recouped) / 100.0,
            }
            for r in results
        ]
    }


@router.get("/earnings/{org_id}/by-track")
def earnings_by_track(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    verify_org_access(current_user, org_id, db)

    matched_results = db.query(
        Song.id, Song.title, Song.primary_artist, Song.isrc,
        func.sum(RoyaltyTransaction.revenue_cents).label("total_revenue_cents"),
        func.sum(RoyaltyTransaction.quantity).label("total_quantity"),
    ).join(
        RoyaltyTransaction, RoyaltyTransaction.song_id == Song.id
    ).filter(
        RoyaltyTransaction.organization_id == org_id,
    ).group_by(Song.id, Song.title, Song.primary_artist, Song.isrc).order_by(desc("total_revenue_cents")).all()

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

    unmatched_results = db.query(
        RoyaltyTransaction.original_track_title,
        RoyaltyTransaction.original_artist,
        func.sum(RoyaltyTransaction.revenue_cents).label("total_revenue_cents"),
        func.sum(RoyaltyTransaction.quantity).label("total_quantity"),
    ).filter(
        RoyaltyTransaction.organization_id == org_id,
        RoyaltyTransaction.song_id.is_(None),
        RoyaltyTransaction.original_track_title.isnot(None),
    ).group_by(
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

    earnings.sort(key=lambda x: x.get("total_revenue_cents", 0) or 0, reverse=True)

    return {"earnings": earnings}


@router.get("/payments/{org_id}")
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


@router.post("/payments/{org_id}")
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


@router.patch("/payments/{org_id}/{payment_id}")
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


@router.get("/fees/{org_id}")
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


@router.post("/fees/{org_id}")
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


@router.patch("/fees/{org_id}/{fee_id}")
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


@router.delete("/fees/{org_id}/{fee_id}")
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


@router.get("/advances/{org_id}")
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


@router.post("/advances/{org_id}")
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


@router.patch("/advances/{org_id}/{advance_id}")
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


@router.delete("/advances/{org_id}/{advance_id}")
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


@router.post("/confirm-contract-payment/{org_id}/{contract_id}")
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


@router.get("/creator-accounting/{org_id}/{creator_id}")
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
